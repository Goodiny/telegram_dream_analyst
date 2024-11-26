
from pyrogram import Client

from handlers.keyboards import character_keyboard


async def show_sleep_characteristics_menu(client: Client, user_id: int):
    msg = await client.send_message(
        chat_id=user_id,
        text="Выберите характеристику сна:",
        reply_markup=character_keyboard()
    )

    return msg.id