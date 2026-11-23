import asyncio
import json
import logging
import os
import re
from datetime import datetime, timezone
from urllib.parse import quote, urlsplit

import aiohttp
import discord
from discord.ext import commands, tasks


LOGGER = logging.getLogger(__name__)
QUEUE = "LegacyRobberyLogs_v1"
COMBAT_QUEUE = "LegacyCombatLogs_v1"
AVATAR_URL = "https://thumbnails.roblox.com/v1/users/avatar"
USERNAME_URL = "https://users.roblox.com/v1/usernames/users"
LOCATIONS = {
    "Bank": "Banco Legacy",
    "Bar": "Bar Legacy │ Caixa registradora",
    "ATM": "Banco Legacy │ Cidade",
    "Vault": "Banco Legacy │ Cofre",
    "Jewelry": "Joalheria Legacy",
}


def ler_dados(item):
    event = item.get("data")
    if isinstance(event, str):
        event = json.loads(event)
    if not isinstance(event, dict):
        raise ValueError("formato de evento inválido")
    return event


def ler_assalto(item):
    event = ler_dados(item)
    if event.get("action") == "loot":
        return None
    if event.get("action") != "start":
        raise ValueError("tipo de evento desconhecido")

    if event.get("kind") not in LOCATIONS:
        raise ValueError("local do assalto desconhecido")
    return event


def ler_eliminacao(item):
    event = ler_dados(item)
    if event.get("action") != "kill":
        raise ValueError("tipo de evento de combate desconhecido")
    return event


def montar_embed(event, avatar=None):
    descricao = f"**{LOCATIONS[event['kind']]}**\n\n**Assalto confirmado**"
    username = event.get("username")
    if isinstance(username, str) and username.strip():
        nome = " ".join(username.split())[:20].replace("`", "")
        if nome:
            descricao += f"\n**Assaltante:** `{nome}`"
    embed = discord.Embed(
        title="REGISTROS DE ROUBO",
        description=descricao,
        colour=0xE53935,
    )
    completar_embed(embed, event, avatar)
    return embed


def montar_embed_combate(event, avatar=None):
    campos = (
        ("Jogador eliminado", event.get("victim")),
        ("Eliminado por", event.get("username")),
        ("Arma usada", event.get("weapon")),
    )
    linhas = []
    for rotulo, valor in campos:
        texto = " ".join(valor.replace("`", "").split())[:64] if isinstance(valor, str) else ""
        linhas.append(f"**{rotulo}:** `{texto or 'Não identificado'}`")
    embed = discord.Embed(
        title="RELATÓRIO DE COMBATE",
        description="\n".join(linhas),
        colour=0xE53935,
    )
    completar_embed(embed, event, avatar)
    return embed


def completar_embed(embed, event, avatar):
    timestamp = event.get("timestamp")
    if type(timestamp) is int and 0 < timestamp <= 253402300799:
        embed.timestamp = datetime.fromtimestamp(timestamp, timezone.utc)
    if avatar:
        embed.set_thumbnail(url=avatar)


def usuario_do_evento(evento):
    nome = evento.get("username")
    return nome.lower() if isinstance(nome, str) and re.fullmatch(r"[A-Za-z0-9_]{1,20}", nome) else None


