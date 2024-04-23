#### Function filter

This tool checks all defined functions in an input file and prints the names of
these with the following properties:

- All arguments are of type `int`
- The return value is of type `int`
- All references variables are locals
- No other functions are called

#### Prerequisites

LLVM, clang, cmake, parallel, ninja


#### Build

```
make build
cd build
cmake .. -G Ninja
ninja
```

### Run

```
./build/bin/function-filter input_file.c --
```
The output is of the form:
```
File:/path/to/input/file Function:function
```

`./find_functions.sh dir` will filter all functions in files under `dir`
