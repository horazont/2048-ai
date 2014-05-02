import copy
import unittest

import numpy
import numpy.testing

import g2048.logic as logic

class TestGameBoard(unittest.TestCase):
    def test_shift_array(self):
        arr = numpy.asarray([1, 1, 0, 0], logic.GameBoard.dtype)
        list(logic.GameBoard.shift_array(arr))
        numpy.testing.assert_array_equal(
            numpy.asarray([2, 0, 0, 0], logic.GameBoard.dtype),
            arr)

        arr = numpy.asarray([1, 0, 0, 1], logic.GameBoard.dtype)
        list(logic.GameBoard.shift_array(arr))
        numpy.testing.assert_array_equal(
            numpy.asarray([2, 0, 0, 0], logic.GameBoard.dtype),
            arr)

        arr = numpy.asarray([1, 1, 1, 1], logic.GameBoard.dtype)
        actions = list(logic.GameBoard.shift_array(arr))
        numpy.testing.assert_array_equal(
            numpy.asarray([2, 2, 0, 0], logic.GameBoard.dtype),
            arr)
        self.assertSequenceEqual(
            [
                ("merge", 1, 0),
                ("shift", 2, 1),
                ("shift", 3, 2),
                ("merge", 2, 1)
            ],
            actions)

        arr = numpy.asarray([1, 2, 1, 1], logic.GameBoard.dtype)
        actions = list(logic.GameBoard.shift_array(arr))
        numpy.testing.assert_array_equal(
            numpy.asarray([1, 2, 2, 0], logic.GameBoard.dtype),
            arr)
        self.assertSequenceEqual(
            [
                ("merge", 3, 2)
            ],
            actions)

        arr = numpy.asarray([1, 1, 0, 2], logic.GameBoard.dtype)
        actions = list(logic.GameBoard.shift_array(arr))
        numpy.testing.assert_array_equal(
            numpy.asarray([2, 2, 0, 0], logic.GameBoard.dtype),
            arr)

    def test_shift_actions(self):
        start_board = numpy.asarray(
            [
                [1, 2, 1, 2],
                [1, 2, 2, 0],
                [1, 1, 1, 0],
                [1, 1, 1, 1]
            ],
            logic.GameBoard.dtype)


        g = logic.GameBoard(with_board=start_board)

        actions = []
        g = g.shifted(logic.DIR_UP, actions=actions)
        numpy.testing.assert_array_equal(
            numpy.asarray(
                [
                    [2, 3, 1, 2],
                    [2, 2, 2, 1],
                    [0, 0, 2, 0],
                    [0, 0, 0, 0],
                ],
                g.dtype),
            g.board)

        self.assertSequenceEqual(
            [
                ("merge", (0, 1), (0, 0)),
                ("shift", (0, 2), (0, 1)),
                ("shift", (0, 3), (0, 2)),
                ("merge", (0, 2), (0, 1)),
                ("merge", (1, 1), (1, 0)),
                ("shift", (1, 2), (1, 1)),
                ("shift", (1, 3), (1, 2)),
                ("merge", (1, 2), (1, 1)),
                ("merge", (2, 3), (2, 2)),
                ("shift", (3, 3), (3, 1))
            ],
            actions)

        self.assertEqual(
            2,
            g.board.transpose()[actions[0][2]])
        self.assertEqual(
            2,
            g.board.transpose()[actions[3][2]])
        self.assertEqual(
            3,
            g.board.transpose()[actions[4][2]])
        self.assertEqual(
            2,
            g.board.transpose()[actions[7][2]])
        self.assertEqual(
            2,
            g.board.transpose()[actions[8][2]])

    def test_shift_up(self):
        start_board = numpy.asarray(
            [
                [1, 1, 1, 1],
                [1, 1, 1, 1],
                [1, 1, 1, 1],
                [1, 1, 1, 1]
            ],
            logic.GameBoard.dtype)


        g = logic.GameBoard(with_board=start_board)

        g = g.shifted(logic.DIR_UP)
        numpy.testing.assert_array_equal(
            numpy.asarray(
                [
                    [2, 2, 2, 2],
                    [2, 2, 2, 2],
                    [0, 0, 0, 0],
                    [0, 0, 0, 0],
                ],
                g.dtype),
            g.board)

    def test_shift_down(self):
        start_board = numpy.asarray(
            [
                [1, 1, 1, 1],
                [1, 1, 1, 1],
                [1, 1, 1, 1],
                [1, 1, 1, 1]
            ],
            logic.GameBoard.dtype)


        g = logic.GameBoard(with_board=start_board)

        g = g.shifted(logic.DIR_DOWN)
        numpy.testing.assert_array_equal(
            numpy.asarray(
                [
                    [0, 0, 0, 0],
                    [0, 0, 0, 0],
                    [2, 2, 2, 2],
                    [2, 2, 2, 2],
                ],
                g.dtype),
            g.board)

    def test_shift_right(self):
        start_board = numpy.asarray(
            [
                [1, 1, 1, 1],
                [1, 1, 1, 1],
                [1, 1, 1, 1],
                [1, 1, 1, 1]
            ],
            logic.GameBoard.dtype)


        g = logic.GameBoard(with_board=start_board)

        g = g.shifted(logic.DIR_RIGHT)
        numpy.testing.assert_array_equal(
            numpy.asarray(
                [
                    [0, 0, 0, 0],
                    [0, 0, 0, 0],
                    [2, 2, 2, 2],
                    [2, 2, 2, 2],
                ],
                g.dtype).transpose(),
            g.board)

    def test_shift_left(self):
        start_board = numpy.asarray(
            [
                [1, 1, 1, 1],
                [1, 1, 1, 1],
                [1, 1, 1, 1],
                [1, 1, 1, 1]
            ],
            logic.GameBoard.dtype)


        g = logic.GameBoard(with_board=start_board)

        g = g.shifted(logic.DIR_LEFT)
        numpy.testing.assert_array_equal(
            numpy.asarray(
                [
                    [2, 2, 2, 2],
                    [2, 2, 2, 2],
                    [0, 0, 0, 0],
                    [0, 0, 0, 0],
                ],
                g.dtype).transpose(),
            g.board)
