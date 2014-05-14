import copy
import multiprocessing
import logging
import random
import time

import g2048.logic as logic

prng = random.Random()
prng.seed(random.SystemRandom().getrandbits(128))

GAME_OVER_REWARD = -100
MERGE_REWARD_BASE = 1.5

logger = logging.getLogger(__name__)

class RandomNode:
    def __init__(self, weight, result_board):
        self.result_board = result_board
        self.weight = weight
        self.children = {}
        self.reward = 0
        self.is_game_over = False

    def find_best_move(self):
        scores = [(node.get_score(), move, node)
                  for move, node in self.children.items()]
        scores.sort(key=lambda x: x[0])
        try:
            return scores.pop()
        except IndexError:
            return (None, None, None)

    def get_move_node(self, move):
        return self.children.get(move, None)

    def new_child(self, move):
        try:
            return self.children[move]
        except KeyError:
            actions = []
            new_board = self.result_board.shifted(move, actions=actions)
            if actions:
                new_node = MoveNode(move, new_board, actions)
            else:
                return None
            self.children[move] = new_node
            return new_node

    def _iter_sparsity(self):
        for child in self.children.values():
            yield from child._iter_sparsity()

    def calc_sparsity_stats(self):
        iter_sparsity = iter(self._iter_sparsity())
        try:
            first = next(iter_sparsity)
        except StopIteration:
            return float("nan"), float("nan"), float("nan")
        minv, maxv, vsum, count = first, first, first, 1
        for sparsity in iter_sparsity:
            minv = min(sparsity, minv)
            maxv = max(sparsity, maxv)
            vsum += sparsity
            count += 1

        return minv, vsum/count, maxv

class MoveNode:
    def __init__(self, move, result_board, actions):
        self.result_board = result_board
        transposed = self.result_board.board.transpose()
        self.move = move
        self.children = []
        self.reward = sum(MERGE_REWARD_BASE**(transposed[p2])
                          for action, p1, p2 in actions
                          if action == "merge")
        self.max_children = len(list(self.result_board.free_fields())) * 2

        self.original_free_tiles = list(result_board.free_fields())
        self.options2 = list(self.original_free_tiles)
        self.options4 = list(self.original_free_tiles)

    def get_node_by_board(self, board):
        for child in self.children:
            if child.result_board == board:
                return child
        return None

    def get_score(self):
        scores = [(score, child.weight)
                  for (score, _, _), child in ((child.find_best_move(), child)
                                               for child in self.children)
		  if score is not None]
        total_weight = sum(weight
                           for _, weight in scores)
        score = self.reward + sum(
            child_score * weight / total_weight
            for child_score, weight in scores)

        return score

    def new_child(self, probability, new_board):
        # if self.get_node_by_board(new_board) is not None:
        #     raise ValueError("Board already there")
        new_node = RandomNode(probability, new_board)
        self.children.append(new_node)
        return new_node

    def _iter_sparsity(self):
        yield self.sparsity
        for child in self.children:
            yield from child._iter_sparsity()

    @property
    def sparsity(self):
        return (self.max_children - len(self.children)) / self.max_children

class AI:
    def __init__(self,
                 max_tree_depth=2,
                 min_fill=0.99,
                 min_fill_decay=90,
                 min_new_nodes=1,
                 max_new_nodes=6,
                 revisit_share=0.26):
        self.max_tree_depth = max_tree_depth
        self.min_fill = min_fill
        self.min_fill_decay = min_fill_decay
        self.min_new_nodes = min_new_nodes
        self.max_new_nodes = max_new_nodes
        self.revisit_share = revisit_share
        self._cache = None

    def actuate(self, game):
        if game.game_over:
            game.new_game()
            self.clear_cache()
            return

        start_time = time.time()
        score, move, node = self.analyze(game.board)
        self._cache = node
        logger.info("analyze took %f seconds",
                     time.time() - start_time)
        if move is None:
            logger.warn("out of valid moves :(")
        else:
            return move

    def deep_analyze(self, move_node, depth=0, pool=None):
        if depth > self.max_tree_depth:
            return

        min_fill = self.min_fill**(depth*self.min_fill_decay)

        options2 = move_node.options2
        options4 = move_node.options4

        tiles_to_visit = round(move_node.max_children*min_fill)

        nodes_to_revisit = min(len(move_node.children),
                               round(tiles_to_visit*self.revisit_share))

        tiles_to_take = min(max(tiles_to_visit-nodes_to_revisit,
                                self.min_new_nodes),
                            self.max_new_nodes,
                            len(options2)+len(options4))

        # for existing in prng.sample(move_node.children, nodes_to_revisit):
        #     for subchild_node in existing.children.values():
        #         self.deep_analyze(subchild_node, depth=depth+1)

        result_board = move_node.result_board
        randint = prng.randint
        random = prng.random
        PROBABILITY4 = logic.PROBABILITY4
        PROBABILITY2 = logic.PROBABILITY2
        new_child = move_node.new_child

        for i in range(tiles_to_take):
            if options2 and options4:
                tile = 2 if random() > PROBABILITY4 else 4
                options = options2 if tile == 2 else options4
            elif options2:
                tile = 2
                options = options2
            elif options4:
                tile = 4
                options = options4
            else:
                raise AssertionError("This is unexpected")

            idx = randint(0, len(options)-1)
            option = options[idx]
            del options[idx]

            new_board = result_board.with_tile_placed(
                option[1], option[0], tile)
            probability = PROBABILITY4 if tile == 2 else PROBABILITY2

            # try:
            child_node = new_child(probability, new_board)
            # except ValueError as err:
            #     raise ValueError(str(err),
            #                      "\n".join(
            #                          str(node.board) for node in self.children),
            #                      str(new_board),
            #                      " ".join(map(repr, free_tiles)),
            #                      " ".join(map(repr, options2)),
            #                      " ".join(map(repr, options4))) from None

            for possible_move in logic.VALID_DIRECTIONS:
                subchild_node = child_node.new_child(possible_move)
                if subchild_node is not None:
                    self.deep_analyze(subchild_node, depth=depth+1)
            if not child_node.children:
                child_node.reward = GAME_OVER_REWARD


    def analyze(self, board):
        root_node = None
        if self._cache is not None:
            root_node = self._cache.get_node_by_board(board)

        if root_node is None:
            root_node = RandomNode(1.0, board)
            logger.info("cache miss")
        else:
            logger.info("cache hit")
        root_node.weight = 1.0

        # with multiprocessing.Pool(6) as pool:
        for possible_move in logic.VALID_DIRECTIONS:
            node = root_node.new_child(possible_move)
            if node is not None:
                self.deep_analyze(node, depth=1)

        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("sparsity: min=%f, avg=%f, max=%f",
                         *root_node.calc_sparsity_stats())

        return root_node.find_best_move()

    def clear_cache(self):
        self._cache = None
