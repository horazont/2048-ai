#include <array>
#include <algorithm>
#include <cstdio>
#include <cstdint>
#include <memory>
#include <ostream>
#include <random>
#include <tuple>
#include <vector>

typedef uint8_t cell_value_t;
typedef std::tuple<size_t, size_t> cell_coord_t;
typedef int32_t score_t;

struct TreeStats {
    size_t move_node_count;
    size_t random_node_count;
    score_t min_move_score;
    score_t max_move_score;
    score_t total_move_score;
    float avg_move_score;
};

static constexpr double SCORE_MERGE_BASE = 1.9;
static constexpr double SCORE_MERGE_FACTOR = 1.2;
static constexpr score_t SCORE_GAME_OVER = -1024;

static constexpr size_t board_size = 4;

enum Direction {
    DIR_UP = 0,
    DIR_DOWN = 1,
    DIR_LEFT = 2,
    DIR_RIGHT = 3
};

struct BoardAction {
    enum Kind {
        MERGE,
        SHIFT
    };

    Kind kind;
    cell_coord_t p0;
    cell_coord_t p1;
};

struct PartialAction {
    BoardAction::Kind kind;
    size_t i;
    size_t j;
};

typedef std::array<std::array<cell_value_t, board_size>, board_size> RawBoard;

score_t shift_line(std::array<cell_value_t*, board_size> &line);

class GameBoard {
public:
    GameBoard();
    explicit GameBoard(const RawBoard &board);

    RawBoard rows;

    template <typename OutputIterator>
    inline void free_fields(OutputIterator it) {
        size_t y = 0;
        for (auto &row: rows) {
            size_t x = 0;
            for (auto value: row) {
                if (value == 0) {
                    *it++ = cell_coord_t(x, y);
                }
                x++;
            }
            y++;
        }
    };

    GameBoard &place_tile(const size_t x,
                          const size_t y,
                          const cell_value_t v);

    GameBoard &shift(Direction dir, score_t *score);

    inline GameBoard shifted(Direction dir, score_t *score)
    {
        GameBoard result(*this);
        result.shift(dir, score);
        return result;
    };

    score_t gradient_score() const;

};

class RandomNode;
typedef std::unique_ptr<RandomNode> RandomNodePtr;
class MoveNode;
typedef std::unique_ptr<MoveNode> MoveNodePtr;

class Node {
public:
    Node(score_t score,
         std::unique_ptr<GameBoard> &&result_board);

public:
    score_t score;
    const std::unique_ptr<GameBoard> result_board;

};

class RandomNode: public Node {
public:
    RandomNode(score_t score,
               std::unique_ptr<GameBoard> &&result_board,
               float weight);

public:
    float weight;
    std::array<MoveNodePtr, 4> children;

public:
    void aggregate_node_stats(TreeStats &stats) const;
    TreeStats collect_tree_stats() const;
    Direction find_best_move() const;
    std::tuple<score_t, Direction, MoveNode*> find_best_move_info() const;
    bool has_children() const;

    template <typename URNG>
    MoveNode *new_child(Direction dir, URNG &&rng)
    {
        std::unique_ptr<GameBoard> child_board(new GameBoard(*result_board));
        score_t score = 0;
        child_board->shift(dir, &score);
        score += child_board->gradient_score();
        if (child_board->rows == result_board->rows) {
            return nullptr;
        }

        MoveNodePtr child(new MoveNode(
                              score,
                              std::move(child_board),
                              rng));
        children[dir] = std::move(child);
        return children[dir].get();
    }


};

class MoveNode: public Node {
public:
    template <typename URNG>
    MoveNode(score_t score,
             std::unique_ptr<GameBoard> &&result_board,
             URNG &&rng):
        Node(score, std::move(result_board))
    {
        std::vector<cell_coord_t> free_fields;
        this->result_board->free_fields(std::back_inserter(free_fields));
        options2 = free_fields;
        options4 = free_fields;

        std::shuffle(options2.begin(),
                     options2.end(),
                     rng);
        std::shuffle(options4.begin(),
                     options4.end(),
                     rng);

        max_children = free_fields.size() * 2;
    }

public:
    size_t max_children;
    // options are shuffled
    std::vector<cell_coord_t> options2;
    std::vector<cell_coord_t> options4;
    std::vector<RandomNodePtr> children;

public:
    void aggregate_node_stats(TreeStats &stats) const;
    RandomNodePtr extract_node_by_board(const GameBoard &board);
    score_t find_best_move_info() const;
    RandomNode *new_child(float weight,
                          std::unique_ptr<GameBoard> &&new_board);

};

typedef std::tuple<score_t, bool> AnalyzeResult;

class AI {
public:
    explicit AI(size_t max_tree_depth = 4,
                float min_fill = 1.0,
                float min_fill_decay_per_level = 0.3,
                size_t min_new_nodes = 2,
                float revisit_share = 0.26);
    AI(const AI &ref) = delete;
    AI &operator=(const AI &ref) = delete;
    AI(AI &&ref) = default;
    AI &operator=(AI &&ref) = default;

private:
    std::mt19937_64 _prng;

    size_t _max_tree_depth;
    float _min_fill;
    float _min_fill_decay_per_level;
    size_t _min_new_nodes;
    float _revisit_share;

    uint32_t _move_count;

    std::unique_ptr<MoveNode> _cache;

public:
    AnalyzeResult actuate(const RawBoard &current_board);
    AnalyzeResult analyze(std::unique_ptr<GameBoard> &&current_board);
    void deep_analyze(MoveNode *move_node,
                      size_t depth);

};

namespace std {

std::ostream &operator<<(std::ostream &s, const GameBoard &board);

}
