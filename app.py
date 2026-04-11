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
# হেডার স্টাইল (আপডেটেড কালার)
# ============================================
def show_header():
    # ডাটাবেজ থেকে মোট টাকা আনা
    conn = sqlite3.connect('somiti.db')
    c = conn.cursor()
    c.execute("SELECT SUM(total_savings) FROM members WHERE status = 'active'")
    total = c.fetchone()[0] or 0
    conn.close()
    
    st.markdown(f"""
    <style>
    /* হেডার - নীল গ্রেডিয়েন্ট (আগের মত) */
    .somiti-header {{
        background: linear-gradient(135deg, #0066CC 0%, #0099CC 100%);
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
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
    
    /* টোটাল টাকার বক্স - সবুজ (আগের মত) */
    .total-box {{
        background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
        padding: 15px;
        border-radius: 10px;
        text-align: center;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
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
    
    /* বাটন স্টাইল - নীল */
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
        box-shadow: 0 4px 8px rgba(0,0,0,0.15);
    }}
    
    /* প্রাইমারি বাটন - সবুজ */
    .stButton > button[kind="primary"] {{
        background-color: #28a745;
        color: white;
    }}
    
    .stButton > button[kind="primary"]:hover {{
        background-color: #218838;
    }}
    
    /* লগইন কার্ড */
    .login-card {{
        max-width: 400px;
        margin: 30px auto;
        padding: 30px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        background: white;
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
# ডাটাবেজ সেটআপ
# ============================================
def init_db():
    conn = sqlite3.connect('somiti.db')
    c = conn.cursor()
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS members (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            phone TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            telegram_chat_id TEXT,
            photo_url TEXT,
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
            FOREIGN KEY (member_id) REFERENCES members (id)
        )
    ''')
    
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
    conn = sqlite3.connect('somiti.db')
    c = conn.cursor()
    c.execute("SELECT template_content FROM message_templates WHERE id = ?", (template_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else DEFAULT_TEMPLATES.get(template_id, "")

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
    
    st.markdown("""
    <style>
    .login-card {
        max-width: 400px;
        margin: 30px auto;
        padding: 30px;
        border-radius: 16px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.08);
        background: white;
        border: 1px solid #E8ECF1;
    }
    </style>
    """, unsafe_allow_html=True)
    
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
        
        conn = sqlite3.connect('somiti.db')
        c = conn.cursor()
        c.execute("SELECT SUM(total_savings) FROM members WHERE status = 'active'")
        total = c.fetchone()[0] or 0
        conn.close()
        
        st.metric("💰 মোট জমা", f"{total:,.0f} টাকা")
    
    if menu == "🚪 লগআউট":
        st.session_state.logged_in = False
        st.session_state.user_type = None
        st.rerun()
    
    elif menu == "🏠 ড্যাশবোর্ড":
        st.markdown("### 🏠 এডমিন ড্যাশবোর্ড")
        
        col1, col2, col3 = st.columns(3)
        
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
                    
                    conn = sqlite3.connect('somiti.db')
                    c = conn.cursor()
                    
                    try:
                        c.execute("""
                            INSERT INTO members (id, name, phone, password, telegram_chat_id, photo_url, monthly_savings, join_date)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (member_id, name, phone, password, telegram_id, photo_url, monthly_amount, join_date))
                        conn.commit()
                        conn.close()
                        
                        app_url = get_app_url()
                        member_msg = f"""
🎉 *{SOMITI_NAME}-এ স্বাগতম, {name}!*

আপনার সদস্যপদ তৈরি হয়েছে।

🔗 *অ্যাপ লিংক:* {app_url}
📱 *মোবাইল:* {phone}
🔑 *পাসওয়ার্ড:* {password}
💰 *মাসিক কিস্তি:* {monthly_amount} টাকা

⚠️ লগইন করে পাসওয়ার্ড পরিবর্তন করুন।
"""
                        member_msg = re.sub(r'\*(.*?)\*', r'\1', member_msg)
                        send_telegram_message(telegram_id, member_msg)
                        
                        st.success(f"✅ সদস্য তৈরি হয়েছে! আইডি: {member_id} | পাসওয়ার্ড: {password}")
                        st.balloons()
                        
                    except sqlite3.IntegrityError:
                        st.error("❌ এই মোবাইল নম্বরটি ইতিমধ্যে নিবন্ধিত")
    
    elif menu == "✏️ সদস্য ব্যবস্থাপনা":
        st.markdown("### ✏️ সদস্য ব্যবস্থাপনা")
        
        conn = sqlite3.connect('somiti.db')
        c = conn.cursor()
        c.execute("SELECT id, name, phone, status, monthly_savings, telegram_chat_id FROM members ORDER BY name")
        members = c.fetchall()
        conn.close()
        
        if members:
            member_dict = {f"{m[1]} ({m[2]})": m for m in members}
            selected = st.selectbox("সদস্য নির্বাচন করুন", list(member_dict.keys()))
            
            if selected:
                member_data = member_dict[selected]
                member_id, name, phone, status, monthly_savings, telegram_id = member_data
                
                tab1, tab2, tab3 = st.tabs(["📝 তথ্য এডিট", "🔐 পাসওয়ার্ড রিসেট", "🗑️ ডিলিট/নিষ্ক্রিয়"])
                
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
    
    elif menu == "💵 টাকা জমা":
        st.markdown("### 💵 সদস্যের টাকা জমা")
        
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
    
    elif menu == "📊 রিপোর্ট":
        st.markdown("### 📊 রিপোর্ট")
        
        tab1, tab2 = st.tabs(["📈 মাসিক রিপোর্ট", "⚠️ বকেয়া তালিকা"])
        
        with tab1:
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
        
        with tab2:
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
    
    elif menu == "📝 মেসেজ টেমপ্লেট":
        st.markdown("### 📝 মেসেজ টেমপ্লেট ব্যবস্থাপনা")
        st.info("নিচের টেমপ্লেটগুলো এডিট করলে সেই অনুযায়ী অটোমেটিক মেসেজ যাবে।")
        
        with st.expander("📋 ভেরিয়েবল গাইড (ক্লিক করে দেখুন)"):
            st.markdown("""
            | ভেরিয়েবল | বিবরণ | কোন টেমপ্লেটে ব্যবহার |
            |:----------|:-------|:---------------------|
            | `{somiti_name}` | সমিতির নাম | সব টেমপ্লেট |
            | `{member_name}` | সদস্যের নাম | সব টেমপ্লেট |
            | `{month}` | মাসের নাম | ১ তারিখ, ১০ তারিখ, পেমেন্ট |
            | `{year}` | বছর | ১ তারিখ, ১০ তারিখ |
            | `{monthly_amount}` | মাসিক কিস্তি | ১ তারিখ |
            | `{total_savings}` | মোট জমা | ১ তারিখ, পেমেন্ট |
            | `{total_due_amount}` | মোট কিস্তি | ১০ তারিখ |
            | `{paid_amount}` | জমা দিয়েছেন | ১০ তারিখ |
            | `{due_amount}` | বকেয়া | ১০ তারিখ |
            | `{amount}` | জমার পরিমাণ | পেমেন্ট সাকসেস |
            | `{date}` | তারিখ | পেমেন্ট সাকসেস |
            | `{admin_mobile}` | এডমিন মোবাইল | ১০ তারিখ |
            
            **ফরম্যাটিং:** \*টেক্সট\* লিখলে **বোল্ড** হবে।
            """)
        
        tab1, tab2, tab3 = st.tabs(["📢 ১ তারিখ রিমাইন্ডার", "⚠️ ১০ তারিখ রিমাইন্ডার", "✅ পেমেন্ট সাকসেস"])
        
        with tab1:
            current_template = get_template("first_day")
            new_template = st.text_area(
                "টেমপ্লেট এডিট করুন",
                value=current_template,
                height=250,
                key="first_day_template"
            )
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("💾 সেভ করুন", key="save_first"):
                    conn = sqlite3.connect('somiti.db')
                    c = conn.cursor()
                    c.execute("""
                        UPDATE message_templates 
                        SET template_content = ?, updated_at = ?
                        WHERE id = 'first_day'
                    """, (new_template, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                    conn.commit()
                    conn.close()
                    st.success("✅ টেমপ্লেট সেভ হয়েছে!")
            
            with col2:
                if st.button("👁️ প্রিভিউ", key="preview_first"):
                    sample = format_message(
                        new_template,
                        member_name="রহিম উদ্দিন",
                        month=get_bangla_month(),
                        year=datetime.now().year,
                        monthly_amount="500",
                        total_savings="5,000"
                    )
                    st.markdown("#### 📱 প্রিভিউ:")
                    st.markdown(f"<div style='background:#F0F2F6;padding:15px;border-radius:10px;'>{sample}</div>", 
                               unsafe_allow_html=True)
        
        with tab2:
            current_template = get_template("tenth_day")
            new_template = st.text_area(
                "টেমপ্লেট এডিট করুন",
                value=current_template,
                height=250,
                key="tenth_day_template"
            )
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("💾 সেভ করুন", key="save_tenth"):
                    conn = sqlite3.connect('somiti.db')
                    c = conn.cursor()
                    c.execute("""
                        UPDATE message_templates 
                        SET template_content = ?, updated_at = ?
                        WHERE id = 'tenth_day'
                    """, (new_template, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                    conn.commit()
                    conn.close()
                    st.success("✅ টেমপ্লেট সেভ হয়েছে!")
            
            with col2:
                if st.button("👁️ প্রিভিউ", key="preview_tenth"):
                    sample = format_message(
                        new_template,
                        member_name="রহিম উদ্দিন",
                        month=get_bangla_month(),
                        year=datetime.now().year,
                        total_due_amount="500",
                        paid_amount="200",
                        due_amount="300"
                    )
                    st.markdown("#### 📱 প্রিভিউ:")
                    st.markdown(f"<div style='background:#F0F2F6;padding:15px;border-radius:10px;'>{sample}</div>", 
                               unsafe_allow_html=True)
        
        with tab3:
            current_template = get_template("payment_success")
            new_template = st.text_area(
                "টেমপ্লেট এডিট করুন",
                value=current_template,
                height=250,
                key="payment_template"
            )
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("💾 সেভ করুন", key="save_payment"):
                    conn = sqlite3.connect('somiti.db')
                    c = conn.cursor()
                    c.execute("""
                        UPDATE message_templates 
                        SET template_content = ?, updated_at = ?
                        WHERE id = 'payment_success'
                    """, (new_template, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                    conn.commit()
                    conn.close()
                    st.success("✅ টেমপ্লেট সেভ হয়েছে!")
            
            with col2:
                if st.button("👁️ প্রিভিউ", key="preview_payment"):
                    sample = format_message(
                        new_template,
                        member_name="রহিম উদ্দিন",
                        amount="1,000",
                        date=datetime.now().strftime("%Y-%m-%d"),
                        month=datetime.now().strftime("%Y-%m"),
                        total_savings="6,000"
                    )
                    st.markdown("#### 📱 প্রিভিউ:")
                    st.markdown(f"<div style='background:#F0F2F6;padding:15px;border-radius:10px;'>{sample}</div>", 
                               unsafe_allow_html=True)

# ============================================
# সদস্য ড্যাশবোর্ড
# ============================================
def member_dashboard():
    st.set_page_config(page_title=f"{SOMITI_NAME} - সদস্য", page_icon="👤", layout="wide")
    show_header()
    
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
        col2.metric("📅 মাসিক কিস্তি", f"{monthly_savings:,.0f} টাকা")
        
        current_month = datetime.now().strftime("%Y-%m")
        c.execute("""
            SELECT SUM(amount) FROM transactions 
            WHERE member_id = ? AND month = ?
        """, (st.session_state.member_id, current_month))
        month_paid = c.fetchone()[0] or 0
        
        if month_paid >= monthly_savings:
            st.success(f"✅ আপনি {current_month} মাসের কিস্তি পরিশোধ করেছেন")
        else:
            due = monthly_savings - month_paid
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
