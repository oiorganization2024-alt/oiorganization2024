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
            note TEXT,
            late_fee REAL DEFAULT 0
        )
    ''')
    
    # খরচ টেবিল
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
# টেলিগ্রাম মেসেজ ফাংশন
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
    """চ্যানেলে মেসেজ পাঠায়"""
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
# হেডার UI
# ============================================
def show_header():
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
    .stats-box {{
        background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
        padding: 15px;
        border-radius: 10px;
        text-align: center;
        margin-bottom: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }}
    .stats-box h2 {{
        color: white;
        font-size: 24px;
        font-weight: bold;
        margin: 0;
    }}
    .stats-box p {{
        color: #E0FFE0;
        font-size: 12px;
        margin: 5px 0 0 0;
    }}
    .cash-box {{
        background: linear-gradient(135deg, #FF9800 0%, #FFC107 100%);
        padding: 15px;
        border-radius: 10px;
        text-align: center;
        margin-bottom: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }}
    .cash-box h2 {{
        color: white;
        font-size: 24px;
        font-weight: bold;
        margin: 0;
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
    .lottery-box {{
        background: linear-gradient(135deg, #9C27B0 0%, #E91E63 100%);
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        margin: 20px 0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }}
    .lottery-box h3 {{
        color: gold;
        font-size: 28px;
        margin: 0;
    }}
    .lottery-box p {{
        color: white;
        font-size: 16px;
        margin: 10px 0;
    }}
    </style>
    """, unsafe_allow_html=True)

def show_admin_header():
    total = get_total_savings()
    cash = get_cash_balance()
    
    st.markdown(f"""
    <div class="main-header">
        <h1>🌾 {SOMITI_NAME} 🌾</h1>
        <p>সঞ্চয় ও ঋণ ব্যবস্থাপনা সিস্টেম</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
        <div class="stats-box">
            <h2>💰 {total:,.0f} টাকা</h2>
            <p>সমিতির মোট জমা</p>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="cash-box">
            <h2>💵 {cash:,.0f} টাকা</h2>
            <p>ক্যাশ ব্যালেন্স (জমা - খরচ)</p>
        </div>
        """, unsafe_allow_html=True)

def show_member_header():
    st.markdown(f"""
    <div class="main-header">
        <h1>🌾 {SOMITI_NAME} 🌾</h1>
        <p>সঞ্চয় ও ঋণ ব্যবস্থাপনা সিস্টেম</p>
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
    show_member_header()
    
    with st.container():
        st.markdown('<div class="login-box">', unsafe_allow_html=True)
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
# এডমিন ড্যাশবোর্ড
# ============================================
def admin_panel():
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
        
        # KPI কার্ডস
        col1, col2, col3, col4 = st.columns(4)
        
        try:
            conn = sqlite3.connect('somiti.db')
            c = conn.cursor()
            
            # মোট সদস্য
            c.execute("SELECT COUNT(*) FROM members WHERE status = 'active'")
            total_members = c.fetchone()[0]
            col1.metric("👥 মোট সদস্য", total_members)
            
            # মোট জমা
            total_savings = get_total_savings()
            col2.metric("💰 মোট জমা", f"{total_savings:,.0f} টাকা")
            
            # এই মাসের জমা
            month_collection = get_current_month_collection()
            col3.metric("📅 এই মাসের জমা", f"{month_collection:,.0f} টাকা")
            
            # বকেয়াদার সংখ্যা
            defaulters = get_current_month_defaulters_count()
            col4.metric("⚠️ বকেয়াদার", f"{defaulters} জন")
            
            conn.close()
        except:
            pass
        
        st.markdown("---")
        
        # প্রগ্রেস বার
        st.subheader("📊 মাসিক কালেকশন প্রগ্রেস")
        target = get_current_month_target()
        collected = get_current_month_collection()
        
        if target > 0:
            progress = collected / target
            st.progress(min(progress, 1.0))
            st.write(f"লক্ষ্য: {target:,.0f} টাকা | আদায়: {collected:,.0f} টাকা ({progress*100:.1f}%)")
        else:
            st.info("এখনো কোনো টার্গেট সেট করা হয়নি")
        
        st.markdown("---")
        
        # সাম্প্রতিক লেনদেন
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
        except:
            pass
    
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
        
        # সার্চ অপশন
        search_term = st.text_input("🔍 নাম বা আইডি দিয়ে খুঁজুন", key="search_member")
        
        try:
            conn = sqlite3.connect('somiti.db')
            c = conn.cursor()
            
            if search_term:
                c.execute("""
                    SELECT id, name, phone, status, monthly_savings, telegram_id 
                    FROM members 
                    WHERE id LIKE ? OR name LIKE ? OR phone LIKE ?
                    ORDER BY name
                """, (f"%{search_term}%", f"%{search_term}%", f"%{search_term}%"))
            else:
                c.execute("SELECT id, name, phone, status, monthly_savings, telegram_id FROM members ORDER BY name LIMIT 50")
            
            members = c.fetchall()
            conn.close()
            
            if members:
                options = {f"{m[1]} ({m[2]}) [{m[0]}]": m for m in members}
                selected = st.selectbox("সদস্য নির্বাচন করুন", list(options.keys()), key="edit_select")
                
                if selected:
                    m = options[selected]
                    member_id, name, phone, status, monthly, telegram = m
                    monthly = float(monthly) if monthly else 500.0
                    telegram = telegram or ""
                    
                    tab1, tab2, tab3, tab4 = st.tabs(["📝 তথ্য এডিট", "🔐 পাসওয়ার্ড রিসেট", "🔄 স্ট্যাটাস", "🗑️ ডিলিট"])
                    
                    with tab1:
                        new_name = st.text_input("নাম", value=name, key="edit_name")
                        new_telegram = st.text_input("টেলিগ্রাম আইডি", value=telegram, key="edit_telegram")
                        new_monthly = st.number_input("মাসিক কিস্তি", value=monthly, step=50.0, key="edit_monthly")
                        
                        if st.button("💾 আপডেট", key="edit_btn"):
                            conn = sqlite3.connect('somiti.db')
                            c = conn.cursor()
                            c.execute("""
                                UPDATE members 
                                SET name=?, telegram_id=?, monthly_savings=? 
                                WHERE id=?
                            """, (new_name, new_telegram, new_monthly, member_id))
                            conn.commit()
                            conn.close()
                            st.success("✅ তথ্য আপডেট হয়েছে!")
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
                        st.markdown("#### স্ট্যাটাস পরিবর্তন")
                        current_status = "Active (সক্রিয়)" if status == 'active' else "Inactive (নিষ্ক্রিয়)"
                        st.info(f"বর্তমান স্ট্যাটাস: {current_status}")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("✅ সক্রিয় করুন", key="activate_btn"):
                                conn = sqlite3.connect('somiti.db')
                                c = conn.cursor()
                                c.execute("UPDATE members SET status='active' WHERE id=?", (member_id,))
                                conn.commit()
                                conn.close()
                                st.success("✅ সদস্য সক্রিয় করা হয়েছে!")
                                st.rerun()
                        with col2:
                            if st.button("❌ নিষ্ক্রিয় করুন", key="deactivate_btn"):
                                conn = sqlite3.connect('somiti.db')
                                c = conn.cursor()
                                c.execute("UPDATE members SET status='inactive' WHERE id=?", (member_id,))
                                conn.commit()
                                conn.close()
                                st.warning("⚠️ সদস্য নিষ্ক্রিয় করা হয়েছে!")
                                st.rerun()
                    
                    with tab4:
                        st.warning("⚠️ ডিলিট করলে সব তথ্য স্থায়ীভাবে মুছে যাবে!")
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
                st.info("কোনো সদস্য পাওয়া যায়নি")
                
        except Exception as e:
            st.error(f"এরর: {e}")
    
    elif menu == "💵 টাকা জমা":
        st.markdown("### 💵 সদস্যের টাকা জমা")
        
        # সার্চ বক্স
        search_term = st.text_input("🔍 নাম বা আইডি দিয়ে সদস্য খুঁজুন", key="dep_search")
        
        if search_term:
            search_results = search_members(search_term)
            if search_results:
                options = {f"{m[1]} ({m[2]}) [{m[0]}]": m for m in search_results}
                selected = st.selectbox("সদস্য নির্বাচন করুন", list(options.keys()), key="dep_select")
                
                if selected:
                    m = options[selected]
                    member_id, name, phone = m
                    
                    # মাসিক কিস্তি আনা
                    conn = sqlite3.connect('somiti.db')
                    c = conn.cursor()
                    c.execute("SELECT monthly_savings, telegram_id FROM members WHERE id=?", (member_id,))
                    result = c.fetchone()
                    conn.close()
                    
                    monthly = result[0] if result else 500
                    telegram_id = result[1] if result else None
                    
                    st.info(f"নির্বাচিত সদস্য: {name} | মাসিক কিস্তি: {monthly:,.0f} টাকা")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        months_to_pay = st.number_input("কত মাসের কিস্তি", value=1, min_value=1, max_value=12, step=1, key="dep_months")
                    with col2:
                        base_amount = monthly * months_to_pay
                        late_fee = st.number_input("লেট ফি/জরিমানা (ঐচ্ছিক)", value=0.0, step=10.0, key="dep_late_fee")
                    
                    total_amount = base_amount + late_fee
                    st.write(f"**মোট জমা হবে: {total_amount:,.0f} টাকা** (কিস্তি: {base_amount:,.0f} + লেট ফি: {late_fee:,.0f})")
                    
                    month = st.selectbox("কিস্তির মাস (প্রথম মাস)", 
                                        [datetime.now().strftime("%Y-%m")] + 
                                        [(datetime.now() - timedelta(days=30*i)).strftime("%Y-%m") for i in range(1,6)],
                                        key="dep_month")
                    
                    note = st.text_input("নোট (ঐচ্ছিক)", key="dep_note")
                    
                    if st.button("✅ টাকা জমা করুন", type="primary", key="dep_btn"):
                        if total_amount > 0:
                            today = datetime.now().strftime("%Y-%m-%d")
                            
                            conn = sqlite3.connect('somiti.db')
                            c = conn.cursor()
                            
                            # একাধিক মাসের জন্য এন্ট্রি
                            for i in range(months_to_pay):
                                month_date = (datetime.strptime(month, "%Y-%m") + timedelta(days=30*i)).strftime("%Y-%m")
                                c.execute("""
                                    INSERT INTO transactions (member_id, amount, transaction_type, month, date, note, late_fee)
                                    VALUES (?, ?, ?, ?, ?, ?, ?)
                                """, (member_id, monthly, 'deposit', month_date, today, note, late_fee if i == 0 else 0))
                            
                            # মোট জমা আপডেট
                            c.execute("UPDATE members SET total_savings = total_savings + ? WHERE id = ?", 
                                     (total_amount, member_id))
                            
                            c.execute("SELECT total_savings FROM members WHERE id = ?", (member_id,))
                            total = c.fetchone()[0]
                            
                            conn.commit()
                            conn.close()
                            
                            # টেলিগ্রামে রসিদ
                            if telegram_id:
                                receipt_msg = f"""✅ পেমেন্ট সফল - {SOMITI_NAME}

প্রিয় {name},
আপনার জমা হয়েছে: {total_amount:,.0f} টাকা
তারিখ: {today}
বিবরণ: {months_to_pay} মাসের কিস্তি"""
                                if late_fee > 0:
                                    receipt_msg += f"\nলেট ফি: {late_fee:,.0f} টাকা"
                                receipt_msg += f"\n\n💰 মোট জমা: {total:,.0f} টাকা\nধন্যবাদ! 🙏"
                                
                                send_telegram_message(telegram_id, receipt_msg)
                            
                            # চ্যানেলে রসিদ
                            channel_msg = f"""📢 {SOMITI_NAME}

✅ {name} [{member_id}]
জমা দিয়েছেন: {total_amount:,.0f} টাকা
মোট জমা: {total:,.0f} টাকা"""
                            send_telegram_channel_message(channel_msg)
                            
                            st.success(f"✅ {total_amount:,.0f} টাকা জমা হয়েছে!")
                            st.balloons()
            else:
                st.warning("কোনো সদস্য পাওয়া যায়নি")
        else:
            st.info("নাম বা আইডি দিয়ে সদস্য খুঁজুন")
    
    elif menu == "💸 খরচ ব্যবস্থাপনা":
        st.markdown("### 💸 খরচ ব্যবস্থাপনা")
        
        tab1, tab2 = st.tabs(["➕ নতুন খরচ যোগ", "📋 খরচের তালিকা"])
        
        with tab1:
            description = st.text_input("বিবরণ", key="exp_desc")
            amount = st.number_input("টাকার পরিমাণ", value=0.0, step=10.0, key="exp_amount")
            category = st.selectbox("ক্যাটাগরি", ["অফিস ভাড়া", "চা-নাস্তা", "স্টেশনারি", "পরিবহন", "অন্যান্য"], key="exp_cat")
            
            if st.button("💾 খরচ সংরক্ষণ", type="primary", key="exp_btn"):
                if description and amount > 0:
                    today = datetime.now().strftime("%Y-%m-%d")
                    conn = sqlite3.connect('somiti.db')
                    c = conn.cursor()
                    c.execute("""
                        INSERT INTO expenses (description, amount, date, category)
                        VALUES (?, ?, ?, ?)
                    """, (description, amount, today, category))
                    conn.commit()
                    conn.close()
                    
                    st.success(f"✅ {amount:,.0f} টাকা খরচ যোগ হয়েছে!")
                    st.rerun()
                else:
                    st.error("❌ বিবরণ ও টাকার পরিমাণ দিতে হবে")
        
        with tab2:
            try:
                conn = sqlite3.connect('somiti.db')
                c = conn.cursor()
                c.execute("""
                    SELECT date, description, amount, category
                    FROM expenses
                    ORDER BY id DESC
                    LIMIT 50
                """)
                expenses = c.fetchall()
                conn.close()
                
                if expenses:
                    df = pd.DataFrame(expenses, columns=["তারিখ", "বিবরণ", "টাকা", "ক্যাটাগরি"])
                    st.dataframe(df, use_container_width=True, hide_index=True)
                    
                    # টোটাল খরচ
                    total_exp = sum(e[2] for e in expenses)
                    st.metric("📊 এই তালিকায় মোট খরচ", f"{total_exp:,.0f} টাকা")
                else:
                    st.info("এখনো কোনো খরচ যোগ করা হয়নি")
            except Exception as e:
                st.error(f"এরর: {e}")
        
        # ক্যাশ স্ট্যাটাস
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("💰 মোট জমা", f"{get_total_savings():,.0f} টাকা")
        with col2:
            st.metric("💸 মোট খরচ", f"{get_total_expenses():,.0f} টাকা")
        with col3:
            st.metric("💵 ক্যাশ ব্যালেন্স", f"{get_cash_balance():,.0f} টাকা")
    
    elif menu == "📊 রিপোর্ট":
        st.markdown("### 📊 রিপোর্ট")
        
        tab1, tab2, tab3 = st.tabs(["📈 মাসিক রিপোর্ট", "⚠️ বকেয়া তালিকা", "📥 স্টেটমেন্ট ডাউনলোড"])
        
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
                        SELECT name, phone, monthly_savings, telegram_id, id
                        FROM members 
                        WHERE status = 'active' AND id NOT IN ({placeholders})
                    """, paid)
                else:
                    c.execute("SELECT name, phone, monthly_savings, telegram_id, id FROM members WHERE status = 'active'")
                
                defaulters = c.fetchall()
                conn.close()
                
                if defaulters:
                    df = pd.DataFrame(defaulters, columns=["নাম", "মোবাইল", "মাসিক কিস্তি", "টেলিগ্রাম", "আইডি"])
                    st.dataframe(df, use_container_width=True, hide_index=True)
                    st.warning(f"⚠️ {len(defaulters)} জন বকেয়াদার")
                    
                    if st.button("📢 সবার কাছে বকেয়া রিমাইন্ডার পাঠান", type="primary"):
                        sent = 0
                        for name, phone, monthly, telegram_id, member_id in defaulters:
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
        
        with tab3:
            st.markdown("#### 📥 সদস্যের স্টেটমেন্ট ডাউনলোড")
            
            member_search = st.text_input("সদস্যের আইডি বা নাম লিখুন", key="stmt_search")
            
            if member_search:
                member = get_member_by_id_or_name(member_search)
                if member:
                    member_id, name, phone, total, monthly, status, telegram = member
                    
                    st.info(f"সদস্য: {name} [{member_id}] | মোবাইল: {phone}")
                    
                    conn = sqlite3.connect('somiti.db')
                    c = conn.cursor()
                    c.execute("""
                        SELECT date, amount, month, late_fee, note
                        FROM transactions
                        WHERE member_id = ?
                        ORDER BY date DESC
                    """, (member_id,))
                    transactions = c.fetchall()
                    conn.close()
                    
                    if transactions:
                        df = pd.DataFrame(transactions, columns=["তারিখ", "টাকা", "মাস", "লেট ফি", "নোট"])
                        st.dataframe(df, use_container_width=True, hide_index=True)
                        
                        # এক্সেল ডাউনলোড
                        output = BytesIO()
                        with pd.ExcelWriter(output, engine='openpyxl') as writer:
                            df.to_excel(writer, sheet_name='লেনদেন', index=False)
                        
                        st.download_button(
                            label="📥 এক্সেল ডাউনলোড করুন",
                            data=output.getvalue(),
                            file_name=f"{member_id}_{name}_statement.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                    else:
                        st.info("কোনো লেনদেন নেই")
                else:
                    st.warning("সদস্য পাওয়া যায়নি")
    
    elif menu == "🎲 লটারি":
        st.markdown("### 🎲 লটারি ড্র")
        
        st.markdown("""
        <div class="lottery-box">
            <h3>🎰 লাকি ড্র</h3>
            <p>সক্রিয় সকল সদস্যের মধ্য থেকে একজন বিজয়ী নির্বাচন করুন</p>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("🎲 বিজয়ী নির্বাচন করুন", type="primary", key="lottery_btn"):
            winner = pick_lottery_winner()
            
            if winner:
                member_id, name, phone, savings, telegram_id = winner
                
                st.balloons()
                st.success(f"🎉 বিজয়ী: {name} [{member_id}]")
                st.info(f"মোবাইল: {phone} | মোট জমা: {savings:,.0f} টাকা")
                
                # চ্যানেলে ঘোষণা
                announcement = f"""🎉 *লটারি বিজয়ী - {SOMITI_NAME}* 🎉

অভিনন্দন! {name} [{member_id}]
আপনি আজকের লাকি ড্র-তে বিজয়ী হয়েছেন!

🏆 শুভেচ্ছা ও অভিনন্দন! 🏆"""
                
                send_telegram_channel_message(announcement)
                
                if telegram_id:
                    winner_msg = f"""🎉 অভিনন্দন! {SOMITI_NAME}

প্রিয় {name},
আপনি আজকের লাকি ড্র-তে বিজয়ী হয়েছেন!

🏆 শুভেচ্ছা! 🏆"""
                    send_telegram_message(telegram_id, winner_msg)
                
                st.success("✅ বিজয়ীর নাম চ্যানেলে ঘোষণা করা হয়েছে!")
            else:
                st.error("❌ কোনো সক্রিয় সদস্য নেই")

# ============================================
# মেম্বার ড্যাশবোর্ড
# ============================================
def member_panel():
    show_member_header()
    
    try:
        conn = sqlite3.connect('somiti.db')
        c = conn.cursor()
        c.execute("""
            SELECT name, phone, total_savings, monthly_savings, id
            FROM members 
            WHERE id = ?
        """, (st.session_state.member_id,))
        member = c.fetchone()
        
        if not member:
            st.error("সদস্য পাওয়া যায়নি")
            st.session_state.logged_in = False
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
# টেলিগ্রাম মেসেজ ফাংশন
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
# UI স্টাইল (আগের সুন্দর ডিজাইন)
# ============================================
def apply_custom_css():
    st.markdown("""
    <style>
    /* মেইন ব্যাকগ্রাউন্ড */
    .stApp {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    }
    
    /* হেডার */
    .somiti-header {
        background: linear-gradient(135deg, #1a5276 0%, #2980b9 100%);
        padding: 25px;
        border-radius: 15px;
        margin-bottom: 25px;
        text-align: center;
        box-shadow: 0 10px 20px rgba(0,0,0,0.2);
        border: 1px solid rgba(255,255,255,0.1);
    }
    .somiti-header h1 {
        color: white;
        font-size: 38px;
        font-weight: 800;
        margin: 0;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        letter-spacing: 2px;
    }
    .somiti-header p {
        color: #d4e6f1;
        font-size: 16px;
        margin: 8px 0 0 0;
        font-weight: 400;
    }
    
    /* টোটাল টাকার বক্স */
    .total-box {
        background: linear-gradient(135deg, #27ae60 0%, #2ecc71 100%);
        padding: 20px;
        border-radius: 15px;
        text-align: center;
        margin-bottom: 25px;
        box-shadow: 0 10px 20px rgba(0,0,0,0.2);
        border: 1px solid rgba(255,255,255,0.2);
    }
    .total-box h2 {
        color: white;
        font-size: 32px;
        font-weight: 800;
        margin: 0;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
    }
    .total-box p {
        color: #d5f5e3;
        font-size: 14px;
        margin: 5px 0 0 0;
        font-weight: 500;
    }
    
    /* ক্যাশ বক্স */
    .cash-box {
        background: linear-gradient(135deg, #e67e22 0%, #f39c12 100%);
        padding: 20px;
        border-radius: 15px;
        text-align: center;
        margin-bottom: 25px;
        box-shadow: 0 10px 20px rgba(0,0,0,0.2);
        border: 1px solid rgba(255,255,255,0.2);
    }
    .cash-box h2 {
        color: white;
        font-size: 32px;
        font-weight: 800;
        margin: 0;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
    }
    .cash-box p {
        color: #fdebd0;
        font-size: 14px;
        margin: 5px 0 0 0;
        font-weight: 500;
    }
    
    /* KPI কার্ড */
    .kpi-card {
        background: white;
        padding: 20px;
        border-radius: 12px;
        text-align: center;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        margin-bottom: 10px;
        border: 1px solid #e8e8e8;
    }
    .kpi-card h3 {
        color: #2c3e50;
        font-size: 28px;
        font-weight: 700;
        margin: 5px 0;
    }
    .kpi-card p {
        color: #7f8c8d;
        font-size: 14px;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    /* লটারি বক্স */
    .lottery-box {
        background: linear-gradient(135deg, #8e44ad 0%, #9b59b6 100%);
        padding: 30px;
        border-radius: 20px;
        text-align: center;
        margin: 20px 0;
        box-shadow: 0 15px 30px rgba(0,0,0,0.3);
        border: 2px solid gold;
    }
    .lottery-box h3 {
        color: gold;
        font-size: 36px;
        font-weight: 800;
        margin: 0;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
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
        box-shadow: 0 20px 40px rgba(0,0,0,0.2);
        background: white;
        border: 1px solid #e0e0e0;
    }
    .login-card h3 {
        color: #1a5276;
        font-size: 28px;
        font-weight: 700;
        margin-bottom: 25px;
        text-align: center;
    }
    
    /* বাটন */
    .stButton > button {
        background: linear-gradient(135deg, #1a5276 0%, #2980b9 100%);
        color: white;
        font-weight: 600;
        border: none;
        border-radius: 10px;
        padding: 12px 24px;
        width: 100%;
        font-size: 16px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        background: linear-gradient(135deg, #2980b9 0%, #3498db 100%);
        box-shadow: 0 6px 12px rgba(0,0,0,0.15);
        transform: translateY(-2px);
    }
    
    /* প্রাইমারি বাটন */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #27ae60 0%, #2ecc71 100%);
    }
    .stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, #2ecc71 0%, #58d68d 100%);
    }
    
    /* সাইডবার */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
        border-right: 1px solid #0f3460;
    }
    section[data-testid="stSidebar"] * {
        color: white !important;
    }
    section[data-testid="stSidebar"] .stRadio > div {
        background: rgba(255,255,255,0.1);
        border-radius: 10px;
        padding: 10px;
    }
    
    /* মেট্রিক কার্ড */
    div[data-testid="metric-container"] {
        background: white;
        border-radius: 12px;
        padding: 15px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        border: 1px solid #e8e8e8;
    }
    
    /* টেবিল */
    .stDataFrame {
        border-radius: 10px;
        overflow: hidden;
        box-shadow: 0 4px 8px rgba(0,0,0,0.05);
    }
    
    /* ইনপুট ফিল্ড */
    .stTextInput > div > div > input,
    .stSelectbox > div > div,
    .stNumberInput > div > div > input {
        border-radius: 10px;
        border: 1px solid #d0d7de;
        padding: 10px;
    }
    
    /* ট্যাব */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
        background: transparent;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 10px 10px 0 0;
        padding: 12px 24px;
        background: #f0f2f6;
        font-weight: 500;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #1a5276 0%, #2980b9 100%);
        color: white;
    }
    
    /* সাকসেস মেসেজ */
    .stSuccess {
        background: #d4edda;
        border-left: 5px solid #27ae60;
        color: #155724;
        border-radius: 8px;
    }
    
    /* এরর মেসেজ */
    .stError {
        background: #f8d7da;
        border-left: 5px solid #e74c3c;
        color: #721c24;
        border-radius: 8px;
    }
    
    /* ওয়ার্নিং */
    .stWarning {
        background: #fff3cd;
        border-left: 5px solid #f39c12;
        color: #856404;
        border-radius: 8px;
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
    apply_custom_css()
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
# এডমিন ড্যাশবোর্ড
# ============================================
def admin_panel():
    apply_custom_css()
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
        
        # KPI কার্ডস
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
        except:
            pass
        
        st.markdown("---")
        
        # প্রগ্রেস বার
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
        
        # সাম্প্রতিক লেনদেন
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
        except:
            pass
    
    elif menu == "➕ নতুন সদস্য":
        st.markdown("### ➕ নতুন সদস্য নিবন্ধন")
        
        name = st.text_input("নাম *", key="new_name")
        phone = st.text_input("মোবাইল নম্বর *", placeholder="017XXXXXXXX", key="new_phone")
        telegram_id = st.text_input("টেলিগ্রাম চ্যাট আইডি *", key="new_telegram")
        monthly = st.number_input("মাসিক কিস্তি (টাকা)", value=500, step=50, key="new_monthly")
        
        if st.button("✅ সদস্য যোগ করুন", type="primary", key="new_btn"):
            if not name or not phone or not telegram_id:
  OM members WHERE id = ?", (st.session_state.member_id,))
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
