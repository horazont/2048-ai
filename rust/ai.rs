#![feature(phase)]
#[phase(syntax, link)] extern crate log;
#[phase(syntax, link)] extern crate rand;
extern crate sync;

use std::io;
use std::fmt;
use std::cmp;
use std::num;
use rand::Rng;

type Score = i64;
type LineView<'r> = [&'r mut u8, ..4];
type Line = [u8, ..4];

static SCORE_MERGE_FACTOR: f32 = 1.2f32;
static GAME_OVER_SCORE: Score = -2048;

#[deriving(Show, Clone)]
enum Direction {
    Up = 0,
    Down = 1,
    Left = 2,
    Right = 3
}

/// A 2048 game board, consisting of 4 times 4 squares. Each slot in
/// the array holds the log2 of the actual value of the square.
struct Board {
    cols: [[u8, ..4], ..4]
}

/// Shift a 2048 line (either horizontal or vertical) towards lower
/// indicies. Takes a mutable line and returns the merging score
/// obtained by this move.
///
/// Goes through the Line from low to high indicies. On each slot, it
/// is checked whether the previous slot has the same number as the
/// current one. If so, the current one is merged with the previous
/// slot and the current slot is set to zero.
///
/// Then, if the current slot is zero, the subsequent slots are
/// searched for non-zero slots. The first non-zero slot encountered
/// will be shifted into the current position. If no slots were
/// shifted or a merge has taken place, the next iteration will deal
/// with the next slot, otherwise the same slot is inspected again.
///
/// Each merge scores with the resulting number times the
/// SCORE_MERGE_FACTOR.
fn shift_line(line: &mut Line) -> Score {
    let mut result: Score = 0;
    let mut i = 0;
    while i < line.len() {
        let mut merged = false;
        if line[i] != 0 &&
           i > 0 &&
           line[i-1] == line[i]
        {
            line[i-1] += 1;
            line[i] = 0;
            merged = true;
            result += line[i-1] as Score;
        }
        if line[i] == 0 {
            let mut shifted = false;
            let mut j = i+1;
            while j < line.len() {
                if line[j] != 0 {
                    line[i] = line[j];
                    line[j] = 0;
                    shifted = true;
                    break;
                }
                j += 1;
            }
            if !shifted || merged {
                i += 1;
            }
        } else {
            i += 1;
        }
    }

    (result as f32 * SCORE_MERGE_FACTOR).round() as Score
}

/// Reverse a Line and return the result as a copy
fn reversed_line(line: &Line) -> Line {
    [line[3], line[2], line[1], line[0]]
}

/// Clone a line
fn clone_line(line: &Line) -> Line {
    [line[0], line[1], line[2], line[3]]
}

/// Implementation of the 2048 board
impl Board {

    /// Create a board from a vector of bytes. Each byte is taken as
    /// the literal value. The bytes are supposed to be in
    /// columns-first order (that is, x increments before y
    /// increments).
    fn from_raw(src: &Vec<u8>) -> Board {
        assert!(src.len() == 16);

        let mut result = Board { cols : [[0, ..4], ..4] };

        let mut y = 0;
        let mut x = 0;
        for item in src.iter() {
            result.cols[x][y] = *item;

            x += 1;
            if x == 4 {
                x = 0;
                y += 1;
            }
        }

        result
    }

    /// Construct a board from a vector of four lines, taken as
    /// one column each.
    fn from_cols(lines: Vec<Line>) -> Board {
        assert!(lines.len() == 4);
        let mut result = Board { cols: [[0, ..4], ..4] };
        let mut x = 0;
        for col in lines.iter() {
            let mut y = 0;
            for cell in col.iter() {
                result.cols[x][y] = *cell;
                y += 1;
            }
            x += 1;
        }
        result
    }

    /// Construct a board from a vector of four lines, taken as one
    /// row each.
    fn from_rows(lines: Vec<Line>) -> Board {
        assert!(lines.len() == 4);
        let mut result = Board { cols: [[0, ..4], ..4] };
        let mut y = 0;
        for row in lines.iter() {
            let mut x = 0;
            for cell in row.iter() {
                result.cols[x][y] = *cell;
                x += 1;
            }
            y += 1;
        }
        result
    }

    /// Return a Line with the contents of the row with the given
    /// index.
    fn get_row(&self, idx: uint) -> Line {
        [self.cols[0][idx], self.cols[1][idx], self.cols[2][idx], self.cols[3][idx]]
    }

    /// Return a Line with the contents of the column with the given
    /// index.
    fn get_col(&self, idx: uint) -> Line {
        [self.cols[idx][0], self.cols[idx][1], self.cols[idx][2], self.cols[idx][3]]
    }

