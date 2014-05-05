import logging
import subprocess
import struct

import g2048.logic as logic

logger = logging.getLogger(__name__)

class SubprocessAI:
    def __init__(self, cmd):
        super().__init__()
        self._send_struct = struct.Struct("B"*17)
        self._process = subprocess.Popen(
            cmd,
            shell=False,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE)

    def actuate(self, game):
        if not self._process:
            return
        board_and_state = list(game.board.board.flatten())
        board_and_state.append(0)
        buf = self._send_struct.pack(*board_and_state)
        logger.info("sending board to child AI (status=%s, state=%s, buffer=%s)",
                    self._process.poll(),
                    board_and_state,
                    buf)
        self._process.stdin.write(buf)
        self._process.stdin.flush()
        read = self._process.stdout.read(1)
        if not read:
            logger.warn("AI process has terminated. exit code=%d",
                        self._process.returncode)
            self._process = None
            return

        directions = [
            logic.DIR_UP,
            logic.DIR_DOWN,
            logic.DIR_LEFT,
            logic.DIR_RIGHT,
        ]

        try:
            direction = directions[read[0]]
        except IndexError:
            logger.error("Invalid movement code returned: %d",
                         read[0])
            return
        return direction
