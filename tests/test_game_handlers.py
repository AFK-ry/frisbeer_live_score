import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from telegram.error import BadRequest

from domain.actions import EndRound, StartGame, StartRound, SwitchSides
from domain.engine import initial_state
from handlers.callback_data import CallbackData
from handlers.context import Ctx
from handlers import game as game_handlers
from tests.helpers import make_game


def original(decorated):
    """Return the handler captured by the project's context decorator."""
    return decorated.__closure__[0].cell_contents


def make_ctx(history=None, action="live_game", **data_fields):
    game = make_game([StartGame()] if history is None else history)
    query = SimpleNamespace(
        data=f"{action}:game-1",
        answer=AsyncMock(),
        edit_message_text=AsyncMock(),
    )
    storage = SimpleNamespace(save=Mock(), delete=Mock(), load=Mock(return_value=game))
    broadcaster = SimpleNamespace(
        send=AsyncMock(return_value=SimpleNamespace(message_id=99)), delete=AsyncMock()
    )
    context = SimpleNamespace(
        user_data={}, application=SimpleNamespace(bot_data={"storage": storage})
    )
    data = CallbackData(action=action, gid="game-1", **data_fields)
    return Ctx(
        update=SimpleNamespace(callback_query=query), context=context, data=data,
        game=game, storage=storage, broadcaster=broadcaster,
        user=SimpleNamespace(id=1, username="tester", first_name="T", last_name="U"),
    )


class GameHandlerTests(unittest.IsolatedAsyncioTestCase):
    async def test_game_info_wrapper_body_and_both_views(self):
        ctx = make_ctx(history=[])
        with patch("handlers.game.show_game_info", AsyncMock()) as show:
            await original(game_handlers.game_info)(ctx)
            show.assert_awaited_once_with(ctx)
        await game_handlers.show_game_info(ctx)
        ctx.game.history.append(EndRound("team1"))
        ctx.data.round_n = "2"
        await game_handlers.show_game_info(ctx)

    async def test_start_game(self):
        ctx = make_ctx(history=[])
        with patch("handlers.game.show_live_game", AsyncMock()) as show:
            await original(game_handlers.start_game)(ctx)
        self.assertIsInstance(ctx.game.history[0], StartGame)
        self.assertEqual(ctx.game.history[0].message_ids, [99, 99])
        ctx.storage.save.assert_called_once()
        show.assert_awaited_once()

    async def test_confirm_and_delete(self):
        ctx = make_ctx()
        await original(game_handlers.confirm_delete)(ctx)
        await original(game_handlers.delete_game)(ctx)
        ctx.storage.delete.assert_called_once_with("game-1")

    async def test_live_game_delegates(self):
        ctx = make_ctx()
        with patch("handlers.game.show_live_game", AsyncMock()) as show:
            await original(game_handlers.live_game)(ctx)
        show.assert_awaited_once_with(ctx)

    async def test_show_live_game_success_and_ignored_bad_request(self):
        ctx = make_ctx()
        ctx.context.user_data = {"marked": {"game-1": {("team1", 0): "k"}}}
        await game_handlers.show_live_game(ctx)
        ctx.update.callback_query.edit_message_text.side_effect = BadRequest("Message is not modified")
        await game_handlers.show_live_game(ctx)

    async def test_show_live_game_reraises_other_bad_request(self):
        ctx = make_ctx()
        ctx.update.callback_query.edit_message_text.side_effect = BadRequest("broken")
        with self.assertRaises(BadRequest):
            await game_handlers.show_live_game(ctx)

    async def test_mark_beer_cycles_and_ignores_removed_slot(self):
        ctx = make_ctx(action="mark")
        ctx.update.callback_query.data = "mark:game-1:team1:0"
        with patch("handlers.game.show_live_game", AsyncMock()):
            await original(game_handlers.mark_beer)(ctx)
            self.assertEqual(ctx.context.user_data["marked"]["game-1"][("team1", 0)], "k")
            ctx.context.user_data["marked"]["game-1"][("team1", 0)] = "f"
            await original(game_handlers.mark_beer)(ctx)
            self.assertNotIn(("team1", 0), ctx.context.user_data["marked"]["game-1"])

        state = initial_state()
        state.team1_beers[0] = " "
        with patch("handlers.game.compute_state", return_value=state):
            await original(game_handlers.mark_beer)(ctx)

    async def test_switch_and_refresh(self):
        ctx = make_ctx()
        with patch("handlers.game.show_live_game", AsyncMock()) as show:
            await original(game_handlers.switch_sides)(ctx)
            await original(game_handlers.refresh)(ctx)
        self.assertIsInstance(ctx.game.history[-1], SwitchSides)
        self.assertEqual(show.await_count, 2)

    async def test_assign_knocks_empty_and_success(self):
        ctx = make_ctx(action="assign", team="team1", player="Alice")
        await original(game_handlers.assign_knocks)(ctx)
        ctx.context.user_data = {"marked": {"game-1": {("team2", 0): "k"}}}
        with patch("handlers.game.show_live_game", AsyncMock()):
            await original(game_handlers.assign_knocks)(ctx)
        self.assertEqual(ctx.game.history[-1].player, "Alice")

    async def test_undo_empty_start_and_regular_actions(self):
        empty = make_ctx(history=[])
        await original(game_handlers.undo)(empty)

        start = make_ctx(history=[StartRound(1, message_ids=[7])])
        with patch("handlers.game.show_game_info", AsyncMock()) as info:
            await original(game_handlers.undo)(start)
            info.assert_awaited_once()

        regular = make_ctx(history=[SwitchSides(message_ids=[8])])
        with patch("handlers.game.show_live_game", AsyncMock()) as live:
            await original(game_handlers.undo)(regular)
            live.assert_awaited_once()
        regular.broadcaster.delete.assert_awaited_once_with(8)

    async def test_end_and_start_round(self):
        ctx = make_ctx(winner="team1")
        with patch("handlers.game.show_game_info", AsyncMock()):
            await original(game_handlers.end_round)(ctx)
        self.assertIsInstance(ctx.game.history[-1], EndRound)

        ctx.context.user_data = {"marked": {"game-1": {}}}
        with patch("handlers.game.show_live_game", AsyncMock()):
            await original(game_handlers.start_round)(ctx)
        self.assertIsInstance(ctx.game.history[-1], StartRound)

        ctx.context.user_data = {}
        with patch("handlers.game.show_live_game", AsyncMock()):
            await original(game_handlers.start_round)(ctx)

    async def test_confirm_end_game_all_results(self):
        for history in ([EndRound("team1")], [EndRound("team2")], [EndRound("team1"), EndRound("team2")]):
            await original(game_handlers.confirm_end_game)(make_ctx(history=history))

    async def test_end_game(self):
        ctx = make_ctx(history=[EndRound("team1")])
        await original(game_handlers.end_game)(ctx)
        ctx.storage.delete.assert_called_once_with("game-1")


if __name__ == "__main__":
    unittest.main()
