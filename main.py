import os, json
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from pydantic import BaseModel

TOKEN = os.getenv("BOT_TOKEN")
DATA_FILE = "data.json"
data = {"users": {}, "admins": [6203351064, 8232605018, 5743410391]}

if os.path.exists(DATA_FILE):
    try: data.update(json.load(open(DATA_FILE)))
    except: pass

def save():
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2, default=str)

class User(BaseModel):
    balance: int = 500
    dead: bool = False
    protected_until: str | None = None

def get(uid):
    s = str(uid)
    if s not in data["users"]:
        data["users"][s] = User().model_dump()
        save()
    return User(**data["users"][s])

def put(uid, u):
    data["users"][str(uid)] = u.model_dump()
    save()

async def start(update: Update, context):
    await update.message.reply_text(
        "KILL & ROB – TOTAL CARNAGE UNLEASHED\n\n"
        "Reply kisi ko:\n"
        "/kill → Maar daal +$100\n"
        "/bal → Paisa dekh\n"
        "/rob 500 → Loot le\n"
        "/revive → Zinda kar ($1000)\n\n"
        "Apne liye:\n"
        "/protect 1d ($200) │ /protect 2d ($400)\n\n"
        "Mara hua bhi loot sakta hai, kill nahi\n"
        "Admins ko haath nahi laga sakta koi\n\n"
        "Ab shuru kar de bhai — group jalne wala hai!"
    )

async def kill(update: Update, context):
    if not update.message.reply_to_message: return
    killer = update.effective_user
    victim = update.message.reply_to_message.from_user

    if victim.id in data["admins"]:
        return await update.message.reply_text("ADMIN KO HAATH LAGAYA? MAR GAYA TU")
    if victim.id == killer.id:
        return await update.message.reply_text("APNE AAP KO MAREGA? NAHI HOGA BHAI")

    k = get(killer.id)
    v = get(victim.id)

    if v.dead: return await update.message.reply_text("PEHLE HI MAR CHUKA HAI YE")
    if v.protected_until and datetime.fromisoformat(v.protected_until) > datetime.now():
        return await update.message.reply_text("PROTECTION HAI ABHI – HAATH JALEGA")

    v.dead = True
    v.protected_until = None
    k.balance += 100
    put(killer.id, k); put(victim.id, v)

    await update.message.reply_text(
        f"☠️ {victim.first_name} KO MAAR DIYA GAYA ☠️\n"
        f"🩸 {killer.first_name} KO MILA $100 INAAM 🩸\n"
        f"💀 AB YE GRAVEYARD MEIN HAI 💀"
    )

async def revive(update: Update, context):
    m = update.message
    r = m.from_user
    t = m.reply_to_message.from_user if m.reply_to_message else r
    rd = get(r.id)
    td = get(t.id)

    if not td.dead: return await m.reply_text("YE TO ZINDA HI HAI BC")
    if rd.balance < 1000: return await m.reply_text("PAISA NAHI HAI? NAHI UTHEGA YE")

    rd.balance -= 1000
    td.dead = False
    put(r.id, rd); put(t.id, td)

    await m.reply_text(
        f"⚡ {t.first_name} WAAPAS ZINDA HO GAYA ⚡\n"
        f"💸 {r.first_name} NE DI $1000 💸\n"
        f"🔥 WELCOME BACK BHAI 🔥"
    )

async def bal(update: Update, context):
    target = update.message.reply_to_message.from_user if update.message.reply_to_message else update.effective_user
    u = get(target.id)
    status = "💀 MARA HUA" if u.dead else "✅ ZINDA"
    shield = ""
    if u.protected_until:
        left = datetime.fromisoformat(u.protected_until) - datetime.now()
        h = left.seconds // 3600
        shield = f" | 🛡️ {left.days}d {h}h baki"

    await update.message.reply_text(
        f"👤 {target.first_name}\n"
        f"Status: {status}{shield}\n"
        f"💰 Paisa: ${u.balance:,} 💰"
    )

async def protect(update: Update, context):
    if not context.args or context.args[0] not in ["1d","2d"]:
        return await update.message.reply_text("GALAT! /protect 1d ya /protect 2d likh")
    days = 1 if context.args[0]=="1d" else 2
    cost = days*200
    u = get(update.effective_user.id)
    if u.balance < cost: return await update.message.reply_text(f"GAREEB! ${cost} chahiye")

    u.balance -= cost
    u.protected_until = (datetime.now() + timedelta(days=days)).isoformat()
    put(update.effective_user.id, u)

    await update.message.reply_text(
        f"🛡️ PROTECTION LAG GAYA {days} DIN KE LIYE!\n"
        f"💸 Kharcha: ${cost} 💸\n"
        f"⏰ Ab koi haath nahi laga sakta ⏰"
    )

async def rob(update: Update, context):
    if not update.message.reply_to_message or not context.args:
        return await update.message.reply_text("REPLY KARKE /rob 500 LIKH MADARCH*D")
    try: amount = int(context.args[0])
    except: return await update.message.reply_text("NUMBER THEEK SE LIKH")

    robber = update.effective_user
    victim = update.message.reply_to_message.from_user
    if victim.id in data["admins"]: return await update.message.reply_text("ADMIN KO LOOTEGA? MAR JA ABHI")

    r = get(robber.id)
    v = get(victim.id)

    if v.dead: return await update.message.reply_text("LASH SE LOOTEGA?")
    if v.protected_until and datetime.fromisoformat(v.protected_until) > datetime.now():
        return await update.message.reply_text("PROTECTION HAI – HAATH JALEGA")
    if v.balance < amount: return await update.message.reply_text(f"ISKE PAAS SIRF ${v.balance} HAI")

    v.balance -= amount
    r.balance += amount
    put(robber.id, r); put(victim.id, v)

    await update.message.reply_text(
        f"🤑 LOOT LIYA BC!\n"
        f"💰 {robber.first_name} ne {victim.first_name} se uda liye ${amount:,}!\n"
        f"😈 CRIME PAYS 😈"
    )

# BOT CHALAO
app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("protect", protect))
app.add_handler(MessageHandler(filters.REPLY & filters.Command("kill"), kill))
app.add_handler(MessageHandler(filters.REPLY & filters.Command("bal"), bal))
app.add_handler(MessageHandler(filters.REPLY & filters.Command("revive"), revive))
app.add_handler(MessageHandler(filters.REPLY & filters.Regex(r'^/rob'), rob))

print("KILL & ROB BOT FULL POWER MEIN LIVE HAI 24×7")
app.run_polling(drop_pending_updates=True)
