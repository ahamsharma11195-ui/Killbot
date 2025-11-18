import os
import json
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, filters
from pydantic import BaseModel

TOKEN = os.getenv("BOT_TOKEN")

DATA_FILE = "data.json"
data = {"users": {}, "admins": [6203351064, 8232605018, 5743410391]}

if os.path.exists(DATA_FILE):
    try:
        with open(DATA_FILE) as f:
            saved = json.load(f)
            data.update(saved)
    except:
        pass

def save():
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2, default=str)

class User(BaseModel):
    balance: int = 500
    dead: bool = False
    protected_until: str | None = None

def get(uid: int) -> User:
    sid = str(uid)
    if sid not in data["users"]:
        data["users"][sid] = User().model_dump()
        save()
    return User(**data["users"][sid])

def put(uid: int, user: User):
    data["users"][str(uid)] = user.model_dump()
    save()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔪 KILL & ROB GAME 🔥\n\n"
        "💀 Reply /kill → Kill target (+$100)\n"
        "💰 Reply /bal → Check balance\n"
        "🤑 Reply /rob 500 → Steal money\n"
        "⚡ Reply /revive → Revive ($1000)\n"
        "🛡️ /protect 1d ($200) or /protect 2d ($400)\n\n"
        "⚰️ Dead players can rob but CANNOT kill\n"
        "👑 Admins are immortal"
    )

async def kill(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg.reply_to_message: return
    
    killer = msg.from_user
    victim = msg.reply_to_message.from_user

    if victim.id in data["admins"]:
        return await msg.reply_text("😂 Admin is immortal!")

    if victim.id == killer.id:
        return await msg.reply_text("❌ You cannot kill yourself!")

    k = get(killer.id)
    v = get(victim.id)

    if v.dead:
        return await msg.reply_text("⚰️ Already dead!")

    if v.protected_until and datetime.fromisoformat(v.protected_until) > datetime.now():
        return await msg.reply_text("🛡️ Target is protected!")

    v.dead = True
    v.protected_until = None
    k.balance += 100
    put(killer.id, k)
    put(victim.id, v)

    await msg.reply_text(
        f"☠️ {victim.first_name} was BRUTALLY MURDERED!\n"
        f"🩸 {killer.first_name} earned $100 reward!"
    )

async def revive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    reviver = msg.from_user
    target = msg.reply_to_message.from_user if msg.reply_to_message else reviver
    
    r = get(reviver.id)
    t = get(target.id)

    if not t.dead:
        return await msg.reply_text("✅ Already alive!")

    if r.balance < 1000:
        return await msg.reply_text("❌ You need $1000 to revive!")

    r.balance -= 1000
    t.dead = False
    put(reviver.id, r)
    put(target.id, t)

    await msg.reply_text(
        f"⚡ {target.first_name} has been REVIVED!\n"
        f"💸 Paid by {reviver.first_name} (-$1000)"
    )

async def bal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = update.message.reply_to_message.from_user if update.message.reply_to_message else update.effective_user
    u = get(target.id)
    status = "💀 DEAD" if u.dead else "✅ ALIVE"
    shield = ""
    if u.protected_until:
        remaining = datetime.fromisoformat(u.protected_until) - datetime.now()
        h = remaining.seconds // 3600
        shield = f" 🛡️ {remaining.days}d {h}h left"

    await update.message.reply_text(
        f"💰 {target.first_name}'s Profile\n"
        f"Status: {status}{shield}\n"
        f"Balance: ${u.balance:,}"
    )

async def protect(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args or args[0] not in ["1d", "2d"]:
        return await update.message.reply_text("❌ Usage: /protect 1d or /protect 2d")

    days = 1 if args[0] == "1d" else 2
    cost = days * 200
    u = get(update.effective_user.id)

    if u.balance < cost:
        return await update.message.reply_text(f"❌ Not enough money! Need ${cost}")

    u.balance -= cost
    u.protected_until = (datetime.now() + timedelta(days=days)).isoformat()
    put(update.effective_user.id, u)

    await update.message.reply_text(
        f"🛡️ Protection activated for {days} day(s)!\n"
        f"💸 Cost: ${cost}\n"
        f"⏳ No one can kill you now!"
    )

async def rob(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message or not context.args:
        return await update.message.reply_text("❌ Reply to someone → /rob <amount>")

    try:
        amount = int(context.args[0])
        if amount <= 0: raise
    except:
        return await update.message.reply_text("❌ Invalid amount")

    robber = update.effective_user
    victim = update.message.reply_to_message.from_user

    if victim.id in data["admins"]:
        return await update.message.reply_text("🚫 Cannot rob admin!")

    r = get(robber.id)
    v = get(victim.id)

    if v.dead:
        return await msg.reply_text("⚰️ Cannot rob a dead body!")

    if v.protected_until and datetime.fromisoformat(v.protected_until) > datetime.now():
        return await msg.reply_text("🛡️ Target is protected!")

    if v.balance < amount:
        return await msg.reply_text(f"😭 Only has ${v.balance:,}")

    v.balance -= amount
    r.balance += amount
    put(robber.id, r)
    put(victim.id, v)

    await update.message.reply_text(
        f"🤑 ROBBERY SUCCESS!\n"
        f"{robber.first_name} stole ${amount:,} from {victim.first_name}!"
    )

async def give(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in data["admins"]: return
    if not context.args or not update.message.reply_to_message: return
    
    try:
        amount = int(context.args[0])
        target = update.message.reply_to_message.from_user
        t = get(target.id)
        t.balance += amount
        put(target.id, t)
        await update.message.reply_text(f"✅ Admin gave ${amount:,} to {target.first_name}")
    except:
        pass

# Run bot
app = Application.builder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("protect", protect))
app.add_handler(MessageHandler(filters.REPLY & filters.Command("kill"), kill))
app.add_handler(MessageHandler(filters.REPLY & filters.Command("bal"), bal))
app.add_handler(MessageHandler(filters.REPLY & filters.Command("revive"), revive))
app.add_handler(MessageHandler(filters.REPLY & filters.Regex(r'^/rob'), rob))
app.add_handler(MessageHandler(filters.REPLY & filters.Command("give"), give))

print("Bot running 24×7 🔥")
app.run_polling(drop_pending_updates=True)
