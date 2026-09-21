from copy import deepcopy
from html import escape
from urllib.parse import quote
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import ui.text as uitxt
from domain.engine import (
    compute_state,
    get_current_round_knocks,
    count_player_knocks,
    count_round_wins,
)
from domain.models import Game, GameState
from domain.actions import AssignKnocks, SwitchSides, Action, StartGame, StartRound

MARK_MAP = {"b": "k", "k": "f", "f": "b", "u": "k", " ": " "}

EMOJI_MAP = {"b": "🍺", "k": "💥", "f": "🤯", " ": "🕳️", "u": "🙃"}

NUMBER_MAP = ["2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣"]

ACTION_MAP = {
    AssignKnocks: "{emoji}>{player}",
    SwitchSides: "🤖>Switched sides!",
    StartRound: "🤖>Round {n} started!",
}


def beer_row(beers: list):
    return "".join([EMOJI_MAP.get(beer, beer) for beer in beers])


def beer_emoji(beer: str):
    return EMOJI_MAP.get(beer, beer)


def mark_format_beer(current: str) -> str:
    return MARK_MAP.get(current, current)


def render(
    game: Game, state_override: GameState = None
) -> tuple[str, InlineKeyboardMarkup]:
    state = state_override or compute_state(game)
    gid = game.id
    t1 = game.team1
    t2 = game.team2

    t1_score, t2_score = count_round_wins(game.history)

    message = render_game_message(game)
    reply = f"<code>{escape(message)}</code>"

    t1_name_buttons = [
        InlineKeyboardButton(
            player, callback_data=f"assign:{gid}:team1:{quote(player)}"
        )
        for player in t1.players
    ]
    t1_beer_buttons = [
        InlineKeyboardButton(beer_emoji(x), callback_data=f"mark:{gid}:team1:{i}")
        for i, x in enumerate(state.team1_beers)
    ]
    t2_name_buttons = [
        InlineKeyboardButton(
            player, callback_data=f"assign:{gid}:team2:{quote(player)}"
        )
        for player in t2.players
    ]
    t2_beer_buttons = [
        InlineKeyboardButton(beer_emoji(x), callback_data=f"mark:{gid}:team2:{i}")
        for i, x in enumerate(state.team2_beers)
    ]

    keyboard = []
    if state.reverse:
        keyboard.append(t2_name_buttons)
        keyboard.append(t2_beer_buttons)
    else:
        keyboard.append(t1_name_buttons)
        keyboard.append(t1_beer_buttons)

    keyboard.append(
        [
            InlineKeyboardButton(
                (
                    f"⬆️{game.team1.emoji} Refresh {game.team2.emoji}⬇️"
                    if state.reverse
                    else f"⬆️{game.team1.emoji} Refresh {game.team2.emoji}⬇️"
                ),
                callback_data=f"refresh:{gid}",
            )
        ]
    )

    if state.reverse:
        keyboard.append(t1_beer_buttons)
        keyboard.append(t1_name_buttons)
    else:
        keyboard.append(t2_beer_buttons)
        keyboard.append(t2_name_buttons)

    keyboard.append(
        [
            InlineKeyboardButton(uitxt.UNDO, callback_data=f"undo:{gid}"),
            InlineKeyboardButton(
                uitxt.SWITCH_SIDES, callback_data=f"switch_sides:{gid}"
            ),
        ]
    )

    # win round buttons
    keyboard.append(
        [
            InlineKeyboardButton(
                f"{t1.emoji} wins ({t1_score + 1}-{t2_score})",
                callback_data=f"end_round:{gid}:team1",
            ),
            InlineKeyboardButton(
                f"{t2.emoji} wins ({t1_score}-{t2_score + 1})",
                callback_data=f"end_round:{gid}:team2",
            ),
        ]
    )

    return reply, InlineKeyboardMarkup(keyboard)


