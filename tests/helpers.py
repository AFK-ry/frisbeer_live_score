import logging

from domain.models import Game, Team


logging.getLogger("frisbeer_live_score_bot").disabled = True


def make_game(history=None):
    return Game(
        id="game-1",
        timestamp=123.0,
        team1=Team("Blue", "B", ["Alice", "Bob", "Cara"]),
        team2=Team("Red", "R", ["Dan", "Eve", "Finn"]),
        history=[] if history is None else history,
    )
