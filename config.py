import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "your_bot_token_hero")
BOT_USERNAME = os.getenv("BOT_USERNAME", "@mb1uz")

MIN_PLAYERS = 2
MAX_PLAYERS = 5
HAND_SIZE = 6

COLORS = ["red", "green", "yellow", "blue"]
COLOR_EMOJI = {
    "red": "🔴",
    "green": "🟢",
    "yellow": "🟡",
    "blue": "🔵",
}
COLOR_NAME_UZ = {
    "red": "Qizil",
    "green": "Yashil",
    "yellow": "Sariq",
    "blue": "Ko'k",
}
