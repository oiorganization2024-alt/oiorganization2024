import streamlit as st
import pandas as pd
import random
import string
from datetime import datetime
from io import BytesIO
import os
import shutil
import time
import json
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

# ==================== কনফিগারেশন ====================
ADMIN_MOBILE = "01766222373"
ADMIN_PASSWORD = "oio112024"
SOMITI_NAME = "ঐক্য উদ্যোগ সংস্থা"
SOMITI_NAME_EN = "Oikko Uddog Songstha"
SOMITI_START_DATE = "2026-04-12"

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465
SENDER_EMAIL = "oiorganization2024@gmail.com"
SENDER_PASSWORD = "hnhm ocix kyxv ioiz"

st.set_page_config(page_title=SOMITI_NAME, page_icon="🌾", layout="wide")

try:
    query_params = st.query_params
    member_login_id = query_params.get("member") if query_params else None
except:
    member_login_id = None

if 'language' not in st.session_state:
    st.session_state.language = 'bn'

def t(bn_text, en_text):
    return bn_text if st.session_state.language == 'bn' else en_text

BANGLA_MONTHS = {
    1: "জানুয়ারি", 2: "ফেব্রুয়ারি", 3: "মার্চ", 4: "এপ্রিল",
    5: "মে", 6: "জুন", 7: "জুলাই", 8: "আগস্ট",
    9: "সেপ্টেম্বর", 10: "অক্টোবর", 11: "নভেম্বর", 12: "ডিসেম্বর"
}

ENGLISH_MONTHS = {
    1: "January", 2: "February", 3: "March", 4: "April",
    5: "May", 6: "June", 7: "July", 8: "August",
    9: "September", 10: "October", 11: "November", 12: "December"
}

# ==================== ফাইল পাথ ও ডাটাবেস সেটআপ ====================
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

MEMBERS_CSV = f"{DATA_DIR}/members.csv"
TRANSACTIONS_CSV = f"{DATA_DIR}/transactions.csv"
EXPENSES_CSV = f"{DATA_DIR}/expenses.csv"
WITHDRAWALS_CSV = f"{DATA_DIR}/withdrawals.csv"
FUND_CSV = f"{DATA_DIR}/fund_transactions.csv"
SETTINGS_JSON = f"{DATA_DIR}/settings.json"

MEMBER_COLS = ['id', 'name', 'phone', 'email', 'password', 'total_savings', 'monthly_savings', 'join_date', 'status']
TRANSACTION_COLS = ['id', 'member_id', 'amount', 'transaction_type', 'day', 'month', 'year',
                    'month_name', 'month_name_en', 'full_date', 'full_date_en', 'date_iso', 'late_fee', 'created_at']
EXPENSE_COLS = ['id', 'description', 'amount', 'date', 'category']
FUND_COLS = ['id', 'type', 'amount', 'description', 'date', 'previous_balance', 'current_balance', 'created_at']
WITHDRAWAL_COLS = ['id', 'date', 'amount', 'description', 'withdrawn_by', 'previous_balance', 'current_balance', 'created_at']

# ==================== হেল্পার ফাংশনসমূহ ====================
def load_df(file_path, columns):
    if os.path.exists(file_path):
        try:
            df = pd.read_csv(file_path, encoding='utf-8')
            for col in columns:
                if col not in df.columns: df[col] = ''
            return df
        except: return pd.DataFrame(columns=columns)
    return pd.DataFrame(columns=columns)

def save_df(df, file_path):
    df.to_csv(file_path, index=False, encoding='utf-8')

def get_next_id(file_path, columns):
    df = load_df(file_path, columns)
    return int(df['id'].max()) + 1 if len(df) > 0 else 1

def append_row(file_path, row_dict, columns):
    df = load_df(file_path, columns)
    df = pd.concat([df, pd.DataFrame([row_dict])], ignore_index=True)
    save_df(df, file_path)

def fmt(val):
    try: return f"{int(float(val)):,}"
    except: return "0"

