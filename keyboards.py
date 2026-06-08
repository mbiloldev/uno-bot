from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from deck import Card
from config import COLORS, COLOR_EMOJI, COLOR_NAME_UZ


def lobby_keyboard(game_id: str, player_count: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="▶️ O'yinni boshlash" + (" ✅" if player_count >= 2 else " ❌"),
        callback_data=f"start_game:{game_id}",
    )
    return builder.as_markup()


def hand_keyboard(hand: list[Card], playable_uids: set[str], pending_draw: int = 0) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for card in hand:
        if card.uid in playable_uids:
            builder.button(text=card.label, callback_data=f"play:{card.uid}")
        else:
            builder.button(text=f"╌{card.label}", callback_data=f"blocked:{card.uid}")
    builder.adjust(2)

    # Draw button row
    if pending_draw > 0:
        builder.button(text=f"🃏 +{pending_draw} karta ol", callback_data="draw_card")
    else:
        builder.button(text="🃏 Karta olish", callback_data="draw_card")

    builder.adjust(2, repeat=True)
    return builder.as_markup()


def color_keyboard(game_id: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for color in COLORS:
        builder.button(
            text=f"{COLOR_EMOJI[color]} {COLOR_NAME_UZ[color]}",
            callback_data=f"pick_color:{game_id}:{color}",
        )
    builder.adjust(2)
    return builder.as_markup()


def join_keyboard(game_id: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✋ O'yinga qo'shilish", callback_data=f"join:{game_id}")
    return builder.as_markup()
