import streamlit as st
import sqlite3
import requests
import random
import string
import pandas as pd
from datetime import datetime, timedelta
from io import BytesIO

# ============================================
# কনফিগারেশন
# ============================================
TELEGRAM_BOT_TOKEN = "8752100386:AAEa-vMD4yPCKE0LPTFx-198Llbf8qZFgE8"
ADMIN_CHAT_ID = "8548828754"
ADMIN_MOBILE = "01766222373"
ADMIN_PASSWORD = "oio112024"
SOMITI_NAME = "ঐক্য উদ্যোগ সংস্থা"

# ============================================
# পেজ কনফিগ
# ============================================
st.set_page_config(
    page_title=SOMITI_NAME,
    page_icon="🌾",
    layout="wide"
)

# ============================================
# ডাটাবেজ সেটআপ
# ============================================
def init_database():
    conn = sqlite3.connect('somiti.db')
    c = conn.cursor()
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS members (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            phone TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            telegram_id TEXT,
            total_savings REAL DEFAULT 0,
            monthly_savings REAL DEFAULT 500,
            join_date TEXT,
            status TEXT DEFAULT 'active'
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id TEXT NOT NULL,
            amount REAL NOT NULL,
            transaction_type TEXT NOT NULL,
            month TEXT,
            date TEXT NOT NULL,
            note TEXT,
            late_fee REAL DEFAULT 0
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT NOT NULL,
            amount REAL NOT NULL,
            date TEXT NOT NULL,
            category TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

# ============================================
# টেলিগ্রাম মেসেজ
# ============================================
def send_telegram_message(chat_id, message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": chat_id, "text": message}
        response = requests.post(url, json=payload, timeout=10)
        return response.status_code == 200
    except:
        return False

def send_telegram_channel_message(message):
    return send_telegram_message(ADMIN_CHAT_ID, message)

# ============================================
# হেল্পার ফাংশন
# ============================================
def generate_member_id():
    conn = sqlite3.connect('somiti.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM members")
    count = c.fetchone()[0] + 1
    conn.close()
    return f"M-{count:03d}"

def generate_password(length=6):
    return ''.join(random.choices(string.digits, k=length))

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

def get_cash_balance():
    return get_total_savings() - get_total_expenses()

def get_current_month_collection():
    try:
        conn = sqlite3.connect('somiti.db')
        c = conn.cursor()
        current_month = datetime.now().strftime("%Y-%m")
        c.execute("SELECT SUM(amount) FROM transactions WHERE month = ?", (current_month,))
        total = c.fetchone()[0] or 0
        conn.close()
        return total
    except:
        return 0

def get_current_month_target():
    try:
        conn = sqlite3.connect('somiti.db')
        c = conn.cursor()
        c.execute("SELECT SUM(monthly_savings) FROM members WHERE status = 'active'")
        total = c.fetchone()[0] or 0
        conn.close()
        return total
    except:
        return 0

def get_current_month_defaulters_count():
    try:
        current_month = datetime.now().strftime("%Y-%m")
        conn = sqlite3.connect('somiti.db')
        c = conn.cursor()
        c.execute("SELECT DISTINCT member_id FROM transactions WHERE month = ?", (current_month,))
        paid = [row[0] for row in c.fetchall()]
        
        if paid:
            placeholders = ','.join(['?' for _ in paid])
            c.execute(f"""
                SELECT COUNT(*) FROM members 
                WHERE status = 'active' AND id NOT IN ({placeholders})
            """, paid)
        else:
            c.execute("SELECT COUNT(*) FROM members WHERE status = 'active'")
        
        count = c.fetchone()[0]
        conn.close()
        return count
    except:
        return 0

def search_members(search_term):
    conn = sqlite3.connect('somiti.db')
    c = conn.cursor()
    c.execute("""
        SELECT id, name, phone 
        FROM members 
        WHERE status = 'active' AND (id LIKE ? OR name LIKE ? OR phone LIKE ?)
        ORDER BY name
        LIMIT 20
    """, (f"%{search_term}%", f"%{search_term}%", f"%{search_term}%"))
    results = c.fetchall()
    conn.close()
    return results

def get_member_by_id_or_name(search_term):
    conn = sqlite3.connect('somiti.db')
    c = conn.cursor()
    c.execute("""
        SELECT id, name, phone, total_savings, monthly_savings, status, telegram_id
        FROM members 
        WHERE id = ? OR name LIKE ?
    """, (search_term, f"%{search_term}%"))
    result = c.fetchone()
    conn.close()
    return result

def pick_lottery_winner():
    conn = sqlite3.connect('somiti.db')
    c = conn.cursor()
    c.execute("""
        SELECT id, name, phone, total_savings, telegram_id 
        FROM members 
        WHERE status = 'active'
        ORDER BY RANDOM() 
        LIMIT 1
    """)
    winner = c.fetchone()
    conn.close()
    return winner

# ============================================
# UI স্টাইল (শুধু ডার্ক থিম)
# ============================================
def apply_dark_theme():
    st.markdown("""
    <style>
    /* মেইন ব্যাকগ্রাউন্ড */
    .stApp {
        background: linear-gradient(135deg, #0d1117 0%, #161b22 100%);
    }
    
    /* হেডার */
    .somiti-header {
        background: linear-gradient(135deg, #1a5276 0%, #2980b9 100%);
        padding: 25px;
        border-radius: 15px;
        margin-bottom: 25px;
        text-align: center;
        box-shadow: 0 10px 20px rgba(0,0,0,0.5);
        border: 1px solid #30363d;
    }
    .somiti-header h1 {
        color: white;
        font-size: 38px;
        font-weight: 800;
        margin: 0;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
        letter-spacing: 2px;
    }
    .somiti-header p {
        color: #a8d8ea;
        font-size: 16px;
        margin: 8px 0 0 0;
        font-weight: 400;
    }
    
    /* টোটাল বক্স */
    .total-box {
        background: linear-gradient(135deg, #1e8449 0%, #27ae60 100%);
        padding: 20px;
        border-radius: 15px;
        text-align: center;
        margin-bottom: 25px;
        box-shadow: 0 10px 20px rgba(0,0,0,0.5);
        border: 1px solid #30363d;
    }
    .total-box h2 {
        color: white;
        font-size: 32px;
        font-weight: 800;
        margin: 0;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
    }
    .total-box p {
        color: #d5f5e3;
        font-size: 14px;
        margin: 5px 0 0 0;
        font-weight: 500;
    }
    
    /* ক্যাশ বক্স */
    .cash-box {
        background: linear-gradient(135deg, #d35400 0%, #e67e22 100%);
        padding: 20px;
        border-radius: 15px;
        text-align: center;
        margin-bottom: 25px;
        box-shadow: 0 10px 20px rgba(0,0,0,0.5);
        border: 1px solid #30363d;
    }
    .cash-box h2 {
        color: white;
        font-size: 32px;
        font-weight: 800;
        margin: 0;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
    }
    .cash-box p {
        color: #fdebd0;
        font-size: 14px;
        margin: 5px 0 0 0;
        font-weight: 500;
    }
    
    /* KPI কার্ড */
    .kpi-card {
        background: #21262d;
        padding: 20px;
        border-radius: 12px;
        text-align: center;
        box-shadow: 0 4px 8px rgba(0,0,0,0.4);
        margin-bottom: 10px;
        border: 1px solid #30363d;
    }
    .kpi-card h3 {
        color: #c9d1d9;
        font-size: 28px;
        font-weight: 700;
        margin: 5px 0;
    }
    .kpi-card p {
        color: #8b949e;
        font-size: 14px;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    /* লটারি বক্স */
    .lottery-box {
        background: linear-gradient(135deg, #6c3483 0%, #8e44ad 100%);
        padding: 30px;
        border-radius: 20px;
        text-align: center;
        margin: 20px 0;
        box-shadow: 0 15px 30px rgba(0,0,0,0.6);
        border: 2px solid gold;
    }
    .lottery-box h3 {
        color: gold;
        font-size: 36px;
        font-weight: 800;
        margin: 0;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
    }
    .lottery-box p {
        color: white;
        font-size: 18px;
        margin: 10px 0;
    }
    
    /* লগইন কার্ড */
    .login-card {
        max-width: 420px;
        margin: 50px auto;
        padding: 40px;
        border-radius: 20px;
        box-shadow: 0 20px 40px rgba(0,0,0,0.6);
        background: #21262d;
        border: 1px solid #30363d;
    }
    .login-card h3 {
        color: #c9d1d9;
        font-size: 28px;
        font-weight: 700;
        margin-bottom: 25px;
        text-align: center;
    }
    
    /* মেম্বার ইনফো কার্ড */
    .member-info-card {
        background: #21262d;
        padding: 20px;
        border-radius: 12px;
        margin: 15px 0;
        border: 1px solid #30363d;
    }
    .member-info-card h4 {
        color: #c9d1d9;
        margin: 0 0 10px 0;
    }
    .member-info-card p {
        color: #8b949e;
        margin: 5px 0;
    }
    
    /* বাটন */
    .stButton > button {
        background: linear-gradient(135deg, #238636 0%, #2ea043 100%);
        color: white;
        font-weight: 600;
        border: none;
        border-radius: 8px;
        padding: 10px 20px;
        width: 100%;
        font-size: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        transition: all 0.3s ease;
        border: 1px solid #3fb950;
    }
    .stButton > button:hover {
        background: linear-gradient(135deg, #2ea043 0%, #3fb950 100%);
        box-shadow: 0 6px 12px rgba(0,0,0,0.4);
        transform: translateY(-2px);
        border-color: #56d364;
    }
    
    /* প্রাইমারি বাটন */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #1a5276 0%, #2980b9 100%);
        border: 1px solid #3498db;
    }
    .stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, #2980b9 0%, #3498db 100%);
        border-color: #5dade2;
    }
    
    /* ডিলিট/ডেঞ্জার বাটন */
    .stButton > button[kind="secondary"] {
        background: linear-gradient(135deg, #8b0000 0%, #b22222 100%);
        border: 1px solid #dc143c;
    }
    .stButton > button[kind="secondary"]:hover {
        background: linear-gradient(135deg, #b22222 0%, #dc143c 100%);
        border-color: #ff4444;
    }
    
    /* সাইডবার */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0d1117 0%, #161b22 100%);
        border-right: 1px solid #30363d;
    }
    section[data-testid="stSidebar"] * {
        color: #c9d1d9 !important;
    }
    section[data-testid="stSidebar"] .stRadio > div {
        background: #21262d;
        border-radius: 10px;
        padding: 10px;
        border: 1px solid #30363d;
    }
    
    /* মেট্রিক কার্ড */
    div[data-testid="metric-container"] {
        background: #21262d;
        border-radius: 12px;
        padding: 15px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.4);
        border: 1px solid #30363d;
    }
    div[data-testid="metric-container"] label {
        color: #8b949e !important;
    }
    div[data-testid="metric-container"] div {
        color: #c9d1d9 !important;
    }
    
    /* ডাটাফ্রেম/টেবিল */
    .stDataFrame {
        border-radius: 10px;
        overflow: hidden;
        box-shadow: 0 4px 8px rgba(0,0,0,0.4);
        border: 1px solid #30363d;
    }
    .stDataFrame th {
        background: #21262d !important;
        color: #c9d1d9 !important;
    }
    .stDataFrame td {
        background: #161b22 !important;
        color: #c9d1d9 !important;
    }
    
    /* ইনপুট ফিল্ড */
    .stTextInput > div > div > input,
    .stSelectbox > div > div,
    .stNumberInput > div > div > input,
    .stTextArea > div > div > textarea {
        background: #0d1117;
        border: 1px solid #30363d;
        color: #c9d1d9;
        border-radius: 8px;
        padding: 10px;
    }
    .stTextInput > div > div > input:focus,
    .stSelectbox > div > div:focus,
    .stNumberInput > div > div > input:focus {
        border-color: #1f6feb;
        box-shadow: 0 0 0 2px rgba(31,111,235,0.2);
    }
    
    /* ট্যাব */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: transparent;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0;
        padding: 12px 24px;
        background: #21262d;
        font-weight: 500;
        color: #8b949e;
        border: 1px solid #30363d;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #1a5276 0%, #2980b9 100%);
        color: white;
        border-color: #3498db;
    }
    
    /* এক্সপান্ডার */
    .streamlit-expanderHeader {
        background: #21262d;
        border-radius: 8px;
        border: 1px solid #30363d;
        color: #c9d1d9;
    }
    
    /* সাকসেস/এরর/ওয়ার্নিং মেসেজ */
    .stSuccess {
        background: #0d3320;
        border-left: 4px solid #3fb950;
        color: #d4edda;
        border-radius: 8px;
    }
    .stError {
        background: #3a1a1a;
        border-left: 4px solid #f85149;
        color: #f8d7da;
        border-radius: 8px;
    }
    .stWarning {
        background: #3a2a0a;
        border-left: 4px solid #d29922;
        color: #fff3cd;
        border-radius: 8px;
    }
    .stInfo {
        background: #1a2a3a;
        border-left: 4px solid #1f6feb;
        color: #d1ecf1;
        border-radius: 8px;
    }
    
    /* প্রগ্রেস বার */
    .stProgress > div > div {
        background: linear-gradient(90deg, #238636 0%, #3fb950 100%);
    }
    
    /* সিলেক্ট বক্স অপশন */
    select option {
        background: #21262d;
        color: #c9d1d9;
    }
    
    /* টেক্সট কালার */
    p, h1, h2, h3, h4, h5, h6, li, .stMarkdown, .stCaption {
        color: #c9d1d9 !important;
    }
    
    /* ডাউনলোড বাটন */
    .stDownloadButton > button {
        background: linear-gradient(135deg, #1a5276 0%, #2980b9 100%);
        color: white;
        border: 1px solid #3498db;
    }
    </style>
    """, unsafe_allow_html=True)

def show_header():
    total = get_total_savings()
    
    st.markdown(f"""
    <div class="somiti-header">
        <h1>🌾 {SOMITI_NAME} 🌾</h1>
        <p>সঞ্চয় ও ঋণ ব্যবস্থাপনা সিস্টেম</p>
    </div>
    
    <div class="total-box">
        <h2>💰 {total:,.0f} টাকা</h2>
        <p>সমিতির মোট জমা</p>
    </div>
    """, unsafe_allow_html=True)

def show_admin_header():
    total = get_total_savings()
    cash = get_cash_balance()
    
    st.markdown(f"""
    <div class="somiti-header">
        <h1>🌾 {SOMITI_NAME} 🌾</h1>
        <p>সঞ্চয় ও ঋণ ব্যবস্থাপনা সিস্টেম</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
        <div class="total-box">
            <h2>💰 {total:,.0f} টাকা</h2>
            <p>সমিতির মোট জমা</p>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="cash-box">
            <h2>💵 {cash:,.0f} টাকা</h2>
            <p>ক্যাশ ব্যালেন্স</p>
        </div>
        """, unsafe_allow_html=True)

def show_kpi_card(title, value, icon=""):
    st.markdown(f"""
    <div class="kpi-card">
        <p>{icon} {title}</p>
        <h3>{value}</h3>
    </div>
    """, unsafe_allow_html=True)

# ============================================
# সেশন স্টেট
# ============================================
def init_session():
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'user_type' not in st.session_state:
        st.session_state.user_type = None
    if 'member_id' not in st.session_state:
        st.session_state.member_id = None

# ============================================
# লগইন পেজ
# ============================================
def login_page():
    apply_dark_theme()
    show_header()
    
    with st.container():
        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        st.markdown("### 🔐 লগইন")
        
        phone = st.text_input("📱 মোবাইল নম্বর", placeholder="017XXXXXXXX", key="login_phone")
        password = st.text_input("🔑 পাসওয়ার্ড", type="password", key="login_pass")
        
        if st.button("প্রবেশ করুন", key="login_btn"):
            if phone == ADMIN_MOBILE and password == ADMIN_PASSWORD:
                st.session_state.logged_in = True
                st.session_state.user_type = 'admin'
                st.success("✅ এডমিন লগইন সফল!")
                st.rerun()
            else:
                try:
                    conn = sqlite3.connect('somiti.db')
                    c = conn.cursor()
                    c.execute("SELECT id, password, status FROM members WHERE phone = ?", (phone,))
                    result = c.fetchone()
                    conn.close()
                    
                    if result and result[2] != 'active':
                        st.error("❌ অ্যাকাউন্ট নিষ্ক্রিয়")
                    elif result and result[1] == password:
                        st.session_state.logged_in = True
                        st.session_state.user_type = 'member'
                        st.session_state.member_id = result[0]
                        st.success("✅ লগইন সফল!")
                        st.rerun()
                    else:
                        st.error("❌ ভুল মোবাইল বা পাসওয়ার্ড")
                except Exception as e:
                    st.error(f"❌ ডাটাবেজ এরর: {e}")
        
        st.markdown("---")
        st.caption(f"পাসওয়ার্ড ভুলে গেলে: {ADMIN_MOBILE}")
        st.markdown('</div>', unsafe_allow_html=True)

# ============================================
# এডমিন প্যানেল
# ============================================
def admin_panel():
    apply_dark_theme()
    show_admin_header()
    
    with st.sidebar:
        st.markdown("### 📋 এডমিন মেনু")
        st.caption(f"👑 {ADMIN_MOBILE}")
        
        menu = st.radio(
            "নির্বাচন করুন",
            ["🏠 ড্যাশবোর্ড", "➕ নতুন সদস্য", "✏️ সদস্য ব্যবস্থাপনা", "💵 টাকা জমা", 
             "💸 খরচ ব্যবস্থাপনা", "📊 রিপোর্ট", "🎲 লটারি", "🚪 লগআউট"],
            label_visibility="collapsed"
        )
    
    if menu == "🚪 লগআউট":
        for key in ['logged_in', 'user_type', 'member_id']:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()
    
    elif menu == "🏠 ড্যাশবোর্ড":
        st.markdown("### 🏠 এডমিন ড্যাশবোর্ড")
        
        col1, col2, col3, col4 = st.columns(4)
        
        try:
            conn = sqlite3.connect('somiti.db')
            c = conn.cursor()
            
            c.execute("SELECT COUNT(*) FROM members WHERE status = 'active'")
            total_members = c.fetchone()[0]
            with col1:
                show_kpi_card("মোট সদস্য", f"{total_members} জন", "👥")
            
            total_savings = get_total_savings()
            with col2:
                show_kpi_card("মোট জমা", f"{total_savings:,.0f} টাকা", "💰")
            
            month_collection = get_current_month_collection()
            with col3:
                show_kpi_card("এই মাসের জমা", f"{month_collection:,.0f} টাকা", "📅")
            
            defaulters = get_current_month_defaulters_count()
            with col4:
                show_kpi_card("বকেয়াদার", f"{defaulters} জন", "⚠️")
            
            conn.close()
        except Exception as e:
            st.error(f"KPI লোড করতে সমস্যা: {e}")
        
        st.markdown("---")
        
        st.subheader("📊 মাসিক কালেকশন প্রগ্রেস")
        target = get_current_month_target()
        collected = get_current_month_collection()
        
        if target > 0:
            progress = min(collected / target, 1.0)
            st.progress(progress)
            st.write(f"🎯 লক্ষ্য: {target:,.0f} টাকা | ✅ আদায়: {collected:,.0f} টাকা ({progress*100:.1f}%)")
        else:
            st.info("এখনো কোনো টার্গেট সেট করা হয়নি")
        
        st.markdown("---")
        
        st.subheader("📋 সাম্প্রতিক লেনদেন")
        try:
            conn = sqlite3.connect('somiti.db')
            c = conn.cursor()
            c.execute("""
                SELECT m.name, m.id, t.amount, t.date, t.month 
                FROM transactions t
                JOIN members m ON t.member_id = m.id
                ORDER BY t.id DESC LIMIT 10
            """)
            recent = c.fetchall()
            conn.close()
            
            if recent:
                df = pd.DataFrame(recent, columns=["নাম", "আইডি", "টাকা", "তারিখ", "মাস"])
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.info("এখনো কোনো লেনদেন হয়নি")
        except Exception as e:
            st.error(f"লেনদেন লোড করতে সমস্যা: {e}")
    
    elif menu == "➕ নতুন সদস্য":
        st.markdown("### ➕ নতুন সদস্য নিবন্ধন")
        
        with st.form("new_member_form"):
            name = st.text_input("নাম *")
            phone = st.text_input("মোবাইল নম্বর *", placeholder="017XXXXXXXX")
            telegram_id = st.text_input("টেলিগ্রাম চ্যাট আইডি *")
            monthly = st.number_input("মাসিক কিস্তি (টাকা)", value=500, step=50)
            
            submitted = st.form_submit_button("✅ সদস্য যোগ করুন", type="primary")
            
            if submitted:
                if not name or not phone or not telegram_id:
                    st.error("❌ সব ফিল্ড পূরণ করুন")
                elif phone == ADMIN_MOBILE:
                    st.error("❌ এটি এডমিনের মোবাইল")
                else:
                    try:
                        member_id = generate_member_id()
                        password = generate_password()
                        join_date = datetime.now().strftime("%Y-%m-%d")
                        
                        conn = sqlite3.connect('somiti.db')
                        c = conn.cursor()
                        c.execute("""
                            INSERT INTO members (id, name, phone, password, telegram_id, monthly_savings, join_date)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (member_id, name, phone, password, telegram_id, monthly, join_date))
                        conn.commit()
                        conn.close()
                        
                        welcome_msg = f"""🎉 {SOMITI_NAME}-এ স্বাগতম, {name}!

আপনার সদস্যপদ তৈরি হয়েছে।

🆔 আইডি: {member_id}
📱 মোবাইল: {phone}
🔑 পাসওয়ার্ড: {password}
💰 মাসিক কিস্তি: {monthly} টাকা

লগইন করে পাসওয়ার্ড পরিবর্তন করুন।"""
                        
                        send_telegram_message(telegram_id, welcome_msg)
                        
                        st.success(f"✅ সদস্য তৈরি হয়েছে!")
                        st.info(f"আইডি: {member_id} | পাসওয়ার্ড: {password}")
                        st.balloons()
                        
                    except sqlite3.IntegrityError:
                        st.error("❌ এই মোবাইল নম্বর ইতিমধ্যে নিবন্ধিত")
                    except Exception as e:
                        st.error(f"❌ এরর: {e}")
    
    elif menu == "✏️ সদস্য ব্যবস্থাপনা":
        st.markdown("### ✏️ সদস্য ব্যবস্থাপনা")
        
        search_term = st.text_input("🔍 নাম বা আইডি দিয়ে খুঁজুন", key="search_member")
        
        try:
            conn = sqlite3.connect('somiti.db')
            c = conn.cursor()
            
            if search_term:
                c.execute("""
                    SELECT id, name, phone, status, monthly_savings, telegram_id, total_savings
                    FROM members 
                    WHERE id LIKE ? OR name LIKE ? OR phone LIKE ?
                    ORDER BY name
                """, (f"%{search_term}%", f"%{search_term}%", f"%{search_term}%"))
            else:
                c.execute("SELECT id, name, phone, status, monthly_savings, telegram_id, total_savings FROM members ORDER BY name LIMIT 50")
            
            members = c.fetchall()
            conn.close()
            
            if members:
                for m in members:
                    member_id, name, phone, status, monthly, telegram, savings = m
                    monthly = float(monthly) if monthly else 500.0
                    telegram = telegram or ""
                    savings = float(savings) if savings else 0.0
                    
                    with st.expander(f"👤 {name} - {member_id} | 📱 {phone}"):
                        st.markdown(f"""
                        <div class="member-info-card">
                            <p><strong>💰 মোট জমা:</strong> {savings:,.0f} টাকা</p>
                            <p><strong>📅 মাসিক কিস্তি:</strong> {monthly:,.0f} টাকা</p>
                            <p><strong>📬 টেলিগ্রাম:</strong> {telegram or 'N/A'}</p>
                            <p><strong>🔄 স্ট্যাটাস:</strong> {'✅ সক্রিয়' if status == 'active' else '❌ নিষ্ক্রিয়'}</p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        col1, col2, col3, col4 = st.columns(4)
                        
                        with col1:
                            if st.button("📝 এডিট", key=f"edit_{member_id}", use_container_width=True):
                                st.session_state[f"show_edit_{member_id}"] = True
                        with col2:
                            if st.button("🔐 পাসওয়ার্ড", key=f"pass_{member_id}", use_container_width=True):
                                st.session_state[f"show_pass_{member_id}"] = True
                        with col3:
                            if st.button("🔄 স্ট্যাটাস", key=f"stat_{member_id}", use_container_width=True):
                                st.session_state[f"show_stat_{member_id}"] = True
                        with col4:
                            if st.button("🗑️ ডিলিট", key=f"del_{member_id}", use_container_width=True):
                                st.session_state[f"show_del_{member_id}"] = True
                        
                        # এডিট ফর্ম
                        if st.session_state.get(f"show_edit_{member_id}"):
                            with st.form(f"edit_form_{member_id}"):
                                new_name = st.text_input("নাম", value=name)
                                new_tel = st.text_input("টেলিগ্রাম", value=telegram)
                                new_mon = st.number_input("মাসিক কিস্তি", value=monthly, step=50.0)
                                
                                c1, c2 = st.columns(2)
                                with c1:
                                    if st.form_submit_button("💾 সেভ", type="primary"):
                                        conn = sqlite3.connect('somiti.db')
                                        c = conn.cursor()
                                        c.execute("UPDATE members SET name=?, telegram_id=?, monthly_savings=? WHERE id=?", 
                                                 (new_name, new_tel, new_mon, member_id))
                                        conn.commit()
                                        conn.close()
                                        st.success("✅ আপডেট হয়েছে!")
                                        del st.session_state[f"show_edit_{member_id}"]
                                        st.rerun()
                                with c2:
                                    if st.form_submit_button("❌ বাতিল"):
                                        del st.session_state[f"show_edit_{member_id}"]
                                        st.rerun()
                        
                        # পাসওয়ার্ড রিসেট
                        if st.session_state.get(f"show_pass_{member_id}"):
                            st.warning(f"⚠️ {name} এর পাসওয়ার্ড রিসেট করবেন?")
                            c1, c2 = st.columns(2)
                            with c1:
                                if st.button("✅ হ্যাঁ", key=f"yes_pass_{member_id}", type="primary"):
                                    new_pass = generate_password()
                                    conn = sqlite3.connect('somiti.db')
                                    c = conn.cursor()
                                    c.execute("UPDATE members SET password=? WHERE id=?", (new_pass, member_id))
                                    conn.commit()
                                    conn.close()
                                    if telegram:
                                        send_telegram_message(telegram, f"🔐 নতুন পাসওয়ার্ড: {new_pass}")
                                    st.success(f"✅ পাসওয়ার্ড: {new_pass}")
                                    del st.session_state[f"show_pass_{member_id}"]
                            with c2:
                                if st.button("❌ না", key=f"no_pass_{member_id}"):
                                    del st.session_state[f"show_pass_{member_id}"]
                                    st.rerun()
                        
                        # স্ট্যাটাস
                        if st.session_state.get(f"show_stat_{member_id}"):
                            st.info(f"বর্তমান: {'সক্রিয়' if status == 'active' else 'নিষ্ক্রিয়'}")
                            c1, c2 = st.columns(2)
                            with c1:
                                if st.button("✅ সক্রিয়", key=f"act_{member_id}", type="primary"):
                                    conn = sqlite3.connect('somiti.db')
                                    c = conn.cursor()
                                    c.execute("UPDATE members SET status='active' WHERE id=?", (member_id,))
                                    conn.commit()
                                    conn.close()
                                    st.success("✅ সক্রিয় হয়েছে!")
                                    del st.session_state[f"show_stat_{member_id}"]
                                    st.rerun()
                            with c2:
                                if st.button("❌ নিষ্ক্রিয়", key=f"deact_{member_id}"):
                                    conn = sqlite3.connect('somiti.db')
                                    c = conn.cursor()
                                    c.execute("UPDATE members SET status='inactive' WHERE id=?", (member_id,))
                                    conn.commit()
                                    conn.close()
                                    st.warning("⚠️ নিষ্ক্রিয় হয়েছে!")
                                    del st.session_state[f"show_stat_{member_id}"]
                                    st.rerun()
                        
                        # ডিলিট
                        if st.session_state.get(f"show_del_{member_id}"):
                            st.error(f"🗑️ {name} কে স্থায়ীভাবে ডিলিট করবেন?")
                            c1, c2 = st.columns(2)
                            with c1:
                                if st.button("✅ ডিলিট", key=f"yes_del_{member_id}", type="secondary"):
                                    conn = sqlite3.connect('somiti.db')
                                    c = conn.cursor()
                                    c.execute("DELETE FROM transactions WHERE member_id=?", (member_id,))
                                    c.execute("DELETE FROM members WHERE id=?", (member_id,))
                                    conn.commit()
                                    conn.close()
                                    st.success("✅ ডিলিট হয়েছে!")
                                    del st.session_state[f"show_del_{member_id}"]
                                    st.rerun()
                            with c2:
                                if st.button("❌ বাতিল", key=f"no_del_{member_id}"):
                                    del st.session_state[f"show_del_{member_id}"]
                                    st.rerun()
            else:
                st.info("কোনো সদস্য পাওয়া যায়নি")
                
        except Exception as e:
            st.error(f"এরর: {e}")
    
    elif menu == "💵 টাকা জমা":
        st.markdown("### 💵 সদস্যের টাকা জমা")
        
        search_term = st.text_input("🔍 নাম বা আইডি দিয়ে সদস্য খুঁজুন", key="dep_search")
        
        if search_term:
            search_results = search_members(search_term)
            if search_results:
                options = {f"{m[1]} ({m[2]}) [{m[0]}]": m for m in search_results}
                selected = st.selectbox("সদস্য নির্বাচন করুন", list(options.keys()), key="dep_select")
                
                if selected:
                    m = options[selected]
                    member_id, name, phone = m
                    
                    conn = sqlite3.connect('somiti.db')
                    c = conn.cursor()
                    c.execute("SELECT monthly_savings, telegram_id, total_savings FROM members WHERE id=?", (member_id,))
                    result = c.fetchone()
                    conn.close()
                    
                    monthly = result[0] if result else 500
                    telegram_id = result[1] if result else None
                    current_savings = result[2] if result else 0
                    
                    st.info(f"👤 {name} | 💰 মাসিক কিস্তি: {monthly:,.0f} টাকা | মোট জমা: {current_savings:,.0f} টাকা")
                    
                    with st.form("deposit_form"):
                        col1, col2 = st.columns(2)
                        with col1:
                            months = st.number_input("কত মাসের কিস্তি", value=1, min_value=1, max_value=12)
                        with col2:
                            late_fee = st.number_input("লেট ফি (ঐচ্ছিক)", value=0.0, step=10.0)
                        
                        total = monthly * months + late_fee
                        st.write(f"**মোট জমা: {total:,.0f} টাকা**")
                        
                        month = st.selectbox("কিস্তির মাস", 
                                            [datetime.now().strftime("%Y-%m")] + 
                                            [(datetime.now() - timedelta(days=30*i)).strftime("%Y-%m") for i in range(1,6)])
                        
                        if st.form_submit_button("✅ জমা করুন", type="primary"):
                            if total > 0:
                                today = datetime.now().strftime("%Y-%m-%d")
                                
                                conn = sqlite3.connect('somiti.db')
                                c = conn.cursor()
                                
                                for i in range(months):
                                    m_date = (datetime.strptime(month, "%Y-%m") + timedelta(days=30*i)).strftime("%Y-%m")
                                    c.execute("""
                                        INSERT INTO transactions (member_id, amount, transaction_type, month, date, late_fee)
                                        VALUES (?, ?, ?, ?, ?, ?)
                                    """, (member_id, monthly, 'deposit', m_date, today, late_fee if i == 0 else 0))
                                
                                c.execute("UPDATE members SET total_savings = total_savings + ? WHERE id = ?", (total, member_id))
                                c.execute("SELECT total_savings FROM members WHERE id = ?", (member_id,))
                                new_total = c.fetchone()[0]
                                conn.commit()
                                conn.close()
                                
                                if telegram_id:
                                    msg = f"""✅ পেমেন্ট সফল - {SOMITI_NAME}

প্রিয় {name},
জমা: {total:,.0f} টাকা
মোট জমা: {new_total:,.0f} টাকা
ধন্যবাদ! 🙏"""
                                    send_telegram_message(telegram_id, msg)
                                
                                send_telegram_channel_message(f"📢 {name} [{member_id}] জমা দিয়েছেন {total:,.0f} টাকা")
                                
                                st.success(f"✅ {total:,.0f} টাকা জমা হয়েছে!")
                                st.balloons()
            else:
                st.warning("কোনো সদস্য পাওয়া যায়নি")
        else:
            st.info("নাম বা আইডি দিয়ে সদস্য খুঁজুন")
    
    elif menu == "💸 খরচ ব্যবস্থাপনা":
        st.markdown("### 💸 খরচ ব্যবস্থাপনা")
        
        tab1, tab2 = st.tabs(["➕ নতুন খরচ", "📋 তালিকা"])
        
        with tab1:
            with st.form("expense_form"):
                desc = st.text_input("বিবরণ")
                amt = st.number_input("টাকা", value=0.0, step=10.0)
                cat = st.selectbox("ক্যাটাগরি", ["অফিস ভাড়া", "চা-নাস্তা", "স্টেশনারি", "পরিবহন", "অন্যান্য"])
                
                if st.form_submit_button("💾 সংরক্ষণ", type="primary"):
                    if desc and amt > 0:
                        conn = sqlite3.connect('somiti.db')
                        c = conn.cursor()
                        c.execute("INSERT INTO expenses (description, amount, date, category) VALUES (?, ?, ?, ?)",
                                 (desc, amt, datetime.now().strftime("%Y-%m-%d"), cat))
                        conn.commit()
                        conn.close()
                        st.success(f"✅ {amt:,.0f} টাকা যোগ হয়েছে!")
                        st.rerun()
                    else:
                        st.error("❌ বিবরণ ও টাকা দিন")
        
        with tab2:
            try:
                conn = sqlite3.connect('somiti.db')
                c = conn.cursor()
                c.execute("SELECT id, date, description, amount, category FROM expenses ORDER BY id DESC LIMIT 50")
                expenses = c.fetchall()
                conn.close()
                
                if expenses:
                    for e in expenses:
                        eid, date, desc, amt, cat = e
                        c1, c2, c3, c4, c5 = st.columns([2, 2, 3, 2, 1])
                        c1.write(date)
                        c2.write(cat)
                        c3.write(desc)
                        c4.write(f"{amt:,.0f} টাকা")
                        if c5.button("🗑️", key=f"del_{eid}"):
                            conn = sqlite3.connect('somiti.db')
                            c = conn.cursor()
                            c.execute("DELETE FROM expenses WHERE id=?", (eid,))
                            conn.commit()
                            conn.close()
                            st.rerun()
                    
                    total = sum(e[3] for e in expenses)
                    st.metric("📊 মোট খরচ", f"{total:,.0f} টাকা")
                else:
                    st.info("কোনো খরচ নেই")
            except Exception as e:
                st.error(f"এরর: {e}")
        
        st.markdown("---")
        c1, c2, c3 = st.columns(3)
        c1.metric("💰 জমা", f"{get_total_savings():,.0f} টাকা")
        c2.metric("💸 খরচ", f"{get_total_expenses():,.0f} টাকা")
        c3.metric("💵 ব্যালেন্স", f"{get_cash_balance():,.0f} টাকা")
    
    elif menu == "📊 রিপোর্ট":
        st.markdown("### 📊 রিপোর্ট")
        
        tab1, tab2, tab3 = st.tabs(["📈 মাসিক", "⚠️ বকেয়া", "📥 স্টেটমেন্ট"])
        
        with tab1:
            try:
                conn = sqlite3.connect('somiti.db')
                c = conn.cursor()
                c.execute("SELECT month, SUM(amount) FROM transactions GROUP BY month ORDER BY month DESC LIMIT 12")
                data = c.fetchall()
                conn.close()
                
                if data:
                    df = pd.DataFrame(data, columns=["মাস", "জমা"])
                    st.bar_chart(df.set_index("মাস"))
                    st.dataframe(df, use_container_width=True, hide_index=True)
                else:
                    st.info("কোনো লেনদেন নেই")
            except:
                pass
        
        with tab2:
            try:
                current = datetime.now().strftime("%Y-%m")
                conn = sqlite3.connect('somiti.db')
                c = conn.cursor()
                c.execute("SELECT DISTINCT member_id FROM transactions WHERE month=?", (current,))
                paid = [r[0] for r in c.fetchall()]
                
                if paid:
                    ph = ','.join(['?' for _ in paid])
                    c.execute(f"SELECT name, phone, monthly_savings, telegram_id FROM members WHERE status='active' AND id NOT IN ({ph})", paid)
                else:
                    c.execute("SELECT name, phone, monthly_savings, telegram_id FROM members WHERE status='active'")
                
                defaulters = c.fetchall()
                conn.close()
                
                if defaulters:
                    df = pd.DataFrame(defaulters, columns=["নাম", "মোবাইল", "কিস্তি", "টেলিগ্রাম"])
                    st.dataframe(df, use_container_width=True, hide_index=True)
                    st.warning(f"⚠️ {len(defaulters)} জন বকেয়াদার")
                    
                    if st.button("📢 রিমাইন্ডার পাঠান", type="primary"):
                        sent = 0
                        for n, p, m, t in defaulters:
                            if t:
                                if send_telegram_message(t, f"⚠️ {n}, আপনার {m:,.0f} টাকা বকেয়া। জমা দিন।"):
                                    sent += 1
                        st.success(f"✅ {sent} জনকে পাঠানো হয়েছে!")
                else:
                    st.success("🎉 সবাই কিস্তি দিয়েছেন!")
            except:
                pass
        
        with tab3:
            search = st.text_input("আইডি বা নাম", key="stmt")
            if search:
                m = get_member_by_id_or_name(search)
                if m:
                    mid, name, phone, total, monthly, status, tel = m
                    st.info(f"👤 {name} [{mid}]")
                    
                    conn = sqlite3.connect('somiti.db')
                    c = conn.cursor()
                    c.execute("SELECT date, amount, month, late_fee FROM transactions WHERE member_id=? ORDER BY date DESC", (mid,))
                    trans = c.fetchall()
                    conn.close()
                    
                    if trans:
                        df = pd.DataFrame(trans, columns=["তারিখ", "টাকা", "মাস", "লেট ফি"])
                        st.dataframe(df, use_container_width=True, hide_index=True)
                        
                        out = BytesIO()
                        df.to_excel(out, index=False)
                        st.download_button("📥 ডাউনলোড", out.getvalue(), f"{mid}_statement.xlsx", type="primary")
                    else:
                        st.info("কোনো লেনদেন নেই")
                else:
                    st.warning("পাওয়া যায়নি")
    
    elif menu == "🎲 লটারি":
        st.markdown("### 🎲 লটারি ড্র")
        
        st.markdown("""
        <div class="lottery-box">
            <h3>🎰 লাকি ড্র</h3>
            <p>সক্রিয় সদস্যদের মধ্য থেকে বিজয়ী নির্বাচন</p>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("🎲 বিজয়ী নির্বাচন", type="primary", use_container_width=True):
            w = pick_lottery_winner()
            if w:
                mid, name, phone, sav, tel = w
                st.balloons()
                st.success(f"🎉 {name} [{mid}] বিজয়ী!")
                st.info(f"📱 {phone} | 💰 {sav:,.0f} টাকা")
                
                send_telegram_channel_message(f"🎉 লটারি বিজয়ী: {name} [{mid}]")
                if tel:
                    send_telegram_message(tel, f"🎉 অভিনন্দন {name}! আপনি লটারিতে বিজয়ী!")
            else:
                st.error("❌ কোনো সক্রিয় সদস্য নেই")

# ============================================
# মেম্বার প্যানেল
# ============================================
def member_panel():
    apply_dark_theme()
    show_header()
    
    try:
        conn = sqlite3.connect('somiti.db')
        c = conn.cursor()
        c.execute("SELECT name, phone, total_savings, monthly_savings, id FROM members WHERE id=?", 
                 (st.session_state.member_id,))
        m = c.fetchone()
        
        if not m:
            st.error("সদস্য পাওয়া যায়নি")
            st.session_state.logged_in = False
            st.rerun()
            return
        
        name, phone, savings, monthly, mid = m
        monthly = monthly or 500
        
        with st.sidebar:
            st.markdown(f"### 👤 {name}")
            st.caption(f"🆔 {mid}")
            st.caption(f"📱 {phone}")
            st.metric("💰 জমা", f"{savings:,.0f} টাকা")
            st.metric("📅 কিস্তি", f"{monthly:,.0f} টাকা")
            
            menu = st.radio("মেনু", ["📊 ড্যাশবোর্ড", "🔑 পাসওয়ার্ড", "🚪 লগআউট"], label_visibility="collapsed")
        
        if menu == "🚪 লগআউট":
            for k in ['logged_in', 'user_type', 'member_id']:
                if k in st.session_state:
                    del st.session_state[k]
            st.rerun()
        
        elif menu == "📊 ড্যাশবোর্ড":
            st.markdown(f"### স্বাগতম, {name}!")
            
            c1, c2 = st.columns(2)
            c1.metric("💰 জমা", f"{savings:,.0f} টাকা")
            c2.metric("📅 কিস্তি", f"{monthly:,.0f} টাকা")
            
            cur = datetime.now().strftime("%Y-%m")
            c.execute("SELECT SUM(amount) FROM transactions WHERE member_id=? AND month=?", (mid, cur))
            paid = c.fetchone()[0] or 0
            
            if paid >= monthly:
                st.success(f"✅ {cur} মাসের কিস্তি পরিশোধ করেছেন")
            else:
                st.warning(f"⚠️ বকেয়া: {monthly - paid:,.0f} টাকা")
            
            st.markdown("---")
            st.markdown("#### 📋 লেনদেন")
            c.execute("SELECT date, amount, month FROM transactions WHERE member_id=? ORDER BY id DESC LIMIT 20", (mid,))
            trans = c.fetchall()
            
            if trans:
                df = pd.DataFrame(trans, columns=["তারিখ", "টাকা", "মাস"])
                st.dataframe(df, use_container_width=True, hide_index=True)
                
                out = BytesIO()
                df.to_excel(out, index=False)
                st.download_button("📥 ডাউনলোড", out.getvalue(), f"{mid}_statement.xlsx", type="primary")
            else:
                st.info("কোনো লেনদেন নেই")
        
        elif menu == "🔑 পাসওয়ার্ড":
            st.markdown("### 🔑 পাসওয়ার্ড পরিবর্তন")
            
            with st.form("pass_form"):
                cur_p = st.text_input("বর্তমান", type="password")
                new_p = st.text_input("নতুন", type="password")
                con_p = st.text_input("নিশ্চিত", type="password")
                
                if st.form_submit_button("🔄 পরিবর্তন", type="primary"):
                    c.execute("SELECT password FROM members WHERE id=?", (mid,))
                    stored = c.fetchone()[0]
                    
                    if cur_p != stored:
                        st.error("❌ বর্তমান পাসওয়ার্ড ভুল")
                    elif new_p != con_p:
                        st.error("❌ মিলছে না")
                    elif len(new_p) < 4:
                        st.error("❌ ৪+ অক্ষর")
                    else:
                        c.execute("UPDATE members SET password=? WHERE id=?", (new_p, mid))
                        conn.commit()
                        st.success("✅ পরিবর্তন হয়েছে!")
        
        conn.close()
    except Exception as e:
        st.error(f"এরর: {e}")

# ============================================
# মেইন
# ============================================
def main():
    init_database()
    init_session()
    
    if not st.session_state.logged_in:
        login_page()
    else:
        if st.session_state.user_type == 'admin':
            admin_panel()
        elif st.session_state.user_type == 'member':
            member_panel()
        else:
            login_page()

if __name__ == "__main__":
    main()
