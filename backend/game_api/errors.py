class UpstreamError(Exception):
    """API ภายนอก (CheapShark / er-api) ล่ม ช้าเกิน หรือตอบผิดรูปแบบ"""


class UpstreamNotFoundError(UpstreamError):
    """API ภายนอกตอบ 404 เช่น CheapShark ไม่รู้จัก game id

    Subclass of UpstreamError so callers that do not care still treat it as "upstream failed";
    callers that do care (cheapshark.get_game) catch it first and turn it into "no such game".
    """


class ConfigError(Exception):
    """Server ตั้งค่าไม่ครบ เช่น ไม่มี env TWITCH_CLIENT_ID ตอบ 500 ไม่ใช่ 502

    Not a subclass of UpstreamError on purpose: routes catch UpstreamError and answer 502
    ("the other API is down"), which would send whoever debugs it to look at the wrong place.
    """


class InvalidCurrencyError(ValueError):
    """สกุลเงินที่ผู้ใช้ขอไม่มีในตารางอัตราแลกเปลี่ยน"""


class InvalidParamError(ValueError):
    """A query parameter from the user is invalid (bad number, unknown sort...). Routes answer 400.

    The message names the parameter and is safe to show to the user.
    """
