import streamlit as st
import pandas as pd
import random
import string
from datetime import datetime, timedelta
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

# ইমেইল কনফিগ (শুধু টেস্টের জন্য)
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

# ==================== ফাইল পাথ (CSV) ====================
DATA_DIR = "data"
ARCHIVE_DIR = "archives"

MEMBERS_CSV = f"{DATA_DIR}/members.csv"
TRANSACTIONS_CSV = f"{DATA_DIR}/transactions.csv"
EXPENSES_CSV = f"{DATA_DIR}/expenses.csv"
WITHDRAWALS_CSV = f"{DATA_DIR}/withdrawals.csv"
FUND_CSV = f"{DATA_DIR}/fund_transactions.csv"
SETTINGS_JSON = f"{DATA_DIR}/settings.json"

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(ARCHIVE_DIR, exist_ok=True)

# কলাম ডেফিনেশন
MEMBER_COLS = ['id', 'name', 'phone', 'email', 'password', 'total_savings', 'monthly_savings', 'join_date', 'status']
TRANSACTION_COLS = ['id', 'member_id', 'amount', 'transaction_type', 'day', 'month', 'year',
                    'month_name', 'month_name_en', 'full_date', 'full_date_en', 'date_iso', 'late_fee', 'created_at']
EXPENSE_COLS = ['id', 'description', 'amount', 'date', 'category']
WITHDRAWAL_COLS = ['id', 'date', 'amount', 'description', 'withdrawn_by', 'previous_balance', 'current_balance', 'created_at']
FUND_COLS = ['id', 'type', 'amount', 'description', 'date', 'previous_balance', 'current_balance', 'created_at']

# ==================== CSV হেল্পার ফাংশন ====================
def load_df(file_path, columns):
    if os.path.exists(file_path):
        try:
            return pd.read_csv(file_path, encoding='utf-8')
        except:
            return pd.DataFrame(columns=columns)
    return pd.DataFrame(columns=columns)

def save_df(df, file_path):
    df.to_csv(file_path, index=False, encoding='utf-8')

def get_next_id(file_path, columns):
    df = load_df(file_path, columns)
    if len(df) == 0:
        return 1
    return int(df['id'].max()) + 1

def append_row(file_path, row_dict, columns):
    df = load_df(file_path, columns)
    new_row = pd.DataFrame([row_dict])
    df = pd.concat([df, new_row], ignore_index=True)
    save_df(df, file_path)

def update_row(file_path, row_id, updates, columns):
    df = load_df(file_path, columns)
    idx = df[df['id'] == int(row_id)].index
    if len(idx) > 0:
        for k, v in updates.items():
            df.loc[idx[0], k] = v
        save_df(df, file_path)
        return True
    return False

def delete_row(file_path, row_id, columns):
    df = load_df(file_path, columns)
    df = df[df['id'] != int(row_id)]
    save_df(df, file_path)

# ==================== সেটিংস ====================
def load_settings():
    if os.path.exists(SETTINGS_JSON):
        with open(SETTINGS_JSON, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"start_date": SOMITI_START_DATE}

def save_settings(settings):
    with open(SETTINGS_JSON, 'w', encoding='utf-8') as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)

# ==================== আর্কাইভ ====================
def check_and_archive_old_data():
    settings = load_settings()
    start = datetime.strptime(settings['start_date'], "%Y-%m-%d")
    if (datetime.now() - start).days / 365 >= 20:
        archive_name = f"archive_{start.year}_{datetime.now().year}"
        archive_path = f"{ARCHIVE_DIR}/{archive_name}"
        os.makedirs(archive_path, exist_ok=True)
        for f in [MEMBERS_CSV, TRANSACTIONS_CSV, EXPENSES_CSV, WITHDRAWALS_CSV, FUND_CSV]:
            if os.path.exists(f):
                shutil.copy(f, archive_path)
        # ক্লিয়ার
        for f, cols in [(MEMBERS_CSV, MEMBER_COLS), (TRANSACTIONS_CSV, TRANSACTION_COLS),
                        (EXPENSES_CSV, EXPENSE_COLS), (WITHDRAWALS_CSV, WITHDRAWAL_COLS), (FUND_CSV, FUND_COLS)]:
            pd.DataFrame(columns=cols).to_csv(f, index=False)
        settings['start_date'] = datetime.now().strftime("%Y-%m-%d")
        save_settings(settings)

# ==================== ইমেইল টেস্ট ====================
def send_test_email(to_email):
    if not to_email or '@' not in str(to_email):
        return False
    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        msg = MIMEMultipart()
        msg['From'] = f"{SOMITI_NAME} <{SENDER_EMAIL}>"
        msg['To'] = to_email
        msg['Subject'] = f"🧪 ইমেইল টেস্ট - {SOMITI_NAME}"
        
        html = f"""
        <html>
        <head><meta charset="UTF-8"></head>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <h2>🌾 {SOMITI_NAME}</h2>
            <p>✅ আপনার ইমেইল কনফিগারেশন সঠিকভাবে কাজ করছে!</p>
            <hr>
            <p style="color: #666; font-size: 12px;">{SOMITI_NAME_EN}</p>
        </body>
        </html>
        """
        msg.attach(MIMEText(html, 'html', 'utf-8'))
        
        server = smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15)
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Email Error: {e}")
        return False

# ==================== ইউটিলিটি ফাংশন ====================
def generate_member_id():
    df = load_df(MEMBERS_CSV, MEMBER_COLS)
    if len(df) == 0:
        return "10001"
    max_id = max([int(str(x)) for x in df['id'].tolist()])
    return str(max_id + 1)

def generate_password():
    return ''.join(random.choices(string.digits, k=6))

def get_total_savings():
    df = load_df(MEMBERS_CSV, MEMBER_COLS)
    if len(df) == 0:
        return 0.0
    active = df[df['status'] == 'active']
    return active['total_savings'].astype(float).sum()

def get_total_expenses():
    df = load_df(EXPENSES_CSV, EXPENSE_COLS)
    if len(df) == 0:
        return 0.0
    return df['amount'].astype(float).sum()

