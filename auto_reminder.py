import sqlite3
import requests
import re
from datetime import datetime

TELEGRAM_BOT_TOKEN = "8752100386:AAEa-vMD4yPCKE0LPTFx-198Llbf8qZFgE8"
ADMIN_CHAT_ID = "8548828754"
ADMIN_MOBILE = "01766222373"
SOMITI_NAME = "ঐক্য উদ্যোগ সংস্থা"

def get_template(template_id):
    conn = sqlite3.connect('somiti.db')
    c = conn.cursor()
    c.execute("SELECT template_content FROM message_templates WHERE id = ?", (template_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else ""

def format_message(template, **kwargs):
    message = template
    kwargs['somiti_name'] = SOMITI_NAME
    kwargs['admin_mobile'] = ADMIN_MOBILE
    
    for key, value in kwargs.items():
        message = message.replace("{" + key + "}", str(value))
    
    message = re.sub(r'\*(.*?)\*', r'<b>\1</b>', message)
    return message

def send_telegram_message(chat_id, message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"})
        return True
    except:
        return False

def get_bangla_month():
    months = {1: "জানুয়ারি", 2: "ফেব্রুয়ারি", 3: "মার্চ", 4: "এপ্রিল",
              5: "মে", 6: "জুন", 7: "জুলাই", 8: "আগস্ট",
              9: "সেপ্টেম্বর", 10: "অক্টোবর", 11: "নভেম্বর", 12: "ডিসেম্বর"}
    return months[datetime.now().month]

def main():
    today = datetime.now()
    current_month = today.strftime("%Y-%m")
    month_name = get_bangla_month()
    year = today.year
    
    if today.day == 1:
        template = get_template("first_day")
        if template:
            conn = sqlite3.connect('somiti.db')
            c = conn.cursor()
            c.execute("SELECT name, telegram_chat_id, monthly_savings, total_savings FROM members WHERE status = 'active'")
            members = c.fetchall()
            conn.close()
            
            for name, chat_id, monthly, savings in members:
                if chat_id:
                    msg = format_message(template, member_name=name, month=month_name, year=year,
                                        monthly_amount=f"{monthly:,.0f}", total_savings=f"{savings:,.0f}")
                    send_telegram_message(chat_id, msg)
            print(f"১ তারিখ: {len(members)} জনকে রিমাইন্ডার পাঠানো হয়েছে")
    
    elif today.day == 10:
        template = get_template("tenth_day")
        if template:
            conn = sqlite3.connect('somiti.db')
            c = conn.cursor()
            c.execute("SELECT id, name, telegram_chat_id, monthly_savings FROM members WHERE status = 'active'")
            members = c.fetchall()
            
            sent = 0
            for member_id, name, chat_id, monthly in members:
                if chat_id:
                    c.execute("SELECT SUM(amount) FROM transactions WHERE member_id = ? AND month = ?", 
                             (member_id, current_month))
                    paid = c.fetchone()[0] or 0
                    
                    if paid < monthly:
                        due = monthly - paid
                        msg = format_message(template, member_name=name, month=month_name, year=year,
                                            total_due_amount=f"{monthly:,.0f}", 
                                            paid_amount=f"{paid:,.0f}",
                                            due_amount=f"{due:,.0f}")
                        send_telegram_message(chat_id, msg)
                        sent += 1
            conn.close()
            print(f"১০ তারিখ: {sent} জন বকেয়াদারকে রিমাইন্ডার পাঠানো হয়েছে")

if __name__ == "__main__":
    main()
