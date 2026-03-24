#!/usr/bin/env python3
"""GEX Discord Listener — saves the latest GEX chart image for each symbol."""

import os
import sys
import json
import asyncio
import aiohttp
import aiofiles
from datetime import datetime, timezone
from pathlib import Path

import discord

BASE_DIR    = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.json"
IMAGE_DIR   = BASE_DIR / "gex_images"
VALID_SYMBOLS = {"SPY", "QQQ", "IWM"}


def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)


def load_config() -> dict:
    env_token   = os.environ.get("DISCORD_TOKEN")
    env_channel = os.environ.get("DISCORD_CHANNEL_ID")
    env_bot     = os.environ.get("TRADYTICS_BOT_ID")
    if env_token and env_channel and env_bot:
        log("[CONFIG] Loaded from environment variables")
        return {"token": env_token, "channel_id": int(env_channel), "tradytics_bot_id": int(env_bot)}

    if CONFIG_PATH.exists():
        with open(CONFIG_PATH) as f:
            cfg = json.load(f)
        if cfg.get("token") and cfg.get("channel_id") and cfg.get("tradytics_bot_id"):
            cfg["channel_id"]       = int(cfg["channel_id"])
            cfg["tradytics_bot_id"] = int(cfg["tradytics_bot_id"])
            return cfg

    print("=== First-Time Setup ===")
    cfg = {
        "token":            input("Discord user token: ").strip(),
        "channel_id":       int(input("Tradytics channel ID: ").strip()),
        "tradytics_bot_id": int(input("Tradytics Bot V2 user ID: ").strip()),
    }
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)
    return cfg


def extract_symbol(title: str) -> str | None:
    t = title.upper()
    for sym in VALID_SYMBOLS:
        if sym in t:
            return sym
    return None


config = load_config()
client = discord.Client()


@client.event
async def on_ready():
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    log(f"Logged in as {client.user}")
    ch = client.get_channel(config["channel_id"])
    if ch:
        log(f"Watching #{ch.name} in {ch.guild.name}")
    log("Waiting for GEX charts...")


@client.event
async def on_message(message: discord.Message):
    if message.channel.id != config["channel_id"]:
        return
    if message.author.id != config["tradytics_bot_id"]:
        return
    if not message.embeds:
        return

    for embed in message.embeds:
        if not embed.title:
            continue
        symbol = extract_symbol(embed.title)
        if not symbol:
            continue

        image_url = None
        if embed.image and embed.image.url:
            image_url = embed.image.url
        elif embed.thumbnail and embed.thumbnail.url:
            image_url = embed.thumbnail.url

        if not image_url:
            continue

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as resp:
                    resp.raise_for_status()
                    data = await resp.read()

            # Save as latest_{SYMBOL}.png (always overwritten = always latest)
            latest_path = IMAGE_DIR / f"latest_{symbol}.png"
            async with aiofiles.open(latest_path, "wb") as f:
                await f.write(data)

            # Also save a timestamped copy for history
            ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            history_path = IMAGE_DIR / f"{ts}_{symbol}.png"
            async with aiofiles.open(history_path, "wb") as f:
                await f.write(data)

            log(f"Saved {symbol} GEX chart -> {latest_path.name}")
        except Exception as e:
            log(f"[ERROR] Failed to save {symbol} image: {e}")


if __name__ == "__main__":
    try:
        client.run(config["token"], log_handler=None)
    except discord.LoginFailure:
        print("
[FATAL] Invalid Discord token.")
        sys.exit(1)
    except KeyboardInterrupt:
        print("
[INFO] Shutting down.")
