#!/usr/bin/python3

import asyncio
import functools
import urwid
import sys

class AIProtocol(asyncio.Protocol):
    def __init__(self, loop):
        super().__init__()
        self.loop = loop

    def send_board(self, board):
        self.transport.write(board)

    def connection_made(self, transport):
        pass

    def data_received(self, data):
        self.loop.call_soon(asyncio.async, process_received(data))

    def eof_received(self):
        print("eof")

    def pause_writing(self):
        pass

    def resume_writing(self):
        pass

    def connection_lost(self, exc):
        pass

class UrwidWrapper:
    def __init__(self, loop, root, screen):
        self.loop = loop
        self.root = root
        self.screen = screen

    def __iter__(self):
        self.screen.start()
        try:
            for fd in self.screen.get_input_descriptors():
                self.loop.add_reader(fd, self._input_callback)

            while True:
                yield from asyncio.sleep(100)
        finally:
            self.screen.end()

    def _input_callback(self):
        keys = [key for _, key, _ in self.screen.get_input_nonblocking()]


@asyncio.coroutine
def main(args):
    global loop

    controller_coroutine = None
    if args.ai is not None:
        if not args.ai:
            pass
        else:
            pass
    else:
        controller_coroutine = None

    screen = urwid.raw_display.Screen()
    root_widget = urwid.Filler(
        urwid.Pile(
            [
                urwid.Padding(
                    urwid.BigText(
                        "foo",
                        urwid.font.HalfBlock5x4Font()),
                    width='clip')
            ]),
        valign="top")
    yield from iter(UrwidWrapper(loop, root_widget, screen))


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
USING AI COMMANDS

AI commands are executables whose standard input/output adheres to the
AI protocol. The host sends the AI command the whole game board, as
array with 16 bytes, each holding the logarithm to the base 2 of the
value shown on the board. The array is followed by a zero byte. This
byte is reserved for future extension. An AI command which receives a
non-zero byte here should assume that the host speaks a future version
of the protocol it cannot understand and thus terminate itself.

The AI command is supposed to send one byte back, which denotes the
move it wants to make. If no move is possible, the AI should terminate
itself with a return value of 0. The allowed values for the move byte
are:

  0 => move up
  1 => move down
  2 => move left
  3 => move right

After the move has been applied, the protocol starts from the
beginning.

VIEWING A GAME

If running with --listen, a client can connect. A freshly connected
client immediately receives the current board state and score. The
board state is, like in the AI protocol, sent as an array of
bytes. The score follows as an unsigned 32 bit integer in
little-endian byte order.

After the controller makes a turn, the new board is transmitted to all
clients in the same format as before.
"""
    )
    parser.add_argument(
        "--ai",
        dest="ai",
        nargs="*",
        default=None,
        metavar="ARGV",
        help="Enable AI mode. If no arguments are given, the built-in"
             " python AI is used. Otherwise, the first argument is"
             " treated as a path to an executable and all further "
             " arguments to --ai are passed to that executable."
    )
    parser.add_argument(
        "-d", "--detach",
        action="store_true",
        help="If given, detach from the terminal. No local output will"
             " be generated. Quite useless without --listen."
    )
    parser.add_argument(
        "-l", "--listen",
        nargs=1,
        dest="listen",
        metavar="BINDADDR:LISTEN",
        help="Listen for viewers on the TCP port and optionally bind"
             " to a specific address (the BINDADDR: part is optional)."
    )
    parser.add_argument(
        "-m", "--max-viewers",
        type=int,
        metavar="COUNT",
        default=0,
        help="Maximum amount of viewer clients to serve at one"
             " time. The default is 0 (unlimited)."
    )

    args = parser.parse_args()

    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main(args))
    finally:
        loop.close()
