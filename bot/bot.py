"""
GhostBus AI - Telegram Bot Interface

Telegram bot interface for GhostBus AI allowing users to select bus stops,
view live arrivals, and receive notifications about delayed or ghost buses.
"""

import logging
import os
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

# Load environment variables from .env if present
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler for /start command. Welcomes the user and presents main action options.
    """
    user = update.effective_user
    welcome_text = (
        f"🚌 **Welcome to GhostBus AI**, {user.first_name if user else 'commuter'}!\n\n"
        "GhostBus AI monitors public transit schedules, detects 'ghost buses' "
        "(missing or unexpectedly cancelled trips), and predicts real-time arrival times.\n\n"
        "Use the buttons below or commands to get started:\n"
        "• /stop - Select a bus stop\n"
        "• /help - View available commands"
    )

    # Inline keyboard stub for quick navigation
    keyboard = [
        [InlineKeyboardButton("🚏 Select Stop (Stub)", callback_data="select_stop_stub")],
        [InlineKeyboardButton("ℹ️ Help & Info", callback_data="help_stub")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.message:
        await update.message.reply_text(welcome_text, parse_mode="Markdown", reply_markup=reply_markup)


async def stop_selection_stub(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler / Stub for bus stop selection flow.
    """
    # TODO: Connect to FastAPI backend / database to fetch user's nearby or favorite bus stops.
    # TODO: Implement interactive search for bus stops by name, stop ID, or location coordinates.
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text(
            text="🚏 **Bus Stop Selection Stub**\n\n"
                 "[TODO] Real-time stop search and selection logic will be implemented here.",
            parse_mode="Markdown"
        )
    elif update.message:
        await update.message.reply_text(
            "🚏 **Bus Stop Selection Stub**\n\n"
            "[TODO] Send a stop ID or location to select a stop.",
            parse_mode="Markdown"
        )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler for /help command.
    """
    help_text = (
        "🤖 **GhostBus AI Bot Help**\n\n"
        "Available Commands:\n"
        "/start - Start the bot & view main menu\n"
        "/stop - Select or search for a bus stop\n"
        "/help - Display help guidance"
    )
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text(text=help_text, parse_mode="Markdown")
    elif update.message:
        await update.message.reply_text(help_text, parse_mode="Markdown")


def main() -> None:
    """
    Main entry point to start the Telegram bot runner.
    """
    if not TELEGRAM_BOT_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN environment variable is missing! Set TELEGRAM_BOT_TOKEN in .env.")

    # Build Application
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN or "DUMMY_TOKEN").build()

    # Register Command Handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("stop", stop_selection_stub))
    app.add_handler(CommandHandler("help", help_command))

    # Register Callback Query Handlers for inline buttons
    app.add_handler(CallbackQueryHandler(stop_selection_stub, pattern="^select_stop_stub$"))
    app.add_handler(CallbackQueryHandler(help_command, pattern="^help_stub$"))

    # TODO: Add MessageHandler for location sharing or custom text queries
    # TODO: Connect bot handlers with FastAPI backend API endpoints using httpx

    logger.info("GhostBus AI Telegram bot initialized. Starting polling...")
    app.run_polling()


if __name__ == "__main__":
    main()
