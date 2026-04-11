import streamlit as st
import sqlite3
import requests
import random
import string
import pandas as pd
from datetime import datetime, timedelta
import os

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
    """ডাটাবেজ তৈরি করে যদি না থাকে"""
    conn = sqlite3.connect('somiti.db')
    c = conn.cursor()
    
    # মেম্বার টেবিল
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
    
    # ট্রানজেকশন টেবিল
    c.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id TEXT NOT NULL,
            amount REAL NOT NULL,
            transaction_type TEXT NOT NULL,
            month TEXT,
            date TEXT NOT NULL,
            note TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

# ============================================
# টেলিগ্রাম মেসেজ ফাংশন
# ============================================
def send_telegram_message(chat_id, message):
    """টেলিগ্রামে মেসেজ পাঠায়"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": chat_id, "text": message}
        response = requests.post(url, json=payload, timeout=10)
        return response.status_code == 200
    except Exception as e:
        st.error(f"টেলিগ্রাম এরর: {e}")
        return False

# ============================================
# হেল্পার ফাংশন
# ============================================
def generate_member_id():
    """নতুন মেম্বার আইডি জেনারেট করে"""
    conn = sqlite3.connect('somiti.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM members")
    count = c.fetchone()[0] + 1
    conn.close()
    return f"M-{count:03d}"

def generate_password(length=6):
    """র্যান্ডম পাসওয়ার্ড জেনারেট করে"""
    return ''.join(random.choices(string.digits, k=length))

def get_total_savings():
    """মোট জমার পরিমাণ রিটার্ন করে"""
    try:
        conn = sqlite3.connect('somiti.db')
        c = conn.cursor()
        c.execute("SELECT SUM(total_savings) FROM members WHERE status = 'active'")
        total = c.fetchone()[0] or 0
        conn.close()
        return total
    except:
        return 0

# ============================================
# হেডার UI
# ============================================
def show_header():
    """হেডার ও মোট টাকার বক্স দেখায়"""
    total = get_total_savings()
    
    st.markdown(f"""
    <style>
    .main-header {{
        background: linear-gradient(135deg, #0066CC 0%, #0099CC 100%);
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }}
    .main-header h1 {{
        color: white;
        font-size: 32px;
        font-weight: bold;
        margin: 0;
    }}
    .main-header p {{
        color: #E0F0FF;
        font-size: 14px;
        margin: 5px 0 0 0;
    }}
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
    }}
    .total-box p {{
        color: #E0FFE0;
        font-size: 14px;
        margin: 5px 0 0 0;
    }}
    .login-box {{
        max-width: 400px;
        margin: 30px auto;
        padding: 30px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        background: white;
    }}
    .stButton > button {{
        background-color: #0066CC;
        color: white;
        font-weight: 600;
        border: none;
        border-radius: 8px;
        padding: 10px 20px;
        width: 100%;
    }}
    .stButton > button:hover {{
        background-color: #0052A3;
    }}
    </style>
    
    <div class="main-header">
        <h1>🌾 {SOMITI_NAME} 🌾</h1>
        <p>সঞ্চয় ও ঋণ ব্যবস্থাপনা সিস্টেম</p>
    </div>
    
    <div class="total-box">
        <h2>💰 {total:,.0f} টাকা</h2>
        <p>সমিতির মোট জমা</p>
    </div>
    """, unsafe_allow_html=True)

# ============================================
# সেশন স্টেট ইনিশিয়ালাইজ
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
    show_header()
    
    with st.container():
        st.markdown('<div class="login-box">', unsafe_allow_html=True)
        st.markdown("### 🔐 লগইন")
        
        phone = st.text_input("📱 মোবাইল নম্বর", placeholder="017XXXXXXXX", key="login_phone")
        password = st.text_input("🔑 পাসওয়ার্ড", type="password", key="login_pass")
        
        if st.button("প্রবেশ করুন", key="login_btn"):
            # এডমিন চেক
            if phone == ADMIN_MOBILE and password == ADMIN_PASSWORD:
                st.session_state.logged_in = True
                st.session_state.user_type = 'admin'
                st.success("✅ এডমিন লগইন সফল!")
                st.rerun()
            else:
                # মেম্বার চেক
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
# এডমিন ড্যাশবোর্ড
# ============================================
def admin_panel():
    show_header()
    
    # সাইডবার
    with st.sidebar:
        st.markdown("### 📋 এডমিন মেনু")
        st.caption(f"👑 {ADMIN_MOBILE}")
        
        menu = st.radio(
            "নির্বাচন করুন",
            ["🏠 ড্যাশবোর্ড", "➕ নতুন সদস্য", "✏️ সদস্য ব্যবস্থাপনা", "💵 টাকা জমা", "📊 রিপোর্ট", "🚪 লগআউট"],
            label_visibility="collapsed"
        )
        
        total = get_total_savings()
        st.metric("💰 মোট জমা", f"{total:,.0f} টাকা")
    
    # লগআউট
    if menu == "🚪 লগআউট":
        for key in ['logged_in', 'user_type', 'member_id']:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()
    
    # ড্যাশবোর্ড
    elif menu == "🏠 ড্যাশবোর্ড":
        st.markdown("### 🏠 এডমিন ড্যাশবোর্ড")
        
        try:
            conn = sqlite3.connect('somiti.db')
            c = conn.cursor()
            
            col1, col2, col3 = st.columns(3)
            
            # মোট সদস্য
            c.execute("SELECT COUNT(*) FROM members WHERE status = 'active'")
            total_members = c.fetchone()[0]
            col1.metric("👥 মোট সদস্য", total_members)
            
            # আজকের জমা
            today = datetime.now().strftime("%Y-%m-%d")
            c.execute("SELECT SUM(amount) FROM transactions WHERE date = ?", (today,))
            today_deposit = c.fetchone()[0] or 0
            col2.metric("📅 আজকের জমা", f"{today_deposit:,.0f} টাকা")
            
            # এই মাসের জমা
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
                ORDER BY t.id DESC LIMIT 10
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
    
    # নতুন সদস্য
    elif menu == "➕ নতুন সদস্য":
        st.markdown("### ➕ নতুন সদস্য নিবন্ধন")
        
        name = st.text_input("নাম *", key="new_name")
        phone = st.text_input("মোবাইল নম্বর *", placeholder="017XXXXXXXX", key="new_phone")
        telegram_id = st.text_input("টেলিগ্রাম চ্যাট আইডি *", key="new_telegram")
        monthly = st.number_input("মাসিক কিস্তি (টাকা)", value=500, step=50, key="new_monthly")
        
        if st.button("✅ সদস্য যোগ করুন", type="primary", key="new_btn"):
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
                    
                    # স্বাগতম SMS
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
    
    # সদস্য ব্যবস্থাপনা
    elif menu == "✏️ সদস্য ব্যবস্থাপনা":
        st.markdown("### ✏️ সদস্য ব্যবস্থাপনা")
        
        try:
            conn = sqlite3.connect('somiti.db')
            c = conn.cursor()
            c.execute("SELECT id, name, phone, status, monthly_savings, telegram_id FROM members ORDER BY name")
            members = c.fetchall()
            conn.close()
            
            if members:
                options = {f"{m[1]} ({m[2]})": m for m in members}
                selected = st.selectbox("সদস্য নির্বাচন করুন", list(options.keys()), key="edit_select")
                
                if selected:
                    m = options[selected]
                    member_id, name, phone, status, monthly, telegram = m
                    monthly = float(monthly) if monthly else 500.0
                    telegram = telegram or ""
                    
                    tab1, tab2, tab3 = st.tabs(["📝 তথ্য এডিট", "🔐 পাসওয়ার্ড রিসেট", "🗑️ ডিলিট"])
                    
                    with tab1:
                        new_name = st.text_input("নাম", value=name, key="edit_name")
                        new_telegram = st.text_input("টেলিগ্রাম আইডি", value=telegram, key="edit_telegram")
                        new_monthly = st.number_input("মাসিক কিস্তি", value=monthly, step=50.0, key="edit_monthly")
                        new_status = st.selectbox("স্ট্যাটাস", ['active', 'inactive'], 
                                                 index=0 if status == 'active' else 1, key="edit_status")
                        
                        if st.button("💾 আপডেট", key="edit_btn"):
                            conn = sqlite3.connect('somiti.db')
                            c = conn.cursor()
                            c.execute("""
                                UPDATE members 
                                SET name=?, telegram_id=?, monthly_savings=?, status=? 
                                WHERE id=?
                            """, (new_name, new_telegram, new_monthly, new_status, member_id))
                            conn.commit()
                            conn.close()
                            st.success("✅ আপডেট হয়েছে!")
                            st.rerun()
                    
                    with tab2:
                        st.markdown("#### পাসওয়ার্ড রিসেট")
                        if st.button("🔄 নতুন পাসওয়ার্ড জেনারেট", key="reset_btn"):
                            new_pass = generate_password()
                            conn = sqlite3.connect('somiti.db')
                            c = conn.cursor()
                            c.execute("UPDATE members SET password=? WHERE id=?", (new_pass, member_id))
                            conn.commit()
                            conn.close()
                            
                            if telegram:
                                send_telegram_message(telegram, f"🔐 আপনার নতুন পাসওয়ার্ড: {new_pass}")
                            
                            st.success(f"✅ নতুন পাসওয়ার্ড: {new_pass}")
                    
                    with tab3:
                        st.warning("⚠️ ডিলিট করলে সব তথ্য মুছে যাবে!")
                        if st.button("🗑️ সদস্য ডিলিট", key="delete_btn", type="primary"):
                            conn = sqlite3.connect('somiti.db')
                            c = conn.cursor()
                            c.execute("DELETE FROM transactions WHERE member_id=?", (member_id,))
                            c.execute("DELETE FROM members WHERE id=?", (member_id,))
                            conn.commit()
                            conn.close()
                            st.success("✅ সদস্য ডিলিট হয়েছে!")
                            st.rerun()
            else:
                st.info("কোনো সদস্য নেই")
                
        except Exception as e:
            st.error(f"এরর: {e}")
    
    # টাকা জমা
    elif menu == "💵 টাকা জমা":
        st.markdown("### 💵 সদস্যের টাকা জমা")
        
        try:
            conn = sqlite3.connect('somiti.db')
            c = conn.cursor()
            c.execute("SELECT id, name, phone, telegram_id FROM members WHERE status='active' ORDER BY name")
            members = c.fetchall()
            conn.close()
            
            if members:
                options = {f"{m[1]} ({m[2]})": m for m in members}
                selected = st.selectbox("সদস্য নির্বাচন করুন", list(options.keys()), key="dep_select")
                amount = st.number_input("টাকার পরিমাণ", value=0.0, step=100.0, key="dep_amount")
                month = st.selectbox("কিস্তির মাস", [datetime.now().strftime("%Y-%m")], key="dep_month")
                
                if st.button("✅ টাকা জমা করুন", type="primary", key="dep_btn"):
                    if amount > 0:
                        m = options[selected]
                        member_id, name, phone, telegram_id = m
                        today = datetime.now().strftime("%Y-%m-%d")
                        
                        conn = sqlite3.connect('somiti.db')
                        c = conn.cursor()
                        
                        c.execute("""
                            INSERT INTO transactions (member_id, amount, transaction_type, month, date)
                            VALUES (?, ?, ?, ?, ?)
                        """, (member_id, amount, 'deposit', month, today))
                        
                        c.execute("UPDATE members SET total_savings = total_savings + ? WHERE id = ?", 
                                 (amount, member_id))
                        
                        c.execute("SELECT total_savings FROM members WHERE id = ?", (member_id,))
                        total = c.fetchone()[0]
                        
                        conn.commit()
                        conn.close()
                        
                        if telegram_id:
                            msg = f"""✅ পেমেন্ট সফল - {SOMITI_NAME}