    /// Calculate the AI score for the given constellation. This
    /// calculates the gradient of the game board and gives back score
    /// for consistent gradients.
    ///
    /// The gradients along the vertical and the horizontal axis are
    /// scored differently. For each of the axis, two different values
    /// are calculated, but both using the same scheme. One value is
    /// taken in the forward and one in the backward direction.
    ///
    /// For the horizontal axis, the value of a cell is calculated by
    /// taking the difference of the corresponding edge cell (same y
    /// value, but 0 x index). If the difference is greater than or
    /// equal to zero, a small positive score is applied. Otherwise, a
    /// larger negative score is applied. The second value uses the
    /// last (x=3) cell as reference.
    ///
    /// For the vertical axis, the score is based on the difference to
    /// the previous cell (same x, but y-1). For a positive
    /// difference, a small positive amount is scored. Negative or
    /// zero differences are not counted. The second value uses the
    /// reverse direction (comparing to the next cell instead of the
    /// previous).
    ///
    /// Of both axis, the maximum value (taking the sign into account)
    /// is used. Both are summed together, rounded to the nearest
    /// integer and returned as score.
    fn gradient_score(&self) -> Score {
        let zero_hdiff_score = 1.;
        let pos_hdiff_score = 1.;
        let neg_hdiff_score = -12.;
        let pos_vdiff_score = 0.5;

        let (mut horiz_score_a, mut horiz_score_b) = (0.0f32, 0.0f32);
        let (mut vert_score_a, mut vert_score_b) = (0.0f32, 0.0f32);

        let mut x = 0;
        while x < 4 {
            let mut y = 0;
            while y < 4 {
                let horiz_diff_a = self.cols[0][y] as int - self.cols[x][y] as int;
                let horiz_diff_b = self.cols[3][y] as int - self.cols[x][y] as int;
                let vert_diff = if y > 0 {
                    self.cols[x][y-1] as int - self.cols[x][y] as int
                } else {
                    0
                };

                horiz_score_a += match horiz_diff_a {
                    diff if diff > 0 => pos_hdiff_score,
                    diff if diff < 0 => neg_hdiff_score,
                    _ => zero_hdiff_score
                };

                horiz_score_b += match horiz_diff_b {
                    diff if diff > 0 => pos_hdiff_score,
                    diff if diff < 0 => neg_hdiff_score,
                    _ => zero_hdiff_score
                };


                if vert_diff > 0 {
                    vert_score_a += pos_vdiff_score;
                } else if vert_diff < 0 {
                    vert_score_b += pos_vdiff_score;
                };

                y += 1;
            }
            x += 1;
        }

        (horiz_score_a.max(horiz_score_b)+
         vert_score_a.max(vert_score_b)).round() as Score
    }

    /// Return a copy of the board in which the tile at position ``(x,
    /// y)`` is replaced with the value passed as *tile*.
    fn place_tile(&self,
                  x: uint,
                  y: uint,
                  tile: u8) -> Board
    {
        let mut copy = self.clone();
        copy.cols[x][y] = tile;
        copy
    }

    /// Set the tile at position ``x, y`` to the value *tile*.
    fn set_tile(&mut self, x: uint, y: uint, tile: u8)
    {
        self.cols[x][y] = tile;
    }

    /// Shift the board in the given direction and return the new
    /// board, along with the merging score obtained from this move.
    fn shifted_board(&self,
                     dir: Direction) -> (Board, Score) {
        let lines_base = match dir {
            Up | Down => [self.get_col(0), self.get_col(1),
                          self.get_col(2), self.get_col(3)],
            Left | Right => [self.get_row(0), self.get_row(1),
                             self.get_row(2), self.get_row(3)],
        };

        let mut lines = match dir {
            Down | Right => {
                lines_base.iter().map(reversed_line)
                    .collect::<Vec<Line>>()
            }
            Up | Left => {
                lines_base.iter().map(clone_line)
                    .collect::<Vec<Line>>()
            }
        };

        let mut score: Score = 0;
        for line in lines.mut_iter() {
            score += shift_line(line);
        }

        (match dir {
            Left => Board::from_rows(lines),
            Right => Board::from_rows(lines.iter().map(reversed_line).collect::<Vec<Line>>()),
            Up => Board::from_cols(lines),
            Down => Board::from_cols(lines.iter().map(reversed_line).collect::<Vec<Line>>())
        }, score)
    }

    fn total_value(&self) -> Score {
        self.cols.iter().fold(
            0,
            |prev, col| prev + col.iter().fold(
                0,
                |prev, curr| prev + *curr as Score))
    }

    fn total_value_exp(&self) -> Score {
        self.cols.iter().fold(
            0,
            |prev, col| prev + col.iter().fold(
                0,
                |prev, curr| prev + num::pow(2, *curr as uint) as Score))
    }

