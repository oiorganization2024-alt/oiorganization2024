import streamlit as st
import pandas as pd
import sqlite3
import random
import string
import datetime
import os
import shutil
import time
import hashlib
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors
import io
import base64
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
    }
    .stButton > button:hover {
        background: linear-gradient(90deg, #2ea043 0%, #3fb950 100%);
        transform: scale(1.02);
        box-shadow: 0 2px 8px rgba(46,160,67,0.3);
    }
    /* এক্সপ্যান্ডার */
    .streamlit-expanderHeader {
        background-color: #21262d;
        border: 1px solid #30363d;
        border-radius: 8px;
    }
    /* ইনপুট ফিল্ড */
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input {
        background-color: #0d1117;
        color: white;
        border: 1px solid #30363d;
    }
    </style>
    """, unsafe_allow_html=True)

apply_custom_css()

# ------------------------------
# ভাষা সহায়ক ফাংশন
# ------------------------------
if 'language' not in st.session_state:
    st.session_state.language = 'bn'  # 'bn' or 'en'

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
        st.error("ইমেইল কনফিগারেশন পাওয়া যায়নি। secrets.toml ফাইল চেক করুন।")
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
    except Exception as e:
        st.error(f"ইমেইল পাঠাতে ব্যর্থ: {e}")
        return False

# ------------------------------
# এডমিন লগইন
# ------------------------------
ADMIN_MOBILE = "01766222373"
ADMIN_PASSWORD_HASH = hash_password("oio112024")  # ডিফল্ট পাসওয়ার্ড

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
# এডমিন ড্যাশবোর্ড
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
        st.markdown(f'<div class="kpi-card"><div class="kpi-value">৳{paid_count * 500:,.0f}</div><div class="kpi-label">{t("এই মাসের কালেকশন", "This Month Collection")}</div></div>', unsafe_allow_html=True)
    with col4:
        st.markdown(f'<div class="kpi-card"><div class="kpi-value">{unpaid_count}</div><div class="kpi-label">{t("বাকি আছেন", "Pending")}</div></div>', unsafe_allow_html=True)

    # টোটাল ও ক্যাশ বক্স
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f'<div class="total-box"><h3>{t("মোট তহবিল", "Total Fund")}</h3><h2>৳{total_savings:,.0f}</h2></div>', unsafe_allow_html=True)
    with col2:
        cash = get_cash_balance()
        st.markdown(f'<div class="cash-box"><h3>{t("বর্তমান ক্যাশ", "Current Cash")}</h3><h2>৳{cash:,.0f}</h2></div>', unsafe_allow_html=True)

    if st.button(t("রিফ্রেশ করুন", "Refresh Data")):
        st.rerun()

def new_member_registration():
    st.subheader(t("➕ নতুন সদস্য নিবন্ধন", "➕ New Member Registration"))
    with st.form("new_member_form"):
        name = st.text_input(t("নাম *", "Name *"))
        phone = st.text_input(t("মোবাইল *", "Mobile *"))
        email = st.text_input(t("ইমেইল", "Email"))
        monthly = st.number_input(t("মাসিক কিস্তি (টাকা)", "Monthly Installment (Tk)"), value=500, min_value=100, step=50)

        submitted = st.form_submit_button(t("নিবন্ধন করুন", "Register"))
        if submitted:
            if not name or not phone:
                st.error(t("নাম ও মোবাইল আবশ্যক", "Name and mobile are required"))
            else:
                # চেক ইউনিক মোবাইল
                existing = execute_query("SELECT id FROM members WHERE phone=?", (phone,), fetch=True)
                if existing:
                    st.error(t("এই মোবাইল নম্বরটি ইতিমধ্যে নিবন্ধিত", "This mobile number is already registered"))
                else:
                    member_id = generate_member_id()
                    password = generate_password()
                    join_date = datetime.date.today().isoformat()
                    execute_query("""
                        INSERT INTO members (id, name, phone, email, password, monthly_savings, join_date)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (member_id, name, phone, email, hash_password(password), monthly, join_date))
                    st.success(t(f"✅ সদস্য তৈরি হয়েছে! আইডি: {member_id}, পাসওয়ার্ড: {password}", f"✅ Member created! ID: {member_id}, Password: {password}"))
                    st.balloons()
                    time.sleep(1.5)
                    st.rerun()

