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
import time
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

# ==================== কনফিগারেশন ====================
ADMIN_MOBILE = "01766222373"
ADMIN_PASSWORD = "oio112024"
SOMITI_NAME = "ঐক্য উদ্যোগ সংস্থা"
SOMITI_NAME_EN = "Oikko Uddog Songstha"
SOMITI_START_DATE = "2026-04-12"

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465
SENDER_EMAIL = "oiorganization2024@gmail.com"
SENDER_PASSWORD = "hnhm ocix kyxv ioiz"

st.set_page_config(page_title=SOMITI_NAME, page_icon="🌾", layout="wide")

# URL প্যারামিটার থেকে মেম্বার আইডি
try:
    query_params = st.query_params
    member_login_id = query_params.get("member") if query_params else None
except:
    member_login_id = None

if 'language' not in st.session_state:
    st.session_state.language = 'bn'

def t(bn_text, en_text):
    return bn_text if st.session_state.language == 'bn' else en_text

BANGLA_MONTHS = {
    1: "জানুয়ারি", 2: "ফেব্রুয়ারি", 3: "মার্চ", 4: "এপ্রিল",
    5: "মে", 6: "জুন", 7: "জুলাই", 8: "আগস্ট",
    9: "সেপ্টেম্বর", 10: "অক্টোবর", 11: "নভেম্বর", 12: "ডিসেম্বর"
}

ENGLISH_MONTHS = {
    1: "January", 2: "February", 3: "March", 4: "April",
    5: "May", 6: "June", 7: "July", 8: "August",
    9: "September", 10: "October", 11: "November", 12: "December"
}

# ==================== ডাটাবেজ সেটআপ (নিখুঁত) ====================
def init_database():
    conn = sqlite3.connect('somiti.db')
    c = conn.cursor()
    
    # settings
    c.execute('''CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)''')
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('start_date', ?)", (SOMITI_START_DATE,))
    
    # members
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
    try:
        c.execute("ALTER TABLE members ADD COLUMN email TEXT")
    except:
        pass
    
    # transactions (note কলাম বাদ, 13 columns + id)
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
            month_name_en TEXT NOT NULL,
            full_date TEXT NOT NULL,
            full_date_en TEXT NOT NULL,
            date_iso TEXT NOT NULL,
            late_fee REAL DEFAULT 0,
            created_at TEXT NOT NULL
        )
    ''')
    # পুরনো note কলাম থাকলে ডিল করার চেষ্টা
    try:
        c.execute("ALTER TABLE transactions DROP COLUMN note")
    except:
        pass
    
    # expenses
    c.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT NOT NULL,
            amount REAL NOT NULL,
            date TEXT NOT NULL,
            category TEXT
        )
    ''')
    
    # withdrawals
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
    
    # fund_transactions
    c.execute('''
        CREATE TABLE IF NOT EXISTS fund_transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,
            amount REAL NOT NULL,
            description TEXT,
            date TEXT NOT NULL,
            previous_balance REAL,
            current_balance REAL,
            created_at TEXT NOT NULL
        )
    ''')
    
    conn.commit()
    conn.close()

def check_and_archive_old_data():
    try:
        conn = sqlite3.connect('somiti.db')
        c = conn.cursor()
        c.execute("SELECT value FROM settings WHERE key = 'start_date'")
        result = c.fetchone()
        conn.close()
        if result and result[0]:
            start_date = datetime.strptime(result[0], "%Y-%m-%d")
            years_passed = (datetime.now() - start_date).days / 365
            if years_passed >= 20:
                archive_file = f"somiti_archive_{start_date.year}_{datetime.now().year}.db"
                if not os.path.exists(archive_file):
                    shutil.copy('somiti.db', archive_file)
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
    except:
        pass

# ==================== ইমেইল ফাংশন (SSL) ====================
def send_email(to_email, subject, message):
    if not to_email or '@' not in str(to_email):
        return False
    try:
        msg = MIMEMultipart()
        msg['From'] = f"{SOMITI_NAME} <{SENDER_EMAIL}>"
        msg['To'] = to_email
        msg['Subject'] = subject
        
        html = f"""
        <html>
        <head><meta charset="UTF-8"></head>
        <body style="font-family: Arial, sans-serif; background: #f9f9f9; padding: 20px;">
            <div style="max-width: 600px; margin: auto; background: #fff; border: 1px solid #ddd; padding: 20px; border-radius: 10px;">
                <h2 style="color: #1a5276; text-align: center;">🌾 {SOMITI_NAME}</h2>
                <div style="font-size: 16px; line-height: 1.6; color: #333;">
                    {message.replace(chr(10), '<br>')}
                </div>
                <hr style="border: 0; border-top: 1px solid #eee; margin: 20px 0;">
                <p style="font-size: 12px; color: #888; text-align: center;">{t('যোগাযোগ', 'Contact')}: {ADMIN_MOBILE}</p>
            </div>
        </body>
        </html>
        """
        msg.attach(MIMEText(html, 'html', 'utf-8'))
        
        server = smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15)
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Email Error: {e}")
        return False

# ==================== ইমেইল টেমপ্লেট ====================
def get_welcome_email(name, member_id, phone, password, monthly):
    app_url = get_app_url()
    link = f"{app_url}/?member={member_id}"
    return f"""{t('প্রিয়', 'Dear')} {name},

🎉 {t('স্বাগতম', 'Welcome')} - {SOMITI_NAME}

{t('আপনার তথ্য', 'Your info')}:
🆔 {t('আইডি', 'ID')}: {member_id}
📱 {t('মোবাইল', 'Mobile')}: {phone}
🔑 {t('পাসওয়ার্ড', 'Password')}: {password}
💰 {t('মাসিক কিস্তি', 'Monthly')}: {monthly} {t('টাকা', 'Taka')}
🔗 {t('লগইন লিংক', 'Login Link')}: {link}

{t('শুভেচ্ছায়', 'Regards')},
{SOMITI_NAME}"""