    fn total_nonzeros(&self) -> uint {
        self.cols.iter().fold(
            0,
            |prev, col| prev + col.iter().fold(
                0,
                |prev, curr| prev + match *curr {
                    0 => 0,
                    _ => 1
                }))
    }
}

impl Clone for Board {
    fn clone(&self) -> Board {
        Board::from_cols(vec![self.get_col(0),
                              self.get_col(1),
                              self.get_col(2),
                              self.get_col(3)])
    }
}

struct OptionsIterator<'a> {
    board: &'a Board,
    last: Option<(uint, uint)>
}

impl<'a> OptionsIterator<'a> {
    fn new(board: &'a Board) -> OptionsIterator<'a> {
        OptionsIterator { board: board,
                          last: None }
    }
}

impl<'a> Iterator<(uint, uint)> for OptionsIterator<'a> {
    fn next(&mut self) -> Option<(uint, uint)> {
        loop {
            let (nextx, nexty) = match self.last {
                Some((x, y)) if x == 3 && y < 3 =>
                    (0, y+1),
                Some((x, y)) if x == 3 && y == 3 => {
                    return None;
                }
                Some((x, y)) if x < 3 =>
                    (x+1, y),
                None =>
                    (0, 0),
                Some(_) => {
                    return None; // invalid state
                }
            };

            self.last = Some((nextx, nexty));

            if self.board.cols[nextx][nexty] != 0 {
                continue;
            }

            return self.last.clone();
        }
    }
}

impl Eq for Board {
    fn eq(&self, other: &Board) -> bool {
        self.cols.iter().zip(other.cols.iter()).fold(
            true,
            |prev, (acol, bcol)| prev && acol.iter().zip(bcol.iter()).fold(
                true,
                |prev, (acell, bcell)| prev && (acell == bcell)))
    }
}

impl fmt::Show for Board {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        let mut y = 0;
        while y < 4 {
            let mut x = 0;
            while x < 4 {
                try!(write!(f.buf, "{} ", self.cols[x][y]));
                x += 1;
            }
            try!(write!(f.buf, "\n"));
            y += 1;
        }
        Ok(())
    }
}

fn read_request<FileT: Reader>(src: &mut FileT) -> Result<(Board, u8), io::IoError>
{
    let raw_board = try!(src.read_exact(16));
    let raw_unused = try!(src.read_byte());
    Ok((Board::from_raw(&raw_board), raw_unused))
}

fn shuffle<T: Clone>(dest: &mut Vec<T>)
{
    let mut i: uint = 0;
    let sl = dest.as_mut_slice();
    while i < sl.len() - 1 {
        let j = rand::task_rng().gen_range(i+1, sl.len());
        let tmp = sl[j].clone();
        sl[j] = sl[i].clone();
        sl[i] = tmp;
        i += 1;
    }
}

#[deriving(Clone)]
struct EvalContext {
    max_depth: uint,
    min_fill: f32,
    min_fill_decay_per_level: f32,
    min_new_nodes: uint
}

enum MoveEvalResult {
    Valid(Score),
    InvalidMove
}

enum BestMove {
    Move(Score, Direction),
    NoMove
}

#[deriving(Clone)]
enum IntermediateBestMove  {
    Found(Score, Direction),
    DepthExceeded,
    GameOver
}

impl EvalContext {

    fn new(max_depth: uint,
           min_fill: f32,
           min_fill_decay_per_level: f32,
           min_new_nodes: uint) -> EvalContext {
        assert!(max_depth >= 1);
        EvalContext { max_depth: max_depth,
                      min_fill: min_fill,
                      min_fill_decay_per_level: min_fill_decay_per_level,
                      min_new_nodes : min_new_nodes }
    }

