import os
import io
import logging
import datetime
import re
import textwrap
from dotenv import load_dotenv
import pytz
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
    PicklePersistence,
)

# --- Environment and Configuration ---
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("❌ BOT_TOKEN not set in environment")

# Logging configuration
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Constants ---
VERSION = "2.4"
PERSISTENCE_FILE = "brain_vault_persistence.pkl"
ADELAIDE_TZ = pytz.timezone("Australia/Adelaide")

# --- Helper Functions ---

def get_current_timestamp() -> str:
    """Returns the current timestamp formatted for Adelaide time."""
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    adl_time = now_utc.astimezone(ADELAIDE_TZ)
    return adl_time.strftime("%Y-%m-%d %I:%M:%S %p")

def get_notes(context: ContextTypes.DEFAULT_TYPE) -> dict:
    """Safely retrieves the notes dictionary from user_data, initializing if needed."""
    notes = context.user_data.setdefault('notes', {})
    notes.setdefault('all', [])
    return notes

def extract_hashtags(text: str) -> list[str]:
    """Extracts unique, lowercase hashtags from a string."""
    return sorted(list(set(tag.lstrip('#').lower() for tag in re.findall(r'#[\w-]+', text))))

def get_category_keyboard(notes: dict, selected_cats: set) -> InlineKeyboardMarkup | None:
    """Generates the category selection keyboard."""
    buttons = []
    all_categories = sorted([cat for cat in notes if cat != 'all'])

    if not all_categories:
        return None

    row = []
    for cat in all_categories:
        prefix = "✅ " if cat in selected_cats else ""
        count = len(notes.get(cat, []))
        button = InlineKeyboardButton(f"{prefix}#{cat} ({count})", callback_data=f"cat_{cat}")
        row.append(button)
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    buttons.append([InlineKeyboardButton("Done ✅", callback_data="cat_done")])
    return InlineKeyboardMarkup(buttons)

async def save_note(context: ContextTypes.DEFAULT_TYPE, note_text: str, categories: set) -> str:
    """Saves a note to the specified categories and returns a confirmation message."""
    notes = get_notes(context)
    timestamp = context.user_data.pop('pending_note_ts', get_current_timestamp())
    entry = f"{note_text} @ {timestamp}"

    notes['all'].append(entry)
    saved_to = {'#all'}

    for cat in categories:
        if cat != 'all':
            notes.setdefault(cat, []).append(entry)
            saved_to.add(f'#{cat}')

    return f"✅ Note saved to: {', '.join(sorted(list(saved_to)))}\n📝 {entry}"


# --- Command Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Print the banner and send a welcome message to the user."""
    banner = textwrap.dedent(r"""
    🧠━━━━━━━━━━━━━━━━━━━━━━━━━━━━━🧠
      ___               _
     | . >  _ _   ___  <_> ._ _
     | . \\ | '_> <_> | | | | ' |
     |___/ |_|   <___| |_| |_|_|
     _ _               _     _
     | | |  ___   _ _  | |  _| |_
     | ' | <_> | | | | | |   | |
     |__/  <___| `___| |_|   |_|

     BRAIN VAULT - THE MOCKINGJAY
    🧠━━━━━━━━━━━━━━━━━━━━━━━━━━━━━🧠
    """).strip("\n")
    print(banner)

    welcome_text = (
        "Welcome to Brain Vault - The Mockingjay!\n\n"
        "📋 Quick Guide:\n"
        "• Type anything to save a note.\n"
        "• Use #tags in your note to auto-categorize.\n"
        "• Or, select categories from the menu after typing.\n"
        "• All notes are saved to #all by default.\n\n"
        "⚡️ Commands:\n"
        "• /view - Browse all your notes.\n"
        "• /view #category - Filter notes by category.\n"
        "• /export - Download a backup file.\n"
        "• /edit - Manage your notes and categories.\n\n"
        "Notes are stored with Adelaide timestamps."
    )

    await update.message.reply_text(
        welcome_text,
        parse_mode=None,
        disable_web_page_preview=True
    )