প্রিয় {name},
আপনার জমা হয়েছে: {amount:,.0f} টাকা
তারিখ: {today}
মাস: {month}

💰 বর্তমান মোট জমা: {total:,.0f} টাকা

ধন্যবাদ! 🙏"""
                            send_telegram_message(telegram_id, msg)
                        
                        st.success(f"✅ {amount:,.0f} টাকা জমা হয়েছে")
                        st.balloons()
                    else:
                        st.error("❌ টাকা ০ এর বেশি হতে হবে")
            else:
                st.warning("⚠️ কোনো সক্রিয় সদস্য নেই")
                
        except Exception as e:
            st.error(f"এরর: {e}")
    
    # রিপোর্ট
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
                    placeholders = ','.join(['?' for _ in paid])
                    c.execute(f"""
                        SELECT name, phone, monthly_savings, telegram_id
                        FROM members 
                        WHERE status = 'active' AND id NOT IN ({placeholders})
                    """, paid)
                else:
                    c.execute("SELECT name, phone, monthly_savings, telegram_id FROM members WHERE status = 'active'")
                
                defaulters = c.fetchall()
                conn.close()
                
                if defaulters:
                    df = pd.DataFrame(defaulters, columns=["নাম", "মোবাইল", "মাসিক কিস্তি", "টেলিগ্রাম আইডি"])
                    st.dataframe(df, use_container_width=True, hide_index=True)
                    st.warning(f"⚠️ {len(defaulters)} জন বকেয়াদার")
                    
                    if st.button("📢 বকেয়া রিমাইন্ডার পাঠান", type="primary"):
                        sent = 0
                        for name, phone, monthly, telegram_id in defaulters:
                            if telegram_id:
                                msg = f"""⚠️ জরুরি বকেয়া রিমাইন্ডার - {SOMITI_NAME}

