import asyncio
import logging
import re

import discord
from discord.ext import commands

import config

log = logging.getLogger("legacianna.apelidos")

PADRAO_GUEST = re.compile(r"^\s*guest\s+", re.IGNORECASE)


def calcular_novo_nome(nick: str | None) -> str | None:
    """Troca 'Guest' por [Cl]. Retorna None se não precisar mudar."""
    if not nick or nick.lower().startswith(config.PREFIXO_CLAN.lower()):
        return None
    if PADRAO_GUEST.match(nick):
        return PADRAO_GUEST.sub(f"{config.PREFIXO_CLAN} ", nick, count=1)[:32]
    return None


class Apelidos(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def ajustar(self, member: discord.Member):
        if member.bot:
            return
        novo = calcular_novo_nome(member.nick)
        if not novo or novo == member.nick:
            return
        try:
            await member.edit(nick=novo, reason=f"Trocando Guest por {config.PREFIXO_CLAN}")
            log.info("%s -> %s", member, novo)
        except discord.Forbidden:
            log.warning("Sem permissão para alterar %s (cargo do bot abaixo do membro?)", member)
        except discord.HTTPException as e:
            log.error("Erro ao alterar %s: %s", member, e)

    @commands.Cog.listener()
    async def on_ready(self):
        if not config.VARRER_AO_LIGAR:
            return
        for guild in self.bot.guilds:
            for member in guild.members:
                await self.ajustar(member)
                await asyncio.sleep(0.5)  # evita rate limit

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        await asyncio.sleep(10)  # dá tempo pro Bloxlink colocar o apelido
        atual = member.guild.get_member(member.id)
        if atual:
            await self.ajustar(atual)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if before.nick != after.nick:
            await self.ajustar(after)


async def setup(bot: commands.Bot):
    await bot.add_cog(Apelidos(bot))
