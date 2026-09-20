class Broadcaster:
    def __init__(self, bot, chat_id):
        self.bot = bot
        self.chat_id = chat_id

    async def send(self, text):
        return await self.bot.send_message(
            chat_id=self.chat_id, text=f"<code>{text}</code>", parse_mode="HTML"
        )

    async def delete(self, msg_id):
        await self.bot.delete_message(chat_id=self.chat_id, message_id=msg_id)
