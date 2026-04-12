import streamlit as st
import sqlite3
import requests
import random
import string
import pandas as pd
from datetime import datetime, timedelta
from io import BytesIO
import time

# ============================================
# কনফিগারেশন
# ============================================
TELEGRAM_BOT_TOKEN = "8752100386:AAEa-vMD4yPCKE0LPTFx-198Llbf8qZFgE8"
CHANNEL_CHAT_ID = "-1002392909031"  # আপনার চ্যানেলের সঠিক আইডি (নেগেটিভ সহ)
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
    """টেলিগ্রাম চ্যানেলে মেসেজ পাঠায়"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": CHANNEL_CHAT_ID, "text": message}
        response = requests.post(url, json=payload, timeout=10)
        
        # ডিবাগ তথ্য
        if response.status_code != 200:
            st.error(f"টেলিগ্রাম এরর: {response.text}")
            return False
        return True
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

def test_telegram_connection():
    """টেলিগ্রাম বট কানেকশন টেস্ট"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getMe"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('ok'):
                return True, data['result']['first_name']
        return False, None
    except:
        return False, None

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
    """চলতি মাসে যারা টাকা জমা দিয়েছে"""
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
    """চলতি মাসে যারা টাকা জমা দেয়নি"""
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
        padding: 20px;
        border-radius: 15px;
        margin-bottom: 20px;
        text-align: center;
        box-shadow: 0 10px 20px rgba(0,0,0,0.5);
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
        box-shadow: 0 10px 20px rgba(0,0,0,0.5);
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
        box-shadow: 0 10px 20px rgba(0,0,0,0.5);
    }
    .cash-box h2 {
        color: white;
        font-size: 28px;
        font-weight: 800;
        margin: 0;
    }
    
    .member-card {
        background: #21262d;
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 10px;
        border: 1px solid #30363d;
    }
    
    .copy-btn {
        background: #238636;
        color: white;
        border: none;
        padding: 5px 10px;
        border-radius: 5px;
        cursor: pointer;
        font-size: 12px;
    }
    .copy-btn:hover {
        background: #2ea043;
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
    }
    
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0d1117 0%, #161b22 100%);
        border-right: 1px solid #30363d;
    }
    section[data-testid="stSidebar"] * {
        color: #c9d1d9 !important;
    }
    
    p, h1, h2, h3, h4, h5, h6, li, .stMarkdown {
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

def copy_to_clipboard_js(text, element_id):
    """জাভাস্ক্রিপ্ট দিয়ে ক্লিপবোর্ডে কপি করা"""
    js_code = f"""
    <script>
    function copyToClipboard_{element_id}() {{
        navigator.clipboard.writeText("{text}").then(function() {{
            document.getElementById("{element_id}_msg").innerHTML = "✅ কপি হয়েছে!";
            setTimeout(function() {{
                document.getElementById("{element_id}_msg").innerHTML = "";
            }}, 2000);
        }});
    }}
    </script>
    <button onclick="copyToClipboard_{element_id}()" class="copy-btn">📋 কপি</button>
    <span id="{element_id}_msg" style="color: #3fb950; margin-left: 10px;"></span>
    """
    return js_code

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
        bot_ok, bot_name = test_telegram_connection()
        if bot_ok:
            st.success(f"✅ বট এক্টিভ: {bot_name}")
        else:
            st.error("❌ বট কানেক্টেড নয়")
        
        menu = st.radio(
            "নির্বাচন করুন",
            ["🏠 ড্যাশবোর্ড", "➕ নতুন সদস্য", "✏️ সদস্য ব্যবস্থাপনা", "💵 টাকা জমা", 
             "💰 লেনদেন ব্যবস্থাপনা", "🔗 সদস্য লিংক", "💸 খরচ", "📊 রিপোর্ট", 
             "📱 SMS টেস্ট", "🎲 লটারি", "🚪 লগআউট"],
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
            conn.close()
            
            col1.metric("👥 মোট সদস্য", f"{total_members} জন")
            col2.metric("💰 মোট জমা", f"{get_total_savings():,.0f} টাকা")
            col3.metric("📅 এই মাসের জমা", f"{get_current_month_collection():,.0f} টাকা")
            col4.metric("⚠️ বকেয়াদার", f"{len(get_unpaid_members())} জন")
        except:
            pass
        
        st.markdown("---")
        
        # SMS কন্ট্রোল
        st.subheader("📢 SMS কন্ট্রোল")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📢 ১ তারিখ রিমাইন্ডার", use_container_width=True, type="primary"):
                month_name = get_bangla_month()
                year = datetime.now().year
                msg = f"""📢 {SOMITI_NAME} - মাসিক কিস্তি রিমাইন্ডার

তারিখ: ১ {month_name} {year}

সকল সদস্যদের অনুরোধ:
অনুগ্রহ করে আগামী ১০ {month_name} {year} এর মধ্যে মাসিক কিস্তি পরিশোধ করুন।

ধন্যবাদ! 🙏"""
                if send_channel_message(msg):
                    st.success("✅ রিমাইন্ডার পাঠানো হয়েছে!")
                else:
                    st.error("❌ পাঠানো যায়নি। চ্যানেল আইডি চেক করুন।")
        
        with col2:
            if st.button("⚠️ ১০ তারিখ বকেয়া রিমাইন্ডার", use_container_width=True, type="primary"):
                unpaid = get_unpaid_members()
                if unpaid:
                    month_name = get_bangla_month()
                    msg = f"""⚠️ {SOMITI_NAME} - বকেয়া রিমাইন্ডার

বকেয়াদার তালিকা ({month_name}):"""
                    for m in unpaid[:10]:
                        msg += f"\n• {m[1]} ({m[0]}) - {m[3]:,.0f} টাকা"
                    if len(unpaid) > 10:
                        msg += f"\n... এবং আরও {len(unpaid) - 10} জন"
                    msg += "\n\n🙏 দয়া করে আজই পরিশোধ করুন!"
                    
                    if send_channel_message(msg):
                        st.success(f"✅ পাঠানো হয়েছে!")
                    else:
                        st.error("❌ পাঠানো যায়নি")
                else:
                    st.success("🎉 সবাই পরিশোধ করেছেন!")
    
    elif menu == "➕ নতুন সদস্য":
        st.markdown("### ➕ নতুন সদস্য নিবন্ধন")
        
        with st.form("new_member_form"):
            name = st.text_input("নাম *")
            phone = st.text_input("মোবাইল নম্বর *", placeholder="017XXXXXXXX")
            telegram_id = st.text_input("টেলিগ্রাম চ্যাট আইডি (ঐচ্ছিক)")
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
                        welcome = f"""🎉 {SOMITI_NAME} - নতুন সদস্য

{name} ({member_id}) সমিতিতে যোগদান করেছেন!
মাসিক কিস্তি: {monthly} টাকা

সবাই স্বাগতম জানান! 🎊"""
                        send_channel_message(welcome)
                        
                        st.success(f"✅ সদস্য তৈরি হয়েছে!")
                        st.info(f"আইডি: {member_id} | পাসওয়ার্ড: {password}")
                        st.balloons()
                        
                    except sqlite3.IntegrityError:
                        st.error("❌ এই মোবাইল নম্বর ইতিমধ্যে নিবন্ধিত")
    
    elif menu == "✏️ সদস্য ব্যবস্থাপনা":
        st.markdown("### ✏️ সদস্য ব্যবস্থাপনা")
        
        members = get_all_members()
        
        if members:
            for m in members:
                member_id, name, phone, password, telegram_id, status, monthly, savings = m
                monthly = float(monthly) if monthly else 500.0
                savings = float(savings) if savings else 0.0
                
                with st.expander(f"👤 {name} - {member_id} | 📱 {phone}"):
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        if st.button("📝 এডিট", key=f"edit_{member_id}"):
                            st.session_state[f"show_edit_{member_id}"] = True
                    with col2:
                        if st.button("🔐 পাসওয়ার্ড", key=f"pass_{member_id}"):
                            st.session_state[f"show_pass_{member_id}"] = True
                    with col3:
                        status_text = "নিষ্ক্রিয়" if status == 'active' else "সক্রিয়"
                        if st.button(f"🔄 {status_text} করুন", key=f"stat_{member_id}"):
                            new_status = 'inactive' if status == 'active' else 'active'
                            conn = sqlite3.connect('somiti.db')
                            c = conn.cursor()
                            c.execute("UPDATE members SET status=? WHERE id=?", (new_status, member_id))
                            conn.commit()
                            conn.close()
                            st.rerun()
                    with col4:
                        if st.button("🗑️ ডিলিট", key=f"del_{member_id}"):
                            st.session_state[f"show_del_{member_id}"] = True
                    
                    # এডিট ফর্ম
                    if st.session_state.get(f"show_edit_{member_id}"):
                        with st.form(f"edit_form_{member_id}"):
                            new_name = st.text_input("নাম", value=name)
                            new_tel = st.text_input("টেলিগ্রাম আইডি", value=telegram_id or "")
                            new_mon = st.number_input("মাসিক কিস্তি", value=monthly, step=50.0)
                            
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
                    
                    # পাসওয়ার্ড রিসেট
                    if st.session_state.get(f"show_pass_{member_id}"):
                        if st.button("✅ নতুন পাসওয়ার্ড জেনারেট", key=f"gen_pass_{member_id}"):
                            new_pass = generate_password()
                            conn = sqlite3.connect('somiti.db')
                            c = conn.cursor()
                            c.execute("UPDATE members SET password=? WHERE id=?", (new_pass, member_id))
                            conn.commit()
                            conn.close()
                            st.success(f"✅ নতুন পাসওয়ার্ড: {new_pass}")
                            del st.session_state[f"show_pass_{member_id}"]
                    
                    # ডিলিট
                    if st.session_state.get(f"show_del_{member_id}"):
                        if st.button("✅ নিশ্চিত ডিলিট", key=f"confirm_del_{member_id}"):
                            conn = sqlite3.connect('somiti.db')
                            c = conn.cursor()
                            c.execute("DELETE FROM transactions WHERE member_id=?", (member_id,))
                            c.execute("DELETE FROM members WHERE id=?", (member_id,))
                            conn.commit()
                            conn.close()
                            st.success("✅ ডিলিট হয়েছে!")
                            del st.session_state[f"show_del_{member_id}"]
                            st.rerun()
        else:
            st.info("কোনো সদস্য নেই")
    
    elif menu == "💵 টাকা জমা":
        st.markdown("### 💵 সদস্যের টাকা জমা")
        
        paid_members = get_paid_members()
        unpaid_members = get_unpaid_members()
        
        col1, col2 = st.columns(2)
        
        # জমা দিয়েছে - শুধু দেখা যাবে
        with col1:
            st.markdown("#### ✅ জমা দিয়েছে")
            
            if paid_members:
                for m in paid_members:
                    member_id, name, phone, monthly, savings = m
                    st.markdown(f"""
                    <div class="member-card">
                        <strong>{name}</strong> ({member_id})<br>
                        <small>📱 {phone} | 💰 জমা: {savings:,.0f} টাকা</small>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("কেউ এখনো জমা দেয়নি")
        
        # জমা দেয়নি - টাকা জমা নেওয়ার অপশন
        with col2:
            st.markdown("#### ❌ জমা দেয়নি")
            
            if unpaid_members:
                for m in unpaid_members:
                    member_id, name, phone, monthly, savings = m
                    
                    with st.expander(f"❌ {name} ({member_id})"):
                        st.write(f"📱 {phone}")
                        st.write(f"💰 বর্তমান জমা: {savings:,.0f} টাকা")
                        st.write(f"📅 মাসিক কিস্তি: {monthly:,.0f} টাকা")
                        
                        with st.form(f"deposit_{member_id}"):
                            # তারিখ সিলেক্ট
                            deposit_date = st.date_input("জমার তারিখ", value=datetime.now())
                            
                            # মাস সিলেক্ট
                            months = []
                            for i in range(12):
                                d = datetime.now() - timedelta(days=30*i)
                                months.append(d.strftime("%Y-%m"))
                            selected_month = st.selectbox("কিস্তির মাস", months)
                            
                            col_a, col_b = st.columns(2)
                            with col_a:
                                months_count = st.number_input("কত মাস", value=1, min_value=1, max_value=12)
                            with col_b:
                                late_fee = st.number_input("লেট ফি", value=0.0, step=10.0)
                            
                            total = monthly * months_count + late_fee
                            st.write(f"**মোট জমা: {total:,.0f} টাকা**")
                            
                            note = st.text_input("নোট (ঐচ্ছিক)")
                            
                            if st.form_submit_button("✅ জমা নিন", type="primary"):
                                today = deposit_date.strftime("%Y-%m-%d")
                                
                                conn = sqlite3.connect('somiti.db')
                                c = conn.cursor()
                                
                                for i in range(months_count):
                                    m_date = (datetime.strptime(selected_month, "%Y-%m") + timedelta(days=30*i)).strftime("%Y-%m")
                                    c.execute("""
                                        INSERT INTO transactions (member_id, amount, transaction_type, month, date, note, late_fee)
                                        VALUES (?, ?, ?, ?, ?, ?, ?)
                                    """, (member_id, monthly, 'deposit', m_date, today, note, late_fee if i == 0 else 0))
                                
                                c.execute("UPDATE members SET total_savings = total_savings + ? WHERE id = ?", 
                                         (total, member_id))
                                conn.commit()
                                conn.close()
                                
                                # চ্যানেলে মেসেজ
                                channel_msg = f"""✅ পেমেন্ট সফল - {SOMITI_NAME}

{name} ({member_id})
জমা: {total:,.0f} টাকা
তারিখ: {today}"""
                                send_channel_message(channel_msg)
                                
                                st.success(f"✅ {total:,.0f} টাকা জমা হয়েছে!")
                                st.rerun()
            else:
                st.success("🎉 সবাই জমা দিয়েছেন!")
    
    elif menu == "💰 লেনদেন ব্যবস্থাপনা":
        st.markdown("### 💰 লেনদেন ব্যবস্থাপনা")
        
        members = get_all_members()
        
        if members:
            # সদস্য সিলেক্ট
            member_options = {f"{m[1]} ({m[0]})": m[0] for m in members}
            selected = st.selectbox("সদস্য নির্বাচন করুন", list(member_options.keys()))
            
            if selected:
                member_id = member_options[selected]
                member = get_member_by_id(member_id)
                
                if member:
                    st.success(f"👤 {member[1]} | 💰 মোট জমা: {member[6]:,.0f} টাকা")
                    
                    # লেনদেন ইতিহাস
                    transactions = get_member_transactions(member_id)
                    
                    if transactions:
                        st.markdown("#### 📋 লেনদেন ইতিহাস")
                        
                        for trans in transactions:
                            trans_id, date, amount, month, late_fee, note = trans
                            
                            col1, col2, col3, col4, col5, col6 = st.columns([2, 1.5, 1.5, 1, 1, 1])
                            
                            col1.write(date)
                            col2.write(f"{amount:,.0f} টাকা")
                            col3.write(month)
                            col4.write(f"{late_fee:,.0f}" if late_fee else "0")
                            
                            if col5.button("✏️", key=f"edit_{trans_id}"):
                                st.session_state[f"edit_trans_{trans_id}"] = True
                            
                            if col6.button("🗑️", key=f"del_{trans_id}"):
                                conn = sqlite3.connect('somiti.db')
                                c = conn.cursor()
                                c.execute("UPDATE members SET total_savings = total_savings - ? WHERE id = ?", 
                                         (amount, member_id))
                                c.execute("DELETE FROM transactions WHERE id = ?", (trans_id,))
                                conn.commit()
                                conn.close()
                                st.success("✅ রিমুভ হয়েছে!")
                                st.rerun()
                            
                            # এডিট ফর্ম
                            if st.session_state.get(f"edit_trans_{trans_id}"):
                                with st.form(f"edit_{trans_id}"):
                                    new_amt = st.number_input("টাকা", value=float(amount), step=50.0)
                                    new_month = st.text_input("মাস", value=month)
                                    
                                    if st.form_submit_button("💾 সেভ"):
                                        conn = sqlite3.connect('somiti.db')
                                        c = conn.cursor()
                                        diff = new_amt - amount
                                        c.execute("UPDATE transactions SET amount=?, month=? WHERE id=?", 
                                                 (new_amt, new_month, trans_id))
                                        c.execute("UPDATE members SET total_savings = total_savings + ? WHERE id = ?", 
                                                 (diff, member_id))
                                        conn.commit()
                                        conn.close()
                                        st.success("✅ আপডেট হয়েছে!")
                                        del st.session_state[f"edit_trans_{trans_id}"]
                                        st.rerun()
                    else:
                        st.info("কোনো লেনদেন নেই")
                    
                    # নতুন লেনদেন যোগ
                    st.markdown("#### ➕ নতুন লেনদেন যোগ")
                    with st.form(f"add_{member_id}"):
                        new_amt = st.number_input("টাকা", value=0.0, step=50.0)
                        new_date = st.date_input("তারিখ", value=datetime.now())
                        new_month = st.text_input("মাস (YYYY-MM)", value=datetime.now().strftime("%Y-%m"))
                        
                        if st.form_submit_button("✅ যোগ করুন"):
                            if new_amt > 0:
                                conn = sqlite3.connect('somiti.db')
                                c = conn.cursor()
                                c.execute("""
                                    INSERT INTO transactions (member_id, amount, transaction_type, month, date)
                                    VALUES (?, ?, ?, ?, ?)
                                """, (member_id, new_amt, 'deposit', new_month, new_date.strftime("%Y-%m-%d")))
                                c.execute("UPDATE members SET total_savings = total_savings + ? WHERE id = ?", 
                                         (new_amt, member_id))
                                conn.commit()
                                conn.close()
                                st.success("✅ যোগ হয়েছে!")
                                st.rerun()
        else:
            st.info("কোনো সদস্য নেই")
    
    elif menu == "🔗 সদস্য লিংক":
        st.markdown("### 🔗 সদস্য লিংক ও পাসওয়ার্ড")
        
        members = get_all_members()
        app_url = get_app_url()
        
        if members:
            for m in members:
                member_id, name, phone, password, telegram_id, status, monthly, savings = m
                
                member_link = f"{app_url}/?member={member_id}"
                
                st.markdown(f"""
                <div class="member-card">
                    <h4>👤 {name} ({member_id})</h4>
                    <p><strong>📱 মোবাইল:</strong> {phone}</p>
                    <p><strong>🔗 লিংক:</strong> <code>{member_link}</code></p>
                    <p><strong>🔑 পাসওয়ার্ড:</strong> <code>{password}</code></p>
                </div>
                """, unsafe_allow_html=True)
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    # ক্লিপবোর্ডে কপি করার জন্য জাভাস্ক্রিপ্ট
                    st.markdown(f"""
                    <button onclick="navigator.clipboard.writeText('{member_link}')" 
                            style="background:#238636; color:white; border:none; padding:5px 10px; border-radius:5px; cursor:pointer;">
                        📋 লিংক কপি
                    </button>
                    """, unsafe_allow_html=True)
                
                with col2:
                    st.markdown(f"""
                    <button onclick="navigator.clipboard.writeText('{password}')" 
                            style="background:#238636; color:white; border:none; padding:5px 10px; border-radius:5px; cursor:pointer;">
                        📋 পাসওয়ার্ড কপি
                    </button>
                    """, unsafe_allow_html=True)
                
                with col3:
                    if telegram_id:
                        if st.button("📱 টেলিগ্রামে পাঠান", key=f"send_{member_id}"):
                            msg = f"""🔐 {SOMITI_NAME} - লগইন তথ্য

প্রিয় {name},
লিংক: {member_link}
মোবাইল: {phone}
পাসওয়ার্ড: {password}"""
                            if send_personal_message(telegram_id, msg):
                                st.success("✅ পাঠানো হয়েছে!")
                            else:
                                st.error("❌ পাঠানো যায়নি")
                
                st.markdown("---")
        else:
            st.info("কোনো সদস্য নেই")
    
    elif menu == "💸 খরচ":
        st.markdown("### 💸 খরচ ব্যবস্থাপনা")
        
        tab1, tab2 = st.tabs(["➕ নতুন খরচ", "📋 তালিকা"])
        
        with tab1:
            with st.form("expense_form"):
                desc = st.text_input("বিবরণ")
                amt = st.number_input("টাকা", value=0.0, step=10.0)
                cat = st.selectbox("ক্যাটাগরি", ["অফিস ভাড়া", "চা-নাস্তা", "স্টেশনারি", "পরিবহন", "অন্যান্য"])
                
                if st.form_submit_button("💾 সংরক্ষণ"):
                    if desc and amt > 0:
                        conn = sqlite3.connect('somiti.db')
                        c = conn.cursor()
                        c.execute("INSERT INTO expenses (description, amount, date, category) VALUES (?, ?, ?, ?)",
                                 (desc, amt, datetime.now().strftime("%Y-%m-%d"), cat))
                        conn.commit()
                        conn.close()
                        st.success(f"✅ {amt:,.0f} টাকা যোগ হয়েছে!")
                        st.rerun()
        
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
                        if c5.button("🗑️", key=f"del_exp_{eid}"):
                            conn = sqlite3.connect('somiti.db')
                            c = conn.cursor()
                            c.execute("DELETE FROM expenses WHERE id=?", (eid,))
                            conn.commit()
                            conn.close()
                            st.rerun()
                    
                    total = sum(e[3] for e in expenses)
                    st.metric("📊 মোট খরচ", f"{total:,.0f} টাকা")
            except:
                pass
    
    elif menu == "📊 রিপোর্ট":
        st.markdown("### 📊 রিপোর্ট")
        
        tab1, tab2 = st.tabs(["📈 মাসিক", "⚠️ বকেয়া"])
        
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
    
    elif menu == "📱 SMS টেস্ট":
        st.markdown("### 📱 SMS টেস্ট")
        
        # বট স্ট্যাটাস
        bot_ok, bot_name = test_telegram_connection()
        if bot_ok:
            st.success(f"✅ বট এক্টিভ: {bot_name}")
        else:
            st.error("❌ বট কানেক্টেড নয়। টোকেন চেক করুন।")
        
        st.info(f"চ্যানেল আইডি: {CHANNEL_CHAT_ID}")
        
        test_msg = st.text_area("টেস্ট মেসেজ", value=f"🧪 টেস্ট মেসেজ - {SOMITI_NAME}")
        
        if st.button("📨 টেস্ট পাঠান", type="primary"):
            if send_channel_message(test_msg):
                st.success("✅ মেসেজ পাঠানো হয়েছে!")
                st.balloons()
            else:
                st.error("❌ মেসেজ পাঠানো যায়নি। চ্যানেল আইডি সঠিক কিনা চেক করুন।")
                st.info("চ্যানেল আইডি নেগেটিভ নম্বর দিয়ে শুরু হয় (যেমন: -100...)")
    
    elif menu == "🎲 লটারি":
        st.markdown("### 🎲 লটারি")
        
        if st.button("🎲 বিজয়ী নির্বাচন", type="primary"):
            w = pick_lottery_winner()
            if w:
                mid, name, phone, sav, tel = w
                st.balloons()
                st.success(f"🎉 {name} [{mid}] বিজয়ী!")
                
                announce = f"""🎉 লটারি বিজয়ী - {SOMITI_NAME}

অভিনন্দন! {name} ({mid})
আজকের লাকি ড্র-তে বিজয়ী হয়েছেন! 🏆"""
                send_channel_message(announce)
            else:
                st.error("❌ কোনো সক্রিয় সদস্য নেই")

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
            
            # লেনদেন ইতিহাস
            st.markdown("---")
            st.markdown("#### 📋 লেনদেন ইতিহাস")
            
            trans = get_member_transactions(mid)
            
            if trans:
                df = pd.DataFrame(trans, columns=["ID", "তারিখ", "টাকা", "মাস", "লেট ফি", "নোট"])
                st.dataframe(df[["তারিখ", "টাকা", "মাস"]], use_container_width=True, hide_index=True)
                
                out = BytesIO()
                df.to_excel(out, index=False)
                st.download_button("📥 এক্সেল ডাউনলোড", out.getvalue(), f"{mid}_statement.xlsx")
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
