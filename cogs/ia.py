import logging
import re

import discord
from discord.ext import commands

import config
from ai.groq_client import perguntar, resumo_uso
from utils.cooldown import can_reply
from utils.permissoes import eh_autorizado

log = logging.getLogger("legacianna.ia")

SEM_MENCOES = discord.AllowedMentions.none()


def _extras(msg: discord.Message) -> str:
    """Descreve o que não é texto: embeds, anexos e figurinhas."""
    partes = []
    for emb in msg.embeds:
        t = " - ".join(x for x in (emb.title, emb.description) if x)
        if t:
            partes.append(f"[embed: {t}]")
    for a in msg.attachments:
        tipo = "imagem" if (a.content_type or "").startswith("image/") else "anexo"
        partes.append(f"[{tipo}: {a.filename}]")
    if msg.stickers:
        partes.append("[figurinha: " + ", ".join(s.name for s in msg.stickers) + "]")
    return " ".join(partes)


def _descrever(msg: discord.Message, limite: int = 500) -> str:
    """Texto + embeds/anexos de uma mensagem, para a IA ler."""
    return " ".join(x for x in (msg.clean_content.strip(), _extras(msg)) if x)[:limite]


def montar_texto(message: discord.Message, ref: discord.Message | None, bot_id: int) -> str:
    """Monta o que a Legacianna vai ler: a mensagem da pessoa e, se houver, a mensagem marcada/respondida."""
    texto = re.sub(rf"<@!?{bot_id}>", "", message.content).strip()
    extras = _extras(message)
    texto = " ".join(x for x in (texto, extras) if x)

    if ref is None:
        return texto or "oi"

    de_quem = "sua" if ref.author.id == bot_id else "de outra pessoa"
    lida = _descrever(ref) or "(mensagem vazia)"
    if texto:
        return f'(mensagem {de_quem} que a pessoa está respondendo: "{lida}")\n{texto}'
    return f'(a pessoa te marcou numa mensagem {de_quem} e quer que você leia e reaja a ela: "{lida}")'


class IA(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.ativa = True

    async def _contexto(self, message: discord.Message) -> str:
        linhas = []
        async for msg in message.channel.history(limit=config.CONTEXT_MESSAGES, before=message):
            if msg.author.bot:
                continue
            autor = "Pessoa" if msg.author.id == message.author.id else "Outra pessoa"
            linhas.append(f"{autor}: {msg.clean_content.strip()}")
        return "\n".join(reversed(linhas))

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or message.guild is None or not self.ativa:
            return

        bot_user = self.bot.user
        mencionada = bot_user in message.mentions

        # Mensagem à qual a pessoa está respondendo (se houver)
        ref = None
        if message.reference:
            ref = message.reference.resolved
            if ref is None and message.reference.message_id:
                try:
                    ref = await message.channel.fetch_message(message.reference.message_id)
                except discord.HTTPException:
                    ref = None
            if not isinstance(ref, discord.Message):
                ref = None

        respondendo_ela = ref is not None and ref.author.id == bot_user.id

        if not (mencionada or respondendo_ela):
            return
        if message.content.startswith(config.PREFIX):
            return  # é um comando, não conversa

        texto = montar_texto(message, ref, bot_user.id)

        if not can_reply(message.author.id):
            return

        try:
            async with message.channel.typing():
                contexto = await self._contexto(message)
                resposta = await perguntar(texto, message.author, contexto)
        except Exception:
            log.exception("Erro ao falar com a Groq")
            resposta = "Ai... bateu um soninho aqui e eu me perdi. Tenta de novo daqui a pouquinho? 💤"

        if resposta:
            await message.reply(resposta[:2000], mention_author=False, allowed_mentions=SEM_MENCOES)

    @commands.command(name="uso")
    async def uso(self, ctx: commands.Context):
        """+uso — mostra quantos tokens a IA gastou hoje."""
        if not eh_autorizado(ctx.author):
            return
        await ctx.reply(resumo_uso(), mention_author=False)

    @commands.command(name="ia")
    async def ia_toggle(self, ctx: commands.Context, estado: str | None = None):
        """+ia on / +ia off — liga ou desliga as respostas da IA."""
        if not eh_autorizado(ctx.author):
            await ctx.reply("Só quem manda aqui pode mexer nisso 🍞", mention_author=False)
            return

        if estado is None or estado.lower() not in ("on", "off"):
            situacao = "ligada" if self.ativa else "desligada"
            await ctx.reply(f"A IA está **{situacao}**. Use `{config.PREFIX}ia on` ou `{config.PREFIX}ia off`.", mention_author=False)
            return

        self.ativa = estado.lower() == "on"
        await ctx.reply("Acordei! Pode falar comigo 💖" if self.ativa else "Vou tirar uma sonequinha... 💤", mention_author=False)


async def setup(bot: commands.Bot):
    await bot.add_cog(IA(bot))
