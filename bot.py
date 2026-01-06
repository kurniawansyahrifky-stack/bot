import asyncio
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)
from telegram.constants import ChatMemberStatus
from telegram.error import BadRequest

# ================== TOKEN ==================
BOT_TOKEN = os.getenv("8247822535:AAHzZ2XGHcudqwHKJPPeHN050F4gOmduC0k")

# ================== CONFIG =================
BATCH_SIZE = 5
DELAY = 5

# ================== MEMORY =================
MEMBER_CACHE = {}
TAGALL_RUNNING = {}

WELCOME_ENABLED = True
WELCOME_TEXT = "👋 Selamat datang {name} di grup!"
WELCOME_PHOTO = None
WELCOME_BUTTONS = []

WAIT_TEXT = set()
WAIT_PHOTO = set()
WAIT_BTN_NAME = {}
WAIT_BTN_URL = {}

# ================== UTIL ===================
async def is_admin(update, context):
    m = await context.bot.get_chat_member(
        update.effective_chat.id,
        update.effective_user.id
    )
    return m.status in (
        ChatMemberStatus.ADMINISTRATOR,
        ChatMemberStatus.OWNER
    )

def cache_user(chat_id, user_id):
    MEMBER_CACHE.setdefault(chat_id, set()).add(user_id)

# ================== CAPTURE =================
async def capture_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.message.from_user
    cache_user(chat_id, user.id)

    global WELCOME_TEXT

    if chat_id in WAIT_TEXT:
        WELCOME_TEXT = update.message.text
        WAIT_TEXT.remove(chat_id)
        await update.message.reply_text("✅ Teks welcome disimpan")

    elif chat_id in WAIT_BTN_NAME:
        WAIT_BTN_URL[chat_id] = update.message.text
        WAIT_BTN_NAME.pop(chat_id)
        await update.message.reply_text("🔗 Sekarang kirim LINK button")

    elif chat_id in WAIT_BTN_URL:
        WELCOME_BUTTONS.append({
            "text": WAIT_BTN_URL.pop(chat_id),
            "url": update.message.text
        })
        await update.message.reply_text("✅ Button welcome ditambahkan")

async def capture_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    global WELCOME_PHOTO

    if chat_id in WAIT_PHOTO:
        WELCOME_PHOTO = update.message.photo[-1].file_id
        WAIT_PHOTO.remove(chat_id)
        await update.message.reply_text("✅ Foto welcome disimpan")

async def capture_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    for u in update.message.new_chat_members:
        cache_user(chat_id, u.id)

        if not WELCOME_ENABLED:
            return

        text = WELCOME_TEXT.format(name=u.first_name)

        kb = [
            [InlineKeyboardButton(b["text"], url=b["url"])]
            for b in WELCOME_BUTTONS
        ]
        markup = InlineKeyboardMarkup(kb) if kb else None

        if WELCOME_PHOTO:
            await update.message.reply_photo(
                WELCOME_PHOTO,
                caption=text,
                reply_markup=markup
            )
        else:
            await update.message.reply_text(text, reply_markup=markup)

# ================== TAGALL ==================
async def run_tagall(chat_id, context):
    TAGALL_RUNNING[chat_id] = True
    members = list(MEMBER_CACHE.get(chat_id, []))

    for i in range(0, len(members), BATCH_SIZE):
        if not TAGALL_RUNNING.get(chat_id):
            break

        batch = members[i:i + BATCH_SIZE]
        mentions = " ".join(
            f"[👤](tg://user?id={uid})" for uid in batch
        )

        await context.bot.send_message(
            chat_id,
            mentions,
            parse_mode="Markdown",
            disable_notification=True
        )

        await asyncio.sleep(DELAY)

    TAGALL_RUNNING[chat_id] = False
    await context.bot.send_message(chat_id, "✅ Tagall selesai")

# ================== COMMAND ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("🔔 Tagall", callback_data="tagall")],
        [InlineKeyboardButton("🎉 Welcome Setting", callback_data="welcome")],
        [InlineKeyboardButton("⛔ Stop Tagall", callback_data="stop")],
    ]
    await update.message.reply_text(
        "🤖 PANEL BOT ADMIN",
        reply_markup=InlineKeyboardMarkup(kb)
    )

