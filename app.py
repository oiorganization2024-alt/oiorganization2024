import streamlit as st
import sqlite3
import requests
import random
import string
import pandas as pd
from datetime import datetime, timedelta

# ============================================
# কনফিগারেশন
# ============================================
TELEGRAM_BOT_TOKEN = "8752100386:AAEa-vMD4yPCKE0LPTFx-198Llbf8qZFgE8"
ADMIN_CHAT_ID = "8548828754"
ADMIN_MOBILE = "01766222373"
ADMIN_PASSWORD = "oio112024"
SOMITI_NAME = "ঐক্য উদ্যোগ সংস্থা"

# ============================================
# হেডার স্টাইল
# ============================================
def show_header():
    try:
        conn = sqlite3.connect('somiti.db')
        c = conn.cursor()
        c.execute("SELECT SUM(total_savings) FROM members WHERE status = 'active'")
        total = c.fetchone()[0] or 0
        conn.close()
    except:
        total = 0
    
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
    .stButton > button {{
        background-color: #0066CC;
        color: white;
        font-weight: 600;
        border: none;
        border-radius: 8px;
        padding: 10px 20px;
    }}
    .stButton > button[kind="primary"] {{
        background-color: #28a745;
    }}
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
# ডাটাবেজ সেটআপ (সম্পূর্ণ নতুন করে)
# ============================================
def init_db():
    conn = sqlite3.connect('somiti.db')
    c = conn.cursor()
    
    # পুরনো টেবিল ড্রপ করে নতুন তৈরি (ডাটা মুছে যাবে)
    # যদি ডাটা রাখতে চান তাহলে এই লাইন কমেন্ট করে দিন
    c.execute("DROP TABLE IF EXISTS members")
    c.execute("DROP TABLE IF EXISTS transactions")
    
    # নতুন টেবিল
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
            note TEXT
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
        response = requests.post(url, json=payload)
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
# লগইন
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
                except:
                    st.error("❌ ডাটাবেজ এরর")
        
        st.markdown("---")
        st.caption(f"পাসওয়ার্ড ভুলে গেলে: {ADMIN_MOBILE}")
        st.markdown('</div>', unsafe_allow_html=True)