def apply_marked_overlay(state: GameState, marked: list[tuple[str, int]]):
    state = deepcopy(state)

    for (team, index), to in marked.items():
        index = int(index)
        if team == "team1":
            state.team1_beers[index] = to
        else:
            state.team2_beers[index] = to
    return state


def render_game_message(game: Game, pending_action: Action | None = None):
    state = compute_state(game)
    t1 = game.team1
    t2 = game.team2
    if pending_action:
        latest_action = pending_action
    elif game.history:
        latest_action = game.history[-1]
    else:
        latest_action = "Game started!"

    # Construct strings based on last game action
    mid_string = ""
    if isinstance(latest_action, AssignKnocks):
        team = latest_action.team
        if team == "team1":
            emoji = game.team1.emoji
        else:
            emoji = game.team2.emoji
        player = latest_action.player
        mid_string += ACTION_MAP[AssignKnocks].format(emoji=emoji, player=player)
        t1_raw_row = deepcopy(state.team1_beers)
        t2_raw_row = deepcopy(state.team2_beers)
        for knock in latest_action.knocked_beers:
            team, index, to = knock
            if team == "team1":
                t1_raw_row[index] = to
            else:
                t2_raw_row[index] = to
        t1_string = f"{t1.emoji}-{beer_row(t1_raw_row)}\n"
        t2_string = f"{t2.emoji}-{beer_row(t2_raw_row)}\n"
    elif isinstance(latest_action, SwitchSides):
        mid_string += ACTION_MAP[SwitchSides]
        t1_string = f"{t1.emoji}-{beer_row(state.team1_beers)}\n"
        t2_string = f"{t2.emoji}-{beer_row(state.team2_beers)}\n"
    elif isinstance(latest_action, StartRound):
        mid_string += ACTION_MAP[StartRound].format(n=latest_action.round_n)
        t1_string = f"{t1.emoji}-{beer_row(state.team1_beers)}\n"
        t2_string = f"{t2.emoji}-{beer_row(state.team2_beers)}\n"
    elif isinstance(latest_action, StartGame):
        mid_string += ACTION_MAP[StartRound].format(n=1)
        t1_string = f"{t1.emoji}-{beer_row(state.team1_beers)}\n"
        t2_string = f"{t2.emoji}-{beer_row(state.team2_beers)}\n"
    else:
        t1_string = f"{t1.emoji}-{beer_row(state.team1_beers)}\n"
        t2_string = f"{t2.emoji}-{beer_row(state.team2_beers)}\n"
    mid_string += "\n"

    if state.reverse:
        return t2_string + mid_string + t1_string
    return t1_string + mid_string + t2_string


