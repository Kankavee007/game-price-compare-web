"""Entrypoint: Vercel โหลดตัวแปร `app` จากไฟล์นี้ (ดู vercel.json)"""

import os

from game_api import create_app

app = create_app()

if __name__ == "__main__":
    # Local development only.
    app.run(
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "5000")),
        debug=os.environ.get("FLASK_DEBUG") == "1",
    )
