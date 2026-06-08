import random
import uuid
from dataclasses import dataclass, field
from config import COLORS, COLOR_EMOJI


@dataclass
class Card:
    color: str | None  # None for wild cards
    value: str  # "0"-"9", "skip", "reverse", "+2", "wild", "+4", "+10"
    uid: str = field(default_factory=lambda: str(uuid.uuid4()))

    @property
    def is_wild(self) -> bool:
        return self.color is None

    @property
    def draw_value(self) -> int:
        """How many cards this forces the next player to draw (0 if none)."""
        if self.value == "+2":
            return 2
        if self.value == "+4":
            return 4
        if self.value == "+10":
            return 10
        return 0

    @property
    def is_draw_card(self) -> bool:
        return self.draw_value > 0

    @property
    def label(self) -> str:
        emoji = COLOR_EMOJI.get(self.color, "🃏") if self.color else "🃏"
        value_display = {
            "skip": "Skip",
            "reverse": "Reverse",
            "+2": "+2",
            "+4": "+4",
            "+10": "+10",
            "wild": "Wild",
        }.get(self.value, self.value)
        return f"{emoji} {value_display}"

    def sticker_key(self) -> str:
        if self.color is None:
            if self.value == "wild":
                return "wild"
            return f"wild{self.value}"  # wild+4, wild+10
        return f"{self.color}_{self.value}"

    def can_be_played_on(self, top: "Card", active_color: str | None, stack_type: str | None) -> bool:
        """
        Returns True if this card can legally be played on top of `top`.
        active_color overrides top.color after a wild is played.
        stack_type is "+2", "+4", "+10", or None (active penalty chain).
        """
        effective_color = active_color or top.color

        # During an active stack penalty chain
        if stack_type == "+2":
            # Only +2 (matching color or same type logic), +4, +10 can be played
            if self.value == "+2":
                # +2 on +2: must match color of the top +2 card
                return self.color == top.color or (active_color and self.color == active_color)
            if self.value in ("+4", "+10"):
                return True  # wilds always playable
            return False

        if stack_type in ("+4", "+10"):
            # Only +4 and +10 can stack; +2 cannot
            if self.value in ("+4", "+10"):
                return True
            return False

        # Normal play rules
        if self.is_wild:
            return True  # wild/+4/+10 always playable
        if self.color == effective_color:
            return True
        if self.value == top.value:
            return True
        return False

    def __repr__(self):
        return f"Card({self.color}, {self.value})"


def build_deck() -> list[Card]:
    """Build a full 114-card UNO deck."""
    cards = []

    for color in COLORS:
        # Number cards: one 0, two each of 1-9
        cards.append(Card(color=color, value="0"))
        for n in range(1, 10):
            cards.append(Card(color=color, value=str(n)))
            cards.append(Card(color=color, value=str(n)))
        # Action cards: 2 each per color
        for action in ("skip", "reverse", "+2"):
            cards.append(Card(color=color, value=action))
            cards.append(Card(color=color, value=action))

    # Wild cards: 6
    for _ in range(6):
        cards.append(Card(color=None, value="wild"))

    # +4 Wild: 8
    for _ in range(8):
        cards.append(Card(color=None, value="+4"))

    # +10 Wild: 4
    for _ in range(4):
        cards.append(Card(color=None, value="+10"))

    return cards


class Deck:
    def __init__(self):
        self.draw_pile: list[Card] = build_deck()
        self.discard_pile: list[Card] = []
        random.shuffle(self.draw_pile)

    def draw(self) -> Card:
        """Draw one card; reshuffles discard pile if draw pile is empty."""
        if not self.draw_pile:
            self._reshuffle()
        return self.draw_pile.pop()

    def draw_many(self, n: int) -> list[Card]:
        return [self.draw() for _ in range(n)]

    def _reshuffle(self):
        if len(self.discard_pile) <= 1:
            raise RuntimeError("Deck completely exhausted!")
        top = self.discard_pile[-1]
        reshuffled = self.discard_pile[:-1]
        random.shuffle(reshuffled)
        self.draw_pile = reshuffled
        self.discard_pile = [top]

    def play_card(self, card: Card):
        self.discard_pile.append(card)

    @property
    def top_card(self) -> Card | None:
        return self.discard_pile[-1] if self.discard_pile else None

    def flip_start_card(self):
        """Flip the starting discard card; redraws if it's a wild."""
        while True:
            card = self.draw()
            if not card.is_wild:
                self.discard_pile.append(card)
                return card
