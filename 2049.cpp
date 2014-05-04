#include "2049.hpp"

#include <cassert>
#include <chrono>
#include <cmath>
#include <iomanip>
#include <iostream>
#include <fstream>

static std::random_device rd;
static std::independent_bits_engine<std::random_device,
                                    64,
                                    uint64_t> indepbits;

static std::ofstream logfile;

typedef std::chrono::steady_clock default_clock;

/* free functions */

score_t shift_line(std::array<cell_value_t*, board_size> &line)
{
    score_t result = 0;
    for (size_t i = 0; i < line.size(); /* nothing */) {
        bool merged = false;
        if (    *line[i] != 0 &&
                i > 0 &&
                *line[i-1] == *line[i])
        {
            *line[i-1] += 1;
            *line[i] = 0;
            merged = true;
            result += round(pow(SCORE_MERGE_BASE, *line[i-1]));
        }
        if (*line[i] == 0) {
            bool shifted = false;
            for (size_t j = i+1; j < line.size(); j++) {
                if (*line[j] != 0) {
                    *line[i] = *line[j];
                    *line[j] = 0;
                    shifted = true;
                    break;
                }
            }
            if (!shifted || merged) {
                i++;
            }
        } else {
            i++;
        }
    }
    return result;
};


/* GameBoard */

GameBoard::GameBoard():
    rows()
{

}

GameBoard::GameBoard(const RawBoard &board):
    rows(board)
{

}

score_t GameBoard::gradient_score() const
{
    score_t score = 0;
    for (auto &row: rows) {
        for (size_t x = 1; x < board_size; x++) {
            int diff = (int)row[x-1] - (int)row[x];
            if (diff > 0) {
                score += 1;
            } else if (diff < 0) {
                score += diff * 3 - (board_size-x)*8;

            }
        }
    }
    // for (size_t x = 0; x < board_size; x++) {
    //     for (size_t y = 1; y < board_size; y++) {
    //         int diff = (int)rows[y-1][x] - (int)rows[y][x];
    //         if (diff > 0) {
    //             score += 1;
    //         }
    //     }
    // }
    return score;
}

GameBoard &GameBoard::shift(Direction dir, score_t *score)
{
    std::array<std::array<cell_value_t*, board_size>, board_size> views{0};
    switch (dir) {
    case DIR_UP:
    {
        for (size_t x = 0; x < board_size; x++) {
            for (size_t y = 0; y < board_size; y++) {
                views[x][y] = &rows[y][x];
            }
        }
        break;
    };
    case DIR_DOWN:
    {
        for (size_t x = 0; x < board_size; x++) {
            for (size_t y = 0; y < board_size; y++) {
                views[x][(board_size-1)-y] = &rows[y][x];
            }
        }
        break;
    };
    case DIR_LEFT:
    {
        for (size_t y = 0; y < board_size; y++) {
            for (size_t x = 0; x < board_size; x++) {
                views[y][x] = &rows[y][x];
            }
        }
        break;
    };
    case DIR_RIGHT:
    {
        for (size_t y = 0; y < board_size; y++) {
            for (size_t x = 0; x < board_size; x++) {
                views[y][(board_size-1)-x] = &rows[y][x];
            }
        }
        break;
    };
    };

    score_t total_score = 0;
    for (size_t i = 0; i < board_size; i++) {
        total_score += shift_line(
            views[i]);
    }
    if (score) {
        *score = total_score;
    }

    return *this;
};

GameBoard &GameBoard::place_tile(
    const size_t x,
    const size_t y,
    const cell_value_t v)
{
    rows[y][x] = v;
    return *this;
};

/* Node */

Node::Node(score_t score,
           std::unique_ptr<GameBoard> &&result_board):
    score(score),
    result_board(std::move(result_board))
{

}

/* RandomNode */

RandomNode::RandomNode(score_t score,
                       std::unique_ptr<GameBoard> &&result_board,
                       float weight):
    Node(score, std::move(result_board)),
    weight(weight)
{

}

void RandomNode::aggregate_node_stats(TreeStats &stats) const
{
    stats.random_node_count++;
    for (auto &child: children) {
        if (child) {
            child->aggregate_node_stats(stats);
        }
    }
}

