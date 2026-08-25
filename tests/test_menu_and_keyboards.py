import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from handlers import menu
from ui import keyboards
from tests.helpers import make_game


def callback_update():
    return SimpleNamespace(
        callback_query=SimpleNamespace(answer=AsyncMock(), edit_message_text=AsyncMock()),
        effective_user=SimpleNamespace(id=1, username="tester", first_name="Test", last_name="User"),
    )


class KeyboardTests(unittest.TestCase):
    def test_all_keyboard_factories(self):
        factories = [
            keyboards.main_menu_keyboard,
            keyboards.back_to_main_keyboard,
            keyboards.cancel_team_creation_keyboard,
            keyboards.finalize_team_creation_keyboard,
            lambda: keyboards.game_info_start_keyboard("g"),
            lambda: keyboards.game_info_continue_keyboard("g", "B wins", 2),
            lambda: keyboards.confirm_delete_keyboard("g"),
            keyboards.delete_keyboard,
            lambda: keyboards.confirm_end_keyboard("g"),
        ]
        for factory in factories:
            self.assertTrue(factory().inline_keyboard)

    def test_game_list_empty_and_sorted(self):
        self.assertEqual(keyboards.game_list_keyboard([]).inline_keyboard[-1][0].callback_data, "main")
        rows = [("old", 1, "A", "a", "B", "b"), ("new", 2, "C", "c", "D", "d")]
        markup = keyboards.game_list_keyboard(rows)
        self.assertEqual(markup.inline_keyboard[0][0].callback_data, "game_info:new")


class MenuTests(unittest.IsolatedAsyncioTestCase):
    async def test_new_game_and_about(self):
        update = callback_update()
        context = SimpleNamespace(user_data={})
        with patch("handlers.menu.uuid.uuid4", return_value="12345678-rest"):
            await menu.new_game(update, context)
        self.assertEqual(context.user_data["create_game"]["game_id"], "12345678")
        await menu.about(update, context)

    async def test_main_menu_callback_and_start_delegation(self):
        update = callback_update()
        await menu.main_menu(update, None)
        with patch("handlers.menu.main_menu", AsyncMock()) as mocked:
            await menu.start(update, SimpleNamespace())
            mocked.assert_awaited_once()

    async def test_main_menu_message_update(self):
        class FakeUpdate:
            pass

        update = FakeUpdate()
        update.message = SimpleNamespace(reply_text=AsyncMock())
        update.callback_query = None
        with patch("handlers.menu.Update", FakeUpdate):
            await menu.main_menu(update, None)
        update.message.reply_text.assert_awaited_once()

    async def test_cancel_with_and_without_state(self):
        for user_data in ({"create_game": {}}, {}):
            update = callback_update()
            with patch("handlers.menu.main_menu", AsyncMock()) as mocked:
                await menu.cancel_game_creation(update, SimpleNamespace(user_data=user_data))
                mocked.assert_awaited_once()

    async def test_handle_message_validation_errors(self):
        cases = [
            "one,two",
            "aa,bb,cc,x",
            "aa,bb,cc,Valid,toolong",
            "x,bb,cc",
            "aa,bb,cc,x,ok",
        ]
        for text in cases:
            update = SimpleNamespace(message=SimpleNamespace(text=text, reply_text=AsyncMock()))
            context = SimpleNamespace(user_data={"create_game": {"stage": 1}})
            await menu.handle_message(update, context)
            update.message.reply_text.assert_awaited_once()

    async def test_handle_message_ignores_false_state(self):
        update = SimpleNamespace(message=SimpleNamespace(text="aa,bb,cc", reply_text=AsyncMock()))
        await menu.handle_message(update, SimpleNamespace(user_data={"create_game": {}}))
        update.message.reply_text.assert_not_awaited()

    async def test_two_stage_game_creation_with_defaults_and_custom_values(self):
        storage = SimpleNamespace(save=Mock())
        context = SimpleNamespace(
            user_data={"create_game": {"stage": 1, "game_id": "g", "team1": None, "team2": None}},
            application=SimpleNamespace(bot_data={"storage": storage}),
        )
        first = SimpleNamespace(message=SimpleNamespace(text="Ann,Bob,Cara", reply_text=AsyncMock()))
        await menu.handle_message(first, context)
        self.assertEqual(context.user_data["create_game"]["team1"].name, "Blue team")

        second = SimpleNamespace(
            message=SimpleNamespace(text="Dan,Eve,Finn,Reds,R", reply_text=AsyncMock()),
            effective_user=SimpleNamespace(id=1, username=None, first_name="T", last_name="U"),
        )
        with patch("handlers.menu.time.time", return_value=10):
            await menu.handle_message(second, context)
        storage.save.assert_called_once()
        self.assertNotIn("create_game", context.user_data)

    async def test_stage_two_defaults(self):
        storage = SimpleNamespace(save=Mock())
        context = SimpleNamespace(
            user_data={"create_game": {"stage": 2, "game_id": "g", "team1": make_game().team1, "team2": None}},
            application=SimpleNamespace(bot_data={"storage": storage}),
        )
        update = SimpleNamespace(
            message=SimpleNamespace(text="Dan,Eve,Finn", reply_text=AsyncMock()),
            effective_user=SimpleNamespace(id=1, username="tester", first_name="T", last_name="U"),
        )
        await menu.handle_message(update, context)
        saved = storage.save.call_args.args[0]
        self.assertEqual(saved.team2.name, "Red team")

    async def test_game_list(self):
        update = callback_update()
        storage = SimpleNamespace(list_games=Mock(return_value=[]))
        context = SimpleNamespace(application=SimpleNamespace(bot_data={"storage": storage}))
        await menu.game_list(update, context)
        storage.list_games.assert_called_once()


if __name__ == "__main__":
    unittest.main()
