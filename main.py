 import os
import re
import uuid
import asyncio
import threading
from telethon import TelegramClient, events
from telethon.sessions import StringSession
import telebot
from telebot import types

# 1. Credentials
API_ID = 31800390
API_HASH = "41c07303eb651fccda2ff90957d1ded6"
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
SESSION_STRING = "1BVtsOKwBu0_woOgzB1A9opoKGx_QhsHug1kc8mrtVgjoHS-yaKl_eTYiCNAonHtqO5NHwf6_TSAxT6hRd8IuCPNqP1PIxYSJ8JNk4jbH9zkxujqyMPnwY98SfiX_slhZSFX2J9XdJ4-b1-Y3fUgzxvQa5XH0l1xJFjBXwtNKJQNk-zXm3nS5JPQuhafuckdHhrlPoOddPVMEXAfizN86pggqrUHY8bMeTifWgHdmj8FqK2GrIc6HGzthiaQ5iIlF-WLXHWNDOdkne3iUFONowwW-q76ioUwG1wTAf_bcmkY-HDUUMLqzadj1YxU1zVr0WP5ncoPJvURL3eo9f-1Ds35Zo48u8Is="

# 2. Source channel and owner
SOURCE_CHANNEL = -1003280015883  # "X Stock Updates" private channel
OWNER_ID = 7034610665

# 3. Live filter settings — updated at runtime via /set_filter
#    require_*_no = True  → listing MUST have that field = No/False to pass
#    require_*_no = False → that field is not checked
FILTER = {
    "enabled": True,
    "min_balance": 1.00,
    "max_balance": 20.00,
    "require_paypal_no": True,  # skip listing if Used PayPal  != No
    "require_google_no": True,  # skip listing if Used Google  != No
    "require_registered_no": True,  # skip listing if Registered   != No/False
}

bot = telebot.TeleBot(BOT_TOKEN)
pending_purchases = {}

# Runtime state — mutated by /filter_on, /filter_off, /pause, /resume
STATE = {
    "paused": False,  # when True, scraper silently drops all messages
}

# ── Listing parser ─────────────────────────────────────────────────────────────


def parse_listing(text: str) -> dict:
    result = {"raw": text}

    m = re.search(r"[Bb]alance[:\s]+\$?([\d,]+\.?\d*)\s*(?:USD)?", text)
    if m:
        result["balance"] = float(m.group(1).replace(",", ""))

    m = re.search(r"[Uu]sed\s*[Pp]ay[Pp]al[:\s]+(Yes|No)", text)
    if m:
        result["used_paypal"] = m.group(1).strip()

    m = re.search(r"[Uu]sed\s*[Gg]oogle[:\s]+(Yes|No)", text)
    if m:
        result["used_google"] = m.group(1).strip()

    m = re.search(r"[Rr]egistered[:\s]+(Yes|No|True|False)", text, re.I)
    if m:
        val = m.group(1).strip()
        result["registered"] = "No" if val.lower() in ("no", "false") else "Yes"

    m = re.search(r"[Ll]isting\s*[Ii][Dd]?[:\s#]+(\w+)", text)
    if m:
        result["listing_id"] = m.group(1)

    return result


# ── /set_filter parser ────────────────────────────────────────────────────────


def parse_set_filter_args(args: str) -> tuple[dict, list[str]]:
    """
    Parse args like: balance:1-50 paypal:No google:No registered:False
    Returns (updates_dict, errors_list).
    """
    updates = {}
    errors = []

    for token in args.strip().split():
        if ":" not in token:
            errors.append(f"Unrecognised token `{token}` (use key:value)")
            continue

        key, _, value = token.partition(":")
        key = key.lower().strip()
        value = value.strip()

        if key == "balance":
            if "-" in value:
                parts = value.split("-", 1)
                try:
                    lo, hi = float(parts[0]), float(parts[1])
                    updates["min_balance"] = lo
                    updates["max_balance"] = hi
                except ValueError:
                    errors.append(f"Invalid balance range `{value}` — use `1-50`")
            else:
                errors.append(f"Balance needs a range like `1-50`, got `{value}`")

        elif key in ("paypal", "used_paypal"):
            # No/False → require listing to have Used PayPal = No
            # Yes/True → don't enforce Used PayPal field
            if value.lower() in ("no", "false"):
                updates["require_paypal_no"] = True
            elif value.lower() in ("yes", "true"):
                updates["require_paypal_no"] = False
            else:
                errors.append(f"Invalid paypal value `{value}` — use Yes/No")

        elif key in ("google", "used_google"):
            if value.lower() in ("no", "false"):
                updates["require_google_no"] = True
            elif value.lower() in ("yes", "true"):
                updates["require_google_no"] = False
            else:
                errors.append(f"Invalid google value `{value}` — use Yes/No")

        elif key in ("registered",):
            if value.lower() in ("no", "false"):
                updates["require_registered_no"] = True
            elif value.lower() in ("yes", "true"):
                updates["require_registered_no"] = False
            else:
                errors.append(
                    f"Invalid registered value `{value}` — use Yes/No/True/False"
                )

        else:
            errors.append(
                f"Unknown key `{key}` — valid keys: balance, paypal, google, registered"
            )

    return updates, errors


