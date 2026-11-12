class UpstreamError(Exception):
    """API ภายนอก (CheapShark / er-api) ล่ม ช้าเกิน หรือตอบผิดรูปแบบ"""


class ConfigError(Exception):
    """Server ตั้งค่าไม่ครบ เช่น ไม่มี env TWITCH_CLIENT_ID ตอบ 500 ไม่ใช่ 502

    Not a subclass of UpstreamError on purpose: routes catch UpstreamError and answer 502
    ("the other API is down"), which would send whoever debugs it to look at the wrong place.
    """


class InvalidCurrencyError(ValueError):
    """สกุลเงินที่ผู้ใช้ขอไม่มีในตารางอัตราแลกเปลี่ยน"""
