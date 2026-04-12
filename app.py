import streamlit as st
import sqlite3
import smtplib
import random
import string
import pandas as pd
from datetime import datetime, timedelta
from io import BytesIO
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import shutil
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import json

# ============================================
# কনফিগারেশন
# ============================================
ADMIN_MOBILE = "01766222373"
ADMIN_PASSWORD = "oio112024"
SOMITI_NAME = "ঐক্য উদ্যোগ সংস্থা"
SOMITI_START_DATE = "2026-04-12"  # সমিতির শুরুর তারিখ

# ইমেইল কনফিগারেশন
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = "oiorganization2024@gmail.com"
SENDER_PASSWORD = "hnhm ocix kyxv ioiz"

# ============================================
# পেজ কনফিগ
# ============================================
st.set_page_config(page_title=SOMITI_NAME, page_icon="🌾", layout="wide")

# URL প্যারামিটার
query_params = st.query_params
member_login_id = query_params.get("member")
admin_view = query_params.get("admin")

# ============================================
# বাংলা মাসের নাম
# ============================================
BANGLA_MONTHS = {
    1: "জানুয়ারি", 2: "ফেব্রুয়ারি", 3: "মার্চ", 4: "এপ্রিল",
    5: "মে", 6: "জুন", 7: "জুলাই", 8: "আগস্ট",
    9: "সেপ্টেম্বর", 10: "অক্টোবর", 11: "নভেম্বর", 12: "ডিসেম্বর"
}

# ============================================
# ডাটাবেজ সেটআপ
# ============================================
def init_database():
    conn = sqlite3.connect('somiti.db')
    c = conn.cursor()
    
    # সেটিংস টেবিল
    c.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    
    # সমিতির শুরুর তারিখ সেভ
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('start_date', ?)", (SOMITI_START_DATE,))
    
    # সদস্য টেবিল
    c.execute('''
        CREATE TABLE IF NOT EXISTS members (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            phone TEXT UNIQUE NOT NULL,
            email TEXT,
            password TEXT NOT NULL,
            total_savings REAL DEFAULT 0,
            monthly_savings REAL DEFAULT 500,
            join_date TEXT,
            status TEXT DEFAULT 'active'
        )
    ''')
    
    # পুরনো ডাটাবেজ থেকে কলাম যোগ
    try:
        c.execute("SELECT email FROM members LIMIT 1")
    except:
        c.execute("ALTER TABLE members ADD COLUMN email TEXT")
    
    # লেনদেন টেবিল
    c.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id TEXT NOT NULL,
            amount REAL NOT NULL,
            transaction_type TEXT NOT NULL,
            day INTEGER NOT NULL,
            month INTEGER NOT NULL,
            year INTEGER NOT NULL,
            month_name TEXT NOT NULL,
            full_date TEXT NOT NULL,
            date_iso TEXT NOT NULL,
            note TEXT,
            late_fee REAL DEFAULT 0,
            created_at TEXT NOT NULL
        )
    ''')
    
    # পুরনো ট্রানজেকশন মাইগ্রেশন
    try:
        c.execute("SELECT day FROM transactions LIMIT 1")
    except:
        # নতুন কলাম যোগ
        c.execute("ALTER TABLE transactions ADD COLUMN day INTEGER DEFAULT 1")
        c.execute("ALTER TABLE transactions ADD COLUMN month INTEGER DEFAULT 1")
        c.execute("ALTER TABLE transactions ADD COLUMN year INTEGER DEFAULT 2026")
        c.execute("ALTER TABLE transactions ADD COLUMN month_name TEXT DEFAULT 'জানুয়ারি'")
        c.execute("ALTER TABLE transactions ADD COLUMN full_date TEXT DEFAULT ''")
        c.execute("ALTER TABLE transactions ADD COLUMN date_iso TEXT DEFAULT ''")
        c.execute("ALTER TABLE transactions ADD COLUMN created_at TEXT DEFAULT ''")
    
    # খরচ টেবিল
    c.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT NOT NULL,
            amount REAL NOT NULL,
            date TEXT NOT NULL,
            category TEXT
        )
    ''')
    
    # উত্তোলন টেবিল
    c.execute('''
        CREATE TABLE IF NOT EXISTS withdrawals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            amount REAL NOT NULL,
            description TEXT,
            withdrawn_by TEXT,
            previous_balance REAL,
            current_balance REAL,
            created_at TEXT NOT NULL
        )
    ''')
    
    conn.commit()
    conn.close()

# ============================================
# ২০ বছর চেক ও আর্কাইভ
# ============================================
def check_and_archive_old_data():
    """২০ বছর পর পুরনো ডাটা আর্কাইভ করে"""
    conn = sqlite3.connect('somiti.db')
    c = conn.cursor()
    c.execute("SELECT value FROM settings WHERE key = 'start_date'")
    result = c.fetchone()
    conn.close()
    
    if result:
        start_date = datetime.strptime(result[0], "%Y-%m-%d")
        years_passed = (datetime.now() - start_date).days / 365
        
        if years_passed >= 20:
            archive_file = f"somiti_archive_{start_date.year}_{datetime.now().year}.db"
            if not os.path.exists(archive_file):
                shutil.copy('somiti.db', archive_file)
                
                # নতুন ডাটাবেজ শুরু
                conn = sqlite3.connect('somiti.db')
                c = conn.cursor()
                c.execute("DELETE FROM transactions")
                c.execute("DELETE FROM expenses")
                c.execute("DELETE FROM withdrawals")
                c.execute("UPDATE members SET total_savings = 0")
                c.execute("UPDATE settings SET value = ? WHERE key = 'start_date'", 
                         (datetime.now().strftime("%Y-%m-%d"),))
                conn.commit()
                conn.close()
                return True
    return False

# ============================================
# ইমেইল ফাংশন
# ============================================
def send_email(to_email, subject, message):
    if not to_email:
        return False
    try:
        msg = MIMEMultipart()
        msg['From'] = f"{SOMITI_NAME} <{SENDER_EMAIL}>"
        msg['To'] = to_email
        msg['Subject'] = subject
        
        html = f"""
        <html>
        <head><meta charset="UTF-8"></head>
        <body style="font-family: Arial, sans-serif; background: #f5f5f5; padding: 20px;">
            <div style="max-width: 500px; margin: 0 auto; background: white; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 10px rgba(0,0,0,0.1);">
                <div style="background: #1a5276; color: white; padding: 25px; text-align: center;">
                    <h2 style="margin: 0;">🌾 {SOMITI_NAME}</h2>
                    <p style="margin: 5px 0 0; opacity: 0.9;">সঞ্চয় ও ঋণ ব্যবস্থাপনা</p>
                </div>
                <div style="padding: 30px;">
                    {message.replace(chr(10), '<br>')}
                </div>
                <div style="background: #f8f9fa; padding: 15px; text-align: center; font-size: 12px; color: #666; border-top: 1px solid #eee;">
                    <p style="margin: 0;">এই ইমেইলটি স্বয়ংক্রিয়ভাবে পাঠানো হয়েছে।</p>
                    <p style="margin: 5px 0 0;">প্রয়োজনে যোগাযোগ: {ADMIN_MOBILE}</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(html, 'html'))
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"ইমেইল এরর: {e}")
        return False

def send_email_to_all_active_members(subject, message):
    """সকল সক্রিয় সদস্যের ইমেইলে মেসেজ পাঠায়"""
    conn = sqlite3.connect('somiti.db')
    c = conn.cursor()
    c.execute("SELECT email, name FROM members WHERE status = 'active' AND email IS NOT NULL AND email != ''")
    members = c.fetchall()
    conn.close()
    
    sent = 0
    for email, name in members:
        personalized = message.replace("{name}", name)
        if send_email(email, subject, personalized):
            sent += 1
    return sent

# ============================================
# ইমেইল টেমপ্লেট (প্রফেশনাল)
# ============================================
def get_welcome_email(name, member_id, phone, password, monthly):
    return f"""প্রিয় {name},

