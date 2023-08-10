import boto3
from PIL import Image
from moviepy.editor import *
from moviepy.video.io.VideoFileClip import VideoFileClip
import requests
from io import BytesIO
import base64
import tempfile
from telegram import InputFile, Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    Application,
    MessageHandler,
    filters,
    CallbackContext,
)
import asyncio
import numpy as np

# yt
import os
import io
import base64
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# text extractor
import pytesseract

#
import os
from dotenv import load_dotenv


# load env
load_dotenv()
API_SERVICE_NAME = "youtube"
API_VERSION = "v3"
# GUIDE: https://developers.google.com/google-ads/api/docs/first-call/refresh-token
REFRESH_TOKEN = os.getenv("MY_GOOGLE_USER_REFRESH_TOKEN")


# youtube auth
def get_authenticated_service():
    creds = Credentials.from_authorized_user_info(
        {
            "token": "https://accounts.google.com/o/oauth2/token",
            "refresh_token": REFRESH_TOKEN,
            "client_id": os.getenv("GOOGLE_YOUTUBE_CLIENT_ID"),
            "client_secret": os.getenv("GOOGLE_YOUTUBE_CLIENT_SECRET"),
            "scopes": ["https://www.googleapis.com/auth/youtube.upload"],
        }
    )

    if not creds.valid:
        creds.refresh(Request())

    youtube = build(API_SERVICE_NAME, API_VERSION, credentials=creds)
    return youtube


# upload video to youtube
def upload_video(youtube, video_path, title, description, tags):
    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {"title": title, "description": description, "tags": tags},
            "status": {
                "privacyStatus": "public",  # You can change this as needed
            },
        },
        media_body=MediaFileUpload(video_path),
    )

    response = request.execute()
    return response


# telegram

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
BOT_USERNAME = os.getenv("TELEGRAM_BOT_USERNAME")
received_videos = []


