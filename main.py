import logging

import discord
from discord.ext import commands

import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)-8s %(name)s %(message)s")

EXTENSOES = ("cogs.apelidos", "cogs.status", "cogs.ia", "cogs.ensinar", "cogs.roubos")


class Legacianna(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True          # ativar também no Developer Portal
        intents.message_content = True  # ativar também no Developer Portal
        super().__init__(command_prefix=config.PREFIX, intents=intents, help_command=None)

    async def setup_hook(self):
        for ext in EXTENSOES:
            await self.load_extension(ext)

    async def on_ready(self):
        print(f"{self.user} está online! 🍞💖")

    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            return
        logging.getLogger("legacianna").error("Erro no comando %s: %s", ctx.command, error)


def main():
    if not config.DISCORD_BOT_TOKEN:
        raise SystemExit("DISCORD_BOT_TOKEN não encontrado no .env")
    if not config.GROQ_API_KEY:
        raise SystemExit("GROQ_API_KEY não encontrado no .env")
    Legacianna().run(config.DISCORD_BOT_TOKEN, log_handler=None)


if __name__ == "__main__":
    main()