def get_payment_success_email(name, amount, full_date, full_date_en, month_name, month_name_en, total_savings):
    display_date = full_date if st.session_state.language == 'bn' else full_date_en
    display_month = month_name if st.session_state.language == 'bn' else month_name_en
    return f"""{t('প্রিয়', 'Dear')} {name},

✅ {t('পেমেন্ট সফল', 'Payment Success')} - {SOMITI_NAME}

{t('তারিখ', 'Date')}: {display_date}
{t('মাস', 'Month')}: {display_month}
{t('পরিমাণ', 'Amount')}: {amount} {t('টাকা', 'Taka')}
{t('মোট জমা', 'Total')}: {total_savings} {t('টাকা', 'Taka')}

{t('ধন্যবাদ', 'Thank you')}!
{SOMITI_NAME}"""

def get_password_reset_email(name, new_password):
    return f"""{t('প্রিয়', 'Dear')} {name},

🔐 {t('পাসওয়ার্ড রিসেট', 'Password Reset')} - {SOMITI_NAME}

{t('আপনার নতুন পাসওয়ার্ড', 'Your new password')}: {new_password}

{SOMITI_NAME}"""

def get_transaction_edit_email(name, old_amount, new_amount, full_date, full_date_en, total_savings):
    display_date = full_date if st.session_state.language == 'bn' else full_date_en
    return f"""{t('প্রিয়', 'Dear')} {name},

✏️ {t('লেনদেন সংশোধন', 'Transaction Edit')} - {SOMITI_NAME}

{t('তারিখ', 'Date')}: {display_date}
{t('পূর্বের পরিমাণ', 'Old Amount')}: {old_amount} {t('টাকা', 'Taka')}
{t('নতুন পরিমাণ', 'New Amount')}: {new_amount} {t('টাকা', 'Taka')}
{t('সর্বমোট জমা', 'Total Savings')}: {total_savings} {t('টাকা', 'Taka')}

{SOMITI_NAME}"""

def get_transaction_remove_email(name, amount, full_date, full_date_en, total_savings):
    display_date = full_date if st.session_state.language == 'bn' else full_date_en
    return f"""{t('প্রিয়', 'Dear')} {name},

🗑️ {t('লেনদেন বাতিল', 'Transaction Cancelled')} - {SOMITI_NAME}

{t('তারিখ', 'Date')}: {display_date}
{t('বাতিলকৃত পরিমাণ', 'Cancelled Amount')}: {amount} {t('টাকা', 'Taka')}
{t('সর্বমোট জমা', 'Total Savings')}: {total_savings} {t('টাকা', 'Taka')}

{SOMITI_NAME}"""

def get_lottery_winner_email(name):
    return f"""{t('প্রিয়', 'Dear')} {name},

🎉 {t('অভিনন্দন', 'Congratulations')}! 🎉
{t('আপনি লাকি ড্র বিজয়ী হয়েছেন', 'You are the lucky draw winner')}!

{SOMITI_NAME}"""

def get_first_reminder_email(name, monthly_amount):
    monthly_amount = float(monthly_amount) if monthly_amount else 500.0
    return f"""{t('প্রিয়', 'Dear')} {name},

📢 {t('মাসিক কিস্তি রিমাইন্ডার', 'Monthly Installment Reminder')} - {SOMITI_NAME}

{t('আগামী ১০ তারিখের মধ্যে আপনার মাসিক কিস্তি', 'Please pay your monthly installment before the 10th')} {monthly_amount:,.0f} {t('টাকা জমা দিন', 'Taka')}.

{t('ধন্যবাদ', 'Thank you')},
{SOMITI_NAME}"""

def get_tenth_reminder_email(name, monthly_amount, due_amount, month_name):
    monthly_amount = float(monthly_amount) if monthly_amount else 500.0
    due_amount = float(due_amount) if due_amount else monthly_amount
    return f"""{t('প্রিয়', 'Dear')} {name},

⚠️ {t('বকেয়া রিমাইন্ডার', 'Due Reminder')} - {SOMITI_NAME}

{t('আপনার', 'Your')} {month_name} {t('মাসের কিস্তি', 'installment')} {monthly_amount:,.0f} {t('টাকা এখনো জমা পড়েনি', 'Taka has not been paid yet')}.
{t('বর্তমানে আপনার বকেয়া', 'Current due')}: {due_amount:,.0f} {t('টাকা', 'Taka')}.

🙏 {t('অনুগ্রহ করে দ্রুত জমা দিন', 'Please pay as soon as possible')}.

{SOMITI_NAME}"""

def get_fund_movement_email(name, amount, description, current_balance, movement_type):
    type_text = t('উত্তোলন', 'Withdrawal') if movement_type == 'withdrawal' else t('জমা', 'Deposit')
    return f"""{t('প্রিয়', 'Dear')} {name},

🏧 {t('ফান্ড মুভমেন্ট নোটিশ', 'Fund Movement Notice')} - {SOMITI_NAME}

{t('সমিতির ফান্ড থেকে', 'From the fund')} {amount} {t('টাকা', 'Taka')} {type_text} {t('করা হয়েছে', 'has been made')}.
{t('কারণ', 'Reason')}: {description}
{t('বর্তমান ক্যাশ ব্যালেন্স', 'Current Cash Balance')}: {current_balance} {t('টাকা', 'Taka')}

{SOMITI_NAME}"""

# ==================== বাল্ক ইমেইল ====================
def send_bulk_email_to_all_active_members(subject, message_template_func, **kwargs):
    try:
        conn = sqlite3.connect('somiti.db')
        c = conn.cursor()
        c.execute("SELECT name, email, monthly_savings FROM members WHERE status = 'active' AND email IS NOT NULL AND email != ''")
        members = c.fetchall()
        conn.close()
        sent = 0
        for name, email, monthly in members:
            monthly = float(monthly) if monthly else 500.0
            message = message_template_func(name=name, monthly_amount=monthly, **kwargs)
            if send_email(email, subject, message):
                sent += 1
        return sent
    except Exception as e:
        print(f"Bulk email error: {e}")
        return 0

