import random

from battleship.engine import ai, domain


def test_target_caller_calls_correct_amount_of_targets():
    board = domain.Board()
    target_caller = ai.TargetCaller(board)

    assert len(target_caller.call_out()) == 1
    assert len(target_caller.call_out(count=5)) == 5


def test_random_algorithm_doesnt_target_shot_cells():
    random.seed(42)
    board = domain.Board(size=2)
    algorithm = ai.RandomAlgorithm()

    board.grid[0][0].hit()
    board.grid[0][1].hit()

    # Request 4 targets, but only 2 cells are not shot yet.
    targets = algorithm.find_next_targets(board, count=4)

    assert targets == [board.grid[1][0], board.grid[1][1]]
