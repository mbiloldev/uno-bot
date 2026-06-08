from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message
from aiogram.exceptions import TelegramBadRequest

import game as G
from deck import Card
from keyboards import hand_keyboard, color_keyboard
from stickers import get_sticker
from config import COLOR_EMOJI, COLOR_NAME_UZ

router = Router()


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

async def send_game_status(bot: Bot, g: G.GameState):
    """Send or edit the game status message in the group."""
    if not g.group_chat_id:
        return
    text = g.status_text()
    if g.status_message_id:
        try:
            await bot.edit_message_text(
                chat_id=g.group_chat_id,
                message_id=g.status_message_id,
                text=text,
                parse_mode="HTML",
            )
            return
        except TelegramBadRequest:
            pass
    sent = await bot.send_message(g.group_chat_id, text, parse_mode="HTML")
    g.status_message_id = sent.message_id


async def send_hand_to_player(bot: Bot, g: G.GameState, player: G.Player):
    """Send or edit the hand message for a player in their private chat."""
    playable = {c.uid for c in g.playable_cards(player.user_id)}
    markup = hand_keyboard(player.hand, playable, g.pending_draw if player.user_id == g.current_player.user_id else 0)
    
    current_turn = player.user_id == g.current_player.user_id
    if current_turn:
        text = (
            f"🃏 <b>Sizning kartalaringiz</b>\n"
            f"Navbat: <b>SIZNIKI</b> ➡️\n"
            f"Tepadagi karta: {g.top_card_label()}"
        )
    else:
        text = (
            f"🃏 <b>Sizning kartalaringiz</b>\n"
            f"Navbat: <b>{g.current_player.name}</b>\n"
            f"Tepadagi karta: {g.top_card_label()}"
        )

    if player.hand_message_id:
        try:
            await bot.edit_message_text(
                chat_id=player.user_id,
                message_id=player.hand_message_id,
                text=text,
                reply_markup=markup,
                parse_mode="HTML",
            )
            return
        except TelegramBadRequest:
            pass

    sent = await bot.send_message(
        player.user_id,
        text,
        reply_markup=markup,
        parse_mode="HTML",
    )
    player.hand_message_id = sent.message_id


async def refresh_all_hands(bot: Bot, g: G.GameState):
    """Update hand messages for all players."""
    for player in g.players:
        try:
            await send_hand_to_player(bot, g, player)
        except Exception:
            pass


async def announce_winner(bot: Bot, g: G.GameState, winner: G.Player):
    """Announce game winner and clean up."""
    text = (
        f"🏆 <b>{winner.name}</b> o'yinni yutdi! 🎉\n\n"
        f"📊 O'yin yakunlandi:\n{g.scores_text()}"
    )
    if g.group_chat_id:
        await bot.send_message(g.group_chat_id, text, parse_mode="HTML")

    # Clean up
    for player in g.players:
        G.user_game.pop(player.user_id, None)
    del G.games[g.game_id]


# ──────────────────────────────────────────────
# Play a card
# ──────────────────────────────────────────────

@router.callback_query(F.data.startswith("play:"))
async def cb_play_card(call: CallbackQuery, bot: Bot):
    card_uid = call.data.split(":")[1]
    user = call.from_user
    g = G.get_user_game(user.id)

    if not g or not g.started:
        await call.answer("O'yin topilmadi.", show_alert=True)
        return

    result = g.play_card(user.id, card_uid)
    if not result["success"]:
        await call.answer(result["message"], show_alert=False)
        return

    await call.answer()
    card: Card = result["card"]

    # Send sticker to group
    sticker_id = get_sticker(card)
    if sticker_id and g.group_chat_id:
        try:
            await bot.send_sticker(g.group_chat_id, sticker_id)
        except Exception:
            pass

    # Announce card play in group
    if g.group_chat_id:
        await bot.send_message(
            g.group_chat_id,
            f"🎴 <b>{user.full_name}</b>: {card.label}",
            parse_mode="HTML",
        )

    # Check winner
    if result.get("winner"):
        await refresh_all_hands(bot, g)
        await announce_winner(bot, g, result["winner"])
        return

    # UNO announcement
    player = g.get_player(user.id)
    if player and len(player.hand) == 1:
        if g.group_chat_id:
            await bot.send_message(
                g.group_chat_id,
                f"🎴 UNO! <b>{player.name}</b> — bitta kartasi qoldi!",
                parse_mode="HTML",
            )

    # Wild — ask for color (don't refresh yet)
    if result.get("needs_color"):
        await bot.send_message(
            user.id,
            "🎨 Rang tanlang:",
            reply_markup=color_keyboard(g.game_id),
        )
        await refresh_all_hands(bot, g)
        await send_game_status(bot, g)
        return

    # Announce penalty if any
    if result.get("draw_next", 0) > 0 and g.group_chat_id:
        next_p = g.current_player
        await bot.send_message(
            g.group_chat_id,
            f"⚠️ <b>{next_p.name}</b> +{result['draw_next']} karta olishi kerak!",
            parse_mode="HTML",
        )

    # Notify current player it's their turn
    if g.group_chat_id:
        await bot.send_message(
            g.group_chat_id,
            f"➡️ Navbat: <b>{g.current_player.name}</b>",
            parse_mode="HTML",
        )

    await refresh_all_hands(bot, g)
    await send_game_status(bot, g)


