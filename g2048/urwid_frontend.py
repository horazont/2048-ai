import urwid
import sys

import g2048.logic as logic

palette = [
    ("tile-0", "black", "black", None, "#000", "#000"),
    ("tile-1", "black", "white", None, "#000", "#fee"),
    ("tile-2", "black", "white", None, "#000", "#fed"),
    ("tile-3", "black", "white", None, "#000", "#fb8"),
    ("tile-4", "black", "white", None, "#000", "#f96"),
    ("tile-5", "black", "white", None, "#000", "#f86"),
    ("tile-6", "black", "white", None, "#000", "#f64"),
    ("tile-7", "black", "white", None, "#000", "#fd7"),
    ("tile-8", "black", "white", None, "#000", "#fd6"),
    ("tile-9", "black", "white", None, "#000", "#fd5"),
    ("tile-10", "black", "white", None, "#000", "#fc4"),
    ("tile-11", "black", "white", None, "#000", "#fc3"),
]

class CardWidget(urwid.AttrMap):
    def __init__(self, value=0):
        text = urwid.Text("", align="center")
        box = urwid.Filler(text, valign="middle")
        super().__init__(urwid.BoxAdapter(box, 5), "tile-0")
        self._box = box
        self._text = text
        self.value = value

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        value = int(value)
        self.set_attr_map({None: "tile-{}".format(value)})
        self._text.set_text(str(2**value) if value > 0 else "")
        self._value = value

class BoardPile(urwid.Pile):
    def __init__(self, board_size=4):
        rows = []
        items = []
        for i in range(board_size):
            w = CardWidget()
            rows.append(w)
            items.append(w)
            if i < board_size-1:
                items.append(urwid.Divider())
        super().__init__(items)
        self._rows = rows

    def get_row(self, y):
        return self._rows[y]

class Board(urwid.Columns):
    def __init__(self, board_size=4):
        super().__init__(
            [(11, BoardPile(board_size=board_size))
             for i in range(board_size)],
            dividechars=2)

    def get_cell(self, x, y):
        return self.contents[x][0].get_row(y)

class UrwidController:
    def __init__(self, urwid_frontend):
        self._frontend = urwid_frontend
        self._game = urwid_frontend._game

    def actuate(self, direction):
        self._game.shift(direction)
        self._frontend.update()

class UrwidKeyboardController(UrwidController):
    def __init__(self, urwid_frontend):
        super().__init__(urwid_frontend)
        self._frontend.unhandled_input = self.unhandled_input

    def unhandled_input(self, key):
        if key == 'up':
            self.actuate(logic.DIR_UP)
        elif key == 'down':
            self.actuate(logic.DIR_DOWN)
        elif key == 'left':
            self.actuate(logic.DIR_LEFT)
        elif key == 'right':
            self.actuate(logic.DIR_RIGHT)

class UrwidAIController(UrwidController):
    def __init__(self, urwid_frontend, ai, interval=0.5):
        super().__init__(urwid_frontend)
        self._interval = interval
        self._loop = self._frontend._loop
        self._loop.set_alarm_in(interval, self.call_ai)
        self._ai = ai

    def call_ai(self, loop, user_data=None):
        direction = self._ai.actuate(self._game)
        if direction is not None:
            self.actuate(direction)
        loop.set_alarm_in(self._interval, self.call_ai)

class UrwidFrontend:
    def __init__(self, game):
        self._game = game
        self._board = Board()
        fill = urwid.AttrMap(
            urwid.Filler(self._board,
                         valign="top"),
            "tile-0")

        self.unhandled_input = None
        self._screen = urwid.raw_display.Screen()
        self._screen.register_palette(palette)
        self._screen.set_terminal_properties(colors=256)
        self._loop = urwid.MainLoop(fill,
                                    screen=self._screen,
                                    unhandled_input=self.handle_input)
        self.update()

    def handle_input(self, key):
        if key in ('Q', 'q', 'esc'):
            raise urwid.ExitMainLoop()

        if self.unhandled_input:
            self.unhandled_input(key)

    def run(self):
        self._loop.run()

    def update(self):
        board = self._game.board.board
        for y, xs in enumerate(board):
            for x, c in enumerate(xs):
                cell_widget = self._board.get_cell(x, y)
                cell_widget.value = c
