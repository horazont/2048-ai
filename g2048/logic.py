import copy
import numpy
import random
import sys

prng = random.Random()
prng.seed(random.SystemRandom().getrandbits(128))

DIR_UP = (0, -1)
DIR_DOWN = (0, 1)
DIR_RIGHT = (1, 0)
DIR_LEFT = (-1, 0)

PROBABILITY4 = 0.1
PROBABILITY2 = 1-PROBABILITY4

VALID_DIRECTIONS = {DIR_UP, DIR_DOWN, DIR_RIGHT, DIR_LEFT}

class GameBoard:
    """
    Immutable representation of the game board.
    """

    dtype = numpy.dtype("uint8")

    def __init__(self, with_board=None, board_size=4):
        super().__init__()
        if with_board is not None:
            self._board = copy.copy(with_board)
            board_size = self._board.shape[0]
            if self._board.shape[1] != board_size:
                raise ValueError("Board must be square")
        else:
            self._board = numpy.zeros((board_size, board_size),
                                      self.dtype)
        self._board.flags.writeable = False

        self._board_size = board_size

    def __eq__(self, other):
        return (self._board == other._board).all()

    def __hash__(self):
        return hash(self._board.data)

    def __ne__(self, other):
        return not (self == other)

    @property
    def board(self):
        return self._board

    @property
    def board_size(self):
        return self._board_size

    def cleared(self):
        return GameBoard()

    def free_fields(self):
        return zip(*numpy.where(self._board == 0))

    def game_over(self):
        try:
            next(iter(self.free_fields()))
        except StopIteration:
            return False
        for direction in VALID_DIRECTIONS:
            if self.test_shift(direction):
                return False
        return True

    @classmethod
    def shift_array(cls, arr):
        i = 0
        while i < len(arr):
            merged = False
            if arr[i] != 0 and i > 0:
                if arr[i-1] == arr[i]:
                    arr[i-1] += 1
                    arr[i] = 0
                    merged = True
                    yield ("merge", i, i-1)
            if arr[i] == 0:
                for j in range(i+1, len(arr)):
                    if arr[j] != 0:
                        arr[i] = arr[j]
                        arr[j] = 0
                        yield ("shift", j, i)
                        if merged:
                            i += 1
                        break
                else:
                    i += 1
            else:
                i += 1

    @classmethod
    def shift_horiz(cls, board, right):
        for y, row in enumerate(board):
            if right:
                row = row[::-1]
            iterator = cls.shift_array(row)
            if right:
                yield from cls.translate_horiz(y, cls.translate_reversed(iterator))
            else:
                yield from cls.translate_horiz(y, iterator)

    @classmethod
    def shift_vert(cls, board, down):
        for x, col in enumerate(board.transpose()):
            if down:
                col = col[::-1]
            iterator = cls.shift_array(col)
            if down:
                yield from cls.translate_vert(x, cls.translate_reversed(iterator))
            else:
                yield from cls.translate_vert(x, iterator)

    def shifted(self, direction, actions=[]):
        self._validate_direction(direction)

        result = copy.copy(self)
        result._board = copy.copy(self._board)

        if direction[0] == 0:
            actions[:] = self.shift_vert(result._board,
                                         direction[1] > 0)
        else:
            actions[:] = self.shift_horiz(result._board,
                                          direction[0] > 0)

        result._board.flags.writeable = False
        return result

    def test_shift(self, direction, actions=[]):
        self.shifted(direction, actions=actions)
        return bool(actions)

    @classmethod
    def translate_reversed(self, iterable):
        for action, v1, v2 in iterable:
            yield action, 3-v1, 3-v2

    @classmethod
    def translate_horiz(cls, y, input):
        for action, x1, x2 in input:
            yield action, (x1, y), (x2, y)

    @classmethod
    def translate_vert(cls, x, input):
        for action, y1, y2 in input:
            yield action, (x, y1), (x, y2)

    def _validate_direction(self, direction):
        if direction not in VALID_DIRECTIONS:
            raise ValueError("Direction is not valid: {}".format(direction))

    def with_tile_placed(self, x, y, tile):
        if self.board[y, x] != 0:
            raise ValueError("There is a non-zero tile at location "
                             "{},{}".format(x, y))

        result = copy.copy(self)
        result._board = copy.copy(self._board)
        result._board[y, x] = tile
        result._board.flags.writeable = False
        return result

    def with_random_tile_placed(self):
        tile = 1 if prng.random() > PROBABILITY4 else 2
        free_fields = list(self.free_fields())
        picked = prng.choice(free_fields)
        result = copy.copy(self)
        result._board = copy.copy(self._board)
        result._board[picked[0],picked[1]] = tile
        result._board.flags.writeable = False
        return result

class Game:
    def __init__(self, board_size=4):
        super().__init__()
        self._game_over = True
        self.board = GameBoard(board_size=board_size)
        self.score = 0
        self.update_event = None

    def _call_update(self):
        if self.update_event:
            self.update_event(self)

    def _game_over(self):
        self.game_over = True

    def new_game(self):
        self.game_over = False
        self.score = 0
        self.board = self.board.cleared(
        ).with_random_tile_placed(
        ).with_random_tile_placed()

    def shift(self, direction):
        if self.game_over:
            return
        actions = []
        self.board = self.board.shifted(direction, actions=actions)
        if actions:
            with open("shift", "w") as f:
                print(str(self.board.board), file=f)
                for action, p0, p1 in actions:
                    print("{} {} {}".format(action, p0, p1), file=f)
                    if action == "merge":
                        self.score += 2**self.board.board.transpose()[p1]
            self.board = self.board.with_random_tile_placed()
        if self.board.game_over():
            self.game_over = True
