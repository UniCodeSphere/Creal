#!/usr/bin/env python3
import os, re, tempfile, sys, argparse, shutil
from datetime import datetime
from copy import deepcopy, copy
import random
import subprocess as sp
import ctypes
from enum import Enum, auto
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from databaseconstructor.functioner import *
from databaseconstructor.variable import *

CC1 = "gcc" # use two compilers to avoid unspecified behavior
CC2 = "clang"
NUM_ENV = 5 # number of env variables used for each tag, "1" means one env_val, e.g., Tag1:tag_val:env_val
PROFILER = f"{os.path.dirname(__file__)}/../profiler/build/bin/profiler --mode=expr"
CSMITH_HOME = os.environ["CSMITH_HOME"]

INVALID_TAG_VALUE = 111 # we use this value to indicate invalid tag values

class CMD(Enum):
    OK      =   auto()
    Timeout =   auto()
    Error   =   auto()

class VarValue(Enum):
    STABLE      =   auto() # value has been the same
    UNSTABLE    =   auto() # value has been changing

class Var:
    """Variable"""
    var_name:str            # variable name
    var_type:str            # variable type as string
    var_value:int           # value
    is_stable:bool = True   # if the variable values is stable, i.e., never changed or len(set(values))<=1.
    is_constant:bool=False  # variable has "const" keyword
    is_global:bool=False    # if the vairable has global storage
    scope_id:int=-1         # scope id of the variable

class Tag:
    """Tag"""
    tag_id:int
    tag_str:str                 # the original tag string showsn in the source file
    tag_check_strs:list[str]=[] # inserted tag and tagcheck strings
    tag_var:Var                 # tagged variable
    tag_envs:list[Var]          # env vairales
    statement_id:int            # id of the statement that the Tag belongs to
    is_statement:bool = False   # if this tag is a stand-alone statement

class ScopeTree:
    def __init__(self, id:int) -> None:
        self.parent = None
        self.children = []
        self.id = id

def run_cmd(cmd, timeout=10, DEBUG=False):
    if type(cmd) is not list:
        cmd = cmd.split(' ')
    if DEBUG:
        print(datetime.now().strftime("%d/%m/%Y %H:%M:%S"), ">>run_cmd: \n", ' '.join(cmd), flush=True)
    ret, out = CMD.OK, ''
    try:
        process = sp.run(cmd, timeout=timeout, capture_output=True)
        if DEBUG:
            print(datetime.now().strftime("%d/%m/%Y %H:%M:%S"), ">>run_cmd: exit.", flush=True)
        out = process.stdout.decode("utf-8")
        if process.returncode != 0:
            ret = CMD.Error
    except sp.TimeoutExpired:
        if DEBUG:
            print(datetime.now().strftime("%d/%m/%Y %H:%M:%S"), ">>run_cmd: time out.", flush=True)
        ret = CMD.Timeout
    if DEBUG:
        print(datetime.now().strftime("%d/%m/%Y %H:%M:%S"), ">>run_cmd: done.", flush=True)
    return ret, out

def strip_type_str(ori_type_str:str)->str:
    '''Strip type str to remove keywords like const, static, volatile, etc.'''
    return ori_type_str\
        .replace('static', '')\
        .replace('const', '')\
        .replace('volatile', '')\
        .strip()

MAX_CONST_CCOMP = 4611686018427387904 # 2**62, CompCert cannot handle constant values larger than this

