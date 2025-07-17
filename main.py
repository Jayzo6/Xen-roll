import os
import time
import asyncio
from flask import Flask
from threading import Thread
from discord import Intents, Client, Message
from playwright.async_api import async_playwright

# === Load Environment ===
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID_RAW = os.getenv("CHANNEL_ID")
COOKIE_S = os.getenv("COOKIE_S")
CF_CLEARANCE = os.getenv("CF_CLEARANCE")
CF_BM = os.getenv("CF_BM")

if not DISCORD_TOKEN or not CHANNEL_ID_RAW:
    raise ValueError("DISCORD_TOKEN or CHANNEL_ID missing.")
CHANNEL_ID = int(CHANNEL_ID_RAW)

# === Flask server for keep-alive ===
app = Flask('')
@app.route('/')
def home():
    return "Bot is running."

def run_flask():
    app.run(host='0.0.0.0', port=8080)
Thread(target=run_flask).start()

# === Discord Client ===
intents = Intents.default()
intents.message_content = True
client = Client(intents=intents)

async def send_discord_message(text):
    channel = client.get_channel(CHANNEL_ID)
    if channel:
        await channel.send(text)

# === Login Check Command ===
async def login_check():
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
        await page.wait_for_timeout(3000)
        content = await page.content()
        await browser.close()
        return "Logout" not in content  # True if logged in

# === Time Left Checker ===
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
        await page.wait_for_timeout(3000)
        countdown = await page.query_selector("cw-countdown")
        time_left = await countdown.inner_text() if countdown else None
        await browser.close()
        return time_left

# === Daily Claim Automation ===
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

        countdown = await page.query_selector("cw-countdown")
        if countdown:
            time_left = await countdown.inner_text()
            await send_discord_message(f"⏳ Dailies not ready. Time left: **{time_left}**")
            await browser.close()
            return "not_ready"

        try:
            # Click the button using text filter
            await page.locator("button", has_text="Create Free Daily Battle").first.click(timeout=10000)
            await page.wait_for_timeout(2000)
            await page.click("#mat-option-18")
            await page.wait_for_timeout(1000)
            await page.click("#mat-option-23")
            await page.wait_for_timeout(1000)
            await page.click("text=Create battle for free vs bots")
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

# === Background Loop ===
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

    elif content == "!logincheck":
        await message.channel.send("🔐 Checking login status...")
        try:
            logged_in = await login_check()
            if logged_in:
                await message.channel.send("✅ Successfully logged into your CSGORoll account.")
            else:
                await message.channel.send("❌ Not logged in. Your cookies may be invalid or expired.")
        except Exception as e:
            await message.channel.send(f"❌ Login check error: {e}")

client.run(DISCORD_TOKEN)
