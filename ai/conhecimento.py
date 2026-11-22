"""Fatos que a Legacianna sabe sobre o servidor (data/conhecimento.txt)."""
from pathlib import Path

ARQUIVO = Path(__file__).resolve().parent.parent / "data" / "conhecimento.txt"
MAX_FATOS = 40
MAX_TAMANHO = 300


def _ler() -> tuple[list[str], list[str]]:
    """Retorna (comentários do topo, fatos)."""
    if not ARQUIVO.exists():
        return [], []
    comentarios, fatos = [], []
    for linha in ARQUIVO.read_text(encoding="utf-8").splitlines():
        s = linha.strip()
        if not s:
            continue
        (comentarios if s.startswith("#") else fatos).append(s)
    return comentarios, fatos


def _salvar(comentarios: list[str], fatos: list[str]) -> None:
    ARQUIVO.parent.mkdir(parents=True, exist_ok=True)
    ARQUIVO.write_text("\n".join(comentarios + fatos) + "\n", encoding="utf-8")


def listar() -> list[str]:
    return _ler()[1]


def adicionar(fato: str) -> None:
    fato = " ".join(fato.split())
    if not fato:
        raise ValueError("Escreva o que eu devo aprender.")
    if len(fato) > MAX_TAMANHO:
        raise ValueError(f"Muito grande! Use até {MAX_TAMANHO} caracteres.")
    comentarios, fatos = _ler()
    if len(fatos) >= MAX_FATOS:
        raise ValueError(f"Já sei {MAX_FATOS} coisas, esqueça alguma antes.")
    if fato in fatos:
        raise ValueError("Isso eu já sei!")
    _salvar(comentarios, fatos + [fato])


def remover(numero: int) -> str:
    comentarios, fatos = _ler()
    if not 1 <= numero <= len(fatos):
        raise ValueError("Não achei esse número. Veja a lista com o comando de conhecimento.")
    removido = fatos.pop(numero - 1)
    _salvar(comentarios, fatos)
    return removido
