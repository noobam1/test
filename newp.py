import os
import time
import json
from typing import Dict
from faker import Faker
from cryptography.fernet import Fernet
from telegram import Update, ParseMode
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Initialize Faker for generating fake data
fake = Faker()

# Generate a secure encryption key (store this in .env for production)
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", Fernet.generate_key().decode())
cipher_suite = Fernet(ENCRYPTION_KEY.encode())

class CoinManager:
    """Handles user coins and transactions."""
    
    def __init__(self):
        self.users = self._load_users()

    def _load_users(self) -> Dict[str, int]:
        """
        Loads users and their coin balances from a file or initializes an empty dictionary.
        """
        if os.path.exists("users.json"):
            with open("users.json", "r") as f:
                return json.load(f)
        return {}

    def _save_users(self):
        """
        Saves users and their coin balances to a file.
        """
        with open("users.json", "w") as f:
            json.dump(self.users, f)

    def add_coins(self, user_id: str, coins: int):
        """
        Adds coins to a user's balance.
        """
        if user_id not in self.users:
            self.users[user_id] = 0
        self.users[user_id] += coins
        self._save_users()

    def deduct_coins(self, user_id: str, coins: int) -> bool:
        """
        Deducts coins from a user's balance.
        Returns True if successful, False if insufficient coins.
        """
        if user_id in self.users and self.users[user_id] >= coins:
            self.users[user_id] -= coins
            self._save_users()
            return True
        return False

    def get_coins(self, user_id: str) -> int:
        """
        Returns the number of coins a user has.
        """
        return self.users.get(user_id, 0)

class CardManager:
    """Handles secure card data validation and storage."""
    
    @staticmethod
    def luhn_check(card_number: str) -> bool:
        """
        Validates a card number using the Luhn algorithm.
        """
        digits = list(map(int, card_number))
        odd_digits = digits[-1::-2]
        even_digits = digits[-2::-2]
        total = sum(odd_digits)
        for d in even_digits:
            total += sum(divmod(2 * d, 10))
        return total % 10 == 0

    def validate_card(self, card_data: Dict[str, str]) -> Dict[str, str]:
        """
        Validates card data and returns a professional response.
        """
        try:
            card_number = card_data["card_number"]
            expiration_date = card_data["expiration_date"]
            cvv = card_data["cvv"]
            
            # Validate card number using Luhn algorithm
            is_valid = self.luhn_check(card_number)
            
            # Simulate API call for additional card info
            card_info = self._get_card_info(card_number)
            
            return {
                "status": "APPROVED" if is_valid else "DECLINED",
                "code": "00" if is_valid else "01",
                "card_type": card_info["type"],
                "bank": card_info["bank"],
                "country": card_info["country"],
                "response_time": time.time()
            }
        except Exception as e:
            return {
                "status": "INVALID",
                "code": "99",
                "message": f"Error processing card data: {e}"
            }

    def _get_card_info(self, card_number: str) -> Dict[str, str]:
        """
        Simulates a professional API call to fetch card information.
        """
        # Replace this with a real API call in production
        card_types = {
            "4": "VISA",
            "5": "MASTERCARD",
            "3": "AMEX"
        }
        card_type = card_types.get(card_number[0], "UNKNOWN")
        
        # Simulate bank and country lookup
        bank = "UNKNOWN"
        country = "UNKNOWN"
        if card_number.startswith("5"):
            bank = "MASTERCARD BANK"
            country = "Thailand - 🇹🇭 - THB"
        
        return {
            "type": card_type,
            "bank": bank,
            "country": country
        }

class AddressGenerator:
    """Handles address generation for all countries."""
    
    def generate_address(self, country_code: str) -> Dict[str, str]:
        """
        Generates a fake address for the specified country.
        """
        try:
            # Set the locale for the specified country
            fake = Faker(country_code)
            
            # Generate address details
            address = {
                "street": fake.street_address(),
                "city": fake.city(),
                "state": fake.state(),
                "postcode": fake.postcode(),
                "country": fake.current_country()
            }
            return address
        except Exception as e:
            return {
                "error": f"Invalid country code: {country_code}"
            }

class ShopifyChargeManager:
    """Handles Shopify charge validation."""
    
    @staticmethod
    def validate_charge(card_data: Dict[str, str], amount: float) -> Dict[str, str]:
        """
        Simulates Shopify charge validation for a given amount.
        """
        try:
            card_number = card_data["card_number"]
            expiration_date = card_data["expiration_date"]
            cvv = card_data["cvv"]
            
            # Simulate charge validation
            is_valid = CardManager.luhn_check(card_number)
            
            return {
                "status": "APPROVED" if is_valid else "DECLINED",
                "amount": amount,
                "card_type": "MASTERCARD",  # Simulated card type
                "response_time": time.time()
            }
        except Exception as e:
            return {
                "status": "INVALID",
                "message": f"Error processing charge: {e}"
            }