def send_bulk_email_to_unpaid_members(subject, message_template_func, **kwargs):
    try:
        current = datetime.now()
        conn = sqlite3.connect('somiti.db')
        c = conn.cursor()
        c.execute("SELECT DISTINCT member_id FROM transactions WHERE month = ? AND year = ?", 
                 (current.month, current.year))
        paid_ids = [row[0] for row in c.fetchall()]
        if paid_ids:
            placeholders = ','.join(['?' for _ in paid_ids])
            c.execute(f"""
                SELECT name, email, monthly_savings, total_savings
                FROM members 
                WHERE status = 'active' AND email IS NOT NULL AND email != '' AND id NOT IN ({placeholders})
            """, paid_ids)
        else:
            c.execute("""
                SELECT name, email, monthly_savings, total_savings
                FROM members 
                WHERE status = 'active' AND email IS NOT NULL AND email != ''
            """)
        members = c.fetchall()
        conn.close()
        sent = 0
        month_name = BANGLA_MONTHS[current.month] if st.session_state.language == 'bn' else ENGLISH_MONTHS[current.month]
        for name, email, monthly, savings in members:
            monthly = float(monthly) if monthly else 500.0
            due = monthly
            message = message_template_func(name=name, monthly_amount=monthly, due_amount=due, month_name=month_name, **kwargs)
            if send_email(email, subject, message):
                sent += 1
        return sent
    except Exception as e:
        print(f"Unpaid bulk email error: {e}")
        return 0

# ==================== ইউটিলিটি ফাংশন ====================
def generate_member_id():
    try:
        conn = sqlite3.connect('somiti.db')
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM members")
        count = c.fetchone()[0] + 1
        conn.close()
        return f"{10000 + count}"
    except:
        return "10001"

def generate_password():
    return ''.join(random.choices(string.digits, k=6))

def get_total_savings():
    try:
        conn = sqlite3.connect('somiti.db')
        c = conn.cursor()
        c.execute("SELECT SUM(total_savings) FROM members WHERE status = 'active'")
        total = c.fetchone()[0] or 0
        conn.close()
        return float(total)
    except:
        return 0.0

def get_total_expenses():
    try:
        conn = sqlite3.connect('somiti.db')
        c = conn.cursor()
        c.execute("SELECT SUM(amount) FROM expenses")
        total = c.fetchone()[0] or 0
        conn.close()
        return float(total)
    except:
        return 0.0

def get_total_withdrawals():
    try:
        conn = sqlite3.connect('somiti.db')
        c = conn.cursor()
        c.execute("SELECT SUM(amount) FROM withdrawals")
        total = c.fetchone()[0] or 0
        conn.close()
        return float(total)
    except:
        return 0.0

def get_cash_balance():
    return get_total_savings() - get_total_expenses() - get_total_withdrawals()

def get_paid_members():
    try:
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
    except:
        return []

def get_unpaid_members():
    try:
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
    except:
        return []

def get_member_transactions(member_id):
    try:
        conn = sqlite3.connect('somiti.db')
        c = conn.cursor()
        c.execute("""
            SELECT id, full_date, full_date_en, amount, month_name, month_name_en, year, late_fee
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
    try:
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
    except:
        return []

def get_member_by_id(member_id):
    try:
        conn = sqlite3.connect('somiti.db')
        c = conn.cursor()
        c.execute("SELECT * FROM members WHERE id = ?", (member_id,))
        member = c.fetchone()
        conn.close()
        return member
    except:
        return None

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
        c.execute("SELECT id, date, amount, description FROM withdrawals ORDER BY id DESC")
        withdrawals = c.fetchall()
        conn.close()
        return withdrawals
    except:
        return []

def get_fund_transactions():
    try:
        conn = sqlite3.connect('somiti.db')
        c = conn.cursor()
        c.execute("SELECT id, date, type, amount, description FROM fund_transactions ORDER BY id DESC")
        trans = c.fetchall()
        conn.close()
        return trans
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
    try:
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
    except:
        return None

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
        return float(total)
    except:
        return 0.0

# ==================== UI থিম ====================
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
    .kpi-card { background: #21262d; padding: 15px; border-radius: 10px; text-align: center; border: 1px solid #30363d; }
    .kpi-card h3 { color: #c9d1d9; font-size: 14px; margin: 0 0 5px 0; }
    .kpi-card h2 { color: #58a6ff; font-size: 24px; margin: 0; }
    </style>
    """, unsafe_allow_html=True)

