# 🃏 UNO Telegram Bot

Multiplayer UNO o'yini uchun Telegram bot (aiogram 3.x, Python 3.11+).

---

## O'rnatish (Setup)

### 1. Talablar
- Python 3.11+
- pip

### 2. Kutubxonalarni o'rnatish
```bash
pip install -r requirements.txt
```

### 3. Muhit o'zgaruvchilarini sozlash
`.env.example` faylini nusxa olib `.env` nomini bering va to'ldiring:
```bash
cp .env .env
```

`.env` ichida:
```
BOT_TOKEN=123456789:ABCdefGhIjKlmNoPQRsTUVwxYz
BOT_USERNAME=your_bot_username
```

### 4. Sticker ID larini qo'shish
`stickers.py` faylidagi `STICKERS` lug'atiga barcha kartalar uchun
Telegram sticker `file_id` larini qo'ying.

Sticker `file_id` ni olish uchun botga stickerini yuboring va
`@RawDataBot` yordamida `file_id` ni aniqlang.

### 5. Botni ishga tushirish
```bash
python bot.py
```

---

## Fayl tuzilmasi

```
uno_bot/
├── bot.py              # Kirish nuqtasi, dispatcher
├── config.py           # BOT_TOKEN, konstantlar
├── stickers.py         # STICKERS lug'ati (file_id lar)
├── deck.py             # Card klassi, Deck klassi
├── game.py             # GameState klassi, barcha o'yin mantiqi
├── keyboards.py        # Barcha inline keyboard qurilmalari
├── handlers/
│   ├── lobby.py        # /newgame, qo'shilish, boshlash
│   ├── gameplay.py     # karta o'ynash, karta olish, rang tanlash
│   └── misc.py         # /quit, /cards, /status
├── requirements.txt
└── .env.example
```

---

## O'yin qoidalari

| Karta | Ta'sir |
|-------|--------|
| 0–9 | Oddiy raqamli kartalar |
| Skip | Keyingi o'yinchi navbatini o'tkazib yuboradi |
| Reverse | Navbat yo'nalishini o'zgartiradi |
| +2 | Keyingi o'yinchi 2 karta oladi va navbatini yo'qotadi (stack mumkin) |
| Wild | Har qanday kartaga qo'yiladi, rang tanlanadi |
| Wild +4 | Har qanday kartaga qo'yiladi, keyingi +4 karta oladi (stack mumkin) |
| Wild +10 | Har qanday kartaga qo'yiladi, keyingi +10 karta oladi (stack mumkin) |

### Stack qoidalari
- `+2` → `+2` ga stack qilinadi (bir xil rang kerak)
- `+4` va `+10` → `+2` ustiga ham stack qilinadi
- `+2` → `+4` yoki `+10` ustiga **qo'yib bo'lmaydi**

---

## Buyruqlar

| Buyruq | Ta'rif |
|--------|--------|
| `/newgame` | Yangi o'yin yaratish (guruhda) |
| `/quit` | O'yindan chiqish |
| `/cards` | Kartalaringizni qayta ko'rish |
| `/status` | O'yin holatini ko'rish |

---

## Bot sozlamalari (BotFather)

BotFather da quyidagi sozlamalarni o'rnating:

**Commands:**
```
newgame - Yangi UNO o'yini boshlash
quit - O'yindan chiqish
cards - Kartalarimni ko'rish
status - O'yin holati
```

Bot guruhda **xabarlarga javob berish** huquqiga ega bo'lishi kerak.
Guruhga botni qo'shganda admin qiling yoki xabar yuborish ruxsatini bering.