# ============================================
# এডমিন ড্যাশবোর্ড
# ============================================
def admin_dashboard():
    st.set_page_config(page_title=f"{SOMITI_NAME} - এডমিন", page_icon="💰", layout="wide")
    show_header()
    
    with st.sidebar:
        st.markdown("### 📋 এডমিন মেনু")
        st.caption(f"👑 {ADMIN_MOBILE}")
        
        menu = st.radio("নেভিগেশন", 
                       ["🏠 ড্যাশবোর্ড", "➕ নতুন সদস্য", "✏️ সদস্য ব্যবস্থাপনা", 
                        "💵 টাকা জমা", "📊 রিপোর্ট", "🚪 লগআউট"],
                       label_visibility="collapsed")
        
        try:
            conn = sqlite3.connect('somiti.db')
            c = conn.cursor()
            c.execute("SELECT SUM(total_savings) FROM members WHERE status = 'active'")
            total = c.fetchone()[0] or 0
            conn.close()
            st.metric("💰 মোট জমা", f"{total:,.0f} টাকা")
        except:
            pass
    
    if menu == "🚪 লগআউট":
        for key in ['logged_in', 'user_type', 'member_id']:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()
    
    elif menu == "🏠 ড্যাশবোর্ড":
        st.markdown("### 🏠 ড্যাশবোর্ড")
        col1, col2, col3 = st.columns(3)
        
        try:
            conn = sqlite3.connect('somiti.db')
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM members WHERE status = 'active'")
            col1.metric("👥 সদস্য", c.fetchone()[0])
            
            today = datetime.now().strftime("%Y-%m-%d")
            c.execute("SELECT SUM(amount) FROM transactions WHERE date = ?", (today,))
            col2.metric("📅 আজ", f"{c.fetchone()[0] or 0:,.0f} টাকা")
            
            current = datetime.now().strftime("%Y-%m")
            c.execute("SELECT SUM(amount) FROM transactions WHERE month = ?", (current,))
            col3.metric("📆 এই মাস", f"{c.fetchone()[0] or 0:,.0f} টাকা")
            conn.close()
        except:
            pass
    
    elif menu == "➕ নতুন সদস্য":
        st.markdown("### ➕ নতুন সদস্য")
        
        name = st.text_input("নাম")
        phone = st.text_input("মোবাইল")
        telegram_id = st.text_input("টেলিগ্রাম চ্যাট আইডি")
        monthly = st.number_input("মাসিক কিস্তি", value=500, step=50)
        
        if st.button("✅ সদস্য যোগ করুন", type="primary"):
            if name and phone and telegram_id:
                if phone == ADMIN_MOBILE:
                    st.error("❌ এডমিনের মোবাইল ব্যবহার করা যাবে না")
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
                        
                        msg = f"🎉 {SOMITI_NAME}-এ স্বাগতম {name}!\n\nপাসওয়ার্ড: {password}\nমাসিক কিস্তি: {monthly} টাকা"
                        send_telegram_message(telegram_id, msg)
                        
                        st.success(f"✅ সদস্য তৈরি! আইডি: {member_id} | পাস: {password}")
                        st.balloons()
                    except sqlite3.IntegrityError:
                        st.error("❌ এই মোবাইল ইতিমধ্যে নিবন্ধিত")
            else:
                st.error("❌ সব ফিল্ড পূরণ করুন")
    
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
                selected = st.selectbox("সদস্য নির্বাচন করুন", list(options.keys()))
                
                if selected:
                    m = options[selected]
                    member_id, name, phone, status, monthly, telegram = m
                    monthly = float(monthly) if monthly else 500.0
                    telegram = telegram or ""
                    
                    tab1, tab2, tab3 = st.tabs(["📝 এডিট", "🔐 পাসওয়ার্ড", "🗑️ ডিলিট"])
                    
                    with tab1:
                        new_name = st.text_input("নাম", value=name, key="e1")
                        new_tel = st.text_input("টেলিগ্রাম আইডি", value=telegram, key="e2")
                        new_mon = st.number_input("মাসিক কিস্তি", value=monthly, step=50.0, key="e3")
                        new_stat = st.selectbox("স্ট্যাটাস", ['active', 'inactive'], 
                                                index=0 if status == 'active' else 1, key="e4")
                        
                        if st.button("💾 আপডেট", key="btn1"):
                            conn = sqlite3.connect('somiti.db')
                            c = conn.cursor()
                            c.execute("UPDATE members SET name=?, telegram_id=?, monthly_savings=?, status=? WHERE id=?",
                                     (new_name, new_tel, new_mon, new_stat, member_id))
                            conn.commit()
                            conn.close()
                            st.success("✅ আপডেট হয়েছে!")
                            st.rerun()
                    
                    with tab2:
                        if st.button("🔄 নতুন পাসওয়ার্ড", key="btn2"):
                            new_pass = generate_password()
                            conn = sqlite3.connect('somiti.db')
                            c = conn.cursor()
                            c.execute("UPDATE members SET password=? WHERE id=?", (new_pass, member_id))
                            conn.commit()
                            conn.close()
                            if telegram:
                                send_telegram_message(telegram, f"🔐 নতুন পাসওয়ার্ড: {new_pass}")
                            st.success(f"✅ নতুন পাস: {new_pass}")
                    
                    with tab3:
                        st.warning("⚠️ ডিলিট করলে সব তথ্য মুছে যাবে!")
                        if st.button("🗑️ ডিলিট", key="btn3", type="primary"):
                            conn = sqlite3.connect('somiti.db')
                            c = conn.cursor()
                            c.execute("DELETE FROM transactions WHERE member_id=?", (member_id,))
                            c.execute("DELETE FROM members WHERE id=?", (member_id,))
                            conn.commit()
                            conn.close()
                            st.success("✅ ডিলিট হয়েছে!")
                            st.rerun()
            else:
                st.info("কোনো সদস্য নেই")
        except Exception as e:
            st.error(f"এরর: {e}")
    
    elif menu == "💵 টাকা জমা":
        st.markdown("### 💵 টাকা জমা")
        
        try:
            conn = sqlite3.connect('somiti.db')
            c = conn.cursor()
            c.execute("SELECT id, name, phone, telegram_id FROM members WHERE status='active' ORDER BY name")
            members = c.fetchall()
            conn.close()
            
            if members:
                opts = {f"{m[1]} ({m[2]})": m for m in members}
                sel = st.selectbox("সদস্য নির্বাচন", list(opts.keys()), key="dep1")
                amt = st.number_input("টাকার পরিমাণ", value=0.0, step=100.0, key="dep2")
                mon = st.selectbox("মাস", [datetime.now().strftime("%Y-%m")], key="dep3")
                
                if st.button("✅ জমা করুন", type="primary", key="dep4"):
                    if amt > 0:
                        m = opts[sel]
                        today = datetime.now().strftime("%Y-%m-%d")
                        
                        conn = sqlite3.connect('somiti.db')
                        c = conn.cursor()
                        c.execute("INSERT INTO transactions (member_id, amount, transaction_type, month, date) VALUES (?,?,?,?,?)",
                                 (m[0], amt, 'deposit', mon, today))
                        c.execute("UPDATE members SET total_savings = total_savings + ? WHERE id = ?", (amt, m[0]))
                        c.execute("SELECT total_savings FROM members WHERE id = ?", (m[0],))
                        total = c.fetchone()[0]
                        conn.commit()
                        conn.close()
                        
                        if m[3]:
                            msg = f"✅ পেমেন্ট সফল!\n\nপ্রিয় {m[1]},\nজমা: {amt:,.0f} টাকা\nমোট জমা: {total:,.0f} টাকা"
                            send_telegram_message(m[3], msg)
                        
                        st.success(f"✅ {amt:,.0f} টাকা জমা হয়েছে")
                        st.balloons()
                    else:
                        st.error("❌ টাকা ০ এর বেশি হতে হবে")
            else:
                st.warning("⚠️ কোনো সক্রিয় সদস্য নেই")
        except Exception as e:
            st.error(f"এরর: {e}")
    
    elif menu == "📊 রিপোর্ট":
        st.markdown("### 📊 রিপোর্ট")
        st.info("📱 SMS টেস্ট করতে চ্যাট আইডি দিন")
        
        test_id = st.text_input("চ্যাট আইডি", value=ADMIN_CHAT_ID)
        test_msg = st.text_area("মেসেজ", "টেস্ট মেসেজ")
        
        if st.button("📨 টেস্ট পাঠান"):
            if send_telegram_message(test_id, test_msg):
                st.success("✅ পাঠানো হয়েছে!")
            else:
                st.error("❌ পাঠানো যায়নি")

