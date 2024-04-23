import re
from shutil import which
from pathlib import Path
from diopter.compiler import (
    CompilationSetting,
    CompilerExe,
    CompilerProject,
    ExeCompilationOutput,
    OptLevel,
    SourceProgram,
    Language
)
from diopter.sanitizer import Sanitizer
from variable import *
from functioner import *
from proxy import generate_proxy_function, generate_closure_program


class IOGenerator():
    """An IO generator for a C function
    """
    def __init__(self) -> None:
        """Generate a valid input for the input function and return its IO pair
        Args:
            input_func (Function): the input function
            max_try_time (int): the max number of times we try to find a valid input
        """
        self.compilers = []
        for opt in ['O0', 'O1', 'O2', 'O3', 'Os']:
            self.compilers.append(
                CompilationSetting(
                    compiler=CompilerExe.get_system_gcc(),
                    opt_level=OptLevel.from_str(opt),
                    flags=("-march=native",),
                )
            )
            self.compilers.append(
                CompilationSetting(
                    compiler=CompilerExe.get_system_clang(),
                    opt_level=OptLevel.from_str(opt),
                    flags=("-march=native",),
                )
            )

        
        self.sanitizer = Sanitizer(use_ub_address_sanitizer=True, use_memory_sanitizer=True, use_ccomp_if_available=True)

        if which("typesanitizer") is None:
            raise ValueError("The compiler `typesanitizer` is not found in your path.")
        self.typesanitizer = CompilationSetting(
            compiler=CompilerExe(CompilerProject.LLVM, Path(which("typesanitizer")), "main"),
            opt_level=OptLevel.from_str("O0"),
            flags=("-march=native", "-fsanitize=type",),
        )

    def generate(self, input_func:Function, max_try_time:int=5, debug:bool=False) -> tuple[Optional[list], Optional[Function]]:
        """Generate a valid input for the input function and return its IO pair
        Args:
            input_func (Function): the input function
            max_try_time (int): the max number of times we try to find a valid input
        Return:
            None: failed to find a valid IO pair within max_try_time
            list: the [input, output] pair
        """
        try_time = 0
        # try with random input ranges
        while try_time < max_try_time:
            inp = self.get_input(input_func)
            try:
                out, new_func = self.synthesize_proxy(input_func, inp, debug)
                return [inp, out], new_func # succeeded to generate a valida IO pair
            except ValidateError:
                try_time += 1
        # try with a small input range
        try_time = 0
        while try_time < max_try_time:
            inp = self.get_input(input_func, given_min=-5, given_max=5)
            try:
                out, new_func = self.synthesize_proxy(input_func, inp)
                return [inp, out], new_func # succeeded to generate a valida IO pair
            except ValidateError:
                try_time += 1

        return None, None # failed to generate a valid IO pair

    def get_input(self, input_func:Function, to_string=False, given_min=None, given_max=None):
        """Randomly select a valid for each input arg
        """
        inp = []
        for arg_type in input_func.args_type:
            if arg_type == VarType.VOID:
                continue
            v = VarType.get_random_value(arg_type, given_min=given_min, given_max=given_max)
            if to_string and type(v) is str:
                v = f'"{v}"'
            else:
                v = str(v)
            inp.append(v)
        return inp
    
    def parse_output(self, out:str) -> Optional[str]:
        res = re.findall(r'ret=(.*)', out.strip())
        if len(res) == 0:
            return None
        return res[0]

    def compile_and_run(self, compiler:CompilationSetting, program:SourceProgram) -> str:
        """Compile and run the program
        """
        try:
            comp_out = compiler.compile_program(program, ExeCompilationOutput(), timeout=5)
        except:
            raise ValidateError
        try:
            out = comp_out.output.run(timeout=5)
        except:
            raise ValidateError
        out = comp_out.output.run(timeout=5)
        return self.parse_output(out.stdout)

    def check_type_sanitizer(self, program:SourceProgram) -> bool:
        """Validate if the program violates the strict aliasing rule
        """
        try:
            comp_out = self.typesanitizer.compile_program(program, ExeCompilationOutput(), timeout=5)
        except:
            return True
        try:
            out = comp_out.output.run(timeout=5)
        except:
            return False
        out = comp_out.output.run(timeout=5)
        if "TypeSanitizer" in out.stderr:
            return False
        return True

    def execute_program(self, src:str, debug:bool=False) -> str:
        """
        Validate if the function is valid under the given input; if yes, return the output
        """
        prog = SourceProgram(code=src, language=Language.C)
        sanitizer_ret = self.sanitizer.sanitize(prog)
        if not sanitizer_ret:
            raise ValidateError
        # verify with TypeSanitizer
        typesanitizer_ret = self.check_type_sanitizer(prog)
        if not typesanitizer_ret:
            raise ValidateError
        
        # verify consistent outputs from all compilers
        out_list = []
        for compiler in self.compilers:
            out = self.compile_and_run(compiler, prog)
            if out_list != []:
                if out_list[0] != out:
                    raise InconsistentOutputError
            out_list.append(out)
        if len(set(out_list)) != 1:
            raise InconsistentOutputError
        out = out_list[0]

        return out
    
    def synthesize_proxy(self, input_func:Function, inp:list[str], debug:bool=False) -> tuple[str, Function]:
        """
        Synthesize a proxy function if needed and generate output from the given input on the new proxy function.
        """
        # get the proxy function
        proxy_function = generate_proxy_function(input_func, inp)
        closure_program, new_input_function = generate_closure_program(proxy_function, input_func, inp)
        if debug:
            with open('debug.c', 'w') as f:
                f.write(closure_program)
        out = self.execute_program(closure_program, debug)
        return out, new_input_function


class ValidateError(Exception):
    """Validate failure
    """
    pass

class InconsistentOutputError(Exception):
    """The output across compilers is inconsistent
    This is a workaround for the strict aliasing issue
    """
    pass
