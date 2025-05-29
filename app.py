# app.py
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import os
import sqlite3
from utils.sm2 import update_sm2
from datetime import datetime

app = Flask(__name__)

line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))

db_path = os.path.join(os.path.dirname(__file__), 'vocabulary.db')

def get_connection():
    return sqlite3.connect(db_path)

@app.route("/webhook", methods=["POST"])
def callback():
    signature = request.headers["X-Line-Signature"]
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return "OK"

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    msg = event.message.text.strip().lower()

    if msg == "/start":
        profile = line_bot_api.get_profile(user_id)
        name = profile.display_name
        with get_connection() as conn:
            conn.execute("INSERT OR IGNORE INTO users (user_id, display_name) VALUES (?, ?)", (user_id, name))
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"歡迎你，{name}！你已註冊成功。"))

    elif msg == "/quiz":
        with get_connection() as conn:
            word = conn.execute("SELECT id, word, meaning FROM vocabulary ORDER BY RANDOM() LIMIT 1").fetchone()
            if word:
                word_id, word_text, meaning = word
                conn.execute("INSERT OR IGNORE INTO learning_status (user_id, word_id) VALUES (?, ?)", (user_id, word_id))
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"這個單字的意思是什麼？\n👉 {meaning}"))

    elif msg.startswith("/ans "):
        answer = msg.replace("/ans ", "").strip()
        with get_connection() as conn:
            row = conn.execute("""
                SELECT v.word, ls.word_id, ls.ease_factor, ls.interval, ls.repetition 
                FROM learning_status ls 
                JOIN vocabulary v ON ls.word_id = v.id 
                WHERE ls.user_id = ? ORDER BY ls.id DESC LIMIT 1
            """, (user_id,)).fetchone()
            if row:
                word, word_id, ef, interval, rep = row
                if answer.lower() == word.lower():
                    new_ef, new_int, new_rep = update_sm2(ef, interval, rep, 5)
                    conn.execute("""
                        UPDATE learning_status SET ease_factor=?, interval=?, repetition=?, last_review=datetime('now'), next_review=datetime('now', '+' || ? || ' days') 
                        WHERE user_id=? AND word_id=?
                    """, (new_ef, new_int, new_rep, new_int, user_id, word_id))
                    line_bot_api.reply_message(event.reply_token, TextSendMessage(text="✅ 答對了！加油！"))
                else:
                    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=f"❌ 答錯了，正確是：{word}"))

    else:
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text="請輸入 /start 註冊、/quiz 出題、或 /ans <你的答案> 回答題目。"))

if __name__ == "__main__":
    app.run(port=5000)