# ============================================
# সদস্য ড্যাশবোর্ড
# ============================================
def member_dashboard():
    st.set_page_config(page_title=f"{SOMITI_NAME} - সদস্য", page_icon="👤", layout="wide")
    show_header()
    
    try:
        conn = sqlite3.connect('somiti.db')
        c = conn.cursor()
        c.execute("SELECT name, phone, total_savings, monthly_savings FROM members WHERE id = ?", 
                 (st.session_state.member_id,))
        m = c.fetchone()
        
        if not m:
            st.error("সদস্য পাওয়া যায়নি")
            st.session_state.logged_in = False
            st.rerun()
            return
        
        name, phone, savings, monthly = m
        monthly = monthly or 500
        
        with st.sidebar:
            st.markdown(f"### 👤 {name}")
            st.caption(f"📱 {phone}")
            st.metric("💰 জমা", f"{savings:,.0f} টাকা")
            
            menu = st.radio("মেনু", ["📊 ড্যাশবোর্ড", "🔑 পাসওয়ার্ড", "🚪 লগআউট"], label_visibility="collapsed")
        
        if menu == "🚪 লগআউট":
            for key in ['logged_in', 'user_type', 'member_id']:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()
        
        elif menu == "📊 ড্যাশবোর্ড":
            st.markdown(f"### স্বাগতম, {name}!")
            
            col1, col2 = st.columns(2)
            col1.metric("💰 জমা", f"{savings:,.0f} টাকা")
            col2.metric("📅 কিস্তি", f"{monthly:,.0f} টাকা")
            
            current = datetime.now().strftime("%Y-%m")
            c.execute("SELECT SUM(amount) FROM transactions WHERE member_id = ? AND month = ?",
                     (st.session_state.member_id, current))
            paid = c.fetchone()[0] or 0
            
            if paid >= monthly:
                st.success(f"✅ {current} মাসের কিস্তি পরিশোধ করেছেন")
            else:
                st.warning(f"⚠️ বকেয়া: {monthly - paid:,.0f} টাকা")
        
        elif menu == "🔑 পাসওয়ার্ড":
            st.markdown("### 🔑 পাসওয়ার্ড পরিবর্তন")
            
            curr = st.text_input("বর্তমান", type="password")
            new = st.text_input("নতুন", type="password")
            conf = st.text_input("নিশ্চিত করুন", type="password")
            
            if st.button("🔄 পরিবর্তন", type="primary"):
                c.execute("SELECT password FROM members WHERE id = ?", (st.session_state.member_id,))
                stored = c.fetchone()[0]
                
                if curr != stored:
                    st.error("❌ বর্তমান পাসওয়ার্ড ভুল")
                elif new != conf:
                    st.error("❌ মিলছে না")
                elif len(new) < 4:
                    st.error("❌ কমপক্ষে ৪ অক্ষর")
                else:
                    c.execute("UPDATE members SET password = ? WHERE id = ?", 
                             (new, st.session_state.member_id))
                    conn.commit()
                    st.success("✅ পরিবর্তন হয়েছে")
        
        conn.close()
    except Exception as e:
        st.error(f"এরর: {e}")

# ============================================
# মেইন
# ============================================
def main():
    init_db()
    
    if not st.session_state.get('logged_in', False):
        login_screen()
    else:
        if st.session_state.user_type == 'admin':
            admin_dashboard()
        else:
            member_dashboard()

if __name__ == "__main__":
    main()
