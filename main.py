import os
import time
import asyncio
from flask import Flask
from threading import Thread
from discord import Intents, Client, Message
from playwright.async_api import async_playwright

# === Load Environment Safely ===
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID_RAW = os.getenv("CHANNEL_ID")
COOKIE_S = os.getenv("COOKIE_S")
CF_CLEARANCE = os.getenv("CF_CLEARANCE")
CF_BM = os.getenv("CF_BM")

# Validate env vars
if not DISCORD_TOKEN:
    raise ValueError("DISCORD_TOKEN is not set in environment.")
if not CHANNEL_ID_RAW:
    raise ValueError("CHANNEL_ID is not set in environment.")
CHANNEL_ID = int(CHANNEL_ID_RAW)

# === Flask Keep-Alive ===
app = Flask('')
@app.route('/')
def home():
    return "Bot is running."

def run_flask():
    app.run(host='0.0.0.0', port=8080)

Thread(target=run_flask).start()

# === Discord Bot ===
intents = Intents.default()
intents.message_content = True
client = Client(intents=intents)

async def send_discord_message(text):
    channel = client.get_channel(CHANNEL_ID)
    if channel:
        await channel.send(text)

async def get_time_left():
    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=True)
        context = await browser.new_context()
        await context.add_cookies([
            {"name": "s", "value": COOKIE_S, "domain": ".csgoroll.com", "path": "/"},
            {"name": "cf_clearance", "value": CF_CLEARANCE, "domain": ".csgoroll.com", "path": "/"},
            {"name": "__cf_bm", "value": CF_BM, "domain": ".csgoroll.com", "path": "/"},
        ])
        page = await context.new_page()
        await page.goto("https://www.csgoroll.com/cases/daily-free")
        await page.wait_for_timeout(5000)
        countdown = await page.query_selector("body > cw-root > main > mat-sidenav-container > mat-sidenav-content > div > cw-box-list-wrapper > cw-daily-free-boxes > section > cw-daily-free > article > cw-free-boxes-grid > section > cw-box-grid-item-gaming:nth-child(2) > div > div.d-flex.flex-column.main-content > button > span.mat-button-wrapper > div > cw-countdown")
        if countdown:
            time_left = await countdown.inner_text()
            await browser.close()
            return time_left
        await browser.close()
        return None

# === Automation Function ===
async def check_and_claim_daily():
    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=True)
        context = await browser.new_context()

        await context.add_cookies([
            {"name": "s", "value": COOKIE_S, "domain": ".csgoroll.com", "path": "/"},
            {"name": "cf_clearance", "value": CF_CLEARANCE, "domain": ".csgoroll.com", "path": "/"},
            {"name": "__cf_bm", "value": CF_BM, "domain": ".csgoroll.com", "path": "/"},
        ])

        page = await context.new_page()
        await page.goto("https://www.csgoroll.com/cases/daily-free")
        await page.wait_for_timeout(5000)

        countdown = await page.query_selector("body > cw-root > main > mat-sidenav-container > mat-sidenav-content > div > cw-box-list-wrapper > cw-daily-free-boxes > section > cw-daily-free > article > cw-free-boxes-grid > section > cw-box-grid-item-gaming:nth-child(2) > div > div.d-flex.flex-column.main-content > button > span.mat-button-wrapper > div > cw-countdown")
        if countdown:
            time_left = await countdown.inner_text()
            await send_discord_message(f"⏳ Dailies not ready. Time left: **{time_left}**")
            await browser.close()
            return "not_ready"

        try:
            await page.click("body > cw-root > main > mat-sidenav-container > mat-sidenav-content > div > cw-box-list-wrapper > cw-daily-free-boxes > section > cw-daily-free > article > div > div.flex-grow-0.d-flex.flex-column.flex-sm-row.align-items-sm-center.justify-content-between.gap-05.align-self-md-end.align-self-stretch.ng-star-inserted > button")
            await page.wait_for_timeout(2000)
            await page.click("#mat-option-18")
            await page.wait_for_timeout(1000)
            await page.click("#mat-option-23")
            await page.wait_for_timeout(1000)
            await page.click("body > cw-root > main > mat-sidenav-container > mat-sidenav-content > div > cw-pvp-create-unboxing-duel > cw-pvp-create-unboxing-duel-controls > div.d-flex.flex-column.gap-1.ng-star-inserted > div.d-flex.flex-column.flex-sm-row.align-items-sm-center.justify-content-sm-between.gap-1 > div.d-flex.flex-column.flex-md-row.gap-05.gap-md-1.ng-star-inserted > button")
            await page.wait_for_timeout(8000)

            await page.wait_for_selector("cw-pvp-unboxing-game-result", timeout=60000)
            result = await page.inner_text("cw-pvp-unboxing-game-result")
            value = await page.inner_text(".balance-container.fs-16.fs-lg-32")

            await send_discord_message(f"🎉 **Daily Battle Result**: `{result}`\n💰 Winnings: `{value}`")
            await browser.close()
            return "claimed"
        except Exception as e:
            await send_discord_message(f"⚠️ Error while trying to claim dailies: {e}")
            await browser.close()
            return "error"

# === Loop Task ===
async def loop_task():
    await client.wait_until_ready()
    while not client.is_closed():
        await check_and_claim_daily()
        await asyncio.sleep(180)

@client.event
async def on_ready():
    print(f"Logged in as {client.user}")
    client.loop.create_task(loop_task())

@client.event
async def on_message(message: Message):
    if message.author == client.user:
        return

    content = message.content.lower()

    if content == "!checkdailies":
        await send_discord_message("🔍 Manually checking your dailies now...")
        result = await check_and_claim_daily()
        if result == "claimed":
            await message.channel.send("✅ Daily claimed and battle started!")
        elif result == "not_ready":
            await message.channel.send("⏳ Dailies not ready yet.")
        else:
            await message.channel.send("⚠️ An error occurred while checking dailies.")

    elif content == "!status":
        await message.channel.send("🤖 Bot is running and monitoring CSGORoll dailies!")

    elif content == "!timeleft":
        await message.channel.send("⏳ Fetching time left...")
        try:
            time_left = await get_time_left()
            if time_left:
                await message.channel.send(f"⏱️ Time until next daily: **{time_left}**")
            else:
                await message.channel.send("✅ Dailies appear to be ready now!")
        except Exception as e:
            await message.channel.send(f"⚠️ Could not fetch time left: {e}")

client.run(DISCORD_TOKEN)
