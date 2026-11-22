import discord
from discord.ext import commands

from ai import conhecimento
from utils.permissoes import eh_autorizado

SEM_MENCOES = discord.AllowedMentions.none()


class Ensinar(commands.Cog):
    """Comandos para ensinar coisas sobre o servidor à Legacianna (só admins)."""

    async def cog_check(self, ctx: commands.Context) -> bool:
        if ctx.guild is None:
            return False
        if not eh_autorizado(ctx.author):
            await ctx.reply("Só quem manda aqui pode me ensinar coisas 🍞", mention_author=False)
            return False
        return True

    @commands.command(name="ensinar")
    async def ensinar(self, ctx: commands.Context, *, fato: str = ""):
        """+ensinar <fato> — ensina uma coisa nova à Legacianna."""
        try:
            conhecimento.adicionar(fato)
        except ValueError as e:
            await ctx.reply(str(e), mention_author=False, allowed_mentions=SEM_MENCOES)
            return
        await ctx.reply("Anotado! Aprendi uma coisinha nova ✨", mention_author=False)

    @commands.command(name="conhecimento")
    async def ver(self, ctx: commands.Context):
        """+conhecimento — mostra o que ela sabe."""
        fatos = conhecimento.listar()
        if not fatos:
            await ctx.reply("Ainda não sei nada sobre o servidor. Use `+ensinar`!", mention_author=False)
            return
        texto = "\n".join(f"**{i}.** {f}" for i, f in enumerate(fatos, 1))
        await ctx.reply(texto[:1900], mention_author=False, allowed_mentions=SEM_MENCOES)

    @commands.command(name="esquecer")
    async def esquecer(self, ctx: commands.Context, numero: int):
        """+esquecer <número> — faz ela esquecer uma coisa da lista."""
        try:
            conhecimento.remover(numero)
        except ValueError as e:
            await ctx.reply(str(e), mention_author=False)
            return
        await ctx.reply("Esqueci! 💨", mention_author=False)

    @esquecer.error
    async def esquecer_erro(self, ctx, error):
        if isinstance(error, (commands.BadArgument, commands.MissingRequiredArgument)):
            await ctx.reply("Use `+esquecer <número>` (veja os números em `+conhecimento`).", mention_author=False)


async def setup(bot: commands.Bot):
    await bot.add_cog(Ensinar())
