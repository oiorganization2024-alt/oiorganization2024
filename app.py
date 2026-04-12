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
CHANNEL_CHAT_ID = "8548828754"
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
def send_channel_message(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": CHANNEL_CHAT_ID, "text": message}
        response = requests.post(url, json=payload, timeout=10)
        return response.status_code == 200
    except:
        return False

def send_personal_message(chat_id, message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": chat_id, "text": message}
        response = requests.post(url, json=payload, timeout=10)
        return response.status_code == 200
    except:
        return False

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

def get_paid_members():
    current_month = datetime.now().strftime("%Y-%m")
    conn = sqlite3.connect('somiti.db')
    c = conn.cursor()
    c.execute("""
        SELECT DISTINCT m.id, m.name, m.phone, m.monthly_savings, m.total_savings
        FROM members m
        JOIN transactions t ON m.id = t.member_id
        WHERE m.status = 'active' AND t.month = ?
        ORDER BY m.name
    """, (current_month,))
    paid = c.fetchall()
    conn.close()
    return paid

def get_unpaid_members():
    current_month = datetime.now().strftime("%Y-%m")
    conn = sqlite3.connect('somiti.db')
    c = conn.cursor()
    
    c.execute("SELECT DISTINCT member_id FROM transactions WHERE month = ?", (current_month,))
    paid_ids = [row[0] for row in c.fetchall()]
    
    if paid_ids:
        placeholders = ','.join(['?' for _ in paid_ids])
        c.execute(f"""
            SELECT id, name, phone, monthly_savings, total_savings
            FROM members 
            WHERE status = 'active' AND id NOT IN ({placeholders})
            ORDER BY name
        """, paid_ids)
    else:
        c.execute("""
            SELECT id, name, phone, monthly_savings, total_savings
            FROM members 
            WHERE status = 'active'
            ORDER BY name
        """)
    
    unpaid = c.fetchall()
    conn.close()
    return unpaid

def get_current_month_defaulters_count():
    return len(get_unpaid_members())

def get_member_by_id_or_name(search_term):
    conn = sqlite3.connect('somiti.db')
    c = conn.cursor()
    c.execute("""
        SELECT id, name, phone, total_savings, monthly_savings, status, telegram_id, password
        FROM members 
        WHERE id = ? OR name LIKE ?
    """, (search_term, f"%{search_term}%"))
    result = c.fetchone()
    conn.close()
    return result

def get_all_members_with_credentials():
    conn = sqlite3.connect('somiti.db')
    c = conn.cursor()
    c.execute("""
        SELECT id, name, phone, password, telegram_id, status
        FROM members 
        ORDER BY name
    """)
    members = c.fetchall()
    conn.close()
    return members

def get_member_transactions(member_id):
    conn = sqlite3.connect('somiti.db')
    c = conn.cursor()
    c.execute("""
        SELECT id, date, amount, month, late_fee, note
        FROM transactions 
        WHERE member_id = ?
        ORDER BY date DESC
    """, (member_id,))
    trans = c.fetchall()
    conn.close()
    return trans

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

def get_bangla_month():
    months = {
        1: "জানুয়ারি", 2: "ফেব্রুয়ারি", 3: "মার্চ", 4: "এপ্রিল",
        5: "মে", 6: "জুন", 7: "জুলাই", 8: "আগস্ট",
        9: "সেপ্টেম্বর", 10: "অক্টোবর", 11: "নভেম্বর", 12: "ডিসেম্বর"
    }
    return months[datetime.now().month]

def get_app_url():
    try:
        from streamlit.web.server.websocket_headers import _get_websocket_headers
        headers = _get_websocket_headers()
        if headers and "Host" in headers:
            return f"https://{headers['Host']}"
    except:
        pass
    return "https://your-app.streamlit.app"

# ============================================
# UI স্টাইল (ডার্ক থিম)
# ============================================
def apply_dark_theme():
    st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(135deg, #0d1117 0%, #161b22 100%);
    }
    
    .somiti-header {
        background: linear-gradient(135deg, #1a5276 0%, #2980b9 100%);
        padding: 25px;
        border-radius: 15px;
        margin-bottom: 25px;
        text-align: center;
        box-shadow: 0 10px 20px rgba(0,0,0,0.5);
    }
    .somiti-header h1 {
        color: white;
        font-size: 38px;
        font-weight: 800;
        margin: 0;
    }
    .somiti-header p {
        color: #a8d8ea;
        font-size: 16px;
        margin: 8px 0 0 0;
    }
    
    .total-box {
        background: linear-gradient(135deg, #1e8449 0%, #27ae60 100%);
        padding: 20px;
        border-radius: 15px;
        text-align: center;
        margin-bottom: 25px;
        box-shadow: 0 10px 20px rgba(0,0,0,0.5);
    }
    .total-box h2 {
        color: white;
        font-size: 32px;
        font-weight: 800;
        margin: 0;
    }
    
    .cash-box {
        background: linear-gradient(135deg, #d35400 0%, #e67e22 100%);
        padding: 20px;
        border-radius: 15px;
        text-align: center;
        margin-bottom: 25px;
        box-shadow: 0 10px 20px rgba(0,0,0,0.5);
    }
    .cash-box h2 {
        color: white;
        font-size: 32px;
        font-weight: 800;
        margin: 0;
    }
    
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
    }
    
    .member-list-box {
        background: #21262d;
        padding: 20px;
        border-radius: 12px;
        margin-bottom: 15px;
        border: 1px solid #30363d;
        max-height: 500px;
        overflow-y: auto;
    }
    
    .credential-card {
        background: #21262d;
        padding: 20px;
        border-radius: 12px;
        margin-bottom: 15px;
        border: 1px solid #30363d;
    }
    
    .login-card {
        max-width: 420px;
        margin: 50px auto;
        padding: 40px;
        border-radius: 20px;
        box-shadow: 0 20px 40px rgba(0,0,0,0.6);
        background: #21262d;
        border: 1px solid #30363d;
    }
    
    .stButton > button {
        background: linear-gradient(135deg, #238636 0%, #2ea043 100%);
        color: white;
        font-weight: 600;
        border: none;
        border-radius: 8px;
        padding: 8px 16px;
        width: 100%;
        font-size: 14px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        background: linear-gradient(135deg, #2ea043 0%, #3fb950 100%);
        transform: translateY(-2px);
    }
    
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #1a5276 0%, #2980b9 100%);
    }
    
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0d1117 0%, #161b22 100%);
        border-right: 1px solid #30363d;
    }
    section[data-testid="stSidebar"] * {
        color: #c9d1d9 !important;
    }
    
    div[data-testid="metric-container"] {
        background: #21262d;
        border-radius: 12px;
        padding: 15px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.4);
        border: 1px solid #30363d;
    }
    
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
    
    .stTextInput > div > div > input,
    .stSelectbox > div > div,
    .stNumberInput > div > div > input {
        background: #0d1117;
        border: 1px solid #30363d;
        color: #c9d1d9;
        border-radius: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0;
        padding: 12px 24px;
        background: #21262d;
        font-weight: 500;
        color: #8b949e;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #1a5276 0%, #2980b9 100%);
        color: white;
    }
    
    p, h1, h2, h3, h4, h5, h6, li, .stMarkdown, .stCaption {
        color: #c9d1d9 !important;
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
    
    # URL প্যারামিটার থেকে মেম্বার আইডি চেক
    query_params = st.query_params
    member_param = query_params.get("member")
    if member_param:
        st.session_state.auto_member = member_param
    
    with st.container():
        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        st.markdown("### 🔐 লগইন")
        
        # যদি URL থেকে মেম্বার আইডি পাওয়া যায়
        auto_member = st.session_state.get('auto_member', '')
        if auto_member:
            st.info(f"👤 সদস্য আইডি: {auto_member}")
        
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
             "💰 লেনদেন ব্যবস্থাপনা", "🔗 সদস্য লিংক", "💸 খরচ ব্যবস্থাপনা", 
             "📊 রিপোর্ট", "📱 SMS টেস্ট", "🎲 লটারি", "🚪 লগআউট"],
            label_visibility="collapsed"
        )
    
    if menu == "🚪 লগআউট":
        for key in ['logged_in', 'user_type', 'member_id', 'auto_member']:
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
        
        # SMS কন্ট্রোল
        st.subheader("📢 SMS কন্ট্রোল")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📢 ১ তারিখ রিমাইন্ডার", use_container_width=True, type="primary"):
                month_name = get_bangla_month()
                year = datetime.now().year
                msg = f"""📢 *{SOMITI_NAME} - মাসিক কিস্তি রিমাইন্ডার*

তারিখ: ১ {month_name} {year}

সকল সদস্যদের অনুরোধ:
অনুগ্রহ করে আগামী ১০ {month_name} {year} এর মধ্যে আপনার মাসিক কিস্তি পরিশোধ করুন।"""
                if send_channel_message(msg.replace("*", "")):
                    st.success("✅ পাঠানো হয়েছে!")
                else:
                    st.error("❌ ব্যর্থ")
        
        with col2:
            if st.button("⚠️ ১০ তারিখ বকেয়া রিমাইন্ডার", use_container_width=True, type="primary"):
                unpaid = get_unpaid_members()
                if unpaid:
                    month_name = get_bangla_month()
                    msg = f"""⚠️ *{SOMITI_NAME} - বকেয়া রিমাইন্ডার*

বকেয়াদার তালিকা:"""
                    for m in unpaid[:15]:
                        msg += f"\n• {m[1]} ({m[0]}) - {m[3]:,.0f} টাকা"
                    if len(unpaid) > 15:
                        msg += f"\n... এবং আরও {len(unpaid) - 15} জন"
                    msg += "\n\n🙏 দয়া করে আজই পরিশোধ করুন!"
                    
                    if send_channel_message(msg.replace("*", "")):
                        st.success(f"✅ পাঠানো হয়েছে!")
                    else:
                        st.error("❌ ব্যর্থ")
                else:
                    st.success("🎉 সবাই পরিশোধ করেছেন!")
        
        with col3:
            if st.button("📊 ক্যাশ স্ট্যাটাস", use_container_width=True):
                total = get_total_savings()
                expense = get_total_expenses()
                cash = get_cash_balance()
                msg = f"""📊 *{SOMITI_NAME} - ক্যাশ স্ট্যাটাস*

💰 জমা: {total:,.0f} টাকা
💸 খরচ: {expense:,.0f} টাকা
💵 ব্যালেন্স: {cash:,.0f} টাকা"""
                if send_channel_message(msg.replace("*", "")):
                    st.success("✅ পাঠানো হয়েছে!")
                else:
                    st.error("❌ ব্যর্থ")
    
    elif menu == "➕ নতুন সদস্য":
        st.markdown("### ➕ নতুন সদস্য নিবন্ধন")
        
        with st.form("new_member_form"):
            name = st.text_input("নাম *")
            phone = st.text_input("মোবাইল নম্বর *", placeholder="017XXXXXXXX")
            telegram_id = st.text_input("টেলিগ্রাম চ্যাট আইডি (ব্যক্তিগত মেসেজের জন্য)")
            monthly = st.number_input("মাসিক কিস্তি (টাকা)", value=500, step=50)
            
            submitted = st.form_submit_button("✅ সদস্য যোগ করুন", type="primary")
            
            if submitted:
                if not name or not phone:
                    st.error("❌ নাম ও মোবাইল আবশ্যক")
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
                        
                        # চ্যানেলে স্বাগতম মেসেজ
                        welcome_channel = f"""🎉 *{SOMITI_NAME} - নতুন সদস্য*

{name} ({member_id}) সমিতিতে যোগদান করেছেন!
মাসিক কিস্তি: {monthly} টাকা"""
                        send_channel_message(welcome_channel.replace("*", ""))
                        
                        if telegram_id:
                            welcome_personal = f"""🎉 {SOMITI_NAME}-এ স্বাগতম, {name}!

আপনার সদস্যপদ তৈরি হয়েছে।

🆔 আইডি: {member_id}
📱 মোবাইল: {phone}
🔑 পাসওয়ার্ড: {password}
💰 মাসিক কিস্তি: {monthly} টাকা

লগইন লিংক: {get_app_url()}
লগইন করে পাসওয়ার্ড পরিবর্তন করুন।"""
                            send_personal_message(telegram_id, welcome_personal)
                        
                        st.success(f"✅ সদস্য তৈরি হয়েছে!")
                        st.info(f"আইডি: {member_id} | পাসওয়ার্ড: {password}")
                        st.balloons()
                        
                    except sqlite3.IntegrityError:
                        st.error("❌ এই মোবাইল নম্বর ইতিমধ্যে নিবন্ধিত")
    
    elif menu == "✏️ সদস্য ব্যবস্থাপনা":
        st.markdown("### ✏️ সদস্য ব্যবস্থাপনা")
        
        try:
            conn = sqlite3.connect('somiti.db')
            c = conn.cursor()
            c.execute("""
                SELECT id, name, phone, status, monthly_savings, telegram_id, total_savings
                FROM members 
                ORDER BY name
            """)
            members = c.fetchall()
            conn.close()
            
            if members:
                for m in members:
                    member_id, name, phone, status, monthly, telegram, savings = m
                    monthly = float(monthly) if monthly else 500.0
                    savings = float(savings) if savings else 0.0
                    
                    with st.expander(f"👤 {name} - {member_id} | 📱 {phone}"):
                        st.markdown(f"""
                        <div style="background: #21262d; padding: 15px; border-radius: 8px; margin-bottom: 15px;">
                            <p><strong>💰 মোট জমা:</strong> {savings:,.0f} টাকা</p>
                            <p><strong>📅 মাসিক কিস্তি:</strong> {monthly:,.0f} টাকা</p>
                            <p><strong>📬 টেলিগ্রাম:</strong> {telegram or 'N/A'}</p>
                            <p><strong>🔄 স্ট্যাটাস:</strong> {'✅ সক্রিয়' if status == 'active' else '❌ নিষ্ক্রিয়'}</p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        col1, col2, col3, col4 = st.columns(4)
                        
                        with col1:
                            if st.button("📝 এডিট", key=f"edit_{member_id}"):
                                st.session_state[f"show_edit_{member_id}"] = True
                        with col2:
                            if st.button("🔐 পাসওয়ার্ড", key=f"pass_{member_id}"):
                                st.session_state[f"show_pass_{member_id}"] = True
                        with col3:
                            if st.button("🔄 স্ট্যাটাস", key=f"stat_{member_id}"):
                                st.session_state[f"show_stat_{member_id}"] = True
                        with col4:
                            if st.button("🗑️ ডিলিট", key=f"del_{member_id}"):
                                st.session_state[f"show_del_{member_id}"] = True
                        
                        # এডিট ফর্ম
                        if st.session_state.get(f"show_edit_{member_id}"):
                            with st.form(f"edit_form_{member_id}"):
                                new_name = st.text_input("নাম", value=name)
                                new_tel = st.text_input("টেলিগ্রাম আইডি", value=telegram or "")
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
                                        send_personal_message(telegram, f"🔐 আপনার নতুন পাসওয়ার্ড: {new_pass}")
                                    st.success(f"✅ নতুন পাসওয়ার্ড: {new_pass}")
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
                                if st.button("✅ ডিলিট", key=f"yes_del_{member_id}"):
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
        
        paid_members = get_paid_members()
        unpaid_members = get_unpaid_members()
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            <div class="member-list-box">
                <h3>✅ জমা দিয়েছে</h3>
            """, unsafe_allow_html=True)
            
            if paid_members:
                for m in paid_members:
                    member_id, name, phone, monthly, savings = m
                    st.markdown(f"""
                    <div style="padding: 10px; border-bottom: 1px solid #30363d;">
                        <strong>{name}</strong> ({member_id})<br>
                        <small>📱 {phone} | 💰 {savings:,.0f} টাকা</small>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if st.button(f"➕ জমা নিন", key=f"paid_{member_id}"):
                        st.session_state[f"deposit_{member_id}"] = True
                    
                    if st.session_state.get(f"deposit_{member_id}"):
                        with st.form(f"deposit_form_{member_id}"):
                            months = st.number_input("কত মাস", value=1, min_value=1, max_value=12)
                            late_fee = st.number_input("লেট ফি", value=0.0, step=10.0)
                            total = monthly * months + late_fee
                            st.write(f"**মোট: {total:,.0f} টাকা**")
                            
                            if st.form_submit_button("✅ জমা করুন", type="primary"):
                                today = datetime.now().strftime("%Y-%m-%d")
                                current_month = datetime.now().strftime("%Y-%m")
                                
                                conn = sqlite3.connect('somiti.db')
                                c = conn.cursor()
                                
                                for i in range(months):
                                    m_date = (datetime.strptime(current_month, "%Y-%m") + timedelta(days=30*i)).strftime("%Y-%m")
                                    c.execute("""
                                        INSERT INTO transactions (member_id, amount, transaction_type, month, date, late_fee)
                                        VALUES (?, ?, ?, ?, ?, ?)
                                    """, (member_id, monthly, 'deposit', m_date, today, late_fee if i == 0 else 0))
                                
                                c.execute("UPDATE members SET total_savings = total_savings + ? WHERE id = ?", (total, member_id))
                                c.execute("SELECT total_savings FROM members WHERE id = ?", (member_id,))
                                new_total = c.fetchone()[0]
                                conn.commit()
                                conn.close()
                                
                                channel_msg = f"""✅ *পেমেন্ট সফল - {SOMITI_NAME}*

{name} ({member_id})
জমা: {total:,.0f} টাকা
মোট জমা: {new_total:,.0f} টাকা"""
                                send_channel_message(channel_msg.replace("*", ""))
                                
                                st.success(f"✅ {total:,.0f} টাকা জমা হয়েছে!")
                                del st.session_state[f"deposit_{member_id}"]
                                st.rerun()
            else:
                st.info("কেউ এখনো জমা দেয়নি")
            
            st.markdown("</div>", unsafe_allow_html=True)
        
        with col2:
            st.markdown("""
            <div class="member-list-box">
                <h3>❌ জমা দেয়নি</h3>
            """, unsafe_allow_html=True)
            
            if unpaid_members:
                for m in unpaid_members:
                    member_id, name, phone, monthly, savings = m
                    st.markdown(f"""
                    <div style="padding: 10px; border-bottom: 1px solid #30363d;">
                        <strong>{name}</strong> ({member_id})<br>
                        <small>📱 {phone} | 💰 {savings:,.0f} টাকা</small>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if st.button(f"➕ জমা নিন", key=f"unpaid_{member_id}"):
                        st.session_state[f"deposit_{member_id}"] = True
                    
                    if st.session_state.get(f"deposit_{member_id}"):
                        with st.form(f"deposit_form_{member_id}"):
                            months = st.number_input("কত মাস", value=1, min_value=1, max_value=12)
                            late_fee = st.number_input("লেট ফি", value=0.0, step=10.0)
                            total = monthly * months + late_fee
                            st.write(f"**মোট: {total:,.0f} টাকা**")
                            
                            if st.form_submit_button("✅ জমা করুন", type="primary"):
                                today = datetime.now().strftime("%Y-%m-%d")
                                current_month = datetime.now().strftime("%Y-%m")
                                
                                conn = sqlite3.connect('somiti.db')
                                c = conn.cursor()
                                
                                for i in range(months):
                                    m_date = (datetime.strptime(current_month, "%Y-%m") + timedelta(days=30*i)).strftime("%Y-%m")
                                    c.execute("""
                                        INSERT INTO transactions (member_id, amount, transaction_type, month, date, late_fee)
                                        VALUES (?, ?, ?, ?, ?, ?)
                                    """, (member_id, monthly, 'deposit', m_date, today, late_fee if i == 0 else 0))
                                
                                c.execute("UPDATE members SET total_savings = total_savings + ? WHERE id = ?", (total, member_id))
                                c.execute("SELECT total_savings FROM members WHERE id = ?", (member_id,))
                                new_total = c.fetchone()[0]
                                conn.commit()
                                conn.close()
                                
                                channel_msg = f"""✅ *পেমেন্ট সফল - {SOMITI_NAME}*

{name} ({member_id})
জমা: {total:,.0f} টাকা
মোট জমা: {new_total:,.0f} টাকা"""
                                send_channel_message(channel_msg.replace("*", ""))
                                
                                st.success(f"✅ {total:,.0f} টাকা জমা হয়েছে!")
                                del st.session_state[f"deposit_{member_id}"]
                                st.rerun()
            else:
                st.success("🎉 সবাই জমা দিয়েছেন!")
            
            st.markdown("</div>", unsafe_allow_html=True)
    
    elif menu == "💰 লেনদেন ব্যবস্থাপনা":
        st.markdown("### 💰 লেনদেন ব্যবস্থাপনা")
        st.info("এখানে আপনি সদস্যের লেনদেন এডিট বা রিমুভ করতে পারবেন")
        
        # সদস্য সার্চ
        search_term = st.text_input("🔍 সদস্যের নাম বা আইডি লিখুন", key="trans_search")
        
        if search_term:
            member = get_member_by_id_or_name(search_term)
            if member:
                member_id, name, phone, savings, monthly, status, telegram, password = member
                
                st.success(f"👤 {name} ({member_id}) | 📱 {phone} | 💰 মোট জমা: {savings:,.0f} টাকা")
                
                # লেনদেন ইতিহাস
                transactions = get_member_transactions(member_id)
                
                if transactions:
                    st.markdown("#### 📋 লেনদেন ইতিহাস")
                    
                    for trans in transactions:
                        trans_id, date, amount, month, late_fee, note = trans
                        
                        col1, col2, col3, col4, col5, col6 = st.columns([2, 1.5, 1.5, 1, 1, 1])
                        
                        with col1:
                            st.write(date)
                        with col2:
                            st.write(f"{amount:,.0f} টাকা")
                        with col3:
                            st.write(month)
                        with col4:
                            st.write(f"{late_fee:,.0f}" if late_fee else "0")
                        
                        with col5:
                            if st.button("✏️ এডিট", key=f"edit_trans_{trans_id}"):
                                st.session_state[f"edit_trans_{trans_id}"] = True
                        
                        with col6:
                            if st.button("🗑️ রিমুভ", key=f"del_trans_{trans_id}"):
                                st.session_state[f"del_trans_{trans_id}"] = True
                        
                        # এডিট ফর্ম
                        if st.session_state.get(f"edit_trans_{trans_id}"):
                            with st.form(f"edit_trans_form_{trans_id}"):
                                st.markdown(f"**লেনদেন এডিট করুন**")
                                new_amount = st.number_input("নতুন পরিমাণ", value=float(amount), step=50.0)
                                new_month = st.text_input("মাস", value=month)
                                new_late_fee = st.number_input("লেট ফি", value=float(late_fee) if late_fee else 0.0, step=10.0)
                                
                                c1, c2 = st.columns(2)
                                with c1:
                                    if st.form_submit_button("💾 সেভ", type="primary"):
                                        conn = sqlite3.connect('somiti.db')
                                        c = conn.cursor()
                                        
                                        # আগের amount
                                        old_amount = amount
                                        diff = new_amount - old_amount
                                        
                                        c.execute("""
                                            UPDATE transactions 
                                            SET amount=?, month=?, late_fee=?
                                            WHERE id=?
                                        """, (new_amount, new_month, new_late_fee, trans_id))
                                        
                                        # মোট জমা আপডেট
                                        c.execute("UPDATE members SET total_savings = total_savings + ? WHERE id = ?", 
                                                 (diff, member_id))
                                        
                                        conn.commit()
                                        conn.close()
                                        
                                        st.success("✅ লেনদেন আপডেট হয়েছে!")
                                        del st.session_state[f"edit_trans_{trans_id}"]
                                        st.rerun()
                                with c2:
                                    if st.form_submit_button("❌ বাতিল"):
                                        del st.session_state[f"edit_trans_{trans_id}"]
                                        st.rerun()
                        
                        # রিমুভ কনফার্মেশন
                        if st.session_state.get(f"del_trans_{trans_id}"):
                            st.error(f"⚠️ {amount:,.0f} টাকার এই লেনদেনটি রিমুভ করবেন?")
                            
                            c1, c2 = st.columns(2)
                            with c1:
                                if st.button("✅ হ্যাঁ, রিমুভ", key=f"confirm_del_{trans_id}"):
                                    conn = sqlite3.connect('somiti.db')
                                    c = conn.cursor()
                                    
                                    # মোট জমা থেকে বাদ দিন
                                    c.execute("UPDATE members SET total_savings = total_savings - ? WHERE id = ?", 
                                             (amount, member_id))
                                    
                                    # লেনদেন ডিলিট
                                    c.execute("DELETE FROM transactions WHERE id = ?", (trans_id,))
                                    
                                    conn.commit()
                                    conn.close()
                                    
                                    st.success("✅ লেনদেন রিমুভ হয়েছে!")
                                    del st.session_state[f"del_trans_{trans_id}"]
                                    st.rerun()
                            with c2:
                                if st.button("❌ বাতিল", key=f"cancel_del_{trans_id}"):
                                    del st.session_state[f"del_trans_{trans_id}"]
                                    st.rerun()
                        
                        st.markdown("---")
                else:
                    st.info("কোনো লেনদেন নেই")
                
                # নতুন লেনদেন যোগ
                st.markdown("#### ➕ নতুন লেনদেন যোগ")
                with st.form(f"add_trans_{member_id}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        new_amount = st.number_input("টাকার পরিমাণ", value=0.0, step=50.0)
                    with col2:
                        new_month = st.text_input("মাস (YYYY-MM)", value=datetime.now().strftime("%Y-%m"))
                    
                    new_late_fee = st.number_input("লেট ফি", value=0.0, step=10.0)
                    new_note = st.text_input("নোট (ঐচ্ছিক)")
                    
                    if st.form_submit_button("✅ লেনদেন যোগ করুন", type="primary"):
                        if new_amount > 0:
                            today = datetime.now().strftime("%Y-%m-%d")
                            
                            conn = sqlite3.connect('somiti.db')
                            c = conn.cursor()
                            c.execute("""
                                INSERT INTO transactions (member_id, amount, transaction_type, month, date, note, late_fee)
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                            """, (member_id, new_amount, 'deposit', new_month, today, new_note, new_late_fee))
                            
                            c.execute("UPDATE members SET total_savings = total_savings + ? WHERE id = ?", 
                                     (new_amount, member_id))
                            
                            conn.commit()
                            conn.close()
                            
                            st.success(f"✅ {new_amount:,.0f} টাকা যোগ হয়েছে!")
                            st.rerun()
                        else:
                            st.error("❌ টাকার পরিমাণ ০ এর বেশি হতে হবে")
            else:
                st.warning("সদস্য পাওয়া যায়নি")
    
    elif menu == "🔗 সদস্য লিংক":
        st.markdown("### 🔗 সদস্য লিংক ও পাসওয়ার্ড")
        st.info("প্রতিটি সদস্যের লগইন লিংক ও পাসওয়ার্ড")
        
        members = get_all_members_with_credentials()
        app_url = get_app_url()
        
        if members:
            for m in members:
                member_id, name, phone, password, telegram_id, status = m
                
                member_link = f"{app_url}/?member={member_id}"
                
                with st.expander(f"👤 {name} ({member_id}) | {'✅ সক্রিয়' if status == 'active' else '❌ নিষ্ক্রিয়'}"):
                    st.markdown(f"""
                    <div class="credential-card">
                        <p><strong>📱 মোবাইল:</strong> {phone}</p>
                        <p><strong>🔗 লগইন লিংক:</strong><br>
                        <code style="background: #0d1117; padding: 8px; border-radius: 5px; display: block; margin: 10px 0;">{member_link}</code>
                        </p>
                        <p><strong>🔑 পাসওয়ার্ড:</strong> 
                        <code style="background: #0d1117; padding: 5px 10px; border-radius: 5px;">{password}</code>
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        if st.button("📋 লিংক কপি", key=f"copy_link_{member_id}"):
                            st.success("লিংক কপি হয়েছে! (ম্যানুয়ালি কপি করুন)")
                            st.code(member_link, language=None)
                    
                    with col2:
                        if st.button("📋 পাসওয়ার্ড কপি", key=f"copy_pass_{member_id}"):
                            st.success(f"পাসওয়ার্ড: {password}")
                    
                    with col3:
                        if telegram_id:
                            if st.button("📱 টেলিগ্রামে পাঠান", key=f"send_tel_{member_id}"):
                                msg = f"""🔐 *{SOMITI_NAME} - লগইন তথ্য*

প্রিয় {name},
আপনার লগইন তথ্য:

🔗 লিংক: {member_link}
📱 মোবাইল: {phone}
🔑 পাসওয়ার্ড: {password}

লিংকে ক্লিক করে মোবাইল ও পাসওয়ার্ড দিয়ে লগইন করুন।"""
                                
                                if send_personal_message(telegram_id, msg.replace("*", "")):
                                    st.success("✅ টেলিগ্রামে পাঠানো হয়েছে!")
                                else:
                                    st.error("❌ পাঠানো যায়নি")
        else:
            st.info("কোনো সদস্য নেই")
    
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
            except:
                pass
        
        with tab2:
            unpaid = get_unpaid_members()
            if unpaid:
                df = pd.DataFrame(unpaid, columns=["আইডি", "নাম", "মোবাইল", "কিস্তি", "জমা"])
                st.dataframe(df, use_container_width=True, hide_index=True)
                st.warning(f"⚠️ {len(unpaid)} জন বকেয়াদার")
            else:
                st.success("🎉 সবাই কিস্তি দিয়েছেন!")
        
        with tab3:
            search = st.text_input("আইডি বা নাম", key="stmt")
            if search:
                m = get_member_by_id_or_name(search)
                if m:
                    mid, name, phone, total, monthly, status, tel, pwd = m
                    st.info(f"👤 {name} [{mid}]")
                    
                    trans = get_member_transactions(mid)
                    
                    if trans:
                        df = pd.DataFrame(trans, columns=["ID", "তারিখ", "টাকা", "মাস", "লেট ফি", "নোট"])
                        st.dataframe(df, use_container_width=True, hide_index=True)
                        
                        out = BytesIO()
                        df.to_excel(out, index=False)
                        st.download_button("📥 ডাউনলোড", out.getvalue(), f"{mid}_statement.xlsx", type="primary")
                    else:
                        st.info("কোনো লেনদেন নেই")
    
    elif menu == "📱 SMS টেস্ট":
        st.markdown("### 📱 SMS টেস্ট")
        st.info("এই সেকশন থেকে টেস্ট মেসেজ পাঠিয়ে দেখুন চ্যানেলে সঠিকভাবে যাচ্ছে কিনা")
        
        with st.form("test_sms_form"):
            test_message = st.text_area("মেসেজ লিখুন", value=f"🧪 এটি একটি টেস্ট মেসেজ - {SOMITI_NAME}")
            
            if st.form_submit_button("📨 টেস্ট মেসেজ পাঠান", type="primary"):
                if send_channel_message(test_message):
                    st.success("✅ টেস্ট মেসেজ সফলভাবে চ্যানেলে পাঠানো হয়েছে!")
                    st.balloons()
                else:
                    st.error("❌ মেসেজ পাঠানো যায়নি। টেলিগ্রাম বট সেটিংস চেক করুন।")
    
    elif menu == "🎲 লটারি":
        st.markdown("### 🎲 লটারি ড্র")
        
        st.markdown("""
        <div style="background: linear-gradient(135deg, #6c3483 0%, #8e44ad 100%); 
                    padding: 30px; border-radius: 20px; text-align: center; margin: 20px 0;
                    box-shadow: 0 15px 30px rgba(0,0,0,0.6); border: 2px solid gold;">
            <h3 style="color: gold; font-size: 36px; margin: 0;">🎰 লাকি ড্র</h3>
            <p style="color: white; font-size: 18px; margin: 10px 0;">সক্রিয় সদস্যদের মধ্য থেকে বিজয়ী নির্বাচন</p>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("🎲 বিজয়ী নির্বাচন", type="primary", use_container_width=True):
            w = pick_lottery_winner()
            if w:
                mid, name, phone, sav, tel = w
                st.balloons()
                st.success(f"🎉 {name} [{mid}] বিজয়ী!")
                st.info(f"📱 {phone} | 💰 {sav:,.0f} টাকা")
                
                announce = f"""🎉 *লটারি বিজয়ী - {SOMITI_NAME}*

অভিনন্দন! {name} ({mid})
আজকের লাকি ড্র-তে বিজয়ী হয়েছেন!

🏆 শুভেচ্ছা ও অভিনন্দন! 🏆"""
                send_channel_message(announce.replace("*", ""))
                
                if tel:
                    send_personal_message(tel, f"🎉 অভিনন্দন {name}! আপনি লটারিতে বিজয়ী!")
                
                st.success("✅ বিজয়ীর নাম চ্যানেলে ঘোষণা করা হয়েছে!")
            else:
                st.error("❌ কোনো সক্রিয় সদস্য নেই")

# ============================================
# সদস্য প্যানেল (শুধু দেখা)
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
            st.metric("💰 মোট জমা", f"{savings:,.0f} টাকা")
            st.metric("📅 মাসিক কিস্তি", f"{monthly:,.0f} টাকা")
            
            menu = st.radio("মেনু", ["📊 ড্যাশবোর্ড", "🔑 পাসওয়ার্ড", "🚪 লগআউট"], label_visibility="collapsed")
        
        if menu == "🚪 লগআউট":
            for k in ['logged_in', 'user_type', 'member_id', 'auto_member']:
                if k in st.session_state:
                    del st.session_state[k]
            st.rerun()
        
        elif menu == "📊 ড্যাশবোর্ড":
            st.markdown(f"### স্বাগতম, {name}! 👋")
            
            c1, c2 = st.columns(2)
            c1.metric("💰 মোট জমা", f"{savings:,.0f} টাকা")
            c2.metric("📅 মাসিক কিস্তি", f"{monthly:,.0f} টাকা")
            
            cur = datetime.now().strftime("%Y-%m")
            c.execute("SELECT SUM(amount) FROM transactions WHERE member_id=? AND month=?", (mid, cur))
            paid = c.fetchone()[0] or 0
            
            if paid >= monthly:
                st.success(f"✅ {cur} মাসের কিস্তি পরিশোধ করেছেন")
            else:
                st.warning(f"⚠️ বকেয়া: {monthly - paid:,.0f} টাকা")
            
            st.markdown("---")
            st.markdown("#### 📋 লেনদেন ইতিহাস")
            c.execute("SELECT date, amount, month, late_fee FROM transactions WHERE member_id=? ORDER BY id DESC LIMIT 20", (mid,))
            trans = c.fetchall()
            
            if trans:
                df = pd.DataFrame(trans, columns=["তারিখ", "টাকা", "মাস", "লেট ফি"])
                st.dataframe(df, use_container_width=True, hide_index=True)
                
                out = BytesIO()
                df.to_excel(out, index=False)
                st.download_button("📥 এক্সেল ডাউনলোড", out.getvalue(), f"{mid}_statement.xlsx", type="primary")
            else:
                st.info("কোনো লেনদেন নেই")
        
        elif menu == "🔑 পাসওয়ার্ড":
            st.markdown("### 🔑 পাসওয়ার্ড পরিবর্তন")
            
            with st.form("pass_form"):
                cur_p = st.text_input("বর্তমান পাসওয়ার্ড", type="password")
                new_p = st.text_input("নতুন পাসওয়ার্ড", type="password")
                con_p = st.text_input("নিশ্চিত করুন", type="password")
                
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
