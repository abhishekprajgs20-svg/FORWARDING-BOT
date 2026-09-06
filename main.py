import asyncio
from aiohttp import web
from bot import bot
from server import get_app

async def main():
    # Start bot
    await bot.start()
    print("Bot started.")
    
    # Start web server for Render
    app = get_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 10000)
    await site.start()
    print("Web server started on port 10000")
    
    # Keep running
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
