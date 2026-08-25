import unittest
import os
import runpy
from types import SimpleNamespace
from unittest.mock import Mock, patch

import main
from domain.actions import (
    Action, AssignKnocks, EndRound, StartGame, StartRound, SwitchSides,
    action_from_dict, action_to_dict,
)
from domain.models import Game, Team
from tests.helpers import make_game


class SerializationTests(unittest.TestCase):
    def test_all_actions_round_trip(self):
        actions = [SwitchSides(), AssignKnocks("team1", "A", [("team2", 0, "k")]), StartGame(), StartRound(2), EndRound("team1")]
        for action in actions:
            action.message_ids.append(5)
            restored = action_from_dict(action_to_dict(action))
            self.assertEqual(restored, action)

    def test_invalid_actions_raise(self):
        with self.assertRaises(ValueError):
            action_to_dict(Action())
        with self.assertRaises(ValueError):
            action_from_dict({"type": "Unknown"})

    def test_team_and_game_to_dict(self):
        team = Team("T", "E", ["P"])
        self.assertEqual(Team.from_dict(team.to_dict()), team)
        data = make_game([StartGame()]).to_dict()
        self.assertEqual(data["history"][0]["type"], "StartGame")

    def test_game_from_dict_current_failure_is_detected(self):
        with self.assertRaises(TypeError):
            Game.from_dict(make_game().to_dict())

    def test_game_from_dict_flow_with_mocked_team_parser(self):
        data = make_game().to_dict()
        data["history"] = [{"type": "StartGame", "message_ids": []}, {"bad": True}]
        teams = [Team("A", "a", []), Team("B", "b", [])]
        with patch("domain.models.Team.from_dict", side_effect=teams):
            game = Game.from_dict(data)
        self.assertEqual(len(game.history), 1)


class MainTests(unittest.TestCase):
    def test_register_handlers(self):
        app = SimpleNamespace(add_handler=Mock())
        main.register_handlers(app)
        self.assertEqual(app.add_handler.call_count, len(main.COMMAND_HANDLERS) + len(main.CALLBACK_HANDLERS) + 1)

    def test_setup_infrastructure(self):
        app = SimpleNamespace(bot_data={}, bot=object())
        with patch("main.Storage", return_value="storage"), patch("main.Broadcaster", return_value="broadcaster"):
            main.setup_infrastructure(app, 123)
        self.assertEqual(app.bot_data, {"storage": "storage", "broadcaster": "broadcaster"})

    def test_main_builds_and_runs_application(self):
        app = SimpleNamespace(run_polling=Mock())
        builder = SimpleNamespace(token=Mock(return_value=SimpleNamespace(build=Mock(return_value=app))))
        with patch("main.Application.builder", return_value=builder), patch("main.setup_infrastructure") as setup, patch("main.register_handlers") as register:
            main.main("token", 123)
        setup.assert_called_once_with(app, 123)
        register.assert_called_once_with(app)
        app.run_polling.assert_called_once()

    def test_script_entrypoint(self):
        app = SimpleNamespace(bot_data={}, bot=object(), add_handler=Mock(), run_polling=Mock())
        builder = SimpleNamespace(token=Mock(return_value=SimpleNamespace(build=Mock(return_value=app))))
        real_getenv = os.getenv

        def getenv(name, default=None):
            return {"TOKEN": "token", "BROADCAST_CHAT_ID": "123"}.get(name, real_getenv(name, default))

        with patch("os.getenv", side_effect=getenv), \
             patch("dotenv.load_dotenv"), \
             patch("telegram.ext.Application.builder", return_value=builder), \
             patch("infrastructure.storage.sqlite.Storage", return_value="storage"), \
             patch("infrastructure.telegram.broadcaster.Broadcaster", return_value="broadcaster"):
            runpy.run_path("main.py", run_name="__main__")
        app.run_polling.assert_called_once()


if __name__ == "__main__":
    unittest.main()