═══════════════════════════════════════════════════════════════════
                    🎉 স্বাগতম - {SOMITI_NAME}
═══════════════════════════════════════════════════════════════════

আপনাকে জানাই আন্তরিক স্বাগতম! আজ থেকে আপনি "{SOMITI_NAME}" এর একজন গর্বিত সদস্য।

┌─────────────────────────────────────────────────────────────────┐
│                       📋 সদস্যপদ বিবরণ                           │
├─────────────────────────────────────────────────────────────────┤
│   🆔 সদস্য আইডি          : {member_id}                           │
│   👤 সদস্যের নাম         : {name}                                │
│   📱 মোবাইল নম্বর        : {phone}                               │
│   🔐 অস্থায়ী পাসওয়ার্ড   : {password}                            │
│   💰 মাসিক সঞ্চয়         : {monthly} টাকা                        │
└─────────────────────────────────────────────────────────────────┘

🔗 আপনার ব্যক্তিগত ড্যাশবোর্ড:
   https://oiorganization2024.streamlit.app/?member={member_id}

⚠️ গুরুত্বপূর্ণ:
   • প্রথম লগইনের পর পাসওয়ার্ড পরিবর্তন করুন
   • আপনার তথ্য কারো সাথে শেয়ার করবেন না
   • প্রতি মাসের ১০ তারিখের মধ্যে কিস্তি জমা দিন

💚 "আপনার সঞ্চয়, আপনার ভবিষ্যৎ"

আন্তরিক শুভেচ্ছায়,
{SOMITI_NAME} কর্তৃপক্ষ
📞 {ADMIN_MOBILE}"""

def get_payment_success_email(name, amount, full_date, month_name, total_savings):
    return f"""প্রিয় {name},

═══════════════════════════════════════════════════════════════════
                    ✅ পেমেন্ট সফল - {SOMITI_NAME}
═══════════════════════════════════════════════════════════════════

আপনার সঞ্চয় জমা সফলভাবে গৃহীত হয়েছে।

┌─────────────────────────────────────────────────────────────────┐
│                        💰 পেমেন্ট রসিদ                           │
├─────────────────────────────────────────────────────────────────┤
│   জমার তারিখ          : {full_date}                              │
│   জমার মাস            : {month_name}                             │
│   জমার পরিমাণ         : {amount} টাকা                            │
│   ───────────────────────────────────────────────────────────── │
│   🌟 বর্তমান মোট জমা    : {total_savings} টাকা                    │
└─────────────────────────────────────────────────────────────────┘

🙏 আপনার নিয়মিত সঞ্চয় সমিতির উন্নয়নে গুরুত্বপূর্ণ ভূমিকা রাখছে।

💚 "একতাই শক্তি, সঞ্চয়ই মুক্তি"

কৃতজ্ঞতায়,
{SOMITI_NAME} কর্তৃপক্ষ"""

def get_password_reset_email(name, new_password):
    return f"""প্রিয় {name},

═══════════════════════════════════════════════════════════════════
                  🔐 পাসওয়ার্ড রিসেট - {SOMITI_NAME}
═══════════════════════════════════════════════════════════════════

আপনার অ্যাকাউন্টের পাসওয়ার্ড রিসেট করা হয়েছে।

┌─────────────────────────────────────────────────────────────────┐
│                      🔐 নতুন লগইন তথ্য                           │
├─────────────────────────────────────────────────────────────────┤
│   🔑 নতুন পাসওয়ার্ড       : {new_password}                        │
│   📅 রিসেটের সময়         : {datetime.now().strftime('%d %B %Y, %I:%M %p')} │
└─────────────────────────────────────────────────────────────────┘

⚠️ গুরুত্বপূর্ণ:
   • লগইন করার পর অবিলম্বে পাসওয়ার্ড পরিবর্তন করুন
   • এই পাসওয়ার্ডটি শুধুমাত্র আপনি জানেন

❓ আপনি কি পাসওয়ার্ড রিসেটের অনুরোধ করেননি?
যদি তাই হয়, দয়া করে এডমিনকে জানান: {ADMIN_MOBILE}

{SOMITI_NAME} কর্তৃপক্ষ"""

def get_transaction_edit_email(name, old_amount, new_amount, full_date, total_savings):
    return f"""প্রিয় {name},

═══════════════════════════════════════════════════════════════════
                  ✏️ লেনদেন সংশোধন - {SOMITI_NAME}
═══════════════════════════════════════════════════════════════════

আপনার একটি লেনদেন সংশোধন করা হয়েছে।

┌─────────────────────────────────────────────────────────────────┐
│                     📝 সংশোধনের বিবরণ                            │
├─────────────────────────────────────────────────────────────────┤
│   তারিখ               : {full_date}                              │
│   পূর্বের পরিমাণ       : {old_amount} টাকা                       │
│   সংশোধিত পরিমাণ       : {new_amount} টাকা                       │
│   ───────────────────────────────────────────────────────────── │
│   বর্তমান মোট জমা      : {total_savings} টাকা                    │
└─────────────────────────────────────────────────────────────────┘

কোনো প্রশ্ন থাকলে যোগাযোগ করুন: {ADMIN_MOBILE}

{SOMITI_NAME} কর্তৃপক্ষ"""

def get_transaction_remove_email(name, amount, full_date, total_savings):
    return f"""প্রিয় {name},

═══════════════════════════════════════════════════════════════════
                  🗑️ লেনদেন বাতিল - {SOMITI_NAME}
═══════════════════════════════════════════════════════════════════

আপনার একটি লেনদেন বাতিল করা হয়েছে।

┌─────────────────────────────────────────────────────────────────┐
│                     📝 বাতিলের বিবরণ                             │
├─────────────────────────────────────────────────────────────────┤
│   তারিখ               : {full_date}                              │
│   বাতিলকৃত পরিমাণ      : {amount} টাকা                           │
│   ───────────────────────────────────────────────────────────── │
│   বর্তমান মোট জমা      : {total_savings} টাকা                    │
└─────────────────────────────────────────────────────────────────┘

কোনো প্রশ্ন থাকলে যোগাযোগ করুন: {ADMIN_MOBILE}

{SOMITI_NAME} কর্তৃপক্ষ"""

def get_withdrawal_notification(amount, description, date, previous_balance, current_balance):
    return f"""প্রিয় {name},

═══════════════════════════════════════════════════════════════════
                  🏧 টাকা উত্তোলনের নোটিশ - {SOMITI_NAME}
