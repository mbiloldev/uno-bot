import random
import string
from dataclasses import dataclass, field
from deck import Card, Deck
from config import MIN_PLAYERS, MAX_PLAYERS, HAND_SIZE


def generate_game_id(length: int = 8) -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=length))


@dataclass
class Player:
    user_id: int
    name: str
    hand: list[Card] = field(default_factory=list)
    hand_message_id: int | None = None  # message_id of the private hand message


class GameState:
    def __init__(self, creator_id: int, creator_name: str, group_chat_id: int | None = None):
        self.game_id: str = generate_game_id()
        self.creator_id: int = creator_id
        self.group_chat_id: int | None = group_chat_id  # set when game is started from a group
        self.players: list[Player] = []
        self.deck: Deck | None = None
        self.current_index: int = 0
        self.direction: int = 1  # 1 = clockwise, -1 = counter-clockwise
        self.active_color: str | None = None  # overrides top card color after wild
        self.pending_draw: int = 0  # accumulated draw penalty
        self.stack_type: str | None = None  # "+2", "+4", "+10"
        self.awaiting_color: bool = False  # True when wild was played, waiting for color pick
        self.started: bool = False
        self.lobby_message_id: int | None = None  # pinned lobby message
        self.status_message_id: int | None = None  # in-game status message in group

        # Add creator as first player
        self.add_player(creator_id, creator_name)

    # ──────────────────────────────────────────────
    # Player management
    # ──────────────────────────────────────────────

    def add_player(self, user_id: int, name: str) -> bool:
        """Add player. Returns False if full or already joined."""
        if len(self.players) >= MAX_PLAYERS:
            return False
        if self.get_player(user_id):
            return False
        self.players.append(Player(user_id=user_id, name=name))
        return True

    def remove_player(self, user_id: int) -> Player | None:
        player = self.get_player(user_id)
        if player:
            self.players.remove(player)
        return player

    def get_player(self, user_id: int) -> Player | None:
        for p in self.players:
            if p.user_id == user_id:
                return p
        return None

    @property
    def player_count(self) -> int:
        return len(self.players)

    # ──────────────────────────────────────────────
    # Game start
    # ──────────────────────────────────────────────

    def start_game(self):
        assert len(self.players) >= MIN_PLAYERS, "Not enough players"
        self.deck = Deck()
        # Deal hands
        for player in self.players:
            player.hand = self.deck.draw_many(HAND_SIZE)
        # Flip starting card (non-wild)
        self.deck.flip_start_card()
        self.active_color = self.deck.top_card.color
        self.started = True

    # ──────────────────────────────────────────────
    # Turn management
    # ──────────────────────────────────────────────

    @property
    def current_player(self) -> Player:
        return self.players[self.current_index]

    def advance_turn(self, skip: bool = False):
        """Move to the next player. skip=True skips one extra player."""
        steps = 2 if skip else 1
        self.current_index = (self.current_index + steps * self.direction) % len(self.players)

    def reverse_direction(self):
        self.direction *= -1

    def next_player_index(self) -> int:
        return (self.current_index + self.direction) % len(self.players)

    def get_player_at(self, index: int) -> Player:
        return self.players[index % len(self.players)]

    # ──────────────────────────────────────────────
    # Card play
    # ──────────────────────────────────────────────

    def play_card(self, user_id: int, card_uid: str) -> dict:
        """
        Attempt to play a card. Returns a result dict with keys:
          success, card, needs_color, skip_next, draw_next, winner, message
        """
        player = self.get_player(user_id)
        if not player:
            return {"success": False, "message": "Siz o'yinda emassiz."}
        if player.user_id != self.current_player.user_id:
            return {"success": False, "message": "Hozir sizning navbatingiz emas!"}
        if self.awaiting_color:
            return {"success": False, "message": "Avval rang tanlang!"}

        card = next((c for c in player.hand if c.uid == card_uid), None)
        if not card:
            return {"success": False, "message": "Bu karta sizda yo'q."}

        top = self.deck.top_card
        if not card.can_be_played_on(top, self.active_color, self.stack_type):
            return {"success": False, "message": "Bu karta tushmaydi!"}

        # Remove from hand and play
        player.hand.remove(card)
        self.deck.play_card(card)

        result = {"success": True, "card": card, "needs_color": False,
                  "skip_next": False, "draw_next": 0, "winner": None, "message": ""}

        # Check win
        if not player.hand:
            result["winner"] = player
            return result

        # Handle special effects
        if card.value == "reverse":
            if len(self.players) == 2:
                # Reverse acts as skip in 2-player
                self.advance_turn()  # stay on current after advance below
                result["skip_next"] = True
            else:
                self.reverse_direction()
        elif card.value == "skip":
            result["skip_next"] = True
        elif card.value in ("+2", "+4", "+10"):
            self.pending_draw += card.draw_value
            self.stack_type = card.value if card.value != "+2" else (self.stack_type or "+2")
            # For +2 stacking, keep stack_type as "+2" unless upgraded
            if card.value in ("+4", "+10"):
                self.stack_type = card.value
            result["draw_next"] = self.pending_draw

        # Wild / color change
        if card.is_wild:
            self.awaiting_color = True
            result["needs_color"] = True
            # Don't advance turn yet; wait for color pick
            return result

        # Update active color
        self.active_color = card.color

        # Advance turn
        if card.value == "skip":
            self.advance_turn(skip=True)
        elif card.value == "reverse" and len(self.players) == 2:
            self.advance_turn(skip=True)
        else:
            self.advance_turn()

        return result

    def pick_color(self, user_id: int, color: str) -> dict:
        """Called after playing a wild card to choose a color."""
        if not self.awaiting_color:
            return {"success": False, "message": "Rang tanlash kutilmaydi."}
        if user_id != self.current_player.user_id:
            return {"success": False, "message": "Siz hozir karta o'ynamadingiz."}

        self.active_color = color
        self.awaiting_color = False

        top = self.deck.top_card
        skip = top.value == "skip" or (top.value in ("+4", "+10") and self.pending_draw > 0)

        # Advance turn (skip if +4/+10 active)
        if top.value in ("+4", "+10") and self.pending_draw > 0:
            self.advance_turn(skip=True)
        else:
            self.advance_turn()

        return {"success": True, "color": color, "draw_next": self.pending_draw}

    def draw_card(self, user_id: int) -> dict:
        """
        Player draws a card (either forced by penalty or voluntary).
        Returns drawn cards and whether the player must also skip.
        """
        player = self.get_player(user_id)
        if not player:
            return {"success": False, "message": "Siz o'yinda emassiz."}
        if player.user_id != self.current_player.user_id:
            return {"success": False, "message": "Hozir sizning navbatingiz emas!"}
        if self.awaiting_color:
            return {"success": False, "message": "Avval rang tanlang!"}

        if self.pending_draw > 0:
            # Forced draw
            count = self.pending_draw
            drawn = self.deck.draw_many(count)
            player.hand.extend(drawn)
            self.pending_draw = 0
            self.stack_type = None
            self.advance_turn()
            return {"success": True, "cards": drawn, "forced": True, "count": count}
        else:
            # Voluntary draw of 1
            card = self.deck.draw()
            player.hand.append(card)
            self.advance_turn()
            return {"success": True, "cards": [card], "forced": False, "count": 1}

    # ──────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────

    def playable_cards(self, user_id: int) -> list[Card]:
        player = self.get_player(user_id)
        if not player:
            return []
        top = self.deck.top_card
        return [c for c in player.hand if c.can_be_played_on(top, self.active_color, self.stack_type)]

    def top_card_label(self) -> str:
        top = self.deck.top_card
        if not top:
            return "—"
        if top.is_wild and self.active_color:
            from config import COLOR_EMOJI
            return f"{COLOR_EMOJI[self.active_color]} {top.value.upper()}"
        return top.label

    def direction_emoji(self) -> str:
        return "🔄 Soat yo'nalishi" if self.direction == 1 else "🔃 Teskari yo'nalish"

    def scores_text(self) -> str:
        lines = []
        sorted_players = sorted(self.players, key=lambda p: len(p.hand))
        for i, p in enumerate(sorted_players):
            medal = ["🥇", "🥈", "🥉"][i] if i < 3 else "▪️"
            lines.append(f"{medal} {p.name} — {len(p.hand)} karta")
        return "\n".join(lines)

    def status_text(self) -> str:
        lines = [
            f"🎴 Tepадаги karta: {self.top_card_label()}",
            f"{self.direction_emoji()}",
            f"👤 Navbat: <b>{self.current_player.name}</b>",
            "",
        ]
        if self.pending_draw > 0:
            lines.append(f"⚠️ Jarima: +{self.pending_draw} — tashlash yoki olish!")
            lines.append("")
        for p in self.players:
            arrow = "➡️" if p.user_id == self.current_player.user_id else "  "
            lines.append(f"{arrow} {p.name} — {len(p.hand)} karta")
        return "\n".join(lines)


