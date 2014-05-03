2048 AI
=======

An AI (artificial intelligence) for [2048][0], based on a simple maximization
algorithm.

To make that AI run, a 2048 engine has been built. Of the AI, there are two
versions, a C++ and a Python version.

Dependencies
------------

* python3 (≥ 3.3)
* python3-urwid

Compiling (the C++ AI)
----------------------

Run cmake:

    cmake .

Run make:

    make

Running
-------

To just play 2048 yourself:

    python3 -m g2048

To let the Python AI play a game:

    python3 -m g2048 --ai

To let the C++ AI play a game (requires that you have compiled the C++ AI
before):

    python3 -m g2048 --ai --ai-command ./2048++

   [0]: http://gabrielecirulli.github.io/2048/