async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return await update.message.reply_text("❌ Khusus admin")

    chat_id = update.effective_chat.id
    user = None
    title = "Admin"

    if update.message.reply_to_message:
        user = update.message.reply_to_message.from_user
        if context.args:
            title = " ".join(context.args)

    elif context.args:
        username = context.args[0].replace("@", "")
        if len(context.args) > 1:
            title = " ".join(context.args[1:])
        member = await context.bot.get_chat_member(chat_id, f"@{username}")
        user = member.user

    if not user:
        return await update.message.reply_text("⚠️ Reply pesan / username")

    try:
        await context.bot.promote_chat_member(
            chat_id,
            user.id,
            can_manage_chat=True,
            can_delete_messages=True,
            can_pin_messages=True,
            can_invite_users=True
        )
        await context.bot.set_chat_administrator_custom_title(
            chat_id, user.id, title
        )
        await update.message.reply_text(
            f"✅ {user.first_name} jadi admin\n🏷️ {title}"
        )
    except BadRequest as e:
        await update.message.reply_text(f"❌ {e.message}")

async def kick_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return await update.message.reply_text("❌ Khusus admin")

    if not update.message.reply_to_message:
        return await update.message.reply_text("⚠️ Reply user")

    user = update.message.reply_to_message.from_user
    await context.bot.ban_chat_member(update.effective_chat.id, user.id)
    await context.bot.unban_chat_member(update.effective_chat.id, user.id)
    await update.message.reply_text(f"👢 {user.first_name} dikeluarkan")

async def pin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return await update.message.reply_text("❌ Khusus admin")

    if not update.message.reply_to_message:
        return await update.message.reply_text("⚠️ Reply pesan")

    await context.bot.pin_chat_message(
        update.effective_chat.id,
        update.message.reply_to_message.message_id
    )
    await update.message.reply_text("📌 Pesan dipin")

# ================== BUTTON ==================
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    chat_id = q.message.chat.id

    if not await is_admin(update, context):
        return await q.message.reply_text("❌ Khusus admin")

    global WELCOME_ENABLED

    if q.data == "tagall":
        asyncio.create_task(run_tagall(chat_id, context))
        await q.message.reply_text("🔔 Tagall dimulai")

    elif q.data == "stop":
        TAGALL_RUNNING[chat_id] = False
        await q.message.reply_text("⛔ Tagall dihentikan")

    elif q.data == "welcome":
        kb = [
            [InlineKeyboardButton("ON / OFF", callback_data="w_toggle")],
            [InlineKeyboardButton("✏️ Ubah Teks", callback_data="w_text")],
            [InlineKeyboardButton("🖼️ Ubah Foto", callback_data="w_photo")],
            [InlineKeyboardButton("➕ Tambah Button", callback_data="w_btn")],
            [InlineKeyboardButton("🗑️ Hapus Button", callback_data="w_clear")]
        ]
        await q.message.reply_text(
            "🎉 Welcome Setting",
            reply_markup=InlineKeyboardMarkup(kb)
        )

    elif q.data == "w_toggle":
        WELCOME_ENABLED = not WELCOME_ENABLED
        await q.message.reply_text(
            f"Welcome {'ON' if WELCOME_ENABLED else 'OFF'}"
        )

    elif q.data == "w_text":
        WAIT_TEXT.add(chat_id)
        await q.message.reply_text("✏️ Kirim teks welcome baru")

    elif q.data == "w_photo":
        WAIT_PHOTO.add(chat_id)
        await q.message.reply_text("🖼️ Kirim foto welcome")

    elif q.data == "w_btn":
        WAIT_BTN_NAME[chat_id] = True
        await q.message.reply_text("✏️ Kirim NAMA button")

    elif q.data == "w_clear":
        WELCOME_BUTTONS.clear()
        await q.message.reply_text("🗑️ Semua button dihapus")

# ================== MAIN ==================
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_cmd))
    app.add_handler(CommandHandler("kick", kick_cmd))
    app.add_handler(CommandHandler("pin", pin_cmd))
    app.add_handler(CallbackQueryHandler(button))

    app.add_handler(
        MessageHandler(filters.TEXT & filters.ChatType.GROUPS, capture_text)
    )
    app.add_handler(
        MessageHandler(filters.PHOTO & filters.ChatType.GROUPS, capture_photo)
    )
    app.add_handler(
        MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, capture_join)
    )

    print("BOT JALAN...")
    app.run_polling()

if __name__ == "__main__":
    main()