def member_management():
    st.subheader(t("✏️ সদস্য ব্যবস্থাপনা", "✏️ Member Management"))
    members = execute_query("SELECT * FROM members ORDER BY join_date DESC", fetch=True)
    for m in members:
        with st.expander(f"{m['name']} ({m['id']}) - {m['phone']}"):
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**{t('ইমেইল', 'Email')}:** {m['email'] or '-'}")
                st.write(f"**{t('মোট জমা', 'Total Savings')}:** ৳{m['total_savings']:,.0f}")
                st.write(f"**{t('মাসিক কিস্তি', 'Monthly')}:** ৳{m['monthly_savings']:,.0f}")
                st.write(f"**{t('স্ট্যাটাস', 'Status')}:** {m['status']}")
            with col2:
                # এডিট ফর্ম
                with st.form(f"edit_member_{m['id']}"):
                    new_name = st.text_input(t("নাম", "Name"), value=m['name'])
                    new_phone = st.text_input(t("মোবাইল", "Mobile"), value=m['phone'])
                    new_email = st.text_input(t("ইমেইল", "Email"), value=m['email'] or "")
                    new_monthly = st.number_input(t("মাসিক কিস্তি", "Monthly"), value=float(m['monthly_savings']), step=50.0)
                    if st.form_submit_button(t("আপডেট", "Update")):
                        execute_query("""
                            UPDATE members SET name=?, phone=?, email=?, monthly_savings=?
                            WHERE id=?
                        """, (new_name, new_phone, new_email, new_monthly, m['id']))
                        st.success(t("আপডেট সফল", "Updated successfully"))
                        st.rerun()

            # অ্যাকশন বাটন
            c1, c2, c3 = st.columns(3)
            with c1:
                if st.button(t("পাসওয়ার্ড রিসেট", "Reset Password"), key=f"reset_{m['id']}"):
                    new_pwd = generate_password()
                    execute_query("UPDATE members SET password=? WHERE id=?", (hash_password(new_pwd), m['id']))
                    st.success(f"নতুন পাসওয়ার্ড: {new_pwd}")
            with c2:
                new_status = 'inactive' if m['status'] == 'active' else 'active'
                if st.button(t("নিষ্ক্রিয় করুন" if m['status']=='active' else "সক্রিয় করুন", "Deactivate" if m['status']=='active' else "Activate"), key=f"toggle_{m['id']}"):
                    execute_query("UPDATE members SET status=? WHERE id=?", (new_status, m['id']))
                    st.rerun()
            with c3:
                if st.button(t("মুছে ফেলুন", "Delete"), key=f"delete_{m['id']}"):
                    if st.warning(t("নিশ্চিত? এটি স্থায়ী হবে", "Confirm? This is permanent")):
                        execute_query("DELETE FROM members WHERE id=?", (m['id'],))
                        st.rerun()

