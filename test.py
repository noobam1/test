# --------------------------
# SECTION 1: IMPORTS & SETUP
# --------------------------
import concurrent.futures
import heapq
import json
import os
import random
import threading
import time
from functools import wraps
from getpass import getpass
from typing import Dict, List

import pandas as pd
import requests
from bs4 import BeautifulSoup
from sklearn.datasets import load_iris
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from telegram import Update, ParseMode
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ---------------------------
# SECTION 2: CORE SYSTEMS
# ---------------------------

class UserManager:
    """Handles user accounts and coins"""
    
    USERS_FILE = "users.json"
    
    def __init__(self):
        self.users = self._load_users()
        self.broadcasts = []

    def _load_users(self):
        if os.path.exists(self.USERS_FILE):
            with open(self.USERS_FILE) as f:
                return json.load(f)
        return {}

    def _save_users(self):
        with open(self.USERS_FILE, 'w') as f:
            json.dump(self.users, f)

    def add_coins(self, user_id: str, amount: int):
        if user_id not in self.users:
            self.users[user_id] = {"coins": 0}
        self.users[user_id]["coins"] += amount
        self._save_users()

    def deduct_coins(self, user_id: str, amount: int):
        if user_id in self.users and self.users[user_id]["coins"] >= amount:
            self.users[user_id]["coins"] -= amount
            self._save_users()
            return True
        return False

    def get_coins(self, user_id: str):
        return self.users.get(user_id, {}).get("coins", 0)

    def transfer_coins(self, sender_id: str, receiver_id: str, amount: int):
        if sender_id in self.users and receiver_id in self.users:
            if self.users[sender_id]["coins"] >= amount:
                self.users[sender_id]["coins"] -= amount
                self.users[receiver_id]["coins"] += amount
                self._save_users()
                return True
        return False

class CardChecker:
    """Simulated card validation system"""
    
    @staticmethod
    def luhn_check(card_number: str) -> bool:
        digits = list(map(int, card_number))
        odd_digits = digits[-1::-2]
        even_digits = digits[-2::-2]
        total = sum(odd_digits)
        for d in even_digits:
            total += sum(divmod(2*d, 10))
        return total % 10 == 0

    def check_card(self, card_data: str) -> dict:
        try:
            card_number, month, year, cvv = card_data.split('|')
            if (len(card_number) not in [13, 15, 16] or
                len(cvv) not in [3,4] or
                not (1 <= int(month) <= 12)):
                return {"status": "DECLINED", "code": "02"}
                
            return {
                "status": "APPROVED" if self.luhn_check(card_number) else "DECLINED",
                "code": "00" if self.luhn_check(card_number) else "01"
            }
        except:
            return {"status": "INVALID", "code": "99"}

# ---------------------------
# SECTION 3: TELEGRAM BOT INTEGRATION
# ---------------------------

class TelegramBotHandler:
    def __init__(self, token: str, user_manager: UserManager, card_checker: CardChecker, admin_id: int):
        self.updater = Updater(token, use_context=True)
        self.dispatcher = self.updater.dispatcher
        self.user_manager = user_manager
        self.card_checker = card_checker
        self.admin_id = admin_id
        
        # Add handlers
        self.dispatcher.add_handler(CommandHandler("start", self.start))
        self.dispatcher.add_handler(CommandHandler("help", self.help))
        self.dispatcher.add_handler(CommandHandler("coins", self.check_coins))
        self.dispatcher.add_handler(CommandHandler("add", self.add_coins))
        self.dispatcher.add_handler(CommandHandler("transfer", self.transfer_coins))
        self.dispatcher.add_handler(MessageHandler(Filters.regex(r'^\.chk'), self.check_card))
        
    def start_bot(self):
        print("Telegram bot started!")
        self.updater.start_polling()  # Start polling without idle()

    def start(self, update: Update, context: CallbackContext):
        update.message.reply_text(
            "🤖 *Card System Bot*\n"
            "Available commands:\n"
            "/start - Show this message\n"
            "/coins - Check your balance\n"
            ".chk [CARD] - Check card validity\n"
            "/add [user_id] [coins] - Admin: Add coins to user\n"
            "/transfer [receiver_id] [coins] - Transfer coins\n"
            "/help - Show help",
            parse_mode=ParseMode.MARKDOWN
        )

    def help(self, update: Update, context: CallbackContext):
        update.message.reply_text(
            "🔍 *Help Menu*\n"
            "*/coins* - Check your coin balance\n"
            "*.chk 4264510260199808|11|2027|816* - Validate card\n"
            "*/add [user_id] [coins]* - Admin: Add coins to user\n"
            "*/transfer [receiver_id] [coins]* - Transfer coins to another user",
            parse_mode=ParseMode.MARKDOWN
        )

    def check_coins(self, update: Update, context: CallbackContext):
        user_id = str(update.effective_user.id)
        coins = self.user_manager.get_coins(user_id)
        update.message.reply_text(f"💰 Your coins: {coins}")

    def add_coins(self, update: Update, context: CallbackContext):
        user_id = update.effective_user.id
        if user_id != self.admin_id:
            update.message.reply_text("❌ Admin access required!")
            return

        try:
            target_user_id = context.args[0]
            coins = int(context.args[1])
            self.user_manager.add_coins(target_user_id, coins)
            update.message.reply_text(f"✅ Added {coins} coins to user {target_user_id}!")
        except (IndexError, ValueError):
            update.message.reply_text("Usage: /add [user_id] [coins]")

    def transfer_coins(self, update: Update, context: CallbackContext):
        sender_id = str(update.effective_user.id)
        try:
            receiver_id = context.args[0]
            amount = int(context.args[1])
            if self.user_manager.transfer_coins(sender_id, receiver_id, amount):
                update.message.reply_text(f"✅ Transferred {amount} coins to user {receiver_id}!")
            else:
                update.message.reply_text("❌ Transfer failed. Check user ID or balance.")
        except (IndexError, ValueError):
            update.message.reply_text("Usage: /transfer [receiver_id] [coins]")

    def check_card(self, update: Update, context: CallbackContext):
        user_id = str(update.effective_user.id)
        card_data = update.message.text.replace('.chk ', '').strip()
        result = self.card_checker.check_card(card_data)
        
        # Deduct 1 coin for checking
        if self.user_manager.deduct_coins(user_id, 1):
            response = (
                f"🃏 *Card Check Result*\n"
                f"Status: {result['status']}\n"
                f"Code: {result['code']}\n"
                f"Remaining coins: {self.user_manager.get_coins(user_id)}"
            )
        else:
            response = "❌ Insufficient coins! Ask the admin to add coins."
            
        update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)

# ---------------------------
# SECTION 4: MAIN EXECUTION
# ---------------------------

if __name__ == "__main__":
    # Load Telegram token and admin ID from environment
    TOKEN = os.getenv("TELEGRAM_TOKEN")
    ADMIN_ID = os.getenv("ADMIN_ID")

    # Check if environment variables are set
    if not TOKEN or not ADMIN_ID:
        print("Error: TELEGRAM_TOKEN and ADMIN_ID must be set in the environment.")
        exit(1)

    # Convert ADMIN_ID to integer
    ADMIN_ID = int(ADMIN_ID)

    # Initialize systems
    user_manager = UserManager()
    card_checker = CardChecker()

    # Start Telegram bot in parallel thread
    bot = TelegramBotHandler(TOKEN, user_manager, card_checker, ADMIN_ID)
    bot_thread = threading.Thread(target=bot.start_bot, daemon=True)  # Use daemon thread
    bot_thread.start()

    # Keep the main thread alive
    while True:
        pass