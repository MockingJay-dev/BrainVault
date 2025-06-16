import os
import io
import logging
import re
import datetime
import time
from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    PicklePersistence,
    ContextTypes,
    filters
)

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Configure UTC logging with rotation
logging.Formatter.converter = time.gmtime
formatter = logging.Formatter(
    '%(asctime)s %(levelname)s %(name)s: %(message)s',
    datefmt='%Y-%m-%dT%H:%M:%SZ'
)
file_handler = logging.handlers.RotatingFileHandler(
    'bot.log', maxBytes=5 * 1024 * 1024, backupCount=3
)
file_handler.setFormatter(formatter)
logger = logging.getLogger("brainvault")
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)

ASCII_BANNER = (
    "BRAIN VAULT - THE MOCKINGJAY\n"
    " ██████  ██████   █████  ██ ███    ██ ██    ██  █████  ██    ██ ██      ███████\n"
    " ██   ██ ██   ██ ██   ██ ██ ████   ██ ██    ██ ██   ██ ██    ██ ██         ██\n"
    " ██████  ██████  ███████ ██ ██ ██  ██ ██    ██ ███████ ██    ██ ██         ██\n"
    " ██   ██ ██   ██ ██   ██ ██ ██  ██ ██  ██  ██  ██   ██ ██    ██ ██         ██\n"
    " ██████  ██   ██ ██   ██ ██ ██   ████   ████   ██   ██  ██████  ███████    ██\n"
    "             <(v)>   <( )>     ^ ^\n"
)

def private_chat_only(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        if update.effective_chat.type != 'private':
            return
        return await func(update, context, *args, **kwargs)
    return wrapper

@private_chat_only
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "Welcome to Brain Vault – The Mockingjay!\n"
        "Use /add to create tagged notes, /view to see them, and /download to export.\n"
        "Everything is stored privately per user. No one but you can access it."
    )
    await update.message.reply_text(
        f"<pre>{ASCII_BANNER}</pre>\n{text}",
        parse_mode=ParseMode.HTML
    )
    logger.info(f"User {update.effective_user.id} started bot.")

@private_chat_only
async def add(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text
    tags = re.findall(r"#(\w+)", text)
    if not tags:
        await update.message.reply_text("Usage: /add #tag Your note.")
        return
    entry = text[len("/add "):].strip()
    ts = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    tags_data = context.user_data.setdefault('tags', {})
    for tag in sorted(set(t.lower() for t in tags)):
        tags_data.setdefault(tag, []).append(f"{entry} [{ts}]")
    await update.message.reply_text(f"Added under #{', #'.join(sorted(set(tags)))}.")
    logger.info(f"User {update.effective_user.id} added note.")

@private_chat_only
async def view(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tags_data = context.user_data.get('tags', {})
    if not tags_data:
        await update.message.reply_text("No notes yet.")
        return
    arg = context.args[0].lstrip('#').lower() if context.args else None
    if arg:
        entries = tags_data.get(arg, [])
        msg = f"Entries for #{arg}:\n" + '\n'.join(entries) if entries else f"No entries for #{arg}."
    else:
        lines = []
        for tag, entries in tags_data.items():
            lines.append(f"#{tag}:")
            lines.extend(entries)
        msg = '\n'.join(lines)
    await update.message.reply_text(msg)
    logger.info(f"User {update.effective_user.id} viewed notes.")

@private_chat_only
async def download(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tags_data = context.user_data.get('tags', {})
    if not tags_data:
        await update.message.reply_text("No notes to download.")
        return
    lines = []
    for tag, entries in tags_data.items():
        lines.append(f"[{tag}]")
        lines.extend(entries)
        lines.append("")
    content = '\n'.join(lines).encode('utf-8')
    bio = io.BytesIO(content)
    bio.name = f"notes_{update.effective_user.id}.txt"
    bio.seek(0)
    await update.message.reply_document(document=bio)
    logger.info(f"User {update.effective_user.id} downloaded notes.")

def main():
    persistence = PicklePersistence(filepath="bot_data")
    app = ApplicationBuilder().token(BOT_TOKEN).persistence(persistence).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add))
    app.add_handler(CommandHandler("view", view))
    app.add_handler(CommandHandler("download", download))
    logger.info("Bot starting...")
    app.run_polling()

if __name__ == '__main__':
    main()