def filter_summary() -> str:
    f = FILTER
    state = "🟢 *Active*" if f["enabled"] else "🔴 *Disabled* (all listings forwarded)"
    paypal_rule = "must be No  ✅" if f["require_paypal_no"] else "not checked"
    google_rule = "must be No  ✅" if f["require_google_no"] else "not checked"
    reg_rule = "must be No  ✅" if f["require_registered_no"] else "not checked"
    return (
        f"⚙️ *Filter Status:* {state}\n\n"
        f"• Balance: `${f['min_balance']:.2f} – ${f['max_balance']:.2f}`\n"
        f"• Used PayPal: `{paypal_rule}`\n"
        f"• Used Google: `{google_rule}`\n"
        f"• Registered: `{reg_rule}`"
    )


# ── Auto-buy trigger ──────────────────────────────────────────────────────────


def trigger_auto_buy(listing: dict):
    listing_id = listing.get("listing_id", "N/A")
    balance = listing.get("balance", 0)
    print(f"[AUTO-BUY EXECUTED] Listing ID: {listing_id} | Balance: ${balance:.2f}")
    # TODO: Replace with your real purchase API call
    return True


# ── Confirmation prompt ───────────────────────────────────────────────────────


def send_confirmation_prompt(listing: dict):
    token = str(uuid.uuid4())[:8]
    pending_purchases[token] = listing

    balance = listing.get("balance", 0)
    paypal = listing.get("used_paypal", "?")
    google = listing.get("used_google", "?")
    registered = listing.get("registered", "?")
    listing_id = listing.get("listing_id", "N/A")

    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton("✅ Buy Now", callback_data=f"confirm_{token}"),
        types.InlineKeyboardButton("❌ Skip", callback_data=f"cancel_{token}"),
    )

    msg = (
        f"🚨 *Listing Matches Your Criteria!*\n\n"
        f"💰 Balance: `${balance:.2f}`\n"
        f"📋 Used PayPal: `{paypal}`\n"
        f"📋 Used Google: `{google}`\n"
        f"📋 Registered: `{registered}`\n"
        f"🆔 Listing ID: `{listing_id}`\n\n"
        f"*Full listing:*\n{listing.get('raw', '')[:800]}\n\n"
        f"⏳ Auto-skipped in 60 seconds if no action taken."
    )

    sent = bot.send_message(OWNER_ID, msg, parse_mode="Markdown", reply_markup=markup)
    print(f"[APPROVAL PROMPT SENT] token={token} balance=${balance:.2f}")

    # 60-second auto-expiry
    def auto_expire():
        if token not in pending_purchases:
            return  # already handled
        pending_purchases.pop(token, None)
        try:
            bot.edit_message_text(
                chat_id=OWNER_ID,
                message_id=sent.message_id,
                text=msg.split("\n\n⏳")[0]
                + "\n\n⌛ *Expired — listing auto-skipped after 60 seconds.*",
                parse_mode="Markdown",
            )
        except Exception:
            pass
        print(f"[EXPIRED] token={token} — auto-skipped after 60s")

    threading.Timer(60, auto_expire).start()


# ── Security layer ────────────────────────────────────────────────────────────


@bot.message_handler(func=lambda m: m.from_user.id != OWNER_ID)
def deny_unauthorized(message):
    print(f"[BLOCKED] Unauthorised access from ID {message.from_user.id}")
    bot.reply_to(message, "🚫 Access Denied.")


@bot.callback_query_handler(func=lambda call: call.from_user.id != OWNER_ID)
def deny_unauthorized_callback(call):
    bot.answer_callback_query(call.id, "🚫 Access Denied.", show_alert=True)


# ── Callbacks: Confirm / Cancel ───────────────────────────────────────────────


