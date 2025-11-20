# main.py
# Full PRO Game Bot — JSON DB — Render-ready
# Requires: BOT_TOKEN environment variable (no API_ID / API_HASH / session strings)

import os
import json
import time
import random
from typing import Dict, Any, Optional
from datetime import datetime

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

# ---------------- CONFIG ----------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is required")

# Default admin IDs (override via ADMINS env if you want)
DEFAULT_ADMINS = [6203351064, 8232605018, 5743410391]
ADMINS_ENV = os.getenv("ADMINS", "")
ADMINS = set(DEFAULT_ADMINS + [int(x) for x in ADMINS_ENV.split(",") if x.strip()])

DB_FILE = "data.json"

# Game economics
KILL_REWARD = 100
REVIVE_COST = 1000
PROTECT_COST_PER_DAY = 200
PROTECT_MAX_DAYS = 2
DAILY_REWARD = 200
DAILY_COOLDOWN = 24 * 3600

# Cooldowns (seconds)
COOLDOWNS = {
    "kill": 5,
    "rob": 5,
    "protect": 3,
    "revive": 5,
    "daily": DAILY_COOLDOWN,
    "pvp": 10
}

# Shop example
SHOP = {
    "potion": {"price": 150, "desc": "Revive potion (use to revive instantly)"},
    "sword": {"price": 500, "desc": "Sword: cosmetic/for fun"},
    "shield": {"price": 400, "desc": "Shield: reduces chance (not used here)"}
}

# ---------------- DB UTILITIES ----------------
def load_db() -> Dict[str, Any]:
    if not os.path.exists(DB_FILE):
        db = {"users": {}}
        save_db(db)
        return db
    with open(DB_FILE, "r") as f:
        try:
            return json.load(f)
        except:
            return {"users": {}}

def save_db(db: Dict[str, Any]):
    with open(DB_FILE, "w") as f:
        json.dump(db, f, indent=2)

def now_ts() -> int:
    return int(time.time())

def ensure_user(db: Dict[str, Any], uid: int, name: Optional[str] = None) -> Dict[str, Any]:
    users = db.setdefault("users", {})
    k = str(uid)
    if k not in users:
        users[k] = {
            "id": uid,
            "name": name or f"User{uid}",
            "money": 500,
            "alive": True,
            "protect_until": 0,
            "kills": 0,
            "inventory": {},
            "last_actions": {},
            "daily_ts": 0,
            "xp": 0,
            "level": 1,
            "married": None
        }
        save_db(db)
    # update name if changed
    if name and users[k].get("name") != name:
        users[k]["name"] = name
        save_db(db)
    return users[k]

def in_protect(user: Dict[str, Any]) -> bool:
    return now_ts() < int(user.get("protect_until", 0))

def can_do(user: Dict[str, Any], action: str) -> bool:
    last = user.get("last_actions", {}).get(action, 0)
    cd = COOLDOWNS.get(action, 0)
    return (now_ts() - last) >= cd

def set_action_time(user: Dict[str, Any], action: str):
    user.setdefault("last_actions", {})[action] = now_ts()

def add_money(user: Dict[str, Any], amount: int):
    user["money"] = int(user.get("money", 0)) + int(amount)

def sub_money(user: Dict[str, Any], amount: int) -> bool:
    if int(user.get("money", 0)) < amount:
        return False
    user["money"] = int(user.get("money", 0)) - amount
    return True

def get_rank(db: Dict[str, Any], uid: int) -> int:
    users = list(db.get("users", {}).values())
    sorted_users = sorted(users, key=lambda x: x.get("money", 0), reverse=True)
    for idx, u in enumerate(sorted_users, start=1):
        if u["id"] == uid:
            return idx
    return len(sorted_users)

def level_up_check(user: Dict[str, Any]):
    # simple leveling system: +100 xp per action => level increases every 1000 xp
    xp = user.get("xp", 0)
    lvl = user.get("level", 1)
    while xp >= lvl * 1000:
        xp -= lvl * 1000
        lvl += 1
    user["xp"] = xp
    user["level"] = lvl