def deposit_management():
    st.subheader(t("💵 টাকা জমা", "💵 Deposit"))
    today = datetime.date.today()
    current_month = today.month
    current_year = today.year

    tab1, tab2 = st.tabs([t("জমা দিয়েছে", "Paid"), t("জমা দেয়নি", "Unpaid")])

    with tab1:
        paid_ids = get_paid_members(current_month, current_year)
        if not paid_ids:
            st.info(t("এই মাসে কেউ জমা দেয়নি", "No payments this month"))
        else:
            for mid in paid_ids:
                m = execute_query("SELECT * FROM members WHERE id=?", (mid,), fetch=True)[0]
                st.write(f"✅ {m['name']} ({m['id']})")

    with tab2:
        unpaid_ids = get_unpaid_members(current_month, current_year)
        if not unpaid_ids:
            st.success(t("সবাই জমা দিয়েছে!", "Everyone has paid!"))
        else:
            for mid in unpaid_ids:
                m = execute_query("SELECT * FROM members WHERE id=?", (mid,), fetch=True)[0]
                with st.expander(f"{m['name']} ({m['id']}) - মাসিক {m['monthly_savings']} টাকা"):
                    col1, col2 = st.columns(2)
                    with col1:
                        pay_date = st.date_input(t("তারিখ", "Date"), value=today, key=f"date_{mid}")
                        months_count = st.number_input(t("কত মাসের জমা", "Number of months"), min_value=1, max_value=12, value=1, key=f"months_{mid}")
                    with col2:
                        late_fee = st.number_input(t("লেট ফি", "Late Fee"), min_value=0.0, value=0.0, step=10.0, key=f"fee_{mid}")
                    if st.button(t("জমা নিন", "Deposit"), key=f"deposit_{mid}"):
                        amount_per_month = m['monthly_savings']
                        total_amount = amount_per_month * months_count + late_fee
                        # ট্রানজেকশন তৈরি
                        for i in range(months_count):
                            # মাস নির্ধারণ (বর্তমান মাস থেকে পিছিয়ে)
                            month_offset = i
                            tx_date = pay_date - datetime.timedelta(days=30*month_offset)
                            tx_month = tx_date.month
                            tx_year = tx_date.year
                            # চেক করুন ইতিমধ্যে জমা আছে কিনা
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
                                    mid, amount_per_month, tx_date.day, tx_month, tx_year,
                                    tx_date.strftime('%B'), tx_date.strftime('%B'),  # বাংলা পরে ইম্প্রুভ করা যাবে
                                    tx_date.strftime('%d/%m/%Y'), tx_date.strftime('%d/%m/%Y'),
                                    tx_date.isoformat(),
                                    late_fee if i == 0 else 0,  # শুধু প্রথম মাসে লেট ফি
                                    datetime.datetime.now().isoformat()
                                ))
                        # মোট সঞ্চয় আপডেট
                        execute_query("UPDATE members SET total_savings = total_savings + ? WHERE id=?", (total_amount, mid))
                        st.success(t(f"✅ জমা সফল! মোট {total_amount} টাকা", f"✅ Deposit successful! Total {total_amount} Tk"))
                        st.balloons()
                        time.sleep(1.5)
                        st.rerun()

def transaction_management():
    st.subheader(t("💰 লেনদেন ব্যবস্থাপনা", "💰 Transaction Management"))
    members = execute_query("SELECT id, name FROM members WHERE status='active'", fetch=True)
    member_options = {m['name']: m['id'] for m in members}
    selected_name = st.selectbox(t("সদস্য নির্বাচন করুন", "Select Member"), list(member_options.keys()))
    if selected_name:
        member_id = member_options[selected_name]
        transactions = execute_query("""
            SELECT * FROM transactions WHERE member_id=? ORDER BY date_iso DESC
        """, (member_id,), fetch=True)

        if transactions:
            df = pd.DataFrame([dict(t) for t in transactions])
            df_display = df[['full_date', 'amount', 'late_fee', 'month_name']].copy()
            df_display.columns = [t('তারিখ', 'Date'), t('পরিমাণ', 'Amount'), t('লেট ফি', 'Late Fee'), t('মাস', 'Month')]
            st.dataframe(df_display, use_container_width=True)

            # এডিট/ডিলিট
            tx_id = st.selectbox(t("সম্পাদনার জন্য লেনদেন নির্বাচন", "Select transaction to edit"), df['id'].tolist(), format_func=lambda x: f"ID {x}")
            if tx_id:
                tx = df[df['id'] == tx_id].iloc[0].to_dict()
                with st.form("edit_tx"):
                    new_amount = st.number_input(t("পরিমাণ", "Amount"), value=float(tx['amount']))
                    new_fee = st.number_input(t("লেট ফি", "Late Fee"), value=float(tx['late_fee']))
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.form_submit_button(t("আপডেট", "Update")):
                            diff = (new_amount + new_fee) - (tx['amount'] + tx['late_fee'])
                            execute_query("UPDATE transactions SET amount=?, late_fee=? WHERE id=?", (new_amount, new_fee, tx_id))
                            execute_query("UPDATE members SET total_savings = total_savings + ? WHERE id=?", (diff, member_id))
                            st.success(t("আপডেট সফল", "Updated"))
                            st.rerun()
                    with col2:
                        if st.form_submit_button(t("মুছে ফেলুন", "Delete")):
                            execute_query("DELETE FROM transactions WHERE id=?", (tx_id,))
                            execute_query("UPDATE members SET total_savings = total_savings - ? WHERE id=?", (tx['amount'] + tx['late_fee'], member_id))
                            st.success(t("মুছে ফেলা হয়েছে", "Deleted"))
                            st.rerun()
        else:
            st.info(t("কোনো লেনদেন নেই", "No transactions found"))

