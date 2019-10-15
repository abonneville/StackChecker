# Stack Checker

Work in progress.
Overall goal is to implement a call graph that can compute stack usage for both C and C++ projects. 

## Features:
* C / C++ direct calls to methods are mapped.
* Assembly direct calls to methods are mapped.
* Indirect calls (vtable, function pointers) partially working. This is the area I am currently working.

Basic viewer implemented, provides tree navigation.

## References:
* [Function Pointer Analysis for C Programs](https://pdfs.semanticscholar.org/54a3/f70d7d19d8be034d796e32516927e7aaa995.pdf)


