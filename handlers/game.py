from telegram.error import BadRequest
from infrastructure.logging_config import logger
from handlers.decorators import with_context
from handlers.context import Ctx
from domain.actions import SwitchSides, AssignKnocks, StartGame, StartRound, EndRound
from domain.render import (
    render,
    apply_marked_overlay,
    mark_format_beer,
    render_game_message,
    render_round_report,
    render_game_win_message,
    render_result_string,
    render_game_info_string,
    render_game_start_message,
    render_confirm_delete_message,
)
from domain.engine import compute_state, count_round_wins
import ui.text as uitxt
from ui.keyboards import (
    back_to_main_keyboard,
    game_info_start_keyboard,
    game_info_continue_keyboard,
    confirm_delete_keyboard,
    delete_keyboard,
    confirm_end_keyboard,
)


@with_context
async def game_info(ctx: Ctx):
    await show_game_info(ctx)


async def show_game_info(ctx: Ctx):
    t1_score, t2_score = count_round_wins(ctx.game.history)
    if t1_score + t2_score == 0:  # Game not yet started
        keyboard = game_info_start_keyboard(ctx.game.id)
    else:
        result_string = render_result_string(
            t1_score, t2_score, ctx.game.team1.emoji, ctx.game.team2.emoji
        )
        keyboard = game_info_continue_keyboard(
            ctx.data.gid, result_string, ctx.data.round_n
        )

    reply = render_game_info_string(ctx.game)
    await ctx.update.callback_query.answer()
    await ctx.update.callback_query.edit_message_text(
        reply, reply_markup=keyboard, parse_mode="HTML"
    )


@with_context
async def start_game(ctx: Ctx):
    ctx.game.history.append(StartGame())

    game_start_msg = render_game_start_message(ctx.game)
    msg = await ctx.broadcaster.send(game_start_msg)
    ctx.game.history[-1].message_ids.append(msg.message_id)

    first_round_msg = render_game_message(ctx.game, StartRound(1))
    msg = await ctx.broadcaster.send(first_round_msg)
    ctx.game.history[-1].message_ids.append(msg.message_id)

    ctx.storage.save(ctx.game)
    logger.info(
        "User: %s | Started Game | gid=%s %s vs. %s",
        ctx.user_str,
        ctx.game.id,
        ctx.game.team1.name,
        ctx.game.team2.name,
    )

    await ctx.update.callback_query.answer()
    await show_live_game(ctx)


@with_context
async def confirm_delete(ctx: Ctx):
    reply = render_confirm_delete_message(ctx.game)
    await ctx.update.callback_query.answer()
    await ctx.update.callback_query.edit_message_text(
        reply, parse_mode="HTML", reply_markup=confirm_delete_keyboard(ctx.data.gid)
    )


@with_context
async def delete_game(ctx: Ctx):
    ctx.storage.delete(ctx.data.gid)
    logger.info(
        "User: %s | Deleted Game | gid=%s %s vs. %s",
        ctx.user_str,
        ctx.game.id,
        ctx.game.team1.name,
        ctx.game.team2.name,
    )
    await ctx.update.callback_query.answer()
    await ctx.update.callback_query.edit_message_text(
        f"Game id {ctx.data.gid} deleted.",
        reply_markup=delete_keyboard(),
        parse_mode="HTML",
    )


@with_context
async def live_game(ctx: Ctx):
    await show_live_game(ctx)


async def show_live_game(ctx: Ctx):
    marked_by_game = ctx.context.user_data.get("marked", {})
    marked = marked_by_game.get(ctx.data.gid, {})

    base_state = compute_state(ctx.game)
    state = apply_marked_overlay(base_state, marked)
    text, keyboard = render(ctx.game, state_override=state)

    await ctx.update.callback_query.answer()
    try:
        await ctx.update.callback_query.edit_message_text(
            text, reply_markup=keyboard, parse_mode="HTML"
        )
    except BadRequest as e:
        if "Message is not modified" in str(e):
            pass  # ignore safely
        else:
            raise


@with_context
async def mark_beer(ctx: Ctx):
    query = ctx.update.callback_query
    gid, team, index = query.data.split(":")[1:]
    storage = ctx.context.application.bot_data["storage"]
    game = storage.load(gid)
    state = compute_state(game)
    beers = getattr(state, f"{team}_beers")
    if beers[int(index)] == " ":
        await query.answer()
        return

    marked_by_game = ctx.context.user_data.setdefault("marked", {})
    marked = marked_by_game.setdefault(gid, {})

    key = (team, int(index))
    current = marked.get(key, "b")
    new = mark_format_beer(current)
    if new == "b":
        del marked[key]
    else:
        marked[key] = new

    await query.answer()
    await show_live_game(ctx)


@with_context
async def switch_sides(ctx: Ctx):
    action = SwitchSides()
    ctx.game.history.append(action)
    message = render_game_message(ctx.game)
    msg = await ctx.broadcaster.send(message)
    ctx.game.history[-1].message_ids.append(msg.message_id)
    ctx.storage.save(ctx.game)
    logger.info("User: %s | Switched Sides | gid=%s", ctx.user_str, ctx.game.id)
    await ctx.update.callback_query.answer()
    await show_live_game(ctx)


