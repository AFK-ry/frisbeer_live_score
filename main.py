from os import getenv
from dotenv import load_dotenv
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)
from handlers.menu import (
    start,
    about,
    main_menu,
    legend,
    handle_message,
    new_game,
    game_list,
    cancel_game_creation,
)
from handlers.game import (
    game_info,
    confirm_delete,
    delete_game,
    live_game,
    mark_beer,
    switch_sides,
    refresh,
    assign_knocks,
    undo,
    start_game,
    end_round,
    start_round,
    end_game,
    confirm_end_game,
)
from infrastructure.logging_config import logger
from infrastructure.storage.sqlite import Storage
from infrastructure.telegram.broadcaster import Broadcaster

COMMAND_HANDLERS = [
    ("start", start),
]

CALLBACK_HANDLERS = [
    ("^about$", about),
    ("^main$", main_menu),
    ("^new_game$", new_game),
    ("^game_list$", game_list),
    ("^legend$", legend),
    ("^cancel$", cancel_game_creation),
    ("^game_info:", game_info),
    ("^start_game:", start_game),
    ("^confirm_del:", confirm_delete),
    ("^del_game:", delete_game),
    ("^live_game:", live_game),
    ("^mark:", mark_beer),
    ("^switch_sides:", switch_sides),
    ("^refresh:", refresh),
    ("^assign:", assign_knocks),
    ("^undo:", undo),
    ("^end_round:", end_round),
    ("^start_round:", start_round),
    ("^end_game:", end_game),
    ("^confirm_end_game:", confirm_end_game),
]


def register_handlers(app):
    for command, handler in COMMAND_HANDLERS:
        app.add_handler(CommandHandler(command, handler))

    for pattern, handler in CALLBACK_HANDLERS:
        app.add_handler(CallbackQueryHandler(handler, pattern=pattern))

    app.add_handler(MessageHandler(filters.TEXT, handle_message))


def setup_infrastructure(app, chat_id):
    storage = Storage()
    app.bot_data["storage"] = storage
    broadcaster = Broadcaster(app.bot, chat_id)
    app.bot_data["broadcaster"] = broadcaster


def main(token, broadcast_chat_id):
    app = Application.builder().token(token).build()
    setup_infrastructure(app, broadcast_chat_id)
    register_handlers(app)
    app.run_polling()


if __name__ == "__main__":
    load_dotenv()
    token = getenv("TOKEN")
    broadcast_chat_id = int(getenv("BROADCAST_CHAT_ID"))
    logger.info("Bot starting...")
    main(token, broadcast_chat_id)
