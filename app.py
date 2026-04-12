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
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

ADMIN_MOBILE = "01766222373"
ADMIN_PASSWORD = "oio112024"
SOMITI_NAME = "ঐক্য উদ্যোগ সংস্থা"
SOMITI_NAME_EN = "Oikko Uddog Songstha"
SOMITI_START_DATE = "2026-04-12"

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = "oiorganization2024@gmail.com"
SENDER_PASSWORD = "hnhm ocix kyxv ioiz"

st.set_page_config(page_title=SOMITI_NAME, page_icon="🌾", layout="wide")

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

def init_database():
    conn = sqlite3.connect('somiti.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)''')
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('start_date', ?)", (SOMITI_START_DATE,))
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
        c.execute("SELECT email FROM members LIMIT 1")
    except:
        c.execute("ALTER TABLE members ADD COLUMN email TEXT")
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
            note TEXT,
            late_fee REAL DEFAULT 0,
            created_at TEXT NOT NULL
        )
    ''')
    try:
        c.execute("SELECT day FROM transactions LIMIT 1")
    except:
        for col, default_val in [
            ('day', '1'), ('month', '1'), ('year', '2026'),
            ('month_name', "''"), ('month_name_en', "''"),
            ('full_date', "''"), ('full_date_en', "''"),
            ('date_iso', "''"), ('created_at', "''")
        ]:
            try:
                c.execute(f"ALTER TABLE transactions ADD COLUMN {col} TEXT DEFAULT {default_val}")
            except:
                pass
    c.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT NOT NULL,
            amount REAL NOT NULL,
            date TEXT NOT NULL,
            category TEXT
        )
    ''')
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

def send_email(to_email, subject, message):
    if not to_email or '@' not in to_email:
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
            <div style="max-width: 500px; margin: 0 auto; background: white; border-radius: 10px; overflow: hidden;">
                <div style="background: #1a5276; color: white; padding: 25px; text-align: center;">
                    <h2 style="margin: 0;">🌾 {SOMITI_NAME}</h2>
                    <p style="margin: 5px 0 0;">{SOMITI_NAME_EN}</p>
                </div>
                <div style="padding: 30px;">
                    {message.replace(chr(10), '<br>')}
                </div>
                <div style="background: #f8f9fa; padding: 15px; text-align: center; font-size: 12px; color: #666;">
                    <p style="margin: 0;">{t('স্বয়ংক্রিয় ইমেইল', 'Automated email')}</p>
                    <p style="margin: 5px 0 0;">{t('যোগাযোগ', 'Contact')}: {ADMIN_MOBILE}</p>
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
    except:
        return False

def get_welcome_email(name, member_id, phone, password, monthly):
    return f"""{t('প্রিয়', 'Dear')} {name},

{t('স্বাগতম', 'Welcome')} - {SOMITI_NAME}

{t('আপনার তথ্য', 'Your info')}:
🆔 {member_id}
📱 {phone}
🔑 {password}
💰 {monthly} {t('টাকা', 'Taka')}

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

🔐 {t('পাসওয়ার্ড রিসেট', 'Password Reset')}

{t('নতুন পাসওয়ার্ড', 'New password')}: {new_password}

{SOMITI_NAME}"""

def get_transaction_edit_email(name, old_amount, new_amount, full_date, full_date_en, total_savings):
    display_date = full_date if st.session_state.language == 'bn' else full_date_en
    return f"""{t('প্রিয়', 'Dear')} {name},

✏️ {t('লেনদেন সংশোধন', 'Transaction Edit')}

{t('তারিখ', 'Date')}: {display_date}
{t('পূর্বে', 'Old')}: {old_amount} → {t('নতুন', 'New')}: {new_amount}
{t('মোট', 'Total')}: {total_savings}

{SOMITI_NAME}"""

def get_transaction_remove_email(name, amount, full_date, full_date_en, total_savings):
    display_date = full_date if st.session_state.language == 'bn' else full_date_en
    return f"""{t('প্রিয়', 'Dear')} {name},

🗑️ {t('লেনদেন বাতিল', 'Transaction Cancelled')}

{t('তারিখ', 'Date')}: {display_date}
{t('বাতিলকৃত', 'Cancelled')}: {amount} {t('টাকা', 'Taka')}
{t('মোট', 'Total')}: {total_savings}

{SOMITI_NAME}"""