class Synthesizer:
    def __init__(self, func_database:str, prob:int) -> None:
        assert 0 < prob <= 100
        self.prob = prob
        self.functionDB = FunctionDB(func_database)
    
    def static_analysis(self, src_file):
        """
        Statically analyze the source file to (1) get tag_var_name for each tag
        and (2) get all variables' values and stabibility information.
        """
        # get global/local information of each tag
        with open(src_file, "r") as f:
            code = f.read()
        static_tags = re.findall(r'(Tag(\d+)\(\/\*(.*?):(\w+):(\w+):(\w+):(\w+)\*\/(.*?)\))', code)
        self.tags = {}
        self.scope_up = {} # key:val ==> child_scope:parent_scope
        self.scope_down = {} # key:[val] ==> parent_scope:[child_scope(s)]
        for tag_info in static_tags:
            tag_str, tag_id, tag_type_str, scope_curr_id, scope_parent_id, stmt_id, tag_style, tag_var_name = tag_info[:]
            tag_id = int(tag_id)
            scope_curr_id = int(scope_curr_id)
            scope_parent_id = int(scope_parent_id)
            assert tag_id not in self.tags
            new_var = Var()
            new_var.scope_id = scope_curr_id
            new_var.is_constant = "const" in tag_type_str
            new_var.var_name = tag_var_name
            new_var.var_type = strip_type_str(tag_type_str)
            new_var.is_global = scope_curr_id == 0

            new_tag = Tag()
            new_tag.tag_str = tag_str
            new_tag.is_statement = tag_style == 's'
            new_tag.tag_var = new_var
            new_tag.tag_envs = []
            new_tag.statement_id = int(stmt_id)
            self.tags[tag_id] = new_tag
            #construct scope_up tree
            if scope_curr_id not in self.scope_up:
                self.scope_up[scope_curr_id] = scope_parent_id
            else:
                assert self.scope_up[scope_curr_id] == scope_parent_id
    
    def valid_scope(self, from_scope:int, to_scope:int) -> bool:
        """Identify if we can access something in to_scope from from_scope"""
        if to_scope == 0: # global
            return True
        if from_scope == to_scope:
            return True
        child_scope = from_scope
        while True:
            if self.scope_up[child_scope] == to_scope:
                return True
            child_scope = self.scope_up[child_scope]
            if child_scope not in self.scope_up or child_scope == self.scope_up[child_scope]:
                break
        return False
    
    def get_envs(self, tag_id, env_num=1):
        """
        Get env vars for the given tag
        """
        curr_scope_id = self.tags[tag_id].tag_var.scope_id
        curr_tag_var_name = self.tags[tag_id].tag_var.var_name
        tag_id_list = list(self.tags.keys())
        tag_index = tag_id_list.index(tag_id)
        MAX_STEP = 20 # search backward or forward for MAX_STEP tags
        envs = []
        env_vars = []
        # for k in range(max(0, tag_index-MAX_STEP), min(len(tag_id_list), tag_index+MAX_STEP)): # search both upward and downward
        for k in range(max(0, tag_index-MAX_STEP), tag_index): # search upward only to avoid use uninitialized variable
            env_tag_id = tag_id_list[k]
            if self.tags[env_tag_id].tag_var.var_name == curr_tag_var_name:
                continue
            #FIXME: this is a work around to avoid using uninitialized i,j,k in csmith generated prgrams
            if self.tags[env_tag_id].tag_var.var_name in ['i', 'j', 'k']:
                continue
            if self.valid_scope(from_scope=curr_scope_id, to_scope=self.tags[env_tag_id].tag_var.scope_id):
                if self.tags[env_tag_id].tag_var.var_name not in env_vars:
                    envs.append(env_tag_id)
                    env_vars.append(self.tags[env_tag_id].tag_var.var_name)
        random.shuffle(envs)
        return envs[:env_num]

    def construct_tag_def(self, tag_id:int, var_types:list[str]) -> str:
        """Construct Tag definition"""
        return_type = var_types[0]
        fmt_strs = ""
        for var_ty in var_types:
            fmt_strs += f':%"{VarType.get_format(VarType.from_str(var_ty))}"'
        v_para_strs = ",".join([f'v{var_i}' for var_i in range(len(var_types))])
        print_tag = f'printf("Tag{tag_id}{fmt_strs}\\n", {v_para_strs});'
        var_defs = []
        count_defs = []
        last_defs = []
        all_i_ones = []
        last_assigns = []
        else_ifs = []
        for var_i, var_ty in enumerate(var_types):
            var_defs.append(f'{var_ty} v{var_i}')
            count_defs.append(f'static char i{var_i}=0;')
            last_defs.append(f'static {var_ty} last_v{var_i}=0;')
            all_i_ones.append(f'i{var_i}=1;')
            last_assigns.append(f'last_v{var_i}=v{var_i};')
            else_ifs.append(f'else if(i{var_i}==1&&v{var_i}!=last_v{var_i}){{{print_tag}i{var_i}=2;}}')
        
        tag_def = \
