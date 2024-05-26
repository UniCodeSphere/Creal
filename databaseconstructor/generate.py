#!/usr/bin/env python3
import os, argparse, json, warnings
from pathlib import Path
from tqdm import tqdm
import multiprocessing as mp
from IOGenerator import *
from functioner import *

DEBUG = False

NUM_IO=5

def generate_io(input_func: Function)->Function:
    """Generate IO pairs
    Args:
        input_func (Function) : the input function
    """
    # remove inline keyword in input_func to avoid undefined reference to non-static inlined function
    if 'inline ' in input_func.function_body and 'static' not in input_func.function_body:
        input_func.function_body = input_func.function_body.replace('inline ', ' ')

    iogenerator = IOGenerator()
    io_list = []
    num_generated = 0
    new_func = None
    while num_generated < NUM_IO:
        try:
            io, generated_new_func = iogenerator.generate(input_func, debug=DEBUG)
        except InconsistentOutputError:
            # we probably meet a violation of strict aliasing
            new_func = None
            io_list = []
            break
        if io is not None and io not in io_list:
            io_list.append(io)
        if generated_new_func is not None:
            new_func = generated_new_func
        num_generated += 1
        if new_func is not None and 'realsmith_proxy' in new_func.function_body: # we do not support more than 1 NUM_IO for functions with proxy because each time we call iogenerator.generate(input_func), the proxy function would change.
            break
    if len(io_list) != 0:
        new_func.set_io(io_list)
        return new_func
    else:
        return None


if __name__=='__main__':

    parser = argparse.ArgumentParser(description='Generate IO pairs for funtioncs.')
    parser.add_argument('--src', dest='SRC', required=True, help='path to the source function_db_file.')
    parser.add_argument('--dst', dest='DST', required=True, help='path to the destination function_db_file with io.')
    parser.add_argument('--num', dest='NUM', default=5, type=int, help='number of io pairs generated for each function. (default=5)')
    parser.add_argument('--cpu', dest='CPU', default=-1, type=int, help='number of io pairs generated for each function. (default=#ALL_CPUs)')
    args = parser.parse_args()
    if not os.path.exists(args.SRC):
        print(f"File {args.SRC} does not exist!")
        parser.print_help()
        exit(1)
    NUM_IO = args.NUM
    
    # construct function database
    functiondb = FunctionDB(args.SRC)
    new_functiondb = FunctionDB()

    if DEBUG:
        for func in functiondb:
            new_func = generate_io(func)
            if new_func is not None:
                new_functiondb.append(new_func)
        with open(args.DST, "w") as f:
            json.dump(new_functiondb.to_json(), f)
        exit(0)

    # typesanitizer is used in IOGenerator.py
    if which('typesanitizer') is None:
        warnings.warn("The compiler `typesanitizer` is not found in your path and thus possible misaligned types could happen in programs.")

    cpu_count = mp.cpu_count()
    cpu_use = cpu_count if args.CPU == -1 else min(cpu_count, args.CPU)
    with tqdm(total=len(functiondb)) as pbar, mp.Pool(cpu_use) as pool:
        for idx, new_func in enumerate(pool.imap(generate_io, functiondb)):
            pbar.update()
            if new_func is not None:
                new_functiondb.append(new_func)
    
    with open(args.DST, "w") as f:
        json.dump(new_functiondb.to_json(), f)

