import unittest

from domain.actions import AssignKnocks, EndRound, StartGame, StartRound, SwitchSides
from domain.engine import (
    apply_action,
    assign_format_beer,
    compute_state,
    count_player_knocks,
    count_round_wins,
    get_current_round_knocks,
    initial_state,
)
from tests.helpers import make_game


class EngineTests(unittest.TestCase):
    def test_initial_state_has_eight_beers_per_team(self):
        state = initial_state()

        self.assertEqual(state.team1_beers, ["b"] * 8)
        self.assertEqual(state.team2_beers, ["b"] * 8)
        self.assertFalse(state.reverse)

    def test_assign_format_converts_marked_states(self):
        expected = {"b": "b", "k": " ", "f": "u", "u": "u", " ": " "}

        for source, result in expected.items():
            with self.subTest(source=source):
                self.assertEqual(assign_format_beer(source), result)

    def test_apply_action_assigns_knocks_and_flips_sides(self):
        state = initial_state()
        action = AssignKnocks(
            team="team1",
            player="Alice",
            knocked_beers=[("team2", 2, "k"), ("team1", 4, "f")],
        )

        state = apply_action(state, action)
        state = apply_action(state, SwitchSides())

        self.assertEqual(state.team2_beers[2], " ")
        self.assertEqual(state.team1_beers[4], "u")
        self.assertTrue(state.reverse)

    def test_end_round_resets_beers_and_side_order(self):
        state = initial_state()
        state.team1_beers[0] = " "
        state.reverse = True

        result = apply_action(state, EndRound("team1"))

        self.assertEqual(result, initial_state())

    def test_compute_state_uses_only_latest_round(self):
        game = make_game(
            [
                StartGame(),
                AssignKnocks("team1", "Alice", [("team2", 0, "k")]),
                EndRound("team1"),
                StartRound(2),
                AssignKnocks("team2", "Dan", [("team1", 3, "k")]),
            ]
        )

        state = compute_state(game)

        self.assertEqual(state.team2_beers, ["b"] * 8)
        self.assertEqual(state.team1_beers[3], " ")

    def test_current_round_knocks_stop_at_round_end(self):
        first = AssignKnocks("team1", "Alice", [("team2", 0, "k")])
        after_end = AssignKnocks("team2", "Dan", [("team1", 0, "k")])
        actions = [StartGame(), first, EndRound("team1"), after_end]

        self.assertEqual(get_current_round_knocks(actions), [first])
        self.assertEqual(get_current_round_knocks([first]), [])
        self.assertEqual(get_current_round_knocks([StartGame(), first]), [first])

    def test_count_player_knocks_separates_opponent_and_self_knocks(self):
        game = make_game([StartGame()])
        actions = [
            AssignKnocks(
                "team1",
                "Alice",
                [("team2", 0, "k"), ("team2", 1, "f"), ("team1", 0, "k")],
            )
        ]

        results = count_player_knocks(game, actions)

        self.assertEqual(results["team1"]["Alice"], [1, 1])
        self.assertEqual(results["team2"]["Dan"], [0, 0])

    def test_count_round_wins_ignores_other_actions(self):
        actions = [StartGame(), EndRound("team1"), StartRound(2), EndRound("team2"), EndRound("team1")]

        self.assertEqual(count_round_wins(actions), (2, 1))


if __name__ == "__main__":
    unittest.main()
