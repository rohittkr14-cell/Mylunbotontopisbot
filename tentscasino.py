from telethon import TelegramClient, events, Button
from telethon.tl.types import InputMediaDice
import sqlite3
import re
import asyncio

API_ID = 37893084
API_HASH = "853a6c0f3be11009f667bc153244452e"
BOT_TOKEN = "8665954893:AAHHTNNTNiyXAPZxf2-6p197mRB0RLwBo4w"

GROUP_ID = -1003382668169
ADMIN_IDS = [7691071175]

UPI_ID = "zioxrohit@fam"
CRYPTO_WALLET = "UQDdN_wiNuA8PLtLtsq6A-jkoUxoz47j5lgF4YOg04GvBTyS"

USD_RATE = 98

client = TelegramClient("casino",API_ID,API_HASH).start(bot_token=BOT_TOKEN)

# ---------------- DATABASE ----------------

db = sqlite3.connect("casino.db")
cur = db.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS users(
user_id INTEGER PRIMARY KEY,
balance REAL DEFAULT 0,
wins INTEGER DEFAULT 0,
games INTEGER DEFAULT 0
)
""")

db.commit()

games={}
deposits={}
withdraws={}

# ---------------- USER ----------------

def get_user(uid):
    cur.execute("SELECT balance,wins,games FROM users WHERE user_id=?",(uid,))
    r=cur.fetchone()
    if not r:
        cur.execute("INSERT INTO users(user_id) VALUES(?)",(uid,))
        db.commit()
        return 0,0,0
    return r

def update_balance(uid,amt):
    cur.execute("UPDATE users SET balance = balance + ? WHERE user_id=?",(amt,uid))
    db.commit()

async def get_username(uid):
    try:
        user = await client.get_entity(uid)
        return user.first_name or f"User{uid}"
    except:
        return f"User{uid}"

# ---------------- START ----------------

@client.on(events.NewMessage(pattern="/start"))
async def start(e):
    text="""
🎰 ULTIMATE DICE CASINO GAME BOT

🎲 Real Dice
💰 Real Balance
🔥 1.9x Payout Per Win 
   Add Your Funds and Play 
"""
    btns=[
    [Button.url("🎲 PLAY","https://t.me/frmchats")],
    [Button.inline("💰 BALANCE","bal"),Button.inline("🏆 LEADERBOARD","top")],
    [Button.inline("➕ DEPOSIT","dep"),Button.inline("💸 WITHDRAW","wd")]
    ]
    await e.respond(text,buttons=btns)

# ---------------- BALANCE ----------------

@client.on(events.CallbackQuery(data=b"bal"))
async def bal(e):
    bal,wins,games_count=get_user(e.sender_id)
    rate=(wins/games_count*100) if games_count else 0
    await e.edit(f"""
💰 Balance ${bal:.2f}

🏆 Wins {wins}
🎮 Games {games_count}

📊 Winrate {rate:.1f}%
""")

# ---------------- LEADERBOARD ----------------

@client.on(events.CallbackQuery(data=b"top"))
async def top(e):
    cur.execute("SELECT user_id,wins FROM users ORDER BY wins DESC LIMIT 10")
    rows=cur.fetchall()
    txt="🏆 TOP PLAYERS\n\n"
    for i,r in enumerate(rows,1):
        txt+=f"{i}. `{r[0]}` — {r[1]} wins\n"
    await e.edit(txt)

# ---------------- DICE START ----------------

@client.on(events.NewMessage(pattern=r"/dice (\d+)"))
async def dice_start(e):
    if e.chat_id!=GROUP_ID:
        return
    bet=float(e.pattern_match.group(1))
    uid=e.sender_id
    bal,_,_=get_user(uid)
    if bal<bet:
        return await e.reply("Low balance")
    
    username = await get_username(uid)
    
    btns=[
    [Button.inline("🎯 1 POINT",f"target_1_{bet}")],
    [Button.inline("🎯 2 POINTS",f"target_2_{bet}")],
    [Button.inline("🎯 3 POINTS",f"target_3_{bet}")]
    ]
    
    await e.reply(f"🎲 {username} wants to play Dice against the bot!\n\nBet: ${bet:.2f}\nPayout: ${bet*1.9:.2f} 1.9x\n\nSelect target points:", buttons=btns)

# ---------------- TARGET SELECT ----------------

@client.on(events.CallbackQuery(pattern=rb"target_(\d+)_(\d+\.?\d*)"))
async def set_target(e):
    target=int(e.pattern_match.group(1))
    bet=float(e.pattern_match.group(2))
    uid=e.sender_id
    
    update_balance(uid, -bet)
    
    username = await get_username(uid)
    
    start_msg = f"""🎲 {username} wants to play Dice against the bot!

Mode: Normal 
First to: {target} point(s)
Bet: ${bet:.2f}
Payout: ${bet*1.9:.2f} 1.9x

👤 {username}, it's your turn."""
    
    games[uid] = {
        "bet": bet, 
        "user_points": 0, 
        "bot_points": 0, 
        "target": target,
        "waiting_roll": True,
        "username": username
    }
    
    await e.edit(start_msg)

