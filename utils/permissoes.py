import config


def eh_autorizado(member) -> bool:
    """Administrador do servidor ou ID listado em IDS_AUTORIZADOS."""
    return member.guild_permissions.administrator or member.id in config.IDS_AUTORIZADOS
