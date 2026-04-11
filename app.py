import streamlit as st
import sqlite3
import requests
import random
import string
import pandas as pd
from PIL import Image
from io import BytesIO
from datetime import datetime, timedelta
import base64
import re
import os

# ============================================
# কনফিগারেশন
# ============================================
IMGBB_API_KEY = "9479d7a2b0908f8a9b353df1e2c38e00"
TELEGRAM_BOT_TOKEN = "8752100386:AAEa-vMD4yPCKE0LPTFx-198Llbf8qZFgE8"
ADMIN_CHAT_ID = "8548828754"
ADMIN_MOBILE = "01766222373"
ADMIN_PASSWORD = "oio112024"
SOMITI_NAME = "ঐক্য উদ্যোগ সংস্থা"

# ============================================
# ডিফল্ট মেসেজ টেমপ্লেট
# ============================================
DEFAULT_TEMPLATES = {
    "first_day": """📢 *{somiti_name}* - মাসিক কিস্তি রিমাইন্ডার

প্রিয় {member_name},
{month} {year} মাসের কিস্তির রিমাইন্ডার।

💰 *আপনার মাসিক কিস্তি:* {monthly_amount} টাকা
💎 *বর্তমান জমা:* {total_savings} টাকা

📅 *শেষ তারিখ:* ১০ {month} {year}

⚠️ দয়া করে ১০ তারিখের মধ্যে কিস্তি পরিশোধ করুন।

ধন্যবাদ! 🙏""",

    "tenth_day": """⚠️ *{somiti_name}* - জরুরি বকেয়া রিমাইন্ডার

প্রিয় {member_name},
{month} {year} মাসের কিস্তি এখনো সম্পূর্ণ পরিশোধ করেননি।

💰 *মাসিক কিস্তি:* {total_due_amount} টাকা
✅ *জমা দিয়েছেন:* {paid_amount} টাকা
❌ *বকেয়া আছেন:* {due_amount} টাকা

🙏 দয়া করে আজই বকেয়া পরিশোধ করুন।

প্রয়োজনে এডমিনের সাথে যোগাযোগ করুন: {admin_mobile}""",

    "payment_success": """✅ *পেমেন্ট সফল - {somiti_name}*

প্রিয় {member_name},
আপনার জমা সফলভাবে গৃহীত হয়েছে।

💰 *জমার পরিমাণ:* {amount} টাকা
📅 *তারিখ:* {date}
📆 *মাস:* {month}

💎 *বর্তমান মোট জমা:* {total_savings} টাকা

ধন্যবাদ! 🙏"""
}

