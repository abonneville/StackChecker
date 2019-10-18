# Stack Checker
Goal is to implement a call graph that can compute stack usage for both C and C++ embedded projects. 

# Dependencies:
* Python 3.6 or later (due to pathlib)
* Embedded GCC compiler targeting ARM cores for the *.elf binary file. Currently using with Atollic v9.2.0 

## Features:
* C / C++ direct calls to methods are mapped.
* Assembly direct calls to methods are mapped.
* Direct and indirect recursion detection & reporting completed.
* Basic viewer implemented, provides tree navigation.
* Indirect calls (vtable, function pointers) partially working. This is the area I am currently working.


## Quick Start:
Call graph is generated from the binary *.elf file. Follow these steps:
* Write a configuration file that captures command line parameters, example contents (config.txt):
  - --infile=MyApplication.elf
  - --tool_objdump=C:\Program Files (x86)\Atollic\TrueSTUDIO for STM32 9.2.0\ARMTools\bin\arm-atollic-eabi-objdump.exe
  - --vector=g_pfnVectors
* Start the analysis with "python stack_checker.py @config.txt"
* Terminal window will display progress:
Generating node list...done.
Generating call graph...done.
Launching viewer...
* Be patient. Depending on the size of your call graph the viewer can take several minutes to load.

## Unfinished:
* The challenge remains how to clearly display indirect calls inside the viewer.
* Calculate stack usage.
* Viewer needs filter and search capability to enhance navigation
* Implement multi-processor support to accelerate viewer loading. By default, python enforces single thread execution...GIL

