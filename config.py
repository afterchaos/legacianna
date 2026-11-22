"""Configurações da Legacianna. Edite aqui, não precisa mexer no resto do código."""
import os
from dotenv import load_dotenv

load_dotenv()

# ---------- Chaves (ficam no arquivo .env) ----------
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN") or os.getenv("DISCORD_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
# Modelo reserva: usado automaticamente quando o limite do principal acaba (cada modelo tem limite próprio)
GROQ_FALLBACK_MODEL = os.getenv("GROQ_FALLBACK_MODEL", "openai/gpt-oss-20b")

# ---------- Bot ----------
PREFIX = "+"

# IDs que podem usar comandos administrativos (além de quem tem permissão de Administrador)
IDS_AUTORIZADOS: list[int] = [
    # 123456789012345678,
]

# IDs prioritários: ignoram o cooldown e a Legacianna os trata pelo título definido aqui
PRIORIZED_USERS: dict[int, str] = {
    # 123456789012345678: "Fundador, nome",
}

# ---------- IA ----------
CHAT_TIMEOUT = 120      # segundos sem conversar até ela "esquecer" o papo com a pessoa
MAX_HISTORY = 4         # quantas mensagens do papo (pessoa + bot) ela lembra
CONTEXT_MESSAGES = 6    # quantas mensagens recentes do canal ela lê como contexto
USER_COOLDOWN = 15      # segundos entre respostas para a mesma pessoa
GLOBAL_COOLDOWN = 10    # segundos entre uma resposta e outra, no geral (servidor inteiro)


# Contas que ignoram os dois limites acima (sempre são respondidas)
IDS_SEM_LIMITE: list[int] = [
    # 123456789012345678,
]

MAX_FRASES = 2          # no máximo de frases por resposta
MAX_CHARS = 200         # no máximo de caracteres por resposta

GENERATION_CONFIG = {
    "temperature": 0.8,
    "max_output_tokens": 80,
    "top_p": 0.9,
}

# ---------- Apelidos ----------
PREFIXO_CLAN = "[Cl]"
VARRER_AO_LIGAR = True  # ao ligar, corrige quem já está no servidor com "Guest" no nome

# ---------- Status ----------
STATUS_INTERVAL = 20  # segundos entre cada troca
STATUS = [
    ("playing", "Legacy 💖"),
    ("watching", "seus apelidos 👀"),
    ("listening", "pedidos de pão 🍞"),
]
