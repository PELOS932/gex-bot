#!/usr/bin/env python3
"""GEX Discord Listener — saves GEX chart images + scrapes history on startup."""

import os
import sys
import asyncio
import aiohttp
import aiofiles
from datetime import datetime, timezone, timedelta
from pathlib import Path

import discord

BASE_DIR = Path(__file__).resolve().parent
IMAGE_DIR = BASE_DIR / "gex_images"
VALID_SYMBOLS = {"SPY", "QQQ", "IWM"}

TOKEN = os.environ.get("DISCORD_TOKEN", "")
CHANNEL_ID = int(os.environ.get("DISCORD_CHANNEL_ID", "0"))
BOT_ID = int(os.environ.get("TRADYTICS_BOT_ID", "0"))


def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)


def extract_symbol(title):
    if not title:
        return None
    t = title.upper()
    for sym in VALID_SYMBOLS:
        if sym in t:
            return sym
    return None


def get_image_url(embed):
    if embed.image and embed.image.url:
        return embed.image.url
    if embed.thumbnail and embed.thumbnail.url:
        return embed.thumbnail.url
    return None


async def save_image(url, symbol, timestamp):
    """Download and save a GEX chart image."""
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    ts_str = timestamp.strftime("%Y-%m-%d_%H-%M-%S")

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                log(f"[WARN] HTTP {resp.status} downloading {symbol}")
                return False
            data = await resp.read()

    # Save timestamped copy (for history/calendar)
    history_path = IMAGE_DIR / f"{ts_str}_{symbol}.png"
    if not history_path.exists():
        async with aiofiles.open(history_path, "wb") as f:
            await f.write(data)

    # Save/overwrite latest copy
    latest_path = IMAGE_DIR / f"latest_{symbol}.png"
    async with aiofiles.open(latest_path, "wb") as f:
        await f.write(data)

    return True


client = discord.Client()


@client.event
async def on_ready():
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    log(f"Logged in as {client.user} (ID: {client.user.id})")

    # Fetch channel
    try:
        channel = await client.fetch_channel(CHANNEL_ID)
        log(f"Watching #{channel.name} in {channel.guild.name}")
    except Exception as e:
        log(f"[ERROR] Cannot access channel {CHANNEL_ID}: {e}")
        log("Bot will still listen for new messages...")
        return

    # Scrape history (last 30 days)
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    log(f"Scraping GEX history since {cutoff.strftime('%Y-%m-%d')}...")

    count = 0
    saved = 0
    try:
        async for message in channel.history(limit=None, after=cutoff, oldest_first=True):
            count += 1
            if count % 200 == 0:
                log(f"  Scanned {count} messages, saved {saved} GEX charts...")

            if message.author.id != BOT_ID:
                continue
            if not message.embeds:
                continue

            for embed in message.embeds:
                symbol = extract_symbol(embed.title)
                if not symbol:
                    continue
                image_url = get_image_url(embed)
                if not image_url:
                    continue

                try:
                    was_saved = await save_image(image_url, symbol, message.created_at)
                    if was_saved:
                        saved += 1
                except Exception as e:
                    log(f"[WARN] Failed to save historical {symbol}: {e}")

    except Exception as e:
        log(f"[ERROR] History scrape failed: {e}")

    log(f"History scrape done: scanned {count} messages, saved {saved} GEX charts")
    log("Now watching for new GEX charts...")


@client.event
async def on_message(message):
    if message.channel.id != CHANNEL_ID:
        return
    if message.author.id != BOT_ID:
        return
    if not message.embeds:
        return

    for embed in message.embeds:
        symbol = extract_symbol(embed.title)
        if not symbol:
            continue
        image_url = get_image_url(embed)
        if not image_url:
            continue

        try:
            await save_image(image_url, symbol, message.created_at)
            log(f"NEW: Saved {symbol} GEX chart")
        except Exception as e:
            log(f"[ERROR] Failed to save {symbol}: {e}")


if __name__ == "__main__":
    if not TOKEN or not CHANNEL_ID or not BOT_ID:
        print("[FATAL] Set env vars: DISCORD_TOKEN, DISCORD_CHANNEL_ID, TRADYTICS_BOT_ID")
        sys.exit(1)
    try:
        client.run(TOKEN, log_handler=None)
    except discord.LoginFailure:
        print("[FATAL] Invalid Discord token.")
        sys.exit(1)
