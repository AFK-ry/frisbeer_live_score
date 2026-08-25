import unittest

from domain.actions import AssignKnocks, EndRound, StartGame, StartRound, SwitchSides
from infrastructure.storage.sqlite import Storage
from tests.helpers import make_game


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.storage = Storage(":memory:")

    def tearDown(self):
        self.storage.conn.close()

    def test_save_and_load_round_trip(self):
        game = make_game(
            [
                StartGame(message_ids=[10]),
                AssignKnocks("team1", "Alice", [("team2", 1, "k")], message_ids=[11]),
                SwitchSides(message_ids=[12]),
                StartRound(2, message_ids=[14]),
                EndRound("team1", message_ids=[13]),
            ]
        )

        self.storage.save(game)
        loaded = self.storage.load(game.id)

        self.assertEqual(loaded.id, game.id)
        self.assertEqual(loaded.team1, game.team1)
        self.assertEqual(loaded.team2, game.team2)
        self.assertEqual(loaded.history[0], game.history[0])
        self.assertEqual(loaded.history[1].knocked_beers, [["team2", 1, "k"]])
        self.assertEqual(loaded.history[2:], game.history[2:])

    def test_save_replaces_existing_game(self):
        game = make_game([StartGame()])
        self.storage.save(game)
        game.team1.name = "Renamed"

        self.storage.save(game)

        self.assertEqual(self.storage.load(game.id).team1.name, "Renamed")
        self.assertEqual(len(self.storage.list_games()), 1)

    def test_load_unknown_game_returns_none(self):
        self.assertIsNone(self.storage.load("missing"))

    def test_list_games_is_newest_first(self):
        older = make_game()
        older.id = "older"
        older.timestamp = 1
        newer = make_game()
        newer.id = "newer"
        newer.timestamp = 2
        self.storage.save(older)
        self.storage.save(newer)

        rows = self.storage.list_games()

        self.assertEqual([row[0] for row in rows], ["newer", "older"])

    def test_delete_removes_only_selected_game(self):
        first = make_game()
        second = make_game()
        second.id = "game-2"
        self.storage.save(first)
        self.storage.save(second)

        self.storage.delete(first.id)

        self.assertIsNone(self.storage.load(first.id))
        self.assertIsNotNone(self.storage.load(second.id))


if __name__ == "__main__":
    unittest.main()
