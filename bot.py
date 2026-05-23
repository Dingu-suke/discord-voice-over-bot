import asyncio
import io
import logging
import os
import re

import aiohttp
import discord
from discord.ext import commands

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("yomiage")

DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]
VOICEVOX_URL = os.environ.get("VOICEVOX_URL", "http://voicevox:50021")
SPEAKER_ID = int(os.environ.get("SPEAKER_ID", "3"))
MAX_TEXT_LEN = 100

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

read_channel: dict[int, int] = {}
queues: dict[int, asyncio.Queue] = {}
players: dict[int, asyncio.Task] = {}

URL_RE = re.compile(r"https?://\S+")
CUSTOM_EMOJI_RE = re.compile(r"<a?:\w+:\d+>")
MENTION_RE = re.compile(r"<@!?\d+>|<#\d+>|<@&\d+>")


def sanitize(text: str) -> str:
    text = URL_RE.sub("URL", text)
    text = CUSTOM_EMOJI_RE.sub("", text)
    text = MENTION_RE.sub("", text)
    text = text.strip()
    if len(text) > MAX_TEXT_LEN:
        text = text[:MAX_TEXT_LEN] + " 以下略"
    return text


async def synthesize(session: aiohttp.ClientSession, text: str) -> bytes:
    async with session.post(
        f"{VOICEVOX_URL}/audio_query",
        params={"text": text, "speaker": SPEAKER_ID},
    ) as r:
        r.raise_for_status()
        query = await r.json()
    async with session.post(
        f"{VOICEVOX_URL}/synthesis",
        params={"speaker": SPEAKER_ID},
        json=query,
    ) as r:
        r.raise_for_status()
        return await r.read()


async def player_loop(guild_id: int):
    queue = queues[guild_id]
    async with aiohttp.ClientSession() as session:
        while True:
            text, vc = await queue.get()
            if not vc.is_connected():
                continue
            try:
                wav = await synthesize(session, text)
            except Exception:
                log.exception("synthesize failed")
                continue

            done = asyncio.Event()
            loop = asyncio.get_running_loop()
            source = discord.FFmpegPCMAudio(io.BytesIO(wav), pipe=True)
            vc.play(source, after=lambda e: loop.call_soon_threadsafe(done.set))
            await done.wait()


@bot.event
async def on_ready():
    await bot.tree.sync()
    log.info("Logged in as %s", bot.user)


@bot.tree.command(name="join", description="あなたが居るボイスチャンネルに参加します")
async def join(interaction: discord.Interaction):
    if not interaction.user.voice or not interaction.user.voice.channel:
        await interaction.response.send_message("先にVCに参加してください", ephemeral=True)
        return
    channel = interaction.user.voice.channel
    guild_id = interaction.guild.id

    if interaction.guild.voice_client:
        await interaction.guild.voice_client.move_to(channel)
    else:
        await channel.connect()

    read_channel[guild_id] = channel.id
    queues.setdefault(guild_id, asyncio.Queue())
    if guild_id not in players or players[guild_id].done():
        players[guild_id] = asyncio.create_task(player_loop(guild_id))

    await interaction.response.send_message(
        f"{channel.name} に参加しました。VC内のチャットを読み上げます"
    )


@bot.tree.command(name="leave", description="ボイスチャンネルから退出します")
async def leave(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if not vc:
        await interaction.response.send_message("VCに参加していません", ephemeral=True)
        return
    await vc.disconnect()
    read_channel.pop(interaction.guild.id, None)
    await interaction.response.send_message("退出しました")


@bot.event
async def on_message(message: discord.Message):
    if message.author.bot or message.guild is None:
        return
    guild_id = message.guild.id
    if read_channel.get(guild_id) != message.channel.id:
        return
    vc = message.guild.voice_client
    if not vc or not vc.is_connected():
        return
    text = sanitize(message.content)
    if not text:
        return
    await queues[guild_id].put((text, vc))


bot.run(DISCORD_TOKEN)