# ──────────────────────────────────────────────
# Global games registry
# ──────────────────────────────────────────────

# game_id -> GameState
games: dict[str, GameState] = {}

# user_id -> game_id  (which game a player is in)
user_game: dict[int, str] = {}


def create_game(creator_id: int, creator_name: str) -> GameState:
    # Remove user from any existing game
    leave_game(creator_id)
    game = GameState(creator_id=creator_id, creator_name=creator_name)
    games[game.game_id] = game
    user_game[creator_id] = game.game_id
    return game


def join_game(game_id: str, user_id: int, name: str) -> tuple[bool, str]:
    game = games.get(game_id)
    if not game:
        return False, "O'yin topilmadi."
    if game.started:
        return False, "O'yin allaqachon boshlangan."
    if len(game.players) >= MAX_PLAYERS:
        return False, "O'yin to'liq (maksimal 5 o'yinchi)."
    if game.get_player(user_id):
        return False, "Siz allaqachon qo'shilgansiz."
    # Leave any current game
    leave_game(user_id)
    game.add_player(user_id, name)
    user_game[user_id] = game_id
    return True, "Muvaffaqiyatli qo'shildingiz!"


def leave_game(user_id: int) -> GameState | None:
    game_id = user_game.pop(user_id, None)
    if not game_id:
        return None
    game = games.get(game_id)
    if not game:
        return None
    game.remove_player(user_id)
    if not game.players:
        del games[game_id]
    return game


def get_user_game(user_id: int) -> GameState | None:
    game_id = user_game.get(user_id)
    return games.get(game_id) if game_id else None