@with_context
async def refresh(ctx: Ctx):
    await ctx.update.callback_query.answer(uitxt.REFRESH_NOTIFY)
    await show_live_game(ctx)


@with_context
async def assign_knocks(ctx: Ctx):
    marked_by_game = ctx.context.user_data.get("marked", {})
    marked = marked_by_game.get(ctx.data.gid, {})

    if not marked:
        await ctx.update.callback_query.answer(uitxt.NO_BEERS)
        return

    knocked_beers = [
        (team, index, state_to) for (team, index), state_to in marked.items()
    ]

    action = AssignKnocks(
        team=ctx.data.team, player=ctx.data.player, knocked_beers=knocked_beers
    )
    message = render_game_message(ctx.game, pending_action=action)
    msg = await ctx.broadcaster.send(message)
    action.message_ids.append(msg.message_id)
    ctx.game.history.append(action)
    ctx.storage.save(ctx.game)
    ctx.context.user_data["marked"].pop(ctx.data.gid, None)
    logger.info(
        "User: %s | Assigned Knocks | gid=%s team=%s player=%s n_knocks=%s",
        ctx.user_str,
        ctx.game.id,
        ctx.data.team,
        ctx.data.player,
        str(knocked_beers),
    )
    await ctx.update.callback_query.answer()
    await show_live_game(ctx)


@with_context
async def undo(ctx: Ctx):
    history = ctx.game.history
    if len(history) == 0:
        await ctx.update.callback_query.answer()
        return
    last_action = history.pop()
    for m_id in last_action.message_ids:
        await ctx.broadcaster.delete(m_id)
    ctx.storage.save(ctx.game)
    logger.info(
        "User: %s | Undid last action | gid=%s last_action=%s",
        ctx.user_str,
        ctx.game.id,
        str(last_action),
    )
    await ctx.update.callback_query.answer()
    if isinstance(last_action, (StartGame, StartRound)):
        await show_game_info(ctx)
    else:
        await show_live_game(ctx)


@with_context
async def end_round(ctx: Ctx):
    ctx.game.history.append(EndRound(ctx.data.winner))
    message = render_round_report(ctx.game)
    msg = await ctx.broadcaster.send(message)
    ctx.game.history[-1].message_ids.append(msg.message_id)
    ctx.storage.save(ctx.game)
    logger.info(
        "User: %s | Ended round | gid=%s winner=%s",
        ctx.user_str,
        ctx.game.id,
        ctx.data.winner,
    )
    await ctx.update.callback_query.answer()
    await show_game_info(ctx)


@with_context
async def start_round(ctx: Ctx):
    n_rounds = len([g for g in ctx.game.history if isinstance(g, EndRound)])
    ctx.game.history.append(StartRound(round_n=n_rounds + 1))
    message = render_game_message(ctx.game)
    msg = await ctx.broadcaster.send(message)
    ctx.game.history[-1].message_ids.append(msg.message_id)
    ctx.storage.save(ctx.game)
    logger.info(
        "User: %s | Started round | gid=%s round_n=%s",
        ctx.user_str,
        ctx.game.id,
        str(n_rounds + 1),
    )
    try:
        ctx.context.user_data["marked"].pop(ctx.data.gid, None)
    except KeyError:
        pass
    await ctx.update.callback_query.answer()
    await show_live_game(ctx)


@with_context
async def confirm_end_game(ctx: Ctx):
    round_results = [a for a in ctx.game.history if isinstance(a, EndRound)]
    t1_score = len([round for round in round_results if round.winner == "team1"])
    t2_score = len([round for round in round_results if round.winner == "team2"])
    reply = "<b>Really end game?</b>\n\n"
    if t1_score > t2_score:
        reply += f"{ctx.game.team1.emoji} <b>{ctx.game.team1.name}</b> wins {t1_score} - {t2_score}\n"
    elif t2_score > t1_score:
        reply += f"{ctx.game.team2.emoji} <b>{ctx.game.team2.name}</b> wins {t2_score} - {t1_score}\n"
    else:
        reply += f"Tie {ctx.game.team1.emoji} <b>{ctx.game.team1.name}</b> {t1_score} - {t2_score} <b>{ctx.game.team2.name}</b> {ctx.game.team2.emoji}"
    keyboard = confirm_end_keyboard(ctx.data.gid)
    await ctx.update.callback_query.answer()
    await ctx.update.callback_query.edit_message_text(
        reply, reply_markup=keyboard, parse_mode="HTML"
    )


@with_context
async def end_game(ctx: Ctx):
    message = render_game_win_message(ctx.game)
    msg = await ctx.broadcaster.send(message)
    ctx.game.history[-1].message_ids.append(msg.message_id)
    keyboard = back_to_main_keyboard()
    ctx.storage.delete(ctx.data.gid)
    logger.info("User: %s | Ended game | gid=%s", ctx.user_str, ctx.game.id)
    await ctx.update.callback_query.answer()
    await ctx.update.callback_query.edit_message_text(
        message, reply_markup=keyboard, parse_mode="HTML"
    )
