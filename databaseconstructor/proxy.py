import os, string
from copy import deepcopy
from variable import *
from functioner import *


def generate_random_string(len:int=5) -> str:
    """Generate a random string of length len"""
    return ''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for _ in range(len))

def generate_proxy_function(input_func:Function, synthesized_input:list[str], expose_pointer:bool=False) -> str:
    """
    Synthesize a proxy function for a function.
    When there are unsupported types in func_arg_tpyes such as pointers and structs,
    proxy function can make these types transparent to invokers.
    Args:
    input_func: the input function of type Function
    synthesized_input: the input list
    expose_pointer: whether to keep pointers in the parameters of proxy function
    """
    # no need for a proxy function if all input args and return are base type.
    need_proxy = False
    for input_arg_type in input_func.args_type:
        if input_arg_type != VarType.get_base_type(input_arg_type):
            need_proxy = True
            break
    if input_func.return_type != VarType.get_base_type(input_func.return_type):
        need_proxy = True
    if not need_proxy:
        return Function({})
    
    if expose_pointer:
        return generate_proxy_function_expose_pointer(input_func, synthesized_input)
    
    return generate_proxy_function_hide_pointer(input_func, synthesized_input)

def generate_proxy_function_hide_pointer(input_func:Function, synthesized_input:list[str]) -> str:
    # proxy function name
    proxy_function_name = f"realsmith_proxy_{generate_random_string(5)}"
    proxy_args_var = [f"p_{idx}_{generate_random_string(5)}" for idx in range(len(input_func.args_type))]
    
    proxy_args_type = []
    for input_arg_type in input_func.args_type:
        # use base type of the original type if it is a base type or a pointer of base type
        if not VarType.is_unsupport_type(input_arg_type):
            proxy_args_type.append(VarType.get_base_type(input_arg_type))
        # use a random type otherwise
        else:
            raise ValueError(f"Not supported yet {VarType.to_str(input_arg_type)}")
    proxy_args_str = ", ".join([f"{VarType.to_str(proxy_args_type[idx])} {proxy_args_var[idx]}" if proxy_args_type[idx] != VarType.VOID else "" for idx in range(len(proxy_args_var))])
    
    pre_call_to_input_func = []
    call_args_to_input_func = []
    post_call_to_input_func = []

    for idx in range(len(input_func.args_type)):
        # we do not need to call to function with void parameter.
        if proxy_args_type[idx] == VarType.VOID:
            continue
        #  base type or a pointer of base type
        if proxy_args_type[idx] == input_func.args_type[idx]:
            call_args_to_input_func.append(proxy_args_var[idx])
        # pointer
        elif proxy_args_type[idx] == VarType.get_base_type(input_func.args_type[idx]):
            proxy_args_idx_base_type = VarType.get_base_type(proxy_args_type[idx])
            match random.choice(['pointer', 'array']):
                case 'pointer':
                    # call arg
                    call_args_to_input_func.append(f"&({proxy_args_var[idx]})")
                case 'array':
                    proxy_var_arr = f"proxy_{generate_random_string(5)}"
                    # randomly decide arrat length, use [10, 20)
                    arr_len = random.randint(10, 20)
                    # initialize array
                    arr_values = []
                    for _ in range(arr_len):
                        arr_values.append(random.choice([f"{proxy_args_var[idx]}", str(VarType.get_random_value(proxy_args_idx_base_type))]))
                    arr_init = ', '.join(arr_values)
                    pre_call_to_input_func.append(f"{VarType.to_str(proxy_args_idx_base_type)} {proxy_var_arr}[{arr_len}] = {{ {arr_init} }};")
                    # call arg
                    call_args_to_input_func.append(proxy_var_arr)
        # unusual types such as pointer
        else:
            raise VarType(f"(TODO) Unsupported type, maybe a struct.")

    proxy_function_body = f"{VarType.to_str(VarType.get_base_type(input_func.return_type))} {proxy_function_name}({proxy_args_str}) {{\n"

    # pre call
    for pre_call in pre_call_to_input_func:
        proxy_function_body += f"{pre_call}\n"
    # call
    proxy_ret_var = f"proxy_ret_{generate_random_string(5)}"
    proxy_ret_type = input_func.return_type
    call_args_str = ', '.join(call_args_to_input_func)
    proxy_function_body += f"{VarType.to_str(proxy_ret_type)} {proxy_ret_var} = {input_func.call_name}({call_args_str});\n"
    # post call
    for post_call in post_call_to_input_func:
        proxy_function_body += f"{post_call}\n"
    # return
    if proxy_ret_type == VarType.get_base_type(proxy_ret_type):
        proxy_function_body += f"return {proxy_ret_var};\n"
    else:
        proxy_function_body += f"return *{proxy_ret_var};\n"
    proxy_ret_type = VarType.get_base_type(proxy_ret_type)

    proxy_function_body += "}\n"

    proxy_function = {
        "function_name": proxy_function_name,
        "parameter_types":  proxy_args_type,
        "return_type": proxy_ret_type,
        "function": proxy_function_body
    }

    return Function(proxy_function)


