import streamlit as st
import sqlite3
import smtplib
import random
import string
import pandas as pd
from datetime import datetime, timedelta
from io import BytesIO
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ============================================
# কনফিগারেশন
# ============================================
ADMIN_MOBILE = "01766222373"
ADMIN_PASSWORD = "oio112024"
SOMITI_NAME = "ঐক্য উদ্যোগ সংস্থা"

# ইমেইল কনফিগারেশন (আপনার দেওয়া)
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = "oiorganization2024@gmail.com"
SENDER_PASSWORD = "hnhm ocix kyxv ioiz"

# ============================================
# পেজ কনফিগ
# ============================================
st.set_page_config(page_title=SOMITI_NAME, page_icon="🌾", layout="wide")

# পাবলিক ভিউ
query_params = st.query_params
member_view_id = query_params.get("member")

# ============================================
# ডাটাবেজ
# ============================================
def init_database():
    conn = sqlite3.connect('somiti.db')
    c = conn.cursor()
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS members (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            phone TEXT UNIQUE NOT NULL,
            email TEXT,
            password TEXT NOT NULL,
            total_savings REAL DEFAULT 0,
            monthly_savings REAL DEFAULT 500,
            join_date TEXT,
            status TEXT DEFAULT 'active'
        )
    ''')
    
    try:
        c.execute("SELECT email FROM members LIMIT 1")
    except:
        c.execute("ALTER TABLE members ADD COLUMN email TEXT")
    
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
# ইমেইল ফাংশন
# ============================================
def send_email(to_email, subject, message):
    """সদস্যের ইমেইলে নোটিফিকেশন পাঠায়"""
    if not to_email:
        return False
    
    try:
        msg = MIMEMultipart()
        msg['From'] = f"{SOMITI_NAME} <{SENDER_EMAIL}>"
        msg['To'] = to_email
        msg['Subject'] = subject
        
        html = f"""
        <html>
        <head><meta charset="UTF-8"></head>
        <body style="font-family: Arial, sans-serif; background: #f5f5f5; padding: 20px;">
            <div style="max-width: 500px; margin: 0 auto; background: white; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 10px rgba(0,0,0,0.1);">
                <div style="background: #1a5276; color: white; padding: 25px; text-align: center;">
                    <h2 style="margin: 0;">🌾 {SOMITI_NAME}</h2>
                    <p style="margin: 5px 0 0; opacity: 0.9;">সঞ্চয় ও ঋণ ব্যবস্থাপনা</p>
                </div>
                <div style="padding: 30px;">
                    {message.replace(chr(10), '<br>')}
                </div>
                <div style="background: #f8f9fa; padding: 15px; text-align: center; font-size: 12px; color: #666; border-top: 1px solid #eee;">
                    <p style="margin: 0;">এই ইমেইলটি স্বয়ংক্রিয়ভাবে পাঠানো হয়েছে।</p>
                    <p style="margin: 5px 0 0;">প্রয়োজনে যোগাযোগ: {ADMIN_MOBILE}</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(html, 'html'))
        
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"ইমেইল এরর: {e}")
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

def generate_password():
    return ''.join(random.choices(string.digits, k=6))

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
        SELECT DISTINCT m.id, m.name, m.phone, m.monthly_savings, m.total_savings, m.email
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
            SELECT id, name, phone, monthly_savings, total_savings, email
            FROM members 
            WHERE status = 'active' AND id NOT IN ({placeholders})
            ORDER BY name
        """, paid_ids)
    else:
        c.execute("""
            SELECT id, name, phone, monthly_savings, total_savings, email
            FROM members 
            WHERE status = 'active'
            ORDER BY name
        """)
    
    unpaid = c.fetchall()
    conn.close()
    return unpaid

def get_member_transactions(member_id):
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
    except:
        return []

def get_all_members():
    conn = sqlite3.connect('somiti.db')
    c = conn.cursor()
    c.execute("""
        SELECT id, name, phone, email, password, status, monthly_savings, total_savings, join_date
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

def get_all_expenses():
    try:
        conn = sqlite3.connect('somiti.db')
        c = conn.cursor()
        c.execute("SELECT id, date, description, amount, category FROM expenses ORDER BY id DESC")
        expenses = c.fetchall()
        conn.close()
        return expenses
    except:
        return []

def get_monthly_report():
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
        return data
    except:
        return []

def pick_lottery_winner():
    conn = sqlite3.connect('somiti.db')
    c = conn.cursor()
    c.execute("""
        SELECT id, name, phone, total_savings, email 
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
# UI স্টাইল (ডার্ক থিম)
# ============================================
def apply_dark_theme():
    st.markdown("""
    <style>
    .stApp { background: linear-gradient(135deg, #0d1117 0%, #161b22 100%); }
    .somiti-header { background: linear-gradient(135deg, #1a5276 0%, #2980b9 100%); padding: 20px; border-radius: 15px; margin-bottom: 20px; text-align: center; }
    .somiti-header h1 { color: white; font-size: 32px; font-weight: 800; margin: 0; }
    .total-box { background: linear-gradient(135deg, #1e8449 0%, #27ae60 100%); padding: 15px; border-radius: 15px; text-align: center; margin-bottom: 20px; }
    .total-box h2 { color: white; font-size: 28px; font-weight: 800; margin: 0; }
    .cash-box { background: linear-gradient(135deg, #d35400 0%, #e67e22 100%); padding: 15px; border-radius: 15px; text-align: center; margin-bottom: 20px; }
    .cash-box h2 { color: white; font-size: 28px; font-weight: 800; margin: 0; }
    .member-card { background: #21262d; padding: 15px; border-radius: 10px; margin-bottom: 10px; border: 1px solid #30363d; }
    .stButton > button { background: linear-gradient(135deg, #238636 0%, #2ea043 100%); color: white; font-weight: 600; border: none; border-radius: 8px; padding: 8px 16px; width: 100%; }
    section[data-testid="stSidebar"] { background: linear-gradient(180deg, #0d1117 0%, #161b22 100%); border-right: 1px solid #30363d; }
    section[data-testid="stSidebar"] * { color: #c9d1d9 !important; }
    p, h1, h2, h3, h4, h5, h6, .stMarkdown { color: #c9d1d9 !important; }
    .stDataFrame { border-radius: 10px; overflow: hidden; border: 1px solid #30363d; }
    .stDataFrame th { background: #21262d !important; color: #c9d1d9 !important; }
    .stDataFrame td { background: #161b22 !important; color: #c9d1d9 !important; }
    </style>
    """, unsafe_allow_html=True)

def show_header():
    total = get_total_savings()
    st.markdown(f"""
    <div class="somiti-header"><h1>🌾 {SOMITI_NAME} 🌾</h1><p>সঞ্চয় ও ঋণ ব্যবস্থাপনা সিস্টেম</p></div>
    <div class="total-box"><h2>💰 {total:,.0f} টাকা</h2><p>সমিতির মোট জমা</p></div>
    """, unsafe_allow_html=True)

def show_admin_header():
    total = get_total_savings()
    cash = get_cash_balance()
    st.markdown(f'<div class="somiti-header"><h1>🌾 {SOMITI_NAME} 🌾</h1><p>সঞ্চয় ও ঋণ ব্যবস্থাপনা সিস্টেম</p></div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1: st.markdown(f'<div class="total-box"><h2>💰 {total:,.0f} টাকা</h2><p>সমিতির মোট জমা</p></div>', unsafe_allow_html=True)
    with col2: st.markdown(f'<div class="cash-box"><h2>💵 {cash:,.0f} টাকা</h2><p>ক্যাশ ব্যালেন্স</p></div>', unsafe_allow_html=True)

# ============================================
# পাবলিক ভিউ
# ============================================
def public_member_view(member_id):
    apply_dark_theme()
    member = get_member_by_id(member_id)
    if not member:
        st.error("❌ সদস্য পাওয়া যায়নি")
        return
    member_id, name, phone, email, password, total_savings, monthly_savings, join_date, status = member
    st.markdown(f'<div class="somiti-header"><h1>🌾 {SOMITI_NAME} 🌾</h1><p>সদস্য তথ্য</p></div>', unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    col1.metric("👤 নাম", name)
    col2.metric("🆔 আইডি", member_id)
    col3.metric("📱 মোবাইল", phone)
    col1, col2 = st.columns(2)
    col1.metric("💰 মোট জমা", f"{total_savings:,.0f} টাকা")
    col2.metric("📅 মাসিক কিস্তি", f"{monthly_savings:,.0f} টাকা")
    st.markdown("---"); st.markdown("### 📋 লেনদেন ইতিহাস")
    transactions = get_member_transactions(member_id)
    if transactions:
        data = [{"তারিখ": t[1], "টাকা": f"{t[2]:,.0f}", "মাস": t[3]} for t in transactions]
        st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)
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
                st.session_state.logged_in = True; st.session_state.user_type = 'admin'
                st.success("✅ এডমিন লগইন সফল!"); st.rerun()
            else:
                conn = sqlite3.connect('somiti.db'); c = conn.cursor()
                c.execute("SELECT id, password, status FROM members WHERE phone = ?", (phone,))
                result = c.fetchone(); conn.close()
                if result and result[2] != 'active': st.error("❌ অ্যাকাউন্ট নিষ্ক্রিয়")
                elif result and result[1] == password:
                    st.session_state.logged_in = True; st.session_state.user_type = 'member'
                    st.session_state.member_id = result[0]
                    st.success("✅ লগইন সফল!"); st.rerun()
                else: st.error("❌ ভুল মোবাইল বা পাসওয়ার্ড")
        st.markdown("---"); st.caption(f"সাহায্য: {ADMIN_MOBILE}")

# ============================================
# এডমিন প্যানেল
# ============================================
def admin_panel():
    apply_dark_theme()
    show_admin_header()
    
    with st.sidebar:
        st.markdown("### 📋 এডমিন মেনু")
        st.caption(f"👑 {ADMIN_MOBILE}")
        menu = st.radio("নির্বাচন করুন", 
            ["🏠 ড্যাশবোর্ড", "➕ নতুন সদস্য", "✏️ সদস্য ব্যবস্থাপনা", "💵 টাকা জমা", 
             "💰 লেনদেন ব্যবস্থাপনা", "🔗 সদস্য লিংক", "💸 খরচ ব্যবস্থাপনা", 
             "📊 রিপোর্ট", "📧 ইমেইল টেস্ট", "🎲 লটারি", "🚪 লগআউট"], label_visibility="collapsed")
    
    if menu == "🚪 লগআউট":
        for key in ['logged_in', 'user_type', 'member_id']:
            if key in st.session_state: del st.session_state[key]
        st.rerun()
    
    elif menu == "🏠 ড্যাশবোর্ড":
        st.markdown("### 🏠 এডমিন ড্যাশবোর্ড")
        col1, col2, col3, col4 = st.columns(4)
        try:
            conn = sqlite3.connect('somiti.db'); c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM members WHERE status = 'active'")
            col1.metric("👥 সদস্য", c.fetchone()[0])
            conn.close()
            col2.metric("💰 জমা", f"{get_total_savings():,.0f} টাকা")
            col3.metric("📅 এই মাস", f"{get_current_month_collection():,.0f} টাকা")
            col4.metric("⚠️ বকেয়া", f"{len(get_unpaid_members())} জন")
        except: pass
    
    elif menu == "➕ নতুন সদস্য":
        st.markdown("### ➕ নতুন সদস্য নিবন্ধন")
        name = st.text_input("নাম *")
        phone = st.text_input("মোবাইল নম্বর *", placeholder="017XXXXXXXX")
        email = st.text_input("ইমেইল অ্যাড্রেস (নোটিফিকেশনের জন্য)")
        monthly = st.number_input("মাসিক কিস্তি (টাকা)", value=500, step=50)
        
        if st.button("✅ সদস্য যোগ করুন", type="primary", use_container_width=True):
            if not name or not phone: st.error("❌ নাম ও মোবাইল আবশ্যক")
            elif phone == ADMIN_MOBILE: st.error("❌ এটি এডমিনের মোবাইল")
            else:
                try:
                    member_id = generate_member_id()
                    password = generate_password()
                    join_date = datetime.now().strftime("%Y-%m-%d")
                    conn = sqlite3.connect('somiti.db'); c = conn.cursor()
                    c.execute("INSERT INTO members (id, name, phone, email, password, monthly_savings, join_date) VALUES (?, ?, ?, ?, ?, ?, ?)",
                             (member_id, name, phone, email, password, monthly, join_date))
                    conn.commit(); conn.close()
                    
                    if email:
                        subject = f"🎉 স্বাগতম - {SOMITI_NAME}"
                        msg = f"""প্রিয় {name},

{SOMITI_NAME} এ আপনাকে স্বাগতম!

আপনার লগইন তথ্য:
🆔 আইডি: {member_id}
📱 মোবাইল: {phone}
🔑 পাসওয়ার্ড: {password}
💰 মাসিক কিস্তি: {monthly} টাকা

লগইন লিংক: {get_app_url()}

ধন্যবাদ! 🙏"""
                        send_email(email, subject, msg)
                    
                    st.success(f"✅ সদস্য তৈরি!")
                    st.info(f"আইডি: {member_id} | পাস: {password}")
                    st.balloons()
                except sqlite3.IntegrityError: st.error("❌ এই মোবাইল ইতিমধ্যে নিবন্ধিত")
    
    elif menu == "✏️ সদস্য ব্যবস্থাপনা":
        st.markdown("### ✏️ সদস্য ব্যবস্থাপনা")
        members = get_all_members()
        if members:
            for m in members:
                member_id, name, phone, email, password, status, monthly, savings, join_date = m
                monthly = float(monthly) if monthly else 500.0
                savings = float(savings) if savings else 0.0
                
                with st.expander(f"👤 {name} - {member_id} | {'✅ সক্রিয়' if status == 'active' else '❌ নিষ্ক্রিয়'}"):
                    st.write(f"📱 {phone} | 📧 {email or 'N/A'} | 💰 জমা: {savings:,.0f} টাকা | 📅 কিস্তি: {monthly:,.0f} টাকা")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        if st.button("📝 এডিট", key=f"e_{member_id}"): st.session_state[f"edit_{member_id}"] = True
                    with col2:
                        if st.button("🔐 পাসওয়ার্ড", key=f"p_{member_id}"): st.session_state[f"pass_{member_id}"] = True
                    with col3:
                        new_status = 'inactive' if status == 'active' else 'active'
                        if st.button(f"🔄 {'নিষ্ক্রিয়' if status == 'active' else 'সক্রিয়'}", key=f"s_{member_id}"):
                            conn = sqlite3.connect('somiti.db'); c = conn.cursor()
                            c.execute("UPDATE members SET status=? WHERE id=?", (new_status, member_id))
                            conn.commit(); conn.close(); st.rerun()
                    
                    if st.session_state.get(f"edit_{member_id}"):
                        with st.form(f"edit_form_{member_id}"):
                            new_name = st.text_input("নাম", value=name)
                            new_email = st.text_input("ইমেইল", value=email or "")
                            new_mon = st.number_input("কিস্তি", value=monthly, step=50.0)
                            if st.form_submit_button("💾 সেভ", type="primary"):
                                conn = sqlite3.connect('somiti.db'); c = conn.cursor()
                                c.execute("UPDATE members SET name=?, email=?, monthly_savings=? WHERE id=?", (new_name, new_email, new_mon, member_id))
                                conn.commit(); conn.close()
                                st.success("✅ আপডেট!"); del st.session_state[f"edit_{member_id}"]; st.rerun()
                    
                    if st.session_state.get(f"pass_{member_id}"):
                        if st.button("✅ নতুন পাসওয়ার্ড জেনারেট", key=f"gen_{member_id}", type="primary"):
                            new_pass = generate_password()
                            conn = sqlite3.connect('somiti.db'); c = conn.cursor()
                            c.execute("UPDATE members SET password=? WHERE id=?", (new_pass, member_id))
                            conn.commit(); conn.close()
                            if email:
                                send_email(email, f"🔐 পাসওয়ার্ড রিসেট - {SOMITI_NAME}", f"প্রিয় {name},\n\nআপনার নতুন পাসওয়ার্ড: {new_pass}\n\nলগইন করে পরিবর্তন করুন।")
                            st.success(f"✅ নতুন পাস: {new_pass}")
                            del st.session_state[f"pass_{member_id}"]; st.rerun()
        else: st.info("কোনো সদস্য নেই")
    
    elif menu == "💵 টাকা জমা":
        st.markdown("### 💵 সদস্যের টাকা জমা")
        paid, unpaid = get_paid_members(), get_unpaid_members()
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("#### ✅ জমা দিয়েছে")
            for m in paid: st.markdown(f'<div class="member-card"><strong>{m[1]}</strong> ({m[0]})<br><small>💰 {m[4]:,.0f} টাকা</small></div>', unsafe_allow_html=True)
            if not paid: st.info("কেউ জমা দেয়নি")
        with col2:
            st.markdown("#### ❌ জমা দেয়নি")
            for m in unpaid:
                with st.expander(f"❌ {m[1]} ({m[0]})"):
                    st.write(f"📱 {m[2]} | 💰 জমা: {m[4]:,.0f} টাকা | 📅 কিস্তি: {m[3]:,.0f} টাকা")
                    deposit_date = st.date_input("তারিখ", datetime.now(), key=f"d_{m[0]}")
                    months = [(datetime.now() - timedelta(days=30*i)).strftime("%Y-%m") for i in range(12)]
                    sel_month = st.selectbox("মাস", months, key=f"m_{m[0]}")
                    c1, c2 = st.columns(2)
                    with c1: months_count = st.number_input("কত মাস", 1, 1, 12, key=f"c_{m[0]}")
                    with c2: late_fee = st.number_input("লেট ফি", 0.0, step=10.0, key=f"f_{m[0]}")
                    total = m[3] * months_count + late_fee
                    if st.button("✅ জমা নিন", key=f"dep_{m[0]}", type="primary"):
                        today = deposit_date.strftime("%Y-%m-%d")
                        conn = sqlite3.connect('somiti.db'); c = conn.cursor()
                        for i in range(months_count):
                            m_date = (datetime.strptime(sel_month, "%Y-%m") + timedelta(days=30*i)).strftime("%Y-%m")
                            c.execute("INSERT INTO transactions (member_id, amount, transaction_type, month, date, late_fee) VALUES (?,?,?,?,?,?)",
                                     (m[0], m[3], 'deposit', m_date, today, late_fee if i==0 else 0))
                        c.execute("UPDATE members SET total_savings = total_savings + ? WHERE id=?", (total, m[0]))
                        c.execute("SELECT total_savings FROM members WHERE id=?", (m[0],))
                        new_total = c.fetchone()[0]
                        conn.commit(); conn.close()
                        if m[5]: send_email(m[5], f"✅ পেমেন্ট সফল - {SOMITI_NAME}", f"প্রিয় {m[1]},\n\nজমা: {total:,.0f} টাকা\nমোট জমা: {new_total:,.0f} টাকা\n\nধন্যবাদ! 🙏")
                        st.success(f"✅ {total:,.0f} টাকা জমা!"); st.rerun()
            if not unpaid: st.success("🎉 সবাই জমা দিয়েছেন!")
    
    elif menu == "💰 লেনদেন ব্যবস্থাপনা":
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
                    trans = get_member_transactions(member_id)
                    if trans:
                        for t in trans:
                            c1, c2, c3, c4 = st.columns([2, 1.5, 1, 1])
                            c1.write(t[1]); c2.write(f"{t[2]:,.0f} টাকা"); c3.write(t[3])
                            if c4.button("🗑️", key=f"del_{t[0]}"):
                                conn = sqlite3.connect('somiti.db'); c = conn.cursor()
                                c.execute("UPDATE members SET total_savings = total_savings - ? WHERE id=?", (t[2], member_id))
                                c.execute("DELETE FROM transactions WHERE id=?", (t[0],))
                                conn.commit(); conn.close(); st.rerun()
                    else: st.info("কোনো লেনদেন নেই")
    
    elif menu == "🔗 সদস্য লিংক":
        st.markdown("### 🔗 সদস্য লিংক ও পাসওয়ার্ড")
        members = get_all_members()
        app_url = get_app_url()
        for m in members:
            member_id, name, phone, email, password, status = m[:6]
            link = f"{app_url}/?member={member_id}"
            st.markdown(f"""
            <div class="member-card">
                <h4>👤 {name} ({member_id})</h4>
                <p>📱 {phone} | 📧 {email or 'N/A'}</p>
                <p>🔗 <code>{link}</code></p>
                <p>🔑 <code>{password}</code></p>
            </div>""", unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1: st.markdown(f'<button onclick="navigator.clipboard.writeText(\'{link}\')" style="background:#238636; color:white; border:none; padding:8px; border-radius:5px; width:100%;">📋 লিংক কপি</button>', unsafe_allow_html=True)
            with c2: st.markdown(f'<button onclick="navigator.clipboard.writeText(\'{password}\')" style="background:#238636; color:white; border:none; padding:8px; border-radius:5px; width:100%;">📋 পাসওয়ার্ড কপি</button>', unsafe_allow_html=True)
            st.markdown("---")
    
    elif menu == "💸 খরচ ব্যবস্থাপনা":
        st.markdown("### 💸 খরচ ব্যবস্থাপনা")
        tab1, tab2 = st.tabs(["➕ নতুন", "📋 তালিকা"])
        with tab1:
            with st.form("exp_form"):
                desc = st.text_input("বিবরণ")
                amt = st.number_input("টাকা", 0.0, step=10.0)
                cat = st.selectbox("ক্যাটাগরি", ["অফিস ভাড়া", "চা-নাস্তা", "স্টেশনারি", "পরিবহন", "অন্যান্য"])
                if st.form_submit_button("💾 সংরক্ষণ", type="primary"):
                    if desc and amt > 0:
                        conn = sqlite3.connect('somiti.db'); c = conn.cursor()
                        c.execute("INSERT INTO expenses (description, amount, date, category) VALUES (?,?,?,?)", (desc, amt, datetime.now().strftime("%Y-%m-%d"), cat))
                        conn.commit(); conn.close(); st.success(f"✅ {amt:,.0f} টাকা যোগ!"); st.rerun()
        with tab2:
            expenses = get_all_expenses()
            if expenses:
                for e in expenses[:20]:
                    c1, c2, c3, c4, c5 = st.columns([2, 2, 3, 2, 1])
                    c1.write(e[1]); c2.write(e[4]); c3.write(e[2]); c4.write(f"{e[3]:,.0f} টাকা")
                    if c5.button("🗑️", key=f"de_{e[0]}"):
                        conn = sqlite3.connect('somiti.db'); c = conn.cursor()
                        c.execute("DELETE FROM expenses WHERE id=?", (e[0],)); conn.commit(); conn.close(); st.rerun()
                st.metric("মোট খরচ", f"{sum(e[3] for e in expenses):,.0f} টাকা")
    
    elif menu == "📊 রিপোর্ট":
        st.markdown("### 📊 রিপোর্ট")
        tab1, tab2 = st.tabs(["📈 মাসিক", "⚠️ বকেয়া"])
        with tab1:
            data = get_monthly_report()
            if data:
                df = pd.DataFrame(data, columns=["মাস", "জমা"])
                st.bar_chart(df.set_index("মাস")); st.dataframe(df, use_container_width=True, hide_index=True)
        with tab2:
            unpaid = get_unpaid_members()
            if unpaid:
                df = pd.DataFrame([{"নাম": m[1], "মোবাইল": m[2], "কিস্তি": f"{m[3]:,.0f}", "জমা": f"{m[4]:,.0f}"} for m in unpaid])
                st.dataframe(df, use_container_width=True, hide_index=True)
                if st.button("📧 বকেয়া রিমাইন্ডার পাঠান", type="primary"):
                    sent = 0
                    for m in unpaid:
                        if m[5] and send_email(m[5], f"⚠️ বকেয়া রিমাইন্ডার - {SOMITI_NAME}", f"প্রিয় {m[1]},\n\n{get_bangla_month()} মাসের কিস্তি ({m[3]:,.0f} টাকা) বকেয়া আছে।\n\n🙏 আজই পরিশোধ করুন।"): sent += 1
                    st.success(f"✅ {sent} জনকে ইমেইল পাঠানো হয়েছে!")
    
    elif menu == "📧 ইমেইল টেস্ট":
        st.markdown("### 📧 ইমেইল টেস্ট")
        test_email = st.text_input("টেস্ট ইমেইল", placeholder="example@gmail.com")
        if st.button("📨 টেস্ট ইমেইল পাঠান", type="primary"):
            if send_email(test_email, f"🧪 টেস্ট - {SOMITI_NAME}", "এটি একটি টেস্ট ইমেইল। আপনার ইমেইল নোটিফিকেশন কাজ করছে!"):
                st.success("✅ ইমেইল পাঠানো হয়েছে!")
            else: st.error("❌ ইমেইল পাঠানো যায়নি")
    
    elif menu == "🎲 লটারি":
        st.markdown("### 🎲 লটারি")
        if st.button("🎲 বিজয়ী নির্বাচন", type="primary"):
            w = pick_lottery_winner()
            if w:
                st.balloons()
                st.success(f"🎉 বিজয়ী: {w[1]} ({w[0]})")
                if w[4]: send_email(w[4], f"🎉 লটারি বিজয়ী - {SOMITI_NAME}", f"অভিনন্দন {w[1]}!\n\nআপনি লটারিতে বিজয়ী হয়েছেন! 🏆")

# ============================================
# সদস্য প্যানেল
# ============================================
def member_panel():
    apply_dark_theme()
    show_header()
    conn = sqlite3.connect('somiti.db'); c = conn.cursor()
    c.execute("SELECT name, phone, total_savings, monthly_savings, id FROM members WHERE id=?", (st.session_state.member_id,))
    m = c.fetchone()
    if not m: st.error("সদস্য নেই"); st.stop()
    name, phone, savings, monthly, mid = m
    monthly = monthly or 500
    
    with st.sidebar:
        st.markdown(f"### 👤 {name}"); st.caption(f"🆔 {mid} | 📱 {phone}")
        st.metric("💰 জমা", f"{savings:,.0f} টাকা")
        menu = st.radio("মেনু", ["📊 ড্যাশবোর্ড", "🔑 পাসওয়ার্ড", "🚪 লগআউট"], label_visibility="collapsed")
    
    if menu == "🚪 লগআউট":
        for k in ['logged_in', 'user_type', 'member_id']: del st.session_state[k]
        st.rerun()
    elif menu == "📊 ড্যাশবোর্ড":
        st.markdown(f"### স্বাগতম, {name}!")
        c1, c2 = st.columns(2)
        c1.metric("💰 জমা", f"{savings:,.0f} টাকা"); c2.metric("📅 কিস্তি", f"{monthly:,.0f} টাকা")
        trans = get_member_transactions(mid)
        if trans:
            df = pd.DataFrame([{"তারিখ": t[1], "টাকা": f"{t[2]:,.0f}", "মাস": t[3]} for t in trans])
            st.dataframe(df, use_container_width=True, hide_index=True)
    elif menu == "🔑 পাসওয়ার্ড":
        cur = st.text_input("বর্তমান", type="password"); new = st.text_input("নতুন", type="password")
        if st.button("🔄 পরিবর্তন", type="primary"):
            c.execute("SELECT password FROM members WHERE id=?", (mid,))
            if cur != c.fetchone()[0]: st.error("❌ ভুল")
            elif len(new) < 4: st.error("❌ ৪+ অক্ষর")
            else:
                c.execute("UPDATE members SET password=? WHERE id=?", (new, mid))
                conn.commit(); st.success("✅ পরিবর্তন হয়েছে!")
    conn.close()

# ============================================
# মেইন
# ============================================
def main():
    init_database()
    if member_view_id:
        public_member_view(member_view_id)
        return
    
    if 'logged_in' not in st.session_state: st.session_state.logged_in = False
    if 'user_type' not in st.session_state: st.session_state.user_type = None
    if 'member_id' not in st.session_state: st.session_state.member_id = None
    
    if not st.session_state.logged_in: login_page()
    elif st.session_state.user_type == 'admin': admin_panel()
    elif st.session_state.user_type == 'member': member_panel()

if __name__ == "__main__":
    main()
