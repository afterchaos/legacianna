import itertools

import discord
from discord.ext import commands, tasks

import config

TIPOS = {
    "watching": discord.ActivityType.watching,
    "listening": discord.ActivityType.listening,
    "competing": discord.ActivityType.competing,
}


def montar_atividade(tipo: str, texto: str) -> discord.BaseActivity:
    if tipo == "playing":
        return discord.Game(name=texto)
    return discord.Activity(type=TIPOS[tipo], name=texto)


class Status(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.ciclo = itertools.cycle(montar_atividade(t, x) for t, x in config.STATUS)
        self.trocar.change_interval(seconds=config.STATUS_INTERVAL)

    async def cog_load(self):
        self.trocar.start()

    async def cog_unload(self):
        self.trocar.cancel()

    @tasks.loop(seconds=60)
    async def trocar(self):
        await self.bot.change_presence(activity=next(self.ciclo))

    @trocar.before_loop
    async def antes(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(Status(bot))