# ---------------- DICE ----------------

@client.on(events.NewMessage(func=lambda e: e.dice))
async def dice(e):
    uid=e.sender_id
    if uid not in games or e.chat_id!=GROUP_ID or not games[uid]["waiting_roll"]:
        return
    
    game = games[uid]
    username = game["username"]
    
    # User rolled
    user_roll = e.dice.value
    
    # Bot roll
    bot_msg = await client.send_message(e.chat_id, file=InputMediaDice(emoticon="🎲"))
    bot_roll = bot_msg.media.value
    
    # Result
    if user_roll > bot_roll:
        game["user_points"] += 1
        result = f"🏆 {username} wins this round!"
    elif bot_roll > user_roll:
        game["bot_points"] += 1
        result = f"👺 Bot wins this round!"
    else:
        result = f"🤝 It's a TIE!"
    
    result_msg = f"{result}\n\nYou: 🎲{user_roll} | Bot: 🎲{bot_roll}\n\nScores:\n👤 Bot • {game['bot_points']}\n👤 {username} • {game['user_points']}"
    
    # Check win
    if game["user_points"] >= game["target"]:
        win = game["bet"] * 1.9
        update_balance(uid, game["bet"] + win)
        cur.execute("UPDATE users SET wins=wins+1,games=games+1 WHERE user_id=?", (uid,))
        db.commit()
        result_msg += f"\n\n🎉 {username} WINS THE GAME!\n+${win:.2f}"
        del games[uid]
    elif game["bot_points"] >= game["target"]:
        cur.execute("UPDATE users SET games=games+1 WHERE user_id=?", (uid,))
        db.commit()
        result_msg += f"\n\n😢 Bot wins the game!"
        del games[uid]
    else:
        result_msg += f"\n\n🎰 Waiting...\n🪙 Next round: {username}, it's your turn."
        game["waiting_roll"] = True
    
    await e.reply(result_msg)

# ---------------- DEPOSIT ----------------

@client.on(events.CallbackQuery(data=b"dep"))
async def dep(e):
    btns=[
    [Button.inline("💳 UPI","dep_upi")],
    [Button.inline("₿ USDT","dep_usdt")]
    ]
    await e.edit("Select deposit method",buttons=btns)

@client.on(events.CallbackQuery(data=b"dep_upi"))
async def dep_upi(e):
    btns=[
    [Button.inline("₹100","upi_100"),Button.inline("₹500","upi_500")],
    [Button.inline("₹1000","upi_1000")],
    [Button.inline("Custom","upi_custom")]
    ]
    await e.edit(f"Send to UPI\n{UPI_ID}",buttons=btns)

@client.on(events.CallbackQuery(pattern=rb"upi_(\d+)"))
async def upi_amt(e):
    amt=int(e.pattern_match.group(1))
    usd=amt/USD_RATE
    deposits[e.sender_id]={"method":"upi","amt":usd,"step":"proof"}
    await e.respond("Send payment screenshot")

@client.on(events.CallbackQuery(pattern=rb"upi_custom"))
async def upi_custom(e):
    deposits[e.sender_id]={"method":"upi","waiting_amount":True}
    await e.respond("Enter custom INR amount")

@client.on(events.CallbackQuery(data=b"dep_usdt"))
async def dep_usdt(e):
    btns=[
    [Button.inline("💵 $5","usdt_5"),Button.inline("💵 $10","usdt_10")],
    [Button.inline("💵 $50","usdt_50")],
    [Button.inline("Custom USDT","usdt_custom")]
    ]
    await e.edit(f"Send USDT to\n{CRYPTO_WALLET}",buttons=btns)

@client.on(events.CallbackQuery(pattern=rb"usdt_(\d+)"))
async def usdt_amt(e):
    amt=float(e.pattern_match.group(1))
    deposits[e.sender_id]={"method":"usdt","amt":amt,"step":"proof"}
    await e.respond("Send transaction screenshot")

@client.on(events.CallbackQuery(pattern=rb"usdt_custom"))
async def usdt_custom(e):
    deposits[e.sender_id]={"method":"usdt","waiting_amount":True}
    await e.respond("Enter custom USDT amount")

# ---------------- WITHDRAW BUTTONS ----------------

@client.on(events.CallbackQuery(data=b"wd"))
async def wd(e):
    btns=[
    [Button.inline("💳 UPI","wd_upi")],
    [Button.inline("₿ USDT","wd_usdt")]
    ]
    await e.edit("Select withdraw method",buttons=btns)

@client.on(events.CallbackQuery(data=b"wd_upi"))
async def wd_upi(e):
    withdraws[e.sender_id]={"method":"upi","step":"amount"}
    await e.respond("Enter USD amount to withdraw (min $5)")

@client.on(events.CallbackQuery(data=b"wd_usdt"))
async def wd_usdt(e):
    withdraws[e.sender_id]={"method":"usdt","step":"amount"}
    await e.respond("Enter USDT amount to withdraw (min $5)")