# ==================== কোর লজিক ফাংশনসমূহ ====================
def get_total_savings():
    df = load_df(MEMBERS_CSV, MEMBER_COLS)
    return int(df[df['status'] == 'active']['total_savings'].astype(float).sum()) if len(df) > 0 else 0

def get_fund_balance():
    df = load_df(FUND_CSV, FUND_COLS)
    if len(df) == 0: return 0
    deposits = df[df['type'] == 'deposit']['amount'].astype(float).sum()
    withdrawals = df[df['type'] == 'withdrawal']['amount'].astype(float).sum()
    return int(deposits - withdrawals)

def get_cash_balance():
    exp = load_df(EXPENSES_CSV, EXPENSE_COLS)['amount'].astype(float).sum() if os.path.exists(EXPENSES_CSV) else 0
    withd = load_df(WITHDRAWALS_CSV, WITHDRAWAL_COLS)['amount'].astype(float).sum() if os.path.exists(WITHDRAWALS_CSV) else 0
    return int(get_total_savings() + get_fund_balance() - exp - withd)

def get_member_by_id(member_id):
    df = load_df(MEMBERS_CSV, MEMBER_COLS)
    match = df[df['id'].astype(str) == str(member_id)]
    return match.iloc[0].to_dict() if len(match) > 0 else None

def get_member_transactions(member_id):
    df = load_df(TRANSACTIONS_CSV, TRANSACTION_COLS)
    return df[df['member_id'].astype(str) == str(member_id)].sort_values('id', ascending=False).to_dict('records')

def get_unpaid_members():
    curr = datetime.now()
    tdf = load_df(TRANSACTIONS_CSV, TRANSACTION_COLS)
    mdf = load_df(MEMBERS_CSV, MEMBER_COLS)
    paid_ids = tdf[(tdf['month'] == curr.month) & (tdf['year'] == curr.year)]['member_id'].astype(str).unique()
    return mdf[(mdf['status'] == 'active') & (~mdf['id'].astype(str).isin(paid_ids))].to_dict('records')

def delete_member(member_id):
    mid = str(member_id)
    mdf = load_df(MEMBERS_CSV, MEMBER_COLS)
    save_df(mdf[mdf['id'].astype(str) != mid], MEMBERS_CSV)
    tdf = load_df(TRANSACTIONS_CSV, TRANSACTION_COLS)
    save_df(tdf[tdf['member_id'].astype(str) != mid], TRANSACTIONS_CSV)
    return True

# ==================== UI থিম ও ড্যাশবোর্ড ====================
def apply_dark_theme():
    st.markdown("""
    <style>
    .stApp { background: #0d1117; }
    .somiti-header { background: linear-gradient(135deg, #1a5276 0%, #2980b9 100%); padding: 20px; border-radius: 15px; text-align: center; color: white; margin-bottom: 20px; }
    .total-box { background: #1e8449; padding: 15px; border-radius: 10px; text-align: center; color: white; }
    .cash-box { background: #d35400; padding: 15px; border-radius: 10px; text-align: center; color: white; }
    .kpi-card { background: #21262d; padding: 15px; border-radius: 10px; text-align: center; border: 1px solid #30363d; }
    .member-card { background: #21262d; padding: 15px; border-radius: 10px; margin-bottom: 10px; border: 1px solid #30363d; }
    </style>
    """, unsafe_allow_html=True)

def show_admin_header():
    st.markdown(f'<div class="somiti-header"><h1>🌾 {SOMITI_NAME} 🌾</h1><p>সঞ্চয় ও ঋণ ব্যবস্থাপনা</p></div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    c1.markdown(f'<div class="total-box"><h2>💰 {fmt(get_total_savings())}</h2><p>মোট সঞ্চয়</p></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="cash-box"><h2>💵 {fmt(get_cash_balance())}</h2><p>ক্যাশ ব্যালেন্স</p></div>', unsafe_allow_html=True)

# ==================== পিডিএফ জেনারেটর ====================
def generate_pdf_member_list():
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()
    elements.append(Paragraph(f"{SOMITI_NAME} - Member List", styles['Heading1']))
    mdf = load_df(MEMBERS_CSV, MEMBER_COLS)
    data = [['ID', 'Name', 'Phone', 'Savings']]
    for _, r in mdf.iterrows(): data.append([r['id'], r['name'], r['phone'], fmt(r['total_savings'])])
    table = Table(data)
    table.setStyle(TableStyle([('BACKGROUND', (0,0), (-1,0), colors.blue), ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke), ('GRID', (0,0), (-1,-1), 1, colors.black)]))
    elements.append(table)
    doc.build(elements)
    buffer.seek(0)
    return buffer

