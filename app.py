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

# ============================================
# কনফিগারেশন
# ============================================
IMGBB_API_KEY = "9479d7a2b0908f8a9b353df1e2c38e00"
TELEGRAM_BOT_TOKEN = "8752100386:AAEa-vMD4yPCKE0LPTFx-198Llbf8qZFgE8"
ADMIN_CHAT_ID = "8548828754"

# এডমিন লগইন তথ্য
ADMIN_MOBILE = "01766222373"
ADMIN_PASSWORD = "oio112024"

# সমিতির নাম
SOMITI_NAME = "ঐক্য উদ্যোগ সংস্থা"

# ============================================
# হেডার স্টাইল
# ============================================
def show_header():
    st.markdown(f"""
    <style>
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
    </style>
    
    <div class="somiti-header">
        <h1>🌾 {SOMITI_NAME} 🌾</h1>
        <p>সঞ্চয় ও ঋণ ব্যবস্থাপনা সিস্টেম</p>
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
        payload = {
            "key": IMGBB_API_KEY,
            "image": img_str,
        }
        response = requests.post(url, payload)
        
        if response.status_code == 200:
            return response.json()['data']['url']
        else:
            return None
    except:
        return None

def send_telegram_message(chat_id: str, message: str):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML"
        }
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

def notify_admin_new_member(member_data: dict):
    message = f"""
🆕 <b>নতুন সদস্য - {SOMITI_NAME}</b>

────────────────────
👤 <b>নাম:</b> {member_data['name']}
📱 <b>মোবাইল:</b> {member_data['phone']}
🆔 <b>আইডি:</b> {member_data['id']}
📬 <b>টেলিগ্রাম:</b> <code>{member_data['telegram_id']}</code>
📅 <b>তারিখ:</b> {member_data['join_date']}
────────────────────

✅ সদস্যটি তার টেলিগ্রামে লগইন তথ্য পেয়েছে।
"""
    send_telegram_message(ADMIN_CHAT_ID, message)

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
# UI কম্পোনেন্টস
# ============================================
def login_screen():
    show_header()
    
    st.markdown("""
    <style>
    .login-card {
        max-width: 400px;
        margin: 30px auto;
        padding: 30px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        background: white;
    }
    .stButton > button {
        width: 100%;
        background-color: #0066CC;
        color: white;
        font-size: 16px;
        padding: 10px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    with st.container():
        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        st.title("🔐 লগইন")
        
        phone = st.text_input("📱 মোবাইল নম্বর", placeholder="017XXXXXXXX")
        password = st.text_input("🔑 পাসওয়ার্ড", type="password")
        
        if st.button("প্রবেশ করুন", type="primary"):
            # এডমিন চেক
            if phone == ADMIN_MOBILE and password == ADMIN_PASSWORD:
                st.session_state.logged_in = True
                st.session_state.user_type = 'admin'
                st.success("✅ এডমিন হিসেবে লগইন সফল!")
                st.rerun()
            else:
                # সাধারণ সদস্য চেক
                conn = sqlite3.connect('somiti.db')
                c = conn.cursor()
                c.execute("SELECT id, password FROM members WHERE phone = ?", (phone,))
                result = c.fetchone()
                conn.close()
                
                if result and result[1] == password:
                    st.session_state.logged_in = True
                    st.session_state.user_type = 'member'
                    st.session_state.member_id = result[0]
                    st.success("✅ লগইন সফল!")
                    st.rerun()
                else:
                    st.error("❌ ভুল মোবাইল নম্বর বা পাসওয়ার্ড")
        
        st.markdown("---")
        st.caption("পাসওয়ার্ড ভুলে গেলে এডমিনের সাথে যোগাযোগ করুন: 01766222373")
        
        st.markdown('</div>', unsafe_allow_html=True)

def admin_dashboard():
    st.set_page_config(page_title=f"{SOMITI_NAME} - এডমিন", page_icon="💰", layout="wide")
    show_header()
    
    with st.sidebar:
        st.title("📋 এডমিন মেনু")
        st.caption(f"👑 এডমিন | {ADMIN_MOBILE}")
        menu = st.radio(
            "নেভিগেশন",
            ["🏠 ড্যাশবোর্ড", "➕ নতুন সদস্য", "💵 টাকা জমা", "📊 রিপোর্ট", "🚪 লগআউট"]
        )
        
        conn = sqlite3.connect('somiti.db')
        c = conn.cursor()
        c.execute("SELECT SUM(total_savings) FROM members")
        total = c.fetchone()[0] or 0
        conn.close()
        
        st.metric("💰 মোট জমা", f"{total:,.0f} টাকা")
    
    if menu == "🚪 লগআউট":
        st.session_state.logged_in = False
        st.session_state.user_type = None
        st.rerun()
    
    elif menu == "🏠 ড্যাশবোর্ড":
        st.title("🏠 এডমিন ড্যাশবোর্ড")
        
        col1, col2, col3 = st.columns(3)
        
        conn = sqlite3.connect('somiti.db')
        c = conn.cursor()
        
        c.execute("SELECT COUNT(*) FROM members")
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
        
        st.subheader("📋 সাম্প্রতিক লেনদেন")
        c.execute("""
            SELECT m.name, t.amount, t.date 
            FROM transactions t
            JOIN members m ON t.member_id = m.id
            ORDER BY t.date DESC LIMIT 10
        """)
        recent = c.fetchall()
        conn.close()
        
        if recent:
            df = pd.DataFrame(recent, columns=["নাম", "টাকা", "তারিখ"])
            st.dataframe(df, use_container_width=True)
        else:
            st.info("এখনো কোনো লেনদেন হয়নি")
    
    elif menu == "➕ নতুন সদস্য":
        st.title("➕ নতুন সদস্য নিবন্ধন")
        
        with st.form("new_member_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                name = st.text_input("নাম *")
                phone = st.text_input("মোবাইল নম্বর *", placeholder="017XXXXXXXX")
                telegram_id = st.text_input("টেলিগ্রাম চ্যাট আইডি *", 
                                          help="সদস্যের টেলিগ্রাম চ্যাট আইডি")
            
            with col2:
                photo = st.file_uploader("ছবি আপলোড", type=['jpg', 'jpeg', 'png'])
                if photo:
                    st.image(photo, width=200)
            
            submitted = st.form_submit_button("✅ সদস্য যোগ করুন", type="primary")
            
            if submitted:
                if not name or not phone or not telegram_id:
                    st.error("❌ নাম, মোবাইল এবং টেলিগ্রাম আইডি আবশ্যক")
                elif phone == ADMIN_MOBILE:
                    st.error("❌ এটি এডমিনের মোবাইল নম্বর। অন্য নম্বর ব্যবহার করুন।")
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
                            INSERT INTO members (id, name, phone, password, telegram_chat_id, photo_url, join_date)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (member_id, name, phone, password, telegram_id, photo_url, join_date))
                        conn.commit()
                        
                        # সদস্যকে মেসেজ
                        app_url = get_app_url()
                        member_msg = f"""
🎉 <b>{SOMITI_NAME}-এ স্বাগতম, {name}!</b>

আপনার সদস্যপদ তৈরি হয়েছে।

🔗 <b>লিংক:</b> {app_url}
📱 <b>মোবাইল:</b> {phone}
🔑 <b>পাসওয়ার্ড:</b> <code>{password}</code>

⚠️ লগইন করে পাসওয়ার্ড পরিবর্তন করুন।
"""
                        send_telegram_message(telegram_id, member_msg)
                        
                        # এডমিন গ্রুপে নোটিফিকেশন
                        notify_admin_new_member({
                            'name': name,
                            'phone': phone,
                            'id': member_id,
                            'telegram_id': telegram_id,
                            'join_date': join_date
                        })
                        
                        st.success(f"""
                        ✅ সদস্য তৈরি হয়েছে!
                        
                        **সদস্য আইডি:** {member_id}
                        **পাসওয়ার্ড:** {password}
                        
                        📨 সদস্যের টেলিগ্রামে তথ্য পাঠানো হয়েছে
                        📢 এডমিন গ্রুপে নোটিফিকেশন পাঠানো হয়েছে
                        """)
                        
                        st.balloons()
                        
                    except sqlite3.IntegrityError:
                        st.error("❌ এই মোবাইল নম্বরটি ইতিমধ্যে নিবন্ধিত")
                    finally:
                        conn.close()
    
    elif menu == "💵 টাকা জমা":
        st.title("💵 সদস্যের টাকা জমা")
        
        conn = sqlite3.connect('somiti.db')
        c = conn.cursor()
        c.execute("SELECT id, name, phone FROM members ORDER BY name")
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
                note = st.text_input("নোট (ঐচ্ছিক)")
                
                submitted = st.form_submit_button("✅ টাকা জমা করুন", type="primary")
                
                if submitted:
                    if amount <= 0:
                        st.error("❌ টাকার পরিমাণ ০ এর বেশি হতে হবে")
                    else:
                        member_id = member_dict[selected_member]
                        today = datetime.now().strftime("%Y-%m-%d")
                        
                        conn = sqlite3.connect('somiti.db')
                        c = conn.cursor()
                        
                        c.execute("""
                            INSERT INTO transactions (member_id, amount, transaction_type, month, date, note)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (member_id, amount, 'deposit', month, today, note))
                        
                        c.execute("UPDATE members SET total_savings = total_savings + ? WHERE id = ?", 
                                 (amount, member_id))
                        
                        c.execute("SELECT name, telegram_chat_id FROM members WHERE id = ?", (member_id,))
                        member_info = c.fetchone()
                        
                        conn.commit()
                        conn.close()
                        
                        if member_info and member_info[1]:
                            message = f"""
✅ <b>পেমেন্ট সফল - {SOMITI_NAME}</b>

প্রিয় {member_info[0]},
আপনার জমা হয়েছে: <b>{amount:,.0f} টাকা</b>
তারিখ: {today}
মাস: {month}

ধন্যবাদ! 🙏
"""
                            send_telegram_message(member_info[1], message)
                        
                        st.success(f"✅ {amount:,.0f} টাকা জমা হয়েছে")
                        st.balloons()
        
        else:
            st.warning("⚠️ কোনো সদস্য নেই। আগে সদস্য যোগ করুন।")
    
    elif menu == "📊 রিপোর্ট":
        st.title("📊 রিপোর্ট ও পরিসংখ্যান")
        
        tab1, tab2, tab3 = st.tabs(["📈 মাসিক রিপোর্ট", "⚠️ বকেয়া তালিকা", "👥 সদস্য তালিকা"])
        
        with tab1:
            st.subheader("মাসিক জমার রিপোর্ট")
            
            conn = sqlite3.connect('somiti.db')
            c = conn.cursor()
            c.execute("""
                SELECT month, SUM(amount) as total
                FROM transactions
                GROUP BY month
                ORDER BY month DESC
                LIMIT 12
            """)
            monthly_data = c.fetchall()
            conn.close()
            
            if monthly_data:
                df = pd.DataFrame(monthly_data, columns=["মাস", "মোট জমা"])
                st.bar_chart(df.set_index("মাস"))
                st.dataframe(df, use_container_width=True)
            else:
                st.info("এখনো কোনো লেনদেন হয়নি")
        
        with tab2:
            st.subheader("⚠️ চলতি মাসে যারা জমা দেননি")
            
            current_month = datetime.now().strftime("%Y-%m")
            
            conn = sqlite3.connect('somiti.db')
            c = conn.cursor()
            
            c.execute("SELECT DISTINCT member_id FROM transactions WHERE month = ?", (current_month,))
            paid_members = [row[0] for row in c.fetchall()]
            
            if paid_members:
                placeholders = ','.join('?' * len(paid_members))
                c.execute(f"""
                    SELECT id, name, phone, total_savings 
                    FROM members 
                    WHERE id NOT IN ({placeholders}) AND status = 'active'
                """, paid_members)
            else:
                c.execute("SELECT id, name, phone, total_savings FROM members WHERE status = 'active'")
            
            defaulters = c.fetchall()
            conn.close()
            
            if defaulters:
                df = pd.DataFrame(defaulters, columns=["আইডি", "নাম", "মোবাইল", "বর্তমান জমা"])
                st.dataframe(df, use_container_width=True)
                st.warning(f"⚠️ মোট {len(defaulters)} জন সদস্য এখনো জমা দেননি")
            else:
                st.success("🎉 সবাই এই মাসের জমা দিয়েছেন!")
        
        with tab3:
            st.subheader("👥 সকল সদস্য")
            
            conn = sqlite3.connect('somiti.db')
            c = conn.cursor()
            c.execute("""
                SELECT id, name, phone, total_savings, join_date 
                FROM members 
                ORDER BY name
            """)
            all_members = c.fetchall()
            conn.close()
            
            if all_members:
                df = pd.DataFrame(all_members, 
                                 columns=["আইডি", "নাম", "মোবাইল", "মোট জমা", "যোগদানের তারিখ"])
                st.dataframe(df, use_container_width=True)

def member_dashboard():
    st.set_page_config(page_title=f"{SOMITI_NAME} - সদস্য", page_icon="👤", layout="wide")
    show_header()
    
    conn = sqlite3.connect('somiti.db')
    c = conn.cursor()
    c.execute("""
        SELECT name, phone, photo_url, total_savings 
        FROM members 
        WHERE id = ?
    """, (st.session_state.member_id,))
    member = c.fetchone()
    
    if not member:
        st.error("সদস্য পাওয়া যায়নি")
        st.session_state.logged_in = False
        st.rerun()
        return
    
    name, phone, photo_url, total_savings = member
    
    with st.sidebar:
        if photo_url:
            st.image(photo_url, width=200)
        else:
            st.image("https://via.placeholder.com/200", width=200)
        
        st.title(f"👤 {name}")
        st.caption(f"📱 {phone}")
        
        st.markdown("---")
        menu = st.radio("মেনু", ["📊 ড্যাশবোর্ড", "🔑 পাসওয়ার্ড পরিবর্তন", "🚪 লগআউট"])
    
    if menu == "🚪 লগআউট":
        st.session_state.logged_in = False
        st.session_state.user_type = None
        st.session_state.member_id = None
        st.rerun()
    
    elif menu == "📊 ড্যাশবোর্ড":
        st.title(f"স্বাগতম, {name}! 👋")
        
        st.markdown("---")
        col1, col2 = st.columns(2)
        col1.metric("💰 বর্তমান জমা", f"{total_savings:,.0f} টাকা")
        
        current_month = datetime.now().strftime("%Y-%m")
        c.execute("""
            SELECT SUM(amount) FROM transactions 
            WHERE member_id = ? AND month = ?
        """, (st.session_state.member_id, current_month))
        month_paid = c.fetchone()[0] or 0
        col2.metric(f"📅 {current_month} জমা", f"{month_paid:,.0f} টাকা")
        
        st.markdown("---")
        st.subheader("📋 লেনদেন ইতিহাস")
        
        c.execute("""
            SELECT date, amount, month, note 
            FROM transactions 
            WHERE member_id = ?
            ORDER BY date DESC 
            LIMIT 20
        """, (st.session_state.member_id,))
        transactions = c.fetchall()
        
        if transactions:
            df = pd.DataFrame(transactions, columns=["তারিখ", "টাকা", "মাস", "নোট"])
            st.dataframe(df, use_container_width=True)
        else:
            st.info("এখনো কোনো লেনদেন হয়নি")
    
    elif menu == "🔑 পাসওয়ার্ড পরিবর্তন":
        st.title("🔑 পাসওয়ার্ড পরিবর্তন")
        
        with st.form("change_password_form"):
            current_pass = st.text_input("বর্তমান পাসওয়ার্ড", type="password")
            new_pass = st.text_input("নতুন পাসওয়ার্ড", type="password")
            confirm_pass = st.text_input("নতুন পাসওয়ার্ড নিশ্চিত করুন", type="password")
            
            submitted = st.form_submit_button("🔄 পাসওয়ার্ড আপডেট করুন")
            
            if submitted:
                c.execute("SELECT password FROM members WHERE id = ?", (st.session_state.member_id,))
                stored_pass = c.fetchone()[0]
                
                if current_pass != stored_pass:
                    st.error("❌ বর্তমান পাসওয়ার্ড ভুল")
                elif new_pass != confirm_pass:
                    st.error("❌ নতুন পাসওয়ার্ড মিলছে না")
                elif len(new_pass) < 4:
                    st.error("❌ পাসওয়ার্ড কমপক্ষে ৪ অক্ষরের হতে হবে")
                else:
                    c.execute("UPDATE members SET password = ? WHERE id = ?", 
                             (new_pass, st.session_state.member_id))
                    conn.commit()
                    st.success("✅ পাসওয়ার্ড সফলভাবে পরিবর্তন হয়েছে")
                    
                    c.execute("SELECT telegram_chat_id FROM members WHERE id = ?", 
                             (st.session_state.member_id,))
                    chat_id = c.fetchone()[0]
                    if chat_id:
                        message = f"""
🔐 <b>পাসওয়ার্ড পরিবর্তন - {SOMITI_NAME}</b>

আপনার পাসওয়ার্ড সফলভাবে পরিবর্তন করা হয়েছে।
"""
                        send_telegram_message(chat_id, message)
    
    conn.close()

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
