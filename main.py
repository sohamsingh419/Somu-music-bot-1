import os
from pyrogram import Client, filters
from pyrogram.types import Message
from pytgcalls import PyTgCalls
from pytgcalls.types import Update
from pytgcalls.types.input_stream import InputStream, AudioPiped
from pytgcalls.types.input_stream.quality import HighQualityAudio

import yt_dlp
import asyncio

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
SESSION_STRING = os.getenv("SESSION_STRING")

app = Client(name="somu_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, session_string=SESSION_STRING)
pytgcalls = PyTgCalls(app)

queue = {}

def yt_download(url):
    ydl_opts = {
        'format': 'bestaudio',
        'outtmpl': 'downloads/%(title)s.%(ext)s',
        'quiet': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return ydl.prepare_filename(info)

@app.on_message(filters.command("start"))
async def start(_, message: Message):
    await message.reply_text("Somu Music Bot is alive! Use /play <song name or link>")

@app.on_message(filters.command("play") & filters.group)
async def play(_, message: Message):
    if len(message.command) < 2:
        return await message.reply_text("Please provide a song name or YouTube link.")
    query = " ".join(message.command[1:])
    msg = await message.reply_text("Downloading...")
    audio_file = yt_download(query)
    chat_id = message.chat.id
    if chat_id not in queue:
        queue[chat_id] = []
    queue[chat_id].append(audio_file)
    if len(queue[chat_id]) == 1:
        await pytgcalls.join_group_call(
            chat_id,
            InputStream(
                AudioPiped(audio_file, HighQualityAudio())
            )
        )
        await msg.edit("Playing now!")
    else:
        await msg.edit("Added to queue.")

@app.on_message(filters.command("skip") & filters.group)
async def skip(_, message: Message):
    chat_id = message.chat.id
    if chat_id in queue and len(queue[chat_id]) > 1:
        queue[chat_id].pop(0)
        await pytgcalls.change_stream(
            chat_id,
            InputStream(AudioPiped(queue[chat_id][0], HighQualityAudio()))
        )
        await message.reply_text("Skipped to next track.")
    else:
        await pytgcalls.leave_group_call(chat_id)
        queue.pop(chat_id, None)
        await message.reply_text("No more songs in queue, left VC.")

@app.on_message(filters.command("stop") & filters.group)
async def stop(_, message: Message):
    chat_id = message.chat.id
    await pytgcalls.leave_group_call(chat_id)
    queue.pop(chat_id, None)
    await message.reply_text("Stopped playback and left VC.")

@pytgcalls.on_stream_end()
async def stream_end_handler(_, update: Update):
    chat_id = update.chat_id
    if chat_id in queue and len(queue[chat_id]) > 1:
        queue[chat_id].pop(0)
        await pytgcalls.change_stream(
            chat_id,
            InputStream(AudioPiped(queue[chat_id][0], HighQualityAudio()))
        )
    else:
        await pytgcalls.leave_group_call(chat_id)
        queue.pop(chat_id, None)

app.start()
pytgcalls.start()
print("Somu Music Bot is running...")
app.idle()