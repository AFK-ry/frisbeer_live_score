import uuid
import time
from telegram import Update
from telegram.ext import CallbackContext
from wcwidth import wcswidth
from infrastructure.logging_config import logger
from domain.models import Team, Game
from ui.keyboards import (
    main_menu_keyboard,
    cancel_team_creation_keyboard,
    finalize_team_creation_keyboard,
    back_to_main_keyboard,
    game_list_keyboard,
)
import ui.text as uitxt


async def start(update: Update, context: CallbackContext):
    await main_menu(update, context)


async def main_menu(update: Update, _: CallbackContext):
    if isinstance(update, Update) and update.message:
        await update.message.reply_text(
            uitxt.WELCOME, reply_markup=main_menu_keyboard()
        )
    elif update.callback_query:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(uitxt.WELCOME, reply_markup=main_menu_keyboard())


async def new_game(update: Update, context: CallbackContext):
    gid = str(uuid.uuid4())[:8]
    context.user_data["create_game"] = {
        "stage": 1,
        "game_id": gid,
        "team1": None,
        "team2": None,
    }
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        uitxt.TEAM1_PROMPT,
        parse_mode="HTML",
        reply_markup=cancel_team_creation_keyboard(),
    )


async def cancel_game_creation(update: Update, context: CallbackContext):
    try:
        del context.user_data["create_game"]
    except KeyError:
        pass  # if create game not exist, continue
    await update.callback_query.answer()
    await main_menu(update, context)


async def handle_message(update: Update, context: CallbackContext):
    state = context.user_data["create_game"]
    if not state:
        return  # ignore if hasn't started game creation process

    cancel_markup = cancel_team_creation_keyboard()

    stage = state["stage"]
    text = update.message.text.strip()
    parts = text.split(",")

    if len(parts) not in range(3, 6):
        await update.message.reply_text(
            uitxt.NUM_VALUES_ERROR, parse_mode="HTML", reply_markup=cancel_markup
        )
        return

    if len(parts) == 3:
        p1, p2, p3 = [part.strip() for part in parts]
        team_name = None
        team_emoji = None
    elif len(parts) == 4:
        p1, p2, p3, team_name = [part.strip() for part in parts]
        team_emoji = None
        if len(team_name) not in range(2, 21):
            await update.message.reply_text(
                uitxt.TEAM_NAME_LEN_ERROR,
                parse_mode="HTML",
                reply_markup=cancel_markup,
            )
            return
    else:
        p1, p2, p3, team_name, team_emoji = [part.strip() for part in parts]
        if len(team_name) not in range(2, 21):
            await update.message.reply_text(
                uitxt.TEAM_NAME_LEN_ERROR,
                parse_mode="HTML",
                reply_markup=cancel_markup,
            )
            return
        if wcswidth(team_emoji) > 3:
            await update.message.reply_text(
                uitxt.TEAM_EMOJI_LEN_ERROR,
                parse_mode="HTML",
                reply_markup=cancel_markup,
            )
            return
    if (
        len(p1) not in range(2, 21)
        or len(p2) not in range(2, 21)
        or len(p3) not in range(2, 21)
    ):
        await update.message.reply_text(
            uitxt.PLAYER_NAME_LEN_ERROR,
            parse_mode="HTML",
            reply_markup=cancel_markup,
        )
        return

    if stage == 1:
        if team_name is None:
            team_name = "Blue team"
        if team_emoji is None:
            team_emoji = "🔵"
        state["team1"] = Team(name=team_name, emoji=team_emoji, players=[p1, p2, p3])
        state["stage"] = 2
        await update.message.reply_text(
            f"✅ Team 1 set as <b>{team_name}</B> {team_emoji}!"
            + "\n"
            + uitxt.TEAM2_PROMPT,
            parse_mode="HTML",
            reply_markup=cancel_markup,
        )
        return

    if stage == 2:
        if team_name is None:
            team_name = "Red team"
        if team_emoji is None:
            team_emoji = "🔴"
        state["team2"] = Team(name=team_name, emoji=team_emoji, players=[p1, p2, p3])

        game = Game(
            id=state["game_id"],
            timestamp=time.time(),
            team1=state["team1"],
            team2=state["team2"],
        )

        storage = context.application.bot_data["storage"]
        storage.save(game)

        user = update.effective_user

        del context.user_data["create_game"]
        logger.info(
            "User: %s | Created game | gid=%s %s vs. %s",
            f"{user.id} {user.username if user.username else user.first_name + ' ' + user.last_name}",
            game.id,
            game.team1.name,
            game.team2.name,
        )
        await update.message.reply_text(
            f"✅ Team 2 set as <b>{team_name}</b> {team_emoji}!"
            + "\n"
            + uitxt.CHECK_CREATED_GAME,
            parse_mode="HTML",
            reply_markup=finalize_team_creation_keyboard(),
        )
        return


async def game_list(update: Update, context: CallbackContext):
    storage = context.application.bot_data["storage"]
    games = storage.list_games()
    gamelist = game_list_keyboard(games)
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        uitxt.GAME_LIST_HEADER, reply_markup=gamelist
    )

async def legend(update: Update, _: CallbackContext):
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        uitxt.LEGEND_MESSAGE, reply_markup=back_to_main_keyboard()
    )

async def about(update: Update, _: CallbackContext):
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        uitxt.ABOUT_MESSAGE, reply_markup=back_to_main_keyboard()
    )
