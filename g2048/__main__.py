import argparse
import logging
import os

import g2048.logic
import g2048.ai
import g2048.pipe_ai
import g2048.urwid_frontend

parser = argparse.ArgumentParser()
parser.add_argument(
    "--ai",
    default=False,
    action="store_true",
    help="Run with AI instead of user input")
parser.add_argument(
    "--ai-command",
    nargs="+",
    default=None,
    help="Use the stdio AI provided instead of builtin")
parser.add_argument(
    "--profile",
    default=False,
    help="""Profiling: The profiling data will be saved to the given file
    name. If the file name is -, a shell will be spawned after the program has
    terminated.""")

args = parser.parse_args()

if os.path.isfile("ai.log"):
    os.unlink("ai.log")

logging.basicConfig(
    level=logging.DEBUG,
    filename="ai.log")

game = g2048.logic.Game()
game.new_game()
frontend = g2048.urwid_frontend.UrwidFrontend(game)
if args.ai:
    if args.ai_command:
        ai = g2048.pipe_ai.SubprocessAI(args.ai_command)
    else:
        ai = g2048.ai.AI()

    g2048.urwid_frontend.UrwidAIController(
        frontend,
        ai,
        interval=0.1)
else:
    g2048.urwid_frontend.UrwidController(frontend)

def run():
    try:
        frontend.run()
    except KeyboardInterrupt:
        return

if args.profile is not False:
    import cProfile
    if args.profile != "-":
        cProfile.run("run()", args.profile)
    else:
        stats = cProfile.run("run()")
        raise NotImplementedError("Not implemented")
else:
    run()
