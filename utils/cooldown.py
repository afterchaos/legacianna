import time

import config

_ultima_por_usuario: dict[int, float] = {}
_ultima_global = 0.0


def can_reply(user_id: int) -> bool:
    """Limites: GLOBAL_COOLDOWN entre qualquer resposta e USER_COOLDOWN por pessoa.
    Contas prioritárias e sem limite passam direto e não atrasam as outras."""
    global _ultima_global

    if user_id in config.PRIORIZED_USERS or user_id in config.IDS_SEM_LIMITE:
        return True

    agora = time.time()
    if agora - _ultima_global < config.GLOBAL_COOLDOWN:
        return False
    if agora - _ultima_por_usuario.get(user_id, 0) < config.USER_COOLDOWN:
        return False

    _ultima_por_usuario[user_id] = agora
    _ultima_global = agora
    return True
