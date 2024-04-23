import os, json
from typing import Optional
from variable import *


class Function:
    """A container for a function
    """
    call_name = ''
    args_type = ''
    return_type = ''
    function_body = ''
    io_list = []
    misc = []
    src_file = ''
    include_headers = []
    include_sources = []
    is_valid:bool = False
    has_io:bool = False
    load_from_file:bool = False
    def __init__(self, func_json:dict) -> None:
        if 'function_name' in func_json:
            self.call_name = func_json['function_name']
        else:
            return
        if 'parameter_types' in func_json:
            self.args_type = VarType.from_list(func_json['parameter_types'])
        else:
            return
        if 'return_type' in func_json:
            if isinstance(func_json['return_type'], VarType):
                self.return_type = func_json['return_type']
            else:
                self.return_type = VarType.from_str(func_json['return_type'])
        else:
            return
        if 'function' in func_json:
            self.function_body = func_json['function']
        else:
            return
        # no io_list is fine as we may add it later
        if 'io_list' in func_json:
            self.set_io(func_json['io_list'])
        self.is_valid = True
        if 'misc' in func_json:
            self.misc = func_json['misc']
        if 'src_file' in func_json:
            self.src_file = func_json['src_file']
            self.load_from_file = True
        if 'include_headers' in func_json:
            self.include_headers = func_json['include_headers']
        if 'include_sources' in func_json:
            self.include_sources = func_json['include_sources']
    
    def to_json(self):
        out_str = {
            "function_name": self.call_name,
            "parameter_types": [VarType.to_str(t) for t in self.args_type],
            "return_type": VarType.to_str(self.return_type),
            "function": self.function_body,
            "io_list": self.io_list,
            "misc": self.misc,
            "src_file": self.src_file,
            "include_headers": self.include_headers,
            "include_sources": self.include_sources
        }
        return out_str
    
    def set_io(self, io_list:list) -> None:
        self.io_list = io_list
        self.has_io = True if len(io_list) > 0 else False
        self.num_io = len(io_list)
    
    def get_random_io(self):
        return random.choice(self.io_list)


class FunctionDB:
    """A database class that contains a set of Function()
    """
    def __init__(self, func_db_file:Optional[str]=None) -> None:
        self.all_functions = []
        if func_db_file is None:
            return
        if not os.path.exists(func_db_file):
            ValueError(f"{func_db_file} does not exist!")
        with open(func_db_file, 'r') as f:
            raw_function_db = json.loads(f.read())
        for func_json in raw_function_db:
            func = Function(func_json)
            if func.is_valid:
                self.all_functions.append(func)
    
    def from_list(self, function_list:list[Function])->None:
        for function in function_list:
            assert isinstance(function, Function)
        self.all_functions = function_list

    def __len__(self):
        return len(self.all_functions)

    def __iter__(self):
        self.curr = 0
        return self
    
    def __next__(self):
        if self.curr < len(self):
            self.curr += 1
            return self.all_functions[self.curr-1]
        else:
            raise StopIteration
    
    def __getitem__(self, i):
        return self.all_functions[i]
    
    def to_json(self):
        return [func.to_json() for func in self]
    
    def append(self, function:Function):
        assert isinstance(function, Function)
        self.all_functions.append(function)
