# lil memer bot - [@lil_memer](https://www.youtube.com/@lil_memer)

Python Telegram bot for automating my Meme YouTube channel @lil_memer. Directly from Telegram, I can easily make videos (text + image), add voiceovers, combine clips, and upload everything to YouTube

## Features (/help)

- Extract text from image - Send only an image (no caption)
- Convert Text & Image to Video - Send an image and with caption
- Merge Videos - (/clear) then send Videos you want to Merge before using the (/merge) command
- Upload Videos - (/clear) then send Videos you want to Upload before using the (/upload) command
- Clear Videos - Use the (/clear) command to clear the videos queue

## Command List

- /start - Starts the bot
- /help - Provides help
- /merge - Merge videos together
- /clear - Clear the videos queue
- /upload - Upload Videos to Youtube Channel
- /youtube - Provides direct link to youtube studio video upload

## Run Locally

Clone the project

```bash
git clone https://github.com/calebareeveso/lil_memer_bot.git
```

Go to the project directory

```bash
cd lil_memer
```

Install dependencies

```bash
pip install boto3 Pillow moviepy python-telegram-bot google-api-python-client google-auth pytesseract

```

Run bot 🤖

## Environment Variables

To run this project, you will need to add the following environment variables to your .env file. Check .env.example

`AWS_ACCESS_KEY_ID`

`AWS_SECRET_ACCESS_KEY`

`TELEGRAM_BOT_TOKEN`

`TELEGRAM_BOT_USERNAME`

`MY_GOOGLE_USER_REFRESH_TOKEN`

`GOOGLE_YOUTUBE_CLIENT_ID`

`GOOGLE_YOUTUBE_CLIENT_SECRET`

## License

[MIT](https://choosealicense.com/licenses/mit/)

## Authors

- [@calebareeveso](https://www.github.com/calebareeveso) - [calebareeveso.com](https://www.calebareeveso.com)