# ---------------- COMMANDS ----------------

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = load_db()
    ensure_user(db, update.effective_user.id, update.effective_user.first_name)
    text = (
        "🎮 *Welcome to Ultimate Game World!* 🎮\n\n"
        "⚔️ Reply to someone's message to interact with them.\n\n"
        "🔥 Commands (reply where required):\n"
        "• /bal — show profile (reply to see other's)\n"
        "• /kill — reply to kill (reward $100)\n"
        "• /rob <amount> — reply to rob (dead allowed) — 100% success if allowed\n"
        "• /protect <1d|2d> — buy protection (200$/day, max 2d)\n"
        "• /revive — revive yourself (cost $1000)\n"
        "• /daily — claim daily reward\n"
        "• /shop — show shop\n"
        "• /buy <item> — buy item\n"
        "• /inventory — show items\n"
        "• /leaderboard — top players\n"
        "• /pvp — reply to challenge\n"
        "• /marry — reply to propose\n"
        "• /give — admin only (reply + amount)\n\n"
        "🛡 Protected users cannot be killed or robbed.\n"
        "💀 Dead users cannot be killed but CAN be robbed (if not protected).\n"
        "👑 Admins are immune from rob/kill.\n\n"
        "Have fun — play fair! 🏆"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def cmd_bal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = load_db()
    if update.message.reply_to_message:
        t = update.message.reply_to_message.from_user
        tu = ensure_user(db, t.id, t.first_name)
        rank = get_rank(db, t.id)
        prot = "None" if not in_protect(tu) else f"{int((tu['protect_until'] - now_ts())/3600)}h left"
        status = "Dead 💀" if not tu["alive"] else "Alive ❤️"
        text = (
            f"💳 *Player Profile*\n\n"
            f"👤 *Name:* {tu['name']}\n"
            f"💰 *Money:* ${tu['money']}\n"
            f"🏆 *Rank:* #{rank}\n"
            f"🔪 *Kills:* {tu['kills']}\n"
            f"❤️ *Status:* {status}\n"
            f"🛡 *Protection:* {prot}\n"
            f"⭐ *Level:* {tu.get('level',1)}"
        )
        await update.message.reply_text(text, parse_mode="Markdown")
        return

    uid = update.effective_user.id
    u = ensure_user(db, uid, update.effective_user.first_name)
    rank = get_rank(db, uid)
    prot = "None" if not in_protect(u) else f"{int((u['protect_until'] - now_ts())/3600)}h left"
    status = "Dead 💀" if not u["alive"] else "Alive ❤️"
    text = (
        f"💳 *Your Profile*\n\n"
        f"👤 *Name:* {u['name']}\n"
        f"💰 *Money:* ${u['money']}\n"
        f"🏆 *Rank:* #{rank}\n"
        f"🔪 *Kills:* {u['kills']}\n"
        f"❤️ *Status:* {status}\n"
        f"🛡 *Protection:* {prot}\n"
        f"⭐ *Level:* {u.get('level',1)}"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def cmd_kill(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = load_db()
    if not update.message.reply_to_message:
        await update.message.reply_text("❗ Reply to someone's message with /kill to attempt a kill.")
        return
    killer = update.effective_user
    target_user = update.message.reply_to_message.from_user
    if target_user.id == killer.id:
        await update.message.reply_text("🤨 You cannot kill yourself.")
        return
    if target_user.id in ADMINS:
        await update.message.reply_text("🛡 Target is an admin — action blocked.")
        return

    k = ensure_user(db, killer.id, killer.first_name)
    t = ensure_user(db, target_user.id, target_user.first_name)

    if not t["alive"]:
        await update.message.reply_text("💀 Target is already dead.")
        return
    if in_protect(t):
        await update.message.reply_text("🛡 Target is protected — cannot kill.")
        return
    if not can_do(k, "kill"):
        await update.message.reply_text("⏳ Kill cooldown active. Try later.")
        return

    # perform kill
    t["alive"] = False
    k["kills"] = int(k.get("kills", 0)) + 1
    add_money(k, KILL_REWARD)
    set_action_time(k, "kill")
    k["xp"] = k.get("xp", 0) + 50
    level_up_check(k)
    db["users"][str(killer.id)] = k
    db["users"][str(target_user.id)] = t
    save_db(db)

    await update.message.reply_text(
        f"🔪 *Kill successful!* {k['name']} killed {t['name']}.\n💵 Reward: ${KILL_REWARD}",
        parse_mode="Markdown"
    )

async def cmd_rob(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = load_db()
    if not update.message.reply_to_message:
        await update.message.reply_text("❗ Reply to a user's message with /rob <amount> to attempt robbery.")
        return
    args = context.args
    if not args or not args[0].isdigit():
        await update.message.reply_text("❗ Usage: /rob <amount> (reply to target)")
        return
    amt = int(args[0])
    robber = update.effective_user
    target_user = update.message.reply_to_message.from_user

    if target_user.id == robber.id:
        await update.message.reply_text("❌ You cannot rob yourself.")
        return
    if target_user.id in ADMINS:
        await update.message.reply_text("🛡 Target is an admin — cannot rob.")
        return

    r = ensure_user(db, robber.id, robber.first_name)
    t = ensure_user(db, target_user.id, target_user.first_name)

    # Protection blocks rob too
    if in_protect(t):
        await update.message.reply_text("🛡 Target is protected — rob failed.")
        return
    if not can_do(r, "rob"):
        await update.message.reply_text("⏳ Rob cooldown active. Try later.")
        return

    # per your rule: dead users CAN be robbed; rob chance = 100% if allowed
    if t["money"] < amt:
        await update.message.reply_text("❗ Target doesn't have that much money.")
        return

    # success guaranteed
    t["money"] = int(t.get("money", 0)) - amt
    r["money"] = int(r.get("money", 0)) + amt
    set_action_time(r, "rob")
    r["xp"] = r.get("xp", 0) + 20
    level_up_check(r)
    db["users"][str(robber.id)] = r
    db["users"][str(target_user.id)] = t
    save_db(db)

    await update.message.reply_text(
        f"🕵️‍♂️ *Rob successful!* You stole ${amt} from {t['name']}.",
        parse_mode="Markdown"
    )

async def cmd_protect(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = load_db()
    args = context.args
    uid = update.effective_user.id
    u = ensure_user(db, uid, update.effective_user.first_name)
    if not args:
        await update.message.reply_text("❗ Use /protect 1d or /protect 2d")
        return
    arg = args[0].lower()
    if arg.endswith("d") and arg[:-1].isdigit():
        days = int(arg[:-1])
    elif arg.isdigit():
        days = int(arg)
    else:
        await update.message.reply_text("❗ Invalid format. Use /protect 1d or /protect 2d")
        return
    if days < 1 or days > PROTECT_MAX_DAYS:
        await update.message.reply_text(f"❗ Max protection = {PROTECT_MAX_DAYS} days.")
        return
    cost = PROTECT_COST_PER_DAY * days
    if u["money"] < cost:
        await update.message.reply_text(f"❗ You need ${cost} to buy protection for {days} day(s).")
        return
    u["money"] -= cost
    u["protect_until"] = now_ts() + days * 86400
    set_action_time(u, "protect")
    db["users"][str(uid)] = u
    save_db(db)
    await update.message.reply_text(f"🛡️ Protection active for {days} day(s). Cost: ${cost}")

async def cmd_revive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = load_db()
    uid = update.effective_user.id
    u = ensure_user(db, uid, update.effective_user.first_name)
    if u["alive"]:
        await update.message.reply_text("❗ You are already alive.")
        return
    if u["money"] < REVIVE_COST:
        await update.message.reply_text(f"❗ You need ${REVIVE_COST} to revive.")
        return
    u["money"] -= REVIVE_COST
    u["alive"] = True
    u["xp"] = u.get("xp", 0) + 30
    level_up_check(u)
    db["users"][str(uid)] = u
    save_db(db)
    await update.message.reply_text(f"❤️ You have been revived! ${REVIVE_COST} deducted.")

async def cmd_daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = load_db()
    uid = update.effective_user.id
    u = ensure_user(db, uid, update.effective_user.first_name)
    last = u.get("daily_ts", 0)
    if now_ts() - last < DAILY_COOLDOWN:
        remain = int((DAILY_COOLDOWN - (now_ts() - last)) / 3600)
        await update.message.reply_text(f"⏳ Daily already claimed. Come back in {remain}h.")
        return
    add_money(u, DAILY_REWARD)
    u["daily_ts"] = now_ts()
    u["xp"] = u.get("xp", 0) + 10
    level_up_check(u)
    db["users"][str(uid)] = u
    save_db(db)
    await update.message.reply_text(f"🎁 Daily claimed! You received ${DAILY_REWARD}.")

async def cmd_shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "🛒 *Shop Items:*\n"
    for key, it in SHOP.items():
        text += f"\n• *{key}* — ${it['price']} — {it['desc']}"
    text += "\n\nUse /buy <item>"
    await update.message.reply_text(text, parse_mode="Markdown")

async def cmd_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = load_db()
    uid = update.effective_user.id
    u = ensure_user(db, uid, update.effective_user.first_name)
    if not context.args:
        await update.message.reply_text("❗ Use /buy <item>")
        return
    item = context.args[0].lower()
    if item not in SHOP:
        await update.message.reply_text("❗ Item not found.")
        return
    price = SHOP[item]["price"]
    if u["money"] < price:
        await update.message.reply_text("❗ Not enough money.")
        return
    u["money"] -= price
    inv = u.setdefault("inventory", {})
    inv[item] = inv.get(item, 0) + 1
    db["users"][str(uid)] = u
    save_db(db)
    await update.message.reply_text(f"✅ You bought {item} for ${price}!")

async def cmd_inventory(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = load_db()
    uid = update.effective_user.id
    u = ensure_user(db, uid, update.effective_user.first_name)
    inv = u.get("inventory", {})
    if not inv:
        await update.message.reply_text("📦 Inventory empty.")
        return
    text = "📦 *Your Inventory:*\n"
    for k, v in inv.items():
        text += f"\n• {k} x{v}"
    await update.message.reply_text(text, parse_mode="Markdown")

async def cmd_give(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = load_db()
    uid = update.effective_user.id
    if uid not in ADMINS:
        await update.message.reply_text("❌ Admins only.")
        return
    if not update.message.reply_to_message:
        await update.message.reply_text("❗ Reply to someone to give money.")
        return
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("❗ Usage: /give <amount> (reply)")
        return
    amt = int(context.args[0])
    target = update.message.reply_to_message.from_user
    t = ensure_user(db, target.id, target.first_name)
    t["money"] += amt
    db["users"][str(target.id)] = t
    save_db(db)
    await update.message.reply_text(f"💳 Added ${amt} to {t['name']}")

async def cmd_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = load_db()
    users = list(db.get("users", {}).values())
    users_sorted = sorted(users, key=lambda x: x.get("money", 0), reverse=True)[:10]
    text = "🏆 *Leaderboard (Top 10)*\n\n"
    for i, u in enumerate(users_sorted, start=1):
        text += f"{i}. {u.get('name')} — ${u.get('money')}\n"
    await update.message.reply_text(text, parse_mode="Markdown")

# Simple PVP (challenge by reply)
async def cmd_pvp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = load_db()
    if not update.message.reply_to_message:
        await update.message.reply_text("❗ Reply to someone to challenge them to PVP.")
        return
    challenger = ensure_user(db, update.effective_user.id, update.effective_user.first_name)
    target_user = update.message.reply_to_message.from_user
    target = ensure_user(db, target_user.id, target_user.first_name)
    if challenger["dead"]:
        await update.message.reply_text("🔴 Dead can't PVP.")
        return
    if target["dead"]:
        await update.message.reply_text("❗ Target is dead. You can rob them instead.")
        return
    if not can_do(challenger, "pvp"):
        await update.message.reply_text("⏳ PVP cooldown active.")
        return
    # simple random outcome influenced by level
    power_a = challenger.get("level", 1) * random.randint(1, 6) + random.randint(0, 20)
    power_b = target.get("level", 1) * random.randint(1, 6) + random.randint(0, 20)
    set_action_time(challenger, "pvp")
    challenger["xp"] = challenger.get("xp", 0) + 20
    target["xp"] = target.get("xp", 0) + 10
    level_up_check(challenger); level_up_check(target)
    if power_a > power_b:
        loot = min(int(target.get("money", 0) * 0.05) + 50, target.get("money", 0))
        target["money"] -= loot
        challenger["money"] += loot
        challenger["kills"] += 1
        db["users"][str(challenger["id"])] = challenger
        db["users"][str(target["id"])] = target
        save_db(db)
        await update.message.reply_text(f"⚔️ *PVP:* {challenger['name']} defeated {target['name']} and looted ${loot}!", parse_mode="Markdown")
    else:
        await update.message.reply_text(f"⚔️ *PVP:* {target['name']} defended and won!", parse_mode="Markdown")

async def cmd_marry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = load_db()
    if not update.message.reply_to_message:
        await update.message.reply_text("❗ Reply to someone's message to propose.")
        return
    proposer = ensure_user(db, update.effective_user.id, update.effective_user.first_name)
    target_user = update.message.reply_to_message.from_user
    target = ensure_user(db, target_user.id, target_user.first_name)
    if proposer.get("married"):
        await update.message.reply_text("❗ You are already married.")
        return
    if target.get("married"):
        await update.message.reply_text("❗ Target is already married.")
        return
    # auto-accept for simplicity
    proposer["married"] = target_user.id
    target["married"] = proposer["id"]
    db["users"][str(proposer["id"])] = proposer
    db["users"][str(target_user.id)] = target
    save_db(db)
    await update.message.reply_text(f"💍 {proposer['name']} and {target['name']} are now married! Congratulations! 🎉")

# ---------------- APP SETUP ----------------
def build_app():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("bal", cmd_bal))
    app.add_handler(CommandHandler("kill", cmd_kill))
    app.add_handler(CommandHandler("rob", cmd_rob))
    app.add_handler(CommandHandler("protect", cmd_protect))
    app.add_handler(CommandHandler("revive", cmd_revive))
    app.add_handler(CommandHandler("daily", cmd_daily))
    app.add_handler(CommandHandler("shop", cmd_shop))
    app.add_handler(CommandHandler("buy", cmd_buy))
    app.add_handler(CommandHandler("inventory", cmd_inventory))
    app.add_handler(CommandHandler("give", cmd_give))
    app.add_handler(CommandHandler("leaderboard", cmd_leaderboard))
    app.add_handler(CommandHandler("pvp", cmd_pvp))
    app.add_handler(CommandHandler("marry", cmd_marry))

    return app

# ---------------- RUN ----------------
if __name__ == "__main__":
    print("Starting PRO Game Bot...")
    application = build_app()
    application.run_polling()