class RegistrosRoblox(commands.Cog):
    def __init__(self, bot, universo, canal_id, chave):
        self.bot = bot
        self.canal_id = canal_id
        self.url = (
            f"https://apis.roblox.com/cloud/v2/universes/{universo}"
            f"/memory-store/queues/{quote(self.fila, safe='')}"
        )
        self.chave = chave
        self.sessao = None
        self.confirmacao_pendente = None
        self.ultimo_erro = None

    async def cog_load(self):
        self.sessao = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10))
        self.consultar.start()

    async def cog_unload(self):
        self.consultar.cancel()
        await self.sessao.close()

    async def confirmar(self):
        async with self.sessao.post(
            f"{self.url}/items:discard",
            headers={"x-api-key": self.chave},
            allow_redirects=False,
            json={"readId": self.confirmacao_pendente},
        ) as resposta:
            if resposta.status not in (200, 204, 404):
                raise ValueError(f"confirmação da fila: HTTP {resposta.status}")
        self.confirmacao_pendente = None

    async def resolver_ids(self, eventos):
        ids = []
        nomes = []
        for evento in eventos:
            user_id = evento.get("userId")
            ids.append(user_id if type(user_id) is int and user_id > 0 else None)
            nomes.append(usuario_do_evento(evento))
        faltantes = {nome for user_id, nome in zip(ids, nomes) if user_id is None and nome}
        if not faltantes:
            return ids

        try:
            async with self.sessao.post(
                USERNAME_URL,
                json={"usernames": sorted(faltantes), "excludeBannedUsers": False},
                timeout=aiohttp.ClientTimeout(total=4),
            ) as resposta:
                resposta.raise_for_status()
                dados = await resposta.json()
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as erro:
            LOGGER.warning("Falha ao buscar contas Roblox para os avatares: %s", erro)
            return ids

        encontrados = {}
        itens = dados.get("data") if isinstance(dados, dict) else None
        if isinstance(itens, list):
            for item in itens:
                if not isinstance(item, dict):
                    continue
                solicitado = item.get("requestedUsername") or item.get("name")
                user_id = item.get("id")
                if isinstance(solicitado, str) and solicitado.lower() in faltantes and type(user_id) is int and user_id > 0:
                    encontrados[solicitado.lower()] = user_id
        return [user_id or encontrados.get(nome) for user_id, nome in zip(ids, nomes)]

    async def buscar_avatares(self, ids):
        ids = {user_id for user_id in ids if user_id is not None}
        if not ids:
            return {}
        try:
            async with self.sessao.get(
                AVATAR_URL,
                params={
                    "userIds": ",".join(map(str, sorted(ids))),
                    "size": "420x420",
                    "format": "Png",
                    "isCircular": "false",
                },
                timeout=aiohttp.ClientTimeout(total=4),
            ) as resposta:
                resposta.raise_for_status()
                dados = await resposta.json()
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as erro:
            LOGGER.warning("Falha ao buscar miniaturas de avatar do Roblox: %s", erro)
            return {}

        itens = dados.get("data") if isinstance(dados, dict) else None
        if not isinstance(itens, list):
            return {}
        fotos = {}
        for item in itens:
            if not isinstance(item, dict) or item.get("state") != "Completed":
                continue
            user_id, url = item.get("targetId"), item.get("imageUrl")
            if type(user_id) is not int or user_id not in ids or not isinstance(url, str):
                continue
            try:
                origem = urlsplit(url)
            except ValueError:
                continue
            if origem.scheme == "https" and (origem.hostname or "").endswith(".rbxcdn.com"):
                fotos[user_id] = url
        return fotos

    async def processar_lote(self):
        if self.confirmacao_pendente:
            await self.confirmar()

        async with self.sessao.get(
            f"{self.url}/items:read",
            headers={"x-api-key": self.chave},
            allow_redirects=False,
            params={"count": "5", "invisibilityWindow": "90s"},
        ) as resposta:
            if resposta.status == 404:
                return
            if resposta.status != 200:
                raise ValueError(f"leitura da fila: HTTP {resposta.status}")
            lote = await resposta.json()

        itens = lote.get("queueItems", lote.get("items", []))
        if not itens:
            return
        leitura = lote.get("readId") or lote.get("id")
        if not leitura:
            raise ValueError("Roblox não retornou o ID da leitura")

        eventos = []
        for item in itens:
            try:
                evento = self.ler_evento(item)
                if evento is not None:
                    eventos.append(evento)
            except (KeyError, ValueError, TypeError, AttributeError, OverflowError):
                LOGGER.warning("Evento inválido recebido na fila %s.", self.fila)

        if eventos:
            canal = self.bot.get_channel(self.canal_id)
            if canal is None:
                canal = await self.bot.fetch_channel(self.canal_id)
            if not isinstance(canal, discord.abc.Messageable):
                raise ValueError("o canal de registros não aceita mensagens")
            ids = await self.resolver_ids(eventos)
            fotos = await self.buscar_avatares(ids)
            embeds = [self.montar_mensagem(evento, fotos.get(user_id)) for evento, user_id in zip(eventos, ids)]
            await canal.send(
                embeds=embeds,
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
                LOGGER.warning("Falha na integração da fila %s: %s", self.fila, mensagem)
            self.ultimo_erro = mensagem
        else:
            self.ultimo_erro = None

    @consultar.before_loop
    async def antes(self):
        await self.bot.wait_until_ready()


class Roubos(RegistrosRoblox):
    fila = QUEUE
    ler_evento = staticmethod(ler_assalto)
    montar_mensagem = staticmethod(montar_embed)


class Combate(RegistrosRoblox):
    fila = COMBAT_QUEUE
    ler_evento = staticmethod(ler_eliminacao)
    montar_mensagem = staticmethod(montar_embed_combate)


async def setup(bot: commands.Bot):
    universo = os.getenv("ROBLOX_UNIVERSE_ID", "")
    chave = os.getenv("ROBLOX_OPEN_CLOUD_KEY", "")
    if not (universo.isdecimal() and chave):
        LOGGER.info("Logs do Roblox desativados. Configure o universo e a chave.")
        return

    for cog, variavel in ((Roubos, "ROBBERY_LOG_CHANNEL_ID"), (Combate, "KILL_LOG_CHANNEL_ID")):
        canal_id = os.getenv(variavel, "")
        if canal_id.isdecimal() and int(canal_id) > 0:
            await bot.add_cog(cog(bot, universo, int(canal_id), chave))