TreeStats RandomNode::collect_tree_stats() const
{
    TreeStats stats{0, 0, 0, 0, 0, 0};
    aggregate_node_stats(stats);
    stats.avg_move_score = ((double)stats.total_move_score) / stats.move_node_count;
    return stats;
}

Direction RandomNode::find_best_move() const
{
    Direction move;
    score_t score;
    MoveNode *node;
    std::tie(score, move, node) = find_best_move_info();
    return move;
}

std::tuple<score_t, Direction, MoveNode*> RandomNode::find_best_move_info() const
{
    std::tuple<score_t, Direction, MoveNode*> result = std::make_tuple(
        SCORE_GAME_OVER*2,
        DIR_UP,
        nullptr);


    for (size_t i = 0; i < 4; i++) {
        MoveNode *child = children[i].get();
        if (!child) {
            continue;
        }

        score_t child_result = child->find_best_move_info();

        if (child_result > std::get<0>(result)) {
            result = std::make_tuple(
                child_result,
                (Direction)i,
                child);
        }
    }

    return result;
}

bool RandomNode::has_children() const
{
    for (auto &child: children) {
        if (child) {
            return true;
        }
    }
    return false;
}

/* MoveNode */

void MoveNode::aggregate_node_stats(TreeStats &stats) const
{
    stats.move_node_count++;
    stats.min_move_score = std::min(stats.min_move_score, score);
    stats.max_move_score = std::max(stats.max_move_score, score);
    stats.total_move_score += score;
    for (auto &child: children) {
        child->aggregate_node_stats(stats);
    }
}

RandomNodePtr MoveNode::extract_node_by_board(const GameBoard &board)
{
    for (auto it = children.begin();
         it != children.end();
         it++)
    {
        RandomNodePtr &child = *it;
        if (child->result_board->rows == board.rows) {
            RandomNodePtr result = std::move(*it);
            children.erase(it);
            return std::move(result);
        }
    }

    return RandomNodePtr();
}

score_t MoveNode::find_best_move_info() const
{
    score_t total_child_score = 0;
    for (auto &child: children)
    {
        total_child_score += child->find_best_move();
    }

    score_t result_score = score;
    if (children.size() > 0) {
        result_score += ((double)total_child_score)/children.size();
    }

    return result_score;
}

RandomNode *MoveNode::new_child(float weight,
                                std::unique_ptr<GameBoard> &&new_board)
{
    return (*children.emplace(children.end(),
                              new RandomNode(0,
                                             std::move(new_board),
                                             weight))).get();

}

/* AI */

AI::AI(size_t max_tree_depth,
       float min_fill,
       float min_fill_decay_per_level,
       size_t min_new_nodes,
       float revisit_share):
    _prng(indepbits()),
    _max_tree_depth(max_tree_depth),
    _min_fill(min_fill),
    _min_fill_decay_per_level(min_fill_decay_per_level),
    _min_new_nodes(min_new_nodes),
    _revisit_share(revisit_share),
    _move_count(),
    _cache()
{

}

AnalyzeResult AI::actuate(const RawBoard &current_board)
{
    std::unique_ptr<GameBoard> board(new GameBoard(current_board));
    default_clock::time_point start = default_clock::now();
    AnalyzeResult move = analyze(std::move(board));
    std::chrono::duration<double> elapsed = default_clock::now() - start;
    logfile << "ai [move=" << (_move_count+1) << "]: eval time = "
            << elapsed.count() << " seconds" << std::endl;
    if (std::get<1>(move)) {
        _move_count++;
    }
    return move;
}

AnalyzeResult AI::analyze(std::unique_ptr<GameBoard> &&current_board)
{
    RandomNodePtr root;
    if (_cache) {
        root = std::move(_cache->extract_node_by_board(*current_board));
    }

    if (!root) {
        root = RandomNodePtr(new RandomNode(0, std::move(current_board), 1.0));
        logfile << "ai [move=" << (_move_count+1) << "]: cache miss" << std::endl;
    } else {
        logfile << "ai [move=" << (_move_count+1) << "]: cache hit" << std::endl;
    }

    for (unsigned int i = 0; i < 4; i++) {
        Direction dir = (Direction)i;
        MoveNode *child = root->new_child(dir, _prng);
        if (child) {
            deep_analyze(child, 1);
        }
    }

    {
        score_t score;
        Direction move;
        MoveNode *node;
        std::tie(score, move, node) = root->find_best_move_info();
        if (!node) {
            return std::make_tuple(0, false);
        } else {
            _cache = std::move(root->children[move]);
            TreeStats stats = root->collect_tree_stats();
            logfile << "ai [move=" << (_move_count+1) << "]: "<< std::endl
                    << "  move nodes analyzed : " << stats.move_node_count << std::endl
                    << "  rnd nodes analyzed  : " << stats.random_node_count << std::endl
                    << "  min move score      : " << stats.min_move_score << std::endl
                    << "  avg move score      : " << stats.avg_move_score << std::endl
                    << "  max move score      : " << stats.max_move_score << std::endl
                    << "  chosen subtree score: " << score << std::endl;

            return std::make_tuple(move, true);
        }
    }
}