def generate_proxy_function_expose_pointer(input_func:Function, synthesized_input:list[str]) -> str:
    # proxy function name
    proxy_function_name = f"realsmith_proxy_{generate_random_string(5)}"
    proxy_args_var = [f"p_{idx}_{generate_random_string(5)}" for idx in range(len(input_func.args_type))]
    
    proxy_args_type = []
    for input_arg_type in input_func.args_type:
        # use original type if it is a base type or a pointer of base type
        if not VarType.is_unsupport_type(input_arg_type):
            proxy_args_type.append(input_arg_type)
        # use a random type otherwise
        else:
            proxy_args_type.append(VarType.get_random_type())
    proxy_args_str = ", ".join([f"{VarType.to_str(proxy_args_type[idx])} {proxy_args_var[idx]}" for idx in range(len(proxy_args_var))])
    
    pre_call_to_input_func = []
    call_args_to_input_func = []
    post_call_to_input_func = []

    for idx in range(len(input_func.args_type)):
        #  base type or a pointer of base type
        if proxy_args_type[idx] == input_func.args_type[idx]:
            # base type
            if proxy_args_type[idx] == VarType.get_base_type(proxy_args_type[idx]):
                call_args_to_input_func.append(proxy_args_var[idx])
            # pointer
            else:
                proxy_args_idx_base_type = VarType.get_base_type(proxy_args_type[idx])
                proxy_var = f"proxy_{generate_random_string(5)}"
                # save original pointed-to value
                pre_call_to_input_func.append(f"{VarType.to_str(proxy_args_idx_base_type)} {proxy_var} = *{proxy_args_var[idx]};")
                # mutate original value
                pre_call_to_input_func.append(f"*{proxy_args_var[idx]} = {synthesized_input[idx]};")
                match random.choice(['pointer', 'array']):
                    case 'pointer':
                        # call arg
                        call_args_to_input_func.append(proxy_args_var[idx])
                    case 'array':
                        proxy_var_arr = f"proxy_{generate_random_string(5)}"
                        # randomly decide arrat length, use [10, 20)
                        arr_len = random.randint(10, 20)
                        # initialize array
                        arr_values = []
                        for _ in range(arr_len):
                            arr_values.append(random.choice([f"*{proxy_args_var[idx]}", str(VarType.get_random_value(proxy_args_idx_base_type))]))
                        arr_init = ', '.join(arr_values)
                        pre_call_to_input_func.append(f"{VarType.to_str(proxy_args_idx_base_type)} {proxy_var_arr}[{arr_len}] = {{ {arr_init} }};")
                        # call arg
                        call_args_to_input_func.append(proxy_var_arr)
                # recover original pointed-to value
                post_call_to_input_func.append(f"*{proxy_args_var[idx]} = {proxy_var};")
        # unusual types such as pointer
        else:
            raise VarType(f"(TODO) Unsupported type, maybe a struct.")

    proxy_function_body = f"{VarType.to_str(VarType.get_base_type(input_func.return_type))} {proxy_function_name}({proxy_args_str}) {{\n"

    # pre call
    for pre_call in pre_call_to_input_func:
        proxy_function_body += f"{pre_call}\n"
    # call
    proxy_ret_var = f"proxy_ret_{generate_random_string(5)}"
    proxy_ret_type = input_func.return_type
    call_args_str = ', '.join(call_args_to_input_func)
    proxy_function_body += f"{VarType.to_str(proxy_ret_type)} {proxy_ret_var} = {input_func.call_name}({call_args_str});\n"
    # post call
    for post_call in post_call_to_input_func:
        proxy_function_body += f"{post_call}\n"
    # return
    if proxy_ret_type == VarType.get_base_type(proxy_ret_type):
        proxy_function_body += f"return {proxy_ret_var};\n"
    else:
        proxy_function_body += f"return *{proxy_ret_var};\n"

    proxy_function_body += "}\n"

    proxy_function = {
        "function_name": proxy_function_name,
        "parameter_types":  proxy_args_type,
        "return_type": proxy_ret_type,
        "function": proxy_function_body
    }

    return Function(proxy_function)