═══════════════════════════════════════════════════════════════════

সমিতির তহবিল থেকে টাকা উত্তোলন করা হয়েছে।

┌─────────────────────────────────────────────────────────────────┐
│                    🏧 উত্তোলনের বিবরণ                             │
├─────────────────────────────────────────────────────────────────┤
│   📅 উত্তোলনের তারিখ     : {date}                                │
│   💰 উত্তোলনের পরিমাণ    : {amount} টাকা                         │
│   📝 বিবরণ             : {description}                          │
│   ───────────────────────────────────────────────────────────── │
│   💵 পূর্বের ব্যালেন্স    : {previous_balance} টাকা               │
│   💵 বর্তমান ব্যালেন্স    : {current_balance} টাকা                │
└─────────────────────────────────────────────────────────────────┘

ℹ️ এটি শুধুমাত্র আপনার অবগতির জন্য পাঠানো হলো।

💚 "স্বচ্ছতা আমাদের অঙ্গীকার"

{SOMITI_NAME} কর্তৃপক্ষ"""

def get_lottery_winner_email(name):
    return f"""প্রিয় {name},

═══════════════════════════════════════════════════════════════════
                  🎉 অভিনন্দন! লাকি ড্র বিজয়ী - {SOMITI_NAME}
═══════════════════════════════════════════════════════════════════

╔═════════════════════════════════════════════════════════════════╗
║                    🎉  অভিনন্দন!  🎉                            ║
║                 আপনি লাকি ড্র বিজয়ী!                            ║
╚═════════════════════════════════════════════════════════════════╝

আপনি {SOMITI_NAME} এর লাকি ড্র-তে বিজয়ী হয়েছেন! 🏆

পুরস্কার সম্পর্কে বিস্তারিত জানতে যোগাযোগ করুন: {ADMIN_MOBILE}

💚 "আপনার সাফল্যে আমরা গর্বিত"