def member_links():
    st.subheader(t("🔗 সদস্য লিংক", "🔗 Member Links"))
    members = execute_query("SELECT id, name, email, password FROM members WHERE status='active'", fetch=True)
    base_url = st.query_params.get("base_url", "http://localhost:8501")  # ডিফল্ট লোকাল
    for m in members:
        with st.container():
            cols = st.columns([3,1,1,1])
            with cols[0]:
                st.write(f"**{m['name']}** ({m['id']})")
            with cols[1]:
                link = f"{base_url}?id={m['id']}"
                st.code(link, language=None)
            with cols[2]:
                if st.button(t("লিংক কপি", "Copy Link"), key=f"copy_link_{m['id']}"):
                    st.write(f'<span id="copy_{m["id"]}">{link}</span>', unsafe_allow_html=True)
                    st.markdown(f"""
                    <script>
                    navigator.clipboard.writeText("{link}");
                    alert("লিংক কপি করা হয়েছে");
                    </script>
                    """, unsafe_allow_html=True)
            with cols[3]:
                if st.button(t("পাসওয়ার্ড কপি", "Copy Password"), key=f"copy_pwd_{m['id']}"):
                    st.write(f'<span id="pwd_{m["id"]}">{m["password"]}</span>', unsafe_allow_html=True)
                    st.markdown(f"""
                    <script>
                    navigator.clipboard.writeText("{m["password"]}");
                    alert("পাসওয়ার্ড কপি করা হয়েছে");
                    </script>
                    """, unsafe_allow_html=True)
            if m['email'] and st.button(t("ইমেইল পাঠান", "Send Email"), key=f"email_{m['id']}"):
                subject = "আপনার ঐক্য উদ্যোগ সংস্থা লগইন তথ্য"
                body = f"আইডি: {m['id']}\nপাসওয়ার্ড: {m['password']}\nলগইন লিংক: {link}"
                if send_email(m['email'], subject, body):
                    st.success("ইমেইল পাঠানো হয়েছে")