def render_round_report(game: Game) -> str:
    MAX_WIDTH = 31
    team1 = game.team1
    team2 = game.team2
    actions = get_current_round_knocks(game.history)
    winner = game.history[-1].winner
    t1_rounds, t2_rounds = count_round_wins(game.history)
    round_n = t1_rounds + t2_rounds
    knocks = count_player_knocks(game, actions)
    round_report = ""
    if winner == "team1":
        round_report += f"{team1.emoji} {team1.name} won round {round_n}!\n"
    else:
        round_report += f"{team2.emoji} {team2.name} won round {round_n}!\n"
    round_report += f"{team1.emoji} {t1_rounds} - {t2_rounds} {team2.emoji}\n\n"
    round_report += "Round report:\n"
    round_report += f"<b>{team1.emoji} {team1.name}</b>\n"
    w = str(max(len(pname) for pname in team1.players))
    for player in team1.players:
        player_str = f"{player:<{w}}"

        knock_n = knocks["team1"][player]["knocks"]
        knock_str = f" {knock_n}x💥"

        if knock_n == 8:
            player_str += "♠️"

        selfknocks = knocks["team1"][player]["selfknocks"]
        selfknock_str = f" {selfknocks}x💀" if selfknocks != 0 else ""

        flips = knocks["team1"][player]["flips"]
        flip_str = f" {flips}x🤯" if flips != 0 else ""

        multiple = [
            (i, n) for i, n in enumerate(knocks["team1"][player]["multiple"]) if n > 0
        ]
        mult_str = (
            (" " + " ".join([f"{n}x{NUMBER_MAP[i]}" for i, n in multiple]))
            if len(multiple) > 0
            else ""
        )
        round_report += (
            f"{player_str}\n {knock_str}{selfknock_str}{flip_str}{mult_str}\n"
        )

    round_report += f"\n{team2.emoji} {team2.name}\n"
    w = str(max(len(pname) for pname in team2.players))
    for player in team2.players:
        player_str = f"{player:<{w}}"

        knock_n = knocks["team2"][player]["knocks"]
        knock_str = f" {knock_n}x💥"

        if knock_n == 8:
            player_str += "♠️"

        selfknocks = knocks["team2"][player]["selfknocks"]
        selfknock_str = f" {selfknocks}x💀" if selfknocks != 0 else ""

        flips = knocks["team2"][player]["flips"]
        flip_str = f" {flips}x🤯" if flips != 0 else ""

        multiple = [
            (i, n) for i, n in enumerate(knocks["team2"][player]["multiple"]) if n > 0
        ]
        mult_str = (
            (" " + " ".join([f"{n}x{NUMBER_MAP[i]}" for i, n in multiple]))
            if len(multiple) > 0
            else ""
        )
        round_report += (
            f"{player_str}\n {knock_str}{selfknock_str}{flip_str}{mult_str}\n"
        )

    return round_report


def render_game_win_message(game: Game) -> str:
    t1_score, t2_score = count_round_wins(game.history)

    if t1_score > t2_score:
        reply = (
            "Game over!\n"
            f"{game.team1.name} won\n"
            f"{game.team1.emoji} {t1_score} - {t2_score} {game.team2.emoji}"
        )
    elif t2_score > t1_score:
        reply = (
            "Game over!\n"
            f"{game.team2.name} won\n"
            f"{game.team1.emoji} {t1_score} - {t2_score} {game.team2.emoji}"
        )
    else:
        reply = (
            "Game over!\n"
            f"Ended in tie between {game.team1.name} and {game.team2.name}\n"
            f"{game.team1.emoji} {t1_score} - {t2_score} {game.team2.emoji}"
        )
    return reply


def render_result_string(team1_score, team2_score, team1_emoji, team2_emoji):
    if team1_score > team2_score:
        return f"{team1_emoji} wins {team1_score}-{team2_score}"
    if team2_score > team1_score:
        return f"{team2_emoji} wins {team2_score}-{team1_score}"
    return f"Tie {team1_emoji} {team1_score}-{team2_score} {team2_emoji}"


def render_game_info_string(game):
    t1_score, t2_score = count_round_wins(game.history)
    return (
        f"{game.team1.emoji} {t1_score} - {t2_score} {game.team2.emoji}\n\n"
        f"{game.team1.emoji} <b>{game.team1.name}</b>\n"
        f"<b>Players:</b> {', '.join(game.team1.players)}\n"
        "vs.\n"
        f"{game.team2.emoji} <b>{game.team2.name}</b>\n"
        f"<b>Players:</b> {', '.join(game.team2.players)}\n"
    )


def render_game_start_message(game):
    return (
        "New game starting!\n"
        f"{game.team1.emoji} {game.team1.name}\n"
        f"{', '.join(game.team1.players)}\n"
        "vs.\n"
        f"{game.team2.emoji} {game.team2.name}\n"
        f"{', '.join(game.team2.players)}\n"
    )


def render_confirm_delete_message(game):
    return (
        f"<b>Really delete game {game.id}</b>?\n\n"
        f"{game.team1.emoji} <b>{game.team1.name}</b>\n"
        "vs.\n"
        f"{game.team2.emoji} <b>{game.team2.name}</b>\n"
    )

def render_legend():
    return LEGEND