# ============================================
# ডাটাবেজ সেটআপ ও মাইগ্রেশন
# ============================================
def init_db():
    conn = sqlite3.connect('somiti.db')
    c = conn.cursor()
    
    # সদস্য টেবিল তৈরি
    c.execute('''
        CREATE TABLE IF NOT EXISTS members (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            phone TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            telegram_chat_id TEXT,
            photo_url TEXT,
            total_savings REAL DEFAULT 0,
            join_date TEXT,
            status TEXT DEFAULT 'active'
        )
    ''')
    
    # monthly_savings কলাম না থাকলে যোগ করা
    try:
        c.execute("SELECT monthly_savings FROM members LIMIT 1")
    except sqlite3.OperationalError:
        c.execute("ALTER TABLE members ADD COLUMN monthly_savings REAL DEFAULT 500")
    
    # লেনদেন টেবিল
    c.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id TEXT NOT NULL,
            amount REAL NOT NULL,
            transaction_type TEXT NOT NULL,
            month TEXT,
            date TEXT NOT NULL,
            note TEXT,
            FOREIGN KEY (member_id) REFERENCES members (id)
        )
    ''')
    
    # মেসেজ টেমপ্লেট টেবিল
    c.execute('''
        CREATE TABLE IF NOT EXISTS message_templates (
            id TEXT PRIMARY KEY,
            template_name TEXT NOT NULL,
            template_content TEXT NOT NULL,
            updated_at TEXT
        )
    ''')
    
    for template_id, content in DEFAULT_TEMPLATES.items():
        c.execute("SELECT COUNT(*) FROM message_templates WHERE id = ?", (template_id,))
        if c.fetchone()[0] == 0:
            c.execute("""
                INSERT INTO message_templates (id, template_name, template_content, updated_at)
                VALUES (?, ?, ?, ?)
            """, (template_id, template_id, content, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    
    conn.commit()
    conn.close()

# ============================================
# হেডার স্টাইল (ডার্ক UI)
# ============================================
def show_header():
    conn = sqlite3.connect('somiti.db')
    c = conn.cursor()
    c.execute("SELECT SUM(total_savings) FROM members WHERE status = 'active'")
    total = c.fetchone()[0] or 0
    conn.close()
    
    st.markdown(f"""
    <style>
    /* ডার্ক ব্যাকগ্রাউন্ড */
    .main {{
        background-color: #1a1a2e;
    }}
    
    .stApp {{
        background-color: #1a1a2e;
    }}
    
    section[data-testid="stSidebar"] {{
        background-color: #16213e;
        border-right: 1px solid #0f3460;
    }}
    
    /* হেডার - নীল গ্রেডিয়েন্ট */
    .somiti-header {{
        background: linear-gradient(135deg, #0066CC 0%, #0099CC 100%);
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }}
    
    .somiti-header h1 {{
        color: white;
        font-size: 32px;
        font-weight: bold;
        margin: 0;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
    }}
    
    .somiti-header p {{
        color: #E0F0FF;
        font-size: 14px;
        margin: 5px 0 0 0;
    }}
    
    /* টোটাল বক্স - সবুজ */
    .total-box {{
        background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
        padding: 15px;
        border-radius: 10px;
        text-align: center;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }}
    
    .total-box h2 {{
        color: white;
        font-size: 28px;
        font-weight: bold;
        margin: 0;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
    }}
    
    .total-box p {{
        color: #E0FFE0;
        font-size: 14px;
        margin: 5px 0 0 0;
    }}
    
    /* টেক্সট কালার - ডার্ক মোডের জন্য */
    p, h1, h2, h3, h4, h5, h6, li, label, .stMarkdown {{
        color: #e0e0e0 !important;
    }}
    
    .stCaption {{
        color: #a0a0a0 !important;
    }}
    
    /* মেট্রিক কার্ড */
    div[data-testid="metric-container"] {{
        background-color: #16213e;
        border-radius: 10px;
        padding: 15px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.2);
        border: 1px solid #0f3460;
    }}
    
    div[data-testid="metric-container"] label {{
        color: #a0a0a0 !important;
    }}
    
    div[data-testid="metric-container"] div {{
        color: #00cc88 !important;
    }}
    
    /* ডাটাফ্রেম */
    .stDataFrame {{
        background-color: #16213e;
        border-radius: 10px;
        overflow: hidden;
        border: 1px solid #0f3460;
    }}
    
    .stDataFrame th {{
        background-color: #0f3460 !important;
        color: #e0e0e0 !important;
    }}
    
    .stDataFrame td {{
        background-color: #16213e !important;
        color: #c0c0c0 !important;
    }}
    
    /* ইনপুট ফিল্ড */
    .stTextInput > div > div > input,
    .stSelectbox > div > div,
    .stNumberInput > div > div > input {{
        background-color: #16213e;
        border: 1px solid #0f3460;
        color: #e0e0e0;
        border-radius: 8px;
    }}
    
    .stTextInput > div > div > input:focus {{
        border-color: #0099CC;
        box-shadow: 0 0 0 2px rgba(0,153,204,0.2);
    }}
    
    /* বাটন */
    .stButton > button {{
        background-color: #0066CC;
        color: white;
        font-weight: 600;
        border: none;
        border-radius: 8px;
        padding: 10px 20px;
        transition: all 0.3s ease;
    }}
    
    .stButton > button:hover {{
        background-color: #0052A3;
        box-shadow: 0 4px 8px rgba(0,0,0,0.3);
    }}
    
    .stButton > button[kind="primary"] {{
        background-color: #28a745;
        color: white;
    }}
    
    .stButton > button[kind="primary"]:hover {{
        background-color: #218838;
    }}
    
    /* ট্যাব */
    .stTabs [data-baseweb="tab-list"] {{
        background-color: transparent;
        gap: 8px;
    }}
    
    .stTabs [data-baseweb="tab"] {{
        border-radius: 8px 8px 0 0;
        padding: 10px 20px;
        background-color: #16213e;
        border: 1px solid #0f3460;
        color: #a0a0a0;
    }}
    
    .stTabs [aria-selected="true"] {{
        background: linear-gradient(135deg, #0066CC 0%, #0099CC 100%);
        color: white;
    }}
    
    /* এক্সপান্ডার */
    .streamlit-expanderHeader {{
        background-color: #16213e;
        border-radius: 8px;
        border: 1px solid #0f3460;
        color: #e0e0e0;
    }}
    
    /* রেডিও বাটন */
    .stRadio > div {{
        background-color: #16213e;
        padding: 10px;
        border-radius: 10px;
        border: 1px solid #0f3460;
    }}
    
    /* লগইন কার্ড */
    .login-card {{
        max-width: 400px;
        margin: 30px auto;
        padding: 30px;
        border-radius: 10px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.4);
        background: #16213e;
        border: 1px solid #0f3460;
    }}
    
    /* ফর্ম */
    .stForm {{
        background-color: #16213e;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #0f3460;
    }}
    
    /* সাকসেস/এরর মেসেজ */
    .stSuccess {{
        background-color: #1a3a2a;
        border-left: 4px solid #28a745;
        color: #d4edda;
    }}
    
    .stError {{
        background-color: #3a1a1a;
        border-left: 4px solid #dc3545;
        color: #f8d7da;
    }}
    
    .stWarning {{
        background-color: #3a2a1a;
        border-left: 4px solid #ffc107;
        color: #fff3cd;
    }}
    
    .stInfo {{
        background-color: #1a2a3a;
        border-left: 4px solid #17a2b8;
        color: #d1ecf1;
    }}
    </style>
    
    <div class="somiti-header">
        <h1>🌾 {SOMITI_NAME} 🌾</h1>
        <p>সঞ্চয় ও ঋণ ব্যবস্থাপনা সিস্টেম</p>
    </div>
    
    <div class="total-box">
        <h2>💰 {total:,.0f} টাকা</h2>
        <p>সমিতির মোট জমা</p>
    </div>
    """, unsafe_allow_html=True)

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

def upload_image_to_imgbb(image_file):
    if image_file is None:
        return None
    
    try:
        img = Image.open(image_file)
        img = img.resize((500, 500), Image.Resampling.LANCZOS)
        
        buffered = BytesIO()
        img.save(buffered, format="JPEG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        url = "https://api.imgbb.com/1/upload"
        payload = {"key": IMGBB_API_KEY, "image": img_str}
        response = requests.post(url, payload)
        
        if response.status_code == 200:
            return response.json()['data']['url']
        return None
    except:
        return None

def get_template(template_id):
    try:
        conn = sqlite3.connect('somiti.db')
        c = conn.cursor()
        c.execute("SELECT template_content FROM message_templates WHERE id = ?", (template_id,))
        result = c.fetchone()
        conn.close()
        return result[0] if result else DEFAULT_TEMPLATES.get(template_id, "")
    except:
        return DEFAULT_TEMPLATES.get(template_id, "")

def format_message(template_content, **kwargs):
    message = template_content
    kwargs['somiti_name'] = SOMITI_NAME
    kwargs['admin_mobile'] = ADMIN_MOBILE
    
    for key, value in kwargs.items():
        message = message.replace("{" + key + "}", str(value))
    
    message = re.sub(r'\*(.*?)\*', r'<b>\1</b>', message)
    return message

def send_telegram_message(chat_id: str, message: str):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": chat_id, "text": message, "parse_mode": "HTML"}
        response = requests.post(url, json=payload)
        return response.status_code == 200
    except:
        return False

def get_app_url():
    try:
        from streamlit.web.server.websocket_headers import _get_websocket_headers
        headers = _get_websocket_headers()
        if headers and "Host" in headers:
            return f"http://{headers['Host']}"
    except:
        pass
    return "http://localhost:8501"

def get_bangla_month():
    months = {
        1: "জানুয়ারি", 2: "ফেব্রুয়ারি", 3: "মার্চ", 4: "এপ্রিল",
        5: "মে", 6: "জুন", 7: "জুলাই", 8: "আগস্ট",
        9: "সেপ্টেম্বর", 10: "অক্টোবর", 11: "নভেম্বর", 12: "ডিসেম্বর"
    }
    return months[datetime.now().month]

# ============================================
# সেশন স্টেট
# ============================================
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_type' not in st.session_state:
    st.session_state.user_type = None
if 'member_id' not in st.session_state:
    st.session_state.member_id = None

# ============================================
# লগইন স্ক্রিন
# ============================================
def login_screen():
    show_header()
    
    with st.container():
        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        st.markdown("### 🔐 লগইন")
        
        phone = st.text_input("📱 মোবাইল নম্বর", placeholder="017XXXXXXXX")
        password = st.text_input("🔑 পাসওয়ার্ড", type="password")
        
        if st.button("প্রবেশ করুন", type="primary"):
            if phone == ADMIN_MOBILE and password == ADMIN_PASSWORD:
                st.session_state.logged_in = True
                st.session_state.user_type = 'admin'
                st.success("✅ এডমিন হিসেবে লগইন সফল!")
                st.rerun()
            else:
                conn = sqlite3.connect('somiti.db')
                c = conn.cursor()
                c.execute("SELECT id, password, status FROM members WHERE phone = ?", (phone,))
                result = c.fetchone()
                conn.close()
                
                if result and result[2] != 'active':
                    st.error("❌ আপনার অ্যাকাউন্ট নিষ্ক্রিয় করা হয়েছে।")
                elif result and result[1] == password:
                    st.session_state.logged_in = True
                    st.session_state.user_type = 'member'
                    st.session_state.member_id = result[0]
                    st.success("✅ লগইন সফল!")
                    st.rerun()
                else:
                    st.error("❌ ভুল মোবাইল নম্বর বা পাসওয়ার্ড")
        
        st.markdown("---")
        st.caption(f"পাসওয়ার্ড ভুলে গেলে এডমিনের সাথে যোগাযোগ করুন: {ADMIN_MOBILE}")
        st.markdown('</div>', unsafe_allow_html=True)

# ============================================
# এডমিন ড্যাশবোর্ড
# ============================================
def admin_dashboard():
    st.set_page_config(page_title=f"{SOMITI_NAME} - এডমিন", page_icon="💰", layout="wide")
    show_header()
    
    with st.sidebar:
        st.markdown("### 📋 এডমিন মেনু")
        st.caption(f"👑 এডমিন | {ADMIN_MOBILE}")
        
        menu = st.radio(
            "নেভিগেশন",
            ["🏠 ড্যাশবোর্ড", "➕ নতুন সদস্য", "✏️ সদস্য ব্যবস্থাপনা", "💵 টাকা জমা", 
             "📊 রিপোর্ট", "📝 মেসেজ টেমপ্লেট", "🚪 লগআউট"],
            label_visibility="collapsed"
        )
        
        try:
            conn = sqlite3.connect('somiti.db')
            c = conn.cursor()
            c.execute("SELECT SUM(total_savings) FROM members WHERE status = 'active'")
            total = c.fetchone()[0] or 0
            conn.close()
            st.metric("💰 মোট জমা", f"{total:,.0f} টাকা")
        except:
            st.metric("💰 মোট জমা", "0 টাকা")
    
    if menu == "🚪 লগআউট":
        st.session_state.logged_in = False
        st.session_state.user_type = None
        st.rerun()
    
    elif menu == "🏠 ড্যাশবোর্ড":
        st.markdown("### 🏠 এডমিন ড্যাশবোর্ড")
        
        col1, col2, col3 = st.columns(3)
        
        try:
            conn = sqlite3.connect('somiti.db')
            c = conn.cursor()
            
            c.execute("SELECT COUNT(*) FROM members WHERE status = 'active'")
            total_members = c.fetchone()[0]
            col1.metric("👥 মোট সদস্য", total_members)
            
            today = datetime.now().strftime("%Y-%m-%d")
            c.execute("SELECT SUM(amount) FROM transactions WHERE date = ?", (today,))
            today_deposit = c.fetchone()[0] or 0
            col2.metric("📅 আজকের জমা", f"{today_deposit:,.0f} টাকা")
            
            current_month = datetime.now().strftime("%Y-%m")
            c.execute("SELECT SUM(amount) FROM transactions WHERE month = ?", (current_month,))
            month_deposit = c.fetchone()[0] or 0
            col3.metric("📆 এই মাসের জমা", f"{month_deposit:,.0f} টাকা")
            
            st.markdown("---")
            st.markdown("#### 📋 সাম্প্রতিক লেনদেন")
            c.execute("""
                SELECT m.name, t.amount, t.date, t.month 
                FROM transactions t
                JOIN members m ON t.member_id = m.id
                ORDER BY t.date DESC LIMIT 10
            """)
            recent = c.fetchall()
            conn.close()
            
            if recent:
                df = pd.DataFrame(recent, columns=["নাম", "টাকা", "তারিখ", "মাস"])
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.info("এখনো কোনো লেনদেন হয়নি")
        except Exception as e:
            st.error(f"ডাটাবেজ এরর: {e}")
    
    elif menu == "➕ নতুন সদস্য":
        st.markdown("### ➕ নতুন সদস্য নিবন্ধন")
        
        with st.form("new_member_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                name = st.text_input("নাম *")
                phone = st.text_input("মোবাইল নম্বর *", placeholder="017XXXXXXXX")
                telegram_id = st.text_input("টেলিগ্রাম চ্যাট আইডি *")
                monthly_amount = st.number_input("মাসিক কিস্তির পরিমাণ", value=500, step=50)
            
            with col2:
                photo = st.file_uploader("ছবি আপলোড", type=['jpg', 'jpeg', 'png'])
                if photo:
                    st.image(photo, width=200)
            
            submitted = st.form_submit_button("✅ সদস্য যোগ করুন", type="primary")
            
            if submitted:
                if not name or not phone or not telegram_id:
                    st.error("❌ নাম, মোবাইল এবং টেলিগ্রাম আইডি আবশ্যক")
                elif phone == ADMIN_MOBILE:
                    st.error("❌ এটি এডমিনের মোবাইল নম্বর।")
                else:
                    photo_url = None
                    if photo:
                        with st.spinner("ছবি আপলোড হচ্ছে..."):
                            photo_url = upload_image_to_imgbb(photo)
                    
                    member_id = generate_member_id()
                    password = generate_password()
                    join_date = datetime.now().strftime("%Y-%m-%d")
                    
                    try:
                        conn = sqlite3.connect('somiti.db')
                        c = conn.cursor()
                        c.execute("""
                            INSERT INTO members (id, name, phone, password, telegram_chat_id, photo_url, monthly_savings, join_date)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (member_id, name, phone, password, telegram_id, photo_url, monthly_amount, join_date))
                        conn.commit()
                        conn.close()
                        
                        app_url = get_app_url()
                        member_msg = f"""
🎉 {SOMITI_NAME}-এ স্বাগতম, {name}!

আপনার সদস্যপদ তৈরি হয়েছে।

🔗 অ্যাপ লিংক: {app_url}
📱 মোবাইল: {phone}
🔑 পাসওয়ার্ড: {password}
💰 মাসিক কিস্তি: {monthly_amount} টাকা

⚠️ লগইন করে পাসওয়ার্ড পরিবর্তন করুন।
"""
                        send_telegram_message(telegram_id, member_msg)
                        
                        st.success(f"✅ সদস্য তৈরি হয়েছে! আইডি: {member_id} | পাসওয়ার্ড: {password}")
                        st.balloons()
                        
                    except sqlite3.IntegrityError:
                        st.error("❌ এই মোবাইল নম্বরটি ইতিমধ্যে নিবন্ধিত")
                    except Exception as e:
                        st.error(f"❌ এরর: {e}")
    
    elif menu == "✏️ সদস্য ব্যবস্থাপনা":
        st.markdown("### ✏️ সদস্য ব্যবস্থাপনা")
        
        try:
            conn = sqlite3.connect('somiti.db')
            c = conn.cursor()
            
            # কলাম চেক
            c.execute("PRAGMA table_info(members)")
            columns = [col[1] for col in c.fetchall()]
            
            if 'monthly_savings' in columns and 'telegram_chat_id' in columns:
                c.execute("SELECT id, name, phone, status, monthly_savings, telegram_chat_id FROM members ORDER BY name")
            else:
                c.execute("SELECT id, name, phone, status FROM members ORDER BY name")
            
            members = c.fetchall()
            conn.close()
            
            if members:
                member_dict = {f"{m[1]} ({m[2]})": m for m in members}
                selected = st.selectbox("সদস্য নির্বাচন করুন", list(member_dict.keys()))
                
                if selected:
                    member_data = member_dict[selected]
                    member_id = member_data[0]
                    name = member_data[1]
                    phone = member_data[2]
                    status = member_data[3] if len(member_data) > 3 else 'active'
                    monthly_savings = member_data[4] if len(member_data) > 4 else 500
                    telegram_id = member_data[5] if len(member_data) > 5 else ''
                    
                    tab1, tab2, tab3 = st.tabs(["📝 তথ্য এডিট", "🔐 পাসওয়ার্ড রিসেট", "🗑️ ডিলিট"])
                    
                    with tab1:
                        with st.form("edit_form"):
                            new_name = st.text_input("নাম", value=name)
                            new_telegram = st.text_input("টেলিগ্রাম চ্যাট আইডি", value=telegram_id or "")
                            new_monthly = st.number_input("মাসিক কিস্তি", value=monthly_savings, step=50)
                            new_status = st.selectbox("স্ট্যাটাস", ['active', 'inactive'], 
                                                     index=0 if status == 'active' else 1)
                            
                            if st.form_submit_button("💾 আপডেট"):
                                conn = sqlite3.connect('somiti.db')
                                c = conn.cursor()
                                c.execute("""
                                    UPDATE members 
                                    SET name = ?, telegram_chat_id = ?, monthly_savings = ?, status = ? 
                                    WHERE id = ?
                                """, (new_name, new_telegram, new_monthly, new_status, member_id))
                                conn.commit()
                                conn.close()
                                st.success("✅ আপডেট হয়েছে!")
                                st.rerun()
                    
                    with tab2:
                        st.markdown("#### পাসওয়ার্ড রিসেট")
                        if st.button("🔄 নতুন পাসওয়ার্ড জেনারেট করুন"):
                            new_password = generate_password()
                            conn = sqlite3.connect('somiti.db')
                            c = conn.cursor()
                            c.execute("UPDATE members SET password = ? WHERE id = ?", (new_password, member_id))
                            conn.commit()
                            conn.close()
                            
                            if telegram_id:
                                msg = f"🔐 আপনার নতুন পাসওয়ার্ড: {new_password}"
                                send_telegram_message(telegram_id, msg)
                            
                            st.success(f"✅ নতুন পাসওয়ার্ড: {new_password}")
                    
                    with tab3:
                        st.markdown("#### সদস্য ডিলিট")
                        st.warning("⚠️ ডিলিট করলে সকল তথ্য স্থায়ীভাবে মুছে যাবে!")
                        
                        if st.button("🗑️ সদস্য ডিলিট করুন", type="primary"):
                            conn = sqlite3.connect('somiti.db')
                            c = conn.cursor()
                            c.execute("DELETE FROM transactions WHERE member_id = ?", (member_id,))
                            c.execute("DELETE FROM members WHERE id = ?", (member_id,))
                            conn.commit()
                            conn.close()
                            st.success("✅ সদস্য ডিলিট হয়েছে!")
                            st.rerun()
            else:
                st.info("এখনো কোনো সদস্য নেই")
        except Exception as e:
            st.error(f"ডাটাবেজ এরর: {e}। দয়া করে somiti.db ফাইলটি ডিলিট করে আবার ট্রাই করুন।")
    
    elif menu == "💵 টাকা জমা":
        st.markdown("### 💵 সদস্যের টাকা জমা")
        
        try:
            conn = sqlite3.connect('somiti.db')
            c = conn.cursor()
            c.execute("SELECT id, name, phone FROM members WHERE status = 'active' ORDER BY name")
            members = c.fetchall()
            conn.close()
            
            if members:
                member_dict = {f"{m[1]} ({m[2]})": m[0] for m in members}
                
                with st.form("deposit_form"):
                    selected_member = st.selectbox("সদস্য নির্বাচন করুন", list(member_dict.keys()))
                    amount = st.number_input("টাকার পরিমাণ", min_value=0.0, step=100.0)
                    month = st.selectbox("কিস্তির মাস", 
                                        [datetime.now().strftime("%Y-%m")] + 
                                        [(datetime.now() - timedelta(days=30*i)).strftime("%Y-%m") for i in range(1,6)])
                    
                    submitted = st.form_submit_button("✅ টাকা জমা করুন", type="primary")
                    
                    if submitted and amount > 0:
                        member_id = member_dict[selected_member]
                        today = datetime.now().strftime("%Y-%m-%d")
                        
                        conn = sqlite3.connect('somiti.db')
                        c = conn.cursor()
                        
                        c.execute("""
                            INSERT INTO transactions (member_id, amount, transaction_type, month, date)
                            VALUES (?, ?, ?, ?, ?)
                        """, (member_id, amount, 'deposit', month, today))
                        
                        c.execute("UPDATE members SET total_savings = total_savings + ? WHERE id = ?", 
                                 (amount, member_id))
                        
                        c.execute("SELECT name, telegram_chat_id, total_savings FROM members WHERE id = ?", (member_id,))
                        member_info = c.fetchone()
                        
                        conn.commit()
                        conn.close()
                        
                        if member_info and member_info[1]:
                            template = get_template("payment_success")
                            message = format_message(
                                template,
                                member_name=member_info[0],
                                amount=f"{amount:,.0f}",
                                date=today,
                                month=month,
                                total_savings=f"{member_info[2]:,.0f}"
                            )
                            send_telegram_message(member_info[1], message)
                        
                        st.success(f"✅ {amount:,.0f} টাকা জমা হয়েছে")
                        st.balloons()
            else:
                st.warning("⚠️ কোনো সক্রিয় সদস্য নেই")
        except Exception as e:
            st.error(f"ডাটাবেজ এরর: {e}")
    
    elif menu == "📊 রিপোর্ট":
        st.markdown("### 📊 রিপোর্ট")
        
        tab1, tab2 = st.tabs(["📈 মাসিক রিপোর্ট", "⚠️ বকেয়া তালিকা"])
        
        with tab1:
            try:
                conn = sqlite3.connect('somiti.db')
                c = conn.cursor()
                c.execute("""
                    SELECT month, SUM(amount) as total
                    FROM transactions
                    GROUP BY month
                    ORDER BY month DESC
                    LIMIT 12
                """)
                data = c.fetchall()
                conn.close()
                
                if data:
                    df = pd.DataFrame(data, columns=["মাস", "মোট জমা"])
                    st.bar_chart(df.set_index("মাস"))
                    st.dataframe(df, use_container_width=True, hide_index=True)
                else:
                    st.info("এখনো কোনো লেনদেন হয়নি")
            except Exception as e:
                st.error(f"এরর: {e}")
        
        with tab2:
            try:
                current_month = datetime.now().strftime("%Y-%m")
                
                conn = sqlite3.connect('somiti.db')
                c = conn.cursor()
                
                c.execute("SELECT DISTINCT member_id FROM transactions WHERE month = ?", (current_month,))
                paid = [row[0] for row in c.fetchall()]
                
                if paid:
                    placeholders = ','.join('?' * len(paid))
                    c.execute(f"""
                        SELECT name, phone, monthly_savings 
                        FROM members 
                        WHERE status = 'active' AND id NOT IN ({placeholders})
                    """, paid)
                else:
                    c.execute("SELECT name, phone, monthly_savings FROM members WHERE status = 'active'")
                
                defaulters = c.fetchall()
                conn.close()
                
                if defaulters:
                    df = pd.DataFrame(defaulters, columns=["নাম", "মোবাইল", "মাসিক কিস্তি"])
                    st.dataframe(df, use_container_width=True, hide_index=True)
                    st.warning(f"⚠️ {len(defaulters)} জন বকেয়াদার")
                else:
                    st.success("🎉 সবাই কিস্তি পরিশোধ করেছেন!")
            except Exception as e:
                st.error(f"এরর: {e}")
    
    elif menu == "📝 মেসেজ টেমপ্লেট":
        st.markdown("### 📝 মেসেজ টেমপ্লেট ব্যবস্থাপনা")
        st.info("নিচের টেমপ্লেটগুলো এডিট করলে সেই অনুযায়ী অটোমেটিক মেসেজ যাবে।")
        
        with st.expander("📋 ভেরিয়েবল গাইড (ক্লিক করে দেখুন)"):
            st.markdown("""
            | ভেরিয়েবল | বিবরণ |
            |:----------|:-------|
            | `{somiti_name}` | সমিতির নাম |
            | `{member_name}` | সদস্যের নাম |
            | `{month}` | মাসের নাম |
            | `{year}` | বছর |
            | `{monthly_amount}` | মাসিক কিস্তি |
            | `{total_savings}` | মোট জমা |
            | `{total_due_amount}` | মোট কিস্তি |
            | `{paid_amount}` | জমা দিয়েছেন |
            | `{due_amount}` | বকেয়া |
            | `{amount}` | জমার পরিমাণ |
            | `{date}` | তারিখ |
            | `{admin_mobile}` | এডমিন মোবাইল |
            
            **ফরম্যাটিং:** \*টেক্সট\* লিখলে **বোল্ড** হবে।
            """)
        
        tab1, tab2, tab3 = st.tabs(["📢 ১ তারিখ", "⚠️ ১০ তারিখ", "✅ পেমেন্ট"])
        
        with tab1:
            current = get_template("first_day")
            new_template = st.text_area("টেমপ্লেট", value=current, height=200, key="t1")
            if st.button("💾 সেভ", key="s1"):
                try:
                    conn = sqlite3.connect('somiti.db')
                    c = conn.cursor()
                    c.execute("UPDATE message_templates SET template_content = ?, updated_at = ? WHERE id = 'first_day'",
                             (new_template, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                    conn.commit()
                    conn.close()
                    st.success("✅ সেভ হয়েছে!")
                except:
                    st.error("❌ সেভ করা যায়নি")
        
        with tab2:
            current = get_template("tenth_day")
            new_template = st.text_area("টেমপ্লেট", value=current, height=200, key="t2")
            if st.button("💾 সেভ", key="s2"):
                try:
                    conn = sqlite3.connect('somiti.db')
                    c = conn.cursor()
                    c.execute("UPDATE message_templates SET template_content = ?, updated_at = ? WHERE id = 'tenth_day'",
                             (new_template, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                    conn.commit()
                    conn.close()
                    st.success("✅ সেভ হয়েছে!")
                except:
                    st.error("❌ সেভ করা যায়নি")
        
        with tab3:
            current = get_template("payment_success")
            new_template = st.text_area("টেমপ্লেট", value=current, height=200, key="t3")
            if st.button("💾 সেভ", key="s3"):
                try:
                    conn = sqlite3.connect('somiti.db')
                    c = conn.cursor()
                    c.execute("UPDATE message_templates SET template_content = ?, updated_at = ? WHERE id = 'payment_success'",
                             (new_template, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                    conn.commit()
                    conn.close()
                    st.success("✅ সেভ হয়েছে!")
                except:
                    st.error("❌ সেভ করা যায়নি")

# ============================================
# সদস্য ড্যাশবোর্ড
# ============================================
def member_dashboard():
    st.set_page_config(page_title=f"{SOMITI_NAME} - সদস্য", page_icon="👤", layout="wide")
    show_header()
    
    try:
        conn = sqlite3.connect('somiti.db')
        c = conn.cursor()
        c.execute("""
            SELECT name, phone, photo_url, total_savings, monthly_savings 
            FROM members 
            WHERE id = ?
        """, (st.session_state.member_id,))
        member = c.fetchone()
        
        if not member:
            st.error("সদস্য পাওয়া যায়নি")
            st.session_state.logged_in = False
            st.rerun()
            return
        
        name, phone, photo_url, total_savings, monthly_savings = member
        
        with st.sidebar:
            if photo_url:
                st.image(photo_url, width=200)
            st.markdown(f"### 👤 {name}")
            st.caption(f"📱 {phone}")
            st.metric("💰 মোট জমা", f"{total_savings:,.0f} টাকা")
            
            menu = st.radio("মেনু", ["📊 ড্যাশবোর্ড", "🔑 পাসওয়ার্ড পরিবর্তন", "🚪 লগআউট"], label_visibility="collapsed")
        
        if menu == "🚪 লগআউট":
            st.session_state.logged_in = False
            st.session_state.user_type = None
            st.rerun()
        
        elif menu == "📊 ড্যাশবোর্ড":
            st.markdown(f"### স্বাগতম, {name}! 👋")
            
            col1, col2 = st.columns(2)
            col1.metric("💰 বর্তমান জমা", f"{total_savings:,.0f} টাকা")
            col2.metric("📅 মাসিক কিস্তি", f"{monthly_savings or 500:,.0f} টাকা")
            
            current_month = datetime.now().strftime("%Y-%m")
            c.execute("""
                SELECT SUM(amount) FROM transactions 
                WHERE member_id = ? AND month = ?
            """, (st.session_state.member_id, current_month))
            month_paid = c.fetchone()[0] or 0
            
            if month_paid >= (monthly_savings or 500):
                st.success(f"✅ আপনি {current_month} মাসের কিস্তি পরিশোধ করেছেন")
            else:
                due = (monthly_savings or 500) - month_paid
                st.warning(f"⚠️ {current_month} মাসের বকেয়া: {due:,.0f} টাকা")
            
            st.markdown("---")
            st.markdown("#### 📋 লেনদেন ইতিহাস")
            c.execute("""
                SELECT date, amount, month FROM transactions 
                WHERE member_id = ? ORDER BY date DESC LIMIT 10
            """, (st.session_state.member_id,))
            transactions = c.fetchall()
            
            if transactions:
                df = pd.DataFrame(transactions, columns=["তারিখ", "টাকা", "মাস"])
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.info("এখনো কোনো লেনদেন হয়নি")
        
        elif menu == "🔑 পাসওয়ার্ড পরিবর্তন":
            st.markdown("### 🔑 পাসওয়ার্ড পরিবর্তন")
            
            with st.form("change_pass"):
                current = st.text_input("বর্তমান পাসওয়ার্ড", type="password")
                new = st.text_input("নতুন পাসওয়ার্ড", type="password")
                confirm = st.text_input("নিশ্চিত করুন", type="password")
                
                if st.form_submit_button("🔄 পরিবর্তন করুন", type="primary"):
                    c.execute("SELECT password FROM members WHERE id = ?", (st.session_state.member_id,))
                    stored = c.fetchone()[0]
                    
                    if current != stored:
                        st.error("❌ বর্তমান পাসওয়ার্ড ভুল")
                    elif new != confirm:
                        st.error("❌ পাসওয়ার্ড মিলছে না")
                    elif len(new) < 4:
                        st.error("❌ কমপক্ষে ৪ অক্ষর হতে হবে")
                    else:
                        c.execute("UPDATE members SET password = ? WHERE id = ?", 
                                 (new, st.session_state.member_id))
                        conn.commit()
                        st.success("✅ পাসওয়ার্ড পরিবর্তন হয়েছে")
        
        conn.close()
    except Exception as e:
        st.error(f"ডাটাবেজ এরর: {e}")

# ============================================
# মেইন
# ============================================
def main():
    init_db()
    
    if not st.session_state.logged_in:
        login_screen()
    else:
        if st.session_state.user_type == 'admin':
            admin_dashboard()
        else:
            member_dashboard()

if __name__ == "__main__":
    main()