DRIVER_FUNC = """
#include <stdio.h>

RealSmith_MISC_PLACEHOLDER

RealSmith_FUNCTION_PLACEHOLDER

PROXY_FUNCTION_PLACEHOLDER

int main() {

    PRE_CALL_PLACEHOLDER

    long long ret = FUNCTION_CALL_PLACEHOLDER(CALL_ARGS);

    POST_CALL_PLACEHOLDER

    printf(\"ret=%lld\", ret); 
    return 0;
}
"""

def generate_closure_program(proxy_function:Function, input_function:Function, synthesized_intput:list[str]) -> tuple[str, Function]:
    synthesized_intput = deepcopy(synthesized_intput)
    RealSmith_MISC_PLACEHOLDER = '\n'.join(input_function.misc)
    RealSmith_FUNCTION_PLACEHOLDER = input_function.function_body
    if proxy_function.function_body == '':
        PROXY_FUNCTION_PLACEHOLDER = ""
        FUNCTION_CALL_PLACEHOLDER = input_function.call_name
    else:
        PROXY_FUNCTION_PLACEHOLDER = proxy_function.function_body
        FUNCTION_CALL_PLACEHOLDER = proxy_function.call_name

    PRE_CALL_PLACEHOLDER = ""
    pre_call_list = []
    for idx in range(len(proxy_function.args_type)):
        arg_type = proxy_function.args_type[idx]
        if arg_type != VarType.get_base_type(arg_type):
            arg_var_base = f"arg_{generate_random_string(5)}"
            arg_var = f"arg_{generate_random_string(5)}"
            arg_var_value = VarType.get_random_value(VarType.get_base_type(arg_type))
            pre_call_list.append(f"{VarType.to_str(VarType.get_base_type(arg_type))} {arg_var_base} = {arg_var_value}; {VarType.to_str(arg_type)} {arg_var} = &{arg_var_base};")
            synthesized_intput[idx] = arg_var
    PRE_CALL_PLACEHOLDER += "\n".join(pre_call_list)

    CALL_ARGS = ", ".join(list(map(str, synthesized_intput)))

    POST_CALL_PLACEHOLDER = ""
    # construct the program
    closure_program = DRIVER_FUNC\
        .replace(
        "RealSmith_MISC_PLACEHOLDER", RealSmith_MISC_PLACEHOLDER)\
        .replace(
        "RealSmith_FUNCTION_PLACEHOLDER", RealSmith_FUNCTION_PLACEHOLDER)\
        .replace(
        "PROXY_FUNCTION_PLACEHOLDER", PROXY_FUNCTION_PLACEHOLDER)\
        .replace(
        "PRE_CALL_PLACEHOLDER", PRE_CALL_PLACEHOLDER)\
        .replace(
        "FUNCTION_CALL_PLACEHOLDER", FUNCTION_CALL_PLACEHOLDER)\
        .replace(
        "CALL_ARGS", CALL_ARGS)\
        .replace(
        "POST_CALL_PLACEHOLDER", POST_CALL_PLACEHOLDER)
    
    if proxy_function.function_body != '':
        proxy_function.function_body = f"{input_function.function_body}\n{proxy_function.function_body}"
        proxy_function.misc = input_function.misc
        new_function = proxy_function
    else:
        new_function = input_function
    return closure_program, new_function
