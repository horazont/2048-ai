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
* python3-numpy

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

AI protocol
-----------

If you want to create a custom AI in a language of your choice, you can use this
engine and let your AI talk to the engine using the AI protocol.

The AI protocol is a simple binary protocol. The host engine sends the AI 17
unsigned bytes. The first 16 bytes are the game board, with the inner loop
iterating over the x axis and the outer loop over the y axis.

The seventh byte is an extension byte, which is zero for now. If it is nonzero,
you’re running in a future version of the engine host and should terminate now.

The AI then has to send back the action it wants to take. This is one unsigned
byte number, adhering to the following mapping:

    0 => move up
    1 => move down
    2 => move left
    3 => move right

Any other number will let the host engine ignore the request in this protocol
version. In a future version, a host engine might interpret different values
differently.

If the AI does not want to continue playing (e.g. because it doesn’t have any
options anymore), it should just exit after having received the board.

   [0]: http://gabrielecirulli.github.io/2048/