def get_total_withdrawals():
    df = load_df(WITHDRAWALS_CSV, WITHDRAWAL_COLS)
    if len(df) == 0:
        return 0.0
    return df['amount'].astype(float).sum()

def get_fund_balance():
    df = load_df(FUND_CSV, FUND_COLS)
    if len(df) == 0:
        return 0.0
    deposits = df[df['type'] == 'deposit']['amount'].astype(float).sum()
    withdrawals = df[df['type'] == 'withdrawal']['amount'].astype(float).sum()
    return deposits - withdrawals

def get_cash_balance():
    return get_total_savings() + get_fund_balance() - get_total_expenses() - get_total_withdrawals()

def get_paid_members():
    current = datetime.now()
    trans_df = load_df(TRANSACTIONS_CSV, TRANSACTION_COLS)
    mem_df = load_df(MEMBERS_CSV, MEMBER_COLS)
    if len(trans_df) == 0 or len(mem_df) == 0:
        return []
    paid_ids = trans_df[(trans_df['month'] == current.month) & (trans_df['year'] == current.year)]['member_id'].unique()
    paid = mem_df[mem_df['id'].isin(paid_ids) & (mem_df['status'] == 'active')]
    return paid.to_dict('records')

def get_unpaid_members():
    current = datetime.now()
    trans_df = load_df(TRANSACTIONS_CSV, TRANSACTION_COLS)
    mem_df = load_df(MEMBERS_CSV, MEMBER_COLS)
    active = mem_df[mem_df['status'] == 'active']
    if len(trans_df) == 0:
        return active.to_dict('records')
    paid_ids = trans_df[(trans_df['month'] == current.month) & (trans_df['year'] == current.year)]['member_id'].unique()
    unpaid = active[~active['id'].isin(paid_ids)]
    return unpaid.to_dict('records')

def get_member_transactions(member_id):
    df = load_df(TRANSACTIONS_CSV, TRANSACTION_COLS)
    if len(df) == 0:
        return []
    mem_df = df[df['member_id'] == str(member_id)]
    mem_df = mem_df.sort_values(['year', 'month', 'day'], ascending=[False, False, False])
    return mem_df.to_dict('records')

def get_all_members():
    df = load_df(MEMBERS_CSV, MEMBER_COLS)
    return df.to_dict('records')

def get_member_by_id(member_id):
    df = load_df(MEMBERS_CSV, MEMBER_COLS)
    match = df[df['id'] == str(member_id)]
    if len(match) > 0:
        return match.iloc[0].to_dict()
    return None

def add_member(data):
    data['id'] = generate_member_id()
    data['total_savings'] = data.get('total_savings', 0)
    data['monthly_savings'] = data.get('monthly_savings', 500)
    data['join_date'] = datetime.now().strftime("%Y-%m-%d")
    data['status'] = 'active'
    append_row(MEMBERS_CSV, data, MEMBER_COLS)
    return data['id']

def update_member(member_id, updates):
    df = load_df(MEMBERS_CSV, MEMBER_COLS)
    idx = df[df['id'] == str(member_id)].index
    if len(idx) > 0:
        for k, v in updates.items():
            df.loc[idx[0], k] = v
        save_df(df, MEMBERS_CSV)
        return True
    return False

def delete_member(member_id):
    # ট্রানজেকশন ডিলিট
    trans_df = load_df(TRANSACTIONS_CSV, TRANSACTION_COLS)
    trans_df = trans_df[trans_df['member_id'] != str(member_id)]
    save_df(trans_df, TRANSACTIONS_CSV)
    # মেম্বার ডিলিট
    mem_df = load_df(MEMBERS_CSV, MEMBER_COLS)
    mem_df = mem_df[mem_df['id'] != str(member_id)]
    save_df(mem_df, MEMBERS_CSV)

def add_transaction(data):
    data['id'] = get_next_id(TRANSACTIONS_CSV, TRANSACTION_COLS)
    append_row(TRANSACTIONS_CSV, data, TRANSACTION_COLS)

def update_transaction(trans_id, updates):
    return update_row(TRANSACTIONS_CSV, trans_id, updates, TRANSACTION_COLS)

def delete_transaction(trans_id):
    delete_row(TRANSACTIONS_CSV, trans_id, TRANSACTION_COLS)

def get_all_expenses():
    df = load_df(EXPENSES_CSV, EXPENSE_COLS)
    return df.to_dict('records')

def add_expense(data):
    data['id'] = get_next_id(EXPENSES_CSV, EXPENSE_COLS)
    append_row(EXPENSES_CSV, data, EXPENSE_COLS)

def delete_expense(exp_id):
    delete_row(EXPENSES_CSV, exp_id, EXPENSE_COLS)

def get_all_withdrawals():
    df = load_df(WITHDRAWALS_CSV, WITHDRAWAL_COLS)
    return df.to_dict('records')

def add_withdrawal(data):
    data['id'] = get_next_id(WITHDRAWALS_CSV, WITHDRAWAL_COLS)
    append_row(WITHDRAWALS_CSV, data, WITHDRAWAL_COLS)

def get_fund_transactions():
    df = load_df(FUND_CSV, FUND_COLS)
    df = df.sort_values('id', ascending=False)
    return df.to_dict('records')

def add_fund_transaction(data):
    data['id'] = get_next_id(FUND_CSV, FUND_COLS)
    append_row(FUND_CSV, data, FUND_COLS)

def get_monthly_report():
    df = load_df(TRANSACTIONS_CSV, TRANSACTION_COLS)
    if len(df) == 0:
        return []
    df['month_year'] = df['month_name'] + ' ' + df['year'].astype(str)
    report = df.groupby(['year', 'month', 'month_year'])['amount'].sum().reset_index()
    report = report.sort_values(['year', 'month'], ascending=[False, False]).head(12)
    return report[['month_year', 'amount']].to_dict('records')

def pick_lottery_winner():
    df = load_df(MEMBERS_CSV, MEMBER_COLS)
    active = df[df['status'] == 'active']
    if len(active) == 0:
        return None
    return active.sample(1).iloc[0].to_dict()