def show_admin_header():
    total = get_total_savings()
    cash = get_cash_balance()
    st.markdown(f'<div class="somiti-header"><h1>🌾 {SOMITI_NAME} 🌾</h1><p>{t("সঞ্চয় ও ঋণ ব্যবস্থাপনা", "Savings & Loan Management")}</p></div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f'<div class="total-box"><h2>💰 {total:,.0f} {t("টাকা", "Taka")}</h2><p>{t("মোট জমা", "Total Savings")}</p></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="cash-box"><h2>💵 {cash:,.0f} {t("টাকা", "Taka")}</h2><p>{t("ক্যাশ ব্যালেন্স", "Cash Balance")}</p></div>', unsafe_allow_html=True)

# ==================== পিডিএফ জেনারেশন ====================
def generate_pdf_member_list():
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()
    elements.append(Paragraph(f"{SOMITI_NAME} - {t('সদস্য তালিকা', 'Member List')}", styles['Heading1']))
    elements.append(Spacer(1, 20))
    members = get_all_members()
    data = [[t('আইডি', 'ID'), t('নাম', 'Name'), t('মোবাইল', 'Mobile'), t('কিস্তি', 'Monthly'), t('জমা', 'Savings')]]
    for m in members:
        monthly = float(m[6]) if m[6] else 500.0
        savings = float(m[7]) if m[7] else 0.0
        data.append([m[0], m[1], m[2], f"{monthly:,.0f}", f"{savings:,.0f}"])
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a5276')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
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
    title = f"{SOMITI_NAME} - {t('লেনদেন রিপোর্ট', 'Transaction Report')}"
    if member_id:
        member = get_member_by_id(member_id)
        if member:
            title = f"{SOMITI_NAME} - {member[1]} ({member_id})"
    elements.append(Paragraph(title, styles['Heading1']))
    elements.append(Spacer(1, 20))
    if member_id:
        trans = get_member_transactions(member_id)
        data = [[t('তারিখ', 'Date'), t('পরিমাণ', 'Amount'), t('মাস', 'Month'), t('সাল', 'Year')]]
        for tr in trans:
            amount = float(tr[3]) if tr[3] else 0.0
            data.append([tr[1], f"{amount:,.0f}", tr[4], str(tr[6])])
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
        data = [[t('তারিখ', 'Date'), t('সদস্য', 'Member'), t('পরিমাণ', 'Amount'), t('মাস', 'Month'), t('সাল', 'Year')]]
        for tr in trans:
            amount = float(tr[2]) if tr[2] else 0.0
            data.append([tr[0], tr[1], f"{amount:,.0f}", tr[3], str(tr[4])])
    if data:
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a5276')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        elements.append(table)
    doc.build(elements)
    buffer.seek(0)
    return buffer

# ==================== মেম্বার লগইন ও ড্যাশবোর্ড ====================
def member_login_page(member_id):
    apply_dark_theme()
    member = get_member_by_id(member_id)
    if not member:
        st.error(t("❌ সদস্য পাওয়া যায়নি", "❌ Member not found"))
        return
    st.markdown(f"""
    <div class="somiti-header">
        <h1>🌾 {SOMITI_NAME} 🌾</h1>
        <p>{t('সদস্য লগইন', 'Member Login')}</p>
    </div>
    """, unsafe_allow_html=True)
    st.markdown(f"### 🔐 {t('স্বাগতম', 'Welcome')}, {member[1]}")
    st.info(f"🆔 {t('সদস্য আইডি', 'Member ID')}: {member_id}")
    email = st.text_input(f"📧 {t('ইমেইল', 'Email')}")
    password = st.text_input(f"🔑 {t('পাসওয়ার্ড', 'Password')}", type="password")
    if st.button(t("প্রবেশ করুন", "Login"), use_container_width=True, type="primary"):
        if email == member[3] and password == member[4]:
            st.session_state.member_logged_in = True
            st.session_state.member_id = member_id
            st.rerun()
        else:
            st.error(t("❌ ভুল ইমেইল বা পাসওয়ার্ড", "❌ Wrong email or password"))

def member_dashboard_view():
    apply_dark_theme()
    member = get_member_by_id(st.session_state.member_id)
    if not member:
        st.error(t("সদস্য পাওয়া যায়নি", "Member not found"))
        return
    member_id, name, phone, email, password, total_savings, monthly_savings, join_date, status = member
    total_savings = float(total_savings) if total_savings else 0.0
    monthly = float(monthly_savings) if monthly_savings else 500.0
    st.markdown(f"""
    <div class="somiti-header">
        <h1>🌾 {SOMITI_NAME} 🌾</h1>
        <p>{t('সদস্য ড্যাশবোর্ড', 'Member Dashboard')}</p>
    </div>
    <div class="total-box">
        <h2>💰 {total_savings:,.0f} {t('টাকা', 'Taka')}</h2>
        <p>{t('আপনার মোট জমা', 'Your Total Savings')}</p>
    </div>
    """, unsafe_allow_html=True)
    with st.sidebar:
        st.markdown(f"### 👤 {name}")
        st.caption(f"🆔 {member_id} | 📱 {phone}")
        st.metric(f"💰 {t('মোট জমা', 'Total')}", f"{total_savings:,.0f} {t('টাকা', 'Taka')}")
        st.metric(f"📅 {t('মাসিক কিস্তি', 'Monthly')}", f"{monthly:,.0f} {t('টাকা', 'Taka')}")
        if st.button(f"🚪 {t('লগআউট', 'Logout')}", use_container_width=True):
            for k in ['member_logged_in', 'member_id']:
                if k in st.session_state:
                    del st.session_state[k]
            st.rerun()
    
    tab1, tab2, tab3 = st.tabs([
        f"📊 {t('ড্যাশবোর্ড', 'Dashboard')}",
        f"🔐 {t('পাসওয়ার্ড পরিবর্তন', 'Change Password')}",
        f"📥 {t('রিপোর্ট', 'Report')}"
    ])
    
    with tab1:
        st.markdown(f"### {t('স্বাগতম', 'Welcome')}, {name}! 👋")
        col1, col2 = st.columns(2)
        col1.metric(f"💰 {t('বর্তমান জমা', 'Current')}", f"{total_savings:,.0f} {t('টাকা', 'Taka')}")
        col2.metric(f"📅 {t('মাসিক কিস্তি', 'Monthly')}", f"{monthly:,.0f} {t('টাকা', 'Taka')}")
        current = datetime.now()
        conn = sqlite3.connect('somiti.db')
        c = conn.cursor()
        c.execute("SELECT SUM(amount) FROM transactions WHERE member_id = ? AND month = ? AND year = ?", 
                 (member_id, current.month, current.year))
        paid = c.fetchone()[0] or 0
        conn.close()
        paid = float(paid)
        if paid >= monthly:
            st.success(f"✅ {BANGLA_MONTHS[current.month]} {current.year} {t('মাসের কিস্তি পরিশোধ করেছেন', 'monthly paid')}")
        else:
            st.warning(f"⚠️ {t('বকেয়া', 'Due')}: {monthly - paid:,.0f} {t('টাকা', 'Taka')}")
        st.markdown("---")
        st.markdown(f"#### 📋 {t('লেনদেন ইতিহাস', 'Transaction History')}")
        trans = get_member_transactions(member_id)
        if trans:
            df_data = []
            for tr in trans:
                amount = float(tr[3]) if tr[3] else 0.0
                df_data.append({t("তারিখ", "Date"): tr[1], t("টাকা", "Amount"): f"{amount:,.0f}", t("মাস", "Month"): tr[4]})
            df = pd.DataFrame(df_data)
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info(t("কোনো লেনদেন নেই", "No transactions"))
    
    with tab2:
        st.markdown(f"### 🔐 {t('পাসওয়ার্ড পরিবর্তন', 'Change Password')}")
        new_pass = st.text_input(t("নতুন পাসওয়ার্ড", "New Password"), type="password", key="new_pass_member")
        confirm_pass = st.text_input(t("পাসওয়ার্ড নিশ্চিত করুন", "Confirm Password"), type="password", key="confirm_pass_member")
        if st.button(f"💾 {t('পাসওয়ার্ড আপডেট', 'Update Password')}", type="primary"):
            if new_pass and new_pass == confirm_pass:
                conn = sqlite3.connect('somiti.db')
                c = conn.cursor()
                c.execute("UPDATE members SET password = ? WHERE id = ?", (new_pass, member_id))
                conn.commit()
                conn.close()
                st.success(f"✅ {t('পাসওয়ার্ড পরিবর্তন হয়েছে', 'Password changed')}!")
                if email:
                    send_email(email, f"🔐 {t('পাসওয়ার্ড পরিবর্তন', 'Password Changed')}", f"{t('প্রিয়', 'Dear')} {name},\n\n{t('আপনার পাসওয়ার্ড সফলভাবে পরিবর্তন হয়েছে', 'Your password has been changed successfully')}.")
            elif not new_pass:
                st.error(t("❌ পাসওয়ার্ড দিন", "❌ Enter password"))
            else:
                st.error(t("❌ পাসওয়ার্ড মিলছে না", "❌ Passwords do not match"))
    
    with tab3:
        st.markdown(f"### 📥 {t('লেনদেন রিপোর্ট', 'Transaction Report')}")
        if st.button(f"📥 {t('পিডিএফ ডাউনলোড', 'Download PDF')}", type="primary"):
            pdf = generate_pdf_transactions(member_id)
            st.download_button(f"📥 {t('ডাউনলোড', 'Download')} PDF", pdf, f"{member_id}_transactions.pdf", mime="application/pdf")

# ==================== এডমিন প্যানেল ====================
def admin_login_page():
    apply_dark_theme()
    total = get_total_savings()
    st.markdown(f"""
    <div class="somiti-header"><h1>🌾 {SOMITI_NAME} 🌾</h1><p>{t('সঞ্চয় ও ঋণ ব্যবস্থাপনা', 'Savings & Loan Management')}</p></div>
    <div class="total-box"><h2>💰 {total:,.0f} {t('টাকা', 'Taka')}</h2><p>{t('মোট জমা', 'Total Savings')}</p></div>
    """, unsafe_allow_html=True)
    st.markdown(f"### 🔐 {t('এডমিন লগইন', 'Admin Login')}")
    phone = st.text_input(f"📱 {t('মোবাইল নম্বর', 'Mobile')}", placeholder="017XXXXXXXX")
    password = st.text_input(f"🔑 {t('পাসওয়ার্ড', 'Password')}", type="password")
    if st.button(t("প্রবেশ করুন", "Login"), use_container_width=True, type="primary"):
        if phone == ADMIN_MOBILE and password == ADMIN_PASSWORD:
            st.session_state.admin_logged_in = True
            st.success(t("✅ এডমিন লগইন সফল!", "✅ Admin login successful!"))
            st.rerun()
        else:
            st.error(t("❌ ভুল মোবাইল বা পাসওয়ার্ড", "❌ Wrong mobile or password"))

def admin_panel():
    apply_dark_theme()
    show_admin_header()
    with st.sidebar:
        st.markdown("### 🌐 " + t("ভাষা", "Language"))
        language = st.radio(
            t("ভাষা নির্বাচন করুন", "Select Language"),
            options=["🇧🇩 বাংলা", "🇬🇧 English"],
            index=0 if st.session_state.language == 'bn' else 1,
            label_visibility="collapsed",
            key="language_selector"
        )
        new_lang = 'bn' if language == "🇧🇩 বাংলা" else 'en'
        if new_lang != st.session_state.language:
            st.session_state.language = new_lang
            st.rerun()
        st.markdown("---")
        st.markdown(f"### 📋 {t('এডমিন মেনু', 'Admin Menu')}")
        st.caption(f"👑 {ADMIN_MOBILE}")
        menu = st.radio(
            t("নির্বাচন করুন", "Select"),
            [
                f"🏠 {t('ড্যাশবোর্ড', 'Dashboard')}",
                f"➕ {t('নতুন সদস্য', 'New Member')}",
                f"✏️ {t('সদস্য ব্যবস্থাপনা', 'Manage Members')}",
                f"💵 {t('টাকা জমা', 'Deposit')}",
                f"💰 {t('লেনদেন ব্যবস্থাপনা', 'Transactions')}",
                f"🔗 {t('সদস্য লিংক', 'Member Links')}",
                f"💸 {t('খরচ ব্যবস্থাপনা', 'Expenses')}",
                f"🏧 {t('ফান্ড ব্যবস্থাপনা', 'Fund Management')}",
                f"📊 {t('রিপোর্ট', 'Reports')}",
                f"📥 {t('পিডিএফ ডাউনলোড', 'PDF Download')}",
                f"📧 {t('ইমেইল টেস্ট', 'Email Test')}",
                f"🎲 {t('লটারি', 'Lottery')}",
                f"🚪 {t('লগআউট', 'Logout')}"
            ],
            label_visibility="collapsed"
        )
    
    if f"🚪 {t('লগআউট', 'Logout')}" in menu:
        if 'admin_logged_in' in st.session_state:
            del st.session_state.admin_logged_in
        st.rerun()
    
    elif f"🏠 {t('ড্যাশবোর্ড', 'Dashboard')}" in menu:
        st.markdown(f"### 🏠 {t('এডমিন ড্যাশবোর্ড', 'Admin Dashboard')}")
        col1, col2, col3, col4 = st.columns(4)
        try:
            conn = sqlite3.connect('somiti.db')
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM members WHERE status = 'active'")
            total_members = c.fetchone()[0]
            conn.close()
            total_savings = get_total_savings()
            this_month = get_current_month_collection()
            unpaid_count = len(get_unpaid_members())
            
            with col1:
                st.markdown(f"""<div class="kpi-card"><h3>👥 {t('সদস্য', 'Members')}</h3><h2>{total_members}</h2></div>""", unsafe_allow_html=True)
            with col2:
                st.markdown(f"""<div class="kpi-card"><h3>💰 {t('মোট জমা', 'Total')}</h3><h2>{total_savings:,.0f}</h2></div>""", unsafe_allow_html=True)
            with col3:
                st.markdown(f"""<div class="kpi-card"><h3>📅 {t('এই মাস', 'This Month')}</h3><h2>{this_month:,.0f}</h2></div>""", unsafe_allow_html=True)
            with col4:
                st.markdown(f"""<div class="kpi-card"><h3>⚠️ {t('বকেয়া', 'Due')}</h3><h2>{unpaid_count}</h2></div>""", unsafe_allow_html=True)
        except Exception as e:
            st.error(f"Error: {e}")
        
        st.markdown("---")
        st.markdown(f"### 📢 {t('বাল্ক ইমেইল', 'Bulk Email')}")
        col1, col2 = st.columns(2)
        with col1:
            if st.button(f"📢 {t('১ তারিখ রিমাইন্ডার', '1st Reminder')}", type="primary", use_container_width=True):
                subject = f"📢 {t('মাসিক কিস্তি রিমাইন্ডার', 'Monthly Reminder')} - {SOMITI_NAME}"
                sent = send_bulk_email_to_all_active_members(subject, get_first_reminder_email)
                st.success(f"✅ {sent} {t('জনকে পাঠানো হয়েছে', 'sent')}!")
        with col2:
            if st.button(f"⚠️ {t('১০ তারিখ বকেয়া', '10th Due')}", type="primary", use_container_width=True):
                subject = f"⚠️ {t('বকেয়া রিমাইন্ডার', 'Due Reminder')} - {SOMITI_NAME}"
                sent = send_bulk_email_to_unpaid_members(subject, get_tenth_reminder_email)
                st.success(f"✅ {sent} {t('জনকে পাঠানো হয়েছে', 'sent')}!")
    
    elif f"➕ {t('নতুন সদস্য', 'New Member')}" in menu:
        st.markdown(f"### ➕ {t('নতুন সদস্য নিবন্ধন', 'New Member Registration')}")
        name = st.text_input(f"{t('নাম', 'Name')} *")
        phone = st.text_input(f"{t('মোবাইল', 'Mobile')} *", placeholder="017XXXXXXXX")
        email = st.text_input(f"📧 {t('ইমেইল', 'Email')}")
        monthly = st.number_input(f"{t('মাসিক কিস্তি', 'Monthly')} ({t('টাকা', 'Taka')})", value=500, step=50)
        if st.button(f"✅ {t('সদস্য যোগ করুন', 'Add Member')}", type="primary"):
            if name and phone:
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
                        send_email(email, f"🎉 {t('স্বাগতম', 'Welcome')} - {SOMITI_NAME}", get_welcome_email(name, member_id, phone, password, monthly))
                    st.success(f"✅ {t('সদস্য তৈরি', 'Member created')}!")
                    st.info(f"{t('আইডি', 'ID')}: {member_id} | {t('পাস', 'Pass')}: {password}")
                    st.balloons()
                except sqlite3.IntegrityError:
                    st.error(t("❌ এই মোবাইল ইতিমধ্যে নিবন্ধিত", "❌ Mobile already registered"))
            else:
                st.error(t("❌ নাম ও মোবাইল আবশ্যক", "❌ Name and mobile required"))
    
    elif f"✏️ {t('সদস্য ব্যবস্থাপনা', 'Manage Members')}" in menu:
        st.markdown(f"### ✏️ {t('সদস্য ব্যবস্থাপনা', 'Member Management')}")
        members = get_all_members()
        if members:
            for m in members:
                member_id, name, phone, email, password, status, monthly, savings = m
                monthly = float(monthly) if monthly else 500.0
                savings = float(savings) if savings else 0.0
                with st.expander(f"👤 {name} - {member_id}"):
                    st.write(f"📱 {phone} | 📧 {email or 'N/A'} | 💰 {savings:,.0f} {t('টাকা', 'Taka')}")
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        if st.button(f"📝 {t('এডিট', 'Edit')}", key=f"e_{member_id}"):
                            st.session_state[f"edit_{member_id}"] = True
                    with col2:
                        if st.button(f"🔐 {t('পাসওয়ার্ড', 'Password')}", key=f"p_{member_id}"):
                            st.session_state[f"pass_{member_id}"] = True
                    with col3:
                        new_status = 'inactive' if status == 'active' else 'active'
                        btn_text = t('নিষ্ক্রিয়', 'Inactive') if status == 'active' else t('সক্রিয়', 'Active')
                        if st.button(f"🔄 {btn_text}", key=f"s_{member_id}"):
                            conn = sqlite3.connect('somiti.db')
                            c = conn.cursor()
                            c.execute("UPDATE members SET status=? WHERE id=?", (new_status, member_id))
                            conn.commit()
                            conn.close()
                            st.rerun()
                    with col4:
                        if st.button(f"🗑️ {t('ডিলিট', 'Delete')}", key=f"del_{member_id}"):
                            st.session_state[f"delete_{member_id}"] = True
                    
                    if st.session_state.get(f"delete_{member_id}"):
                        st.warning(f"⚠️ {t('আপনি কি নিশ্চিত?', 'Are you sure?')}")
                        c1, c2 = st.columns(2)
                        with c1:
                            if st.button(f"✅ {t('হ্যাঁ', 'Yes')}", key=f"confirm_del_{member_id}"):
                                conn = sqlite3.connect('somiti.db')
                                c = conn.cursor()
                                c.execute("DELETE FROM transactions WHERE member_id = ?", (member_id,))
                                c.execute("DELETE FROM members WHERE id = ?", (member_id,))
                                conn.commit()
                                conn.close()
                                st.success(f"✅ {t('ডিলিট', 'Deleted')}!")
                                del st.session_state[f"delete_{member_id}"]
                                st.rerun()
                        with c2:
                            if st.button(f"❌ {t('না', 'No')}", key=f"cancel_del_{member_id}"):
                                del st.session_state[f"delete_{member_id}"]
                                st.rerun()
                    
                    if st.session_state.get(f"edit_{member_id}"):
                        with st.form(f"bio_edit_{member_id}"):
                            new_name = st.text_input(t("নাম", "Name"), value=name)
                            new_phone = st.text_input(t("মোবাইল", "Mobile"), value=phone)
                            new_email = st.text_input(t("ইমেইল", "Email"), value=email or "")
                            new_mon = st.number_input(t("কিস্তি", "Monthly"), value=monthly, step=50.0)
                            if st.form_submit_button(f"💾 {t('সেভ', 'Save')}", type="primary"):
                                try:
                                    conn = sqlite3.connect('somiti.db')
                                    c = conn.cursor()
                                    c.execute("UPDATE members SET name=?, phone=?, email=?, monthly_savings=? WHERE id=?",
                                             (new_name, new_phone, new_email, new_mon, member_id))
                                    conn.commit()
                                    conn.close()
                                    st.success(f"✅ {t('আপডেট', 'Updated')}!")
                                    del st.session_state[f"edit_{member_id}"]
                                    st.rerun()
                                except sqlite3.IntegrityError:
                                    st.error(t("❌ মোবাইল ইতিমধ্যে নিবন্ধিত", "❌ Mobile already registered"))
                    
                    if st.session_state.get(f"pass_{member_id}"):
                        if st.button(f"✅ {t('নতুন পাসওয়ার্ড', 'New Password')}", key=f"gen_{member_id}"):
                            new_pass = generate_password()
                            conn = sqlite3.connect('somiti.db')
                            c = conn.cursor()
                            c.execute("UPDATE members SET password=? WHERE id=?", (new_pass, member_id))
                            conn.commit()
                            conn.close()
                            if email:
                                send_email(email, f"🔐 {t('পাসওয়ার্ড রিসেট', 'Password Reset')}", get_password_reset_email(name, new_pass))
                            st.success(f"✅ {t('নতুন পাস', 'New Pass')}: {new_pass}")
                            del st.session_state[f"pass_{member_id}"]
                            st.rerun()
        else:
            st.info(t("কোনো সদস্য নেই", "No members"))
    
    elif f"💵 {t('টাকা জমা', 'Deposit')}" in menu:
        st.markdown(f"### 💵 {t('সদস্যের টাকা জমা', 'Member Deposit')}")
        tab1, tab2 = st.tabs([f"✅ {t('জমা দিয়েছে', 'Paid')}", f"❌ {t('জমা দেয়নি', 'Unpaid')}"])
        with tab1:
            paid = get_paid_members()
            if paid:
                for pm in paid:
                    savings_val = float(pm[4]) if pm[4] else 0.0
                    st.markdown(f"""<div class="member-card"><strong>{pm[1]}</strong> ({pm[0]})<br><small>📱 {pm[2]} | 💰 {savings_val:,.0f} {t('টাকা', 'Taka')}</small></div>""", unsafe_allow_html=True)
            else:
                st.info(t("কেউ জমা দেয়নি", "No one paid"))
        with tab2:
            unpaid = get_unpaid_members()
            if unpaid:
                for um in unpaid:
                    savings_val = float(um[4]) if um[4] else 0.0
                    monthly_val = float(um[3]) if um[3] else 500.0
                    with st.expander(f"❌ {um[1]} ({um[0]})"):
                        st.write(f"📱 {um[2]} | 💰 {savings_val:,.0f} {t('টাকা', 'Taka')} | 📅 {t('কিস্তি', 'Monthly')}: {monthly_val:,.0f}")
                        deposit_date = st.date_input(t("জমার তারিখ", "Deposit Date"), datetime.now(), key=f"date_{um[0]}")
                        day = deposit_date.day
                        month = deposit_date.month
                        year = deposit_date.year
                        c1, c2 = st.columns(2)
                        with c1:
                            months_count = st.number_input(t("কত মাস", "Months"), 1, 12, 1, key=f"count_{um[0]}")
                        with c2:
                            late_fee = st.number_input(t("লেট ফি", "Late Fee"), 0.0, step=10.0, key=f"fee_{um[0]}")
                        total = monthly_val * months_count + late_fee
                        if st.button(f"✅ {t('জমা নিন', 'Deposit')}", key=f"dep_{um[0]}", type="primary"):
                            today_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            full_date = f"{day} {BANGLA_MONTHS[month]} {year}"
                            full_date_en = f"{day} {ENGLISH_MONTHS[month]} {year}"
                            date_iso = f"{year}-{month:02d}-{day:02d}"
                            conn = sqlite3.connect('somiti.db')
                            c = conn.cursor()
                            for i in range(int(months_count)):
                                c.execute("""
                                    INSERT INTO transactions 
                                    (member_id, amount, transaction_type, day, month, year, month_name, month_name_en, full_date, full_date_en, date_iso, late_fee, created_at)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                """, (um[0], monthly_val, 'deposit', day, month, year, BANGLA_MONTHS[month], ENGLISH_MONTHS[month], full_date, full_date_en, date_iso, late_fee if i == 0 else 0, today_str))
                            c.execute("UPDATE members SET total_savings = IFNULL(total_savings, 0) + ? WHERE id = ?", (total, um[0]))
                            conn.commit()
                            conn.close()
                            if um[5]:
                                send_email(um[5], f"✅ {t('পেমেন্ট সফল', 'Payment Success')} - {SOMITI_NAME}", get_payment_success_email(um[1], f"{total:,.0f}", full_date, full_date_en, BANGLA_MONTHS[month], ENGLISH_MONTHS[month], f"{savings_val + total:,.0f}"))
                            st.success(f"✅ {total:,.0f} {t('টাকা জমা', 'Deposited')}!")
                            st.balloons()
                            time.sleep(1)
                            st.rerun()
            else:
                st.success(f"🎉 {t('সবাই জমা দিয়েছেন', 'All paid')}!")
    
    elif f"💰 {t('লেনদেন ব্যবস্থাপনা', 'Transactions')}" in menu:
        st.markdown(f"### 💰 {t('লেনদেন ব্যবস্থাপনা', 'Transaction Management')}")
        members_list = get_all_members()
        if members_list:
            options = {f"{m[1]} ({m[0]})": m[0] for m in members_list}
            selected = st.selectbox(t("সদস্য নির্বাচন", "Select Member"), list(options.keys()))
            if selected:
                member_id = options[selected]
                member = get_member_by_id(member_id)
                if member:
                    savings_val = float(member[7]) if len(member) > 7 and member[7] else 0.0
                    st.success(f"👤 {member[1]} | 💰 {savings_val:,.0f} {t('টাকা', 'Taka')}")
                    trans = get_member_transactions(member_id)
                    if trans:
                        for tr in trans:
                            c1, c2, c3, c4, c5 = st.columns([2, 1.5, 1.5, 1, 1])
                            c1.write(tr[1])
                            amount_val = float(tr[3]) if tr[3] else 0.0
                            c2.write(f"{amount_val:,.0f} {t('টাকা', 'Taka')}")
                            c3.write(f"{tr[4]} {tr[6]}")
                            if c4.button("✏️", key=f"edit_{tr[0]}"):
                                st.session_state[f"edit_trans_{tr[0]}"] = True
                            if c5.button("🗑️", key=f"del_{tr[0]}"):
                                st.session_state[f"confirm_del_{tr[0]}"] = True
                            
                            if st.session_state.get(f"confirm_del_{tr[0]}"):
                                st.warning(t("নিশ্চিত?", "Confirm?"))
                                cy, cn = st.columns(2)
                                with cy:
                                    if st.button("✅", key=f"yes_{tr[0]}"):
                                        conn = sqlite3.connect('somiti.db')
                                        c = conn.cursor()
                                        c.execute("UPDATE members SET total_savings = total_savings - ? WHERE id = ?", (amount_val, member_id))
                                        c.execute("DELETE FROM transactions WHERE id = ?", (tr[0],))
                                        conn.commit()
                                        conn.close()
                                        if member[3]:
                                            send_email(member[3], f"🗑️ {t('লেনদেন বাতিল', 'Cancelled')}", get_transaction_remove_email(member[1], f"{amount_val:,.0f}", tr[1], tr[2], f"{savings_val - amount_val:,.0f}"))
                                        st.success("✅")
                                        del st.session_state[f"confirm_del_{tr[0]}"]
                                        st.rerun()
                                with cn:
                                    if st.button("❌", key=f"no_{tr[0]}"):
                                        del st.session_state[f"confirm_del_{tr[0]}"]
                                        st.rerun()
                            
                            if st.session_state.get(f"edit_trans_{tr[0]}"):
                                with st.form(f"edit_{tr[0]}"):
                                    new_amt = st.number_input(t("টাকা", "Amount"), value=amount_val, step=50.0)
                                    if st.form_submit_button("💾"):
                                        conn = sqlite3.connect('somiti.db')
                                        c = conn.cursor()
                                        diff = new_amt - amount_val
                                        c.execute("UPDATE transactions SET amount = ? WHERE id = ?", (new_amt, tr[0]))
                                        c.execute("UPDATE members SET total_savings = total_savings + ? WHERE id = ?", (diff, member_id))
                                        conn.commit()
                                        conn.close()
                                        if member[3]:
                                            send_email(member[3], f"✏️ {t('সংশোধন', 'Edit')}", get_transaction_edit_email(member[1], f"{amount_val:,.0f}", f"{new_amt:,.0f}", tr[1], tr[2], f"{savings_val + diff:,.0f}"))
                                        st.success("✅")
                                        del st.session_state[f"edit_trans_{tr[0]}"]
                                        st.rerun()
                    else:
                        st.info(t("কোনো লেনদেন নেই", "No transactions"))
        else:
            st.info(t("কোনো সদস্য নেই", "No members"))
    
    # বাকি মেনু (সংক্ষিপ্ত) - প্রয়োজনীয় অংশ সংযুক্ত
    # ... (লিংক, খরচ, ফান্ড, রিপোর্ট, পিডিএফ, ইমেইল টেস্ট, লটারি)
    # সম্পূর্ণ ফাইলটি পরবর্তী মেসেজে দেওয়া হবে।

# ==================== মেইন ====================
def main():
    init_database()
    check_and_archive_old_data()
    if 'member_logged_in' not in st.session_state:
        st.session_state.member_logged_in = False
    if 'admin_logged_in' not in st.session_state:
        st.session_state.admin_logged_in = False
    if member_login_id:
        if not st.session_state.member_logged_in:
            member_login_page(member_login_id)
        else:
            member_dashboard_view()
        return
    if not st.session_state.admin_logged_in:
        admin_login_page()
    else:
        admin_panel()

if __name__ == "__main__":
    main()
