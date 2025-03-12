"""
ULTIMATE PYTHON SYSTEM: Users, Coins, Admin Broadcasts, Card Checking, and Telegram Bot
"""

# --------------------------
# SECTION 1: IMPORTS & SETUP
# --------------------------
from dotenv import load_dotenv
   load_dotenv()  # Load environment variables from .env file
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

# ---------------------------
# SECTION 2: CORE SYSTEMS
# ---------------------------

class UserManager:
    """Handles user accounts, coins, and authentication"""
    
    USERS_FILE = "users.json"
    ADMIN_PASSWORD = "admin123"  # Change in production
    
    def __init__(self):
        self.current_user = None
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

    def register(self):
        username = input("Enter username: ").lower()
        if username in self.users:
            print("Username exists!")
            return False

        password = getpass("Enter password: ")
        is_admin = getpass("Admin password (leave empty if not admin): ") == self.ADMIN_PASSWORD
        
        self.users[username] = {
            'password': password,  # In real apps, use hashing!
            'coins': 100 if not is_admin else 1000,
            'is_admin': is_admin,
            'cards_checked': 0
        }
        self._save_users()
        print("Registration successful!")
        return True

    def login(self):
        username = input("Username: ").lower()
        password = getpass("Password: ")
        
        user = self.users.get(username)
        if user and user['password'] == password:
            self.current_user = username
            self._show_broadcasts()
            print(f"Welcome {username}! Coins: {user['coins']}")
            return True
        print("Invalid credentials!")
        return False

    def _show_broadcasts(self):
        if self.broadcasts:
            print("\n--- NEW BROADCASTS ---")
            for msg in self.broadcasts:
                print(f"* {msg}")

    def add_coins(self, amount: int):
        if self.current_user:
            self.users[self.current_user]['coins'] += amount
            self._save_users()

    def transfer_coins(self, receiver: str, amount: int):
        if self.current_user and self.users.get(receiver):
            if self.users[self.current_user]['coins'] >= amount:
                self.users[self.current_user]['coins'] -= amount
                self.users[receiver]['coins'] += amount
                self._save_users()
                print("Transfer successful!")
            else:
                print("Insufficient coins!")
        else:
            print("Invalid transfer!")

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
        self.dispatcher.add_handler(CommandHandler("broadcast", self.broadcast))
        self.dispatcher.add_handler(MessageHandler(Filters.regex(r'^\.chk'), self.check_card))
        
    def start_bot(self):
        print("Telegram bot started!")
        self.updater.start_polling()
        self.updater.idle()

    def start(self, update: Update, context: CallbackContext):
        update.message.reply_text(
            "🤖 *Card System Bot*\n"
            "Available commands:\n"
            "/start - Show this message\n"
            "/coins - Check your balance\n"
            ".chk [CARD] - Check card validity\n"
            "/broadcast [msg] - Admin broadcast\n"
            "/help - Show help",
            parse_mode=ParseMode.MARKDOWN
        )

    def help(self, update: Update, context: CallbackContext):
        update.message.reply_text(
            "🔍 *Help Menu*\n"
            "*/coins* - Check your coin balance\n"
            "*.chk 4264510260199808|11|2027|816* - Validate card\n"
            "*/broadcast [msg]* - Admin broadcast (admins only)",
            parse_mode=ParseMode.MARKDOWN
        )

    def check_coins(self, update: Update, context: CallbackContext):
        user_id = update.effective_user.id
        if str(user_id) in self.user_manager.users:
            coins = self.user_manager.users[str(user_id)]['coins']
            update.message.reply_text(f"💰 Your coins: {coins}")
        else:
            update.message.reply_text("❌ Please register first in the console system!")

    def check_card(self, update: Update, context: CallbackContext):
        user_id = str(update.effective_user.id)
        if user_id not in self.user_manager.users:
            update.message.reply_text("❌ Register in console first!")
            return

        card_data = update.message.text.replace('.chk ', '').strip()
        result = self.card_checker.check_card(card_data)
        
        # Deduct coins for checking
        if self.user_manager.users[user_id]['coins'] >= 5:
            self.user_manager.users[user_id]['coins'] -= 5
            response = (
                f"🃏 *Card Check Result*\n"
                f"Status: {result['status']}\n"
                f"Code: {result['code']}\n"
                f"Remaining coins: {self.user_manager.users[user_id]['coins']}"
            )
        else:
            response = "❌ Insufficient coins! Earn more through activities."
            
        update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)

    def broadcast(self, update: Update, context: CallbackContext):
        user_id = update.effective_user.id
        if user_id != self.admin_id:
            update.message.reply_text("❌ Admin access required!")
            return

        message = ' '.join(context.args)
        if not message:
            update.message.reply_text("Usage: /broadcast [message]")
            return

        self.user_manager.broadcasts.append(message)
        update.message.reply_text("✅ Broadcast sent to all users!")

# ---------------------------
# SECTION 4: MAIN EXECUTION
# ---------------------------

if __name__ == "__main__":
    # Load Telegram token and admin ID from environment
    TOKEN = os.getenv("TELEGRAM_TOKEN")
    ADMIN_ID = int(os.getenv("ADMIN_ID"))  # Your Telegram user ID

    # Initialize systems
    user_manager = UserManager()
    card_checker = CardChecker()

    # Start Telegram bot in parallel thread
    if TOKEN and ADMIN_ID:
        bot = TelegramBotHandler(TOKEN, user_manager, card_checker, ADMIN_ID)
        bot_thread = threading.Thread(target=bot.start_bot)
        bot_thread.start()

    # Start console interface
    menu = EnhancedMenu(user_manager, card_checker)
    menu.main_menu()