class TelegramBotHandler:
    def __init__(self, token: str, coin_manager: CoinManager, card_manager: CardManager, address_generator: AddressGenerator, shopify_manager: ShopifyChargeManager):
        self.updater = Updater(token, use_context=True)
        self.dispatcher = self.updater.dispatcher
        self.coin_manager = coin_manager
        self.card_manager = card_manager
        self.address_generator = address_generator
        self.shopify_manager = shopify_manager
        
        # Add handlers
        self.dispatcher.add_handler(CommandHandler("start", self.start))
        self.dispatcher.add_handler(CommandHandler("chk", self.check_card))
        self.dispatcher.add_handler(MessageHandler(Filters.regex(r'^\.chk'), self.check_card))
        self.dispatcher.add_handler(CommandHandler("gen", self.generate_address))
        self.dispatcher.add_handler(MessageHandler(Filters.regex(r'^\.gen'), self.generate_address))
        self.dispatcher.add_handler(CommandHandler("sh", self.shopify_charge_10))
        self.dispatcher.add_handler(CommandHandler("msh", self.mass_shopify_charge_10))
        self.dispatcher.add_handler(CommandHandler("so", self.shopify_charge_27_51))
        self.dispatcher.add_handler(CommandHandler("mso", self.mass_shopify_charge_27_51))
        self.dispatcher.add_handler(CommandHandler("sho", self.shopify_charge_20))
        self.dispatcher.add_handler(CommandHandler("msho", self.mass_shopify_charge_20))
        self.dispatcher.add_handler(CommandHandler("sg", self.shopify_charge_20_alt))
        self.dispatcher.add_handler(CommandHandler("msg", self.mass_shopify_charge_20_alt))
        self.dispatcher.add_handler(CommandHandler("add", self.add_coins))
        self.dispatcher.add_handler(CommandHandler("balance", self.check_balance))
        
    def start_bot(self):
        print("Telegram bot started!")
        self.updater.start_polling()

    def start(self, update: Update, context: CallbackContext):
        update.message.reply_text(
            "🤖 *Card Checker, Address Generator & Shopify Charge Bot*\n"
            "Available commands:\n"
            "/start - Show this message\n"
            "/chk or .chk cc|mm|yy|cvv - Check card validity (1 coin per check)\n"
            "/gen or .gen [country_code] - Generate address (e.g., /gen us, /gen uk)\n"
            "/sh cc|mm|yy|cvv - Shopify Charge $10 (Single)\n"
            "/msh cc|mm|yy|cvv - Shopify Charge $10 (Mass)\n"
            "/so cc|mm|yy|cvv - Shopify Charge $27.51 (Single)\n"
            "/mso cc|mm|yy|cvv - Shopify Charge $27.51 (Mass)\n"
            "/sho cc|mm|yy|cvv - Shopify Charge $20 (Single)\n"
            "/msho cc|mm|yy|cvv - Shopify Charge $20 (Mass)\n"
            "/sg cc|mm|yy|cvv - Shopify Charge $20 (Alternative) (Single)\n"
            "/msg cc|mm|yy|cvv - Shopify Charge $20 (Alternative) (Mass)\n"
            "/add user_id coins - Admin: Add coins to a user\n"
            "/balance - Check your coin balance\n",
            parse_mode=ParseMode.MARKDOWN
        )

    def check_card(self, update: Update, context: CallbackContext):
        user_id = str(update.effective_user.id)
        
        # Deduct 1 coin for the check
        if not self.coin_manager.deduct_coins(user_id, 1):
            update.message.reply_text("❌ Insufficient coins! Ask the admin to add coins.")
            return
        
        try:
            card_data = update.message.text.replace('/chk', '').replace('.chk', '').strip()
            card_number, month, year, cvv = card_data.split('|')
            
            # Validate card data
            validation_result = self.card_manager.validate_card({
                "card_number": card_number,
                "expiration_date": f"{month}/{year}",
                "cvv": cvv
            })
            
            response = (
                f"🃏 *Card Data:* `{card_number}|{month}|{year}|{cvv}`\n"
                f"📊 *Status:* {validation_result['status']}\n"
                f"💳 *Card Type:* {validation_result['card_type']}\n"
                f"🏦 *Bank:* {validation_result['bank']}\n"
                f"🌍 *Country:* {validation_result['country']}\n"
                f"⏱ *Response Time:* {validation_result['response_time']:.2f} seconds\n"
                f"💰 *Remaining Coins:* {self.coin_manager.get_coins(user_id)}"
            )
            update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            update.message.reply_text(f"❌ Error processing card data: {e}")

    def generate_address(self, update: Update, context: CallbackContext):
        try:
            # Extract country code from the command
            command = update.message.text.replace('/gen', '').replace('.gen', '').strip()
            country_code = command.split()[0].lower()  # Get the first word as the country code
            
            # Generate address
            address = self.address_generator.generate_address(country_code)
            
            if "error" in address:
                update.message.reply_text(f"❌ {address['error']}")
            else:
                response = (
                    f"🏠 *Address Details:*\n"
                    f"📍 *Street:* {address['street']}\n"
                    f"🏙️ *City:* {address['city']}\n"
                    f"🏛️ *State:* {address['state']}\n"
                    f"📮 *Postcode:* {address['postcode']}\n"
                    f"🌍 *Country:* {address['country']}"
                )
                update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            update.message.reply_text(f"❌ Error generating address: {e}")

    def shopify_charge_10(self, update: Update, context: CallbackContext):
        self._process_shopify_charge(update, context, 10.00)

    def mass_shopify_charge_10(self, update: Update, context: CallbackContext):
        self._process_shopify_charge(update, context, 10.00, mass=True)

    def shopify_charge_27_51(self, update: Update, context: CallbackContext):
        self._process_shopify_charge(update, context, 27.51)

    def mass_shopify_charge_27_51(self, update: Update, context: CallbackContext):
        self._process_shopify_charge(update, context, 27.51, mass=True)

    def shopify_charge_20(self, update: Update, context: CallbackContext):
        self._process_shopify_charge(update, context, 20.00)

    def mass_shopify_charge_20(self, update: Update, context: CallbackContext):
        self._process_shopify_charge(update, context, 20.00, mass=True)

    def shopify_charge_20_alt(self, update: Update, context: CallbackContext):
        self._process_shopify_charge(update, context, 20.00)

    def mass_shopify_charge_20_alt(self, update: Update, context: CallbackContext):
        self._process_shopify_charge(update, context, 20.00, mass=True)

    def _process_shopify_charge(self, update: Update, context: CallbackContext, amount: float, mass: bool = False):
        """
        Processes Shopify charge validation for a given amount.
        """
        user_id = str(update.effective_user.id)
        
        # Deduct 1 coin for the check
        if not self.coin_manager.deduct_coins(user_id, 1):
            update.message.reply_text("❌ Insufficient coins! Ask the admin to add coins.")
            return
        
        try:
            card_data = context.args[0].split('|')
            if len(card_data) != 4:
                update.message.reply_text("❌ Invalid card format. Use: /sh cc|mm|yy|cvv")
                return
            
            card_info = {
                "card_number": card_data[0],
                "expiration_date": f"{card_data[1]}/{card_data[2]}",
                "cvv": card_data[3]
            }
            
            if mass:
                update.message.reply_text(f"🔄 Processing mass Shopify charge of ${amount:.2f}...")
                results = []
                for _ in range(3):  # Simulate mass processing
                    result = self.shopify_manager.validate_charge(card_info, amount)
                    results.append(
                        f"🃏 *Card Data:* `{card_info['card_number']}|{card_info['expiration_date']}|{card_info['cvv']}`\n"
                        f"📊 *Status:* {result['status']}\n"
                        f"💳 *Amount:* ${amount:.2f}\n"
                        f"⏱ *Response Time:* {result['response_time']:.2f} seconds\n"
                        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                    )
                update.message.reply_text(
                    f"📋 *Mass Shopify Charge Results (${amount:.2f}):*\n\n" + "\n\n".join(results),
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                update.message.reply_text(f"🔄 Processing Shopify charge of ${amount:.2f}...")
                result = self.shopify_manager.validate_charge(card_info, amount)
                response = (
                    f"🃏 *Card Data:* `{card_info['card_number']}|{card_info['expiration_date']}|{card_info['cvv']}`\n"
                    f"📊 *Status:* {result['status']}\n"
                    f"💳 *Amount:* ${amount:.2f}\n"
                    f"⏱ *Response Time:* {result['response_time']:.2f} seconds\n"
                    f"💰 *Remaining Coins:* {self.coin_manager.get_coins(user_id)}"
                )
                update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            update.message.reply_text(f"❌ Error processing charge: {e}")

    def add_coins(self, update: Update, context: CallbackContext):
        user_id = str(update.effective_user.id)
        if user_id != os.getenv("ADMIN_ID"):
            update.message.reply_text("❌ Admin access required!")
            return
        
        try:
            target_user_id = context.args[0]
            coins = int(context.args[1])
            self.coin_manager.add_coins(target_user_id, coins)
            update.message.reply_text(f"✅ Added {coins} coins to user {target_user_id}!")
        except (IndexError, ValueError):
            update.message.reply_text("Usage: /add user_id coins")

    def check_balance(self, update: Update, context: CallbackContext):
        user_id = str(update.effective_user.id)
        coins = self.coin_manager.get_coins(user_id)
        update.message.reply_text(f"💰 Your coin balance: {coins}")

# Example Usage
if __name__ == "__main__":
    # Load Telegram token from environment
    TOKEN = os.getenv("TELEGRAM_TOKEN")
    if not TOKEN:
        print("Error: TELEGRAM_TOKEN must be set in the environment.")
        exit(1)

    # Initialize managers
    coin_manager = CoinManager()
    card_manager = CardManager()
    address_generator = AddressGenerator()
    shopify_manager = ShopifyChargeManager()

    # Start the bot
    bot = TelegramBotHandler(TOKEN, coin_manager, card_manager, address_generator, shopify_manager)
    bot.start_bot()