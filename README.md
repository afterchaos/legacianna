# Legacianna 🍞💖

Mascote e bot do servidor Legacy.

## O que ela faz
- **IA:** conversa quando é mencionada (@Legacianna) ou quando respondem a uma mensagem dela.
- **Apelidos:** troca `Guest nome` por `[Cl] nome` (para o Bloxlink).
- **Status:** alterna entre vários status.
- **Ritmo:** ela responde a todo mundo, com 10 segundos entre uma resposta e outra, no geral (`GLOBAL_COOLDOWN`), e 15 segundos entre respostas para a mesma pessoa (`USER_COOLDOWN`). Contas em `IDS_SEM_LIMITE` ignoram os dois limites.
- `+ia on` / `+ia off`: liga e desliga a IA (só administradores).
- `+uso`: mostra quantos tokens a IA gastou hoje (só administradores). O terminal também mostra o gasto de cada resposta.
- **Ensinar:** `+ensinar <fato>`, `+conhecimento` e `+esquecer <número>` (só administradores).

## Como programar a Legacianna
- `data/personalidade.txt`: jeito de falar, regras e exemplos. Edite e salve, sem reiniciar. Anotações que a IA não vê começam com `//`.
- `data/conhecimento.txt`: fatos sobre o servidor, um por linha (ou use os comandos acima).

## Como rodar
1. `pip install -r requirements.txt`
2. Copie `.env.example` para `.env` e preencha o token e a chave da Groq.
3. No Developer Portal, ative **Server Members Intent** e **Message Content Intent**.
4. Dê ao bot as permissões **Manage Nicknames**, **Send Messages** e **Read Message History**, e deixe o cargo dele acima dos cargos dos membros.
5. `python main.py`

## Trocar o modelo da IA
`python listar_modelos.py` mostra os modelos disponíveis. Depois coloque `GROQ_MODEL=<id>` no `.env`.

O bot usa um modelo reserva (`GROQ_FALLBACK_MODEL`) quando o limite do principal acaba.

## Estrutura
```
main.py            inicia o bot e carrega os cogs
config.py          todas as configurações
ai/persona.py      monta o prompt (personalidade + conhecimento)
ai/conhecimento.py lê e grava os fatos do servidor
data/              personalidade.txt (otimizada), personalidade_original.txt (backup) e conhecimento.txt
ai/groq_client.py  conversa com a Groq, histórico por pessoa
cogs/ia.py         responde menções e replies
cogs/ensinar.py    comandos +ensinar, +conhecimento, +esquecer
cogs/apelidos.py   Guest -> [Cl]
cogs/status.py     status rotativos
utils/             cooldown e limpeza de texto
```
