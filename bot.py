import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    CallbackContext,
    CallbackQueryHandler
)
from dotenv import load_dotenv

# Load Environment Variables
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Enable Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Start Command
def start(update: Update, context: CallbackContext):
    user = update.effective_user
    update.message.reply_text(f"Namaste {user.first_name}! 🙏\nमैं आपका Telegram Bot हूँ।")

# Echo Message (For Testing)
def echo(update: Update, context: CallbackContext):
    text = update.message.text
    update.message.reply_text(f"आपने लिखा: {text}")

# Ban User (Admin Command)
def ban(update: Update, context: CallbackContext):
    if update.effective_user.id not in ADMINS:
        update.message.reply_text("⚠️ आपके पास Permission नहीं है!")
        return

    user_id = update.message.reply_to_message.from_user.id
    context.bot.ban_chat_member(update.effective_chat.id, user_id)
    update.message.reply_text("🚫 User को Ban कर दिया गया!")

# Warn User
def warn(update: Update, context: CallbackContext):
    user = update.message.reply_to_message.from_user
    warnings = context.chat_data.get(user.id, 0) + 1
    context.chat_data[user.id] = warnings

    if warnings >= 3:
        context.bot.ban_chat_member(update.effective_chat.id, user.id)
        update.message.reply_text(f"❌ {user.first_name} को 3 Warnings के बाद Ban किया गया!")
    else:
        update.message.reply_text(f"⚠️ Warning {warnings}/3: {user.first_name}")

# AI Chat (GPT-3.5 Integration)
def ai_chat(update: Update, context: CallbackContext):
    import openai
    openai.api_key = os.getenv("OPENAI_API_KEY")

    prompt = update.message.text
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )
    update.message.reply_text(response.choices[0].message['content'])

# Error Handler
def error(update: Update, context: CallbackContext):
    logger.warning(f'Update {update} caused error: {context.error}')

# Main Function
def main():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    # Commands
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("ban", ban))
    dp.add_handler(CommandHandler("warn", warn))
    dp.add_handler(CommandHandler("ai", ai_chat))

    # Messages
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, echo))

    # Errors
    dp.add_error_handler(error)

    # Start Bot
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()