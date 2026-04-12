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
CHANNEL_CHAT_ID = "-1002392909031"  # getUpdates থেকে সঠিক আইডি বসান
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
# পাবলিক ভিউ চেক (লগইন ছাড়া)
# ============================================
query_params = st.query_params
public_view = query_params.get("view") == "public"
member_view_id = query_params.get("member")

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
# টেলিগ্রাম মেসেজ - ফিক্সড
# ============================================
def send_channel_message(message):
    """টেলিগ্রাম চ্যানেলে মেসেজ পাঠায়"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": CHANNEL_CHAT_ID, "text": message}
        response = requests.post(url, json=payload, timeout=10)
        
        if response.status_code == 200:
            return True
        else:
            st.error(f"টেলিগ্রাম এরর: {response.json().get('description', 'Unknown error')}")
            return False
    except Exception as e:
        st.error(f"টেলিগ্রাম কানেকশন এরর: {e}")
        return False

def send_personal_message(chat_id, message):
    """ব্যক্তিগত টেলিগ্রামে মেসেজ পাঠায়"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": chat_id, "text": message}
        response = requests.post(url, json=payload, timeout=10)
        return response.status_code == 200
    except:
        return False

def get_bot_info():
    """বট তথ্য আনে"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getMe"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('ok'):
                return data['result']
    except:
        pass
    return None

def get_chat_info():
    """চ্যাট তথ্য আনে"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getChat"
        payload = {"chat_id": CHANNEL_CHAT_ID}
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('ok'):
                return data['result']
    except:
        pass
    return None

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

def get_member_transactions(member_id):
    """সদস্যের লেনদেন ইতিহাস - ফিক্সড"""
    try:
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
    except Exception as e:
        st.error(f"লেনদেন লোড এরর: {e}")
        return []