শুভেচ্ছান্তে,
{SOMITI_NAME} পরিবার"""

# ============================================
# হেল্পার ফাংশন
# ============================================
def generate_member_id():
    conn = sqlite3.connect('somiti.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM members")
    count = c.fetchone()[0] + 1
    conn.close()
    return f"{10000 + count}"  # ৫ ডিজিট: 10001, 10002...

def generate_password():
    return ''.join(random.choices(string.digits, k=6))

def get_total_savings():
    try:
        conn = sqlite3.connect('somiti.db')
        c = conn.cursor()
        c.execute("SELECT SUM(total_savings) FROM members WHERE status = 'active'")
        total = c.fetchone()[0] or 0
        conn.close()
        return total
    except:
        return 0

def get_total_expenses():
    try:
        conn = sqlite3.connect('somiti.db')
        c = conn.cursor()
        c.execute("SELECT SUM(amount) FROM expenses")
        total = c.fetchone()[0] or 0
        conn.close()
        return total
    except:
        return 0

def get_total_withdrawals():
    try:
        conn = sqlite3.connect('somiti.db')
        c = conn.cursor()
        c.execute("SELECT SUM(amount) FROM withdrawals")
        total = c.fetchone()[0] or 0
        conn.close()
        return total
    except:
        return 0

def get_cash_balance():
    return get_total_savings() - get_total_expenses() - get_total_withdrawals()

def get_paid_members():
    current = datetime.now()
    conn = sqlite3.connect('somiti.db')
    c = conn.cursor()
    c.execute("""
        SELECT DISTINCT m.id, m.name, m.phone, m.monthly_savings, m.total_savings, m.email
        FROM members m
        JOIN transactions t ON m.id = t.member_id
        WHERE m.status = 'active' AND t.month = ? AND t.year = ?
        ORDER BY m.name
    """, (current.month, current.year))
    paid = c.fetchall()
    conn.close()
    return paid

def get_unpaid_members():
    current = datetime.now()
    conn = sqlite3.connect('somiti.db')
    c = conn.cursor()
    
    c.execute("SELECT DISTINCT member_id FROM transactions WHERE month = ? AND year = ?", 
             (current.month, current.year))
    paid_ids = [row[0] for row in c.fetchall()]
    
    if paid_ids:
        placeholders = ','.join(['?' for _ in paid_ids])
        c.execute(f"""
            SELECT id, name, phone, monthly_savings, total_savings, email
            FROM members 
            WHERE status = 'active' AND id NOT IN ({placeholders})
            ORDER BY name
        """, paid_ids)
    else:
        c.execute("""
            SELECT id, name, phone, monthly_savings, total_savings, email
            FROM members 
            WHERE status = 'active'
            ORDER BY name
        """)
    
    unpaid = c.fetchall()
    conn.close()
    return unpaid

def get_member_transactions(member_id):
    try:
        conn = sqlite3.connect('somiti.db')
        c = conn.cursor()
        c.execute("""
            SELECT id, full_date, amount, month_name, year, late_fee, note, day, month, date_iso
            FROM transactions 
            WHERE member_id = ?
            ORDER BY year DESC, month DESC, day DESC
        """, (member_id,))
        trans = c.fetchall()
        conn.close()
        return trans
    except:
        return []

def get_all_members():
    conn = sqlite3.connect('somiti.db')
    c = conn.cursor()
    c.execute("""
        SELECT id, name, phone, email, password, status, monthly_savings, total_savings
        FROM members 
        ORDER BY name
    """)
    members = c.fetchall()
    conn.close()
    return members

def get_member_by_id(member_id):
    conn = sqlite3.connect('somiti.db')
    c = conn.cursor()
    c.execute("SELECT * FROM members WHERE id = ?", (member_id,))
    member = c.fetchone()
    conn.close()
    return member

def get_all_expenses():
    try:
        conn = sqlite3.connect('somiti.db')
        c = conn.cursor()
        c.execute("SELECT id, date, description, amount, category FROM expenses ORDER BY id DESC")
        expenses = c.fetchall()
        conn.close()
        return expenses
    except:
        return []

def get_all_withdrawals():
    try:
        conn = sqlite3.connect('somiti.db')
        c = conn.cursor()
        c.execute("SELECT id, date, amount, description, withdrawn_by, previous_balance, current_balance FROM withdrawals ORDER BY id DESC")
        withdrawals = c.fetchall()
        conn.close()
        return withdrawals
    except:
        return []

def get_monthly_report():
    try:
        conn = sqlite3.connect('somiti.db')
        c = conn.cursor()
        c.execute("""
            SELECT month_name || ' ' || year as month_year, SUM(amount) as total
            FROM transactions
            GROUP BY year, month
            ORDER BY year DESC, month DESC
            LIMIT 12
        """)
        data = c.fetchall()
        conn.close()
        return data
    except:
        return []

def pick_lottery_winner():
    conn = sqlite3.connect('somiti.db')
    c = conn.cursor()
    c.execute("""
        SELECT id, name, phone, total_savings, email 
        FROM members 
        WHERE status = 'active'
        ORDER BY RANDOM() 
        LIMIT 1
    """)
    winner = c.fetchone()
    conn.close()
    return winner

def get_app_url():
    return "https://oiorganization2024.streamlit.app"

def get_current_month_collection():
    try:
        current = datetime.now()
        conn = sqlite3.connect('somiti.db')
        c = conn.cursor()
        c.execute("SELECT SUM(amount) FROM transactions WHERE month = ? AND year = ?", 
                 (current.month, current.year))
        total = c.fetchone()[0] or 0
        conn.close()
        return total
    except:
        return 0

# ============================================
# UI স্টাইল (ডার্ক থিম)
# ============================================
def apply_dark_theme():
    st.markdown("""
    <style>
    .stApp { background: linear-gradient(135deg, #0d1117 0%, #161b22 100%); }
    .somiti-header { background: linear-gradient(135deg, #1a5276 0%, #2980b9 100%); padding: 20px; border-radius: 15px; margin-bottom: 20px; text-align: center; }
    .somiti-header h1 { color: white; font-size: 32px; font-weight: 800; margin: 0; }
    .total-box { background: linear-gradient(135deg, #1e8449 0%, #27ae60 100%); padding: 15px; border-radius: 15px; text-align: center; margin-bottom: 20px; }
    .total-box h2 { color: white; font-size: 28px; font-weight: 800; margin: 0; }
    .cash-box { background: linear-gradient(135deg, #d35400 0%, #e67e22 100%); padding: 15px; border-radius: 15px; text-align: center; margin-bottom: 20px; }
    .cash-box h2 { color: white; font-size: 28px; font-weight: 800; margin: 0; }
    .member-card { background: #21262d; padding: 15px; border-radius: 10px; margin-bottom: 10px; border: 1px solid #30363d; }
    .stButton > button { background: linear-gradient(135deg, #238636 0%, #2ea043 100%); color: white; font-weight: 600; border: none; border-radius: 8px; padding: 8px 16px; width: 100%; }
    section[data-testid="stSidebar"] { background: linear-gradient(180deg, #0d1117 0%, #161b22 100%); border-right: 1px solid #30363d; }
    section[data-testid="stSidebar"] * { color: #c9d1d9 !important; }
    p, h1, h2, h3, h4, h5, h6, .stMarkdown { color: #c9d1d9 !important; }
    .stDataFrame { border-radius: 10px; overflow: hidden; border: 1px solid #30363d; }
    .stDataFrame th { background: #21262d !important; color: #c9d1d9 !important; }
    .stDataFrame td { background: #161b22 !important; color: #c9d1d9 !important; }
    </style>
    """, unsafe_allow_html=True)

def show_header():
    total = get_total_savings()
    st.markdown(f"""
    <div class="somiti-header"><h1>🌾 {SOMITI_NAME} 🌾</h1><p>সঞ্চয় ও ঋণ ব্যবস্থাপনা সিস্টেম</p></div>
    <div class="total-box"><h2>💰 {total:,.0f} টাকা</h2><p>সমিতির মোট জমা</p></div>
    """, unsafe_allow_html=True)

def show_admin_header():
    total = get_total_savings()
    cash = get_cash_balance()
    st.markdown(f'<div class="somiti-header"><h1>🌾 {SOMITI_NAME} 🌾</h1><p>সঞ্চয় ও ঋণ ব্যবস্থাপনা সিস্টেম</p></div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1: st.markdown(f'<div class="total-box"><h2>💰 {total:,.0f} টাকা</h2><p>সমিতির মোট জমা</p></div>', unsafe_allow_html=True)
    with col2: st.markdown(f'<div class="cash-box"><h2>💵 {cash:,.0f} টাকা</h2><p>ক্যাশ ব্যালেন্স</p></div>', unsafe_allow_html=True)

# ============================================
# পিডিএফ জেনারেটর
# ============================================
def generate_pdf_member_list():
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], alignment=1, fontSize=18, textColor=colors.HexColor('#1a5276'))
    elements.append(Paragraph(f"{SOMITI_NAME} - সদস্য তালিকা", title_style))
    elements.append(Spacer(1, 20))
    elements.append(Paragraph(f"তারিখ: {datetime.now().strftime('%d %B %Y')}", styles['Normal']))
    elements.append(Spacer(1, 20))
    
    members = get_all_members()
    data = [['আইডি', 'নাম', 'মোবাইল', 'মাসিক কিস্তি', 'মোট জমা']]
    for m in members:
        data.append([m[0], m[1], m[2], f"{m[6]:,.0f} টাকা", f"{m[7]:,.0f} টাকা"])
    
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a5276')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f5f5f5')),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elements.append(table)
    
    doc.build(elements)
    buffer.seek(0)
    return buffer

def generate_pdf_transactions(member_id=None):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()
    
    title = f"{SOMITI_NAME} - লেনদেন রিপোর্ট"
    if member_id:
        member = get_member_by_id(member_id)
        if member:
            title = f"{SOMITI_NAME} - {member[1]} ({member_id}) এর লেনদেন"
    
    elements.append(Paragraph(title, styles['Heading1']))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(f"তারিখ: {datetime.now().strftime('%d %B %Y')}", styles['Normal']))
    elements.append(Spacer(1, 20))
    
    if member_id:
        trans = get_member_transactions(member_id)
    else:
        conn = sqlite3.connect('somiti.db')
        c = conn.cursor()
        c.execute("""
            SELECT t.full_date, m.name, t.amount, t.month_name, t.year 
            FROM transactions t
            JOIN members m ON t.member_id = m.id
            ORDER BY t.year DESC, t.month DESC, t.day DESC LIMIT 100
        """)
        trans = c.fetchall()
        conn.close()
    
    if trans:
        if member_id:
            data = [['তারিখ', 'পরিমাণ', 'মাস', 'সাল']]
            for t in trans:
                data.append([t[1], f"{t[2]:,.0f} টাকা", t[3], str(t[4])])
        else:
            data = [['তারিখ', 'সদস্য', 'পরিমাণ', 'মাস', 'সাল']]
            for t in trans:
                data.append([t[0], t[1], f"{t[2]:,.0f} টাকা", t[3], str(t[4])])
        
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a5276')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        elements.append(table)
    
    doc.build(elements)
    buffer.seek(0)
    return buffer

# ============================================
# মেম্বার লগইন পেজ
# ============================================
def member_login_page(member_id):
    apply_dark_theme()
    
    st.markdown(f"""
    <div class="somiti-header">
        <h1>🌾 {SOMITI_NAME} 🌾</h1>
        <p>সদস্য লগইন</p>
    </div>
    """, unsafe_allow_html=True)
    
    member = get_member_by_id(member_id)
    if not member:
        st.error("❌ সদস্য পাওয়া যায়নি")
        return
    
    with st.container():
        st.markdown(f"### 🔐 স্বাগতম, {member[1]}")
        st.info(f"🆔 সদস্য আইডি: {member_id}")
        
        email = st.text_input("📧 ইমেইল অ্যাড্রেস", placeholder="আপনার ইমেইল")
        password = st.text_input("🔑 পাসওয়ার্ড", type="password")
        
        if st.button("প্রবেশ করুন", use_container_width=True, type="primary"):
            if email == member[3] and password == member[4]:
                st.session_state.member_logged_in = True
                st.session_state.member_id = member_id
                st.session_state.member_name = member[1]
                st.rerun()
            else:
                st.error("❌ ভুল ইমেইল বা পাসওয়ার্ড")
        
        st.markdown("---")
        st.caption(f"সাহায্য: {ADMIN_MOBILE}")

def member_dashboard_view():
    apply_dark_theme()
    show_header()
    
    member = get_member_by_id(st.session_state.member_id)
    if not member:
        st.error("সদস্য পাওয়া যায়নি")
        return
    
    member_id, name, phone, email, password, total_savings, monthly_savings, join_date, status = member
    monthly = monthly_savings or 500
    
    with st.sidebar:
        st.markdown(f"### 👤 {name}")
        st.caption(f"🆔 {member_id}")
        st.caption(f"📱 {phone}")
        st.metric("💰 মোট জমা", f"{total_savings:,.0f} টাকা")
        st.metric("📅 মাসিক কিস্তি", f"{monthly:,.0f} টাকা")
        
        if st.button("🚪 লগআউট", use_container_width=True):
            for k in ['member_logged_in', 'member_id', 'member_name']:
                if k in st.session_state:
                    del st.session_state[k]
            st.rerun()
    
    st.markdown(f"### স্বাগতম, {name}! 👋")
    
    col1, col2 = st.columns(2)
    col1.metric("💰 বর্তমান জমা", f"{total_savings:,.0f} টাকা")
    col2.metric("📅 মাসিক কিস্তি", f"{monthly:,.0f} টাকা")
    
    current = datetime.now()
    conn = sqlite3.connect('somiti.db')
    c = conn.cursor()
    c.execute("SELECT SUM(amount) FROM transactions WHERE member_id = ? AND month = ? AND year = ?", 
             (member_id, current.month, current.year))
    paid = c.fetchone()[0] or 0
    conn.close()
    
    if paid >= monthly:
        st.success(f"✅ {BANGLA_MONTHS[current.month]} {current.year} মাসের কিস্তি পরিশোধ করেছেন")
    else:
        st.warning(f"⚠️ বকেয়া: {monthly - paid:,.0f} টাকা")
    
    st.markdown("---")
    st.markdown("#### 📋 লেনদেন ইতিহাস")
    
    trans = get_member_transactions(member_id)
    if trans:
        df = pd.DataFrame([{"তারিখ": t[1], "টাকা": f"{t[2]:,.0f}", "মাস": t[3], "সাল": t[4]} for t in trans])
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        if st.button("📥 পিডিএফ ডাউনলোড", type="primary"):
            pdf = generate_pdf_transactions(member_id)
            st.download_button("📥 ডাউনলোড", pdf, f"{member_id}_transactions.pdf", mime="application/pdf")
    else:
        st.info("কোনো লেনদেন নেই")

# ============================================
# এডমিন লগইন পেজ
# ============================================
def admin_login_page():
    apply_dark_theme()
    show_header()
    
    with st.container():
        st.markdown("### 🔐 এডমিন লগইন")
        phone = st.text_input("📱 মোবাইল নম্বর", placeholder="017XXXXXXXX")
        password = st.text_input("🔑 পাসওয়ার্ড", type="password")
        
        if st.button("প্রবেশ করুন", use_container_width=True, type="primary"):
            if phone == ADMIN_MOBILE and password == ADMIN_PASSWORD:
                st.session_state.admin_logged_in = True
                st.success("✅ এডমিন লগইন সফল!")
                st.rerun()
            else:
                st.error("❌ ভুল মোবাইল বা পাসওয়ার্ড")

# ============================================
# এডমিন প্যানেল
# ============================================
def admin_panel():
    apply_dark_theme()
    show_admin_header()
    
    with st.sidebar:
        st.markdown("### 📋 এডমিন মেনু")
        st.caption(f"👑 {ADMIN_MOBILE}")
        
        menu = st.radio("নির্বাচন করুন",
            ["🏠 ড্যাশবোর্ড", "➕ নতুন সদস্য", "✏️ সদস্য ব্যবস্থাপনা", "💵 টাকা জমা",
             "💰 লেনদেন ব্যবস্থাপনা", "🔗 সদস্য লিংক", "💸 খরচ ব্যবস্থাপনা",
             "🏧 টাকা উত্তোলন", "📊 রিপোর্ট", "📥 পিডিএফ ডাউনলোড",
             "📧 ইমেইল টেস্ট", "🎲 লটারি", "🚪 লগআউট"], label_visibility="collapsed")
    
    if menu == "🚪 লগআউট":
        if 'admin_logged_in' in st.session_state:
            del st.session_state.admin_logged_in
        st.rerun()
    
    elif menu == "🏠 ড্যাশবোর্ড":
        st.markdown("### 🏠 এডমিন ড্যাশবোর্ড")
        
        col1, col2, col3, col4 = st.columns(4)
        try:
            conn = sqlite3.connect('somiti.db')
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM members WHERE status = 'active'")
            col1.metric("👥 সদস্য", c.fetchone()[0])
            conn.close()
            col2.metric("💰 জমা", f"{get_total_savings():,.0f} টাকা")
            col3.metric("📅 এই মাস", f"{get_current_month_collection():,.0f} টাকা")
            col4.metric("⚠️ বকেয়া", f"{len(get_unpaid_members())} জন")
        except: pass
    
    elif menu == "➕ নতুন সদস্য":
        st.markdown("### ➕ নতুন সদস্য নিবন্ধন")
        
        name = st.text_input("নাম *")
        phone = st.text_input("মোবাইল নম্বর *", placeholder="017XXXXXXXX")
        email = st.text_input("ইমেইল অ্যাড্রেস (নোটিফিকেশনের জন্য)")
        monthly = st.number_input("মাসিক কিস্তি (টাকা)", value=500, step=50)
        
        if st.button("✅ সদস্য যোগ করুন", type="primary", use_container_width=True):
            if not name or not phone:
                st.error("❌ নাম ও মোবাইল আবশ্যক")
            else:
                try:
                    member_id = generate_member_id()
                    password = generate_password()
                    join_date = datetime.now().strftime("%Y-%m-%d")
                    
                    conn = sqlite3.connect('somiti.db')
                    c = conn.cursor()
                    c.execute("INSERT INTO members (id, name, phone, email, password, monthly_savings, join_date) VALUES (?, ?, ?, ?, ?, ?, ?)",
                             (member_id, name, phone, email, password, monthly, join_date))
                    conn.commit()
                    conn.close()
                    
                    if email:
                        msg = get_welcome_email(name, member_id, phone, password, monthly)
                        send_email(email, f"🎉 স্বাগতম - {SOMITI_NAME}", msg)
                    
                    st.success(f"✅ সদস্য তৈরি!")
                    st.info(f"আইডি: {member_id} | পাস: {password}")
                    st.balloons()
                except sqlite3.IntegrityError:
                    st.error("❌ এই মোবাইল ইতিমধ্যে নিবন্ধিত")
    
    elif menu == "✏️ সদস্য ব্যবস্থাপনা":
        st.markdown("### ✏️ সদস্য ব্যবস্থাপনা")
        members = get_all_members()
        
        if members:
            for m in members:
                member_id, name, phone, email, password, status, monthly, savings = m
                monthly = float(monthly) if monthly else 500.0
                savings = float(savings) if savings else 0.0
                
                with st.expander(f"👤 {name} - {member_id} | {'✅ সক্রিয়' if status == 'active' else '❌ নিষ্ক্রিয়'}"):
                    st.write(f"📱 {phone} | 📧 {email or 'N/A'} | 💰 জমা: {savings:,.0f} টাকা | 📅 কিস্তি: {monthly:,.0f} টাকা")
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        if st.button("📝 এডিট", key=f"e_{member_id}"):
                            st.session_state[f"edit_{member_id}"] = True
                    with col2:
                        if st.button("🔐 পাসওয়ার্ড", key=f"p_{member_id}"):
                            st.session_state[f"pass_{member_id}"] = True
                    with col3:
                        new_status = 'inactive' if status == 'active' else 'active'
                        if st.button(f"🔄 {'নিষ্ক্রিয়' if status == 'active' else 'সক্রিয়'}", key=f"s_{member_id}"):
                            conn = sqlite3.connect('somiti.db')
                            c = conn.cursor()
                            c.execute("UPDATE members SET status=? WHERE id=?", (new_status, member_id))
                            conn.commit()
                            conn.close()
                            st.rerun()
                    
                    if st.session_state.get(f"edit_{member_id}"):
                        with st.form(f"edit_form_{member_id}"):
                            new_name = st.text_input("নাম", value=name)
                            new_email = st.text_input("ইমেইল", value=email or "")
                            new_mon = st.number_input("কিস্তি", value=monthly, step=50.0)
                            if st.form_submit_button("💾 সেভ", type="primary"):
                                conn = sqlite3.connect('somiti.db')
                                c = conn.cursor()
                                c.execute("UPDATE members SET name=?, email=?, monthly_savings=? WHERE id=?",
                                         (new_name, new_email, new_mon, member_id))
                                conn.commit()
                                conn.close()
                                st.success("✅ আপডেট!")
                                del st.session_state[f"edit_{member_id}"]
                                st.rerun()
                    
                    if st.session_state.get(f"pass_{member_id}"):
                        if st.button("✅ নতুন পাসওয়ার্ড", key=f"gen_{member_id}", type="primary"):
                            new_pass = generate_password()
                            conn = sqlite3.connect('somiti.db')
                            c = conn.cursor()
                            c.execute("UPDATE members SET password=? WHERE id=?", (new_pass, member_id))
                            conn.commit()
                            conn.close()
                            if email:
                                msg = get_password_reset_email(name, new_pass)
                                send_email(email, f"🔐 পাসওয়ার্ড রিসেট - {SOMITI_NAME}", msg)
                            st.success(f"✅ নতুন পাস: {new_pass}")
                            del st.session_state[f"pass_{member_id}"]
                            st.rerun()
        else:
            st.info("কোনো সদস্য নেই")
    
    elif menu == "💵 টাকা জমা":
        st.markdown("### 💵 সদস্যের টাকা জমা")
        paid, unpaid = get_paid_members(), get_unpaid_members()
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### ✅ জমা দিয়েছে")
            for m in paid:
                st.markdown(f'<div class="member-card"><strong>{m[1]}</strong> ({m[0]})<br><small>💰 {m[4]:,.0f} টাকা</small></div>', unsafe_allow_html=True)
            if not paid:
                st.info("কেউ জমা দেয়নি")
        
        with col2:
            st.markdown("#### ❌ জমা দেয়নি")
            for m in unpaid:
                with st.expander(f"❌ {m[1]} ({m[0]})"):
                    st.write(f"📱 {m[2]} | 💰 জমা: {m[4]:,.0f} টাকা | 📅 কিস্তি: {m[3]:,.0f} টাকা")
                    
                    current = datetime.now()
                    day = st.number_input("দিন", 1, 31, current.day, key=f"day_{m[0]}")
                    month = st.selectbox("মাস", list(BANGLA_MONTHS.keys()), 
                                        format_func=lambda x: BANGLA_MONTHS[x], 
                                        index=current.month-1, key=f"month_{m[0]}")
                    year = st.number_input("সাল", 2020, 2050, current.year, key=f"year_{m[0]}")
                    
                    c1, c2 = st.columns(2)
                    with c1:
                        months_count = st.number_input("কত মাস", 1, 1, 12, key=f"count_{m[0]}")
                    with c2:
                        late_fee = st.number_input("লেট ফি", 0.0, step=10.0, key=f"fee_{m[0]}")
                    
                    total = m[3] * months_count + late_fee
                    
                    if st.button("✅ জমা নিন", key=f"dep_{m[0]}", type="primary"):
                        today_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        full_date = f"{day} {BANGLA_MONTHS[month]} {year}"
                        date_iso = f"{year}-{month:02d}-{day:02d}"
                        
                        conn = sqlite3.connect('somiti.db')
                        c = conn.cursor()
                        
                        for i in range(months_count):
                            c.execute("""
                                INSERT INTO transactions 
                                (member_id, amount, transaction_type, day, month, year, month_name, full_date, date_iso, late_fee, created_at)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, (m[0], m[3], 'deposit', day, month, year, BANGLA_MONTHS[month], 
                                  full_date, date_iso, late_fee if i == 0 else 0, today_str))
                        
                        c.execute("UPDATE members SET total_savings = total_savings + ? WHERE id = ?", (total, m[0]))
                        c.execute("SELECT total_savings FROM members WHERE id = ?", (m[0],))
                        new_total = c.fetchone()[0]
                        conn.commit()
                        conn.close()
                        
                        if m[5]:
                            msg = get_payment_success_email(m[1], f"{total:,.0f}", full_date, BANGLA_MONTHS[month], f"{new_total:,.0f}")
                            send_email(m[5], f"✅ পেমেন্ট সফল - {SOMITI_NAME}", msg)
                        
                        st.success(f"✅ {total:,.0f} টাকা জমা!")
                        st.rerun()
            if not unpaid:
                st.success("🎉 সবাই জমা দিয়েছেন!")
    
    elif menu == "💰 লেনদেন ব্যবস্থাপনা":
        st.markdown("### 💰 লেনদেন ব্যবস্থাপনা")
        
        members = get_all_members()
        if members:
            options = {f"{m[1]} ({m[0]})": m[0] for m in members}
            selected = st.selectbox("সদস্য নির্বাচন", list(options.keys()))
            
            if selected:
                member_id = options[selected]
                member = get_member_by_id(member_id)
                
                if member:
                    st.success(f"👤 {member[1]} | 💰 {member[7]:,.0f} টাকা")
                    trans = get_member_transactions(member_id)
                    
                    if trans:
                        for t in trans:
                            trans_id, full_date, amount, month_name, year, late_fee, note, day, month, date_iso = t
                            
                            c1, c2, c3, c4, c5, c6 = st.columns([2, 1.5, 1.5, 1, 1, 1])
                            c1.write(full_date)
                            c2.write(f"{amount:,.0f} টাকা")
                            c3.write(f"{month_name} {year}")
                            
                            if c4.button("✏️", key=f"edit_{trans_id}"):
                                st.session_state[f"edit_trans_{trans_id}"] = True
                            
                            if c5.button("🗑️", key=f"del_{trans_id}"):
                                conn = sqlite3.connect('somiti.db')
                                c = conn.cursor()
                                c.execute("UPDATE members SET total_savings = total_savings - ? WHERE id = ?", (amount, member_id))
                                c.execute("DELETE FROM transactions WHERE id = ?", (trans_id,))
                                c.execute("SELECT total_savings FROM members WHERE id = ?", (member_id,))
                                new_total = c.fetchone()[0]
                                conn.commit()
                                conn.close()
                                
                                if member[3]:
                                    msg = get_transaction_remove_email(member[1], f"{amount:,.0f}", full_date, f"{new_total:,.0f}")
                                    send_email(member[3], f"🗑️ লেনদেন বাতিল - {SOMITI_NAME}", msg)
                                
                                st.success("✅ রিমুভ!")
                                st.rerun()
                            
                            if st.session_state.get(f"edit_trans_{trans_id}"):
                                with st.form(f"edit_{trans_id}"):
                                    new_amt = st.number_input("টাকা", value=float(amount), step=50.0)
                                    if st.form_submit_button("💾 সেভ", type="primary"):
                                        conn = sqlite3.connect('somiti.db')
                                        c = conn.cursor()
                                        diff = new_amt - amount
                                        c.execute("UPDATE transactions SET amount = ? WHERE id = ?", (new_amt, trans_id))
                                        c.execute("UPDATE members SET total_savings = total_savings + ? WHERE id = ?", (diff, member_id))
                                        c.execute("SELECT total_savings FROM members WHERE id = ?", (member_id,))
                                        new_total = c.fetchone()[0]
                                        conn.commit()
                                        conn.close()
                                        
                                        if member[3]:
                                            msg = get_transaction_edit_email(member[1], f"{amount:,.0f}", f"{new_amt:,.0f}", full_date, f"{new_total:,.0f}")
                                            send_email(member[3], f"✏️ লেনদেন সংশোধন - {SOMITI_NAME}", msg)
                                        
                                        st.success("✅ আপডেট!")
                                        del st.session_state[f"edit_trans_{trans_id}"]
                                        st.rerun()
                    else:
                        st.info("কোনো লেনদেন নেই")
        else:
            st.info("কোনো সদস্য নেই")
    
    elif menu == "🔗 সদস্য লিংক":
        st.markdown("### 🔗 সদস্য লিংক ও পাসওয়ার্ড")
        members = get_all_members()
        app_url = get_app_url()
        
        for m in members:
            member_id, name, phone, email, password, status = m[:6]
            link = f"{app_url}/?member={member_id}"
            
            st.markdown(f"""
            <div class="member-card">
                <h4>👤 {name} ({member_id})</h4>
                <p>📱 {phone} | 📧 {email or 'N/A'}</p>
                <p>🔗 <code>{link}</code></p>
                <p>🔑 <code>{password}</code></p>
            </div>""", unsafe_allow_html=True)
            
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown(f'<button onclick="navigator.clipboard.writeText(\'{link}\')" style="background:#238636; color:white; border:none; padding:8px; border-radius:5px; width:100%;">📋 লিংক কপি</button>', unsafe_allow_html=True)
            with c2:
                st.markdown(f'<button onclick="navigator.clipboard.writeText(\'{password}\')" style="background:#238636; color:white; border:none; padding:8px; border-radius:5px; width:100%;">📋 পাসওয়ার্ড কপি</button>', unsafe_allow_html=True)
            with c3:
                if email and st.button("📧 ইমেইল", key=f"mail_{member_id}"):
                    msg = f"""প্রিয় {name},

আপনার লগইন তথ্য:
🔗 লিংক: {link}
📱 মোবাইল: {phone}
🔑 পাসওয়ার্ড: {password}"""
                    send_email(email, f"🔐 লগইন তথ্য - {SOMITI_NAME}", msg)
                    st.success("✅ পাঠানো হয়েছে!")
            st.markdown("---")
    
    elif menu == "💸 খরচ ব্যবস্থাপনা":
        st.markdown("### 💸 খরচ ব্যবস্থাপনা")
        tab1, tab2 = st.tabs(["➕ নতুন", "📋 তালিকা"])
        
        with tab1:
            with st.form("exp_form"):
                desc = st.text_input("বিবরণ")
                amt = st.number_input("টাকা", 0.0, step=10.0)
                cat = st.selectbox("ক্যাটাগরি", ["অফিস ভাড়া", "চা-নাস্তা", "স্টেশনারি", "পরিবহন", "অন্যান্য"])
                if st.form_submit_button("💾 সংরক্ষণ", type="primary"):
                    if desc and amt > 0:
                        conn = sqlite3.connect('somiti.db')
                        c = conn.cursor()
                        c.execute("INSERT INTO expenses (description, amount, date, category) VALUES (?,?,?,?)",
                                 (desc, amt, datetime.now().strftime("%Y-%m-%d"), cat))
                        conn.commit()
                        conn.close()
                        st.success(f"✅ {amt:,.0f} টাকা যোগ!")
                        st.rerun()
        
        with tab2:
            expenses = get_all_expenses()
            if expenses:
                for e in expenses[:20]:
                    c1, c2, c3, c4, c5 = st.columns([2, 2, 3, 2, 1])
                    c1.write(e[1])
                    c2.write(e[4])
                    c3.write(e[2])
                    c4.write(f"{e[3]:,.0f} টাকা")
                    if c5.button("🗑️", key=f"de_{e[0]}"):
                        conn = sqlite3.connect('somiti.db')
                        c = conn.cursor()
                        c.execute("DELETE FROM expenses WHERE id=?", (e[0],))
                        conn.commit()
                        conn.close()
                        st.rerun()
                st.metric("মোট খরচ", f"{sum(e[3] for e in expenses):,.0f} টাকা")
    
    elif menu == "🏧 টাকা উত্তোলন":
        st.markdown("### 🏧 সমিতির টাকা উত্তোলন")
        
        cash = get_cash_balance()
        st.info(f"💰 বর্তমান ক্যাশ ব্যালেন্স: {cash:,.0f} টাকা")
        
        with st.form("withdraw_form"):
            amount = st.number_input("উত্তোলনের পরিমাণ", 0.0, step=100.0)
            description = st.text_area("বিবরণ (কেন উত্তোলন করা হচ্ছে)")
            date = st.date_input("উত্তোলনের তারিখ", datetime.now())
            
            if st.form_submit_button("✅ উত্তোলন করুন", type="primary"):
                if amount > 0 and amount <= cash:
                    if description:
                        conn = sqlite3.connect('somiti.db')
                        c = conn.cursor()
                        c.execute("""
                            INSERT INTO withdrawals (date, amount, description, withdrawn_by, previous_balance, current_balance, created_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (date.strftime("%Y-%m-%d"), amount, description, "এডমিন", cash, cash - amount, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                        conn.commit()
                        conn.close()
                        
                        # সকল সদস্যকে ইমেইল
                        subject = f"🏧 টাকা উত্তোলনের নোটিশ - {SOMITI_NAME}"
                        msg_template = f"""প্রিয় {{name}},

═══════════════════════════════════════════════════════════════════
                  🏧 টাকা উত্তোলনের নোটিশ - {SOMITI_NAME}
═══════════════════════════════════════════════════════════════════

সমিতির তহবিল থেকে টাকা উত্তোলন করা হয়েছে।

┌─────────────────────────────────────────────────────────────────┐
│                    🏧 উত্তোলনের বিবরণ                             │
├─────────────────────────────────────────────────────────────────┤
│   📅 উত্তোলনের তারিখ     : {date.strftime('%d %B %Y')}           │
│   💰 উত্তোলনের পরিমাণ    : {amount:,.0f} টাকা                    │
│   📝 বিবরণ             : {description}                          │
│   ───────────────────────────────────────────────────────────── │
│   💵 পূর্বের ব্যালেন্স    : {cash:,.0f} টাকা                      │
│   💵 বর্তমান ব্যালেন্স    : {cash - amount:,.0f} টাকা             │
└─────────────────────────────────────────────────────────────────┘

ℹ️ এটি শুধুমাত্র আপনার অবগতির জন্য পাঠানো হলো।

💚 "স্বচ্ছতা আমাদের অঙ্গীকার"

{SOMITI_NAME} কর্তৃপক্ষ"""
                        
                        sent = send_email_to_all_active_members(subject, msg_template)
                        st.success(f"✅ {amount:,.0f} টাকা উত্তোলন সম্পন্ন! {sent} জন সদস্যকে ইমেইল পাঠানো হয়েছে।")
                        st.rerun()
                    else:
                        st.error("❌ বিবরণ দিতে হবে")
                else:
                    st.error("❌ সঠিক পরিমাণ দিন")
        
        st.markdown("---")
        st.markdown("#### 📋 উত্তোলন ইতিহাস")
        withdrawals = get_all_withdrawals()
        if withdrawals:
            df = pd.DataFrame(withdrawals, columns=["ID", "তারিখ", "পরিমাণ", "বিবরণ", "উত্তোলনকারী", "পূর্বের ব্যালেন্স", "বর্তমান ব্যালেন্স"])
            st.dataframe(df[["তারিখ", "পরিমাণ", "বিবরণ", "পূর্বের ব্যালেন্স", "বর্তমান ব্যালেন্স"]], use_container_width=True, hide_index=True)
    
    elif menu == "📊 রিপোর্ট":
        st.markdown("### 📊 রিপোর্ট")
        tab1, tab2, tab3 = st.tabs(["📈 মাসিক", "⚠️ বকেয়া", "🏧 উত্তোলন"])
        
        with tab1:
            data = get_monthly_report()
            if data:
                df = pd.DataFrame(data, columns=["মাস", "জমা"])
                st.bar_chart(df.set_index("মাস"))
                st.dataframe(df, use_container_width=True, hide_index=True)
        
        with tab2:
            unpaid = get_unpaid_members()
            if unpaid:
                df = pd.DataFrame([{"নাম": m[1], "মোবাইল": m[2], "কিস্তি": f"{m[3]:,.0f}", "জমা": f"{m[4]:,.0f}"} for m in unpaid])
                st.dataframe(df, use_container_width=True, hide_index=True)
                if st.button("📧 বকেয়া রিমাইন্ডার", type="primary"):
                    sent = 0
                    for m in unpaid:
                        if m[5]:
                            msg = f"""প্রিয় {m[1]},

{BANGLA_MONTHS[datetime.now().month]} মাসের কিস্তি ({m[3]:,.0f} টাকা) বকেয়া আছে।
🙏 আজই পরিশোধ করুন।"""
                            if send_email(m[5], f"⚠️ বকেয়া রিমাইন্ডার - {SOMITI_NAME}", msg):
                                sent += 1
                    st.success(f"✅ {sent} জনকে পাঠানো হয়েছে!")
        
        with tab3:
            withdrawals = get_all_withdrawals()
            if withdrawals:
                df = pd.DataFrame(withdrawals, columns=["ID", "তারিখ", "পরিমাণ", "বিবরণ", "উত্তোলনকারী", "পূর্বের ব্যালেন্স", "বর্তমান ব্যালেন্স"])
                st.dataframe(df[["তারিখ", "পরিমাণ", "বিবরণ"]], use_container_width=True, hide_index=True)
                st.metric("মোট উত্তোলন", f"{sum(w[2] for w in withdrawals):,.0f} টাকা")
    
    elif menu == "📥 পিডিএফ ডাউনলোড":
        st.markdown("### 📥 পিডিএফ ডাউনলোড সেন্টার")
        
        report_type = st.selectbox("রিপোর্ট সিলেক্ট করুন", 
            ["সদস্য তালিকা", "সম্পূর্ণ লেনদেন", "নির্দিষ্ট সদস্যের লেনদেন"])
        
        if report_type == "নির্দিষ্ট সদস্যের লেনদেন":
            members = get_all_members()
            if members:
                options = {f"{m[1]} ({m[0]})": m[0] for m in members}
                selected = st.selectbox("সদস্য নির্বাচন", list(options.keys()))
                member_id = options[selected]
                
                if st.button("📥 পিডিএফ ডাউনলোড", type="primary"):
                    pdf = generate_pdf_transactions(member_id)
                    st.download_button("📥 ডাউনলোড", pdf, f"{member_id}_transactions.pdf", mime="application/pdf")
        else:
            if st.button("📥 পিডিএফ ডাউনলোড", type="primary"):
                if report_type == "সদস্য তালিকা":
                    pdf = generate_pdf_member_list()
                    st.download_button("📥 ডাউনলোড", pdf, "member_list.pdf", mime="application/pdf")
                else:
                    pdf = generate_pdf_transactions()
                    st.download_button("📥 ডাউনলোড", pdf, "all_transactions.pdf", mime="application/pdf")
    
    elif menu == "📧 ইমেইল টেস্ট":
        st.markdown("### 📧 ইমেইল টেস্ট")
        test_email = st.text_input("টেস্ট ইমেইল", placeholder="example@gmail.com")
        if st.button("📨 টেস্ট পাঠান", type="primary"):
            if send_email(test_email, f"🧪 টেস্ট - {SOMITI_NAME}", "আপনার ইমেইল নোটিফিকেশন কাজ করছে!"):
                st.success("✅ পাঠানো হয়েছে!")
            else:
                st.error("❌ পাঠানো যায়নি")
    
    elif menu == "🎲 লটারি":
        st.markdown("### 🎲 লটারি")
        if st.button("🎲 বিজয়ী নির্বাচন", type="primary"):
            w = pick_lottery_winner()
            if w:
                st.balloons()
                st.success(f"🎉 বিজয়ী: {w[1]} ({w[0]})")
                if w[4]:
                    msg = get_lottery_winner_email(w[1])
                    send_email(w[4], f"🎉 লটারি বিজয়ী - {SOMITI_NAME}", msg)

# ============================================
# মেইন
# ============================================
def main():
    init_database()
    check_and_archive_old_data()
    
    # সেশন ইনিশিয়ালাইজ
    if 'member_logged_in' not in st.session_state:
        st.session_state.member_logged_in = False
    if 'admin_logged_in' not in st.session_state:
        st.session_state.admin_logged_in = False
    
    # মেম্বার লিংক চেক
    if member_login_id:
        if not st.session_state.member_logged_in:
            member_login_page(member_login_id)
        else:
            member_dashboard_view()
        return
    
    # এডমিন চেক
    if not st.session_state.admin_logged_in:
        admin_login_page()
    else:
        admin_panel()

if __name__ == "__main__":
    main()