# ==================== এডমিন প্যানেল ====================
def admin_panel():
    apply_dark_theme()
    show_admin_header()
    
    with st.sidebar:
        st.markdown("### 🌐 ভাষা / Language")
        if st.radio("Select Language", ["🇧🇩 বাংলা", "🇬🇧 English"], label_visibility="collapsed") == "🇬🇧 English": st.session_state.language = 'en'
        else: st.session_state.language = 'bn'
        
        st.markdown("---")
        st.markdown("### 📋 এডমিন মেনু")
        menu = st.radio("নির্বাচন করুন", [
            f"🏠 {t('ড্যাশবোর্ড', 'Dashboard')}", f"➕ {t('নতুন সদস্য', 'New Member')}", f"✏️ {t('সদস্য ব্যবস্থাপনা', 'Manage Members')}",
            f"💵 {t('টাকা জমা', 'Deposit')}", f"🔄 {t('লেনদেন পরিবর্তন', 'Transactions')}", f"💸 {t('ব্যয় হিসাব', 'Expenses')}",
            f"📒 {t('ব্যয় তালিকা', 'Expense List')}", f"🔗 {t('সদস্য লিংক', 'Member Links')}", f"🏧 {t('ফান্ড ব্যবস্থাপনা', 'Fund Management')}",
            f"📊 {t('রিপোর্ট', 'Reports')}", f"📥 {t('পিডিএফ ডাউনলোড', 'PDF Download')}", f"📧 {t('ইমেইল টেস্ট', 'Email Test')}",
            f"🎲 {t('লটারি', 'Lottery')}", f"🚪 {t('লগআউট', 'Logout')}"
        ], label_visibility="collapsed")

    if "লগআউট" in menu:
        st.session_state.admin_logged_in = False
        st.rerun()

    elif "ড্যাশবোর্ড" in menu:
        st.markdown(f"### 🏠 {t('এডমিন ড্যাশবোর্ড', 'Admin Dashboard')}")
        mdf = load_df(MEMBERS_CSV, MEMBER_COLS)
        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(f'<div class="kpi-card"><h3>👥 সদস্য</h3><h2>{len(mdf[mdf["status"]=="active"])}</h2></div>', unsafe_allow_html=True)
        c2.markdown(f'<div class="kpi-card"><h3>💰 মোট জমা</h3><h2>{fmt(get_total_savings())}</h2></div>', unsafe_allow_html=True)
        c3.markdown(f'<div class="kpi-card"><h3>📅 এই মাস</h3><h2>{fmt(load_df(TRANSACTIONS_CSV, TRANSACTION_COLS).amount.astype(float).sum())}</h2></div>', unsafe_allow_html=True) #Simplified
        c4.markdown(f'<div class="kpi-card"><h3>⚠️ বকেয়া</h3><h2>{len(get_unpaid_members())}</h2></div>', unsafe_allow_html=True)

    elif "নতুন সদস্য" in menu:
        st.markdown(f"### ➕ {t('নতুন সদস্য নিবন্ধন', 'New Member')}")
        with st.form("add_mem"):
            name = st.text_input("নাম *")
            phone = st.text_input("মোবাইল *")
            email = st.text_input("ইমেইল")
            monthly = st.number_input("মাসিক কিস্তি", value=500)
            if st.form_submit_button("✅ সদস্য যোগ করুন"):
                if name and phone:
                    mid = generate_member_id()
                    append_row(MEMBERS_CSV, {'id': mid, 'name': name, 'phone': phone, 'email': email, 'password': ''.join(random.choices(string.digits, k=6)), 'total_savings': 0, 'monthly_savings': int(monthly), 'join_date': datetime.now().strftime("%Y-%m-%d"), 'status': 'active'}, MEMBER_COLS)
                    st.success(f"সদস্য আইডি {mid} সফলভাবে তৈরি হয়েছে।")
                else: st.error("নাম ও মোবাইল আবশ্যক।")

    elif "সদস্য ব্যবস্থাপনা" in menu:
        st.markdown(f"### ✏️ {t('সদস্য ব্যবস্থাপনা', 'Manage Members')}")
        mdf = load_df(MEMBERS_CSV, MEMBER_COLS)
        for _, m in mdf.iterrows():
            with st.expander(f"👤 {m['name']} ({m['id']})"):
                st.write(f"মোবাইল: {m['phone']} | কিস্তি: {m['monthly_savings']}")
                if st.button(f"🗑️ ডিলিট করুন", key=f"del_{m['id']}"):
                    delete_member(m['id'])
                    st.success("সদস্য ডিলিট হয়েছে।")
                    st.rerun()

    elif "টাকা জমা" in menu:
        st.markdown(f"### 💵 {t('সদস্যের টাকা জমা', 'Deposit')}")
        unpaid = get_unpaid_members()
        if not unpaid: st.success("সবাই কিস্তি পরিশোধ করেছেন।")
        for u in unpaid:
            with st.expander(f"❌ {u['name']} ({u['id']}) - কিস্তি: {u['monthly_savings']}"):
                amt = st.number_input("পরিমাণ", value=int(u['monthly_savings']), key=f"amt_{u['id']}")
                fee = st.number_input("লেট ফি", value=0, key=f"fee_{u['id']}")
                if st.button("✅ জমা নিন", key=f"btn_{u['id']}"):
                    today = datetime.now()
                    add_transaction({
                        'id': get_next_id(TRANSACTIONS_CSV, TRANSACTION_COLS), 'member_id': u['id'], 'amount': int(amt), 'transaction_type': 'deposit',
                        'day': today.day, 'month': today.month, 'year': today.year, 'month_name': BANGLA_MONTHS[today.month],
                        'full_date': f"{today.day} {BANGLA_MONTHS[today.month]} {today.year}", 'created_at': today.strftime("%Y-%m-%d %H:%M:%S"), 'late_fee': int(fee)
                    })
                    mdf = load_df(MEMBERS_CSV, MEMBER_COLS)
                    mdf.loc[mdf['id'].astype(str) == str(u['id']), 'total_savings'] = int(float(u['total_savings'])) + amt + fee
                    save_df(mdf, MEMBERS_CSV)
                    st.success("জমা সম্পন্ন হয়েছে!")
                    st.rerun()

    # ==================== লেনদেন পরিবর্তন (FIXED LOGIC) ====================
    elif "লেনদেন পরিবর্তন" in menu:
        st.markdown(f"### 🔄 {t('লেনদেন পরিবর্তন', 'Transactions')}")
        members = [m for m in get_all_members() if m['status'] == 'active']
        options = ["— নির্বাচন করুন —"] + [f"{m['name']} ({m['id']})" for m in members]
        chosen = st.selectbox("সদস্য নির্বাচন করুন", options)
        
        if not chosen.startswith("—"):
            sel_id = chosen.split("(")[-1].rstrip(")")
            sel_member = get_member_by_id(sel_id)
            if sel_member:
                st.info(f"সদস্য: {sel_member['name']} | মোট জমা: {fmt(sel_member['total_savings'])}")
                trans = get_member_transactions(sel_id)
                if trans:
                    t_options = [f"ID: {tr['id']} | {tr['full_date']} | {fmt(tr['amount'])} টাকা" for tr in trans]
                    sel_t_label = st.selectbox("লেনদেন নির্বাচন করুন", t_options)
                    sel_t = trans[t_options.index(sel_t_label)]
                    
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("✏️ এডিট"): st.session_state.edit_id = sel_t['id']
                    with c2:
                        if st.button("🗑️ ডিলিট"):
                            # Delete and adjust balance
                            mdf = load_df(MEMBERS_CSV, MEMBER_COLS)
                            cur = int(float(mdf.loc[mdf['id'].astype(str) == str(sel_id), 'total_savings'].values[0]))
                            mdf.loc[mdf['id'].astype(str) == str(sel_id), 'total_savings'] = max(0, cur - int(float(sel_t['amount'])))
                            save_df(mdf, MEMBERS_CSV)
                            save_df(load_df(TRANSACTIONS_CSV, TRANSACTION_COLS)[load_df(TRANSACTIONS_CSV, TRANSACTION_COLS).id != sel_t['id']], TRANSACTIONS_CSV)
                            st.success("ডিলিট হয়েছে।")
                            st.rerun()
                else: st.warning("কোনো লেনদেন পাওয়া যায়নি।")

    elif "ব্যয় হিসাব" in menu:
        st.markdown(f"### 💸 {t('ব্যয় হিসাব', 'Expenses')}")
        with st.form("exp"):
            desc = st.text_input("বিবরণ")
            amt = st.number_input("পরিমাণ", min_value=1)
            cat = st.selectbox("ক্যাটাগরি", ["অফিস", "নাস্তা", "পরিবহন", "অন্যান্য"])
            if st.form_submit_button("💾 খরচ যোগ করুন"):
                append_row(EXPENSES_CSV, {'id': get_next_id(EXPENSES_CSV, EXPENSE_COLS), 'description': desc, 'amount': int(amt), 'date': datetime.now().strftime("%Y-%m-%d"), 'category': cat}, EXPENSE_COLS)
                st.success("খরচ যোগ হয়েছে।")

    elif "সদস্য লিংক" in menu:
        st.markdown(f"### 🔗 {t('সদস্য লিংক', 'Member Links')}")
        for m in get_all_members():
            link = f"https://oiorganization2024.streamlit.app/?member={m['id']}"
            st.markdown(f'<div class="member-card"><b>👤 {m["name"]}</b><br>ID: {m["id"]} | Pass: {m["password"]}<br><code>{link}</code></div>', unsafe_allow_html=True)

    elif "পিডিএফ ডাউনলোড" in menu:
        if st.button("📥 সদস্য তালিকা পিডিএফ ডাউনলোড"):
            pdf = generate_pdf_member_list()
            st.download_button("Download Now", pdf, "members.pdf", "application/pdf")

    elif "লটারি" in menu:
        if st.button("🎲 লটারি ড্র করুন"):
            m = random.choice([m for m in get_all_members() if m['status']=='active'])
            st.balloons()
            st.success(f"🎉 বিজয়ীর নাম: {m['name']} (ID: {m['id']})")

# ==================== মেইন লগইন পেজ ====================
def main():
    if 'admin_logged_in' not in st.session_state: st.session_state.admin_logged_in = False
    
    if member_login_id:
        st.info(f"মেম্বার লগইন (ID: {member_login_id}) ফিচারটি সক্রিয় করা হচ্ছে...")
        # এখানে মেম্বার ড্যাশবোর্ড লজিক যোগ করা যাবে
        return

    if not st.session_state.admin_logged_in:
        apply_dark_theme()
        st.markdown('<div class="somiti-header"><h1>🌾 ঐক্য উদ্যোগ সংস্থা 🌾</h1><p>এডমিন প্যানেল লগইন</p></div>', unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            phone = st.text_input("📱 মোবাইল নম্বর", placeholder="017XXXXXXXX")
            password = st.text_input("🔑 পাসওয়ার্ড", type="password")
            if st.button("প্রবেশ করুন", use_container_width=True, type="primary"):
                if phone == ADMIN_MOBILE and password == ADMIN_PASSWORD:
                    st.session_state.admin_logged_in = True
                    st.rerun()
                else: st.error("❌ ভুল মোবাইল নম্বর বা পাসওয়ার্ড!")
    else:
        admin_panel()

if __name__ == "__main__":
    main()
