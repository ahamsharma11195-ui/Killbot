import os
import json
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN") or "8436875930:AAHEGdIF1yZEU-s7M9Sc0sQKzfQfm52UFjQ"

DATA_FILE = "data.json"
data = {"users": {}, "admins": [6203351064, 8232605018, 5743410391]}

if os.path.exists(DATA_FILE):
    with open(DATA_FILE) as f:
        try: data.update(json.load(f))
        except: pass

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
        "🔪 Kill & Rob Game Started!\n\n"
        "Reply to anyone:\n"
        "💀 /kill → kill & earn $100\n"
        "💰 /bal → check balance\n"
        "🤑 /rob 500 → steal money\n"
        "⚡ /revive → revive ($1000)\n\n"
        "On yourself:\n"
        "🛡️ /protect 1d → $200 | /protect 2d → $400\n\n"
        "⚰️ Dead users can rob but cannot kill"
    )

async def kill(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg.reply_to_message: return
    killer = msg.from_user
    victim = msg.reply_to_message.from_user
    
    if victim.id in data["admins"]:
        return await msg.reply_text("😂 Admin is god! Can't kill")
    if victim.id == killer.id:
        return await msg.reply_text("❌ Suicide not allowed bro")

    k = get(killer.id)
    v = get(victim.id)

    if v.dead:
        return await msg.reply_text("⚰️ Already in graveyard!")

    if v.protected_until and datetime.fromisoformat(v.protected_until) > datetime.now():
        return await msg.reply_text("🛡️ Victim is protected right now!")

    v.dead = True
    v.protected_until = None
    k.balance += 100
    put(killer.id, k); put(victim.id, v)

    await msg.reply_text(
        f"☠️ {victim.first_name} has been MURDERED!\n"
        f"🩸 Killer {killer.first_name} earned $100"
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
    put(reviver.id, r); put(target.id, t)

    await msg.reply_text(
        f"⚡ {target.first_name} came back from hell!\n"
        f"💸 {reviver.first_name} paid $1000"
    )

async def bal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    target = msg.reply_to_message.from_user if msg.reply_to_message else msg.from_user
    u = get(target.id)
    status = "💀 DEAD" if u.dead else "✅ ALIVE"
    prot = ""
    if u.protected_until:
        left = datetime.fromisoformat(u.protected_until) - datetime.now()
        days = left.days
        hours = left.seconds // 3600
        prot = f" 🛡️ {days}d {hours}h left"
    
    await msg.reply_text(
        f"💰 {target.first_name}'s Profile\n"
        f"Status: {status}{prot}\n"
        f"Balance: ${u.balance:,}"
    )

async def protect(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.text.endswith(("1d", "2d")):
        return await update.message.reply_text("❌ Use: /protect 1d  or  /protect 2d")
    
    arg = update.message.text.strip().split()[-1]
    days = 1 if arg == "1d" else 2
    cost = days * 200
    u = get(update.effective_user.id)

    if u.balance < cost:
        return await update.message.reply_text(f"❌ Not enough money! Need ${cost}")

    u.balance -= cost
    u.protected_until = (datetime.now() + timedelta(days=days)).isoformat()
    put(update.effective_user.id, u)

    await update.message.reply_text(
        f"🛡️ Protection ON for {days} day(s)!\n"
        f"💸 Paid ${cost}\n"
        f"⏰ Expires in {days} days"
    )

async def rob(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg.reply_to_message or not context.args:
        return await msg.reply_text("❌ Reply someone's message → /rob 500")

    try:
        amount = int(context.args[0])
        if amount <= 0: raise ValueError
    except:
        return await msg.reply_text("❌ Enter valid amount")

    robber = msg.from_user
    victim = msg.reply_to_message.from_user

    if victim.id in data["admins"]:
        return await msg.reply_text("🚫 Can't rob Admin!")

    r = get(robber.id)
    v = get(victim.id)

    if v.dead:
        return await msg.reply_text("⚰️ You can't rob a dead body!")

    if v.protected_until and datetime.fromisoformat(v.protected_until) > datetime.now():
        return await msg.reply_text("🛡️ Victim is under protection!")

    if v.balance < amount:
        return await msg.reply_text(f"😢 Only has ${v.balance:,}")

    v.balance -= amount
    r.balance += amount
    put(robber.id, r); put(victim.id, v)

    await msg.reply_text(
        f"🤑 ROBBERY SUCCESS!\n"
        f"{robber.first_name} stole ${amount:,} from {victim.first_name}!"
    )

# Admin only
async def give(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in data["admins"]: return
    if not context.args or not update.message.reply_to_message:
        return await update.message.reply_text("Admin: Reply + /give 1000")
    
    try:
        amt = int(context.args[0])
        target = update.message.reply_to_message.from_user
        t = get(target.id)
        t.balance += amt
        put(target.id, t)
        await update.message.reply_text(f"✅ Admin gave ${amt:,} → {target.first_name}")
    except:
        await update.message.reply_text("Wrong format")

# Register handlers
app = Application.builder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.REPLY & filters.Command("kill"), kill))
app.add_handler(MessageHandler(filters.REPLY & filters.Command("bal"), bal))
app.add_handler(MessageHandler(filters.REPLY & filters.Command("revive"), revive))
app.add_handler(MessageHandler(filters.REPLY & filters.Regex(r'^/rob'), rob))
app.add_handler(CommandHandler("protect", protect))
app.add_handler(MessageHandler(filters.REPLY & filters.Command("give"), give))

print("Bot is live 24×7 with full emojis")
app.run_polling()