def get_withdrawal_notification(name, amount, description, date, previous_balance, current_balance):
    return f"""{t('প্রিয়', 'Dear')} {name},

🏧 {t('টাকা উত্তোলন', 'Withdrawal Notice')}

{t('তারিখ', 'Date')}: {date}
{t('পরিমাণ', 'Amount')}: {amount} {t('টাকা', 'Taka')}
{t('বিবরণ', 'Description')}: {description}
{t('পূর্বে', 'Before')}: {previous_balance} → {t('পরে', 'After')}: {current_balance}

{SOMITI_NAME}"""

def get_lottery_winner_email(name):
    return f"""{t('প্রিয়', 'Dear')} {name},

🎉 {t('অভিনন্দন', 'Congratulations')}!
{t('লাকি ড্র বিজয়ী', 'Lucky draw winner')}!

{SOMITI_NAME}"""

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
            SELECT id, full_date, full_date_en, amount, month_name, month_name_en, year, late_fee, note
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
        return total
    except:
        return 0

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
    <div class="somiti-header"><h1>🌾 {SOMITI_NAME} 🌾</h1><p>{t('সঞ্চয় ও ঋণ ব্যবস্থাপনা', 'Savings & Loan Management')}</p></div>
    <div class="total-box"><h2>💰 {total:,.0f} {t('টাকা', 'Taka')}</h2><p>{t('মোট জমা', 'Total Savings')}</p></div>
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
        data.append([m[0], m[1], m[2], f"{m[6]:,.0f}", f"{m[7]:,.0f}"])
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
        for t in trans:
            data.append([t[1], f"{t[3]:,.0f}", t[4], str(t[6])])
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
        for t in trans:
            data.append([t[0], t[1], f"{t[2]:,.0f}", t[3], str(t[4])])
    if data:
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
    monthly = monthly_savings or 500
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
    if paid >= monthly:
        st.success(f"✅ {BANGLA_MONTHS[current.month]} {current.year} {t('মাসের কিস্তি পরিশোধ করেছেন', 'monthly paid')}")
    else:
        st.warning(f"⚠️ {t('বকেয়া', 'Due')}: {monthly - paid:,.0f} {t('টাকা', 'Taka')}")
    st.markdown("---")
    st.markdown(f"#### 📋 {t('লেনদেন ইতিহাস', 'Transaction History')}")
    trans = get_member_transactions(member_id)
    if trans:
        df = pd.DataFrame([{t("তারিখ", "Date"): t[1], t("টাকা", "Amount"): f"{t[3]:,.0f}", t("মাস", "Month"): t[4]} for t in trans])
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info(t("কোনো লেনদেন নেই", "No transactions"))

