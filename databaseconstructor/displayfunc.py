#!/usr/bin/env python3
import io, json, random, sys
from pygments import highlight
from pygments.lexers import CppLexer, PythonLexer
from pygments.formatters import TerminalFormatter
from functioner import *

if len(sys.argv) < 2 or not os.path.exists(sys.argv[1]):
    raise ValueError("Please input the function database json file and make sure it exist.")

functiondb = FunctionDB(sys.argv[1])

while True:
    rand_id = random.randint(0, len(functiondb)-1)
    # if functiondb[rand_id].has_io:
    break

# display_message = highlight(functiondb[rand_id].function_body, PythonLexer(), TerminalFormatter())
io_str = ''
# for each_io in functiondb[rand_id].io_list:
#     inp = each_io[0]
#     out = each_io[1]
#     io_str += f"input: {inp}\noutput: {out}\n"
display_message = f"{functiondb[rand_id].function_body}\n\n/*\n{io_str}*/"
print(display_message)