def expense_management():
    st.subheader(t("💸 খরচ ব্যবস্থাপনা", "💸 Expense Management"))
    # নতুন খরচ ফর্ম
    with st.form("add_expense"):
        desc = st.text_input(t("বিবরণ", "Description"))
        amount = st.number_input(t("পরিমাণ", "Amount"), min_value=0.0)
        category = st.selectbox(t("ক্যাটাগরি", "Category"), ["অফিস খরচ", "ইভেন্ট", "অন্যান্য"])
        exp_date = st.date_input(t("তারিখ", "Date"), value=datetime.date.today())
        if st.form_submit_button(t("যোগ করুন", "Add")):
            execute_query("""
                INSERT INTO expenses (description, amount, date, category, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (desc, amount, exp_date.isoformat(), category, datetime.datetime.now().isoformat()))
            st.success(t("খরচ যোগ করা হয়েছে", "Expense added"))
            st.rerun()

    # খরচ তালিকা
    expenses = execute_query("SELECT * FROM expenses ORDER BY date DESC", fetch=True)
    if expenses:
        df = pd.DataFrame([dict(e) for e in expenses])
        total_exp = df['amount'].sum()
        st.metric(t("মোট খরচ", "Total Expenses"), f"৳{total_exp:,.0f}")
        for _, row in df.iterrows():
            cols = st.columns([2,1,2,1,1])
            cols[0].write(row['date'])
            cols[1].write(row['category'])
            cols[2].write(row['description'])
            cols[3].write(f"৳{row['amount']:,.0f}")
            if cols[4].button(t("মুছুন", "Delete"), key=f"del_exp_{row['id']}"):
                execute_query("DELETE FROM expenses WHERE id=?", (row['id'],))
                st.rerun()

def fund_management():
    st.subheader(t("🏧 ফান্ড ব্যবস্থাপনা", "🏧 Fund Management"))
    cash = get_cash_balance()
    st.metric(t("বর্তমান ক্যাশ ব্যালেন্স", "Current Cash Balance"), f"৳{cash:,.0f}")

    tab1, tab2, tab3 = st.tabs([t("জমা", "Deposit"), t("উত্তোলন", "Withdrawal"), t("ইতিহাস", "History")])

    with tab1:
        with st.form("fund_deposit"):
            amount = st.number_input(t("পরিমাণ", "Amount"), min_value=0.0)
            desc = st.text_input(t("বিবরণ", "Description"))
            if st.form_submit_button(t("জমা করুন", "Deposit")):
                prev = cash
                new_bal = prev + amount
                execute_query("""
                    INSERT INTO fund_transactions (type, amount, description, date, previous_balance, current_balance, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, ('deposit', amount, desc, datetime.date.today().isoformat(), prev, new_bal, datetime.datetime.now().isoformat()))
                st.success(t("ফান্ড জমা হয়েছে", "Fund deposited"))
                st.rerun()

    with tab2:
        with st.form("fund_withdraw"):
            amount = st.number_input(t("পরিমাণ", "Amount"), min_value=0.0)
            desc = st.text_input(t("বিবরণ", "Description"))
            if st.form_submit_button(t("উত্তোলন করুন", "Withdraw")):
                if amount > cash:
                    st.error(t("পর্যাপ্ত ব্যালেন্স নেই", "Insufficient balance"))
                else:
                    prev = cash
                    new_bal = prev - amount
                    execute_query("""
                        INSERT INTO fund_transactions (type, amount, description, date, previous_balance, current_balance, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, ('withdrawal', amount, desc, datetime.date.today().isoformat(), prev, new_bal, datetime.datetime.now().isoformat()))
                    st.success(t("উত্তোলন সম্পন্ন", "Withdrawn"))
                    st.rerun()

    with tab3:
        history = execute_query("SELECT * FROM fund_transactions ORDER BY date DESC", fetch=True)
        if history:
            df = pd.DataFrame([dict(h) for h in history])
            st.dataframe(df[['date', 'type', 'amount', 'description', 'current_balance']])

def reports():
    st.subheader(t("📊 রিপোর্ট", "📊 Reports"))
    # মাসিক কালেকশন বার চার্ট
    tx_data = execute_query("""
        SELECT year, month, SUM(amount) as total FROM transactions GROUP BY year, month ORDER BY year, month
    """, fetch=True)
    if tx_data:
        df = pd.DataFrame([dict(r) for r in tx_data])
        df['period'] = df['year'].astype(str) + '-' + df['month'].astype(str).str.zfill(2)
        st.bar_chart(df.set_index('period')['total'])

    # বকেয়াদার তালিকা
    unpaid = get_unpaid_members(datetime.date.today().month, datetime.date.today().year)
    if unpaid:
        st.subheader(t("এই মাসের বাকি সদস্য", "Pending Members This Month"))
        for mid in unpaid:
            m = execute_query("SELECT name, phone FROM members WHERE id=?", (mid,), fetch=True)[0]
            st.write(f"- {m['name']} ({m['phone']})")

def pdf_download():
    st.subheader(t("📥 পিডিএফ ডাউনলোড", "📥 PDF Download"))
    report_type = st.selectbox(t("রিপোর্ট টাইপ", "Report Type"),
                               [t("সদস্য তালিকা", "Member List"),
                                t("সম্পূর্ণ লেনদেন", "All Transactions"),
                                t("নির্দিষ্ট সদস্যের লেনদেন", "Specific Member Transactions")])

    if report_type == t("নির্দিষ্ট সদস্যের লেনদেন", "Specific Member Transactions"):
        members = execute_query("SELECT id, name FROM members", fetch=True)
        member_id = st.selectbox(t("সদস্য", "Member"), [m['id'] for m in members], format_func=lambda x: f"{x} - {next(m['name'] for m in members if m['id']==x)}")

    if st.button(t("পিডিএফ জেনারেট করুন", "Generate PDF")):
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4

        if report_type == t("সদস্য তালিকা", "Member List"):
            members = execute_query("SELECT * FROM members", fetch=True)
            data = [['ID', 'Name', 'Phone', 'Total Savings']]
            for m in members:
                data.append([m['id'], m['name'], m['phone'], f"{m['total_savings']:.0f}"])
            table = Table(data)
            table.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.grey),
                                       ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
                                       ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                                       ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                                       ('BOTTOMPADDING', (0,0), (-1,0), 12),
                                       ('GRID', (0,0), (-1,-1), 1, colors.black)]))
            table.wrapOn(c, width, height)
            table.drawOn(c, 30, height-150)

        elif report_type == t("সম্পূর্ণ লেনদেন", "All Transactions"):
            tx = execute_query("""
                SELECT m.name, t.full_date, t.amount, t.late_fee FROM transactions t
                JOIN members m ON t.member_id = m.id ORDER BY t.date_iso DESC
            """, fetch=True)
            data = [['Member', 'Date', 'Amount', 'Late Fee']]
            for row in tx:
                data.append([row['name'], row['full_date'], f"{row['amount']:.0f}", f"{row['late_fee']:.0f}"])
            table = Table(data)
            table.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.grey),
                                       ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
                                       ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                                       ('GRID', (0,0), (-1,-1), 1, colors.black)]))
            table.wrapOn(c, width, height)
            table.drawOn(c, 30, height-150)

        else:
            tx = execute_query("""
                SELECT full_date, amount, late_fee FROM transactions WHERE member_id=? ORDER BY date_iso DESC
            """, (member_id,), fetch=True)
            data = [['Date', 'Amount', 'Late Fee']]
            for row in tx:
                data.append([row['full_date'], f"{row['amount']:.0f}", f"{row['late_fee']:.0f}"])
            table = Table(data)
            table.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.grey),
                                       ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
                                       ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                                       ('GRID', (0,0), (-1,-1), 1, colors.black)]))
            table.wrapOn(c, width, height)
            table.drawOn(c, 30, height-150)

        c.save()
        buffer.seek(0)
        b64 = base64.b64encode(buffer.read()).decode()
        href = f'<a href="data:application/octet-stream;base64,{b64}" download="report.pdf">📥 {t("ডাউনলোড", "Download")}</a>'
        st.markdown(href, unsafe_allow_html=True)

def email_test():
    st.subheader(t("📧 ইমেইল টেস্ট", "📧 Email Test"))
    email = st.text_input(t("ইমেইল ঠিকানা", "Email Address"))
    if st.button(t("টেস্ট ইমেইল পাঠান", "Send Test Email")):
        if send_email(email, "Test from Oikko Uddog", "This is a test email."):
            st.success(t("ইমেইল পাঠানো হয়েছে", "Email sent successfully"))
        else:
            st.error(t("পাঠানো সম্ভব হয়নি", "Failed to send"))

def lottery():
    st.subheader(t("🎲 লটারি", "🎲 Lottery"))
    if st.button(t("বিজয়ী নির্বাচন করুন", "Pick Winner")):
        members = execute_query("SELECT id, name FROM members WHERE status='active'", fetch=True)
        if members:
            winner = random.choice(members)
            st.success(f"🏆 {t('বিজয়ী', 'Winner')}: {winner['name']} ({winner['id']})")
            st.balloons()
        else:
            st.warning(t("কোনো সক্রিয় সদস্য নেই", "No active members"))

# ------------------------------
# সদস্য প্যানেল
# ------------------------------
def member_panel():
    member = st.session_state.user_data
    st.markdown(f'<div class="main-header"><h1>স্বাগতম, {member["name"]}</h1></div>', unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs([t("ড্যাশবোর্ড", "Dashboard"),
                                t("পাসওয়ার্ড পরিবর্তন", "Change Password"),
                                t("রিপোর্ট", "Report")])

    with tab1:
        st.metric(t("মোট জমা", "Total Savings"), f"৳{member['total_savings']:,.0f}")
        # এই মাসের পেমেন্ট স্ট্যাটাস
        today = datetime.date.today()
        paid = execute_query("""
            SELECT * FROM transactions WHERE member_id=? AND month=? AND year=?
        """, (member['id'], today.month, today.year), fetch=True)
        if paid:
            st.success(t("এই মাসের কিস্তি জমা হয়েছে", "This month's installment paid"))
        else:
            st.warning(t("এই মাসের কিস্তি জমা হয়নি", "This month's installment not paid"))

        # লেনদেন ইতিহাস
        tx = execute_query("""
            SELECT full_date, amount, late_fee FROM transactions WHERE member_id=? ORDER BY date_iso DESC LIMIT 10
        """, (member['id'],), fetch=True)
        if tx:
            df = pd.DataFrame([dict(t) for t in tx])
            st.dataframe(df)

    with tab2:
        with st.form("change_password"):
            new_pwd = st.text_input(t("নতুন পাসওয়ার্ড", "New Password"), type="password")
            confirm = st.text_input(t("পাসওয়ার্ড নিশ্চিত করুন", "Confirm Password"), type="password")
            if st.form_submit_button(t("আপডেট", "Update")):
                if new_pwd != confirm:
                    st.error(t("পাসওয়ার্ড মিলছে না", "Passwords do not match"))
                elif len(new_pwd) < 6:
                    st.error(t("পাসওয়ার্ড কমপক্ষে ৬ অক্ষরের হতে হবে", "Password must be at least 6 characters"))
                else:
                    execute_query("UPDATE members SET password=? WHERE id=?", (hash_password(new_pwd), member['id']))
                    st.success(t("পাসওয়ার্ড পরিবর্তন সফল", "Password changed successfully"))

    with tab3:
        if st.button(t("আমার লেনদেন রিপোর্ট (পিডিএফ)", "My Transaction Report (PDF)")):
            buffer = io.BytesIO()
            c = canvas.Canvas(buffer, pagesize=A4)
            tx = execute_query("SELECT full_date, amount, late_fee FROM transactions WHERE member_id=? ORDER BY date_iso", (member['id'],), fetch=True)
            data = [['Date', 'Amount', 'Late Fee']]
            for row in tx:
                data.append([row['full_date'], f"{row['amount']:.0f}", f"{row['late_fee']:.0f}"])
            table = Table(data)
            table.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.grey),
                                       ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
                                       ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                                       ('GRID', (0,0), (-1,-1), 1, colors.black)]))
            table.wrapOn(c, 400, 600)
            table.drawOn(c, 30, 750)
            c.save()
            buffer.seek(0)
            b64 = base64.b64encode(buffer.read()).decode()
            href = f'<a href="data:application/octet-stream;base64,{b64}" download="my_transactions.pdf">📥 {t("ডাউনলোড", "Download")}</a>'
            st.markdown(href, unsafe_allow_html=True)

# ------------------------------
# মেইন অ্যাপ
# ------------------------------
def main():
    init_database()

    # ভাষা টগল
    col1, col2 = st.columns([4,1])
    with col2:
        lang = st.radio("🌐", ["বাংলা", "English"], horizontal=True, label_visibility="collapsed")
        st.session_state.language = 'bn' if lang == "বাংলা" else 'en'

    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.user_type = None
        st.session_state.user_data = None

    # লগইন না থাকলে লগইন ফর্ম দেখাও
    if not st.session_state.logged_in:
        # চেক ইউআরএল প্যারামিটার (সদস্য লগইনের জন্য)
        params = st.query_params
        member_id_from_url = params.get("id", None)

        if member_id_from_url:
            st.title(t("সদস্য লগইন", "Member Login"))
            with st.form("member_login"):
                email = st.text_input(t("ইমেইল", "Email"))
                password = st.text_input(t("পাসওয়ার্ড", "Password"), type="password")
                submitted = st.form_submit_button(t("লগইন", "Login"))
                if submitted:
                    if member_login(email, password, member_id_from_url):
                        st.success(t("লগইন সফল", "Login successful"))
                        st.rerun()
                    else:
                        st.error(t("ভুল তথ্য", "Invalid credentials"))
        else:
            st.title(t("এডমিন লগইন", "Admin Login"))
            with st.form("admin_login"):
                mobile = st.text_input(t("মোবাইল নম্বর", "Mobile Number"))
                password = st.text_input(t("পাসওয়ার্ড", "Password"), type="password")
                submitted = st.form_submit_button(t("লগইন", "Login"))
                if submitted:
                    if admin_login(mobile, password):
                        st.success(t("লগইন সফল", "Login successful"))
                        st.rerun()
                    else:
                        st.error(t("ভুল মোবাইল বা পাসওয়ার্ড", "Invalid mobile or password"))
        st.stop()

    # লগইন থাকলে সাইডবার ও কন্টেন্ট
    with st.sidebar:
        st.image("https://via.placeholder.com/200x80?text=Oikko+Uddog", use_column_width=True)
        if st.session_state.user_type == 'admin':
            menu = st.radio(
                t("মেনু", "Menu"),
                [t("🏠 ড্যাশবোর্ড", "🏠 Dashboard"),
                 t("➕ নতুন সদস্য", "➕ New Member"),
                 t("✏️ সদস্য ব্যবস্থাপনা", "✏️ Member Management"),
                 t("💵 টাকা জমা", "💵 Deposit"),
                 t("💰 লেনদেন ব্যবস্থাপনা", "💰 Transactions"),
                 t("🔗 সদস্য লিংক", "🔗 Member Links"),
                 t("💸 খরচ ব্যবস্থাপনা", "💸 Expenses"),
                 t("🏧 ফান্ড ব্যবস্থাপনা", "🏧 Fund"),
                 t("📊 রিপোর্ট", "📊 Reports"),
                 t("📥 পিডিএফ ডাউনলোড", "📥 PDF Download"),
                 t("📧 ইমেইল টেস্ট", "📧 Email Test"),
                 t("🎲 লটারি", "🎲 Lottery")]
            )
        else:
            menu = t("সদস্য প্যানেল", "Member Panel")

        if st.button(t("লগআউট", "Logout")):
            st.session_state.logged_in = False
            st.rerun()

    if st.session_state.user_type == 'admin':
        if menu == t("🏠 ড্যাশবোর্ড", "🏠 Dashboard"):
            admin_dashboard()
        elif menu == t("➕ নতুন সদস্য", "➕ New Member"):
            new_member_registration()
        elif menu == t("✏️ সদস্য ব্যবস্থাপনা", "✏️ Member Management"):
            member_management()
        elif menu == t("💵 টাকা জমা", "💵 Deposit"):
            deposit_management()
        elif menu == t("💰 লেনদেন ব্যবস্থাপনা", "💰 Transactions"):
            transaction_management()
        elif menu == t("🔗 সদস্য লিংক", "🔗 Member Links"):
            member_links()
        elif menu == t("💸 খরচ ব্যবস্থাপনা", "💸 Expenses"):
            expense_management()
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