# ---------------- WITHDRAW AMOUNT ONLY ----------------

@client.on(events.NewMessage(pattern=r"\d+(\.\d+)?"))
async def wd_amount_only(e):
    uid = e.sender_id
    text = e.text.strip()
    
    # Deposit amount first check
    if uid in deposits and deposits[uid].get("waiting_amount"):
        dep = deposits[uid]
        try:
            amt = float(text)
            usd = amt if dep["method"] == "usdt" else amt/USD_RATE
            dep["amt"] = usd
            del dep["waiting_amount"]
            dep["step"] = "proof"
            await e.reply("Send payment screenshot")
            return
        except:
            pass
    
    # Withdraw amount - ONLY when step="amount"
    if uid in withdraws and withdraws[uid]["step"] == "amount":
        wd = withdraws[uid]
        try:
            amt = float(text)
            bal, _, _ = get_user(uid)
            if amt < 5 or amt > bal:
                return await e.reply("❌ Invalid amount (min $5, max balance)")
            
            wd["amt"] = amt
            wd["step"] = "details"
            
            if wd["method"] == "upi":
                inr = amt * USD_RATE
                await e.reply(f"✅ Amount set: ${amt:.2f} (₹{int(inr)})\n\n**Send your UPI ID**")
            else:
                await e.reply(f"✅ Amount set: ${amt:.2f}\n\n**Send your wallet address**")
            return
        except:
            pass

# ---------------- WITHDRAW DETAILS ONLY ----------------

@client.on(events.NewMessage)
async def wd_details_only(e):
    uid = e.sender_id

    if uid not in withdraws:
        return

    wd = withdraws[uid]

    # only when waiting for details
    if wd.get("step") != "details":
        return

    # ignore numbers (amount message)
    if e.text.strip().replace('.', '', 1).isdigit():
        return

    details = e.text.strip()
    if not details:
        return

    amt = wd["amt"]

    # Deduct balance
    update_balance(uid, -amt)

    # Send to admin
    for admin in ADMIN_IDS:
        btns = [
            [Button.inline("✅ SEND", f"wdok_{uid}_{amt}_{wd['method']}")],
            [Button.inline("💰 REFUND", f"wdr_{uid}_{amt}")]
        ]

        msg = f"💸 Withdraw Request\nUser: `{uid}`\nAmount: ${amt:.2f}\n"

        if wd["method"] == "upi":
            msg += f"UPI: `{details}`"
        else:
            msg += f"Wallet: `{details}`"

        await client.send_message(admin, msg, buttons=btns)

    await e.reply("✅ Withdraw request sent to admin!")

    del withdraws[uid]

# ---------------- DEPOSIT PROOF ----------------

@client.on(events.NewMessage(func=lambda e: e.media))
async def deposit_proof(e):
    uid = e.sender_id
    if uid not in deposits:
        return
    
    dep = deposits[uid]
    if dep.get("step") != "proof":
        return
    
    for admin in ADMIN_IDS:
        btns = [
            [Button.inline("✅ APPROVE", f"depok_{uid}_{dep['amt']}"),
             Button.inline("❌ REJECT", f"depno_{uid}")]
        ]
        await client.send_message(
            admin,
            f"Deposit Request\nUser: `{uid}`\nMethod: {dep['method'].upper()}\nAmount: ${dep['amt']:.2f}",
            buttons=btns,
            file=e.media
        )
    
    await e.reply("✅ Deposit request sent to admin!")
    del deposits[uid]

# ---------------- ADMIN ACTIONS ----------------

@client.on(events.CallbackQuery(pattern=rb"depok_(\d+)_(\d+\.?\d*)"))
async def depok(e):
    uid = int(e.pattern_match.group(1))
    amt = float(e.pattern_match.group(2))
    update_balance(uid, amt)
    await client.send_message(uid, f"✅ Deposit approved!\n+${amt:.2f}")
    await e.answer("Approved ✅")

@client.on(events.CallbackQuery(pattern=rb"depno_(\d+)"))
async def depno(e):
    uid = int(e.pattern_match.group(1))
    await client.send_message(uid, "❌ Deposit rejected")
    await e.answer("Rejected ❌")

@client.on(events.CallbackQuery(pattern=rb"wdok_(\d+)_(\d+\.?\d*)_(\w+)"))
async def wdok(e):
    uid = int(e.pattern_match.group(1))
    await client.send_message(uid, "✅ Withdrawal sent! Check your wallet/UPI")
    await e.answer("Sent ✅")

@client.on(events.CallbackQuery(pattern=rb"wdr_(\d+)_(\d+\.?\d*)"))
async def wdr(e):
    uid = int(e.pattern_match.group(1))
    amt = float(e.pattern_match.group(2))
    # ADD BACK TO BALANCE
    update_balance(uid, amt)
    await client.send_message(uid, f"💰 Refunded +${amt:.2f} to your balance!")
    await e.answer("Refunded ✅")

print("🎲 CASINO BOT RUNNING")

client.run_until_disconnected()
