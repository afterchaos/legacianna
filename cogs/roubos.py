import asyncio
import json
import logging
import os
from urllib.parse import quote

import aiohttp
import discord
from discord.ext import commands, tasks


LOGGER = logging.getLogger(__name__)
QUEUE = "LegacyRobberyLogs_v1"
LOCATIONS = {
    "Bank": "Banco Legacy · caixa registradora",
    "Bar": "Bar Legacy · caixa registradora",
    "ATM": "Caixa eletrônico",
    "Vault": "Banco Legacy · cofre",
    "Jewelry": "Joalheria Legacy",
}


def formatar_registro(item):
    event = item.get("data")
    if isinstance(event, str):
        event = json.loads(event)
    if not isinstance(event, dict):
        raise ValueError("formato de evento inválido")
    if event.get("action") == "loot":
        return None
    if event.get("action") != "start":
        raise ValueError("tipo de evento desconhecido")

    location = LOCATIONS[event["kind"]]
    timestamp = event.get("timestamp")
    horario = f"<t:{timestamp}:t> " if type(timestamp) is int and timestamp > 0 else ""
    linha = f"{horario}**{location}** · Assalto confirmado"
    username = event.get("username")
    if isinstance(username, str) and username.strip():
        nome = discord.utils.escape_markdown(username[:20])
        linha += f" · {nome}"
    return linha


class Roubos(commands.Cog):
    def __init__(self, bot, universo, canal_id, chave):
        self.bot = bot
        self.canal_id = canal_id
        self.url = (
            f"https://apis.roblox.com/cloud/v2/universes/{universo}"
            f"/memory-store/queues/{quote(QUEUE, safe='')}"
        )
        self.chave = chave
        self.sessao = None
        self.confirmacao_pendente = None
        self.ultimo_erro = None

    async def cog_load(self):
        self.sessao = aiohttp.ClientSession(
            headers={"x-api-key": self.chave},
            timeout=aiohttp.ClientTimeout(total=10),
        )
        self.consultar.start()

    async def cog_unload(self):
        self.consultar.cancel()
        await self.sessao.close()

    async def confirmar(self):
        async with self.sessao.post(
            f"{self.url}/items:discard", json={"readId": self.confirmacao_pendente},
        ) as resposta:
            if resposta.status not in (200, 204, 404):
                resposta.raise_for_status()
        self.confirmacao_pendente = None

    async def processar_lote(self):
        if self.confirmacao_pendente:
            await self.confirmar()

        async with self.sessao.get(
            f"{self.url}/items:read",
            params={"count": "5", "invisibilityWindow": "90s"},
        ) as resposta:
            if resposta.status == 404:
                return
            resposta.raise_for_status()
            lote = await resposta.json()

        itens = lote.get("queueItems", lote.get("items", []))
        if not itens:
            return
        leitura = lote.get("readId") or lote.get("id")
        if not leitura:
            raise ValueError("Roblox não retornou o ID da leitura")

        linhas = []
        for item in itens:
            try:
                linha = formatar_registro(item)
                if linha is not None:
                    linhas.append(linha)
            except (KeyError, ValueError, TypeError, AttributeError, OverflowError):
                LOGGER.warning("Evento inválido recebido na fila de roubos.")

        if linhas:
            canal = self.bot.get_channel(self.canal_id)
            if canal is None:
                canal = await self.bot.fetch_channel(self.canal_id)
            if not isinstance(canal, discord.abc.Messageable):
                raise ValueError("o canal de roubos não aceita mensagens")
            await canal.send(
                "**Registros de roubos · Roblox**\n" + "\n".join(linhas),
                allowed_mentions=discord.AllowedMentions.none(),
            )

        self.confirmacao_pendente = leitura
        await self.confirmar()

    @tasks.loop(seconds=5)
    async def consultar(self):
        try:
            await self.processar_lote()
        except (aiohttp.ClientError, asyncio.TimeoutError, discord.HTTPException, ValueError) as erro:
            mensagem = str(erro)
            if mensagem != self.ultimo_erro:
                LOGGER.warning("Falha na integração de roubos: %s", mensagem)
            self.ultimo_erro = mensagem
        else:
            self.ultimo_erro = None

    @consultar.before_loop
    async def antes(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    universo = os.getenv("ROBLOX_UNIVERSE_ID", "")
    canal_id = os.getenv("ROBBERY_LOG_CHANNEL_ID", "")
    chave = os.getenv("ROBLOX_OPEN_CLOUD_KEY", "")
    if not (universo.isdecimal() and canal_id.isdecimal() and chave):
        LOGGER.info("Logs de roubos desativados. Configure as variáveis do Roblox e do canal.")
        return
    await bot.add_cog(Roubos(bot, universo, int(canal_id), chave))