def get_all_members():
    conn = sqlite3.connect('somiti.db')
    c = conn.cursor()
    c.execute("""
        SELECT id, name, phone, password, telegram_id, status, monthly_savings, total_savings
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
    return "https://oiorganization2024.streamlit.app"

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

# ============================================
# UI স্টাইল
# ============================================
def apply_dark_theme():
    st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(135deg, #0d1117 0%, #161b22 100%);
    }
    
    .somiti-header {
        background: linear-gradient(135deg, #1a5276 0%, #2980b9 100%);
        padding: 20px;
        border-radius: 15px;
        margin-bottom: 20px;
        text-align: center;
    }
    .somiti-header h1 {
        color: white;
        font-size: 32px;
        font-weight: 800;
        margin: 0;
    }
    
    .total-box {
        background: linear-gradient(135deg, #1e8449 0%, #27ae60 100%);
        padding: 15px;
        border-radius: 15px;
        text-align: center;
        margin-bottom: 20px;
    }
    .total-box h2 {
        color: white;
        font-size: 28px;
        font-weight: 800;
        margin: 0;
    }
    
    .cash-box {
        background: linear-gradient(135deg, #d35400 0%, #e67e22 100%);
        padding: 15px;
        border-radius: 15px;
        text-align: center;
        margin-bottom: 20px;
    }
    
    .member-card {
        background: #21262d;
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 10px;
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
    }
    
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0d1117 0%, #161b22 100%);
        border-right: 1px solid #30363d;
    }
    section[data-testid="stSidebar"] * {
        color: #c9d1d9 !important;
    }
    
    p, h1, h2, h3, h4, h5, h6, .stMarkdown {
        color: #c9d1d9 !important;
    }
    
    .stDataFrame {
        border-radius: 10px;
        overflow: hidden;
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

# ============================================
# পাবলিক ভিউ (লগইন ছাড়া)
# ============================================
def public_member_view(member_id):
    """লগইন ছাড়া সদস্যের তথ্য দেখা"""
    apply_dark_theme()
    
    member = get_member_by_id(member_id)
    
    if not member:
        st.error("❌ সদস্য পাওয়া যায়নি")
        return
    
    member_id, name, phone, password, telegram_id, total_savings, monthly_savings, join_date, status = member
    
    st.markdown(f"""
    <div class="somiti-header">
        <h1>🌾 {SOMITI_NAME} 🌾</h1>
        <p>সদস্য তথ্য</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("👤 নাম", name)
    with col2:
        st.metric("🆔 আইডি", member_id)
    with col3:
        st.metric("📱 মোবাইল", phone)
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("💰 মোট জমা", f"{total_savings:,.0f} টাকা")
    with col2:
        st.metric("📅 মাসিক কিস্তি", f"{monthly_savings:,.0f} টাকা")
    
    st.markdown("---")
    st.markdown("### 📋 লেনদেন ইতিহাস")
    
    transactions = get_member_transactions(member_id)
    
    if transactions:
        data = []
        for t in transactions:
            data.append({
                "তারিখ": t[1],
                "টাকা": f"{t[2]:,.0f}",
                "মাস": t[3],
                "লেট ফি": f"{t[4]:,.0f}" if t[4] else "0"
            })
        df = pd.DataFrame(data)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("কোনো লেনদেন নেই")

# ============================================
# লগইন পেজ
# ============================================
def login_page():
    apply_dark_theme()
    show_header()
    
    with st.container():
        st.markdown("### 🔐 লগইন")
        
        phone = st.text_input("📱 মোবাইল নম্বর", placeholder="017XXXXXXXX")
        password = st.text_input("🔑 পাসওয়ার্ড", type="password")
        
        if st.button("প্রবেশ করুন", use_container_width=True):
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
                    st.error(f"❌ এরর: {e}")
        
        st.markdown("---")
        st.caption(f"সাহায্য: {ADMIN_MOBILE}")

# ============================================
# এডমিন প্যানেল
# ============================================
def admin_panel():
    apply_dark_theme()
    show_admin_header()
    
    with st.sidebar:
        st.markdown("### 📋 এডমিন মেনু")
        st.caption(f"👑 {ADMIN_MOBILE}")
        
        # টেলিগ্রাম স্ট্যাটাস
        bot = get_bot_info()
        chat = get_chat_info()
        
        if bot:
            st.success(f"✅ বট: @{bot.get('username', 'N/A')}")
        else:
            st.error("❌ বট কানেক্টেড নয়")
        
        if chat:
            st.success(f"✅ চ্যাট: {chat.get('title', 'N/A')}")
        else:
            st.error("❌ চ্যাট পাওয়া যায়নি")
        
        menu = st.radio(
            "নির্বাচন করুন",
            ["🏠 ড্যাশবোর্ড", "➕ নতুন সদস্য", "✏️ সদস্য ব্যবস্থাপনা", "💵 টাকা জমা", 
             "💰 লেনদেন", "🔗 লিংক", "💸 খরচ", "📊 রিপোর্ট", 
             "📱 SMS টেস্ট", "🎲 লটারি", "🚪 লগআউট"],
            label_visibility="collapsed"
        )
    
    if menu == "🚪 লগআউត":
        for key in ['logged_in', 'user_type', 'member_id']:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()
    
    elif menu == "🏠 ড্যাশবোর্ড":
        st.markdown("### 🏠 ড্যাশবোর্ড")
        
        col1, col2, col3, col4 = st.columns(4)
        
        try:
            conn = sqlite3.connect('somiti.db')
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM members WHERE status = 'active'")
            total_members = c.fetchone()[0]
            conn.close()
            
            col1.metric("👥 সদস্য", f"{total_members} জন")
            col2.metric("💰 জমা", f"{get_total_savings():,.0f} টাকা")
            col3.metric("📅 এই মাস", f"{get_current_month_collection():,.0f} টাকা")
            col4.metric("⚠️ বকেয়া", f"{len(get_unpaid_members())} জন")
        except:
            pass
        
        st.markdown("---")
        st.subheader("📢 SMS কন্ট্রোল")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📢 ১ তারিখ রিমাইন্ডার", use_container_width=True, type="primary"):
                month_name = get_bangla_month()
                year = datetime.now().year
                msg = f"""📢 {SOMITI_NAME} - মাসিক কিস্তি রিমাইন্ডার

১ {month_name} {year}

সকল সদস্যদের অনুরোধ:
১০ {month_name} এর মধ্যে কিস্তি পরিশোধ করুন। 🙏"""
                if send_channel_message(msg):
                    st.success("✅ পাঠানো হয়েছে!")
                else:
                    st.error("❌ চ্যাট আইডি চেক করুন")
        
        with col2:
            if st.button("⚠️ ১০ তারিখ রিমাইন্ডার", use_container_width=True, type="primary"):
                unpaid = get_unpaid_members()
                if unpaid:
                    month_name = get_bangla_month()
                    msg = f"""⚠️ {SOMITI_NAME} - বকেয়া রিমাইন্ডার

{month_name} মাসের বকেয়াদার:"""
                    for m in unpaid[:10]:
                        msg += f"\n• {m[1]} ({m[0]}) - {m[3]:,.0f} টাকা"
                    if len(unpaid) > 10:
                        msg += f"\n... আরও {len(unpaid) - 10} জন"
                    msg += "\n\n🙏 আজই পরিশোধ করুন!"
                    
                    if send_channel_message(msg):
                        st.success("✅ পাঠানো হয়েছে!")
                    else:
                        st.error("❌ পাঠানো যায়নি")
                else:
                    st.success("🎉 সবাই পরিশোধ করেছেন!")
    
    elif menu == "➕ নতুন সদস্য":
        st.markdown("### ➕ নতুন সদস্য")
        
        name = st.text_input("নাম *")
        phone = st.text_input("মোবাইল *", placeholder="017XXXXXXXX")
        telegram_id = st.text_input("টেলিগ্রাম আইডি (ঐচ্ছিক)")
        monthly = st.number_input("মাসিক কিস্তি", value=500, step=50)
        
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
                    c.execute("""
                        INSERT INTO members (id, name, phone, password, telegram_id, monthly_savings, join_date)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (member_id, name, phone, password, telegram_id, monthly, join_date))
                    conn.commit()
                    conn.close()
                    
                    welcome = f"""🎉 {SOMITI_NAME} - নতুন সদস্য

{name} ({member_id}) যোগদান করেছেন!
মাসিক কিস্তি: {monthly} টাকা"""
                    send_channel_message(welcome)
                    
                    st.success(f"✅ সদস্য তৈরি!")
                    st.info(f"আইডি: {member_id} | পাস: {password}")
                    st.balloons()
                    
                except sqlite3.IntegrityError:
                    st.error("❌ এই মোবাইল ইতিমধ্যে নিবন্ধিত")
    
    elif menu == "💵 টাকা জমা":
        st.markdown("### 💵 টাকা জমা")
        
        paid = get_paid_members()
        unpaid = get_unpaid_members()
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### ✅ জমা দিয়েছে")
            if paid:
                for m in paid:
                    st.markdown(f"""
                    <div class="member-card">
                        <strong>{m[1]}</strong> ({m[0]})<br>
                        <small>💰 {m[4]:,.0f} টাকা</small>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("কেউ জমা দেয়নি")
        
        with col2:
            st.markdown("#### ❌ জমা দেয়নি")
            if unpaid:
                for m in unpaid:
                    with st.expander(f"❌ {m[1]} ({m[0]})"):
                        st.write(f"📱 {m[2]}")
                        st.write(f"💰 জমা: {m[4]:,.0f} টাকা")
                        st.write(f"📅 কিস্তি: {m[3]:,.0f} টাকা")
                        
                        deposit_date = st.date_input("তারিখ", value=datetime.now(), key=f"date_{m[0]}")
                        months_list = [(datetime.now() - timedelta(days=30*i)).strftime("%Y-%m") for i in range(12)]
                        selected_month = st.selectbox("মাস", months_list, key=f"month_{m[0]}")
                        
                        col_a, col_b = st.columns(2)
                        with col_a:
                            months_count = st.number_input("কত মাস", value=1, min_value=1, max_value=12, key=f"count_{m[0]}")
                        with col_b:
                            late_fee = st.number_input("লেট ফি", value=0.0, step=10.0, key=f"fee_{m[0]}")
                        
                        total = m[3] * months_count + late_fee
                        st.write(f"**মোট: {total:,.0f} টাকা**")
                        
                        if st.button("✅ জমা নিন", key=f"dep_{m[0]}", type="primary"):
                            today = deposit_date.strftime("%Y-%m-%d")
                            
                            conn = sqlite3.connect('somiti.db')
                            c = conn.cursor()
                            
                            for i in range(months_count):
                                m_date = (datetime.strptime(selected_month, "%Y-%m") + timedelta(days=30*i)).strftime("%Y-%m")
                                c.execute("""
                                    INSERT INTO transactions (member_id, amount, transaction_type, month, date, late_fee)
                                    VALUES (?, ?, ?, ?, ?, ?)
                                """, (m[0], m[3], 'deposit', m_date, today, late_fee if i == 0 else 0))
                            
                            c.execute("UPDATE members SET total_savings = total_savings + ? WHERE id = ?", (total, m[0]))
                            conn.commit()
                            conn.close()
                            
                            msg = f"""✅ পেমেন্ট সফল - {SOMITI_NAME}

{m[1]} ({m[0]})
জমা: {total:,.0f} টাকা"""
                            send_channel_message(msg)
                            
                            st.success(f"✅ {total:,.0f} টাকা জমা হয়েছে!")
                            st.rerun()
            else:
                st.success("🎉 সবাই জমা দিয়েছেন!")
    
    elif menu == "💰 লেনদেন":
        st.markdown("### 💰 লেনদেন ব্যবস্থাপনা")
        
        members = get_all_members()
        
        if members:
            options = {f"{m[1]} ({m[0]})": m[0] for m in members}
            selected = st.selectbox("সদস্য নির্বাচন", list(options.keys()))
            
            if selected:
                member_id = options[selected]
                member = get_member_by_id(member_id)
                
                if member:
                    st.success(f"👤 {member[1]} | 💰 {member[6]:,.0f} টাকা")
                    
                    transactions = get_member_transactions(member_id)
                    
                    if transactions:
                        st.markdown("#### লেনদেন ইতিহাস")
                        
                        for t in transactions:
                            c1, c2, c3, c4, c5 = st.columns([2, 1.5, 1.5, 1, 1])
                            c1.write(t[1])
                            c2.write(f"{t[2]:,.0f} টাকা")
                            c3.write(t[3])
                            
                            if c4.button("✏️", key=f"e_{t[0]}"):
                                st.session_state[f"edit_{t[0]}"] = True
                            
                            if c5.button("🗑️", key=f"d_{t[0]}"):
                                conn = sqlite3.connect('somiti.db')
                                c = conn.cursor()
                                c.execute("UPDATE members SET total_savings = total_savings - ? WHERE id = ?", (t[2], member_id))
                                c.execute("DELETE FROM transactions WHERE id = ?", (t[0],))
                                conn.commit()
                                conn.close()
                                st.success("✅ রিমুভ হয়েছে!")
                                st.rerun()
                            
                            if st.session_state.get(f"edit_{t[0]}"):
                                new_amt = st.number_input("টাকা", value=float(t[2]), step=50.0, key=f"amt_{t[0]}")
                                if st.button("💾 সেভ", key=f"save_{t[0]}"):
                                    conn = sqlite3.connect('somiti.db')
                                    c = conn.cursor()
                                    diff = new_amt - t[2]
                                    c.execute("UPDATE transactions SET amount = ? WHERE id = ?", (new_amt, t[0]))
                                    c.execute("UPDATE members SET total_savings = total_savings + ? WHERE id = ?", (diff, member_id))
                                    conn.commit()
                                    conn.close()
                                    st.success("✅ আপডেট হয়েছে!")
                                    del st.session_state[f"edit_{t[0]}"]
                                    st.rerun()
                    else:
                        st.info("কোনো লেনদেন নেই")
        else:
            st.info("কোনো সদস্য নেই")
    
    elif menu == "🔗 লিংক":
        st.markdown("### 🔗 সদস্য লিংক")
        
        members = get_all_members()
        app_url = get_app_url()
        
        if members:
            for m in members:
                member_id, name, phone, password, telegram_id, status, monthly, savings = m
                
                public_link = f"{app_url}/?member={member_id}"
                
                st.markdown(f"""
                <div class="member-card">
                    <h4>👤 {name} ({member_id})</h4>
                    <p><strong>📱 মোবাইল:</strong> {phone}</p>
                    <p><strong>🔗 পাবলিক লিংক:</strong><br>
                    <code style="background:#0d1117; padding:5px; border-radius:5px;">{public_link}</code>
                    </p>
                    <p><strong>🔑 পাসওয়ার্ড:</strong> <code>{password}</code></p>
                </div>
                """, unsafe_allow_html=True)
                
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"""
                    <button onclick="navigator.clipboard.writeText('{public_link}')" 
                            style="background:#238636; color:white; border:none; padding:8px 16px; border-radius:5px; cursor:pointer; width:100%;">
                        📋 লিংক কপি
                    </button>
                    """, unsafe_allow_html=True)
                with col2:
                    st.markdown(f"""
                    <button onclick="navigator.clipboard.writeText('{password}')" 
                            style="background:#238636; color:white; border:none; padding:8px 16px; border-radius:5px; cursor:pointer; width:100%;">
                        📋 পাসওয়ার্ড কপি
                    </button>
                    """, unsafe_allow_html=True)
                
                if telegram_id:
                    if st.button("📱 টেলিগ্রামে পাঠান", key=f"send_{member_id}"):
                        msg = f"""🔐 {SOMITI_NAME} - লগইন তথ্য

প্রিয় {name},
লিংক: {public_link}
মোবাইল: {phone}
পাসওয়ার্ড: {password}"""
                        if send_personal_message(telegram_id, msg):
                            st.success("✅ পাঠানো হয়েছে!")
                
                st.markdown("---")
        else:
            st.info("কোনো সদস্য নেই")
    
    elif menu == "📱 SMS টেস্ট":
        st.markdown("### 📱 SMS টেস্ট")
        
        bot = get_bot_info()
        chat = get_chat_info()
        
        if bot:
            st.success(f"✅ বট: @{bot.get('username')}")
        else:
            st.error("❌ বট কানেক্টেড নয়")
        
        if chat:
            st.success(f"✅ চ্যাট: {chat.get('title')} ({chat.get('id')})")
        else:
            st.error("❌ চ্যাট পাওয়া যায়নি - বটকে গ্রুপে এড করুন")
        
        st.info(f"চ্যানেল আইডি: {CHANNEL_CHAT_ID}")
        
        test_msg = st.text_area("টেস্ট মেসেজ", value=f"🧪 টেস্ট - {SOMITI_NAME}")
        
        if st.button("📨 টেস্ট পাঠান", type="primary"):
            if send_channel_message(test_msg):
                st.success("✅ পাঠানো হয়েছে!")
                st.balloons()
            else:
                st.error("❌ চ্যাট আইডি সঠিক নয়")

# ============================================
# সদস্য প্যানেল
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
            
            menu = st.radio("মেনু", ["📊 ড্যাশবোর্ড", "🔑 পাসওয়ার্ড", "🚪 লগআউট"], label_visibility="collapsed")
        
        if menu == "🚪 লগআউត":
            for k in ['logged_in', 'user_type', 'member_id']:
                if k in st.session_state:
                    del st.session_state[k]
            st.rerun()
        
        elif menu == "📊 ড্যাশবোর্ড":
            st.markdown(f"### স্বাগতম, {name}!")
            
            c1, c2 = st.columns(2)
            c1.metric("💰 জমা", f"{savings:,.0f} টাকা")
            c2.metric("📅 কিস্তি", f"{monthly:,.0f} টাকা")
            
            st.markdown("---")
            st.markdown("#### 📋 লেনদেন ইতিহাস")
            
            trans = get_member_transactions(mid)
            
            if trans:
                data = []
                for t in trans:
                    data.append({
                        "তারিখ": t[1],
                        "টাকা": f"{t[2]:,.0f}",
                        "মাস": t[3]
                    })
                df = pd.DataFrame(data)
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.info("কোনো লেনদেন নেই")
        
        elif menu == "🔑 পাসওয়ার্ড":
            st.markdown("### 🔑 পাসওয়ার্ড পরিবর্তন")
            
            cur_p = st.text_input("বর্তমান", type="password")
            new_p = st.text_input("নতুন", type="password")
            con_p = st.text_input("নিশ্চিত", type="password")
            
            if st.button("🔄 পরিবর্তন", type="primary"):
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
    
    # পাবলিক ভিউ চেক
    if member_view_id:
        public_member_view(member_view_id)
        return
    
    # সেশন স্টেট
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'user_type' not in st.session_state:
        st.session_state.user_type = None
    if 'member_id' not in st.session_state:
        st.session_state.member_id = None
    
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
