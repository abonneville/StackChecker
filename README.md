# Stack Checker

Work in progress.
Overall goal is to implement a call graph that can compute stack usage for both C and C++ projects. 

## Features:
* C / C++ direct calls to methods are mapped.
* Assembly direct calls to methods are mapped.
* Indirect calls (vtable, function pointers) partially working. This is the area I am currently working.

Reporting and visulationization has not started. A *.json file is being generated now, but it captures the internal node list generated from an *.elf binary.

