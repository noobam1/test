import os
import logging
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext
from dotenv import load_dotenv
from config import ADMINS

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def is_admin(user_id: int) -> bool:
    return user_id in ADMINS

def start(update: Update, context: CallbackContext):
    update.message.reply_text("🚀 Bot Active! Use /ban, /warn, /ai")

def ban(update: Update, context: CallbackContext):
    try:
        # Check if user is admin
        if not is_admin(update.effective_user.id):
            update.message.reply_text("❌ Only Admins can use this command!")
            return

        # Check if command is used in group
        if update.effective_chat.type == "private":
            update.message.reply_text("❌ This command works only in groups!")
            return

        # Check if replied to a message
        if not update.message.reply_to_message:
            update.message.reply_text("⚠️ Reply to a user's message to ban!")
            return

        target_user = update.message.reply_to_message.from_user

        # Check self-ban
        if target_user.id == context.bot.id:
            update.message.reply_text("🤖 I can't ban myself!")
            return

        # Check if target is admin
        chat_admins = context.bot.get_chat_administrators(update.effective_chat.id)
        admin_ids = [admin.user.id for admin in chat_admins]
        if target_user.id in admin_ids:
            update.message.reply_text("❌ Cannot ban admins!")
            return

        # Ban user with username mention
        username = target_user.username or target_user.first_name
        context.bot.ban_chat_member(update.effective_chat.id, target_user.id)
        update.message.reply_text(f"🚫 Banned [@{username}](tg://user?id={target_user.id})!", parse_mode="Markdown")
    except Exception as e:
        update.message.reply_text(f"Error: {str(e)}")

def warn(update: Update, context: CallbackContext):
    try:
        # Admin check
        if not is_admin(update.effective_user.id):
            update.message.reply_text("❌ Only Admins can use this command!")
            return

        # Group check
        if update.effective_chat.type == "private":
            update.message.reply_text("❌ This command works only in groups!")
            return

        # Reply check
        if not update.message.reply_to_message:
            update.message.reply_text("⚠️ Reply to a user's message to warn!")
            return

        target_user = update.message.reply_to_message.from_user

        # Self-warn check
        if target_user.id == context.bot.id:
            update.message.reply_text("🤖 I can't warn myself!")
            return

        # Admin target check
        chat_admins = context.bot.get_chat_administrators(update.effective_chat.id)
        admin_ids = [admin.user.id for admin in chat_admins]
        if target_user.id in admin_ids:
            update.message.reply_text("❌ Cannot warn admins!")
            return

        # Warn user with username mention
        username = target_user.username or target_user.first_name
        update.message.reply_text(f"⚠️ Warning sent to [@{username}](tg://user?id={target_user.id})!", parse_mode="Markdown")
    except Exception as e:
        update.message.reply_text(f"Error: {str(e)}")

def ai_chat(update: Update, context: CallbackContext):
    try:
        import openai
        openai.api_key = os.getenv("OPENAI_API_KEY")
        prompt = update.message.text.replace("/ai ", "")
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        update.message.reply_text(response.choices[0].message['content'])
    except Exception as e:
        update.message.reply_text(f"❌ AI Error: {str(e)}")

def main():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("ban", ban))
    dp.add_handler(CommandHandler("warn", warn))
    dp.add_handler(CommandHandler("ai", ai_chat))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()