f'{return_type} Tag{tag_id}({",".join(var_defs)}){{ \
{" ".join(count_defs)} \
{" ".join(last_defs)} \
if (i0 == 0) {{ \
    {"".join(all_i_ones)} \
    {print_tag} \
    {"".join(last_assigns)}\
}} \
{"".join(else_ifs)}\
return v0; \
}}'
        return tag_def

    def add_tags(self, src_file):
        """
        Add Tags for later profiling
        """
        with open(src_file, 'r') as f:
            src = f.read()
        for tag_id in self.tags:
            envs = self.get_envs(tag_id, env_num=NUM_ENV)
            for env_id in envs:
                self.tags[tag_id].tag_envs.append(deepcopy(self.tags[env_id].tag_var))
            envs = [tag_id] + envs # add self as the first env
            envs_str = ','.join([self.tags[env_id].tag_var.var_name if '*' not in self.tags[env_id].tag_var.var_name else '&({var})==0?{invalid}:{var}'.format(var=self.tags[env_id].tag_var.var_name, invalid=INVALID_TAG_VALUE) for env_id in envs])
            # place TagBefore check Call
            bef_tag_call = f'/*bef*/Tag{tag_id}({envs_str});'
            src = src.replace(f'/*bef_stmt:{self.tags[tag_id].statement_id}*/', bef_tag_call, 1)
            self.tags[tag_id].tag_check_strs.append(bef_tag_call+"\n")
            # place Tag call
            tag_call = f'/*tag*/Tag{tag_id}({envs_str})'
            src = src.replace(self.tags[tag_id].tag_str, tag_call, 1)
            # self.tags[tag_id].tag_str = tag_call
            # place TagAfter check Call
            aft_tag_call = f'/*aft*/Tag{tag_id}({envs_str});'
            src = src.replace(f'/*aft_stmt:{self.tags[tag_id].statement_id}*/', aft_tag_call, 1)
            self.tags[tag_id].tag_check_strs.append(aft_tag_call+"\n")
            # replace Tag declaration
            var_types = []
            for env in envs:
                var_types.append(self.tags[env].tag_var.var_type)
            tag_defs = "\n" + self.construct_tag_def(tag_id, var_types)
            src = src.replace(f"#define Tag{tag_id}(x) (x)", tag_defs, 1)
            self.tags[tag_id].tag_check_strs.append(tag_defs + "\n")
        with open(src_file, 'w') as f:
            f.write(src)


    def profiling(self, filename):
        """
        Instrument file with profiler;
        Run and collect values.
        """
        # profiling
        ret, _ = run_cmd(f"{PROFILER} {filename} -- -I{CSMITH_HOME}/include", DEBUG=self.DEBUG)
        if ret != CMD.OK:
            raise SynthesizerError
        
        # further synthesis will be based on self.src_syn instead of self.src to avoid heavy removal of useless tags after synthesis.
        with open(filename, 'r') as f:
            self.src_syn_orig = f.read()
        
        self.static_analysis(filename)
        self.add_tags(filename)

        with tempfile.NamedTemporaryFile(suffix=".out", delete=True) as tmp_f:
            tmp_f.close()
            exe_out = tmp_f.name
            # run with CC1
            ret, _ = run_cmd(f"{CC1} -I{CSMITH_HOME}/include -w -O0 {filename} -o {exe_out}", DEBUG=self.DEBUG)
            if ret != CMD.OK:
                if os.path.exists(exe_out):
                    os.remove(exe_out)
                raise SynthesizerError
            ret, profile_out_1 = run_cmd(exe_out, timeout=3, DEBUG=self.DEBUG)
            if ret != CMD.OK:
                os.remove(exe_out)
                raise SynthesizerError
            os.remove(exe_out)
        env_re_str = ":".join([':?([-|\d]+)?']*(NUM_ENV)) #@FIXME: no need to have exact NUM_ENV env vars here, now a temp fix is shown below and thus env_re_str is useless.

        raw_values_1 = [[item.split(':')[0].replace('Tag', '')]+[x for x in item.split(':')[1:] if x != ''] for item in profile_out_1.split() if 'Tag' in item]

        if self.DEBUG:
            print(datetime.now().strftime("%d/%m/%Y %H:%M:%S"), f">>length of raw_values: {len(raw_values_1)}", flush=True)
        # construct tags
        self.alive_tags = []
        # get values and check stability with raw_values_1
        checked_tag_id = [] # all tag_id that have been checked. A tag's env is not stable if it has never been checked.
        for i in range(len(raw_values_1)):
            tag_info = raw_values_1[i]
            curr_tag_id = int(tag_info[0])
            curr_num_env = len(tag_info) - 2
            curr_tag_var_value = int(tag_info[1])
            curr_tag_env_value_list = [] if curr_num_env == 0 else list(map(int, tag_info[2:]))
            # Test the stability of the tag_var
            if hasattr(self.tags[curr_tag_id].tag_var, "var_value"):
                if curr_tag_var_value != self.tags[curr_tag_id].tag_var.var_value:
                    self.tags[curr_tag_id].tag_var.is_stable = False
            else:
                self.tags[curr_tag_id].tag_var.var_value = curr_tag_var_value
            if curr_tag_var_value == INVALID_TAG_VALUE: # invalid tag value because of null pointer. should only in env vars
                self.tags[curr_tag_id].tag_var.is_stable = False
            # Test the stability of each env var
            for env_i in range(curr_num_env):
                if hasattr(self.tags[curr_tag_id].tag_envs[env_i], "var_value"):
                    if curr_tag_env_value_list[env_i] != self.tags[curr_tag_id].tag_envs[env_i].var_value:
                        self.tags[curr_tag_id].tag_envs[env_i].is_stable = False
                    checked_tag_id.append(curr_tag_id) # if we are not assigning the value for the first time, the value is now checked.
                else:
                    self.tags[curr_tag_id].tag_envs[env_i].var_value =curr_tag_env_value_list[env_i]
                if curr_tag_env_value_list[env_i] == INVALID_TAG_VALUE: # invalid tag value because of null pointer. should only in env vars
                    self.tags[curr_tag_id].tag_envs[env_i].is_stable = False
            if curr_tag_id not in self.alive_tags:
                self.alive_tags.append(curr_tag_id)
        # all tag_id that have been checked. A tag's env is not stable if it has never been checked.
        for tag_id in self.alive_tags:
            if tag_id not in checked_tag_id:
                for env_i in range(len(self.tags[tag_id].tag_envs)):
                    self.tags[tag_id].tag_envs[env_i].is_stable = False


    def remove_valuetag(self):
        """
        Remove a ValueTag from source file
        """
        for tag_id in self.tags:
            self.src = self.src.replace(f"#define Tag{tag_id}(x) (x)\n", "")
            if self.tags[tag_id].is_statement:
                self.src = self.src.replace(self.tags[tag_id].tag_str, '')
            else:
                self.src =self.src.replace(self.tags[tag_id].tag_str, self.tags[tag_id].tag_var.var_name)
            for tag_check_str in self.tags[tag_id].tag_check_strs:
                self.src = self.src.replace(tag_check_str, '')
        self.src = re.sub(r'[\w|_|\s|*]+ Tag\d+\(.*\)\{.*\}\n', '', self.src)
    
    def ignore_typedef(self, _typedef:str) -> bool:
        ignored_typedef = [
            "int8_t", "uint8_t", "int16_t", "uint16_t", "int32_t", "uint32_t", "int64_t", "uint64_t", "char"
        ]
        for ignored in ignored_typedef:
            if f'{ignored};' in _typedef:
                return True
        return False

    def insert_func_decl(self, func_id_list):
        # locate the last header include
        headers = re.findall(r'(#include.*)', self.src_syn)
        if len(headers) == 0:
            header_end_loc = 0
        else:
            header_end_loc = self.src_syn.index(headers[-1]) + len(headers[-1])
        # insert the function declaration 
        for func_id in list(set(func_id_list)):
            for misc in self.functionDB[func_id].misc:
                if not self.ignore_typedef(misc):
                    misc = "\n" + misc + "\n"
                    self.src_syn = self.src_syn[:header_end_loc] + misc + self.src_syn[header_end_loc:]
                    header_end_loc += len(misc)

            function_body = self.functionDB[func_id].function_body
            #FIXME: the added attribute may be incompatible with existing function attributes from the database. Can use this feature again if attributes are removed from the database.
            # prob_attr = random.randint(0, 100-1)
            # if prob_attr > 50:
            #     function_body = "inline __attribute__((always_inline))\n" + function_body
            function_body = "\n" + function_body + "\n"
            self.src_syn = self.src_syn[:header_end_loc] + function_body + self.src_syn[header_end_loc:]
            header_end_loc += len(function_body)
        
    def synthesize_input(self, env_vars:list[Var], func_inp_list:list[str], func_inp_types:list[VarType]):
        """Synthesize input to the target function call with environmental variables"""
        new_inp_list = []
        for inp_i in range(len(func_inp_list)):
            inp_value = int(func_inp_list[inp_i])
            if len(env_vars) > 0:
                env = random.choice(env_vars)
                env_value_cast = VarType.get_ctypes(func_inp_types[inp_i], env.var_value).value
                if abs(env_value_cast) > MAX_CONST_CCOMP:
                    new_inp_list.append(f"{inp_value}")
                else:
                    new_inp_list.append(f"({VarType.to_str(func_inp_types[inp_i])})({env.var_name})+({inp_value - env_value_cast})")
            else:
                new_inp_list.append(f"{inp_value}")
        return new_inp_list

    def synthesize_output(self, env_vars:list[Var], func_out, func_return_type:VarType):
        """Synthesize output to make sure the function return a value in a reasonable range"""
        ret_val_min, ret_val_max = VarType.get_range(func_return_type) # the range of the return value
        func_return_type = VarType.get_base_type(func_return_type) #FIXME: This is a bug in generating proxy functions where we did not convert the proxy return type. This has been fixed in proxy.py but need to regenerate function datebase to get rid of this work-around
        func_out = int(func_out)
        output_str = ""
        output = func_out
        # if func_out already exceeds the range limit
        if not (ret_val_min <= func_out <= ret_val_max):
            output_str += f'-({func_out})'
            output = 0
        for env in env_vars:
            env_value_cast = VarType.get_ctypes(func_return_type, env.var_value).value
            if abs(env_value_cast) > MAX_CONST_CCOMP or abs(env_value_cast+output) > MAX_CONST_CCOMP:
                continue
            if ret_val_min <= env_value_cast+output <= ret_val_max:
                output_str += f'+({VarType.to_str(func_return_type)})({env.var_name})'
                output += env_value_cast
            else:
                output_str += f'+(({VarType.to_str(func_return_type)})({env.var_name})-({env_value_cast}))'
        return output_str, output

    def replace_valuetag_with_func(self, tag_id:int, tgt_func_idx:int):
        """
        Replace a ValueTag with the selected function call
        """
        # use stable tag_var and env_vars for synthesis
        stable_env_vars = []
        if self.tags[tag_id].tag_var.is_stable:
            stable_env_vars.append(self.tags[tag_id].tag_var)
        for env in self.tags[tag_id].tag_envs:
            if env.is_stable:
                stable_env_vars.append(env)

        # randomly select an io pair of the tgt_func
        func_inp_list, func_out = random.choice(self.functionDB[tgt_func_idx].io_list)
        new_input_str = self.synthesize_input(stable_env_vars, func_inp_list, self.functionDB[tgt_func_idx].args_type)
        new_output_str, new_output = self.synthesize_output(stable_env_vars, func_out, self.functionDB[tgt_func_idx].return_type)
        
        # synthesize func_call for expr, make sure to restore the value of the expr
        if not self.tags[tag_id].is_statement:
            func_call = "(({tag_type})({call_name}({input}){output})+{tag_var_value})".format(
                tag_type=self.tags[tag_id].tag_var.var_type, 
                call_name=self.functionDB[tgt_func_idx].call_name, 
                input=", ".join(new_input_str), 
                output=f"{new_output_str}-({new_output})",
                tag_var_value=self.tags[tag_id].tag_var.var_name,
            )
        # for statement tag, we also want to assign the function call to a stable env variable
        else:
            func_call = "({call_name}({input}){output})".format(
                call_name=self.functionDB[tgt_func_idx].call_name, 
                input=",".join(new_input_str), 
                output=new_output_str
            )
            restore_env = None
            if not self.tags[tag_id].tag_var.is_constant:
                restore_env = self.tags[tag_id].tag_var
            elif len(stable_env_vars) > 0:
                restore_env = random.choice(stable_env_vars)
            if restore_env is not None and not restore_env.is_constant:
                func_call = f'{restore_env.var_name} = ({restore_env.var_type})({func_call}-({new_output}))+({restore_env.var_value});'

        # insert the function call
        self.src_syn = self.src_syn.replace(self.tags[tag_id].tag_str, f'/*TAG{tag_id}:STA*/' + func_call + f'/*TAG{tag_id}:END:{self.tags[tag_id].tag_var.var_name}*/')


    def synthesizer(self, src_filename:str, num_mutant:int=1, DEBUG:bool=False):
        """
        Synthesize a source file by replacing variables/constants with function calls.
        """
        self.tags = {} # all tags information
        self.vars = {} # all variale information
        self.tag_id_list = [] # tag_id in a sequential order as appeared in the execution
        self.scope_up = {} # key:val ==> child_scope:parent_scope
        self.scope_down = {} # key:[val] ==> parent_scope:[child_scope(s)]
        self.alive_tags = [] # all alive tag id

        self.DEBUG = DEBUG
        assert num_mutant >= 1
        # backup src file
        tmp_f = tempfile.NamedTemporaryFile(suffix=".c", delete=False)
        tmp_f.close
        shutil.copy(src_filename, tmp_f.name)
        # insert ValueTag
        if self.DEBUG:
            print(datetime.now().strftime("%d/%m/%Y %H:%M:%S"), ">profiling start", flush=True)
        self.profiling(tmp_f.name)
        if self.DEBUG:
            print(datetime.now().strftime("%d/%m/%Y %H:%M:%S"), ">profiling end", flush=True)
        with open(tmp_f.name, "r") as f:
            self.src_orig = f.read()
        os.remove(tmp_f.name)
        # sythesis
        all_syn_files = []
        if len(self.alive_tags) == 0:
            return all_syn_files
        for num_i in range(num_mutant):
            if self.DEBUG:
                print(datetime.now().strftime("%d/%m/%Y %H:%M:%S"), ">synthesize mutatant start", num_i, flush=True)
            self.src = copy(self.src_orig)
            self.src_syn = copy(self.src_syn_orig)
            replaced_valuetag = []
            inserted_func_ids = []
            for tag_id in self.alive_tags:
                # randomly decide if we want to replace this value
                if tag_id in replaced_valuetag or random.randint(0, 100) > self.prob:
                    continue #skip this value
                # randomly select a function from database
                while True:
                    tgt_func_idx = random.randint(0, len(self.functionDB)-1)
                    if self.functionDB[tgt_func_idx].has_io:
                        break
                # replace the ValueTag with the selected function
                self.replace_valuetag_with_func(tag_id, tgt_func_idx)
                replaced_valuetag.append(tag_id)
                inserted_func_ids.append(tgt_func_idx)
            # self.remove_valuetag() # we don't do this now because this removal is too costly and it has no impact on the semantics of the synthesized program.
            self.insert_func_decl(inserted_func_ids)
            dst_filename = f'{os.path.splitext(src_filename)[0]}_syn{num_i}.c'
            with open(dst_filename, "w") as f:
                f.write(self.src_syn)
            all_syn_files.append(dst_filename)
            if self.DEBUG:
                print(datetime.now().strftime("%d/%m/%Y %H:%M:%S"), ">synthesize mutatant end", num_i, flush=True)

        return all_syn_files


class SynthesizerError(Exception):
    pass


if __name__=='__main__':

    parser = argparse.ArgumentParser(description='Synthesize a new program based on a seed program and a function database.')
    parser.add_argument('--src', dest='SRC', required=True, help='path to the seed program.')
    parser.add_argument('--dst', dest='DST', required=True, help='path to the destination program.')
    parser.add_argument('--db', dest='DB', required=True, help='path to the function database json file.')
    args = parser.parse_args()
    if not os.path.exists(args.SRC):
        print(f"File {args.SRC} does not exist!")
        parser.print_help()
        exit(1)
    if not os.path.exists(args.DB):
        print(f"File {args.DB} does not exist!")
        parser.print_help()
        exit(1)

    syner = Synthesizer(args.DB, prob=100)
    try:
        all_syn_files = syner.synthesizer(args.SRC, num_mutant=1)
    except SynthesizerError:
        print("SynthesizerError (OK).")