@bot.callback_query_handler(
    func=lambda c: c.data.startswith("confirm_") and c.from_user.id == OWNER_ID
)
def handle_confirm(call):
    token = call.data[len("confirm_") :]
    listing = pending_purchases.pop(token, None)
    if not listing:
        bot.answer_callback_query(call.id, "⚠️ Already handled.", show_alert=True)
        return
    bot.edit_message_reply_markup(
        call.message.chat.id, call.message.message_id, reply_markup=None
    )
    if trigger_auto_buy(listing):
        bot.send_message(
            OWNER_ID,
            f"✅ *Purchase Executed!*\n\n"
            f"💰 Balance: `${listing.get('balance', 0):.2f}`\n"
            f"🆔 Listing ID: `{listing.get('listing_id', 'N/A')}`",
            parse_mode="Markdown",
        )
        bot.answer_callback_query(call.id, "✅ Buying now!")
    else:
        bot.send_message(OWNER_ID, "❌ Purchase failed. Check logs.")
        bot.answer_callback_query(call.id, "❌ Failed.")


@bot.callback_query_handler(
    func=lambda c: c.data.startswith("cancel_") and c.from_user.id == OWNER_ID
)
def handle_cancel(call):
    token = call.data[len("cancel_") :]
    pending_purchases.pop(token, None)
    bot.edit_message_reply_markup(
        call.message.chat.id, call.message.message_id, reply_markup=None
    )
    bot.answer_callback_query(call.id, "❌ Cancelled.")
    bot.send_message(OWNER_ID, "❌ Purchase cancelled.")
    print(f"[CANCELLED] token={token}")


# ── Bot commands ──────────────────────────────────────────────────────────────


@bot.message_handler(commands=["start"], func=lambda m: m.from_user.id == OWNER_ID)
def cmd_start(message):
    bot.reply_to(
        message,
        "✅ *StockZone Scraper is active!*\n\n"
        "*Scraper control:*\n"
        "• /pause — stop receiving listing prompts\n"
        "• /resume — start receiving listing prompts again\n\n"
        "*Filter control:*\n"
        "• /filter\\_on — apply criteria before notifying\n"
        "• /filter\\_off — forward every listing (no criteria)\n"
        "• /set\\_filter — update filter values in one line\n\n"
        "*Info:*\n"
        "• /status — current state, filter settings, pending approvals\n\n"
        "*Example:*\n"
        "`/set_filter balance:1-50 paypal:No google:No registered:False`",
        parse_mode="Markdown",
    )


@bot.message_handler(commands=["status"], func=lambda m: m.from_user.id == OWNER_ID)
def cmd_status(message):
    scraper_state = "⏸ *Paused*" if STATE["paused"] else "▶️ *Running*"
    bot.reply_to(
        message,
        f"🤖 *Scraper:* {scraper_state}\n\n"
        + filter_summary()
        + f"\n\n• Pending approvals: `{len(pending_purchases)}`",
        parse_mode="Markdown",
    )


@bot.message_handler(
    commands=["toggle_filter"], func=lambda m: m.from_user.id == OWNER_ID
)
def cmd_toggle_filter(message):
    FILTER["enabled"] = not FILTER["enabled"]
    state = "🟢 *Active*" if FILTER["enabled"] else "🔴 *Disabled*"
    note = (
        "Criteria will be applied to incoming listings."
        if FILTER["enabled"]
        else "Every listing will be forwarded to you for manual review."
    )
    print(f"[FILTER TOGGLE] enabled={FILTER['enabled']}")
    bot.reply_to(
        message,
        f"Filter is now {state}\n\n{note}\n\n" + filter_summary(),
        parse_mode="Markdown",
    )


@bot.message_handler(commands=["filter_on"], func=lambda m: m.from_user.id == OWNER_ID)
def cmd_filter_on(message):
    if FILTER["enabled"]:
        bot.reply_to(message, "ℹ️ Filter is already *Active*.", parse_mode="Markdown")
        return
    FILTER["enabled"] = True
    print("[FILTER ON]")
    bot.reply_to(
        message,
        "✅ Filter is now 🟢 *Active*\n\nCriteria will be applied to incoming listings.\n\n"
        + filter_summary(),
        parse_mode="Markdown",
    )


@bot.message_handler(commands=["filter_off"], func=lambda m: m.from_user.id == OWNER_ID)
def cmd_filter_off(message):
    if not FILTER["enabled"]:
        bot.reply_to(message, "ℹ️ Filter is already *Disabled*.", parse_mode="Markdown")
        return
    FILTER["enabled"] = False
    print("[FILTER OFF]")
    bot.reply_to(
        message,
        "🔴 Filter is now *Disabled*\n\nEvery listing will be forwarded to you for manual review.\n\n"
        + filter_summary(),
        parse_mode="Markdown",
    )


@bot.message_handler(commands=["pause"], func=lambda m: m.from_user.id == OWNER_ID)
def cmd_pause(message):
    if STATE["paused"]:
        bot.reply_to(message, "ℹ️ Scraper is already *Paused*.", parse_mode="Markdown")
        return
    STATE["paused"] = True
    print("[SCRAPER PAUSED]")
    bot.reply_to(
        message,
        "⏸ *Scraper Paused*\n\nAll incoming listings will be silently dropped until you resume.\n\n"
        "Use /resume to start receiving listings again.",
        parse_mode="Markdown",
    )


