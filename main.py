import json
import os
import time
from pyrogram import Client, filters
from pyrogram.types import Message

BOT_TOKEN = os.getenv("BOT_TOKEN")

ADMIN_IDS = [6203351064, 8232605018, 5743410391]

DB_FILE = "data.json"


# ---------------- DATABASE SYSTEM ---------------- #

def load_db():
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, "w") as f:
            json.dump({}, f)
    with open(DB_FILE, "r") as f:
        return json.load(f)


def save_db(db):
    with open(DB_FILE, "w") as f:
        json.dump(db, f, indent=2)


def get_user(db, uid):
    if str(uid) not in db:
        db[str(uid)] = {
            "balance": 500,
            "alive": True,
            "protection_until": 0
        }
    return db[str(uid)]


def now():
    return int(time.time())


# ---------------- TELEGRAM BOT ---------------- #

app = Client(
    "gamebot",
    bot_token=BOT_TOKEN,
)


# ---------------- COMMANDS ---------------- #

@app.on_message(filters.command("start"))
async def start(_, m: Message):
    await m.reply(
        "🎮 **Welcome to the Survival Game!** 🎮\n\n"
        "⚔️ Reply to someone's message to interact!\n"
        "💀 /kill — Kill a user\n"
        "🕵️‍♂️ /rob <amount> — Rob a user\n"
        "🏦 /bal — Check balance\n"
        "❤️ /revive — Revive yourself (1000$)\n"
        "🛡 /protect 1d/2d — Protect yourself (200$/day, max 2d)\n"
        "💳 /give — Admin only, give credits to someone\n\n"
        "🔥 **Play smart, survive, and earn money!** 🔥"
    )


@app.on_message(filters.command("bal"))
async def bal(_, m: Message):
    db = load_db()

    if m.reply_to_message:
        target = m.reply_to_message.from_user.id
        user = get_user(db, target)
        await m.reply(f"💰 Balance of **{target}**: **{user['balance']}$**")
        save_db(db)
        return

    user = get_user(db, m.from_user.id)

    all_bal = sorted(
        [(uid, data["balance"]) for uid, data in db.items()],
        key=lambda x: x[1], reverse=True
    )
    rank = [u[0] for u in all_bal].index(str(m.from_user.id)) + 1

    await m.reply(
        f"🏦 Your Balance: **{user['balance']}$**\n"
        f"🌍 World Rank: **#{rank}**"
    )
    save_db(db)


@app.on_message(filters.command("kill"))
async def kill(_, m: Message):
    if not m.reply_to_message:
        await m.reply("❗ Reply to someone to kill them.")
        return

    db = load_db()
    killer = m.from_user.id
    target = m.reply_to_message.from_user.id

    if target in ADMIN_IDS:
        await m.reply("🛡 Admins cannot be killed.")
        return

    tuser = get_user(db, target)

    if not tuser["alive"]:
        await m.reply("💀 User is already dead.")
        return

    if now() < tuser["protection_until"]:
        await m.reply("🛡 User is protected. You cannot kill them.")
        return

    tuser["alive"] = False
    killer_user = get_user(db, killer)
    killer_user["balance"] += 100
    save_db(db)

    await m.reply(f"🔪 **{target} has been killed!**\n💵 You earned 100$")


@app.on_message(filters.command("rob"))
async def rob(_, m: Message):
    if not m.reply_to_message:
        await m.reply("❗ Reply to someone to rob.")
        return

    parts = m.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        await m.reply("❗ Usage: /rob amount (reply to user)")
        return

    amt = int(parts[1])
    db = load_db()
    robber = m.from_user.id
    target = m.reply_to_message.from_user.id

    if target in ADMIN_IDS:
        await m.reply("🛡 Admins cannot be robbed.")
        return

    tuser = get_user(db, target)
    ruser = get_user(db, robber)

    if tuser["balance"] < amt:
        await m.reply("❗ User doesn't have enough money.")
        return

    tuser["balance"] -= amt
    ruser["balance"] += amt
    save_db(db)

    await m.reply(f"🕵️‍♂️ You stole **{amt}$** from {target}!")


@app.on_message(filters.command("protect"))
async def protect(_, m: Message):
    parts = m.text.split()
    if len(parts) < 2:
        await m.reply("❗ Use: /protect 1d or /protect 2d")
        return

    days = parts[1].replace("d", "")
    if not days.isdigit():
        await m.reply("❗ Invalid duration.")
        return

    days = int(days)
    if days < 1 or days > 2:
        await m.reply("❗ Max protection is 2 days.")
        return

    cost = 200 * days
    db = load_db()
    user = get_user(db, m.from_user.id)

    if user["balance"] < cost:
        await m.reply("❗ Not enough balance.")
        return

    user["balance"] -= cost
    user["protection_until"] = now() + days * 86400
    save_db(db)

    await m.reply(f"🛡 Protection activated for {days} day(s)!")


@app.on_message(filters.command("revive"))
async def revive(_, m: Message):
    db = load_db()
    user = get_user(db, m.from_user.id)

    if user["alive"]:
        await m.reply("❗ You are already alive.")
        return

    if user["balance"] < 1000:
        await m.reply("❗ You need 1000$ to revive.")
        return

    user["balance"] -= 1000
    user["alive"] = True
    save_db(db)

    await m.reply("❤️ You have been revived!")


@app.on_message(filters.command("give"))
async def give(_, m: Message):
    if m.from_user.id not in ADMIN_IDS:
        await m.reply("❗ Admin only.")
        return

    if not m.reply_to_message:
        await m.reply("❗ Reply to someone to give money.")
        return

    parts = m.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        await m.reply("❗ Usage: /give amount (reply)")
        return

    amt = int(parts[1])
    db = load_db()
    target = m.reply_to_message.from_user.id
    user = get_user(db, target)
    user["balance"] += amt
    save_db(db)

    await m.reply(f"💳 Added **{amt}$** to {target}!")


# ---------------- RUN ---------------- #

app.run()
