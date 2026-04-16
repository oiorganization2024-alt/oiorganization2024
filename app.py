import streamlit as st
import pandas as pd
import sqlite3
import random
import string
import datetime
import hashlib
import smtplib
import io
import base64
import json
import calendar
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from reportlab.lib.pagesizes import A4, letter
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from contextlib import contextmanager

# ------------------------------
# পৃষ্ঠা কনফিগারেশন
# ------------------------------
st.set_page_config(
    page_title="ঐক্য উদ্যোগ সংস্থা",
    page_icon="🤝",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ------------------------------
# কাস্টম CSS (ডার্ক থিম)
# ------------------------------
def apply_custom_css():
    st.markdown("""
    <style>
    /* মূল ব্যাকগ্রাউন্ড */
    .stApp {
        background: linear-gradient(135deg, #0d1117 0%, #161b22 100%);
        color: #c9d1d9;
    }
    
    /* সাইডবার */
    section[data-testid="stSidebar"] {
        background-color: #161b22;
        border-right: 1px solid #30363d;
    }
    
    /* হেডার */
    .main-header {
        background: linear-gradient(90deg, #1a5276 0%, #2980b9 100%);
        padding: 1.2rem 2rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    }
    
    .main-header h1 {
        color: white;
        margin: 0;
        font-size: 2.2rem;
    }
    
    /* কার্ড */
    .card {
        background: #21262d;
        border: 1px solid #30363d;
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        transition: transform 0.2s;
    }
    
    .card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0,0,0,0.3);
    }
    
    /* KPI কার্ড */
    .kpi-card {
        background: #21262d;
        border-radius: 12px;
        padding: 1.2rem;
        text-align: center;
        border-left: 4px solid #58a6ff;
    }
    
    .kpi-value {
        font-size: 2.2rem;
        font-weight: bold;
        color: #58a6ff;
        margin: 0.2rem 0;
    }
    
    .kpi-label {
        font-size: 0.9rem;
        color: #8b949e;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    /* টোটাল ও ক্যাশ বক্স */
    .total-box {
        background: linear-gradient(135deg, #1e8449 0%, #27ae60 100%);
        padding: 1.2rem;
        border-radius: 12px;
        color: white;
        text-align: center;
    }
    
    .cash-box {
        background: linear-gradient(135deg, #d35400 0%, #e67e22 100%);
        padding: 1.2rem;
        border-radius: 12px;
        color: white;
        text-align: center;
    }
    
    /* বাটন */
    .stButton > button {
        background: linear-gradient(90deg, #238636 0%, #2ea043 100%);
        color: white;
        border: none;
        border-radius: 6px;
        padding: 0.5rem 1.2rem;
        font-weight: 500;
        transition: all 0.2s;
        width: 100%;
    }
    
    .stButton > button:hover {
        background: linear-gradient(90deg, #2ea043 0%, #3fb950 100%);
        transform: scale(1.02);
        box-shadow: 0 2px 8px rgba(46,160,67,0.3);
    }
    
    /* ডিলিট বাটন */
    button[key*="delete"], button[key*="confirm_yes"] {
        background: linear-gradient(90deg, #da3633 0%, #f85149 100%) !important;
    }
    
    /* এক্সপ্যান্ডার */
    .streamlit-expanderHeader {
        background-color: #21262d;
        border: 1px solid #30363d;
        border-radius: 8px;
    }
    
    /* ইনপুট ফিল্ড */
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input,
    .stSelectbox > div > div {
        background-color: #0d1117;
        color: white;
        border: 1px solid #30363d;
    }
    
    /* ট্যাব */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        background-color: #21262d;
        border-radius: 8px;
        padding: 8px 16px;
        color: #c9d1d9;
    }
    
    .stTabs [aria-selected="true"] {
        background-color: #238636;
        color: white;
    }
    
    /* মেট্রিক কার্ড */
    [data-testid="stMetric"] {
        background-color: #21262d;
        padding: 10px;
        border-radius: 8px;
        border: 1px solid #30363d;
    }
    
    [data-testid="stMetric"] label {
        color: #58a6ff !important;
    }
    
    [data-testid="stMetric"] div {
        color: white !important;
    }
    </style>
    """, unsafe_allow_html=True)

apply_custom_css()

# ------------------------------
# ভাষা সহায়ক ফাংশন
# ------------------------------
if 'language' not in st.session_state:
    st.session_state.language = 'bn'

def t(bn_text, en_text):
    """ভাষা অনুযায়ী টেক্সট রিটার্ন করে"""
    return bn_text if st.session_state.language == 'bn' else en_text

# ------------------------------
# ডাটাবেজ সংযোগ ও ইউটিলিটি
# ------------------------------
DB_PATH = "somiti.db"

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_database():
    """প্রয়োজনীয় টেবিল তৈরি ও মাইগ্রেশন"""
    with get_db() as conn:
        c = conn.cursor()
        
        # মেম্বার টেবিল
        c.execute('''
            CREATE TABLE IF NOT EXISTS members (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                phone TEXT UNIQUE NOT NULL,
                email TEXT,
                password TEXT NOT NULL,
                total_savings REAL DEFAULT 0,
                monthly_savings REAL DEFAULT 500,
                join_date TEXT NOT NULL,
                status TEXT DEFAULT 'active'
            )
        ''')
        
        # লেনদেন টেবিল
        c.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                member_id TEXT NOT NULL,
                amount REAL NOT NULL,
                transaction_type TEXT DEFAULT 'deposit',
                day INTEGER,
                month INTEGER,
                year INTEGER,
                month_name TEXT,
                month_name_en TEXT,
                full_date TEXT,
                full_date_en TEXT,
                date_iso TEXT,
                late_fee REAL DEFAULT 0,
                created_at TEXT,
                FOREIGN KEY (member_id) REFERENCES members(id)
            )
        ''')
        
        # খরচ টেবিল
        c.execute('''
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                description TEXT NOT NULL,
                amount REAL NOT NULL,
                date TEXT NOT NULL,
                category TEXT,
                created_at TEXT
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
                created_at TEXT
            )
        ''')
        
        # ফান্ড লেনদেন টেবিল
        c.execute('''
            CREATE TABLE IF NOT EXISTS fund_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,
                amount REAL NOT NULL,
                description TEXT,
                date TEXT NOT NULL,
                previous_balance REAL,
                current_balance REAL,
                created_at TEXT
            )
        ''')
        
        # সেটিংস টেবিল
        c.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        
        # ডিফল্ট সেটিংস
        c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('start_date', ?)",
                  (datetime.date.today().isoformat(),))
        
        conn.commit()

def execute_query(query, params=(), fetch=False):
    with get_db() as conn:
        c = conn.cursor()
        c.execute(query, params)
        if fetch:
            return c.fetchall()
        conn.commit()

def get_setting(key, default=None):
    row = execute_query("SELECT value FROM settings WHERE key=?", (key,), fetch=True)
    return row[0]['value'] if row else default

def set_setting(key, value):
    execute_query("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))

# ------------------------------
# অথেন্টিকেশন ও ইউটিলিটি
# ------------------------------
def generate_member_id():
    rows = execute_query("SELECT COUNT(*) as cnt FROM members", fetch=True)
    count = rows[0]['cnt']
    return str(10001 + count)

def generate_password(length=6):
    return ''.join(random.choices(string.digits, k=length))

def hash_password(pwd):
    return hashlib.sha256(pwd.encode()).hexdigest()

def verify_password(pwd, hashed):
    return hash_password(pwd) == hashed

def get_cash_balance():
    total_savings = execute_query("SELECT SUM(total_savings) FROM members WHERE status='active'", fetch=True)[0][0] or 0
    total_expenses = execute_query("SELECT SUM(amount) FROM expenses", fetch=True)[0][0] or 0
    total_withdrawals = execute_query("SELECT SUM(amount) FROM withdrawals", fetch=True)[0][0] or 0
    fund_deposits = execute_query("SELECT SUM(amount) FROM fund_transactions WHERE type='deposit'", fetch=True)[0][0] or 0
    fund_withdrawals = execute_query("SELECT SUM(amount) FROM fund_transactions WHERE type='withdrawal'", fetch=True)[0][0] or 0
    return total_savings - total_expenses - total_withdrawals + fund_deposits - fund_withdrawals

def get_paid_members(month, year):
    rows = execute_query("""
        SELECT DISTINCT member_id FROM transactions
        WHERE month=? AND year=?
    """, (month, year), fetch=True)
    return [r['member_id'] for r in rows]

def get_unpaid_members(month, year):
    all_active = execute_query("SELECT id FROM members WHERE status='active'", fetch=True)
    paid = get_paid_members(month, year)
    return [r['id'] for r in all_active if r['id'] not in paid]

# ------------------------------
# ইমেইল ফাংশন
# ------------------------------
def send_email(to_email, subject, body):
    try:
        smtp_user = st.secrets["email"]["smtp_user"]
        smtp_pass = st.secrets["email"]["smtp_pass"]
    except:
        return False
    
    msg = MIMEMultipart()
    msg['From'] = smtp_user
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))
    
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        return True
    except:
        return False

# ------------------------------
# এডমিন লগইন
# ------------------------------
ADMIN_MOBILE = "01766222373"
ADMIN_PASSWORD_HASH = hash_password("admin123")

def admin_login(mobile, password):
    if mobile == ADMIN_MOBILE and verify_password(password, ADMIN_PASSWORD_HASH):
        st.session_state.logged_in = True
        st.session_state.user_type = 'admin'
        st.session_state.user_data = {'mobile': mobile}
        return True
    return False

def member_login(email, password, member_id):
    rows = execute_query("SELECT * FROM members WHERE id=? AND email=? AND status='active'",
                         (member_id, email), fetch=True)
    if rows and verify_password(password, rows[0]['password']):
        st.session_state.logged_in = True
        st.session_state.user_type = 'member'
        st.session_state.user_data = dict(rows[0])
        return True
    return False

# ------------------------------
# এডমিন ফাংশন
# ------------------------------
def admin_dashboard():
    st.markdown('<div class="main-header"><h1>🤝 ঐক্য উদ্যোগ সংস্থা - এডমিন প্যানেল</h1></div>', unsafe_allow_html=True)
    
    # KPI কার্ড
    total_members = execute_query("SELECT COUNT(*) FROM members WHERE status='active'", fetch=True)[0][0]
    total_savings = execute_query("SELECT SUM(total_savings) FROM members WHERE status='active'", fetch=True)[0][0] or 0
    current_month = datetime.date.today().month
    current_year = datetime.date.today().year
    paid_count = len(get_paid_members(current_month, current_year))
    unpaid_count = total_members - paid_count
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f'<div class="kpi-card"><div class="kpi-value">{total_members}</div><div class="kpi-label">{t("মোট সদস্য", "Total Members")}</div></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="kpi-card"><div class="kpi-value">৳{total_savings:,.0f}</div><div class="kpi-label">{t("মোট জমা", "Total Savings")}</div></div>', unsafe_allow_html=True)
    with col3:
        this_month_collection = execute_query("""
            SELECT SUM(amount) FROM transactions 
            WHERE month=? AND year=?
        """, (current_month, current_year), fetch=True)[0][0] or 0
        st.markdown(f'<div class="kpi-card"><div class="kpi-value">৳{this_month_collection:,.0f}</div><div class="kpi-label">{t("এই মাসের কালেকশন", "This Month Collection")}</div></div>', unsafe_allow_html=True)
    with col4:
        st.markdown(f'<div class="kpi-card"><div class="kpi-value">{unpaid_count}</div><div class="kpi-label">{t("বকেয়াদার সংখ্যা", "Defaulters")}</div></div>', unsafe_allow_html=True)
    
    # টোটাল ও ক্যাশ বক্স
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f'<div class="total-box"><h3>{t("মোট তহবিল", "Total Fund")}</h3><h2>৳{total_savings:,.0f}</h2></div>', unsafe_allow_html=True)
    with col2:
        cash = get_cash_balance()
        st.markdown(f'<div class="cash-box"><h3>{t("বর্তমান ক্যাশ", "Current Cash")}</h3><h2>৳{cash:,.0f}</h2></div>', unsafe_allow_html=True)
    
    if st.button(t("🔄 রিফ্রেশ করুন", "🔄 Refresh Data")):
        st.rerun()

def new_member_registration():
    st.subheader(t("➕ নতুন সদস্য নিবন্ধন", "➕ New Member Registration"))
    
    with st.form("new_member_form"):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input(t("নাম *", "Name *"), placeholder=t("পূর্ণ নাম লিখুন", "Enter full name"))
            phone = st.text_input(t("মোবাইল *", "Mobile *"), placeholder="01XXXXXXXXX")
        with col2:
            email = st.text_input(t("ইমেইল", "Email"), placeholder="example@email.com")
            monthly = st.number_input(t("মাসিক কিস্তি (টাকা)", "Monthly Installment (Tk)"), value=500, min_value=100, step=50)
        
        submitted = st.form_submit_button(t("✅ নিবন্ধন করুন", "✅ Register"), use_container_width=True)
        
        if submitted:
            if not name or not phone:
                st.error(t("❌ নাম ও মোবাইল আবশ্যক", "❌ Name and mobile are required"))
            elif len(phone) != 11 or not phone.isdigit():
                st.error(t("❌ মোবাইল নম্বর ১১ ডিজিটের হতে হবে", "❌ Mobile number must be 11 digits"))
            else:
                existing = execute_query("SELECT id FROM members WHERE phone=?", (phone,), fetch=True)
                if existing:
                    st.error(t("❌ এই মোবাইল নম্বরটি ইতিমধ্যে নিবন্ধিত", "❌ This mobile number is already registered"))
                else:
                    member_id = generate_member_id()
                    password = generate_password()
                    join_date = datetime.date.today().isoformat()
                    
                    execute_query("""
                        INSERT INTO members (id, name, phone, email, password, monthly_savings, join_date)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (member_id, name, phone, email, hash_password(password), monthly, join_date))
                    
                    st.success(t(f"✅ সদস্য তৈরি হয়েছে!\n\n📋 আইডি: {member_id}\n🔑 পাসওয়ার্ড: {password}", 
                                 f"✅ Member created!\n\n📋 ID: {member_id}\n🔑 Password: {password}"))
                    st.balloons()
                    time.sleep(2)
                    st.rerun()

def member_management():
    st.subheader(t("✏️ সদস্য ব্যবস্থাপনা", "✏️ Member Management"))
    
    # ফিল্টার
    filter_status = st.selectbox(t("স্ট্যাটাস ফিল্টার", "Filter by Status"), 
                                 [t("সব", "All"), t("সক্রিয়", "Active"), t("নিষ্ক্রিয়", "Inactive")])
    
    query = "SELECT * FROM members"
    if filter_status == t("সক্রিয়", "Active"):
        query += " WHERE status='active'"
    elif filter_status == t("নিষ্ক্রিয়", "Inactive"):
        query += " WHERE status='inactive'"
    query += " ORDER BY join_date DESC"
    
    members = execute_query(query, fetch=True)
    
    if not members:
        st.info(t("কোনো সদস্য পাওয়া যায়নি", "No members found"))
        return
    
    for m in members:
        status_color = "🟢" if m['status'] == 'active' else "🔴"
        with st.expander(f"{status_color} {m['name']} ({m['id']}) - {m['phone']}"):
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**{t('ইমেইল', 'Email')}:** {m['email'] or '-'}")
                st.write(f"**{t('মোট জমা', 'Total Savings')}:** ৳{m['total_savings']:,.0f}")
                st.write(f"**{t('মাসিক কিস্তি', 'Monthly')}:** ৳{m['monthly_savings']:,.0f}")
                st.write(f"**{t('যোগদানের তারিখ', 'Join Date')}:** {m['join_date']}")
            with col2:
                with st.form(f"edit_member_{m['id']}"):
                    new_name = st.text_input(t("নাম", "Name"), value=m['name'], key=f"name_{m['id']}")
                    new_phone = st.text_input(t("মোবাইল", "Mobile"), value=m['phone'], key=f"phone_{m['id']}")
                    new_email = st.text_input(t("ইমেইল", "Email"), value=m['email'] or "", key=f"email_{m['id']}")
                    new_monthly = st.number_input(t("মাসিক কিস্তি", "Monthly"), value=float(m['monthly_savings']), step=50.0, key=f"monthly_{m['id']}")
                    
                    if st.form_submit_button(t("💾 আপডেট", "💾 Update")):
                        execute_query("""
                            UPDATE members SET name=?, phone=?, email=?, monthly_savings=?
                            WHERE id=?
                        """, (new_name, new_phone, new_email, new_monthly, m['id']))
                        st.success(t("✅ আপডেট সফল", "✅ Updated successfully"))
                        time.sleep(1)
                        st.rerun()
            
            c1, c2, c3 = st.columns(3)
            with c1:
                if st.button(t("🔑 পাসওয়ার্ড রিসেট", "🔑 Reset Password"), key=f"reset_{m['id']}", use_container_width=True):
                    new_pwd = generate_password()
                    execute_query("UPDATE members SET password=? WHERE id=?", (hash_password(new_pwd), m['id']))
                    st.success(f"{t('নতুন পাসওয়ার্ড:', 'New Password:')} {new_pwd}")
                    st.info(t("পাসওয়ার্ডটি কপি করে সংরক্ষণ করুন", "Copy and save this password"))
            with c2:
                new_status = 'inactive' if m['status'] == 'active' else 'active'
                btn_text = t("🔴 নিষ্ক্রিয় করুন" if m['status']=='active' else "🟢 সক্রিয় করুন", 
                            "🔴 Deactivate" if m['status']=='active' else "🟢 Activate")
                if st.button(btn_text, key=f"toggle_{m['id']}", use_container_width=True):
                    execute_query("UPDATE members SET status=? WHERE id=?", (new_status, m['id']))
                    st.rerun()
            with c3:
                if st.button(t("🗑️ মুছে ফেলুন", "🗑️ Delete"), key=f"delete_{m['id']}", use_container_width=True):
                    st.session_state[f"confirm_delete_member_{m['id']}"] = True
            
            if st.session_state.get(f"confirm_delete_member_{m['id']}", False):
                st.error(t("⚠️ সতর্কতা: এই সদস্যকে মুছে ফেললে তার সব লেনদেনও মুছে যাবে!", 
                          "⚠️ Warning: Deleting this member will also delete all their transactions!"))
                col_x, col_y = st.columns(2)
                with col_x:
                    if st.button(t("✅ হ্যাঁ, মুছে ফেলুন", "✅ Yes, Delete"), key=f"confirm_yes_member_{m['id']}", use_container_width=True):
                        execute_query("DELETE FROM transactions WHERE member_id=?", (m['id'],))
                        execute_query("DELETE FROM members WHERE id=?", (m['id'],))
                        st.session_state[f"confirm_delete_member_{m['id']}"] = False
                        st.success(t("✅ সদস্য মুছে ফেলা হয়েছে", "✅ Member deleted successfully"))
                        time.sleep(1)
                        st.rerun()
                with col_y:
                    if st.button(t("❌ বাতিল", "❌ Cancel"), key=f"confirm_no_member_{m['id']}", use_container_width=True):
                        st.session_state[f"confirm_delete_member_{m['id']}"] = False
                        st.rerun()

def deposit_management():
    st.subheader(t("💵 টাকা জমা", "💵 Deposit"))
    
    today = datetime.date.today()
    current_month = today.month
    current_year = today.year
    
    # মাস ও বছর সিলেক্টর
    col1, col2 = st.columns(2)
    with col1:
        selected_month = st.selectbox(t("মাস", "Month"), range(1, 13), 
                                      index=current_month-1,
                                      format_func=lambda x: calendar.month_name[x])
    with col2:
        selected_year = st.selectbox(t("বছর", "Year"), range(2020, 2031), 
                                     index=current_year-2020)
    
    tab1, tab2 = st.tabs([t("✅ জমা দিয়েছে", "✅ Paid"), t("⏳ জমা দেয়নি", "⏳ Unpaid")])
    
    with tab1:
        paid_ids = get_paid_members(selected_month, selected_year)
        if not paid_ids:
            st.info(t("এই মাসে কেউ জমা দেয়নি", "No payments this month"))
        else:
            total_paid_amount = 0
            for mid in paid_ids:
                m = execute_query("SELECT * FROM members WHERE id=?", (mid,), fetch=True)[0]
                tx = execute_query("""
                    SELECT SUM(amount + late_fee) as total FROM transactions 
                    WHERE member_id=? AND month=? AND year=?
                """, (mid, selected_month, selected_year), fetch=True)[0]
                amount = tx['total'] or 0
                total_paid_amount += amount
                st.success(f"✅ {m['name']} ({m['id']}) - ৳{amount:,.0f}")
            
            st.metric(t("মোট জমা", "Total Deposited"), f"৳{total_paid_amount:,.0f}")
    
    with tab2:
        unpaid_ids = get_unpaid_members(selected_month, selected_year)
        if not unpaid_ids:
            st.success(t("🎉 সবাই জমা দিয়েছে!", "🎉 Everyone has paid!"))
            st.balloons()
        else:
            st.info(f"{t('মোট বকেয়াদার সংখ্যা:', 'Total Defaulters:')} {len(unpaid_ids)}")
            
            for mid in unpaid_ids:
                m = execute_query("SELECT * FROM members WHERE id=?", (mid,), fetch=True)[0]
                with st.expander(f"⏳ {m['name']} ({m['id']}) - {t('মাসিক', 'Monthly')} ৳{m['monthly_savings']:,.0f}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        pay_date = st.date_input(t("তারিখ", "Date"), value=today, key=f"date_{mid}")
                        months_count = st.number_input(t("কত মাসের জমা", "Months"), min_value=1, max_value=12, value=1, key=f"months_{mid}")
                    with col2:
                        late_fee = st.number_input(t("লেট ফি (টাকা)", "Late Fee (Tk)"), min_value=0.0, value=0.0, step=10.0, key=f"fee_{mid}")
                    
                    total_amount = m['monthly_savings'] * months_count
                    st.info(f"{t('মোট জমা হবে:', 'Total Deposit:')} ৳{total_amount:,.0f} + {t('লেট ফি:', 'Late Fee:')} ৳{late_fee:,.0f} = ৳{total_amount + late_fee:,.0f}")
                    
                    if st.button(t("💰 জমা নিন", "💰 Deposit"), key=f"deposit_{mid}", use_container_width=True):
                        for i in range(months_count):
                            tx_date = pay_date - datetime.timedelta(days=30*i)
                            tx_month = tx_date.month
                            tx_year = tx_date.year
                            
                            exists = execute_query("""
                                SELECT id FROM transactions
                                WHERE member_id=? AND month=? AND year=?
                            """, (mid, tx_month, tx_year), fetch=True)
                            
                            if not exists:
                                execute_query("""
                                    INSERT INTO transactions
                                    (member_id, amount, day, month, year, month_name, month_name_en, full_date, full_date_en, date_iso, late_fee, created_at)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                """, (
                                    mid, m['monthly_savings'], tx_date.day, tx_month, tx_year,
                                    calendar.month_name[tx_month], calendar.month_name[tx_month],
                                    tx_date.strftime('%d/%m/%Y'), tx_date.strftime('%d/%m/%Y'),
                                    tx_date.isoformat(),
                                    late_fee if i == 0 else 0,
                                    datetime.datetime.now().isoformat()
                                ))
                        
                        execute_query("UPDATE members SET total_savings = total_savings + ? WHERE id=?", (total_amount + late_fee, mid))
                        st.success(t(f"✅ জমা সফল! মোট ৳{total_amount + late_fee:,.0f}", f"✅ Deposit successful! Total ৳{total_amount + late_fee:,.0f}"))
                        st.balloons()
                        time.sleep(2)
                        st.rerun()

def member_links():
    st.subheader(t("🔗 সদস্য লিংক", "🔗 Member Links"))
    
    members = execute_query("SELECT id, name, email, password, phone FROM members WHERE status='active' ORDER BY name", fetch=True)
    
    if not members:
        st.info(t("কোনো সক্রিয় সদস্য নেই", "No active members found"))
        return
    
    # বেস URL
    base_url = st.text_input(t("অ্যাপের URL", "App URL"), value="http://localhost:8501", 
                             help=t("আপনার অ্যাপের সম্পূর্ণ URL লিখুন", "Enter your app's full URL"))
    
    st.divider()
    
    for m in members:
        with st.container():
            cols = st.columns([2.5, 3, 1, 1, 1])
            with cols[0]:
                st.write(f"**{m['name']}**")
                st.caption(f"{m['id']}")
            with cols[1]:
                link = f"{base_url}?id={m['id']}"
                st.code(link, language=None)
            with cols[2]:
                if st.button("📋", key=f"copy_link_{m['id']}", help=t("লিংক কপি করুন", "Copy Link")):
                    st.write(f'<span id="copy_{m["id"]}">{link}</span>', unsafe_allow_html=True)
                    js_code = f"""
                    <script>
                        navigator.clipboard.writeText("{link}");
                    </script>
                    """
                    st.components.v1.html(js_code, height=0)
                    st.success("✅")
            with cols[3]:
                if st.button("🔑", key=f"copy_pwd_{m['id']}", help=t("পাসওয়ার্ড কপি করুন", "Copy Password")):
                    st.write(f'<span id="pwd_{m["id"]}">{m["password"]}</span>', unsafe_allow_html=True)
                    js_code = f"""
                    <script>
                        navigator.clipboard.writeText("{m['password']}");
                    </script>
                    """
                    st.components.v1.html(js_code, height=0)
                    st.success("✅")
            with cols[4]:
                if m['email'] and st.button("📧", key=f"email_{m['id']}", help=t("ইমেইল পাঠান", "Send Email")):
                    subject = "ঐক্য উদ্যোগ সংস্থা - আপনার লগইন তথ্য"
                    body = f"""প্রিয় {m['name']},

আপনার ঐক্য উদ্যোগ সংস্থা অ্যাকাউন্টের লগইন তথ্য:

সদস্য আইডি: {m['id']}
পাসওয়ার্ড: {m['password']}
লগইন লিংক: {link}

ধন্যবাদ,
ঐক্য উদ্যোগ সংস্থা"""
                    
                    if send_email(m['email'], subject, body):
                        st.success(t("ইমেইল পাঠানো হয়েছে", "Email sent"))
                    else:
                        st.error(t("ইমেইল পাঠানো যায়নি", "Email failed"))
        
        st.divider()

def fund_management():
    st.subheader(t("🏧 ফান্ড ব্যবস্থাপনা", "🏧 Fund Management"))
    
    cash = get_cash_balance()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(t("বর্তমান ক্যাশ ব্যালেন্স", "Current Cash Balance"), f"৳{cash:,.0f}")
    with col2:
        total_fund_deposit = execute_query("SELECT SUM(amount) FROM fund_transactions WHERE type='deposit'", fetch=True)[0][0] or 0
        st.metric(t("মোট ফান্ড জমা", "Total Fund Deposit"), f"৳{total_fund_deposit:,.0f}")
    with col3:
        total_fund_withdrawal = execute_query("SELECT SUM(amount) FROM fund_transactions WHERE type='withdrawal'", fetch=True)[0][0] or 0
        st.metric(t("মোট ফান্ড উত্তোলন", "Total Fund Withdrawal"), f"৳{total_fund_withdrawal:,.0f}")
    
    st.divider()
    
    tab1, tab2, tab3 = st.tabs([t("💰 জমা", "💰 Deposit"), t("💸 উত্তোলন", "💸 Withdrawal"), t("📜 ইতিহাস", "📜 History")])
    
    with tab1:
        with st.form("fund_deposit"):
            col1, col2 = st.columns(2)
            with col1:
                amount = st.number_input(t("পরিমাণ (টাকা)", "Amount (Tk)"), min_value=0.0, step=100.0)
            with col2:
                dep_date = st.date_input(t("তারিখ", "Date"), value=datetime.date.today())
            
            desc = st.text_input(t("বিবরণ", "Description"), placeholder=t("ফান্ড জমার বিবরণ", "Fund deposit description"))
            
            if st.form_submit_button(t("💰 জমা করুন", "💰 Deposit"), use_container_width=True):
                if amount <= 0:
                    st.error(t("❌ পরিমাণ ০ এর বেশি হতে হবে", "❌ Amount must be greater than 0"))
                else:
                    prev = cash
                    new_bal = prev + amount
                    execute_query("""
                        INSERT INTO fund_transactions (type, amount, description, date, previous_balance, current_balance, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, ('deposit', amount, desc, dep_date.isoformat(), prev, new_bal, datetime.datetime.now().isoformat()))
                    st.success(t(f"✅ ফান্ড জমা হয়েছে! নতুন ব্যালেন্স: ৳{new_bal:,.0f}", 
                                f"✅ Fund deposited! New balance: ৳{new_bal:,.0f}"))
                    st.balloons()
                    time.sleep(1)
                    st.rerun()
    
    with tab2:
        with st.form("fund_withdraw"):
            col1, col2 = st.columns(2)
            with col1:
                amount = st.number_input(t("পরিমাণ (টাকা)", "Amount (Tk)"), min_value=0.0, step=100.0, key="withdraw_amount")
            with col2:
                with_date = st.date_input(t("তারিখ", "Date"), value=datetime.date.today(), key="withdraw_date")
            
            desc = st.text_input(t("বিবরণ", "Description"), placeholder=t("উত্তোলনের কারণ", "Reason for withdrawal"), key="withdraw_desc")
            
            if st.form_submit_button(t("💸 উত্তোলন করুন", "💸 Withdraw"), use_container_width=True):
                if amount <= 0:
                    st.error(t("❌ পরিমাণ ০ এর বেশি হতে হবে", "❌ Amount must be greater than 0"))
                elif amount > cash:
                    st.error(t(f"❌ পর্যাপ্ত ব্যালেন্স নেই। বর্তমান ব্যালেন্স: ৳{cash:,.0f}", 
                              f"❌ Insufficient balance. Current balance: ৳{cash:,.0f}"))
                else:
                    prev = cash
                    new_bal = prev - amount
                    execute_query("""
                        INSERT INTO fund_transactions (type, amount, description, date, previous_balance, current_balance, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, ('withdrawal', amount, desc, with_date.isoformat(), prev, new_bal, datetime.datetime.now().isoformat()))
                    st.success(t(f"✅ উত্তোলন সম্পন্ন! নতুন ব্যালেন্স: ৳{new_bal:,.0f}", 
                                f"✅ Withdrawn! New balance: ৳{new_bal:,.0f}"))
                    time.sleep(1)
                    st.rerun()
    
    with tab3:
        history = execute_query("""
            SELECT * FROM fund_transactions 
            ORDER BY date DESC, id DESC
            LIMIT 50
        """, fetch=True)
        
        if history:
            st.subheader(t("সাম্প্রতিক ফান্ড লেনদেন", "Recent Fund Transactions"))
            
            df_data = []
            for h in history:
                df_data.append({
                    t('তারিখ', 'Date'): h['date'],
                    t('ধরন', 'Type'): t('জমা', 'Deposit') if h['type'] == 'deposit' else t('উত্তোলন', 'Withdrawal'),
                    t('পরিমাণ', 'Amount'): f"৳{h['amount']:,.0f}",
                    t('বিবরণ', 'Description'): h['description'] or '-',
                    t('ব্যালেন্স', 'Balance'): f"৳{h['current_balance']:,.0f}"
                })
            
            df = pd.DataFrame(df_data)
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info(t("কোনো ফান্ড লেনদেন নেই", "No fund transactions found"))

def reports():
    st.subheader(t("📊 রিপোর্ট", "📊 Reports"))
    
    # মাসিক কালেকশন চার্ট
    st.subheader(t("📈 মাসিক কালেকশন", "📈 Monthly Collection"))
    
    tx_data = execute_query("""
        SELECT year, month, SUM(amount + late_fee) as total 
        FROM transactions 
        GROUP BY year, month 
        ORDER BY year, month
    """, fetch=True)
    
    if tx_data:
        df = pd.DataFrame([dict(r) for r in tx_data])
        df['period'] = df['year'].astype(str) + '-' + df['month'].astype(str).str.zfill(2)
        df['month_name'] = df['month'].apply(lambda x: calendar.month_name[x])
        df['label'] = df['month_name'] + ' ' + df['year'].astype(str)
        
        st.bar_chart(df.set_index('label')['total'], use_container_width=True)
        
        # টেবিল
        st.subheader(t("📋 মাসিক কালেকশন টেবিল", "📋 Monthly Collection Table"))
        display_df = df[['label', 'total']].copy()
        display_df.columns = [t('মাস-বছর', 'Month-Year'), t('মোট কালেকশন', 'Total Collection')]
        display_df[t('মোট কালেকশন', 'Total Collection')] = display_df[t('মোট কালেকশন', 'Total Collection')].apply(lambda x: f"৳{x:,.0f}")
        st.dataframe(display_df, use_container_width=True, hide_index=True)
    else:
        st.info(t("কোনো লেনদেন ডাটা নেই", "No transaction data available"))
    
    st.divider()
    
    # বকেয়াদার তালিকা
    st.subheader(t("⏳ বর্তমান মাসের বকেয়াদার তালিকা", "⏳ Current Month Defaulters"))
    
    today = datetime.date.today()
    unpaid = get_unpaid_members(today.month, today.year)
    
    if unpaid:
        defaulter_data = []
        for mid in unpaid:
            m = execute_query("SELECT name, phone, monthly_savings, total_savings FROM members WHERE id=?", (mid,), fetch=True)[0]
            defaulter_data.append({
                t('নাম', 'Name'): m['name'],
                t('আইডি', 'ID'): mid,
                t('মোবাইল', 'Mobile'): m['phone'],
                t('মাসিক কিস্তি', 'Monthly'): f"৳{m['monthly_savings']:,.0f}",
                t('মোট জমা', 'Total'): f"৳{m['total_savings']:,.0f}"
            })
        
        df = pd.DataFrame(defaulter_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.metric(t("মোট বকেয়াদার", "Total Defaulters"), len(unpaid))
    else:
        st.success(t("✅ সবাই জমা দিয়েছে!", "✅ Everyone has paid!"))
    
    st.divider()
    
    # সদস্যদের মোট জমার তালিকা
    st.subheader(t("👥 সদস্যদের জমার তালিকা", "👥 Members Savings List"))
    
    members = execute_query("""
        SELECT id, name, phone, total_savings, monthly_savings, join_date 
        FROM members 
        WHERE status='active' 
        ORDER BY total_savings DESC
    """, fetch=True)
    
    if members:
        member_data = []
        for m in members:
            member_data.append({
                t('নাম', 'Name'): m['name'],
                t('আইডি', 'ID'): m['id'],
                t('মোবাইল', 'Mobile'): m['phone'],
                t('মাসিক', 'Monthly'): f"৳{m['monthly_savings']:,.0f}",
                t('মোট জমা', 'Total'): f"৳{m['total_savings']:,.0f}",
                t('যোগদান', 'Join Date'): m['join_date']
            })
        
        df = pd.DataFrame(member_data)
        st.dataframe(df, use_container_width=True, hide_index=True)

def pdf_download():
    st.subheader(t("📥 পিডিএফ ডাউনলোড", "📥 PDF Download"))
    
    report_type = st.selectbox(
        t("রিপোর্ট টাইপ নির্বাচন করুন", "Select Report Type"),
        [t("📋 সদস্য তালিকা", "📋 Member List"),
         t("💰 সম্পূর্ণ লেনদেন", "💰 All Transactions"),
         t("👤 নির্দিষ্ট সদস্যের লেনদেন", "👤 Specific Member Transactions"),
         t("🏧 ফান্ড লেনদেন", "🏧 Fund Transactions")]
    )
    
    member_id = None
    if "নির্দিষ্ট" in report_type or "Specific" in report_type:
        members = execute_query("SELECT id, name FROM members ORDER BY name", fetch=True)
        if members:
            member_id = st.selectbox(
                t("সদস্য নির্বাচন করুন", "Select Member"),
                [m['id'] for m in members],
                format_func=lambda x: f"{x} - {next(m['name'] for m in members if m['id']==x)}"
            )
        else:
            st.warning(t("কোনো সদস্য নেই", "No members found"))
            return
    
    # তারিখ ফিল্টার
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input(t("শুরুর তারিখ", "Start Date"), 
                                   value=datetime.date.today() - datetime.timedelta(days=30))
    with col2:
        end_date = st.date_input(t("শেষ তারিখ", "End Date"), 
                                 value=datetime.date.today())
    
    if st.button(t("📄 পিডিএফ জেনারেট করুন", "📄 Generate PDF"), use_container_width=True):
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, 
                                topMargin=0.5*inch, bottomMargin=0.5*inch,
                                leftMargin=0.5*inch, rightMargin=0.5*inch)
        elements = []
        styles = getSampleStyleSheet()
        
        # টাইটেল
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=20,
            textColor=colors.HexColor('#1a5276'),
            spaceAfter=20,
            alignment=1
        )
        
        elements.append(Paragraph("ঐক্য উদ্যোগ সংস্থা", title_style))
        elements.append(Spacer(1, 10))
        
        # রিপোর্ট সাবটাইটেল
        subtitle_style = ParagraphStyle(
            'Subtitle',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#2980b9'),
            spaceAfter=20,
            alignment=1
        )
        
        report_names = {
            t("📋 সদস্য তালিকা", "📋 Member List"): "সদস্য তালিকা",
            t("💰 সম্পূর্ণ লেনদেন", "💰 All Transactions"): "সম্পূর্ণ লেনদেন রিপোর্ট",
            t("👤 নির্দিষ্ট সদস্যের লেনদেন", "👤 Specific Member Transactions"): "সদস্যের লেনদেন রিপোর্ট",
            t("🏧 ফান্ড লেনদেন", "🏧 Fund Transactions"): "ফান্ড লেনদেন রিপোর্ট"
        }
        
        elements.append(Paragraph(report_names.get(report_type, "রিপোর্ট"), subtitle_style))
        elements.append(Paragraph(f"তারিখ: {start_date} থেকে {end_date}", styles['Normal']))
        elements.append(Spacer(1, 20))
        
        # রিপোর্ট অনুযায়ী ডাটা
        if report_type == t("📋 সদস্য তালিকা", "📋 Member List"):
            members = execute_query("""
                SELECT id, name, phone, email, total_savings, monthly_savings, join_date, status 
                FROM members 
                ORDER BY join_date DESC
            """, fetch=True)
            
            data = [['আইডি', 'নাম', 'মোবাইল', 'ইমেইল', 'মোট জমা', 'মাসিক', 'যোগদান', 'স্ট্যাটাস']]
            for m in members:
                data.append([
                    m['id'], m['name'], m['phone'], m['email'] or '-',
                    f"৳{m['total_savings']:.0f}", f"৳{m['monthly_savings']:.0f}",
                    m['join_date'], m['status']
                ])
            
            table = Table(data, repeatRows=1)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a5276')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
            ]))
            elements.append(table)
            
        elif report_type == t("💰 সম্পূর্ণ লেনদেন", "💰 All Transactions"):
            tx = execute_query("""
                SELECT m.name, m.id, t.full_date, t.amount, t.late_fee, (t.amount + t.late_fee) as total
                FROM transactions t
                JOIN members m ON t.member_id = m.id
                WHERE t.date_iso BETWEEN ? AND ?
                ORDER BY t.date_iso DESC
            """, (start_date.isoformat(), end_date.isoformat()), fetch=True)
            
            data = [['সদস্য', 'আইডি', 'তারিখ', 'পরিমাণ', 'লেট ফি', 'মোট']]
            total_sum = 0
            for row in tx:
                data.append([row['name'], row['id'], row['full_date'], 
                            f"৳{row['amount']:.0f}", f"৳{row['late_fee']:.0f}", f"৳{row['total']:.0f}"])
                total_sum += row['total']
            
            data.append(['', '', '', '', 'সর্বমোট:', f"৳{total_sum:.0f}"])
            
            table = Table(data, repeatRows=1)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a5276')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('GRID', (0, 0), (-1, -2), 0.5, colors.grey),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('SPAN', (0, -1), (3, -1)),
                ('FONTNAME', (4, -1), (5, -1), 'Helvetica-Bold'),
            ]))
            elements.append(table)
            
        elif report_type == t("👤 নির্দিষ্ট সদস্যের লেনদেন", "👤 Specific Member Transactions") and member_id:
            member = execute_query("SELECT name, id, total_savings FROM members WHERE id=?", (member_id,), fetch=True)[0]
            elements.append(Paragraph(f"সদস্য: {member['name']} ({member['id']})", styles['Heading3']))
            elements.append(Paragraph(f"মোট জমা: ৳{member['total_savings']:.0f}", styles['Normal']))
            elements.append(Spacer(1, 10))
            
            tx = execute_query("""
                SELECT full_date, amount, late_fee, (amount + late_fee) as total
                FROM transactions WHERE member_id=? AND date_iso BETWEEN ? AND ?
                ORDER BY date_iso
            """, (member_id, start_date.isoformat(), end_date.isoformat()), fetch=True)
            
            data = [['তারিখ', 'পরিমাণ', 'লেট ফি', 'মোট']]
            total_sum = 0
            for row in tx:
                data.append([row['full_date'], f"৳{row['amount']:.0f}", 
                            f"৳{row['late_fee']:.0f}", f"৳{row['total']:.0f}"])
                total_sum += row['total']
            
            data.append(['', '', 'সর্বমোট:', f"৳{total_sum:.0f}"])
            
            table = Table(data, repeatRows=1)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a5276')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -2), 0.5, colors.grey),
                ('SPAN', (0, -1), (1, -1)),
                ('FONTNAME', (2, -1), (3, -1), 'Helvetica-Bold'),
            ]))
            elements.append(table)
            
        elif report_type == t("🏧 ফান্ড লেনদেন", "🏧 Fund Transactions"):
            fund_tx = execute_query("""
                SELECT date, type, amount, description, current_balance 
                FROM fund_transactions 
                WHERE date BETWEEN ? AND ?
                ORDER BY date DESC
            """, (start_date.isoformat(), end_date.isoformat()), fetch=True)
            
            data = [['তারিখ', 'ধরন', 'পরিমাণ', 'বিবরণ', 'ব্যালেন্স']]
            for ft in fund_tx:
                data.append([
                    ft['date'], 
                    'জমা' if ft['type'] == 'deposit' else 'উত্তোলন',
                    f"৳{ft['amount']:.0f}",
                    ft['description'] or '-',
                    f"৳{ft['current_balance']:.0f}"
                ])
            
            table = Table(data, repeatRows=1)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a5276')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ]))
            elements.append(table)
        
        doc.build(elements)
        buffer.seek(0)
        b64 = base64.b64encode(buffer.read()).decode()
        
        # ডাউনলোড বাটন
        st.markdown(f"""
        <div style="text-align: center; margin-top: 20px;">
            <a href="data:application/octet-stream;base64,{b64}" download="somiti_report_{datetime.date.today()}.pdf" 
               style="background: linear-gradient(90deg, #238636 0%, #2ea043 100%); 
                      color: white; padding: 12px 30px; border-radius: 8px; 
                      text-decoration: none; font-weight: bold; font-size: 16px;">
                📥 {t("পিডিএফ ডাউনলোড করুন", "Download PDF")}
            </a>
        </div>
        """, unsafe_allow_html=True)
        
        st.success(t("✅ পিডিএফ জেনারেট হয়েছে!", "✅ PDF Generated Successfully!"))

def email_test():
    st.subheader(t("📧 ইমেইল টেস্ট", "📧 Email Test"))
    
    st.info(t("এই ফিচারটি ইমেইল কনফিগারেশন টেস্ট করার জন্য", 
              "This feature is to test email configuration"))
    
    with st.form("email_test_form"):
        email = st.text_input(t("ইমেইল ঠিকানা", "Email Address"), 
                              placeholder="example@email.com")
        subject = st.text_input(t("বিষয়", "Subject"), 
                                value="Test Email from Oikko Uddog")
        message = st.text_area(t("বার্তা", "Message"), 
                               value="This is a test email from Oikko Uddog Songstha.")
        
        if st.form_submit_button(t("📧 টেস্ট ইমেইল পাঠান", "📧 Send Test Email"), use_container_width=True):
            if not email:
                st.error(t("❌ ইমেইল ঠিকানা আবশ্যক", "❌ Email address is required"))
            else:
                with st.spinner(t("ইমেইল পাঠানো হচ্ছে...", "Sending email...")):
                    if send_email(email, subject, message):
                        st.success(t("✅ ইমেইল সফলভাবে পাঠানো হয়েছে!", "✅ Email sent successfully!"))
                        st.balloons()
                    else:
                        st.error(t("❌ ইমেইল পাঠানো সম্ভব হয়নি। secrets.toml ফাইল চেক করুন।", 
                                  "❌ Failed to send email. Please check secrets.toml file."))

def lottery():
    st.subheader(t("🎲 লটারি", "🎲 Lottery"))
    
    st.markdown("""
    <div style="text-align: center; padding: 30px;">
        <h2>🎰 ঐক্য উদ্যোগ লটারি 🎰</h2>
        <p>বিজয়ী নির্বাচন করতে নিচের বাটনে ক্লিক করুন</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button(t("🎲 বিজয়ী নির্বাচন করুন", "🎲 Pick Winner"), use_container_width=True):
            members = execute_query("SELECT id, name, phone, total_savings FROM members WHERE status='active'", fetch=True)
            
            if members:
                with st.spinner(t("বিজয়ী নির্বাচন করা হচ্ছে...", "Selecting winner...")):
                    time.sleep(1)
                    winner = random.choice(members)
                
                st.balloons()
                st.snow()
                
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #d35400 0%, #e67e22 100%); 
                            padding: 30px; border-radius: 15px; text-align: center; margin-top: 20px;">
                    <h1 style="color: white;">🏆 {t('বিজয়ী', 'Winner')} 🏆</h1>
                    <h2 style="color: white;">{winner['name']}</h2>
                    <h3 style="color: #f0f0f0;">{winner['id']}</h3>
                    <p style="color: #f0f0f0;">{t('মোবাইল:', 'Mobile:')} {winner['phone']}</p>
                    <p style="color: #f0f0f0;">{t('মোট জমা:', 'Total Savings:')} ৳{winner['total_savings']:,.0f}</p>
                </div>
                """, unsafe_allow_html=True)
                
                # বিজয়ীর ইতিহাস সংরক্ষণ
                st.session_state['last_winner'] = {
                    'name': winner['name'],
                    'id': winner['id'],
                    'date': datetime.date.today().isoformat()
                }
            else:
                st.warning(t("কোনো সক্রিয় সদস্য নেই", "No active members found"))
    
    # আগের বিজয়ী দেখান
    if 'last_winner' in st.session_state:
        st.divider()
        st.subheader(t("📜 সর্বশেষ বিজয়ী", "📜 Last Winner"))
        st.info(f"""
        🏆 {st.session_state['last_winner']['name']} ({st.session_state['last_winner']['id']})
        📅 {st.session_state['last_winner']['date']}
        """)

# ------------------------------
# সদস্য প্যানেল
# ------------------------------
def member_panel():
    member = st.session_state.user_data
    
    # হেডার
    st.markdown(f"""
    <div class="main-header">
        <h1>{t('স্বাগতম', 'Welcome')}, {member['name']}! 👋</h1>
        <p style="color: #c9d1d9; margin: 0;">{t('সদস্য আইডি:', 'Member ID:')} {member['id']}</p>
    </div>
    """, unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs([
        t("📊 ড্যাশবোর্ড", "📊 Dashboard"),
        t("🔐 পাসওয়ার্ড পরিবর্তন", "🔐 Change Password"),
        t("📄 রিপোর্ট", "📄 Report")
    ])
    
    with tab1:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(t("মোট জমা", "Total Savings"), f"৳{member['total_savings']:,.0f}")
        with col2:
            st.metric(t("মাসিক কিস্তি", "Monthly Installment"), f"৳{member['monthly_savings']:,.0f}")
        with col3:
            total_paid_months = execute_query("""
                SELECT COUNT(DISTINCT month || '-' || year) as cnt 
                FROM transactions WHERE member_id=?
            """, (member['id'],), fetch=True)[0]['cnt']
            st.metric(t("মোট জমার মাস", "Total Paid Months"), total_paid_months)
        
        # এই মাসের স্ট্যাটাস
        today = datetime.date.today()
        paid_this_month = execute_query("""
            SELECT * FROM transactions WHERE member_id=? AND month=? AND year=?
        """, (member['id'], today.month, today.year), fetch=True)
        
        st.divider()
        
        if paid_this_month:
            st.success(t(f"✅ {calendar.month_name[today.month]} {today.year} মাসের কিস্তি জমা হয়েছে", 
                        f"✅ Installment for {calendar.month_name[today.month]} {today.year} has been paid"))
            total_this_month = sum(tx['amount'] + tx['late_fee'] for tx in paid_this_month)
            st.info(f"{t('এই মাসে মোট জমা:', 'Total deposited this month:')} ৳{total_this_month:,.0f}")
        else:
            st.warning(t(f"⏳ {calendar.month_name[today.month]} {today.year} মাসের কিস্তি জমা হয়নি", 
                        f"⏳ Installment for {calendar.month_name[today.month]} {today.year} is pending"))
        
        st.divider()
        st.subheader(t("📋 সাম্প্রতিক লেনদেন", "📋 Recent Transactions"))
        
        tx = execute_query("""
            SELECT full_date, month_name, year, amount, late_fee, (amount + late_fee) as total
            FROM transactions WHERE member_id=?
            ORDER BY date_iso DESC LIMIT 10
        """, (member['id'],), fetch=True)
        
        if tx:
            tx_data = []
            for t_row in tx:
                tx_data.append({
                    t('তারিখ', 'Date'): t_row['full_date'],
                    t('মাস', 'Month'): f"{t_row['month_name']} {t_row['year']}",
                    t('পরিমাণ', 'Amount'): f"৳{t_row['amount']:,.0f}",
                    t('লেট ফি', 'Late Fee'): f"৳{t_row['late_fee']:,.0f}",
                    t('মোট', 'Total'): f"৳{t_row['total']:,.0f}"
                })
            
            df = pd.DataFrame(tx_data)
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info(t("কোনো লেনদেন নেই", "No transactions found"))
    
    with tab2:
        st.subheader(t("🔐 পাসওয়ার্ড পরিবর্তন", "🔐 Change Password"))
        
        with st.form("change_password_form"):
            current_pwd = st.text_input(t("বর্তমান পাসওয়ার্ড", "Current Password"), type="password")
            new_pwd = st.text_input(t("নতুন পাসওয়ার্ড", "New Password"), type="password")
            confirm_pwd = st.text_input(t("নতুন পাসওয়ার্ড নিশ্চিত করুন", "Confirm New Password"), type="password")
            
            if st.form_submit_button(t("🔄 পাসওয়ার্ড আপডেট", "🔄 Update Password"), use_container_width=True):
                if not current_pwd or not new_pwd or not confirm_pwd:
                    st.error(t("❌ সবগুলো ফিল্ড পূরণ করুন", "❌ Please fill all fields"))
                elif not verify_password(current_pwd, member['password']):
                    st.error(t("❌ বর্তমান পাসওয়ার্ড ভুল", "❌ Current password is incorrect"))
                elif new_pwd != confirm_pwd:
                    st.error(t("❌ নতুন পাসওয়ার্ড মিলছে না", "❌ New passwords do not match"))
                elif len(new_pwd) < 6:
                    st.error(t("❌ পাসওয়ার্ড কমপক্ষে ৬ অক্ষরের হতে হবে", "❌ Password must be at least 6 characters"))
                else:
                    execute_query("UPDATE members SET password=? WHERE id=?", 
                                 (hash_password(new_pwd), member['id']))
                    st.success(t("✅ পাসওয়ার্ড সফলভাবে পরিবর্তন হয়েছে!", "✅ Password changed successfully!"))
                    st.balloons()
                    
                    # সেশন আপডেট
                    member['password'] = hash_password(new_pwd)
                    st.session_state.user_data = member
    
    with tab3:
        st.subheader(t("📄 আমার লেনদেন রিপোর্ট", "📄 My Transaction Report"))
        
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input(t("শুরুর তারিখ", "Start Date"), 
                                       value=datetime.date.today() - datetime.timedelta(days=365))
        with col2:
            end_date = st.date_input(t("শেষ তারিখ", "End Date"), 
                                     value=datetime.date.today())
        
        if st.button(t("📥 পিডিএফ রিপোর্ট জেনারেট", "📥 Generate PDF Report"), use_container_width=True):
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4)
            elements = []
            styles = getSampleStyleSheet()
            
            # হেডার
            title_style = ParagraphStyle(
                'Title',
                parent=styles['Heading1'],
                fontSize=20,
                textColor=colors.HexColor('#1a5276'),
                spaceAfter=10,
                alignment=1
            )
            elements.append(Paragraph("ঐক্য উদ্যোগ সংস্থা", title_style))
            elements.append(Paragraph(f"সদস্য: {member['name']} ({member['id']})", styles['Heading2']))
            elements.append(Paragraph(f"লেনদেন রিপোর্ট: {start_date} থেকে {end_date}", styles['Normal']))
            elements.append(Spacer(1, 20))
            
            # লেনদেন ডাটা
            tx = execute_query("""
                SELECT full_date, month_name, year, amount, late_fee, (amount + late_fee) as total
                FROM transactions 
                WHERE member_id=? AND date_iso BETWEEN ? AND ?
                ORDER BY date_iso
            """, (member['id'], start_date.isoformat(), end_date.isoformat()), fetch=True)
            
            data = [['তারিখ', 'মাস', 'পরিমাণ', 'লেট ফি', 'মোট']]
            total_sum = 0
            for t_row in tx:
                data.append([
                    t_row['full_date'],
                    f"{t_row['month_name']} {t_row['year']}",
                    f"৳{t_row['amount']:.0f}",
                    f"৳{t_row['late_fee']:.0f}",
                    f"৳{t_row['total']:.0f}"
                ])
                total_sum += t_row['total']
            
            data.append(['', '', '', 'সর্বমোট:', f"৳{total_sum:.0f}"])
            
            table = Table(data, repeatRows=1)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a5276')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -2), 0.5, colors.grey),
                ('SPAN', (0, -1), (2, -1)),
                ('FONTNAME', (3, -1), (4, -1), 'Helvetica-Bold'),
            ]))
            elements.append(table)
            
            # সামারি
            elements.append(Spacer(1, 20))
            elements.append(Paragraph(f"মোট জমা: ৳{member['total_savings']:.0f}", styles['Normal']))
            elements.append(Paragraph(f"মোট লেনদেন সংখ্যা: {len(tx)}", styles['Normal']))
            
            doc.build(elements)
            buffer.seek(0)
            b64 = base64.b64encode(buffer.read()).decode()
            
            st.markdown(f"""
            <div style="text-align: center; margin-top: 20px;">
                <a href="data:application/octet-stream;base64,{b64}" 
                   download="my_transactions_{member['id']}_{datetime.date.today()}.pdf" 
                   style="background: linear-gradient(90deg, #238636 0%, #2ea043 100%); 
                          color: white; padding: 12px 30px; border-radius: 8px; 
                          text-decoration: none; font-weight: bold;">
                    📥 {t("পিডিএফ ডাউনলোড করুন", "Download PDF")}
                </a>
            </div>
            """, unsafe_allow_html=True)
            
            st.success(t("✅ রিপোর্ট জেনারেট হয়েছে!", "✅ Report generated successfully!"))

# ------------------------------
# মেইন অ্যাপ
# ------------------------------
def main():
    # ডাটাবেজ ইনিশিয়ালাইজ
    init_database()
    
    # টপ বারে ভাষা সিলেক্টর
    col1, col2, col3 = st.columns([3, 1, 1])
    with col3:
        lang = st.radio("🌐", ["বাংলা", "English"], horizontal=True, label_visibility="collapsed")
        st.session_state.language = 'bn' if lang == "বাংলা" else 'en'
    
    # সেশন স্টেট ইনিশিয়ালাইজ
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.user_type = None
        st.session_state.user_data = None
    
    # লগইন চেক
    if not st.session_state.logged_in:
        params = st.query_params
        member_id_from_url = params.get("id", None)
        
        if member_id_from_url:
            # সদস্য লগইন
            st.markdown('<div class="main-header"><h1>🔐 সদস্য লগইন</h1></div>', unsafe_allow_html=True)
            
            # সদস্যের তথ্য দেখান
            member_info = execute_query("SELECT name FROM members WHERE id=?", (member_id_from_url,), fetch=True)
            if member_info:
                st.info(f"স্বাগতম, {member_info[0]['name']}! লগইন করতে আপনার ইমেইল ও পাসওয়ার্ড দিন।")
            
            with st.form("member_login_form"):
                email = st.text_input(t("📧 ইমেইল", "📧 Email"), placeholder="your@email.com")
                password = st.text_input(t("🔑 পাসওয়ার্ড", "🔑 Password"), type="password")
                
                col1, col2 = st.columns(2)
                with col1:
                    submitted = st.form_submit_button(t("🚪 লগইন", "🚪 Login"), use_container_width=True)
                with col2:
                    back_to_admin = st.form_submit_button(t("👑 এডমিন লগইন", "👑 Admin Login"), use_container_width=True)
                
                if submitted:
                    if member_login(email, password, member_id_from_url):
                        st.success(t("✅ লগইন সফল!", "✅ Login successful!"))
                        st.balloons()
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(t("❌ ভুল ইমেইল বা পাসওয়ার্ড", "❌ Invalid email or password"))
                
                if back_to_admin:
                    st.query_params.clear()
                    st.rerun()
        else:
            # এডমিন লগইন
            st.markdown('<div class="main-header"><h1>👑 এডমিন লগইন</h1></div>', unsafe_allow_html=True)
            
            with st.form("admin_login_form"):
                mobile = st.text_input(t("📱 মোবাইল নম্বর", "📱 Mobile Number"), placeholder="01XXXXXXXXX")
                password = st.text_input(t("🔑 পাসওয়ার্ড", "🔑 Password"), type="password")
                
                submitted = st.form_submit_button(t("🚪 লগইন", "🚪 Login"), use_container_width=True)
                
                if submitted:
                    if admin_login(mobile, password):
                        st.success(t("✅ লগইন সফল!", "✅ Login successful!"))
                        st.balloons()
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(t("❌ ভুল মোবাইল বা পাসওয়ার্ড", "❌ Invalid mobile or password"))
        
        st.stop()
    
    # সাইডবার
    with st.sidebar:
        st.markdown("""
        <div style="text-align: center; padding: 20px 0;">
            <h2 style="color: #58a6ff; margin: 0;">🤝 ঐক্য উদ্যোগ</h2>
            <p style="color: #8b949e; margin: 0;">সংস্থা</p>
        </div>
        """, unsafe_allow_html=True)
        st.divider()
        
        if st.session_state.user_type == 'admin':
            menu_options = [
                t("🏠 ড্যাশবোর্ড", "🏠 Dashboard"),
                t("➕ নতুন সদস্য", "➕ New Member"),
                t("✏️ সদস্য ব্যবস্থাপনা", "✏️ Member Management"),
                t("💵 টাকা জমা", "💵 Deposit"),
                t("🔗 সদস্য লিংক", "🔗 Member Links"),
                t("🏧 ফান্ড ব্যবস্থাপনা", "🏧 Fund"),
                t("📊 রিপোর্ট", "📊 Reports"),
                t("📥 পিডিএফ ডাউনলোড", "📥 PDF Download"),
                t("📧 ইমেইল টেস্ট", "📧 Email Test"),
                t("🎲 লটারি", "🎲 Lottery")
            ]
            
            menu = st.radio(
                t("📋 মেনু", "📋 Menu"),
                menu_options,
                label_visibility="collapsed"
            )
        else:
            menu = t("👤 সদস্য প্যানেল", "👤 Member Panel")
        
        st.divider()
        
        # ইউজার ইনফো
        if st.session_state.user_type == 'admin':
            st.caption(f"👑 {t('এডমিন', 'Admin')}: {st.session_state.user_data['mobile']}")
        else:
            st.caption(f"👤 {st.session_state.user_data['name']}")
            st.caption(f"🆔 {st.session_state.user_data['id']}")
        
        if st.button(t("🚪 লগআউট", "🚪 Logout"), use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.user_type = None
            st.session_state.user_data = None
            st.query_params.clear()
            st.rerun()
    
    # মেইন কন্টেন্ট
    if st.session_state.user_type == 'admin':
        if menu == t("🏠 ড্যাশবোর্ড", "🏠 Dashboard"):
            admin_dashboard()
        elif menu == t("➕ নতুন সদস্য", "➕ New Member"):
            new_member_registration()
        elif menu == t("✏️ সদস্য ব্যবস্থাপনা", "✏️ Member Management"):
            member_management()
        elif menu == t("💵 টাকা জমা", "💵 Deposit"):
            deposit_management()
        elif menu == t("🔗 সদস্য লিংক", "🔗 Member Links"):
            member_links()
        elif menu == t("🏧 ফান্ড ব্যবস্থাপনা", "🏧 Fund"):
            fund_management()
        elif menu == t("📊 রিপোর্ট", "📊 Reports"):
            reports()
        elif menu == t("📥 পিডিএফ ডাউনলোড", "📥 PDF Download"):
            pdf_download()
        elif menu == t("📧 ইমেইল টেস্ট", "📧 Email Test"):
            email_test()
        elif menu == t("🎲 লটারি", "🎲 Lottery"):
            lottery()
    else:
        member_panel()

if __name__ == "__main__":
    main()
