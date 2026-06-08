from aiogram import Router, Bot
from aiogram.filters import Command
from aiogram.types import Message

import game as G
from config import BOT_USERNAME

router = Router()


    if not g:
        await message.answer("Siz hech qanday o'yinda emassiz.")
        return

    was_started = g.started
    group_id = g.group_chat_id

    G.leave_game(user.id)

    await message.answer("Siz o'yindan chiqdingiz.")

    if group_id:
        await bot.send_message(
            group_id,
            f"🚪 <b>{user.full_name}</b> o'yinni tashlab ketdi.",
            parse_mode="HTML",
        )

    if was_started and g.game_id in G.games and len(g.players) < 2:
        # Not enough players — end game
        if group_id:
            await bot.send_message(
                group_id,
                "⚠️ O'yinchilar yetarli emas. O'yin bekor qilindi.",
            )
        for p in list(g.players):
            G.user_game.pop(p.user_id, None)
        if g.game_id in G.games:
            del G.games[g.game_id]
    elif was_started and g.game_id in G.games:
        from handlers.gameplay import send_game_status, refresh_all_hands
        await refresh_all_hands(bot, g)
        await send_game_status(bot, g)


@router.message(Command("cards"))
async def cmd_cards(message: Message, bot: Bot):
    user = message.from_user
    g = G.get_user_game(user.id)

    if not g or not g.started:
        await message.answer("Hozir aktiv o'yin yo'q.")
        return

    player = g.get_player(user.id)
    if not player:
        await message.answer("Siz o'yinda emassiz.")
        return

    player.hand_message_id = None  # force resend
    from handlers.gameplay import send_hand_to_player
    await send_hand_to_player(bot, g, player)

    if message.chat.type != "private":
        await message.answer("Kartalaringiz shaxsiy xabarda yuborildi.")


@router.message(Command("status"))
async def cmd_status(message: Message, bot: Bot):
    user = message.from_user
    g = G.get_user_game(user.id)

    if not g or not g.started:
        await message.answer("Hozir aktiv o'yin yo'q.")
        return

    await message.answer(g.status_text(), parse_mode="HTML")


@router.message(Command("start"))
async def cmd_start_plain(message: Message):
    """Handle /start without payload (direct bot open)."""
    await message.answer(
        "Salom! Men UNO botiman 🃏\n\n"
        "O'yin boshlash uchun guruh chatida /newgame yozing.\n"
        "Do'stlaringizga yuborilgan havolani bosib o'yinga qo'shilasiz."
    )
