import unittest
from unittest.mock import patch

from domain.actions import AssignKnocks, EndRound, StartGame, StartRound, SwitchSides
from domain.engine import initial_state
from domain.render import (
    apply_marked_overlay,
    beer_emoji,
    beer_row,
    mark_format_beer,
    render,
    render_confirm_delete_message,
    render_game_info_string,
    render_game_message,
    render_game_start_message,
    render_game_win_message,
    render_result_string,
    render_round_report,
)
from tests.helpers import make_game


class RenderTests(unittest.TestCase):
    def test_beer_helpers(self):
        self.assertEqual(beer_emoji("?"), "?")
        self.assertEqual(beer_row(["b", "?"]), beer_emoji("b") + "?")
        self.assertEqual([mark_format_beer(x) for x in ["b", "k", "f", "u", " ", "?"]], ["k", "f", "b", "k", " ", "?"])

    def test_overlay_copies_state_and_updates_both_teams(self):
        original = initial_state()
        result = apply_marked_overlay(original, {("team1", "0"): "k", ("team2", 1): "f"})
        self.assertEqual(original, initial_state())
        self.assertEqual((result.team1_beers[0], result.team2_beers[1]), ("k", "f"))

    def test_render_builds_normal_and_reversed_keyboards(self):
        game = make_game([StartGame()])
        text, markup = render(game, initial_state())
        self.assertTrue(text.startswith("`"))
        self.assertEqual(markup.inline_keyboard[0][0].callback_data, "assign:game-1:team1:Alice")
        self.assertEqual(markup.inline_keyboard[-1][0].callback_data, "end_round:game-1:team1")

        reversed_state = initial_state()
        reversed_state.reverse = True
        _, reversed_markup = render(game, reversed_state)
        self.assertEqual(reversed_markup.inline_keyboard[0][0].callback_data, "assign:game-1:team2:Dan")

    def test_game_message_for_every_action_type(self):
        cases = [
            StartGame(),
            StartRound(2),
            SwitchSides(),
            AssignKnocks("team1", "Alice", [("team1", 0, "k"), ("team2", 1, "f")]),
            AssignKnocks("team2", "Dan", [("team1", 0, "k")]),
        ]
        for action in cases:
            game = make_game([StartGame(), action])
            with self.subTest(action=type(action).__name__):
                self.assertIn("B-", render_game_message(game, action))

        game = make_game([StartGame(), SwitchSides()])
        self.assertTrue(render_game_message(game).startswith("R-"))

        empty = make_game([])
        with patch("domain.render.compute_state", return_value=initial_state()):
            self.assertIn("B-", render_game_message(empty))

    def test_round_report_for_each_winner(self):
        knock = AssignKnocks("team1", "Alice", [("team2", 0, "k"), ("team1", 0, "k")])
        for winner, name in [("team1", "Blue"), ("team2", "Red")]:
            game = make_game([StartGame(), knock, EndRound(winner)])
            report = render_round_report(game)
            self.assertIn(f"{name} won the round!", report)
            self.assertIn("Alice", report)

    def test_win_and_result_messages_cover_win_loss_and_tie(self):
        histories = [
            ([EndRound("team1")], "Blue won"),
            ([EndRound("team2")], "Red won"),
            ([EndRound("team1"), EndRound("team2")], "Ended in tie"),
        ]
        for history, expected in histories:
            self.assertIn(expected, render_game_win_message(make_game(history)))
        self.assertEqual(render_result_string(2, 1, "B", "R"), "B wins 2-1")
        self.assertEqual(render_result_string(1, 2, "B", "R"), "R wins 2-1")
        self.assertEqual(render_result_string(1, 1, "B", "R"), "Tie B 1-1 R")

    def test_static_game_messages(self):
        game = make_game([EndRound("team1")])
        self.assertIn("*Blue*", render_game_info_string(game))
        self.assertIn("New game starting!", render_game_start_message(game))
        self.assertIn("game-1", render_confirm_delete_message(game))


if __name__ == "__main__":
    unittest.main()
