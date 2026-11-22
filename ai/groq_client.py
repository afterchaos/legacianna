import logging
import time
from datetime import date

from groq import AsyncGroq, RateLimitError

import config
from ai.conhecimento import listar
from ai.persona import build_system_prompt
from utils.text_cleaning import clean_response, encurtar, remover_nomes

log = logging.getLogger("legacianna.groq")

_client: AsyncGroq | None = None
_historico: dict[int, list[dict]] = {}
_ultima_interacao: dict[int, float] = {}
_uso = {"dia": date.today(), "tokens": 0, "respostas": 0, "reserva": 0}


def _get_client() -> AsyncGroq:
    global _client
    if _client is None:
        _client = AsyncGroq(api_key=config.GROQ_API_KEY)
    return _client


def _ajustes_do_modelo(modelo: str) -> tuple[int, dict]:
    """Modelos que 'pensam' (gpt-oss, qwen) gastam tokens raciocinando: esconde o raciocínio e dá mais espaço."""
    modelo = modelo.lower()
    limite = config.GENERATION_CONFIG["max_output_tokens"]
    if modelo.startswith("openai/gpt-oss"):
        return max(limite, 400), {"reasoning_effort": "low", "include_reasoning": False}
    if modelo.startswith("qwen/"):
        return max(limite, 400), {"reasoning_format": "hidden"}
    return limite, {}


def _registrar_uso(resposta, modelo: str) -> None:
    hoje = date.today()
    if _uso["dia"] != hoje:
        _uso.update(dia=hoje, tokens=0, respostas=0, reserva=0)

    usage = getattr(resposta, "usage", None)
    entrada = getattr(usage, "prompt_tokens", 0) or 0
    saida = getattr(usage, "completion_tokens", 0) or 0
    total = getattr(usage, "total_tokens", 0) or (entrada + saida)

    _uso["tokens"] += total
    _uso["respostas"] += 1
    if modelo != config.GROQ_MODEL:
        _uso["reserva"] += 1

    log.info("tokens: entrada=%s saída=%s total=%s | modelo=%s | hoje: %s respostas, %s tokens",
             entrada, saida, total, modelo, _uso["respostas"], _uso["tokens"])


def resumo_uso() -> str:
    r, t = _uso["respostas"], _uso["tokens"]
    media = t // r if r else 0
    texto = f"Hoje: **{r}** respostas, **{t}** tokens (média de {media} por resposta)."
    if _uso["reserva"]:
        texto += f" {_uso['reserva']} delas usaram o modelo reserva ({config.GROQ_FALLBACK_MODEL})."
    return texto


async def _chamar(modelo: str, mensagens: list[dict], temperatura: float):
    limite, extra = _ajustes_do_modelo(modelo)
    return await _get_client().chat.completions.create(
        model=modelo,
        messages=mensagens,
        temperature=temperatura,
        max_tokens=limite,
        top_p=config.GENERATION_CONFIG["top_p"],
        extra_body=extra or None,
    )


async def _gerar(mensagens: list[dict], temperatura: float, nomes: list[str]) -> str:
    modelo = config.GROQ_MODEL
    try:
        resposta = await _chamar(modelo, mensagens, temperatura)
    except RateLimitError:
        reserva = config.GROQ_FALLBACK_MODEL
        if not reserva or reserva == modelo:
            raise
        log.warning("Limite do modelo %s atingido, usando o reserva %s", modelo, reserva)
        modelo = reserva
        resposta = await _chamar(modelo, mensagens, temperatura)

    _registrar_uso(resposta, modelo)

    texto = clean_response(resposta.choices[0].message.content or "")
    texto = remover_nomes(texto, nomes, protegidos=listar())
    texto = encurtar(texto, config.MAX_FRASES, config.MAX_CHARS)
    if not texto:
        raise ValueError("A IA devolveu uma resposta vazia")
    return texto


async def perguntar(mensagem: str, usuario, contexto: str = "") -> str:
    """Envia a mensagem para a Groq e devolve a resposta da Legacianna."""
    uid = usuario.id
    agora = time.time()

    # Esquece o papo se a pessoa ficou muito tempo sem falar
    if agora - _ultima_interacao.get(uid, 0) > config.CHAT_TIMEOUT:
        _historico[uid] = []
    _ultima_interacao[uid] = agora
    historico = _historico.setdefault(uid, [])

    system = build_system_prompt(config.PRIORIZED_USERS.get(uid))

    if contexto:
        conteudo = f"Contexto recente do canal:\n{contexto}\n\nMensagem para você: {mensagem}"
    else:
        conteudo = mensagem

    mensagens = [{"role": "system", "content": system}, *historico, {"role": "user", "content": conteudo}]
    nomes = [usuario.display_name, usuario.name, getattr(usuario, "global_name", None)]
    temperatura = config.GENERATION_CONFIG["temperature"]

    texto = await _gerar(mensagens, temperatura, nomes)

    # Trava anti-repetição: se ela repetiu a resposta anterior, tenta de novo mais "solta"
    anterior = historico[-1]["content"] if historico else None
    if anterior and texto.strip().lower() == anterior.strip().lower():
        texto = await _gerar(mensagens, min(temperatura + 0.3, 1.2), nomes)

    # Guarda só a mensagem da pessoa (sem o contexto) para o histórico não crescer à toa
    historico.append({"role": "user", "content": mensagem})
    historico.append({"role": "assistant", "content": texto})
    del historico[:-config.MAX_HISTORY]

    return texto