void AI::deep_analyze(MoveNode *move_node,
                      size_t depth)
{
    if (depth > _max_tree_depth) {
        return;
    }

    const float min_fill = _min_fill*(
        pow(_min_fill_decay_per_level, (depth-1)));

    const size_t nodes_to_create =
        std::min(
            std::max(
                static_cast<size_t>(round(move_node->max_children*min_fill)),
                _min_new_nodes),
            move_node->options2.size() + move_node->options4.size());

    std::vector<cell_coord_t> &options2 = move_node->options2;
    std::vector<cell_coord_t> &options4 = move_node->options4;

    std::uniform_real_distribution<> dist;

    for (auto &child: move_node->children)
    {
        for (auto &subchild: child->children)
        {
            if (subchild) {
                deep_analyze(subchild.get(), depth+1);
            }
        }
    }


    for (size_t i = 0; i < nodes_to_create; i++)
    {
        cell_value_t tile = 0;
        cell_coord_t option;

        if (options2.size() && options4.size()) {
            tile = (dist(_prng) > 0.1
                    ? 1
                    : 2);
            if (tile == 1) {
                option = options2.back();
                options2.pop_back();
            } else {
                option = options4.back();
                options4.pop_back();
            }

        } else if (options2.size()) {
            option = options2.back();
            options2.pop_back();

        } else if (options4.size()) {
            option = options4.back();
            options4.pop_back();

        } else {
            assert(false);

        }

        std::unique_ptr<GameBoard> new_board(
            new GameBoard(*move_node->result_board));
        new_board->place_tile(std::get<0>(option),
                              std::get<1>(option),
                              tile);
        float weight = (tile == 2
                        ? 0.1
                        : 0.9);

        RandomNode *new_node = move_node->new_child(
            weight, std::move(new_board));

        for (unsigned int i = 0; i < 4; i++) {
            Direction dir = (Direction)i;
            MoveNode *subchild = new_node->new_child(dir, _prng);
            if (subchild) {
                deep_analyze(subchild, depth+1);
            }
        }

        if (!new_node->has_children()) {
            new_node->score = SCORE_GAME_OVER;
        }
    }
}

namespace std {

std::ostream &operator<<(std::ostream &s, const GameBoard &board)
{
    for (size_t y = 0; y < board_size; y++) {
        for (size_t x = 0; x < board_size; x++) {
            s << std::setw(3) << (int)board.rows[y][x];
        }
        s << std::endl;
    }
    return s;
};

}

void read_board(std::istream &is, RawBoard &board)
{
    for (size_t y = 0; y < board_size; y++) {
        for (size_t x = 0; x < board_size; x++) {
            is.read((std::istream::char_type*)&board[y][x], 1);
        }
    }
}

void read_state(std::istream &is, uint8_t &state)
{
    is.read((std::istream::char_type*)&state, 1);
}

int main()
{
    logfile.open("ai++.log", std::ios_base::out | std::ios_base::trunc);
    if (!logfile.is_open()) {
        std::cerr << "ai: cannot open log. terminating." << std::endl;
        return 1;
    }

    RawBoard board;
    uint8_t state;
    AI ai;
    while (true) {
        read_board(std::cin, board);
        read_state(std::cin, state);

        AnalyzeResult result = ai.actuate(board);
        if (std::get<1>(result)) {
            std::cout << (uint8_t)std::get<0>(result) << std::flush;
        } else {
            std::cerr << "ai: no further options. terminating." << std::endl;
            return 0;
        }
    }
}
