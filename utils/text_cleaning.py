import re


def remove_bold_markdown(text: str) -> str:
    """Remove negrito em markdown."""
    return re.sub(r"\*\*(.*?)\*\*", r"\1", text)


def remove_extra_spaces(text: str) -> str:
    """Remove espaços duplicados ou desnecessários."""
    return re.sub(r"\s+", " ", text).strip()


def trocar_aka(text: str) -> str:
    """A IA gosta de abreviar "também conhecido como" para "aka"; volta pro português."""
    return re.sub(r"\baka\b", "também conhecido como", text, flags=re.IGNORECASE)


def clean_response(text: str) -> str:
    """Limpa a resposta da IA antes de enviar."""
    return remove_extra_spaces(trocar_aka(remove_bold_markdown(text)))


def encurtar(text: str, max_frases: int = 2, max_chars: int = 200) -> str:
    """Garante respostas curtas, mesmo que a IA fale demais."""
    partes = re.split(r"(?<=[.!?…])\s+", text.strip())
    text = " ".join(partes[:max_frases])
    if len(text) > max_chars:
        text = text[:max_chars].rsplit(" ", 1)[0].rstrip(",;:") + "…"
    return text


def remover_nomes(text: str, nomes, protegidos=()) -> str:
    """Tira da resposta o nome da pessoa, exceto nomes que fazem parte dos fatos ensinados."""
    base = " ".join(protegidos).lower()
    for nome in sorted({n for n in nomes if n and len(n) >= 4}, key=len, reverse=True):
        if nome.lower() in base:
            continue
        text = re.sub(rf",?\s*\b{re.escape(nome)}\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^[,;:\s]+", "", text)
    text = re.sub(r"\s+([!?.,])", r"\1", text)
    return text.strip()
