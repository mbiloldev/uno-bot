from aiogram import Router, F, Bot
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.exceptions import TelegramBadRequest

import game as G
from keyboards import lobby_keyboard, join_keyboard
from config import MIN_PLAYERS, MAX_PLAYERS, BOT_USERNAME

router = Router()


def lobby_text(g: G.GameState) -> str:
    lines = [
        "🃏 <b>UNO — Lobby</b>",
        "",
        f"O'yinchilar ({g.player_count}/{MAX_PLAYERS}):",
    ]
    for i, p in enumerate(g.players):
        crown = " 👑" if p.user_id == g.creator_id else ""
        lines.append(f"  {i+1}. {p.name}{crown}")
    lines += [
        "",
        "O'yinni boshlash uchun kamida 2 kishi kerak." if g.player_count < MIN_PLAYERS else "Tayyor! Boshlash mumkin.",
    ]
    return "\n".join(lines)


async def update_lobby_message(bot: Bot, g: G.GameState):
    if g.lobby_message_id and g.group_chat_id:
        try:
            await bot.edit_message_text(
                chat_id=g.group_chat_id,
                message_id=g.lobby_message_id,
                text=lobby_text(g),
                reply_markup=lobby_keyboard(g.game_id, g.player_count) if not g.started else None,
                parse_mode="HTML",
            )
        except TelegramBadRequest:
            pass


# /newgame — must be used in a group chat
@router.message(Command("newgame"))
async def cmd_newgame(message: Message, bot: Bot):
    if message.chat.type == "private":
        await message.answer(
            "⚠️ Bu buyruqni guruh chatida ishlating. "
            "Bot guruhga qo'shilganidan keyin /newgame yozing."
        )
        return

    user = message.from_user
    existing = G.get_user_game(user.id)
    if existing:
        await message.answer("Siz allaqachon o'yinda ekansiz. Chiqish uchun /quit yozing.")
        return

    g = G.create_game(creator_id=user.id, creator_name=user.full_name)
    g.group_chat_id = message.chat.id

    sent = await message.answer(
        lobby_text(g),
        reply_markup=lobby_keyboard(g.game_id, g.player_count),
        parse_mode="HTML",
    )
    g.lobby_message_id = sent.message_id

    # Share invite link
    invite_link = f"https://t.me/{BOT_USERNAME}?start=join_{g.game_id}"
    await message.answer(
        f"✅ O'yin yaratildi! Do'stlaringizni taklif qiling:\n{invite_link}"
    )


# Deep link: /start join_GAMEID — joining via invite link in private chat
@router.message(CommandStart(deep_link=True))
async def cmd_start_deep(message: Message, bot: Bot):
    payload = message.text.split(maxsplit=1)[1] if " " in message.text else ""
    if not payload.startswith("join_"):
        await message.answer("Salom! O'yin boshlash uchun guruhda /newgame yozing.")
        return

    game_id = payload[5:]
    user = message.from_user
    ok, msg = G.join_game(game_id, user.id, user.full_name)
    if not ok:
        await message.answer(f"❌ {msg}")
        return

    g = G.games[game_id]
    await message.answer(f"✅ O'yinga qo'shildingiz! Lobby yangilanmoqda...")
    await update_lobby_message(bot, g)

    # Notify group
    if g.group_chat_id:
        await bot.send_message(
            g.group_chat_id,
            f"👤 <b>{user.full_name}</b> o'yinga qo'shildi! ({g.player_count}/{MAX_PLAYERS})",
            parse_mode="HTML",
        )


# Inline join button (alternative to deep link)
@router.callback_query(F.data.startswith("join:"))
async def cb_join(call: CallbackQuery, bot: Bot):
    game_id = call.data.split(":")[1]
    user = call.from_user
    ok, msg = G.join_game(game_id, user.id, user.full_name)
    await call.answer(msg, show_alert=not ok)
    if ok:
        g = G.games.get(game_id)
        if g:
            await update_lobby_message(bot, g)


# Start game button — only creator
@router.callback_query(F.data.startswith("start_game:"))
async def cb_start_game(call: CallbackQuery, bot: Bot):
    game_id = call.data.split(":")[1]
    g = G.games.get(game_id)

    if not g:
        await call.answer("O'yin topilmadi.", show_alert=True)
        return
    if call.from_user.id != g.creator_id:
        await call.answer("Faqat o'yin yaratuvchisi boshlashi mumkin.", show_alert=True)
        return
    if g.player_count < MIN_PLAYERS:
        await call.answer("O'yinga qo'shilish uchun kamida 2 kishi kerak!", show_alert=True)
        return
    if g.started:
        await call.answer("O'yin allaqachon boshlangan.", show_alert=True)
        return

    g.start_game()
    await call.answer("O'yin boshlandi! ✅")

    # Remove lobby keyboard
    try:
        await call.message.edit_reply_markup(reply_markup=None)
    except TelegramBadRequest:
        pass

    # Import here to avoid circular imports
    from handlers.gameplay import send_game_status, send_hand_to_player

    await bot.send_message(
        g.group_chat_id,
        f"🎮 <b>O'yin boshlandi!</b>\nHar bir o'yinchi {6} ta karta oldi.\n\n"
        f"Birinchi navbat: <b>{g.current_player.name}</b>",
        parse_mode="HTML",
    )

    # Send each player their hand via private message
    for player in g.players:
        await send_hand_to_player(bot, g, player)

    # Send initial game status to group
    await send_game_status(bot, g)
