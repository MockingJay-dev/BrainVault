<p align="center">
  <img src="https://raw.githubusercontent.com/MockingJay-dev/assets/main/photo_2025-06-16_09-31-00.jpg" alt="Mockingjay Emblem" width="100%"/>
</p>

<h1 align="center">🧠 BrainVault — The Mockingjay</h1>
<p align="center"><i>Effortless note-taking & smart categorization for Telegram.</i></p>

---

## Quick Start

If you just want to use the bot right away, no setup needed—simply start a chat with:  
[@BrainVault_bot](https://t.me/BrainVault_bot)

---

## Self-Hosting & Customization

If you want to run your own copy, make changes, or contribute:

1. Clone this repository and follow the setup instructions below.
2. You are welcome to modify the code to fit your needs.

---

## Features

- **Save notes instantly:** Just send any message to save it.
- **Auto-categorization:** Use `#tags` in your notes to assign categories automatically.
- **Manual categories:** Add notes to categories via an interactive keyboard.
- **View and filter:** List all notes or filter by selected categories.
- **Edit and manage:** Delete notes or categories easily.
- **Export:** Download all your notes as a neatly formatted text file.
- **Timezone-aware:** Notes are timestamped in Adelaide time (customizable).
- **Data persistence:** Notes are safely stored and survive restarts.

---

## Getting Started (Self-Hosting)

### 1. Clone the repository

```bash
git clone https://github.com/MockingJay-dev/BrainVault.git
cd BrainVault
```

### 2. Set up your environment

It's recommended to use a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install requirements

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the root directory:

```env
BOT_TOKEN=your-telegram-bot-token-here
```

### 5. Run the bot

```bash
python main.py
```

---

## Usage

Start the bot:  
Send `/start` to your bot on Telegram to see the welcome guide and available commands.

**Basic commands:**
- `/start` — Show the welcome/help message.
- `/view` — List all your notes.
- `/view #category` — List notes in a specific category.
- `/export` — Export all notes as a text file.
- `/edit` — Manage (delete) notes or categories.

**Quick Tips:**
- Any message you send is saved as a note.
- Add hashtags (e.g., `#work`, `#ideas`) to assign categories.
- Use the interactive keyboard to manually select categories after typing a note.
- All notes are always saved to `#all`.

**Example:**  
`Remember to call Alice #reminders #work`  
This note will be saved under `#all`, `#reminders`, and `#work`.

---

## Production Deployment

To run this bot as a persistent service that starts automatically and survives server reboots, use systemd:

Create a service file (e.g., `/etc/systemd/system/brainvault-bot.service`):

```ini
[Unit]
Description=BrainVault Telegram Bot
After=network.target

[Service]
User=yourusername
WorkingDirectory=/path/to/your/bot/folder
ExecStart=/path/to/your/bot/folder/.venv/bin/python main.py
Restart=always
Environment=BOT_TOKEN=your_actual_bot_token_here

[Install]
WantedBy=multi-user.target
```

Reload systemd and enable the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable brainvault-bot
sudo systemctl start brainvault-bot
```

Check logs and status:

```bash
sudo systemctl status brainvault-bot
journalctl -u brainvault-bot -f
```

---

## Contributing

PRs and suggestions are welcome! Please open an issue or submit a pull request.

---

## License

MIT License

---

## Author

MockingJay-dev
