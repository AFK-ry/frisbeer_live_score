from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from domain.models import Game
import ui.text as uitxt


def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(uitxt.NEW_GAME, callback_data="new_game")],
            [InlineKeyboardButton(uitxt.GAME_LIST, callback_data="game_list")],
            [InlineKeyboardButton(uitxt.LEGEND, callback_data="legend")],
            [InlineKeyboardButton(uitxt.ABOUT, callback_data="about")],
        ]
    )


def game_list_keyboard(games: list[Game]):
    gamelist = []
    if games:
        sorted_games = sorted(games, key=lambda x: x[1], reverse=True)
        for game in sorted_games:
            gid, _, t1_name, t1_emoji, t2_name, t2_emoji = game
            gamelist.append(
                [
                    InlineKeyboardButton(
                        f"{t1_emoji} {t1_name} vs. {t2_name} {t2_emoji}",
                        callback_data=f"game_info:{gid}",
                    )
                ]
            )

    gamelist.append([InlineKeyboardButton(uitxt.BACK, callback_data="main")])
    return InlineKeyboardMarkup(gamelist)


def back_to_main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(uitxt.BACK_TO_MAIN_MENU, callback_data="main")]]
    )


def cancel_team_creation_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(uitxt.CANCEL_GAME_CREATION, callback_data="cancel")]]
    )


def finalize_team_creation_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(uitxt.CREATED_GAMES_LIST, callback_data="game_list")],
            [InlineKeyboardButton(uitxt.BACK_TO_MAIN_MENU, callback_data="main")],
        ]
    )


def game_info_start_keyboard(game_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    uitxt.START_GAME, callback_data=f"start_game:{game_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    uitxt.DELETE_GAME, callback_data=f"confirm_del:{game_id}"
                )
            ],
            [InlineKeyboardButton(uitxt.BACK, callback_data="game_list")],
        ]
    )


def game_info_continue_keyboard(
    game_id: str, result_string: str, round_n: int
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    uitxt.CONTINUE_GAME,
                    callback_data=f"start_round:{game_id}:{round_n}",
                )
            ],
            [
                InlineKeyboardButton(
                    uitxt.UNDO_ROUND_WIN, callback_data=f"undo:{game_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    f"End game ({result_string})",
                    callback_data=f"confirm_end_game:{game_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    uitxt.DELETE_GAME, callback_data=f"confirm_del:{game_id}"
                )
            ],
            [InlineKeyboardButton(uitxt.BACK_TO_GAME_LIST, callback_data="game_list")],
        ]
    )


def confirm_delete_keyboard(game_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(uitxt.CONFIRM, callback_data=f"del_game:{game_id}")],
            [InlineKeyboardButton(uitxt.CANCEL, callback_data=f"game_info:{game_id}")],
        ]
    )


def delete_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(uitxt.BACK, callback_data="game_list")]]
    )


def confirm_end_keyboard(game_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(uitxt.CONFIRM, callback_data=f"end_game:{game_id}")],
            [InlineKeyboardButton(uitxt.CANCEL, callback_data=f"game_info:{game_id}")],
        ]
    )