async def view(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays notes, either all or from a specific category."""
    notes = get_notes(context)
    args = context.args

    if args:
        cat_name = args[0].lstrip('#').lower()
        entries = notes.get(cat_name)
        if not entries:
            await update.message.reply_text(f"⚠️ No entries found for <code>#{cat_name}</code>.", parse_mode=ParseMode.HTML)
            return

        header = f"<b>📝 Notes in #{cat_name} ({len(entries)})</b>"
        note_lines = [f"<code>{idx}.</code> {entry}" for idx, entry in enumerate(entries, 1)]
        message_lines = [header, ""] + note_lines
    else:
        total_unique_notes = len(notes.get('all', []))
        if total_unique_notes == 0:
            await update.message.reply_text("📭 Your brain vault is empty. Start by typing a note!")
            return

        header = f"📚 <b>All Notes ({total_unique_notes} total)</b>"
        message_lines = [header, ""]

        sorted_cats = sorted([cat for cat in notes if notes[cat]])
        if 'all' in sorted_cats:
            sorted_cats.insert(0, sorted_cats.pop(sorted_cats.index('all')))

        for cat_name in sorted_cats:
            entries = notes[cat_name]
            message_lines.append(f"\n<b>📑 #{cat_name} ({len(entries)})</b>")
            message_lines.extend([f"<code>{idx}.</code> {entry}" for idx, entry in enumerate(entries, 1)])
            message_lines.append("")

    message = "\n".join(message_lines)

    if len(message) > 4000:
        for i in range(0, len(message), 4000):
            await update.message.reply_text(message[i:i + 4000], parse_mode=ParseMode.HTML)
    else:
        await update.message.reply_text(message, parse_mode=ParseMode.HTML)

async def export(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Exports all notes to a text file."""
    notes = get_notes(context)
    if not notes.get('all'):
        await update.message.reply_text("📭 Nothing to export. Your vault is empty.")
        return

    timestamp_str = get_current_timestamp().replace(" ", "_").replace(":", "-")
    filename = f"brain_vault_notes_{timestamp_str}.txt"
    lines = [
        "🧠━━━━━━━━━━━━━━━━━━━━━━━━━━━━━🧠",
        "   BRAIN VAULT - THE MOCKINGJAY",
        "🧠━━━━━━━━━━━━━━━━━━━━━━━━━━━━━🧠",
        f"Generated: {get_current_timestamp()}",
        ""
    ]

    sorted_cats = sorted([cat for cat in notes if notes[cat]])
    if 'all' in sorted_cats:
        sorted_cats.insert(0, sorted_cats.pop(sorted_cats.index('all')))

    for cat in sorted_cats:
        lines.append(f"\n# {cat}")
        lines.extend(notes[cat])
        lines.append("")

    file_content = "\n".join(lines).encode('utf-8')
    bio = io.BytesIO(file_content)
    bio.name = filename
    bio.seek(0)

    await update.message.reply_document(
        document=bio,
        filename=filename,
        caption="📦 Here are your exported notes!"
    )

async def edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Shows the editing options keyboard."""
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🗑️ Delete Category", callback_data="edit_delcat")],
        [InlineKeyboardButton("✂️ Delete Note", callback_data="edit_delnote")]
    ])
    await update.message.reply_text("🔧 Choose what to edit:", reply_markup=keyboard)


# --- Message and Callback Handlers ---

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles incoming text messages for saving notes or edit actions."""
    text = update.message.text.strip()
    notes = get_notes(context)

    awaiting_action = context.user_data.get('awaiting_action')
    if awaiting_action:
        await handle_edit_input(update, context, awaiting_action, text)
        return

    hashtags = extract_hashtags(text)
    if text.replace(" ", "") == "".join(f"#{tag}" for tag in hashtags):
        new_cats = []
        for tag in hashtags:
            if tag not in notes:
                notes.setdefault(tag, [])
                new_cats.append(f"#{tag}")
        if new_cats:
            await update.message.reply_text(f"✨ Created new categories: {', '.join(new_cats)}")
        else:
            await update.message.reply_text("✅ Those categories already exist.")
        return

    context.user_data['pending_note'] = text
    context.user_data['pending_note_ts'] = get_current_timestamp()
    context.user_data['selected_categories'] = set(hashtags)

    keyboard = get_category_keyboard(notes, set(hashtags))
    if keyboard:
        msg = "Select additional categories for your note:"
        if hashtags:
            msg += f"\n(Auto-selected from text: {', '.join(f'#{t}' for t in hashtags)})"
        await update.message.reply_text(msg, reply_markup=keyboard)
    else:
        confirmation_message = await save_note(context, text, set(hashtags))
        await update.message.reply_text(confirmation_message)
        context.user_data.pop('pending_note', None)
        context.user_data.pop('selected_categories', None)

async def category_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles button presses from the category selection keyboard."""
    query = update.callback_query
    await query.answer()

    data = query.data
    notes = get_notes(context)
    selected_cats = context.user_data.setdefault('selected_categories', set())

    if data == 'cat_done':
        note_text = context.user_data.pop('pending_note', None)
        if not note_text:
            await query.edit_message_text("❌ Error: No pending note found. Please try again.")
            return

        confirmation_message = await save_note(context, note_text, selected_cats)
        await query.edit_message_text(confirmation_message)
        context.user_data.pop('selected_categories', None)
    else:
        cat_name = data.removeprefix('cat_')
        if cat_name in selected_cats:
            selected_cats.remove(cat_name)
        else:
            selected_cats.add(cat_name)

        keyboard = get_category_keyboard(notes, selected_cats)
        await query.edit_message_reply_markup(reply_markup=keyboard)

async def edit_option_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the initial choice from the /edit command."""
    query = update.callback_query
    await query.answer()

    action = query.data
    context.user_data['awaiting_action'] = action

    if action == 'edit_delcat':
        prompt = "Type the category to delete (e.g., <code>#work</code>). This will delete the category but not the notes within it."
    elif action == 'edit_delnote':
        prompt = "Type the category and note number to delete (e.g., <code>#work 2</code>)."
    else:
        prompt = "Unknown action."

    await query.edit_message_text(prompt, parse_mode=ParseMode.HTML)

async def handle_edit_input(update: Update, context: ContextTypes.DEFAULT_TYPE, action: str, text: str):
    """Processes the text input after an edit option was chosen."""
    context.user_data.pop('awaiting_action')
    notes = get_notes(context)

    if action == 'edit_delcat':
        cat_to_delete = text.lstrip('#').lower()
        if cat_to_delete == 'all':
            await update.message.reply_text("⚠️ The <code>#all</code> category cannot be deleted.", parse_mode=ParseMode.HTML)
        elif cat_to_delete in notes:
            del notes[cat_to_delete]
            await update.message.reply_text(f"✅ Category <code>#{cat_to_delete}</code> has been deleted.", parse_mode=ParseMode.HTML)
        else:
            await update.message.reply_text(f"❌ Category <code>#{cat_to_delete}</code> not found.", parse_mode=ParseMode.HTML)

    elif action == 'edit_delnote':
        match = re.match(r'#([\w-]+)\s+(\d+)', text.strip())
        if not match:
            await update.message.reply_text("⚠️ Invalid format. Please use: <code>#category number</code> (e.g., #work 2).", parse_mode=ParseMode.HTML)
            return

        cat_name, note_num_str = match.groups()
        cat_name = cat_name.lower()
        note_idx = int(note_num_str) - 1

        if cat_name not in notes or not (0 <= note_idx < len(notes[cat_name])):
            await update.message.reply_text(f"❌ Note <code>#{cat_name} {note_num_str}</code> not found.", parse_mode=ParseMode.HTML)
            return

        deleted_note_entry = notes[cat_name].pop(note_idx)
        if deleted_note_entry in notes.get('all', []):
            notes['all'].remove(deleted_note_entry)

        await update.message.reply_text(f"✅ Deleted note from <code>#{cat_name}</code>:\n<s>{deleted_note_entry}</s>", parse_mode=ParseMode.HTML)


# --- Main Application Setup ---

def main() -> None:
    """Starts the bot."""
    persistence = PicklePersistence(filepath=PERSISTENCE_FILE)
    app = ApplicationBuilder().token(TOKEN).persistence(persistence).build()

    # Add handlers
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('view', view))
    app.add_handler(CommandHandler('export', export))
    app.add_handler(CommandHandler('edit', edit))

    app.add_handler(CallbackQueryHandler(category_callback, pattern='^cat_'))
    app.add_handler(CallbackQueryHandler(edit_option_callback, pattern='^edit_'))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    logger.info(f"🚀 Brain Vault Bot v{VERSION} starting...")
    app.run_polling()


if __name__ == '__main__':
    main()
