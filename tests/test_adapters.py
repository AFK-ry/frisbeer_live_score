import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from handlers.callback_data import CallbackData
from handlers.context import Ctx
from handlers.decorators import with_context
from infrastructure.telegram.broadcaster import Broadcaster
from tests.helpers import make_game


class CallbackDataTests(unittest.TestCase):
    def test_parse_assign_decodes_player_name(self):
        data = CallbackData.parse("assign:g1:team1:Alice%20Smith")

        self.assertEqual(data.action, "assign")
        self.assertEqual(data.gid, "g1")
        self.assertEqual(data.team, "team1")
        self.assertEqual(data.player, "Alice Smith")

    def test_parse_mark_converts_index_to_integer(self):
        data = CallbackData.parse("mark:g1:team2:7")

        self.assertEqual((data.team, data.index), ("team2", 7))

    def test_parse_round_callbacks(self):
        end = CallbackData.parse("end_round:g1:team2")
        start = CallbackData.parse("start_round:g1:3")

        self.assertEqual(end.winner, "team2")
        self.assertEqual(start.round_n, "3")


class BroadcasterTests(unittest.IsolatedAsyncioTestCase):
    async def test_send_targets_channel_with_markdown(self):
        bot = SimpleNamespace(send_message=AsyncMock(return_value="message"))
        broadcaster = Broadcaster(bot, -100123)

        result = await broadcaster.send("score")

        self.assertEqual(result, "message")
        bot.send_message.assert_awaited_once_with(
            chat_id=-100123, text="`score`", parse_mode="Markdown"
        )

    async def test_delete_targets_channel_and_message(self):
        bot = SimpleNamespace(delete_message=AsyncMock())

        await Broadcaster(bot, -100123).delete(42)

        bot.delete_message.assert_awaited_once_with(chat_id=-100123, message_id=42)


class ContextDecoratorTests(unittest.IsolatedAsyncioTestCase):
    async def test_decorator_builds_context_from_update_and_application(self):
        game = make_game([ ])
        storage = SimpleNamespace(load=unittest.mock.Mock(return_value=game))
        broadcaster = object()
        user = SimpleNamespace(id=7, username="tester")
        update = SimpleNamespace(
            callback_query=SimpleNamespace(data="refresh:game-1"),
            effective_user=user,
        )
        telegram_context = SimpleNamespace(
            application=SimpleNamespace(
                bot_data={"storage": storage, "broadcaster": broadcaster}
            )
        )
        received = None

        @with_context
        async def handler(ctx):
            nonlocal received
            received = ctx
            return "done"

        result = await handler(update, telegram_context)

        self.assertEqual(result, "done")
        self.assertIsInstance(received, Ctx)
        self.assertIs(received.game, game)
        self.assertIs(received.broadcaster, broadcaster)
        self.assertIs(received.user, user)
        storage.load.assert_called_once_with("game-1")

    async def test_user_string_without_username(self):
        ctx = Ctx(
            update=None, context=None, data=None, game=None, storage=None,
            broadcaster=None,
            user=SimpleNamespace(id=3, username=None, first_name="First", last_name="Last"),
        )
        self.assertEqual(ctx.user_str, "First Last (3)")


if __name__ == "__main__":
    unittest.main()
