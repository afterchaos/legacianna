import os
import re
import asyncio
import itertools
import discord
from discord.ext import tasks
from dotenv import load_dotenv

load_dotenv()  # carrega o arquivo .env
TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise SystemExit("Token não encontrado. Confira o nome da variável no .env (DISCORD_TOKEN).")

PREFIXO = "[Cl]"
PADRAO_GUEST = re.compile(r"^\s*guest\s+", re.IGNORECASE)

# True = ao ligar, o bot varre os membros que já estão no servidor
VARRER_AO_LIGAR = True

intents = discord.Intents.default()
intents.members = True  # precisa estar ativado no Developer Portal também

client = discord.Client(intents=intents)

# Status que ficam alternando (troca a cada 60 segundos)
STATUS = itertools.cycle([
    discord.Game(name="Legacy 💖"),
    discord.Activity(type=discord.ActivityType.watching, name="seus apelidos 👀"),
    discord.Activity(type=discord.ActivityType.listening, name="pedidos de pão 🍞"),
])


@tasks.loop(seconds=60)
async def trocar_status():
    await client.change_presence(activity=next(STATUS))


def calcular_novo_nome(member: discord.Member) -> str | None:
    """Retorna o novo apelido, ou None se não precisar mudar."""
    nick = member.nick

    # Já está com [Cl], não mexe
    if nick and nick.lower().startswith(PREFIXO.lower()):
        return None

    # Caso 1: apelido com Guest -> troca Guest por [Cl]
    if nick and PADRAO_GUEST.match(nick):
        novo = PADRAO_GUEST.sub(f"{PREFIXO} ", nick, count=1)
        return novo[:32]

    # Qualquer outro caso (sem apelido ou apelido normal) -> não mexe
    return None


async def ajustar_membro(member: discord.Member):
    if member.bot:
        return
    novo = calcular_novo_nome(member)
    if novo and novo != member.nick:
        try:
            await member.edit(nick=novo, reason="Padronizando apelido com [Cl]")
            print(f"{member} -> {novo}")
        except discord.Forbidden:
            print(f"Sem permissão para alterar {member} (cargo do bot abaixo do membro?)")
        except discord.HTTPException as e:
            print(f"Erro ao alterar {member}: {e}")


@client.event
async def on_ready():
    print(f"Bot online como {client.user}")
    if not trocar_status.is_running():
        trocar_status.start()
    if VARRER_AO_LIGAR:
        for guild in client.guilds:
            for member in guild.members:
                await ajustar_membro(member)
                await asyncio.sleep(0.5)  # evita rate limit


@client.event
async def on_member_join(member: discord.Member):
    # Dá um tempo pro Bloxlink colocar o apelido dele
    await asyncio.sleep(10)
    atual = member.guild.get_member(member.id)
    if atual:
        await ajustar_membro(atual)


@client.event
async def on_member_update(before: discord.Member, after: discord.Member):
    # Dispara quando o Bloxlink (ou alguém) muda o apelido
    if before.nick != after.nick:
        await ajustar_membro(after)


client.run(TOKEN)