# Commands
# /start command
async def start_commmand(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello, let's start creating!")


# /youtube command
async def youtube_commmand(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Upload to youtube - https://studio.youtube.com/channel/UCz2-rM1K7aX0VixklRTHFZA/videos/upload?d=ud"
    )


# /help command
async def help_commmand(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        """• Extract text from image - Send only an image (no caption)
• Convert Text & Image to Video - Send an image and with caption
• Merge Videos - (/clear) then send Videos you want to Merge before using the (/merge) command
• Upload Videos - (/clear) then send Videos you want to Upload before using the (/upload) command
• Clear Videos - Use the (/clear) command to clear the videos queue
"""
    )


# /merge videos command
async def merge_videos(update: Update, context: CallbackContext) -> None:
    if len(received_videos) < 2:
        await update.message.reply_text("Please send at least two videos to merge.")
        return

    chat_id = update.message.chat_id

    video_clips = []
    max_width = 0
    max_height = 0

    for video in received_videos:
        file = await context.bot.get_file(video.file_id)
        file_bytes = await file.download_as_bytearray()
        with tempfile.NamedTemporaryFile(suffix=".mp4") as temp_file:
            temp_file.write(file_bytes)
            temp_file.seek(0)
            video_clip = VideoFileClip(temp_file.name)
            video_clips.append(video_clip)

            # Update maximum width and height
            max_width = max(max_width, video_clip.w)
            max_height = max(max_height, video_clip.h)

    # Create a white background video
    background_clip = VideoClip(
        make_frame=lambda t: 255 * np.ones((max_height, max_width, 3), dtype=np.uint8),
        duration=max([clip.duration for clip in video_clips]),
    )

    # Position and overlay each video on the white background
    positioned_clips = []
    for video_clip in video_clips:
        # Calculate scaling factors to fit video in background without cropping
        x_scale = max_width / video_clip.w
        y_scale = max_height / video_clip.h
        scale_factor = min(x_scale, y_scale)

        # Resize the video clip to fit in the background
        resized_clip = video_clip.resize(scale_factor)

        # Position the resized video on the background
        positioned_clip = CompositeVideoClip(
            [background_clip, resized_clip.set_position("center")]
        )
        positioned_clips.append(positioned_clip)

    # Merge the positioned video clips
    merged_clip = concatenate_videoclips(positioned_clips)

    # Define the output path for the merged video
    output_path = f"{tempfile.gettempdir()}/merged_video.mp4"
    merged_clip.write_videofile(output_path, codec="libx264", audio_codec="aac", fps=24)
    merged_clip.close()

    # Send the merged video as a document back to Telegram
    with open(output_path, "rb") as video_file:
        await context.bot.send_document(chat_id=chat_id, document=video_file)
    received_videos.clear()
    video_clips.clear()
    positioned_clips.clear()


# /clear command
async def clear_commmand(update: Update, context: CallbackContext) -> None:
    received_videos.clear()
    print(f"Videos Cleared ✅... {len(received_videos)} videos left")
    await update.message.reply_text(
        f"Videos Cleared ✅... {len(received_videos)} videos left"
    )


# /upload video command
async def upload_commmand(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(received_videos) > 1:
        await update.message.reply_text(
            "I can only upload 1 video at a time, run /clear command"
        )
        return
    video = await context.bot.get_file(received_videos[0].file_id)
    # Fetch video content using the provided file_path
    response = requests.get(video.file_path)
    response.raise_for_status()
    video_content = response.content
    video_message = update.message.text.replace("/upload", "").strip()

    print(video)
    print(f"video_message: {video_message}")
    title = video_message
    description = "Funny Memes... Enjoy:)"
    tags = ["Meme", "Funny", "Shorts"]

    youtube = get_authenticated_service()
    response = await upload_video(youtube, video_content, title, description, tags)
    if response:
        await update.message.reply_text(
            f"Video uploaded to YouTube! Review and make it public {response}"
        )
    else:
        await update.message.reply_text(f"Error uploading the video-> {response}")
    print("Video uploaded:", response)


# function to upload video to youtube
async def upload_video(youtube, video_content, title, description, tags):
    try:
        # Create a media upload object
        video_stream = io.BytesIO(video_content)
        media = MediaIoBaseUpload(video_stream, mimetype="video/*", resumable=True)

        # Build the request
        request = youtube.videos().insert(
            part="snippet,status",
            body={
                "snippet": {"title": title, "description": description, "tags": tags},
                "status": {
                    "privacyStatus": "private",
                },
            },
            media_body=media,
        )

        # Execute the request
        response = request.execute()
        video_id = response["id"]
        return f"https://studio.youtube.com/video/{video_id}/edit"
    except Exception as e:
        print("Error uploading to YouTube:", e)
        return None


# Create a video by converting text to audio and playing as voice over on image
async def text_to_audio_overlay_on_image(
    update: Update, context: ContextTypes.DEFAULT_TYPE
):
    chat_id = update.message.chat_id
    print(f"chat_id: {chat_id}")
    print(f"update.message.caption: {update.message.caption}")
    print(f"update.message.photo: {update.message.photo}")

    # Get the text message and image URL
    file_id = update.message.photo[-1].file_id
    file = await context.bot.getFile(file_id)

    # Download the file and convert it to Base64
    file_content = await file.download_as_bytearray()
    image_base64 = base64.b64encode(file_content).decode("utf-8")

    # Convert text to audio using Amazon Polly
    text = update.message.caption.replace(BOT_USERNAME, "").strip()

    aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    region_name = "eu-west-2"

    polly_client = boto3.client(
        "polly",
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        region_name=region_name,
    )

    voice_id = "Stephen"
    engine = "neural"
    response = polly_client.synthesize_speech(
        TextType="ssml",
        Text=f"<speak><prosody rate='75%'>{text}</prosody></speak>",
        OutputFormat="mp3",
        VoiceId=voice_id,
        Engine=engine,
    )

    audio_base64 = base64.b64encode(response["AudioStream"].read()).decode()
    print("1_____audio_base64 completed")

    # Create temporary files for audio and image
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as audio_temp_file:
        audio_temp_file.write(base64.b64decode(audio_base64))
        audio_temp_filename = audio_temp_file.name

    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as image_temp_file:
        image_temp_file.write(base64.b64decode(image_base64))
        image_temp_filename = image_temp_file.name
    print("2_____tempfile created")

    # Create a VideoFileClip from the audio and image temporary files
    audio_clip = AudioFileClip(audio_temp_filename)
    video_clip = ImageClip(image_temp_filename).set_duration(audio_clip.duration)

    # Set the audio of the video clip to the audio we generated
    video_clip = video_clip.set_audio(audio_clip)
    print("3_____video and audio clip created")

    # Save the final video to a temporary file
    output_path = f"{tempfile.gettempdir()}/output_video.mp4"
    video_clip.write_videofile(output_path, codec="libx264", audio_codec="aac", fps=24)
    print("4_____final video save to temp")

    # Clean up temporary files
    audio_clip.close()
    video_clip.close()
    print("5_____clean up temp")

    # Send the video as a document back to Telegram
    # await context.bot.send_document(chat_id=chat_id, document=InputFile(output_path))
    await context.bot.send_document(chat_id=chat_id, document=open(output_path, "rb"))

    print("6_____Video sent successfully!")


# Extract text from image
async def extract_text_from_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message

    photo = message.photo[-1]
    file_id = photo.file_id

    # Get the file object from Telegram's API
    file = await context.bot.get_file(file_id)  # Await the coroutine

    # Download the file content using requests
    file_url = file.file_path
    response = requests.get(file_url)
    image_data = BytesIO(response.content)

    # Convert the image to PIL Image
    image = Image.open(image_data)

    # Perform OCR using pytesseract
    text = pytesseract.image_to_string(image)

    # Respond with the extracted text
    if text.strip():
        await message.reply_text(text)
    else:
        await message.reply_text("OPPSSS, I CAN NOT EXTRACT THE TEXT FROM THIS IMAGE")
    print(("Extracted Text:\n" + text))


# video handler
async def video_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    video = update.message.video
    received_videos.append(video)
    print("received_videos::", received_videos)
    print(f"Video {len(received_videos)} received")
    chat_id = update.message.chat_id
    await context.bot.send_message(
        chat_id, text=f"Video {len(received_videos)} received"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text:
        return
    else:
        if update.message.photo:
            if update.message.caption:
                await text_to_audio_overlay_on_image(update, context)
            else:
                await extract_text_from_image(update, context)
        elif update.message.video:
            await video_handler(update, context)
        else:
            return


async def error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"Update ({update}) caused error {context.error}")


if __name__ == "__main__":
    print("Starting bot 🤖...")

    # build app
    app = Application.builder().token(TOKEN).build()

    # commands
    start_handler = CommandHandler("start", start_commmand)
    app.add_handler(start_handler)

    help_handler = CommandHandler("help", help_commmand)
    app.add_handler(help_handler)

    clear_handler = CommandHandler("clear", clear_commmand)
    app.add_handler(clear_handler)

    upload_handler = CommandHandler("upload", upload_commmand)
    app.add_handler(upload_handler)

    youtube_handler = CommandHandler("youtube", youtube_commmand)
    app.add_handler(youtube_handler)

    merge_handler = CommandHandler("merge", merge_videos)
    app.add_handler(merge_handler)

    # messages
    app.add_handler(MessageHandler(filters.ALL, handle_message))

    # errors
    # app.add_handler(error)

    # check for updates
    print("Polling...")
    app.run_polling(poll_interval=3)