def admin_login_page():
    apply_dark_theme()
    show_header()
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
                f"🏧 {t('টাকা উত্তোলন', 'Withdrawal')}",
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
            col1.metric(f"👥 {t('সদস্য', 'Members')}", c.fetchone()[0])
            conn.close()
            col2.metric(f"💰 {t('জমা', 'Savings')}", f"{get_total_savings():,.0f}")
            col3.metric(f"📅 {t('এই মাস', 'This Month')}", f"{get_current_month_collection():,.0f}")
            col4.metric(f"⚠️ {t('বকেয়া', 'Due')}", f"{len(get_unpaid_members())}")
        except:
            pass
    
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
                        send_email(email, f"🎉 {t('স্বাগতম', 'Welcome')} - {SOMITI_NAME}", 
                                  get_welcome_email(name, member_id, phone, password, monthly))
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
                    col1, col2, col3 = st.columns(3)
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
                    if st.session_state.get(f"edit_{member_id}"):
                        new_name = st.text_input(t("নাম", "Name"), value=name, key=f"name_{member_id}")
                        new_email = st.text_input(t("ইমেইল", "Email"), value=email or "", key=f"email_{member_id}")
                        new_mon = st.number_input(t("কিস্তি", "Monthly"), value=monthly, step=50.0, key=f"mon_{member_id}")
                        if st.button(f"💾 {t('সেভ', 'Save')}", key=f"save_{member_id}"):
                            conn = sqlite3.connect('somiti.db')
                            c = conn.cursor()
                            c.execute("UPDATE members SET name=?, email=?, monthly_savings=? WHERE id=?",
                                     (new_name, new_email, new_mon, member_id))
                            conn.commit()
                            conn.close()
                            st.success(f"✅ {t('আপডেট', 'Updated')}!")
                            del st.session_state[f"edit_{member_id}"]
                            st.rerun()
                    if st.session_state.get(f"pass_{member_id}"):
                        if st.button(f"✅ {t('নতুন পাসওয়ার্ড', 'New Password')}", key=f"gen_{member_id}"):
                            new_pass = generate_password()
                            conn = sqlite3.connect('somiti.db')
                            c = conn.cursor()
                            c.execute("UPDATE members SET password=? WHERE id=?", (new_pass, member_id))
                            conn.commit()
                            conn.close()
                            if email:
                                send_email(email, f"🔐 {t('পাসওয়ার্ড রিসেট', 'Password Reset')}", 
                                          get_password_reset_email(name, new_pass))
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
                for m in paid:
                    st.markdown(f"""
                    <div class="member-card">
                        <strong>{m[1]}</strong> ({m[0]})<br>
                        <small>📱 {m[2]} | 💰 {m[4]:,.0f} {t('টাকা', 'Taka')}</small>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info(t("কেউ জমা দেয়নি", "No one paid"))
        with tab2:
            unpaid = get_unpaid_members()
            if unpaid:
                for m in unpaid:
                    with st.expander(f"❌ {m[1]} ({m[0]})"):
                        st.write(f"📱 {m[2]} | 💰 {m[4]:,.0f} {t('টাকা', 'Taka')} | 📅 {t('কিস্তি', 'Monthly')}: {m[3]:,.0f}")
                        current = datetime.now()
                        day = st.number_input(t("দিন", "Day"), 1, 31, current.day, key=f"day_{m[0]}")
                        month = st.selectbox(t("মাস", "Month"), list(BANGLA_MONTHS.keys()), 
                                            format_func=lambda x: BANGLA_MONTHS[x], index=current.month-1, key=f"month_{m[0]}")
                        year = st.number_input(t("সাল", "Year"), 2020, 2050, current.year, key=f"year_{m[0]}")
                        c1, c2 = st.columns(2)
                        with c1:
                            months_count = st.number_input(t("কত মাস", "Months"), 1, 12, 1, key=f"count_{m[0]}")
                        with c2:
                            late_fee = st.number_input(t("লেট ফি", "Late Fee"), 0.0, step=10.0, key=f"fee_{m[0]}")
                        total = m[3] * months_count + late_fee
                        if st.button(f"✅ {t('জমা নিন', 'Deposit')}", key=f"dep_{m[0]}", type="primary"):
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
                                """, (
                                    m[0], m[3], 'deposit', day, month, year, 
                                    BANGLA_MONTHS[month], ENGLISH_MONTHS[month],
                                    full_date, full_date_en, date_iso, 
                                    late_fee if i == 0 else 0, today_str
                                ))
                            c.execute("UPDATE members SET total_savings = total_savings + ? WHERE id = ?", (total, m[0]))
                            c.execute("SELECT total_savings FROM members WHERE id = ?", (m[0],))
                            new_total = c.fetchone()[0]
                            conn.commit()
                            conn.close()
                            if m[5]:
                                send_email(m[5], f"✅ {t('পেমেন্ট সফল', 'Payment Success')} - {SOMITI_NAME}", 
                                          get_payment_success_email(m[1], f"{total:,.0f}", full_date, full_date_en, 
                                                                    BANGLA_MONTHS[month], ENGLISH_MONTHS[month], f"{new_total:,.0f}"))
                            st.success(f"✅ {total:,.0f} {t('টাকা জমা', 'Deposited')}!")
                            st.rerun()
            else:
                st.success(f"🎉 {t('সবাই জমা দিয়েছেন', 'All paid')}!")
    
    elif f"💰 {t('লেনদেন ব্যবস্থাপনা', 'Transactions')}" in menu:
        st.markdown(f"### 💰 {t('লেনদেন ব্যবস্থাপনা', 'Transaction Management')}")
        members = get_all_members()
        if members:
            options = {f"{m[1]} ({m[0]})": m[0] for m in members}
            selected = st.selectbox(t("সদস্য নির্বাচন", "Select Member"), list(options.keys()))
            if selected:
                member_id = options[selected]
                member = get_member_by_id(member_id)
                if member:
                    st.success(f"👤 {member[1]} | 💰 {member[7]:,.0f} {t('টাকা', 'Taka')}")
                    trans = get_member_transactions(member_id)
                    if trans:
                        for t in trans:
                            c1, c2, c3, c4, c5 = st.columns([2, 1.5, 1.5, 1, 1])
                            c1.write(t[1])
                            c2.write(f"{t[3]:,.0f} {t('টাকা', 'Taka')}")
                            c3.write(f"{t[4]} {t[6]}")
                            if c4.button("✏️", key=f"edit_{t[0]}"):
                                st.session_state[f"edit_trans_{t[0]}"] = True
                            if c5.button("🗑️", key=f"del_{t[0]}"):
                                conn = sqlite3.connect('somiti.db')
                                c = conn.cursor()
                                c.execute("UPDATE members SET total_savings = total_savings - ? WHERE id = ?", (t[3], member_id))
                                c.execute("DELETE FROM transactions WHERE id = ?", (t[0],))
                                c.execute("SELECT total_savings FROM members WHERE id = ?", (member_id,))
                                new_total = c.fetchone()[0]
                                conn.commit()
                                conn.close()
                                if member[3]:
                                    send_email(member[3], f"🗑️ {t('লেনদেন বাতিল', 'Transaction Cancelled')}", 
                                              get_transaction_remove_email(member[1], f"{t[3]:,.0f}", t[1], t[2], f"{new_total:,.0f}"))
                                st.success(f"✅ {t('রিমুভ', 'Removed')}!")
                                st.rerun()
                            if st.session_state.get(f"edit_trans_{t[0]}"):
                                with st.form(f"edit_{t[0]}"):
                                    new_amt = st.number_input(t("টাকা", "Amount"), value=float(t[3]), step=50.0)
                                    if st.form_submit_button(f"💾 {t('সেভ', 'Save')}", type="primary"):
                                        conn = sqlite3.connect('somiti.db')
                                        c = conn.cursor()
                                        diff = new_amt - t[3]
                                        c.execute("UPDATE transactions SET amount = ? WHERE id = ?", (new_amt, t[0]))
                                        c.execute("UPDATE members SET total_savings = total_savings + ? WHERE id = ?", (diff, member_id))
                                        c.execute("SELECT total_savings FROM members WHERE id = ?", (member_id,))
                                        new_total = c.fetchone()[0]
                                        conn.commit()
                                        conn.close()
                                        if member[3]:
                                            send_email(member[3], f"✏️ {t('লেনদেন সংশোধন', 'Transaction Edit')}", 
                                                      get_transaction_edit_email(member[1], f"{t[3]:,.0f}", f"{new_amt:,.0f}", t[1], t[2], f"{new_total:,.0f}"))
                                        st.success(f"✅ {t('আপডেট', 'Updated')}!")
                                        del st.session_state[f"edit_trans_{t[0]}"]
                                        st.rerun()
                    else:
                        st.info(t("কোনো লেনদেন নেই", "No transactions"))
        else:
            st.info(t("কোনো সদস্য নেই", "No members"))
    
    elif f"🔗 {t('সদস্য লিংক', 'Member Links')}" in menu:
        st.markdown(f"### 🔗 {t('সদস্য লিংক ও পাসওয়ার্ড', 'Member Links & Passwords')}")
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
                st.markdown(f'<button onclick="navigator.clipboard.writeText(\'{link}\')" style="background:#238636; color:white; border:none; padding:8px; border-radius:5px; width:100%;">📋 {t("লিংক কপি", "Copy Link")}</button>', unsafe_allow_html=True)
            with c2:
                st.markdown(f'<button onclick="navigator.clipboard.writeText(\'{password}\')" style="background:#238636; color:white; border:none; padding:8px; border-radius:5px; width:100%;">📋 {t("পাসওয়ার্ড কপি", "Copy Pass")}</button>', unsafe_allow_html=True)
            with c3:
                if email and st.button(f"📧 {t('ইমেইল', 'Email')}", key=f"mail_{member_id}"):
                    msg = f"""{t('প্রিয়', 'Dear')} {name},

{t('আপনার লগইন তথ্য', 'Your login info')}:
🔗 {t('লিংক', 'Link')}: {link}
📱 {t('মোবাইল', 'Mobile')}: {phone}
🔑 {t('পাসওয়ার্ড', 'Password')}: {password}"""
                    send_email(email, f"🔐 {t('লগইন তথ্য', 'Login Info')} - {SOMITI_NAME}", msg)
                    st.success(f"✅ {t('পাঠানো হয়েছে', 'Sent')}!")
            st.markdown("---")
    
    elif f"💸 {t('খরচ ব্যবস্থাপনা', 'Expenses')}" in menu:
        st.markdown(f"### 💸 {t('খরচ ব্যবস্থাপনা', 'Expense Management')}")
        tab1, tab2 = st.tabs([f"➕ {t('নতুন খরচ', 'New Expense')}", f"📋 {t('খরচের তালিকা', 'Expense List')}"])
        with tab1:
            with st.form("exp_form"):
                desc = st.text_input(t("বিবরণ", "Description"))
                amt = st.number_input(t("টাকা", "Amount"), 0.0, step=10.0)
                cat = st.selectbox(t("ক্যাটাগরি", "Category"), 
                                   [t("অফিস ভাড়া", "Office Rent"), t("চা-নাস্তা", "Snacks"), 
                                    t("স্টেশনারি", "Stationery"), t("পরিবহন", "Transport"), t("অন্যান্য", "Other")])
                if st.form_submit_button(f"💾 {t('সংরক্ষণ', 'Save')}", type="primary"):
                    if desc and amt > 0:
                        conn = sqlite3.connect('somiti.db')
                        c = conn.cursor()
                        c.execute("INSERT INTO expenses (description, amount, date, category) VALUES (?,?,?,?)",
                                 (desc, amt, datetime.now().strftime("%Y-%m-%d"), cat))
                        conn.commit()
                        conn.close()
                        st.success(f"✅ {amt:,.0f} {t('টাকা যোগ', 'Added')}!")
                        st.rerun()
        with tab2:
            expenses = get_all_expenses()
            if expenses:
                for e in expenses[:20]:
                    c1, c2, c3, c4, c5 = st.columns([2, 2, 3, 2, 1])
                    c1.write(e[1])
                    c2.write(e[4])
                    c3.write(e[2])
                    c4.write(f"{e[3]:,.0f} {t('টাকা', 'Taka')}")
                    if c5.button("🗑️", key=f"de_{e[0]}"):
                        conn = sqlite3.connect('somiti.db')
                        c = conn.cursor()
                        c.execute("DELETE FROM expenses WHERE id=?", (e[0],))
                        conn.commit()
                        conn.close()
                        st.rerun()
                st.metric(f"📊 {t('মোট খরচ', 'Total')}", f"{sum(e[3] for e in expenses):,.0f} {t('টাকা', 'Taka')}")
    
    elif f"🏧 {t('টাকা উত্তোলন', 'Withdrawal')}" in menu:
        st.markdown(f"### 🏧 {t('সমিতির টাকা উত্তোলন', 'Fund Withdrawal')}")
        cash = get_cash_balance()
        st.info(f"💰 {t('বর্তমান ক্যাশ ব্যালেন্স', 'Current Balance')}: {cash:,.0f} {t('টাকা', 'Taka')}")
        with st.form("withdraw_form"):
            amount = st.number_input(t("উত্তোলনের পরিমাণ", "Amount"), 0.0, step=100.0)
            description = st.text_area(t("বিবরণ", "Description") + f" ({t('কেন উত্তোলন', 'Why withdrawing')})")
            date = st.date_input(t("উত্তোলনের তারিখ", "Date"), datetime.now())
            if st.form_submit_button(f"✅ {t('উত্তোলন করুন', 'Withdraw')}", type="primary"):
                if amount > 0 and amount <= cash:
                    if description:
                        conn = sqlite3.connect('somiti.db')
                        c = conn.cursor()
                        c.execute("""
                            INSERT INTO withdrawals (date, amount, description, withdrawn_by, previous_balance, current_balance, created_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (date.strftime("%Y-%m-%d"), amount, description, t("এডমিন", "Admin"), cash, cash - amount, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                        conn.commit()
                        conn.close()
                        subject = f"🏧 {t('টাকা উত্তোলনের নোটিশ', 'Withdrawal Notice')} - {SOMITI_NAME}"
                        sent = 0
                        conn = sqlite3.connect('somiti.db')
                        c = conn.cursor()
                        c.execute("SELECT email, name FROM members WHERE status = 'active' AND email IS NOT NULL AND email != ''")
                        members = c.fetchall()
                        conn.close()
                        for email, name in members:
                            msg = get_withdrawal_notification(name, f"{amount:,.0f}", description, date.strftime('%d %B %Y'), f"{cash:,.0f}", f"{cash - amount:,.0f}")
                            if send_email(email, subject, msg):
                                sent += 1
                        st.success(f"✅ {amount:,.0f} {t('টাকা উত্তোলন', 'Withdrawn')}! {sent} {t('জনকে ইমেইল', 'emailed')}.")
                        st.rerun()
                    else:
                        st.error(t("❌ বিবরণ দিতে হবে", "❌ Description required"))
                else:
                    st.error(t("❌ সঠিক পরিমাণ দিন", "❌ Invalid amount"))
        st.markdown("---")
        st.markdown(f"#### 📋 {t('উত্তোলন ইতিহাস', 'Withdrawal History')}")
        withdrawals = get_all_withdrawals()
        if withdrawals:
            df = pd.DataFrame(withdrawals, columns=["ID", t("তারিখ", "Date"), t("পরিমাণ", "Amount"), t("বিবরণ", "Description")])
            st.dataframe(df[[t("তারিখ", "Date"), t("পরিমাণ", "Amount"), t("বিবরণ", "Description")]], use_container_width=True, hide_index=True)
    
    elif f"📊 {t('রিপোর্ট', 'Reports')}" in menu:
        st.markdown(f"### 📊 {t('রিপোর্ট', 'Reports')}")
        tab1, tab2, tab3 = st.tabs([f"📈 {t('মাসিক', 'Monthly')}", f"⚠️ {t('বকেয়া', 'Due')}", f"🏧 {t('উত্তোলন', 'Withdrawals')}"])
        with tab1:
            data = get_monthly_report()
            if data:
                df = pd.DataFrame(data, columns=[t("মাস", "Month"), t("জমা", "Collection")])
                st.bar_chart(df.set_index(t("মাস", "Month")))
                st.dataframe(df, use_container_width=True, hide_index=True)
        with tab2:
            unpaid = get_unpaid_members()
            if unpaid:
                df = pd.DataFrame([{t("নাম", "Name"): m[1], t("মোবাইল", "Mobile"): m[2], t("কিস্তি", "Monthly"): f"{m[3]:,.0f}", t("জমা", "Savings"): f"{m[4]:,.0f}"} for m in unpaid])
                st.dataframe(df, use_container_width=True, hide_index=True)
                if st.button(f"📧 {t('বকেয়া রিমাইন্ডার', 'Due Reminder')}", type="primary"):
                    sent = 0
                    for m in unpaid:
                        if m[5]:
                            msg = f"""{t('প্রিয়', 'Dear')} {m[1]},

{BANGLA_MONTHS[datetime.now().month]} {t('মাসের কিস্তি', 'monthly installment')} ({m[3]:,.0f} {t('টাকা', 'Taka')}) {t('বকেয়া আছে', 'is due')}.
🙏 {t('আজই পরিশোধ করুন', 'Please pay today')}."""
                            if send_email(m[5], f"⚠️ {t('বকেয়া রিমাইন্ডার', 'Due Reminder')} - {SOMITI_NAME}", msg):
                                sent += 1
                    st.success(f"✅ {sent} {t('জনকে পাঠানো হয়েছে', 'sent')}!")
        with tab3:
            withdrawals = get_all_withdrawals()
            if withdrawals:
                df = pd.DataFrame(withdrawals, columns=["ID", t("তারিখ", "Date"), t("পরিমাণ", "Amount"), t("বিবরণ", "Description")])
                st.dataframe(df[[t("তারিখ", "Date"), t("পরিমাণ", "Amount"), t("বিবরণ", "Description")]], use_container_width=True, hide_index=True)
    
    elif f"📥 {t('পিডিএফ ডাউনলোড', 'PDF Download')}" in menu:
        st.markdown(f"### 📥 {t('পিডিএফ ডাউনলোড', 'PDF Download')}")
        report_type = st.selectbox(t("রিপোর্ট সিলেক্ট", "Select Report"), 
            [t("সদস্য তালিকা", "Member List"), t("সম্পূর্ণ লেনদেন", "All Transactions"), t("নির্দিষ্ট সদস্যের লেনদেন", "Specific Member")])
        if t("নির্দিষ্ট সদস্যের লেনদেন", "Specific Member") in report_type:
            members = get_all_members()
            if members:
                options = {f"{m[1]} ({m[0]})": m[0] for m in members}
                selected = st.selectbox(t("সদস্য নির্বাচন", "Select Member"), list(options.keys()))
                member_id = options[selected]
                if st.button(f"📥 {t('পিডিএফ ডাউনলোড', 'Download PDF')}", type="primary"):
                    pdf = generate_pdf_transactions(member_id)
                    st.download_button(f"📥 {t('ডাউনলোড', 'Download')}", pdf, f"{member_id}_transactions.pdf", mime="application/pdf")
        else:
            if st.button(f"📥 {t('পিডিএফ ডাউনলোড', 'Download PDF')}", type="primary"):
                if t("সদস্য তালিকা", "Member List") in report_type:
                    pdf = generate_pdf_member_list()
                    st.download_button(f"📥 {t('ডাউনলোড', 'Download')}", pdf, "member_list.pdf", mime="application/pdf")
                else:
                    pdf = generate_pdf_transactions()
                    st.download_button(f"📥 {t('ডাউনলোড', 'Download')}", pdf, "all_transactions.pdf", mime="application/pdf")
    
    elif f"📧 {t('ইমেইল টেস্ট', 'Email Test')}" in menu:
        st.markdown(f"### 📧 {t('ইমেইল টেস্ট', 'Email Test')}")
        test_email = st.text_input(t("টেস্ট ইমেইল", "Test Email"), placeholder="example@gmail.com")
        if st.button(f"📨 {t('টেস্ট পাঠান', 'Send Test')}", type="primary"):
            if send_email(test_email, f"🧪 {t('টেস্ট', 'Test')} - {SOMITI_NAME}", 
                         t("আপনার ইমেইল নোটিফিকেশন কাজ করছে!", "Your email notification is working!")):
                st.success(f"✅ {t('পাঠানো হয়েছে', 'Sent')}!")
            else:
                st.error(f"❌ {t('পাঠানো যায়নি', 'Failed')}")
    
    elif f"🎲 {t('লটারি', 'Lottery')}" in menu:
        st.markdown(f"### 🎲 {t('লটারি', 'Lottery')}")
        if st.button(f"🎲 {t('বিজয়ী নির্বাচন', 'Pick Winner')}", type="primary"):
            w = pick_lottery_winner()
            if w:
                st.balloons()
                st.success(f"🎉 {t('বিজয়ী', 'Winner')}: {w[1]} ({w[0]})")
                if w[4]:
                    send_email(w[4], f"🎉 {t('লটারি বিজয়ী', 'Lottery Winner')} - {SOMITI_NAME}", 
                              get_lottery_winner_email(w[1]))

def main():
    init_database()
    check_and_archive_old_data()
    if 'member_logged_in' not in st.session_state:
        st.session_state.member_logged_in = False
    if 'admin_logged_in' not in st.session_state:
        st.session_state.admin_logged_in = False
    if 'language' not in st.session_state:
        st.session_state.language = 'bn'
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
