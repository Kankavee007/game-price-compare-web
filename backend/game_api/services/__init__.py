"""Business logic และตัวเรียก API ภายนอก

- cheapshark.py:  ค้นเกม ข้อมูลเกมตาม id หาร้านของ deal และชื่อร้าน (CheapShark API)
- exchange.py:    อัตราแลกเปลี่ยนจาก USD (open.er-api.com)
- igdb.py:        ข้อมูลเกม (ชื่อ ประเภท คะแนน ปก) จาก IGDB ผ่าน token ของ Twitch
- search.py:      รวม cheapshark + exchange เป็นผลค้นหาที่ส่งให้ frontend
- game_detail.py: รวม cheapshark + exchange + igdb เป็นหน้ารายละเอียดเกม
"""
