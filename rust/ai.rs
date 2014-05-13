#![feature(phase)]
#[phase(syntax, link)] extern crate log;

use std::io;
use std::fmt;

type Score = u64;
type LineView<'r> = [&'r mut u8, ..4];
type Line = [u8, ..4];

static SCORE_MERGE_FACTOR: f32 = 1.2f32;

#[deriving(Show)]
enum Direction {
    Up = 0,
    Down = 1,
    Left = 2,
    Right = 3
}


struct Board {
    cols: [[u8, ..4], ..4]
}

fn shift_line(line: &mut Line) -> u64 {
    let mut result: u64 = 0;
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
            result += line[i-1] as u64;
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

    (result as f32 * SCORE_MERGE_FACTOR).round() as u64
}

fn reversed_line(line: &Line) -> Line {
    [line[3], line[2], line[1], line[0]]
}

fn clone_line(line: &Line) -> Line {
    [line[0], line[1], line[2], line[3]]
}

impl Board {
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

    fn from_cols(lines: Vec<Line>) -> Board {
        let mut result = Board { cols: [[0, ..4], ..4] };
        let mut x = 0;
        for row in lines.iter() {
            let mut y = 0;
            for cell in row.iter() {
                result.cols[x][y] = *cell;
                y += 1;
            }
            x += 1;
        }
        result
    }

    fn from_rows(lines: Vec<Line>) -> Board {
        let mut result = Board { cols: [[0, ..4], ..4] };
        let mut y = 0;
        for col in lines.iter() {
            let mut x = 0;
            for cell in col.iter() {
                result.cols[x][y] = *cell;
                x += 1;
            }
            y += 1;
        }
        result
    }

    fn get_row(&self, idx: uint) -> Line {
        [self.cols[0][idx], self.cols[1][idx], self.cols[2][idx], self.cols[3][idx]]
    }

    fn get_col(&self, idx: uint) -> Line {
        [self.cols[idx][0], self.cols[idx][1], self.cols[idx][2], self.cols[idx][3]]
    }

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

enum MoveEvalResult {
    Valid(Score),
    InvalidMove
}

fn eval_move(curr_board: &Board, dir: Direction) -> MoveEvalResult {
    info!("evaluating move {} for board \n{}...\n",
          dir,
          *curr_board);
    let (new_board, move_score) = curr_board.shifted_board(dir);
    info!("evaluated move. new board: \n{}\n", new_board);
    if new_board == *curr_board {
        info!("boards are equal => InvalidMove\n")
        return InvalidMove;
    }

    Valid(move_score)
}

enum BestMove {
    Found(Score, Direction),
    NoMove
}

fn eval_moves(board: &Board) -> BestMove {
    let mut result: BestMove = NoMove;
    for move in [Up, Down, Left, Right].iter() {
        result = match eval_move(board, *move) {
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

    loop {
        let (board, _) = match read_request(&mut io::stdio::stdin_raw())
        {
            Ok(x) => x,
            Err(e) => {
                fail!("failed reading request: {}\n", e);
            }
        };

        info!("received board: {}", board);

        match eval_moves(&board) {
            Found(score, move) => {
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
