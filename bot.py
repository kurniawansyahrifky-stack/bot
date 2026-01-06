import os
from telegram.ext import ApplicationBuilder, CommandHandler

BOT_TOKEN = os.getenv("8247822535:AAFWkMeAQT9x2G14lXQOE_8T5Py4ysWuw18")

async def start(update, context):
    await update.message.reply_text("BOT HIDUP")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    print("BOT JALAN")
    app.run_polling()

if __name__ == "__main__":
    main()