# ──────────────────────────────────────────────
# Blocked card press
# ──────────────────────────────────────────────

@router.callback_query(F.data.startswith("blocked:"))
async def cb_blocked(call: CallbackQuery):
    await call.answer("Bu karta tushmaydi!", show_alert=False)


# ──────────────────────────────────────────────
# Draw a card
# ──────────────────────────────────────────────

@router.callback_query(F.data == "draw_card")
async def cb_draw_card(call: CallbackQuery, bot: Bot):
    user = call.from_user
    g = G.get_user_game(user.id)

    if not g or not g.started:
        await call.answer("O'yin topilmadi.", show_alert=True)
        return

    result = g.draw_card(user.id)
    if not result["success"]:
        await call.answer(result["message"], show_alert=False)
        return

    await call.answer()
    cards = result["cards"]
    count = result["count"]

    if result["forced"]:
        msg = f"📥 <b>{user.full_name}</b> jarima sifatida +{count} karta oldi."
    else:
        card = cards[0]
        msg = f"📥 <b>{user.full_name}</b> karta oldi: {card.label}"

    if g.group_chat_id:
        await bot.send_message(g.group_chat_id, msg, parse_mode="HTML")
        await bot.send_message(
            g.group_chat_id,
            f"➡️ Navbat: <b>{g.current_player.name}</b>",
            parse_mode="HTML",
        )

    await refresh_all_hands(bot, g)
    await send_game_status(bot, g)


# ──────────────────────────────────────────────
# Color picker
# ──────────────────────────────────────────────

@router.callback_query(F.data.startswith("pick_color:"))
async def cb_pick_color(call: CallbackQuery, bot: Bot):
    _, game_id, color = call.data.split(":")
    user = call.from_user
    g = G.games.get(game_id)

    if not g:
        await call.answer("O'yin topilmadi.", show_alert=True)
        return

    result = g.pick_color(user.id, color)
    if not result["success"]:
        await call.answer(result["message"], show_alert=False)
        return

    await call.answer(f"{COLOR_EMOJI[color]} {COLOR_NAME_UZ[color]} tanlandi!")

    # Remove color picker message
    try:
        await call.message.delete()
    except TelegramBadRequest:
        pass

    if g.group_chat_id:
        draw_next = result.get("draw_next", 0)
        next_p = g.current_player
        if draw_next > 0:
            await bot.send_message(
                g.group_chat_id,
                f"{COLOR_EMOJI[color]} Rang: <b>{COLOR_NAME_UZ[color]}</b>\n"
                f"⚠️ <b>{next_p.name}</b> +{draw_next} karta olishi kerak!\n"
                f"➡️ Navbat: <b>{next_p.name}</b>",
                parse_mode="HTML",
            )
        else:
            await bot.send_message(
                g.group_chat_id,
                f"{COLOR_EMOJI[color]} Rang: <b>{COLOR_NAME_UZ[color]}</b>\n"
                f"➡️ Navbat: <b>{next_p.name}</b>",
                parse_mode="HTML",
            )

    await refresh_all_hands(bot, g)
    await send_game_status(bot, g)
