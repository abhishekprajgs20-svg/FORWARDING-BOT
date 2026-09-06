from aiohttp import web

async def handle(request):
    return web.Response(text="Bot is running!")

app = web.Application()
app.add_routes([web.get('/', handle)])

def get_app():
    return app