প্রিয় {name},
আপনার মাসিক কিস্তি {monthly:,.0f} টাকা এখনো জমা পড়েনি।
দয়া করে আজই পরিশোধ করুন। 🙏"""
                                if send_telegram_message(telegram_id, msg):
                                    sent += 1
                        st.success(f"✅ {sent} জনকে রিমাইন্ডার পাঠানো হয়েছে!")
                else:
                    st.success("🎉 সবাই কিস্তি পরিশোধ করেছেন!")
                    
            except Exception as e:
                st.error(f"এরর: {e}")

# ============================================
# মেম্বার ড্যাশবোর্ড
# ============================================
def member_panel():
    show_header()
    
    try:
        conn = sqlite3.connect('somiti.db')
        c = conn.cursor()
        c.execute("""
            SELECT name, phone, total_savings, monthly_savings 
            FROM members 
            WHERE id = ?
        """, (st.session_state.member_id,))
        member = c.fetchone()
        
        if not member:
            st.error("সদস্য পাওয়া যায়নি")
            st.session_state.logged_in = False
            st.rerun()
            return
        
        name, phone, savings, monthly = member
        monthly = monthly or 500
        
        with st.sidebar:
            st.markdown(f"### 👤 {name}")
            st.caption(f"📱 {phone}")
            st.metric("💰 মোট জমা", f"{savings:,.0f} টাকা")
            
            menu = st.radio("মেনু", ["📊 ড্যাশবোর্ড", "🔑 পাসওয়ার্ড পরিবর্তন", "🚪 লগআউট"], label_visibility="collapsed")
        
        if menu == "🚪 লগআউট":
            for key in ['logged_in', 'user_type', 'member_id']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()
        
        elif menu == "📊 ড্যাশবোর্ড":
            st.markdown(f"### স্বাগতম, {name}! 👋")
            
            col1, col2 = st.columns(2)
            col1.metric("💰 বর্তমান জমা", f"{savings:,.0f} টাকা")
            col2.metric("📅 মাসিক কিস্তি", f"{monthly:,.0f} টাকা")
            
            current_month = datetime.now().strftime("%Y-%m")
            c.execute("""
                SELECT SUM(amount) FROM transactions 
                WHERE member_id = ? AND month = ?
            """, (st.session_state.member_id, current_month))
            paid = c.fetchone()[0] or 0
            
            if paid >= monthly:
                st.success(f"✅ {current_month} মাসের কিস্তি পরিশোধ করেছেন")
            else:
                st.warning(f"⚠️ বকেয়া: {monthly - paid:,.0f} টাকা")
            
            st.markdown("---")
            st.markdown("#### 📋 লেনদেন ইতিহাস")
            
            c.execute("""
                SELECT date, amount, month FROM transactions 
                WHERE member_id = ? ORDER BY id DESC LIMIT 10
            """, (st.session_state.member_id,))
            transactions = c.fetchall()
            
            if transactions:
                df = pd.DataFrame(transactions, columns=["তারিখ", "টাকা", "মাস"])
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.info("এখনো কোনো লেনদেন হয়নি")
        
        elif menu == "🔑 পাসওয়ার্ড পরিবর্তন":
            st.markdown("### 🔑 পাসওয়ার্ড পরিবর্তন")
            
            curr = st.text_input("বর্তমান পাসওয়ার্ড", type="password", key="mem_curr")
            new = st.text_input("নতুন পাসওয়ার্ড", type="password", key="mem_new")
            conf = st.text_input("নিশ্চিত করুন", type="password", key="mem_conf")
            
            if st.button("🔄 পরিবর্তন করুন", type="primary", key="mem_btn"):
                c.execute("SELECT password FROM members WHERE id = ?", (st.session_state.member_id,))
                stored = c.fetchone()[0]
                
                if curr != stored:
                    st.error("❌ বর্তমান পাসওয়ার্ড ভুল")
                elif new != conf:
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
        st.error(f"এরর: {e}")

# ============================================
# মেইন ফাংশন
# ============================================
def main():
    # ডাটাবেজ ইনিশিয়ালাইজ
    init_database()
    
    # সেশন ইনিশিয়ালাইজ
    init_session()
    
    # লগইন চেক
    if not st.session_state.logged_in:
        login_page()
    else:
        if st.session_state.user_type == 'admin':
            admin_panel()
        elif st.session_state.user_type == 'member':
            member_panel()
        else:
            login_page()

# ============================================
# রান
# ============================================
if __name__ == "__main__":
    main()
