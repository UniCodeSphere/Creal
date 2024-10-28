# Creal

This is the tool for our PLDI 2024 paper "*Boosting Compiler Testing by Injecting Real-World Code*". The code and data is also available in our [artifact](https://doi.org/10.5281/zenodo.10951313).

**Creal** is an automated program generator for C. Given a valid C program as the seed, Creal can inject new functions into it and produce new valid programs. By default, Creal uses [Csmith](https://github.com/csmith-project/csmith) to produce seed programs.

## Structure of the project

```
  |-- creal.py                # The default script for applying Creal on Csmith
  |-- generate_mutants.py     # The script for applying Creal on a given seed program
  |-- generate_csmith_seed.py # An auxilary script for generating Csmith programs
  |-- synthesizer             # The synthesizer implementation directory
  |   |-- synthesizer.py      # The synthesizer implementation of Creal
  |-- profiler                # Profiling tools
  |   |-- src                 # The code for the profiler
  |   |-- build               # The compiled profiler(./build/bin/profile) used by synthesizer.py
  |-- databaseconstructor     # Constructing function database
  |   |-- functionextractor
  |   |   |-- extractor.py    # For extracting valid functions from a C/C++ project
  |   |-- generate.py         # For generating IO for functions
```


## Use Creal

**Step 1: Install necessary packages**
- **Python** >= 3.10
- **Csmith** (Please install it following [Csmith](https://github.com/csmith-project/csmith))
- **CSMITH_HOME**: After installing Csmith, please set the environment variable `CSMITH_HOME` to the installation path, with which we can locate `$CSMITH_HOME/include/csmith.h`.
- **CompCert** (Please install it following [CompCert](https://compcert.org/man/manual002.html#install))
- **clang** >= 14, **libclang-dev**
- **diopter** == 0.0.24 (`pip install diopter==0.0.24`)
- **termcolor** (`pip install termcolor`)

**Step 2: Compile the profiler**
```shell
$ cd profiler
$ mkdir build
$ cd build
$ cmake ..
$ make
```

**Step 3: Use Creal**
To generate new programs from Csmith programs, run
```shell
./creal.py --dst ./tmp --syn-prob 20 --num-mutants 5
```
This script will first invoke Csmith to generate a seed program and then generate mutated programs.
The used function database is `databaseconstructor/functions_pointer_global_io.json`.
The seed program will be saved in the directory specified by ``"--dst"``, which is ``"./tmp"`` in the command above.
Parameter explanation:
- `--dst`: path to the directory where programs will be saved.
- `--syn-prob`: synthesis probabiliy (0~100).
- `--num-mutants`: number of mutants per seed.


## More

### Run Creal on a given seed program
We also provide a script for generating new programs by mutating a given seed program.
Note that the given program should satisfy the following requirements:

- It is executable, i.e., contains a main function.

- It has at least another function with some statements and this function is reachable from the main function.

- It returns 0, i.e., normal exit.

For example, the following is a valid seed program:

```C

  int foo(int x) {
    int a = 0;
    a = a + x;
    return a;
  }
  int main(){
    foo(1);
    return 0;
  }
```
Suppose you save this program as `a.c`.
You can invoke Creal on this program by running

```shell
  $ ./generate_mutants.py --seed /path/to/a.c --dst ./tmp --syn-prob 20 --num-mutants 5
```

### Build new function database

All the 50K functions used by ``creal.py`` and ``generate_mutants.py`` are available at ``databaseconstructor/functions_pointer_global_io.json``.

You can generate a new function database as follows:

**Step 0**, build the function extractor

```shell
  $ cd ./databaseconstructor/functionextractor/
  $ mkdir build && cd build
  $ cmake .. && make
```

**Step 1**, prepare a C/C++ project and extract all valid functions from it by running:

```shell
  $ cd ./databaseconstructor/functionextractor/
  $ ./extract.py --src /path/to/your/project --dst functions.json --cpu 10
```
Parameters:
- ``--src``: path to the prepared C/C++ project.
- ``--dst``: the extracted functions will be saved in the specified json files

**Step 2**, generate IO for the extracted functions by running:

```shell
  $ cd ./databaseconstructor/
  $ ./generate.py --src /path/to/functions.json --dst functions_io.json --num 5 --cpu 10
```
Parameters:
- ``--src``: the extracted functions.json
- ``--dst``: the new functions_io.json with generated IO pairs
- ``--num``: number of IO for each function

**Step 3**, after generating the new function database (``functions_io.json``), you can modify ``creal.py`` or ``generate_mutants.py`` to change the path t
o the function database by modifying the value ``FUNCTION_DB_FILE``.

**Step 4**, now you can following the above guidelines to use Creal on the new function database.
