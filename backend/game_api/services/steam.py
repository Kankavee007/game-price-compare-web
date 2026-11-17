from .. import config


def steam_cover_url(steam_app_id):
    """Portrait Steam cover URL for a Steam app id, or None when there is no usable id.

    CheapShark gives steamAppID as a string or null. Only plain digits are used, so nothing
    from outside ends up in the URL path.
    """
    value = str(steam_app_id).strip() if steam_app_id is not None else ""
    if not (value.isascii() and value.isdigit()) or int(value) == 0:
        return None
    return config.STEAM_COVER_URL.format(int(value))
