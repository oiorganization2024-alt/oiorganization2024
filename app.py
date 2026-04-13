import streamlit as st
import sqlite3
import pandas as pd
import random
import string
import os
import shutil
import time
from datetime import datetime, date
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ─── Config ───────────────────────────────────────────────────────────────────
DB_PATH = "somiti.db"
ADMIN_PHONE = "01700000000"
ADMIN_PASSWORD = "admin123"

BN_MONTHS = ["জানুয়ারি","ফেব্রুয়ারি","মার্চ","এপ্রিল","মে","জুন",
              "জুলাই","আগস্ট","সেপ্টেম্বর","অক্টোবর","নভেম্বর","ডিসেম্বর"]
EN_MONTHS = ["January","February","March","April","May","June",
             "July","August","September","October","November","December"]

EXPENSE_CATEGORIES = ["অফিস খরচ","যাতায়াত","খাওয়া-দাওয়া","ইউটিলিটি","বিবিধ"]

st.set_page_config(
    page_title="ঐক্য উদ্যোগ সংস্থা",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── CSS ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Hind+Siliguri:wght@300;400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Hind Siliguri', sans-serif !important; }
.stApp { background: linear-gradient(135deg, #0d1117 0%, #161b22 100%); color: #e6edf3; }
[data-testid="stSidebar"] { background: linear-gradient(180deg, #0d1117 0%, #161b22 100%) !important; border-right: 1px solid #30363d; }
[data-testid="stSidebar"] * { color: #e6edf3 !important; }
.main-header {
    background: linear-gradient(135deg, #1a5276 0%, #2980b9 100%);
    padding: 20px 24px; border-radius: 12px; margin-bottom: 20px;
    box-shadow: 0 4px 20px rgba(41,128,185,0.3);
}
.main-header h1 { color: #ffffff !important; margin: 0; font-size: 1.8rem; }
.main-header p { color: #bee3f8 !important; margin: 4px 0 0 0; font-size: 0.95rem; }
.kpi-card {
    background: #21262d; border: 1px solid #30363d; border-radius: 12px;
    padding: 20px; text-align: center; transition: transform 0.2s;
}
.kpi-card:hover { transform: translateY(-2px); border-color: #58a6ff; }
.kpi-value { font-size: 2rem; font-weight: 700; color: #58a6ff; }
.kpi-label { font-size: 0.85rem; color: #8b949e; margin-top: 4px; }
.kpi-icon { font-size: 1.5rem; margin-bottom: 8px; }
.total-box {
    background: linear-gradient(135deg, #1e8449 0%, #27ae60 100%);
    padding: 20px; border-radius: 12px; text-align: center; color: white;
}
.cash-box {
    background: linear-gradient(135deg, #d35400 0%, #e67e22 100%);
    padding: 20px; border-radius: 12px; text-align: center; color: white;
}
.member-card {
    background: #21262d; border: 1px solid #30363d; border-radius: 10px;
    padding: 16px; margin-bottom: 12px;
}
.badge-active { background: #1e8449; color: white; padding: 2px 10px; border-radius: 20px; font-size: 0.8rem; }
.badge-inactive { background: #922b21; color: white; padding: 2px 10px; border-radius: 20px; font-size: 0.8rem; }
.stButton > button {
    background: linear-gradient(135deg, #238636 0%, #2ea043 100%) !important;
    color: white !important; border: none !important; border-radius: 8px !important;
    font-family: 'Hind Siliguri', sans-serif !important;
}
.stButton > button:hover { opacity: 0.9 !important; }
.stTextInput > div > div > input, .stSelectbox > div > div, .stNumberInput > div > div > input {
    background: #0d1117 !important; color: #e6edf3 !important; border: 1px solid #30363d !important;
    border-radius: 8px !important;
}
.stDataFrame { background: #21262d !important; border-radius: 10px; }
div[data-testid="stExpander"] { background: #21262d; border: 1px solid #30363d; border-radius: 10px; }
.stTabs [data-baseweb="tab"] { color: #8b949e !important; }
.stTabs [aria-selected="true"] { color: #58a6ff !important; border-bottom-color: #58a6ff !important; }
.stAlert { border-radius: 8px !important; }
hr { border-color: #30363d !important; }
.sidebar-title { font-size: 1.1rem; font-weight: 600; color: #58a6ff; margin-bottom: 16px; }
</style>
""", unsafe_allow_html=True)

# ─── Language helper ───────────────────────────────────────────────────────────
def t(bn, en=""):
    lang = st.session_state.get("language", "bn")
    return bn if lang == "bn" else (en or bn)

# ─── DB helpers ───────────────────────────────────────────────────────────────
def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_database():
    conn = get_conn()
    c = conn.cursor()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS members (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        phone TEXT UNIQUE NOT NULL,
        email TEXT DEFAULT '',
        password TEXT NOT NULL,
        total_savings REAL DEFAULT 0,
        monthly_savings REAL DEFAULT 500,
        join_date TEXT,
        status TEXT DEFAULT 'active'
    );
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        member_id TEXT,
        amount REAL,
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
        created_at TEXT
    );
    CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        description TEXT,
        amount REAL,
        date TEXT,
        category TEXT
    );
    CREATE TABLE IF NOT EXISTS withdrawals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        amount REAL,
        description TEXT,
        withdrawn_by TEXT,
        previous_balance REAL,
        current_balance REAL,
        created_at TEXT
    );
    CREATE TABLE IF NOT EXISTS fund_transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type TEXT,
        amount REAL,
        description TEXT,
        date TEXT,
        previous_balance REAL,
        current_balance REAL,
        created_at TEXT
    );
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    );
    """)
    c.execute("INSERT OR IGNORE INTO settings VALUES ('start_date', ?)", (str(date.today()),))
    conn.commit()
    conn.close()

def generate_member_id():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM members")
    count = c.fetchone()[0]
    conn.close()
    return str(10001 + count)

def generate_password():
    return ''.join(random.choices(string.digits, k=6))

def safe_float(val, default=0.0):
    try:
        return float(val) if val is not None else default
    except (TypeError, ValueError):
        return default

def get_total_savings():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT SUM(total_savings) FROM members WHERE status='active'")
    r = c.fetchone()[0]
    conn.close()
    return safe_float(r)

def get_total_expenses():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT SUM(amount) FROM expenses")
    r = c.fetchone()[0]
    conn.close()
    return safe_float(r)

def get_total_withdrawals():
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT SUM(amount) FROM withdrawals")
    r = c.fetchone()[0]
    conn.close()
    return safe_float(r)

def get_cash_balance():
    return get_total_savings() - get_total_expenses() - get_total_withdrawals()

def get_members(status=None):
    conn = get_conn()
    q = "SELECT * FROM members"
    if status:
        q += f" WHERE status='{status}'"
    q += " ORDER BY id"
    df = pd.read_sql_query(q, conn)
    conn.close()
    return df

def get_paid_member_ids(month, year):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT DISTINCT member_id FROM transactions WHERE month=? AND year=?", (month, year))
    ids = {row[0] for row in c.fetchall()}
    conn.close()
    return ids

def get_month_collection(month, year):
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT SUM(amount) FROM transactions WHERE month=? AND year=?", (month, year))
    r = c.fetchone()[0]
    conn.close()
    return safe_float(r)

def add_transaction(member_id, amount, deposit_date, late_fee=0):
    conn = get_conn()
    c = conn.cursor()
    d = deposit_date
    month_bn = BN_MONTHS[d.month - 1]
    month_en = EN_MONTHS[d.month - 1]
    full_date_bn = f"{d.day} {month_bn} {d.year}"
    full_date_en = f"{d.day} {month_en} {d.year}"
    date_iso = d.isoformat()
    created_at = datetime.now().isoformat()
    try:
        c.execute("""
            INSERT INTO transactions (member_id, amount, transaction_type, day, month, year,
                month_name, month_name_en, full_date, full_date_en, date_iso, late_fee, created_at)
            VALUES (?, ?, 'deposit', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (member_id, amount, d.day, d.month, d.year,
              month_bn, month_en, full_date_bn, full_date_en, date_iso, late_fee, created_at))
        c.execute("UPDATE members SET total_savings = total_savings + ? WHERE id = ?", (amount, member_id))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        st.error(f"Error: {e}")
        return False
    finally:
        conn.close()

def delete_transaction(txn_id, amount, member_id):
    conn = get_conn()
    c = conn.cursor()
    try:
        c.execute("DELETE FROM transactions WHERE id=?", (txn_id,))
        c.execute("UPDATE members SET total_savings = total_savings - ? WHERE id=?", (amount, member_id))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        st.error(f"Error: {e}")
        return False
    finally:
        conn.close()

def add_expense(desc, amount, exp_date, category):
    conn = get_conn()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO expenses (description, amount, date, category) VALUES (?,?,?,?)",
                  (desc, amount, str(exp_date), category))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        return False
    finally:
        conn.close()

def add_fund_transaction(ftype, amount, desc, fdate):
    conn = get_conn()
    c = conn.cursor()
    prev = get_cash_balance()
    curr = prev + amount if ftype == 'deposit' else prev - amount
    try:
        c.execute("""INSERT INTO fund_transactions (type, amount, description, date, previous_balance, current_balance, created_at)
                     VALUES (?,?,?,?,?,?,?)""",
                  (ftype, amount, desc, str(fdate), prev, curr, datetime.now().isoformat()))
        if ftype == 'withdrawal':
            c.execute("""INSERT INTO withdrawals (date, amount, description, withdrawn_by, previous_balance, current_balance, created_at)
                         VALUES (?,?,?,?,?,?,?)""",
                      (str(fdate), amount, desc, 'Admin', prev, curr, datetime.now().isoformat()))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        return False
    finally:
        conn.close()

# ─── Session init ─────────────────────────────────────────────────────────────
if "language" not in st.session_state:
    st.session_state.language = "bn"
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_type" not in st.session_state:
    st.session_state.user_type = None
if "member_id" not in st.session_state:
    st.session_state.member_id = None

init_database()

# ─── LOGIN PAGE ───────────────────────────────────────────────────────────────
def show_login():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
        <div style="background:linear-gradient(135deg,#1a5276,#2980b9);padding:32px;border-radius:16px;text-align:center;margin-bottom:24px;">
            <div style="font-size:3rem">🏦</div>
            <h1 style="color:white;margin:8px 0 4px">ঐক্য উদ্যোগ সংস্থা</h1>
            <p style="color:#bee3f8;margin:0">Oikko Uddog Songstha</p>
        </div>
        """, unsafe_allow_html=True)

        tab_admin, tab_member = st.tabs(["🔑 এডমিন লগইন", "👤 সদস্য লগইন"])

        with tab_admin:
            with st.form("admin_login"):
                phone = st.text_input("মোবাইল নম্বর", placeholder="01XXXXXXXXX")
                pwd = st.text_input("পাসওয়ার্ড", type="password")
                if st.form_submit_button("লগইন করুন", use_container_width=True):
                    if phone == ADMIN_PHONE and pwd == ADMIN_PASSWORD:
                        st.session_state.logged_in = True
                        st.session_state.user_type = "admin"
                        st.rerun()
                    else:
                        st.error("ভুল মোবাইল নম্বর বা পাসওয়ার্ড!")

        with tab_member:
            with st.form("member_login"):
                mid = st.text_input("সদস্য আইডি", placeholder="10001")
                email = st.text_input("ইমেইল")
                mpwd = st.text_input("পাসওয়ার্ড", type="password")
                if st.form_submit_button("লগইন করুন", use_container_width=True):
                    conn = get_conn()
                    c = conn.cursor()
                    c.execute("SELECT * FROM members WHERE id=? AND email=? AND password=? AND status='active'",
                              (mid, email, mpwd))
                    m = c.fetchone()
                    conn.close()
                    if m:
                        st.session_state.logged_in = True
                        st.session_state.user_type = "member"
                        st.session_state.member_id = mid
                        st.rerun()
                    else:
                        st.error("ভুল তথ্য! অথবা আপনার অ্যাকাউন্ট নিষ্ক্রিয়।")

# ─── ADMIN PANEL ──────────────────────────────────────────────────────────────
def show_admin():
    with st.sidebar:
        st.markdown('<p class="sidebar-title">🏦 ঐক্য উদ্যোগ সংস্থা</p>', unsafe_allow_html=True)
        lang = st.selectbox("ভাষা / Language", ["বাংলা", "English"], label_visibility="collapsed")
        st.session_state.language = "bn" if lang == "বাংলা" else "en"
        st.markdown("---")
        menu = st.radio("মেনু", [
            "🏠 ড্যাশবোর্ড",
            "➕ নতুন সদস্য",
            "✏️ সদস্য ব্যবস্থাপনা",
            "💵 টাকা জমা",
            "💰 লেনদেন",
            "🔗 সদস্য লিংক",
            "💸 খরচ",
            "🏧 ফান্ড ব্যবস্থাপনা",
            "📊 রিপোর্ট",
            "🎲 লটারি",
        ], label_visibility="collapsed")
        st.markdown("---")
        if st.button("🚪 লগআউট", use_container_width=True):
            for k in ["logged_in", "user_type", "member_id"]:
                st.session_state[k] = None if k == "member_id" else False
            st.rerun()

    # Header
    now = datetime.now()
    st.markdown(f"""
    <div class="main-header">
        <h1>🏦 ঐক্য উদ্যোগ সংস্থা — এডমিন প্যানেল</h1>
        <p>{now.strftime('%d %B %Y')} | {BN_MONTHS[now.month-1]} {now.year}</p>
    </div>
    """, unsafe_allow_html=True)

    # ── DASHBOARD ──
    if "ড্যাশবোর্ড" in menu:
        col1, col2, col3, col4 = st.columns(4)
        members_df = get_members()
        total_members = len(members_df[members_df['status'] == 'active'])
        total_savings = get_total_savings()
        this_month = get_month_collection(now.month, now.year)
        paid_ids = get_paid_member_ids(now.month, now.year)
        active_ids = set(members_df[members_df['status'] == 'active']['id'].tolist())
        due_count = len(active_ids - paid_ids)

        with col1:
            st.markdown(f'<div class="kpi-card"><div class="kpi-icon">👥</div><div class="kpi-value">{total_members}</div><div class="kpi-label">মোট সক্রিয় সদস্য</div></div>', unsafe_allow_html=True)
        with col2:
            st.markdown(f'<div class="kpi-card"><div class="kpi-icon">💰</div><div class="kpi-value">৳{total_savings:,.0f}</div><div class="kpi-label">মোট জমা</div></div>', unsafe_allow_html=True)
        with col3:
            st.markdown(f'<div class="kpi-card"><div class="kpi-icon">📅</div><div class="kpi-value">৳{this_month:,.0f}</div><div class="kpi-label">এই মাসের কালেকশন</div></div>', unsafe_allow_html=True)
        with col4:
            st.markdown(f'<div class="kpi-card"><div class="kpi-icon">⚠️</div><div class="kpi-value">{due_count}</div><div class="kpi-label">বকেয়াদার সংখ্যা</div></div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        col_t, col_c = st.columns(2)
        with col_t:
            st.markdown(f'<div class="total-box"><h3>💰 মোট সঞ্চয়</h3><h2>৳ {total_savings:,.2f}</h2></div>', unsafe_allow_html=True)
        with col_c:
            cash = get_cash_balance()
            st.markdown(f'<div class="cash-box"><h3>🏧 ক্যাশ ব্যালেন্স</h3><h2>৳ {cash:,.2f}</h2></div>', unsafe_allow_html=True)

        if st.button("🔄 রিফ্রেশ করুন"):
            st.rerun()

    # ── NEW MEMBER ──
    elif "নতুন সদস্য" in menu:
        st.subheader("➕ নতুন সদস্য নিবন্ধন")
        with st.form("new_member"):
            name = st.text_input("নাম *")
            phone = st.text_input("মোবাইল নম্বর *")
            email = st.text_input("ইমেইল (ঐচ্ছিক)")
            monthly = st.number_input("মাসিক কিস্তি (৳)", min_value=100, value=500, step=100)
            submitted = st.form_submit_button("✅ নিবন্ধন করুন", use_container_width=True)
            if submitted:
                if not name or not phone:
                    st.error("নাম ও মোবাইল নম্বর আবশ্যক!")
                else:
                    mid = generate_member_id()
                    pwd = generate_password()
                    conn = get_conn()
                    c = conn.cursor()
                    try:
                        c.execute("INSERT INTO members (id,name,phone,email,password,monthly_savings,join_date) VALUES (?,?,?,?,?,?,?)",
                                  (mid, name, phone, email, pwd, monthly, str(date.today())))
                        conn.commit()
                        st.success(f"✅ সফলভাবে নিবন্ধন হয়েছে!")
                        st.info(f"**সদস্য আইডি:** {mid}  |  **পাসওয়ার্ড:** {pwd}")
                        st.balloons()
                    except sqlite3.IntegrityError:
                        st.error("এই মোবাইল নম্বর আগে থেকেই আছে!")
                    finally:
                        conn.close()

    # ── MANAGE MEMBERS ──
    elif "সদস্য ব্যবস্থাপনা" in menu:
        st.subheader("✏️ সদস্য ব্যবস্থাপনা")
        members_df = get_members()
        if members_df.empty:
            st.info("কোনো সদস্য নেই।")
        else:
            for _, row in members_df.iterrows():
                with st.expander(f"{'🟢' if row['status']=='active' else '🔴'} {row['name']} (ID: {row['id']}) — ৳{row['total_savings']:,.0f}"):
                    c1, c2 = st.columns(2)
                    with c1:
                        st.write(f"📱 {row['phone']}"); st.write(f"📧 {row['email'] or 'N/A'}")
                        st.write(f"💰 মাসিক কিস্তি: ৳{row['monthly_savings']}")
                    with c2:
                        st.write(f"📅 যোগদান: {row['join_date']}")
                        st.write(f"🔑 পাসওয়ার্ড: {row['password']}")

                    b1, b2, b3, b4 = st.columns(4)
                    with b1:
                        if st.button("✏️ এডিট", key=f"edit_{row['id']}"):
                            st.session_state[f"editing_{row['id']}"] = True
                    with b2:
                        new_pwd = generate_password()
                        if st.button("🔑 পাসওয়ার্ড রিসেট", key=f"pwd_{row['id']}"):
                            conn = get_conn()
                            conn.execute("UPDATE members SET password=? WHERE id=?", (new_pwd, row['id']))
                            conn.commit(); conn.close()
                            st.success(f"নতুন পাসওয়ার্ড: {new_pwd}")
                    with b3:
                        toggle_lbl = "🔴 নিষ্ক্রিয় করুন" if row['status']=='active' else "🟢 সক্রিয় করুন"
                        if st.button(toggle_lbl, key=f"tog_{row['id']}"):
                            ns = 'inactive' if row['status']=='active' else 'active'
                            conn = get_conn()
                            conn.execute("UPDATE members SET status=? WHERE id=?", (ns, row['id']))
                            conn.commit(); conn.close(); st.rerun()
                    with b4:
                        if st.button("🗑️ ডিলিট", key=f"del_{row['id']}"):
                            st.session_state[f"confirm_del_{row['id']}"] = True

                    if st.session_state.get(f"confirm_del_{row['id']}"):
                        st.warning(f"⚠️ আপনি কি **{row['name']}** কে মুছে ফেলতে চান?")
                        dc1, dc2 = st.columns(2)
                        with dc1:
                            if st.button("✅ হ্যাঁ, মুছুন", key=f"yes_{row['id']}"):
                                conn = get_conn()
                                conn.execute("DELETE FROM members WHERE id=?", (row['id'],))
                                conn.execute("DELETE FROM transactions WHERE member_id=?", (row['id'],))
                                conn.commit(); conn.close()
                                st.session_state.pop(f"confirm_del_{row['id']}", None)
                                st.rerun()
                        with dc2:
                            if st.button("❌ না", key=f"no_{row['id']}"):
                                st.session_state.pop(f"confirm_del_{row['id']}", None)
                                st.rerun()

                    if st.session_state.get(f"editing_{row['id']}"):
                        with st.form(f"edit_form_{row['id']}"):
                            en = st.text_input("নাম", value=row['name'])
                            ep = st.text_input("মোবাইল", value=row['phone'])
                            ee = st.text_input("ইমেইল", value=row['email'])
                            em = st.number_input("মাসিক কিস্তি", value=float(row['monthly_savings']), min_value=100.0)
                            if st.form_submit_button("💾 সংরক্ষণ করুন"):
                                conn = get_conn()
                                conn.execute("UPDATE members SET name=?,phone=?,email=?,monthly_savings=? WHERE id=?",
                                             (en, ep, ee, em, row['id']))
                                conn.commit(); conn.close()
                                st.session_state.pop(f"editing_{row['id']}", None)
                                st.rerun()

    # ── DEPOSIT ──
    elif "টাকা জমা" in menu:
        st.subheader("💵 টাকা জমা")
        now = datetime.now()
        members_df = get_members('active')
        paid_ids = get_paid_member_ids(now.month, now.year)
        paid_df = members_df[members_df['id'].isin(paid_ids)]
        unpaid_df = members_df[~members_df['id'].isin(paid_ids)]

        tab_paid, tab_unpaid = st.tabs([f"✅ জমা দিয়েছে ({len(paid_df)})", f"❌ জমা দেয়নি ({len(unpaid_df)})"])

        with tab_paid:
            if paid_df.empty:
                st.info("এই মাসে এখনো কেউ জমা দেয়নি।")
            else:
                st.dataframe(paid_df[['id','name','phone','total_savings']].rename(columns={
                    'id':'আইডি','name':'নাম','phone':'মোবাইল','total_savings':'মোট জমা'}), use_container_width=True)

        with tab_unpaid:
            if unpaid_df.empty:
                st.success("🎉 সবাই এই মাসে জমা দিয়েছে!")
            else:
                for _, row in unpaid_df.iterrows():
                    with st.expander(f"💳 {row['name']} (ID: {row['id']}) — মাসিক: ৳{row['monthly_savings']:,.0f}"):
                        with st.form(f"deposit_{row['id']}"):
                            dep_date = st.date_input("তারিখ", value=date.today(), key=f"dd_{row['id']}")
                            months = st.number_input("কত মাসের জমা", min_value=1, max_value=12, value=1, key=f"dm_{row['id']}")
                            late = st.number_input("লেট ফি (৳)", min_value=0.0, value=0.0, key=f"dl_{row['id']}")
                            total_amt = row['monthly_savings'] * months + late
                            st.info(f"মোট পরিমাণ: ৳ {total_amt:,.0f}")
                            if st.form_submit_button("✅ জমা নিন", use_container_width=True):
                                if add_transaction(row['id'], total_amt, dep_date, late):
                                    st.success(f"✅ {row['name']} এর জমা সফল!")
                                    st.balloons()
                                    time.sleep(1.5)
                                    st.rerun()

    # ── TRANSACTIONS ──
    elif "লেনদেন" in menu:
        st.subheader("💰 লেনদেন ব্যবস্থাপনা")
        members_df = get_members()
        if members_df.empty:
            st.info("কোনো সদস্য নেই।")
        else:
            options = {f"{r['name']} ({r['id']})": r['id'] for _, r in members_df.iterrows()}
            selected = st.selectbox("সদস্য নির্বাচন করুন", list(options.keys()))
            mid = options[selected]
            conn = get_conn()
            txn_df = pd.read_sql_query("SELECT * FROM transactions WHERE member_id=? ORDER BY date_iso DESC", conn, params=(mid,))
            conn.close()
            if txn_df.empty:
                st.info("কোনো লেনদেন নেই।")
            else:
                for _, tx in txn_df.iterrows():
                    c1, c2, c3 = st.columns([4, 1, 1])
                    with c1:
                        st.write(f"📅 {tx['full_date_en']} | ৳{tx['amount']:,.0f} | লেট ফি: ৳{tx['late_fee']:.0f}")
                    with c2:
                        if st.button("🗑️", key=f"dtx_{tx['id']}"):
                            if delete_transaction(tx['id'], tx['amount'], mid):
                                st.rerun()

    # ── MEMBER LINKS ──
    elif "লিংক" in menu:
        st.subheader("🔗 সদস্য লগইন লিংক")
        members_df = get_members('active')
        base_url = "https://your-app.streamlit.app"
        for _, row in members_df.iterrows():
            link = f"{base_url}/?member_id={row['id']}"
            with st.expander(f"🔗 {row['name']} (ID: {row['id']})"):
                st.code(link)
                st.write(f"🔑 পাসওয়ার্ড: **{row['password']}**")
                st.write(f"📧 ইমেইল: {row['email'] or 'N/A'}")

    # ── EXPENSES ──
    elif "খরচ" in menu:
        st.subheader("💸 খরচ ব্যবস্থাপনা")
        with st.form("add_expense"):
            desc = st.text_input("বিবরণ")
            amt = st.number_input("পরিমাণ (৳)", min_value=1.0, value=100.0)
            cat = st.selectbox("ক্যাটাগরি", EXPENSE_CATEGORIES)
            exp_date = st.date_input("তারিখ", value=date.today())
            if st.form_submit_button("➕ যোগ করুন"):
                if desc:
                    if add_expense(desc, amt, exp_date, cat):
                        st.success("✅ খরচ যোগ হয়েছে!"); st.rerun()

        conn = get_conn()
        exp_df = pd.read_sql_query("SELECT * FROM expenses ORDER BY date DESC", conn)
        conn.close()
        if not exp_df.empty:
            total_exp = exp_df['amount'].sum()
            st.metric("মোট খরচ", f"৳ {total_exp:,.0f}")
            for _, ex in exp_df.iterrows():
                c1, c2 = st.columns([5, 1])
                with c1:
                    st.write(f"📋 {ex['date']} | {ex['category']} | {ex['description']} | ৳{ex['amount']:,.0f}")
                with c2:
                    if st.button("🗑️", key=f"dex_{ex['id']}"):
                        conn = get_conn()
                        conn.execute("DELETE FROM expenses WHERE id=?", (ex['id'],))
                        conn.commit(); conn.close(); st.rerun()

    # ── FUND MANAGEMENT ──
    elif "ফান্ড" in menu:
        st.subheader("🏧 ফান্ড ব্যবস্থাপনা")
        cash = get_cash_balance()
        st.markdown(f'<div class="cash-box"><h3>🏧 বর্তমান ক্যাশ ব্যালেন্স</h3><h2>৳ {cash:,.2f}</h2></div>', unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        tab1, tab2, tab3 = st.tabs(["💵 জমা", "📤 উত্তোলন", "📋 ইতিহাস"])
        with tab1:
            with st.form("fund_dep"):
                fa = st.number_input("পরিমাণ (৳)", min_value=1.0, value=1000.0)
                fd = st.text_input("বিবরণ")
                if st.form_submit_button("✅ জমা করুন"):
                    if add_fund_transaction('deposit', fa, fd, date.today()):
                        st.success("✅ জমা সফল!"); st.rerun()
        with tab2:
            with st.form("fund_with"):
                wa = st.number_input("পরিমাণ (৳)", min_value=1.0, value=1000.0)
                wd = st.text_input("বিবরণ")
                wdate = st.date_input("তারিখ", value=date.today())
                if st.form_submit_button("✅ উত্তোলন করুন"):
                    if wa > cash:
                        st.error(f"অপর্যাপ্ত ব্যালেন্স! বর্তমান: ৳{cash:,.0f}")
                    elif add_fund_transaction('withdrawal', wa, wd, wdate):
                        st.success("✅ উত্তোলন সফল!"); st.rerun()
        with tab3:
            conn = get_conn()
            ft_df = pd.read_sql_query("SELECT * FROM fund_transactions ORDER BY date DESC", conn)
            conn.close()
            if not ft_df.empty:
                st.dataframe(ft_df[['date','type','amount','description','current_balance']].rename(columns={
                    'date':'তারিখ','type':'ধরন','amount':'পরিমাণ',
                    'description':'বিবরণ','current_balance':'ব্যালেন্স'}), use_container_width=True)

    # ── REPORTS ──
    elif "রিপোর্ট" in menu:
        st.subheader("📊 রিপোর্ট")
        conn = get_conn()
        txn_df = pd.read_sql_query("SELECT month, year, month_name_en, SUM(amount) as total FROM transactions GROUP BY year, month ORDER BY year, month", conn)
        conn.close()
        if not txn_df.empty:
            st.bar_chart(txn_df.set_index('month_name_en')['total'])

        members_df = get_members('active')
        now = datetime.now()
        paid_ids = get_paid_member_ids(now.month, now.year)
        due_df = members_df[~members_df['id'].isin(paid_ids)]
        st.markdown("### ⚠️ বকেয়াদার তালিকা")
        if due_df.empty:
            st.success("কোনো বকেয়া নেই!")
        else:
            st.dataframe(due_df[['id','name','phone','monthly_savings']].rename(columns={
                'id':'আইডি','name':'নাম','phone':'মোবাইল','monthly_savings':'মাসিক কিস্তি'}), use_container_width=True)

        conn = get_conn()
        wd_df = pd.read_sql_query("SELECT * FROM withdrawals ORDER BY date DESC", conn)
        conn.close()
        if not wd_df.empty:
            st.markdown("### 📤 উত্তোলন ইতিহাস")
            st.dataframe(wd_df[['date','amount','description','withdrawn_by','current_balance']], use_container_width=True)

    # ── LOTTERY ──
    elif "লটারি" in menu:
        st.subheader("🎲 লটারি")
        members_df = get_members('active')
        if members_df.empty:
            st.warning("কোনো সক্রিয় সদস্য নেই!")
        else:
            st.info(f"মোট {len(members_df)} জন সদস্যের মধ্য থেকে বিজয়ী নির্বাচন করা হবে।")
            if st.button("🎰 বিজয়ী নির্বাচন করুন!", use_container_width=True):
                winner = members_df.sample(1).iloc[0]
                st.markdown(f"""
                <div style="background:linear-gradient(135deg,#1a5276,#2980b9);padding:32px;border-radius:16px;text-align:center;">
                    <div style="font-size:3rem">🏆</div>
                    <h2 style="color:white">বিজয়ী!</h2>
                    <h3 style="color:#bee3f8">{winner['name']}</h3>
                    <p style="color:#e8f4f8">আইডি: {winner['id']} | মোবাইল: {winner['phone']}</p>
                </div>
                """, unsafe_allow_html=True)
                st.balloons()

# ─── MEMBER PANEL ─────────────────────────────────────────────────────────────
def show_member():
    mid = st.session_state.member_id
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM members WHERE id=?", (mid,))
    row = c.fetchone()
    conn.close()
    if not row:
        st.error("সদস্য তথ্য পাওয়া যায়নি!"); return

    cols = ['id','name','phone','email','password','total_savings','monthly_savings','join_date','status']
    member = dict(zip(cols, row))

    with st.sidebar:
        st.markdown(f'<p class="sidebar-title">👤 {member["name"]}</p>', unsafe_allow_html=True)
        st.write(f"আইডি: **{member['id']}**")
        st.markdown("---")
        if st.button("🚪 লগআউট"):
            for k in ["logged_in","user_type","member_id"]:
                st.session_state[k] = None if k == "member_id" else False
            st.rerun()

    st.markdown(f"""
    <div class="main-header">
        <h1>👤 {member['name']}</h1>
        <p>সদস্য আইডি: {member['id']} | যোগদান: {member['join_date']}</p>
    </div>
    """, unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["📊 ড্যাশবোর্ড", "🔑 পাসওয়ার্ড পরিবর্তন", "📋 রিপোর্ট"])

    with tab1:
        now = datetime.now()
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f'<div class="kpi-card"><div class="kpi-icon">💰</div><div class="kpi-value">৳{member["total_savings"]:,.0f}</div><div class="kpi-label">মোট জমা</div></div>', unsafe_allow_html=True)
        with c2:
            st.markdown(f'<div class="kpi-card"><div class="kpi-icon">📅</div><div class="kpi-value">৳{member["monthly_savings"]:,.0f}</div><div class="kpi-label">মাসিক কিস্তি</div></div>', unsafe_allow_html=True)
        with c3:
            paid_ids = get_paid_member_ids(now.month, now.year)
            paid_this_month = mid in paid_ids
            status_icon = "✅" if paid_this_month else "❌"
            status_text = "পরিশোধ করা হয়েছে" if paid_this_month else "বাকি আছে"
            st.markdown(f'<div class="kpi-card"><div class="kpi-icon">{status_icon}</div><div class="kpi-value" style="font-size:1rem">{status_text}</div><div class="kpi-label">এই মাসের স্ট্যাটাস</div></div>', unsafe_allow_html=True)

        st.markdown("### 📋 লেনদেন ইতিহাস")
        conn = get_conn()
        txn_df = pd.read_sql_query("SELECT full_date_en, amount, late_fee, created_at FROM transactions WHERE member_id=? ORDER BY date_iso DESC", conn, params=(mid,))
        conn.close()
        if txn_df.empty:
            st.info("কোনো লেনদেন নেই।")
        else:
            st.dataframe(txn_df.rename(columns={'full_date_en':'তারিখ','amount':'পরিমাণ','late_fee':'লেট ফি','created_at':'তৈরি হয়েছে'}), use_container_width=True)

    with tab2:
        with st.form("change_pwd"):
            new_pwd = st.text_input("নতুন পাসওয়ার্ড", type="password")
            confirm_pwd = st.text_input("পাসওয়ার্ড নিশ্চিত করুন", type="password")
            if st.form_submit_button("🔑 পাসওয়ার্ড পরিবর্তন করুন"):
                if not new_pwd:
                    st.error("পাসওয়ার্ড দিন!")
                elif new_pwd != confirm_pwd:
                    st.error("পাসওয়ার্ড মিলছে না!")
                else:
                    conn = get_conn()
                    conn.execute("UPDATE members SET password=? WHERE id=?", (new_pwd, mid))
                    conn.commit(); conn.close()
                    st.success("✅ পাসওয়ার্ড পরিবর্তন হয়েছে!")

    with tab3:
        st.info("📥 PDF ডাউনলোড ফিচার শীঘ্রই আসছে! ReportLab দিয়ে তৈরি হবে।")
        conn = get_conn()
        txn_df = pd.read_sql_query("SELECT * FROM transactions WHERE member_id=? ORDER BY date_iso DESC", conn, params=(mid,))
        conn.close()
        if not txn_df.empty:
            csv = txn_df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 CSV ডাউনলোড করুন", csv, f"transactions_{mid}.csv", "text/csv")

# ─── MAIN ─────────────────────────────────────────────────────────────────────
def main():
    if not st.session_state.logged_in:
        show_login()
    elif st.session_state.user_type == "admin":
        show_admin()
    elif st.session_state.user_type == "member":
        show_member()

if __name__ == "__main__":
    main()
