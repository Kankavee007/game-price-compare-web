class UpstreamError(Exception):
    """API ภายนอก (CheapShark / er-api) ล่ม ช้าเกิน หรือตอบผิดรูปแบบ"""


class InvalidCurrencyError(ValueError):
    """สกุลเงินที่ผู้ใช้ขอไม่มีในตารางอัตราแลกเปลี่ยน"""