@bot.message_handler(commands=["resume"], func=lambda m: m.from_user.id == OWNER_ID)
def cmd_resume(message):
    if not STATE["paused"]:
        bot.reply_to(message, "ℹ️ Scraper is already *Running*.", parse_mode="Markdown")
        return
    STATE["paused"] = False
    print("[SCRAPER RESUMED]")
    bot.reply_to(
        message,
        "▶️ *Scraper Resumed*\n\nListings will now be forwarded again.\n\n"
        + filter_summary(),
        parse_mode="Markdown",
    )


@bot.message_handler(commands=["set_filter"], func=lambda m: m.from_user.id == OWNER_ID)
def cmd_set_filter(message):
    args = message.text.partition(" ")[2].strip()

    if not args:
        bot.reply_to(
            message,
            "ℹ️ *Usage:*\n"
            "`/set_filter balance:1-50 paypal:No google:No registered:False`\n\n"
            "*Keys:* `balance`, `paypal`, `google`, `registered`\n"
            "*Values:* `balance` takes a range like `1-50`; others accept `Yes`/`No`/`True`/`False`",
            parse_mode="Markdown",
        )
        return

    updates, errors = parse_set_filter_args(args)

    if errors:
        bot.reply_to(
            message,
            "❌ *Errors in your command:*\n" + "\n".join(f"• {e}" for e in errors),
            parse_mode="Markdown",
        )
        return

    if not updates:
        bot.reply_to(message, "⚠️ No valid settings found in your command.")
        return

    FILTER.update(updates)
    print(f"[FILTER UPDATED] {updates}")

    bot.reply_to(
        message, "✅ *Filter updated!*\n\n" + filter_summary(), parse_mode="Markdown"
    )


# ── Scraper (Telethon) ────────────────────────────────────────────────────────


async def run_scraper():
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
    await client.connect()

    if not await client.is_user_authorized():
        print("ERROR: Session expired. Re-authentication required.")
        return

    me = await client.get_me()
    print(f"Logged in as: {me.first_name} (@{me.username})")
    print(f"Monitoring: X Stock Updates (ID {SOURCE_CHANNEL})")
    print(
        f"Criteria: PayPal=No, Google=No, Registered=No | Balance ${FILTER['min_balance']}–${FILTER['max_balance']}"
    )
    print("Scraper is running and listening...")

    @client.on(events.NewMessage(chats=SOURCE_CHANNEL))
    async def handler(event):
        text = event.message.text or ""
        if not text:
            return

        print(f"[NEW MESSAGE] {text[:60].replace(chr(10), ' ')}...")
        listing = parse_listing(text)

        # ── Paused: drop everything silently ─────────────────────────────────
        if STATE["paused"]:
            print("⏸ Scraper paused — listing dropped")
            return

        # ── Filter OFF: forward every listing ────────────────────────────────
        if not FILTER["enabled"]:
            print("📬 Filter DISABLED — forwarding listing to owner")
            send_confirmation_prompt(listing)
            return

        # ── Filter ON: apply criteria ─────────────────────────────────────────
        card_balance = listing.get("balance")
        used_paypal = listing.get("used_paypal")
        used_google = listing.get("used_google")
        registered = listing.get("registered")

        reasons = []

        # Each field must equal "No" when the corresponding require flag is set
        if FILTER["require_paypal_no"] and used_paypal != "No":
            reasons.append(f"Used PayPal = '{used_paypal}' (need No)")
        if FILTER["require_google_no"] and used_google != "No":
            reasons.append(f"Used Google = '{used_google}' (need No)")
        if FILTER["require_registered_no"] and registered != "No":
            reasons.append(f"Registered = '{registered}' (need No/False)")

        # Balance range check
        if card_balance is None:
            reasons.append("Balance not found in listing")
        elif not (FILTER["min_balance"] <= card_balance <= FILTER["max_balance"]):
            reasons.append(
                f"Balance ${card_balance:.2f} outside ${FILTER['min_balance']}–${FILTER['max_balance']}"
            )

        if reasons:
            print(f"⏭ Skipped — {'; '.join(reasons)}")
        else:
            print(
                f"✅ ALL CRITERIA MET — Balance: ${card_balance:.2f} | Sending approval prompt..."
            )
            send_confirmation_prompt(listing)

    await client.run_until_disconnected()


def start_bot_polling():
    print("Bot polling started (owner-only mode)...")
    bot.infinity_polling()


threading.Thread(target=start_bot_polling, daemon=True).start()
asyncio.run(run_scraper())
                