def get_app_url():
    return "https://oiorganization2024.streamlit.app"

def get_current_month_collection():
    current = datetime.now()
    df = load_df(TRANSACTIONS_CSV, TRANSACTION_COLS)
    if len(df) == 0:
        return 0.0
    month_df = df[(df['month'] == current.month) & (df['year'] == current.year)]
    return month_df['amount'].astype(float).sum()

# ==================== UI থিম ====================
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
    .stDataFrame { border-radius: 10px; overflow: hidden; border: 1px solid #30363d; }
    .stDataFrame th { background: #21262d !important; color: #c9d1d9 !important; }
    .stDataFrame td { background: #161b22 !important; color: #c9d1d9 !important; }
    .kpi-card { background: #21262d; padding: 15px; border-radius: 10px; text-align: center; border: 1px solid #30363d; }
    .kpi-card h3 { color: #c9d1d9; font-size: 14px; margin: 0 0 5px 0; }
    .kpi-card h2 { color: #58a6ff; font-size: 24px; margin: 0; }
    </style>
    """, unsafe_allow_html=True)

def show_admin_header():
    total = get_total_savings()
    cash = get_cash_balance()
    st.markdown(f'<div class="somiti-header"><h1>🌾 {SOMITI_NAME} 🌾</h1><p>{t("সঞ্চয় ও ঋণ ব্যবস্থাপনা", "Savings & Loan Management")}</p></div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f'<div class="total-box"><h2>💰 {total:,.0f} {t("টাকা", "Taka")}</h2><p>{t("মোট জমা", "Total Savings")}</p></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="cash-box"><h2>💵 {cash:,.0f} {t("টাকা", "Taka")}</h2><p>{t("ক্যাশ ব্যালেন্স", "Cash Balance")}</p></div>', unsafe_allow_html=True)

# ==================== পিডিএফ ====================
def generate_pdf_member_list():
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()
    elements.append(Paragraph(f"{SOMITI_NAME} - Member List", styles['Heading1']))
    elements.append(Spacer(1, 20))
    members = get_all_members()
    data = [['ID', 'Name', 'Mobile', 'Monthly', 'Savings']]
    for m in members:
        monthly = float(m.get('monthly_savings', 500))
        savings = float(m.get('total_savings', 0))
        data.append([m['id'], m['name'], m['phone'], f"{monthly:,.0f}", f"{savings:,.0f}"])
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a5276')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elements.append(table)
    doc.build(elements)
    buffer.seek(0)
    return buffer

def generate_pdf_transactions(member_id=None):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()
    title = f"{SOMITI_NAME} - Transaction Report"
    if member_id:
        member = get_member_by_id(member_id)
        if member:
            title = f"{SOMITI_NAME} - {member['name']} ({member_id})"
    elements.append(Paragraph(title, styles['Heading1']))
    elements.append(Spacer(1, 20))
    
    if member_id:
        trans = get_member_transactions(member_id)
        data = [['Date', 'Amount', 'Month', 'Year']]
        for tr in trans:
            amount = float(tr.get('amount', 0))
            data.append([tr['full_date'], f"{amount:,.0f}", tr['month_name'], str(tr['year'])])
    else:
        trans_df = load_df(TRANSACTIONS_CSV, TRANSACTION_COLS)
        mem_df = load_df(MEMBERS_CSV, MEMBER_COLS)
        if len(trans_df) > 0 and len(mem_df) > 0:
            merged = trans_df.merge(mem_df[['id', 'name']], left_on='member_id', right_on='id')
            merged = merged.sort_values(['year', 'month', 'day'], ascending=[False, False, False]).head(100)
            data = [['Date', 'Member', 'Amount', 'Month', 'Year']]
            for _, tr in merged.iterrows():
                amount = float(tr['amount'])
                data.append([tr['full_date'], tr['name'], f"{amount:,.0f}", tr['month_name'], str(tr['year'])])
        else:
            data = []
    
    if data:
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a5276')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        elements.append(table)
    doc.build(elements)
    buffer.seek(0)
    return buffer

# ==================== এডমিন প্যানেল ====================
def admin_login_page():
    apply_dark_theme()
    total = get_total_savings()
    st.markdown(f"""
    <div class="somiti-header"><h1>🌾 {SOMITI_NAME} 🌾</h1><p>{t('সঞ্চয় ও ঋণ ব্যবস্থাপনা', 'Savings & Loan Management')}</p></div>
    <div class="total-box"><h2>💰 {total:,.0f} {t('টাকা', 'Taka')}</h2><p>{t('মোট জমা', 'Total Savings')}</p></div>
    """, unsafe_allow_html=True)
    st.markdown(f"### 🔐 {t('এডমিন লগইন', 'Admin Login')}")
    phone = st.text_input(f"📱 {t('মোবাইল নম্বর', 'Mobile')}", placeholder="017XXXXXXXX")
    password = st.text_input(f"🔑 {t('পাসওয়ার্ড', 'Password')}", type="password")
    if st.button(t("প্রবেশ করুন", "Login"), use_container_width=True, type="primary"):
        if phone == ADMIN_MOBILE and password == ADMIN_PASSWORD:
            st.session_state.admin_logged_in = True
            st.rerun()
        else:
            st.error(t("❌ ভুল মোবাইল বা পাসওয়ার্ড", "❌ Wrong mobile or password"))

def admin_panel():
    apply_dark_theme()
    show_admin_header()
    with st.sidebar:
        st.markdown("### 🌐 " + t("ভাষা", "Language"))
        language = st.radio(
            t("ভাষা নির্বাচন করুন", "Select Language"),
            options=["🇧🇩 বাংলা", "🇬🇧 English"],
            index=0 if st.session_state.language == 'bn' else 1,
            label_visibility="collapsed",
            key="language_selector"
        )
        new_lang = 'bn' if language == "🇧🇩 বাংলা" else 'en'
        if new_lang != st.session_state.language:
            st.session_state.language = new_lang
            st.rerun()
        st.markdown("---")
        st.markdown(f"### 📋 {t('এডমিন মেনু', 'Admin Menu')}")
        st.caption(f"👑 {ADMIN_MOBILE}")
        menu = st.radio(
            t("নির্বাচন করুন", "Select"),
            [
                f"🏠 {t('ড্যাশবোর্ড', 'Dashboard')}",
                f"➕ {t('নতুন সদস্য', 'New Member')}",
                f"✏️ {t('সদস্য ব্যবস্থাপনা', 'Manage Members')}",
                f"💵 {t('টাকা জমা', 'Deposit')}",
                f"💰 {t('লেনদেন ব্যবস্থাপনা', 'Transactions')}",
                f"🔗 {t('সদস্য লিংক', 'Member Links')}",
                f"💸 {t('খরচ ব্যবস্থাপনা', 'Expenses')}",
                f"🏧 {t('ফান্ড ব্যবস্থাপনা', 'Fund Management')}",
                f"📊 {t('রিপোর্ট', 'Reports')}",
                f"📥 {t('পিডিএফ ডাউনলোড', 'PDF Download')}",
                f"📧 {t('ইমেইল টেস্ট', 'Email Test')}",
                f"🎲 {t('লটারি', 'Lottery')}",
                f"🚪 {t('লগআউট', 'Logout')}"
            ],
            label_visibility="collapsed"
        )
    
    if f"🚪 {t('লগআউট', 'Logout')}" in menu:
        if 'admin_logged_in' in st.session_state:
            del st.session_state.admin_logged_in
        st.rerun()
    
    elif f"🏠 {t('ড্যাশবোর্ড', 'Dashboard')}" in menu:
        st.markdown(f"### 🏠 {t('এডমিন ড্যাশবোর্ড', 'Admin Dashboard')}")
        col1, col2, col3, col4 = st.columns(4)
        
        members = get_all_members()
        total_members = len([m for m in members if m.get('status') == 'active'])
        total_savings = get_total_savings()
        this_month = get_current_month_collection()
        unpaid_count = len(get_unpaid_members())
        
        with col1:
            st.markdown(f"""<div class="kpi-card"><h3>👥 {t('সদস্য', 'Members')}</h3><h2>{total_members}</h2></div>""", unsafe_allow_html=True)
        with col2:
            st.markdown(f"""<div class="kpi-card"><h3>💰 {t('মোট জমা', 'Total')}</h3><h2>{total_savings:,.0f}</h2></div>""", unsafe_allow_html=True)
        with col3:
            st.markdown(f"""<div class="kpi-card"><h3>📅 {t('এই মাস', 'This Month')}</h3><h2>{this_month:,.0f}</h2></div>""", unsafe_allow_html=True)
        with col4:
            st.markdown(f"""<div class="kpi-card"><h3>⚠️ {t('বকেয়া', 'Due')}</h3><h2>{unpaid_count}</h2></div>""", unsafe_allow_html=True)
    
    elif f"➕ {t('নতুন সদস্য', 'New Member')}" in menu:
        st.markdown(f"### ➕ {t('নতুন সদস্য নিবন্ধন', 'New Member Registration')}")
        name = st.text_input(f"{t('নাম', 'Name')} *")
        phone = st.text_input(f"{t('মোবাইল', 'Mobile')} *", placeholder="017XXXXXXXX")
        email = st.text_input(f"📧 {t('ইমেইল', 'Email')}")
        monthly = st.number_input(f"{t('মাসিক কিস্তি', 'Monthly')} ({t('টাকা', 'Taka')})", value=500, step=50)
        if st.button(f"✅ {t('সদস্য যোগ করুন', 'Add Member')}", type="primary"):
            if name and phone:
                member_id = add_member({
                    'name': name, 'phone': phone, 'email': email,
                    'password': generate_password(), 'monthly_savings': monthly
                })
                password = generate_password()
                update_member(member_id, {'password': password})
                st.success(f"✅ {t('সদস্য তৈরি', 'Member created')}!")
                st.info(f"{t('আইডি', 'ID')}: {member_id} | {t('পাস', 'Pass')}: {password}")
                st.balloons()
            else:
                st.error(t("❌ নাম ও মোবাইল আবশ্যক", "❌ Name and mobile required"))
    
    elif f"✏️ {t('সদস্য ব্যবস্থাপনা', 'Manage Members')}" in menu:
        st.markdown(f"### ✏️ {t('সদস্য ব্যবস্থাপনা', 'Member Management')}")
        members = get_all_members()
        if members:
            # টেবিল আকারে দেখান
            table_data = []
            for m in members:
                table_data.append({
                    t('আইডি', 'ID'): m['id'],
                    t('নাম', 'Name'): m['name'],
                    t('মোবাইল', 'Mobile'): m['phone'],
                    t('কিস্তি', 'Monthly'): f"{float(m.get('monthly_savings', 500)):,.0f}",
                    t('জমা', 'Savings'): f"{float(m.get('total_savings', 0)):,.0f}",
                    t('স্ট্যাটাস', 'Status'): m.get('status', 'active')
                })
            df = pd.DataFrame(table_data)
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            st.markdown("---")
            st.markdown(f"#### ✏️ {t('সদস্য এডিট/ডিলিট', 'Edit/Delete Member')}")
            for m in members:
                with st.expander(f"👤 {m['name']} ({m['id']})"):
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        if st.button(f"📝 {t('এডিট', 'Edit')}", key=f"e_{m['id']}"):
                            st.session_state[f"edit_{m['id']}"] = True
                    with col2:
                        if st.button(f"🔐 {t('পাসওয়ার্ড', 'Password')}", key=f"p_{m['id']}"):
                            st.session_state[f"pass_{m['id']}"] = True
                    with col3:
                        new_status = 'inactive' if m.get('status') == 'active' else 'active'
                        btn_text = t('নিষ্ক্রিয়', 'Inactive') if m.get('status') == 'active' else t('সক্রিয়', 'Active')
                        if st.button(f"🔄 {btn_text}", key=f"s_{m['id']}"):
                            update_member(m['id'], {'status': new_status})
                            st.rerun()
                    with col4:
                        if st.button(f"🗑️ {t('ডিলিট', 'Delete')}", key=f"del_{m['id']}"):
                            st.session_state[f"delete_{m['id']}"] = True
                    
                    if st.session_state.get(f"delete_{m['id']}"):
                        st.warning(f"⚠️ {t('আপনি কি নিশ্চিত?', 'Are you sure?')}")
                        c1, c2 = st.columns(2)
                        with c1:
                            if st.button(f"✅ {t('হ্যাঁ', 'Yes')}", key=f"confirm_{m['id']}"):
                                delete_member(m['id'])
                                st.success(f"✅ {t('ডিলিট', 'Deleted')}!")
                                del st.session_state[f"delete_{m['id']}"]
                                st.rerun()
                        with c2:
                            if st.button(f"❌ {t('না', 'No')}", key=f"cancel_{m['id']}"):
                                del st.session_state[f"delete_{m['id']}"]
                                st.rerun()
                    
                    if st.session_state.get(f"edit_{m['id']}"):
                        with st.form(f"edit_{m['id']}"):
                            new_name = st.text_input(t("নাম", "Name"), value=m['name'])
                            new_phone = st.text_input(t("মোবাইল", "Mobile"), value=m['phone'])
                            new_email = st.text_input(t("ইমেইল", "Email"), value=m.get('email', ''))
                            new_mon = st.number_input(t("কিস্তি", "Monthly"), value=float(m.get('monthly_savings', 500)), step=50.0)
                            if st.form_submit_button("💾"):
                                update_member(m['id'], {
                                    'name': new_name, 'phone': new_phone,
                                    'email': new_email, 'monthly_savings': new_mon
                                })
                                st.success("✅")
                                del st.session_state[f"edit_{m['id']}"]
                                st.rerun()
                    
                    if st.session_state.get(f"pass_{m['id']}"):
                        if st.button(f"✅ {t('নতুন পাসওয়ার্ড', 'New')}", key=f"gen_{m['id']}"):
                            new_pass = generate_password()
                            update_member(m['id'], {'password': new_pass})
                            st.success(f"✅ {t('নতুন পাস', 'New')}: {new_pass}")
                            del st.session_state[f"pass_{m['id']}"]
                            st.rerun()
        else:
            st.info(t("কোনো সদস্য নেই", "No members"))
    
    elif f"💵 {t('টাকা জমা', 'Deposit')}" in menu:
        st.markdown(f"### 💵 {t('সদস্যের টাকা জমা', 'Member Deposit')}")
        tab1, tab2 = st.tabs([f"✅ {t('জমা দিয়েছে', 'Paid')}", f"❌ {t('জমা দেয়নি', 'Unpaid')}"])
        
        with tab1:
            paid = get_paid_members()
            if paid:
                table_data = []
                for pm in paid:
                    table_data.append({
                        t('নাম', 'Name'): pm['name'],
                        t('আইডি', 'ID'): pm['id'],
                        t('মোবাইল', 'Mobile'): pm['phone'],
                        t('জমা', 'Savings'): f"{float(pm.get('total_savings', 0)):,.0f}"
                    })
                df = pd.DataFrame(table_data)
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.info(t("কেউ জমা দেয়নি", "No one paid"))
        
        with tab2:
            unpaid = get_unpaid_members()
            if unpaid:
                for um in unpaid:
                    savings_val = float(um.get('total_savings', 0))
                    monthly_val = float(um.get('monthly_savings', 500))
                    with st.expander(f"❌ {um['name']} ({um['id']})"):
                        deposit_date = st.date_input(t("জমার তারিখ", "Date"), datetime.now(), key=f"date_{um['id']}")
                        day = deposit_date.day
                        month = deposit_date.month
                        year = deposit_date.year
                        c1, c2 = st.columns(2)
                        with c1:
                            months_count = st.number_input(t("কত মাস", "Months"), 1, 12, 1, key=f"count_{um['id']}")
                        with c2:
                            late_fee = st.number_input(t("লেট ফি", "Late Fee"), 0.0, step=10.0, key=f"fee_{um['id']}")
                        total = monthly_val * months_count + late_fee
                        
                        if st.button(f"✅ {t('জমা নিন', 'Deposit')}", key=f"dep_{um['id']}", type="primary"):
                            today_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            full_date = f"{day} {BANGLA_MONTHS[month]} {year}"
                            full_date_en = f"{day} {ENGLISH_MONTHS[month]} {year}"
                            date_iso = f"{year}-{month:02d}-{day:02d}"
                            
                            for i in range(int(months_count)):
                                add_transaction({
                                    'member_id': um['id'], 'amount': monthly_val, 'transaction_type': 'deposit',
                                    'day': day, 'month': month, 'year': year,
                                    'month_name': BANGLA_MONTHS[month], 'month_name_en': ENGLISH_MONTHS[month],
                                    'full_date': full_date, 'full_date_en': full_date_en, 'date_iso': date_iso,
                                    'late_fee': late_fee if i == 0 else 0, 'created_at': today_str
                                })
                            
                            new_savings = savings_val + total
                            update_member(um['id'], {'total_savings': new_savings})
                            
                            st.success(f"✅ {total:,.0f} {t('টাকা জমা হয়েছে', 'deposited')}!")
                            st.balloons()
                            time.sleep(1)
                            st.rerun()
            else:
                st.success(f"🎉 {t('সবাই জমা দিয়েছেন', 'All paid')}!")
    
    elif f"💰 {t('লেনদেন ব্যবস্থাপনা', 'Transactions')}" in menu:
        st.markdown(f"### 💰 {t('লেনদেন ব্যবস্থাপনা', 'Transaction Management')}")
        members = get_all_members()
        if members:
            options = {f"{m['name']} ({m['id']})": m['id'] for m in members}
            selected = st.selectbox(t("সদস্য নির্বাচন", "Select Member"), list(options.keys()))
            if selected:
                member_id = options[selected]
                member = get_member_by_id(member_id)
                if member:
                    st.success(f"👤 {member['name']} | 💰 {float(member.get('total_savings', 0)):,.0f} {t('টাকা', 'Taka')}")
                    trans = get_member_transactions(member_id)
                    if trans:
                        table_data = []
                        for tr in trans:
                            table_data.append({
                                t('তারিখ', 'Date'): tr['full_date'],
                                t('পরিমাণ', 'Amount'): f"{float(tr['amount']):,.0f}",
                                t('মাস', 'Month'): tr['month_name'],
                                t('সাল', 'Year'): str(tr['year']),
                                t('লেট ফি', 'Late Fee'): f"{float(tr.get('late_fee', 0)):,.0f}"
                            })
                        df = pd.DataFrame(table_data)
                        st.dataframe(df, use_container_width=True, hide_index=True)
                        
                        st.markdown("---")
                        st.markdown(f"#### ✏️ {t('লেনদেন এডিট/ডিলিট', 'Edit/Delete')}")
                        for tr in trans:
                            col1, col2, col3 = st.columns([4, 1, 1])
                            with col1:
                                st.write(f"{tr['full_date']} - {float(tr['amount']):,.0f} {t('টাকা', 'Taka')}")
                            with col2:
                                if st.button("✏️", key=f"edit_{tr['id']}"):
                                    st.session_state[f"edit_trans_{tr['id']}"] = True
                            with col3:
                                if st.button("🗑️", key=f"del_{tr['id']}"):
                                    st.session_state[f"confirm_del_{tr['id']}"] = True
                            
                            if st.session_state.get(f"confirm_del_{tr['id']}"):
                                st.warning(t("নিশ্চিত?", "Confirm?"))
                                cy, cn = st.columns(2)
                                with cy:
                                    if st.button("✅", key=f"yes_{tr['id']}"):
                                        current_savings = float(member.get('total_savings', 0))
                                        update_member(member_id, {'total_savings': current_savings - float(tr['amount'])})
                                        delete_transaction(tr['id'])
                                        st.success("✅")
                                        del st.session_state[f"confirm_del_{tr['id']}"]
                                        st.rerun()
                                with cn:
                                    if st.button("❌", key=f"no_{tr['id']}"):
                                        del st.session_state[f"confirm_del_{tr['id']}"]
                                        st.rerun()
                            
                            if st.session_state.get(f"edit_trans_{tr['id']}"):
                                with st.form(f"edit_{tr['id']}"):
                                    new_amt = st.number_input(t("টাকা", "Amount"), value=float(tr['amount']), step=50.0)
                                    if st.form_submit_button("💾"):
                                        diff = new_amt - float(tr['amount'])
                                        current_savings = float(member.get('total_savings', 0))
                                        update_member(member_id, {'total_savings': current_savings + diff})
                                        update_transaction(tr['id'], {'amount': new_amt})
                                        st.success("✅")
                                        del st.session_state[f"edit_trans_{tr['id']}"]
                                        st.rerun()
                    else:
                        st.info(t("কোনো লেনদেন নেই", "No transactions"))
        else:
            st.info(t("কোনো সদস্য নেই", "No members"))
    
    elif f"🔗 {t('সদস্য লিংক', 'Member Links')}" in menu:
        st.markdown(f"### 🔗 {t('সদস্য লিংক', 'Member Links')}")
        members = get_all_members()
        app_url = get_app_url()
        for m in members:
            link = f"{app_url}/?member={m['id']}"
            st.markdown(f"""
            <div class="member-card">
                <h4>👤 {m['name']} ({m['id']})</h4>
                <p>📱 {m['phone']} | 🔑 {m['password']}</p>
                <p>🔗 <code>{link}</code></p>
            </div>""", unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f'<button onclick="navigator.clipboard.writeText(\'{link}\')" style="background:#238636; color:white; border:none; padding:8px; border-radius:5px; width:100%;">📋 {t("লিংক কপি", "Copy Link")}</button>', unsafe_allow_html=True)
            with c2:
                st.markdown(f'<button onclick="navigator.clipboard.writeText(\'{m["password"]}\')" style="background:#238636; color:white; border:none; padding:8px; border-radius:5px; width:100%;">📋 {t("পাসওয়ার্ড কপি", "Copy Pass")}</button>', unsafe_allow_html=True)
            st.markdown("---")
    
    elif f"💸 {t('খরচ ব্যবস্থাপনা', 'Expenses')}" in menu:
        st.markdown(f"### 💸 {t('খরচ ব্যবস্থাপনা', 'Expense Management')}")
        tab1, tab2 = st.tabs([f"➕ {t('নতুন খরচ', 'New')}", f"📋 {t('তালিকা', 'List')}"])
        with tab1:
            with st.form("exp_form"):
                desc = st.text_input(t("বিবরণ", "Description"))
                amt = st.number_input(t("টাকা", "Amount"), 0.0, step=10.0)
                cat = st.selectbox(t("ক্যাটাগরি", "Category"), ["অফিস", "চা-নাস্তা", "স্টেশনারি", "পরিবহন", "অন্যান্য"])
                if st.form_submit_button("💾"):
                    if desc and amt > 0:
                        add_expense({'description': desc, 'amount': amt, 'date': datetime.now().strftime("%Y-%m-%d"), 'category': cat})
                        st.success(f"✅ {amt:,.0f} {t('টাকা যোগ', 'Added')}!")
                        st.rerun()
        with tab2:
            expenses = get_all_expenses()
            if expenses:
                table_data = []
                for exp in expenses[:50]:
                    table_data.append({
                        t('তারিখ', 'Date'): exp['date'],
                        t('ক্যাটাগরি', 'Category'): exp['category'],
                        t('বিবরণ', 'Description'): exp['description'][:40],
                        t('পরিমাণ', 'Amount'): f"{float(exp['amount']):,.0f}"
                    })
                df = pd.DataFrame(table_data)
                st.dataframe(df, use_container_width=True, hide_index=True)
                
                st.markdown("---")
                for exp in expenses[:50]:
                    col1, col2 = st.columns([5, 1])
                    with col1:
                        st.write(f"{exp['date']} - {exp['description']} - {float(exp['amount']):,.0f}")
                    with col2:
                        if st.button("🗑️", key=f"de_{exp['id']}"):
                            delete_expense(exp['id'])
                            st.rerun()
                
                total_exp = sum(float(e['amount']) for e in expenses)
                st.metric(f"📊 {t('মোট খরচ', 'Total')}", f"{total_exp:,.0f}")
    
    elif f"🏧 {t('ফান্ড ব্যবস্থাপনা', 'Fund Management')}" in menu:
        st.markdown(f"### 🏧 {t('ফান্ড ব্যবস্থাপনা', 'Fund Management')}")
        cash = get_cash_balance()
        fund_balance = get_fund_balance()
        st.info(f"💰 {t('ক্যাশ ব্যালেন্স', 'Cash')}: {cash:,.0f} | 🏦 {t('ফান্ড', 'Fund')}: {fund_balance:,.0f}")
        
        tab1, tab2, tab3 = st.tabs([f"➕ {t('জমা', 'Deposit')}", f"➖ {t('উত্তোলন', 'Withdrawal')}", f"📋 {t('ইতিহাস', 'History')}"])
        
        with tab1:
            with st.form("fund_deposit"):
                amount = st.number_input(t("পরিমাণ", "Amount"), 0.0, step=100.0)
                desc = st.text_area(t("বিবরণ", "Description"))
                if st.form_submit_button("✅"):
                    if amount > 0 and desc:
                        add_fund_transaction({
                            'type': 'deposit', 'amount': amount, 'description': desc,
                            'date': datetime.now().strftime("%Y-%m-%d"),
                            'previous_balance': fund_balance, 'current_balance': fund_balance + amount,
                            'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
                        st.success(f"✅ {amount:,.0f} {t('জমা', 'deposited')}!")
                        st.balloons()
                        time.sleep(1)
                        st.rerun()
        
        with tab2:
            with st.form("fund_withdraw"):
                amount = st.number_input(t("পরিমাণ", "Amount"), 0.0, step=100.0)
                desc = st.text_area(t("বিবরণ", "Description"))
                date = st.date_input(t("তারিখ", "Date"), datetime.now())
                if st.form_submit_button("✅"):
                    if amount > 0 and amount <= fund_balance and desc:
                        add_fund_transaction({
                            'type': 'withdrawal', 'amount': amount, 'description': desc,
                            'date': date.strftime("%Y-%m-%d"),
                            'previous_balance': fund_balance, 'current_balance': fund_balance - amount,
                            'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
                        add_withdrawal({
                            'date': date.strftime("%Y-%m-%d"), 'amount': amount, 'description': desc,
                            'withdrawn_by': 'Admin', 'previous_balance': fund_balance, 'current_balance': fund_balance - amount,
                            'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
                        st.success(f"✅ {amount:,.0f} {t('উত্তোলন', 'withdrawn')}!")
                        st.rerun()
                    else:
                        st.error(t("❌ সঠিক পরিমাণ দিন", "❌ Invalid amount"))
        
        with tab3:
            fund_trans = get_fund_transactions()
            if fund_trans:
                table_data = []
                for ft in fund_trans[:30]:
                    table_data.append({
                        t('তারিখ', 'Date'): ft['date'],
                        t('ধরন', 'Type'): "➕ জমা" if ft['type'] == 'deposit' else "➖ উত্তোলন",
                        t('পরিমাণ', 'Amount'): f"{float(ft['amount']):,.0f}",
                        t('বিবরণ', 'Description'): ft['description'][:30],
                        t('ব্যালেন্স', 'Balance'): f"{float(ft['current_balance']):,.0f}"
                    })
                df = pd.DataFrame(table_data)
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.info(t("কোনো লেনদেন নেই", "No transactions"))
    
    elif f"📊 {t('রিপোর্ট', 'Reports')}" in menu:
        st.markdown(f"### 📊 {t('রিপোর্ট', 'Reports')}")
        tab1, tab2 = st.tabs([f"📈 {t('মাসিক', 'Monthly')}", f"⚠️ {t('বকেয়া', 'Due')}"])
        with tab1:
            monthly = get_monthly_report()
            if monthly:
                df = pd.DataFrame(monthly)
                df['amount'] = df['amount'].apply(lambda x: f"{float(x):,.0f}")
                df.columns = [t('মাস', 'Month'), t('জমা', 'Collection')]
                st.bar_chart(df.set_index(t('মাস', 'Month')))
                st.dataframe(df, use_container_width=True, hide_index=True)
        with tab2:
            unpaid = get_unpaid_members()
            if unpaid:
                table_data = []
                for mu in unpaid:
                    table_data.append({
                        t('নাম', 'Name'): mu['name'],
                        t('মোবাইল', 'Mobile'): mu['phone'],
                        t('কিস্তি', 'Monthly'): f"{float(mu.get('monthly_savings', 500)):,.0f}",
                        t('জমা', 'Savings'): f"{float(mu.get('total_savings', 0)):,.0f}"
                    })
                df = pd.DataFrame(table_data)
                st.dataframe(df, use_container_width=True, hide_index=True)
    
    elif f"📥 {t('পিডিএফ ডাউনলোড', 'PDF Download')}" in menu:
        st.markdown(f"### 📥 {t('পিডিএফ ডাউনলোড', 'PDF Download')}")
        report_type = st.selectbox(t("রিপোর্ট", "Report"), ["সদস্য তালিকা", "সব লেনদেন", "নির্দিষ্ট সদস্য"])
        if "নির্দিষ্ট" in report_type:
            members = get_all_members()
            if members:
                options = {f"{m['name']} ({m['id']})": m['id'] for m in members}
                selected = st.selectbox(t("সদস্য", "Member"), list(options.keys()))
                if st.button("📥 PDF", type="primary"):
                    pdf = generate_pdf_transactions(options[selected])
                    st.download_button("📥 Download", pdf, f"{options[selected]}_transactions.pdf", "application/pdf")
        else:
            if st.button("📥 PDF", type="primary"):
                if "সদস্য" in report_type:
                    pdf = generate_pdf_member_list()
                    st.download_button("📥 Download", pdf, "member_list.pdf", "application/pdf")
                else:
                    pdf = generate_pdf_transactions()
                    st.download_button("📥 Download", pdf, "all_transactions.pdf", "application/pdf")
    
    elif f"📧 {t('ইমেইল টেস্ট', 'Email Test')}" in menu:
        st.markdown(f"### 📧 {t('ইমেইল টেস্ট', 'Email Test')}")
        test_email = st.text_input(t("ইমেইল", "Email"), placeholder="example@gmail.com")
        if st.button("📨 টেস্ট", type="primary"):
            if send_test_email(test_email):
                st.success("✅ পাঠানো হয়েছে!")
            else:
                st.error("❌ ব্যর্থ")
    
    elif f"🎲 {t('লটারি', 'Lottery')}" in menu:
        st.markdown(f"### 🎲 {t('লটারি', 'Lottery')}")
        if st.button("🎲 বিজয়ী নির্বাচন", type="primary"):
            winner = pick_lottery_winner()
            if winner:
                st.balloons()
                st.success(f"🎉 {winner['name']} ({winner['id']})")
            else:
                st.error("কোনো সদস্য নেই")

# ==================== মেম্বার প্যানেল ====================
def member_login_page(member_id):
    apply_dark_theme()
    member = get_member_by_id(member_id)
    if not member:
        st.error(t("❌ সদস্য পাওয়া যায়নি", "❌ Member not found"))
        return
    st.markdown(f"""
    <div class="somiti-header">
        <h1>🌾 {SOMITI_NAME} 🌾</h1>
        <p>{t('সদস্য লগইন', 'Member Login')}</p>
    </div>
    """, unsafe_allow_html=True)
    st.markdown(f"### 🔐 {t('স্বাগতম', 'Welcome')}, {member['name']}")
    email = st.text_input(f"📧 {t('ইমেইল', 'Email')}")
    password = st.text_input(f"🔑 {t('পাসওয়ার্ড', 'Password')}", type="password")
    if st.button(t("প্রবেশ করুন", "Login"), type="primary"):
        if email == member.get('email') and password == member.get('password'):
            st.session_state.member_logged_in = True
            st.session_state.member_id = member_id
            st.rerun()
        else:
            st.error(t("❌ ভুল ইমেইল বা পাসওয়ার্ড", "❌ Wrong email or password"))

def member_dashboard_view():
    apply_dark_theme()
    member = get_member_by_id(st.session_state.member_id)
    if not member:
        st.error("Member not found")
        return
    
    total_savings = float(member.get('total_savings', 0))
    monthly = float(member.get('monthly_savings', 500))
    
    st.markdown(f"""
    <div class="somiti-header">
        <h1>🌾 {SOMITI_NAME} 🌾</h1>
        <p>{t('সদস্য ড্যাশবোর্ড', 'Member Dashboard')}</p>
    </div>
    <div class="total-box">
        <h2>💰 {total_savings:,.0f} {t('টাকা', 'Taka')}</h2>
        <p>{t('আপনার মোট জমা', 'Your Total Savings')}</p>
    </div>
    """, unsafe_allow_html=True)
    
    with st.sidebar:
        st.markdown(f"### 👤 {member['name']}")
        st.caption(f"🆔 {member['id']} | 📱 {member['phone']}")
        if st.button(f"🚪 {t('লগআউট', 'Logout')}"):
            del st.session_state.member_logged_in
            del st.session_state.member_id
            st.rerun()
    
    tab1, tab2, tab3 = st.tabs(["📊 ড্যাশবোর্ড", "🔐 পাসওয়ার্ড", "📥 রিপোর্ট"])
    
    with tab1:
        col1, col2 = st.columns(2)
        col1.metric("বর্তমান জমা", f"{total_savings:,.0f} টাকা")
        col2.metric("মাসিক কিস্তি", f"{monthly:,.0f} টাকা")
        
        current = datetime.now()
        trans = get_member_transactions(member['id'])
        paid = sum(float(t['amount']) for t in trans if t['month'] == current.month and t['year'] == current.year)
        
        if paid >= monthly:
            st.success(f"✅ {BANGLA_MONTHS[current.month]} {current.year} মাসের কিস্তি পরিশোধ করেছেন")
        else:
            st.warning(f"⚠️ বকেয়া: {monthly - paid:,.0f} টাকা")
        
        st.markdown("---")
        st.markdown("#### 📋 লেনদেন ইতিহাস")
        if trans:
            table_data = []
            for tr in trans[:20]:
                table_data.append({
                    "তারিখ": tr['full_date'],
                    "পরিমাণ": f"{float(tr['amount']):,.0f}",
                    "মাস": tr['month_name']
                })
            df = pd.DataFrame(table_data)
            st.dataframe(df, use_container_width=True, hide_index=True)
    
    with tab2:
        new_pass = st.text_input("নতুন পাসওয়ার্ড", type="password")
        confirm = st.text_input("নিশ্চিত করুন", type="password")
        if st.button("আপডেট", type="primary"):
            if new_pass and new_pass == confirm:
                update_member(member['id'], {'password': new_pass})
                st.success("✅ পরিবর্তন হয়েছে!")
            else:
                st.error("❌ পাসওয়ার্ড মিলছে না")
    
    with tab3:
        if st.button("📥 পিডিএফ ডাউনলোড", type="primary"):
            pdf = generate_pdf_transactions(member['id'])
            st.download_button("📥 Download PDF", pdf, f"{member['id']}_transactions.pdf", "application/pdf")

# ==================== মেইন ====================
def main():
    check_and_archive_old_data()
    
    if 'member_logged_in' not in st.session_state:
        st.session_state.member_logged_in = False
    if 'admin_logged_in' not in st.session_state:
        st.session_state.admin_logged_in = False
    if 'language' not in st.session_state:
        st.session_state.language = 'bn'
    
    if member_login_id:
        if not st.session_state.member_logged_in:
            member_login_page(member_login_id)
        else:
            member_dashboard_view()
        return
    
    if not st.session_state.admin_logged_in:
        admin_login_page()
    else:
        admin_panel()

if __name__ == "__main__":
    main()
