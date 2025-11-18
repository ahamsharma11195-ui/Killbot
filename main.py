import os
import json
from datetime import datetime, timedelta
from pyrogram import Client, filters
from pyrogram.types import Message

BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"  # ⚠️ Change this!

ADMINS = [6203351064, 8232605018, 5743410391]

KILL_REWARD = 150
REVIVE_COST = 1000
PROTECT_COST_PER_DAY = 200

DATA_FILE = "data.json"

# Load or create database
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r") as f:
        users = json.load(f)
else:
    users = {}

def save():
    with open(DATA_FILE, "w") as f:
        json.dump(users, f, indent=4)

def get(uid):
    s = str(uid)
    if s not in users:
        users[s] = {"balance": 500, "alive": True, "protected_until": None, "kills": 0, "robs": 0}
        save()
    return users[s]

app = Client("KillGame", bot_token=BOT_TOKEN)

@app.on_message(filters.command("start"))
async def start(_, m: Message):
    await m.reply_text(
        "🔪 **KILL OR BE KILLED** 🔪\n\n"
        "Reply to anyone & use:\n"
        "• /kill → Eliminate & earn **$150** 💀\n"
        "• /rob 500 → Steal cash 💰\n"
        "• /bal → Check wallet 👛\n"
        "• /revive → Respawn (**$1000**) ☠️→👤\n"
        "• /protect 1d / 2d → Buy shield (**$200/day**) 🛡️\n"
        "• /top → Richest players 🏆\n"
        "• /stats → Your kills & robs ⚔️\n\n"
        "💀 Dead players can still rob — but can't be killed again!"
    )

@app.on_message(filters.command("bal"))
async def bal(_, m: Message):
    target = m.reply_to_message.from_user if m.reply_to_message else m.from_user
    u = get(target.id)
    status = "🟢 ALIVE" if u["alive"] else "🔴 DEAD"
    shield = "🛡️ Shield Active"
    if u["protected_until"]:
        try:
            until = datetime.fromisoformat(u["protected_until"])
            if datetime.utcnow() < until:
                rem = until - datetime.utcnow()
                days, hours = rem.days, rem.seconds // 3600
                shield = f"🛡️ Shield: {days}d {hours}h left"
            else:
                shield = "❌ Shield Expired"
        except:
            shield = "❌ No Shield"
    else:
        shield = "❌ No Shield"

    await m.reply_text(
        f"**{target.first_name}'s Profile** 👤\n\n"
        f"💰 Balance: **${u['balance']}**\n"
        f"❤️ Status: {status}\n"
        f"{shield}"
    )

@app.on_message(filters.command("kill") & filters.reply)
async def kill(_, m: Message):
    victim_user = m.reply_to_message.from_user
    if victim_user.id in ADMINS:
        return await m.reply_text("😂 Admin is immortal, bro!")

    victim = get(victim_user.id)
    if not victim["alive"]:
        return await m.reply_text("💀 He's already dead!")

    if victim["protected_until"]:
        try:
            if datetime.utcnow() < datetime.fromisoformat(victim["protected_until"]):
                return await m.reply_text("🛡️ Target is protected right now!")
        except:
            pass

    victim["alive"] = False
    killer = get(m.from_user.id)
    killer["balance"] += KILL_REWARD
    killer["kills"] += 1
    save()

    await m.reply_text(
        f"💀 **{victim_user.first_name} GOT FUCKING WASTED!** 🔫\n"
        f"🏆 **+${KILL_REWARD}** → {m.from_user.first_name}"
    )

@app.on_message(filters.command("rob") & filters.reply)
async def rob(_, m: Message):
    if len(m.command) < 2:
        return await m.reply_text("❌ Usage: `/rob <amount>`")
    try:
        amount = int(m.command[1])
        if amount <= 0: raise ValueError
    except:
        return await m.reply_text("❌ Enter a valid amount!")

    victim_user = m.reply_to_message.from_user
    if victim_user.id in ADMINS:
        return await m.reply_text("😈 You can't rob an Admin!")

    victim = get(victim_user.id)
    if victim["balance"] < amount:
        return await m.reply_text("😂 Bro is broke! Not enough money.")

    if victim["protected_until"] and datetime.utcnow() < datetime.fromisoformat(victim["protected_until"]):
        return await m.reply_text("🛡️ Can't rob — shield is active!")

    victim["balance"] -= amount
    get(m.from_user.id)["balance"] += amount
    get(m.from_user.id)["robs"] += 1
    save()

    await m.reply_text(f"💰 **${amount} STOLEN** from {victim_user.first_name}!")

@app.on_message(filters.command("revive"))
async def revive(_, m: Message):
    u = get(m.from_user.id)
    if u["alive"]:
        return await m.reply_text("✅ You're already alive!")
    if u["balance"] < REVIVE_COST:
        return await m.reply_text(f"❌ Need **${REVIVE_COST}** to revive!")
    
    u["alive"] = True
    u["balance"] -= REVIVE_COST
    save()
    await m.reply_text(f"☠️→👤 **YOU'RE BACK FROM THE DEAD!** (-${REVIVE_COST})")

@app.on_message(filters.command("protect"))
async def protect(_, m: Message):
    if len(m.command) != 2 or m.command[1] not in ["1d", "2d"]:
        return await m.reply_text("❌ Use: `/protect 1d` or `/protect 2d`")
    
    days = int(m.command[1][0])
    cost = days * PROTECT_COST_PER_DAY
    u = get(m.from_user.id)
    
    if u["balance"] < cost:
        return await m.reply_text(f"❌ Need **${cost}** for {days}-day shield!")
    
    until = (datetime.utcnow() + timedelta(days=days)).isoformat()
    u["protected_until"] = until
    u["balance"] -= cost
    save()
    
    await m.reply_text(f"🛡️ **{days}-DAY SHIELD ACTIVATED!** (-${cost})")

@app.on_message(filters.command("top"))
async def top(_, m: Message):
    if not users:
        return await m.reply_text("👻 No players yet!")
    
    top10 = sorted(users.items(), key=lambda x: x[1]["balance"], reverse=True)[:10]
    text = "🏆 **TOP 10 RICHEST** 🏆\n\n"
    for rank, (uid, data) in enumerate(top10, 1):
        try:
            user = await app.get_users(int(uid))
            name = user.first_name
        except:
            name = "Unknown User"
        text += f"{rank}. {name} → **${data['balance']}**\n"
    await m.reply_text(text)

@app.on_message(filters.command("stats"))
async def stats(_, m: Message):
    u = get(m.from_user.id)
    status = "🟢 ALIVE" if u["alive"] else "🔴 DEAD"
    await m.reply_text(
        f"⚔️ **YOUR STATS** ⚔️\n\n"
        f"💰 Balance: **${u['balance']}**\n"
        f"❤️ Status: {status}\n"
        f"🔪 Kills: **{u.get('kills', 0)}**\n"
        f"🤑 Robs: **{u.get('robs', 0)}**"
    )

print("Bot is running — GO KILL EVERYONE 🔫")
app.run()