    fn eval_move(&self, curr_board: &Board,
                 dir: Direction, depth: uint) -> MoveEvalResult
    {
        if depth == 1 {
            info!("evaluating move {} for board \n{}...\n",
                  dir,
                  *curr_board);
        }
        let (mut new_board, move_score) = curr_board.shifted_board(dir);
        if depth == 1 {
            info!("evaluated move. new board: \n{}\n", new_board);
        }
        if new_board == *curr_board {
            if depth == 1 {
                info!("boards are equal => InvalidMove\n");
            }
            return InvalidMove;
        }

        let mut options = OptionsIterator::new(&new_board).collect::<Vec<(uint, uint)>>();
        shuffle(&mut options);

        let fill = self.min_fill * num::pow(self.min_fill_decay_per_level,
                                            (depth-1));

        let to_fill = cmp::min(
            cmp::max(
                ((fill*16.).round() as uint),
                self.min_new_nodes),
            options.len());

        let mut results = Vec::new();
        if depth == 1 {
            let mut futures = Vec::new();
            let mut i = 0;
            let copied = (*self).clone();
            while i < to_fill {
                let &(x, y) = options.get(i);
                for tilev in [1u8, 2u8].iter() {
                    let child_board = new_board.place_tile(
                        x, y, *tilev);
                    futures.push(
                        sync::Future::spawn(
                            proc() {
                                copied.eval_moves(&child_board, depth+1)
                            }));
                }
                i += 1;
            }
            results = Vec::from_fn(
                futures.len(),
                |idx| futures.get_mut(idx).get());
        } else {
            let mut i = 0;
            while i < to_fill {
                let &(x, y) = options.get(i);
                for tilev in [1u8, 2u8].iter() {
                    new_board.set_tile(x, y, *tilev);
                    results.push(self.eval_moves(&new_board, depth+1));
                    new_board.set_tile(x, y, 0);
                }
                i += 1;
            }
        }

        let total_child_score = results.iter().fold(
            0,
            |prev, curr| prev + match *curr {
                Found(new_score, _) => new_score,
                GameOver => GAME_OVER_SCORE,
                DepthExceeded => 0
            });

        if depth == 1 {
            info!("gradient score: {}\n", new_board.gradient_score());
        }

        let total_score = move_score + new_board.gradient_score() +
            ((total_child_score as f32) / (results.len() as f32)).round() as Score;

        if depth == 1 {
            info!("total score: {}\n", total_score);
        }

        Valid(total_score)
    }

    fn eval_moves(&self, board: &Board, depth: uint) -> IntermediateBestMove
    {
        if depth > self.max_depth {
            return DepthExceeded;
        }

        let mut result: IntermediateBestMove = GameOver;
        for move in [Up, Down, Left, Right].iter() {
            result = match self.eval_move(board, *move, depth) {
                Valid(score) => match result {
                    Found(found_score, _) if found_score >= score
                        => result,
                    _ => Found(score, *move)
                },
                InvalidMove => result
            }
        }
        result
    }

    fn eval(&self, board: &Board) -> BestMove {
        match self.eval_moves(board, 1) {
            Found(score, dir) => Move(score, dir),
            DepthExceeded => fail!("this must not happen"),
            GameOver => NoMove
        }
    }
}

struct LogToFile<'a> {
    f: io::File
}

impl<'a> LogToFile<'a> {
    fn try_log(&mut self, record: &log::LogRecord) -> Result<(), io::IoError> {
        try!(write!(&mut self.f, "{level:>6}:{file}:{line} {level} {args}",
                    file=record.file,
                    line=record.line,
                    level=record.level,
                    args=record.args));
        Ok(())
    }
}

impl<'a> log::Logger for LogToFile<'a> {
    fn log(&mut self, record: &log::LogRecord) {
        match self.try_log(record) {
            Ok(_) => (),
            Err(e) => {
                fail!("failed to write log: {}\n", e);
            }
        }
    }
}

fn main() {
    let f = match io::File::create(&Path::new("log.txt")) {
        Ok(f) => f,
        Err(e) => {
            println!("failed to open log: {}", e);
            fail!();
        }
    };

    log::set_logger(box LogToFile{ f: f });

    let min_max_depth = 2;
    let max_max_depth = 7;
    let default_max_depth = 5;

    let mut ctx = EvalContext::new(
        5,
        1.0,
        0.6,
        2);

    loop {
        let (board, _) = match read_request(&mut io::stdio::stdin_raw())
        {
            Ok(x) => x,
            Err(e) => {
                fail!("failed reading request: {}\n", e);
            }
        };

        info!("received board: {}", board);

        let value = board.total_value_exp();
        let nonzeros = board.total_nonzeros();

        // high value condition: a total of more than 128 definetly requires
        // attention, independent from the amount of free fields
        let high_value = value >= 128;

        ctx.max_depth = match (high_value, nonzeros) {
            (true, nonzeros) if nonzeros >= 10 =>
                (default_max_depth + max_max_depth) / 2,
            (true, nonzeros) if nonzeros >= 12 =>
                max_max_depth,
            (true, _) => default_max_depth,
            (false, nonzeros) if nonzeros >= 10 =>
                (default_max_depth + max_max_depth) / 2,
            (false, nonzeros) if nonzeros >= 14 =>
                max_max_depth,
            (false, nonzeros) if nonzeros < 4 =>
                min_max_depth,
            (false, nonzeros) if nonzeros < 6 =>
                (min_max_depth + min_max_depth + default_max_depth) / 3,
            (false, _) => default_max_depth
        };

        match ctx.eval(&board) {
            Move(score, move) => {
                info!("evaluated: score={}, move={}\n", score, move as u8);
                match io::stdio::stdout_raw().write_u8(move as u8) {
                    Ok(x) => x,
                    Err(e) => {
                        fail!("failed writing response: {}\n", e);
                    }
                };
            }
            NoMove => {
                error!("evaluated: out of options!\n");
                return;
            }
        }

    }
}
