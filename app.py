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

# ==================== ফাইল পাথ ====================
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

MEMBER_COLS = ['id', 'name', 'phone', 'email', 'password', 'total_savings', 'monthly_savings', 'join_date', 'status']
TRANSACTION_COLS = ['id', 'member_id', 'amount', 'transaction_type', 'day', 'month', 'year',
                    'month_name', 'month_name_en', 'full_date', 'full_date_en', 'date_iso', 'late_fee', 'created_at']
EXPENSE_COLS = ['id', 'description', 'amount', 'date', 'category']
WITHDRAWAL_COLS = ['id', 'date', 'amount', 'description', 'withdrawn_by', 'previous_balance', 'current_balance', 'created_at']
FUND_COLS = ['id', 'type', 'amount', 'description', 'date', 'previous_balance', 'current_balance', 'created_at']

# ==================== CSV হেল্পার ====================
def load_df(file_path, columns):
    if os.path.exists(file_path):
        try:
            df = pd.read_csv(file_path, encoding='utf-8')
            for col in columns:
                if col not in df.columns:
                    df[col] = ''
            return df
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

# ==================== ইউটিলিটি ====================
def generate_member_id():
    df = load_df(MEMBERS_CSV, MEMBER_COLS)
    if len(df) == 0:
        return "10001"
    max_id = max([int(str(x)) for x in df['id'].tolist()])
    return str(max_id + 1)

def generate_password():
    return ''.join(random.choices(string.digits, k=6))

def fmt(val):
    try:
        return f"{int(float(val)):,}"
    except:
        return "0"

def get_total_savings():
    df = load_df(MEMBERS_CSV, MEMBER_COLS)
    if len(df) == 0:
        return 0
    active = df[df['status'] == 'active']
    return int(active['total_savings'].astype(float).sum())

def get_total_expenses():
    df = load_df(EXPENSES_CSV, EXPENSE_COLS)
    return int(df['amount'].astype(float).sum())

def get_total_withdrawals():
    df = load_df(WITHDRAWALS_CSV, WITHDRAWAL_COLS)
    return int(df['amount'].astype(float).sum())

def get_fund_balance():
    df = load_df(FUND_CSV, FUND_COLS)
    deposits = df[df['type'] == 'deposit']['amount'].astype(float).sum()
    withdrawals = df[df['type'] == 'withdrawal']['amount'].astype(float).sum()
    return int(deposits - withdrawals)

def get_cash_balance():
    return int(get_total_savings() + get_fund_balance() - get_total_expenses() - get_total_withdrawals())

def get_all_members():
    df = load_df(MEMBERS_CSV, MEMBER_COLS)
    return df.to_dict('records')

def get_member_by_id(member_id):
    df = load_df(MEMBERS_CSV, MEMBER_COLS)
    match = df[df['id'].astype(str) == str(member_id)]
    if len(match) > 0:
        return match.iloc[0].to_dict()
    return None

def add_member(data):
    data['id'] = generate_member_id()
    data['total_savings'] = int(data.get('total_savings', 0))
    data['monthly_savings'] = int(data.get('monthly_savings', 500))
    data['join_date'] = datetime.now().strftime("%Y-%m-%d")
    data['status'] = 'active'
    append_row(MEMBERS_CSV, data, MEMBER_COLS)
    return data['id']

def update_member(member_id, updates):
    df = load_df(MEMBERS_CSV, MEMBER_COLS)
    idx = df[df['id'].astype(str) == str(member_id)].index
    if len(idx) > 0:
        for k, v in updates.items():
            df.loc[idx[0], k] = v
        save_df(df, MEMBERS_CSV)
        return True
    return False

def delete_member(member_id):
    mid = str(member_id)
    # Delete transactions
    tdf = load_df(TRANSACTIONS_CSV, TRANSACTION_COLS)
    tdf = tdf[tdf['member_id'].astype(str) != mid]
    save_df(tdf, TRANSACTIONS_CSV)
    # Delete member
    mdf = load_df(MEMBERS_CSV, MEMBER_COLS)
    mdf = mdf[mdf['id'].astype(str) != mid]
    save_df(mdf, MEMBERS_CSV)
    return True

def add_transaction(data):
    data['id'] = get_next_id(TRANSACTIONS_CSV, TRANSACTION_COLS)
    data['amount'] = int(data['amount'])
    data['late_fee'] = int(data.get('late_fee', 0))
    append_row(TRANSACTIONS_CSV, data, TRANSACTION_COLS)

def update_transaction(trans_id, updates):
    df = load_df(TRANSACTIONS_CSV, TRANSACTION_COLS)
    idx = df[df['id'] == int(trans_id)].index
    if len(idx) > 0:
        for k, v in updates.items():
            df.loc[idx[0], k] = int(v) if k in ['amount', 'late_fee'] else v
        save_df(df, TRANSACTIONS_CSV)
        return True
    return False

def delete_transaction(trans_id):
    df = load_df(TRANSACTIONS_CSV, TRANSACTION_COLS)
    df = df[df['id'] != int(trans_id)]
    save_df(df, TRANSACTIONS_CSV)
    return True

def get_member_transactions(member_id):
    df = load_df(TRANSACTIONS_CSV, TRANSACTION_COLS)
    mem_df = df[df['member_id'].astype(str) == str(member_id)]
    return mem_df.sort_values(['year', 'month', 'day'], ascending=False).to_dict('records')

def add_expense(data):
    data['id'] = get_next_id(EXPENSES_CSV, EXPENSE_COLS)
    data['amount'] = int(data['amount'])
    append_row(EXPENSES_CSV, data, EXPENSE_COLS)

def delete_expense(exp_id):
    df = load_df(EXPENSES_CSV, EXPENSE_COLS)
    df = df[df['id'] != int(exp_id)]
    save_df(df, EXPENSES_CSV)
    return True

def get_paid_members():
    current = datetime.now()
    trans_df = load_df(TRANSACTIONS_CSV, TRANSACTION_COLS)
    mem_df = load_df(MEMBERS_CSV, MEMBER_COLS)
    paid_ids = trans_df[(trans_df['month'] == current.month) & (trans_df['year'] == current.year)]['member_id'].astype(str).unique()
    return mem_df[mem_df['id'].astype(str).isin(paid_ids) & (mem_df['status'] == 'active')].to_dict('records')

def get_unpaid_members():
    current = datetime.now()
    trans_df = load_df(TRANSACTIONS_CSV, TRANSACTION_COLS)
    mem_df = load_df(MEMBERS_CSV, MEMBER_COLS)
    active = mem_df[mem_df['status'] == 'active']
    paid_ids = trans_df[(trans_df['month'] == current.month) & (trans_df['year'] == current.year)]['member_id'].astype(str).unique()
    return active[~active['id'].astype(str).isin(paid_ids)].to_dict('records')

# ==================== UI থিম ====================
def apply_dark_theme():
    st.markdown("""
    <style>
    .stApp { background: #0d1117; color: #c9d1d9; }
    .somiti-header { background: linear-gradient(135deg, #1a5276 0%, #2980b9 100%); padding: 20px; border-radius: 15px; text-align: center; margin-bottom: 20px; }
    .total-box { background: #1e8449; padding: 15px; border-radius: 10px; text-align: center; margin-bottom: 10px; }
    .cash-box { background: #d35400; padding: 15px; border-radius: 10px; text-align: center; margin-bottom: 10px; }
    .kpi-card { background: #21262d; padding: 15px; border-radius: 10px; text-align: center; border: 1px solid #30363d; }
    </style>
    """, unsafe_allow_html=True)

def show_admin_header():
    total = get_total_savings()
    cash = get_cash_balance()
    st.markdown(f'<div class="somiti-header"><h1>🌾 {SOMITI_NAME} 🌾</h1></div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    c1.markdown(f'<div class="total-box"><h2>💰 {fmt(total)}</h2><p>মোট সঞ্চয়</p></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="cash-box"><h2>💵 {fmt(cash)}</h2><p>ক্যাশ ব্যালেন্স</p></div>', unsafe_allow_html=True)

# ==================== এডমিন প্যানেল ====================
def admin_panel():
    apply_dark_theme()
    show_admin_header()
    
    with st.sidebar:
        st.markdown("### 📋 এডমিন মেনু")
        menu = st.radio("নেভিগেশন", [
            "🏠 ড্যাশবোর্ড", "➕ নতুন সদস্য", "✏️ সদস্য ব্যবস্থাপনা", 
            "💵 টাকা জমা", "🔄 লেনদেন পরিবর্তন", "💸 ব্যয় হিসাব", 
            "🏧 ফান্ড ব্যবস্থাপনা", "📊 রিপোর্ট", "🚪 লগআউট"
        ])

    if "লগআউট" in menu:
        st.session_state.admin_logged_in = False
        st.rerun()

    elif "ড্যাশবোর্ড" in menu:
        st.markdown("### 🏠 ড্যাশবোর্ড")
        col1, col2, col3 = st.columns(3)
        members = get_all_members()
        active_count = len([m for m in members if m['status'] == 'active'])
        with col1: st.markdown(f'<div class="kpi-card"><h3>সদস্য</h3><h2>{active_count}</h2></div>', unsafe_allow_html=True)
        with col2: st.markdown(f'<div class="kpi-card"><h3>মোট জমা</h3><h2>{fmt(get_total_savings())}</h2></div>', unsafe_allow_html=True)
        with col3: st.markdown(f'<div class="kpi-card"><h3>বকেয়া</h3><h2>{len(get_unpaid_members())}</h2></div>', unsafe_allow_html=True)

    elif "নতুন সদস্য" in menu:
        st.markdown("### ➕ নতুন সদস্য নিবন্ধন")
        with st.form("new_member"):
            name = st.text_input("নাম *")
            phone = st.text_input("মোবাইল *")
            monthly = st.number_input("মাসিক কিস্তি", value=500)
            if st.form_submit_button("সংরক্ষণ করুন"):
                if name and phone:
                    mid = add_member({'name': name, 'phone': phone, 'monthly_savings': int(monthly), 'password': generate_password()})
                    st.success(f"সদস্য আইডি: {mid} তৈরি হয়েছে!")
                else: st.error("নাম ও মোবাইল দিন।")

    elif "সদস্য ব্যবস্থাপনা" in menu:
        st.markdown("### ✏️ সদস্য তালিকা")
        members = get_all_members()
        for m in members:
            with st.expander(f"👤 {m['name']} ({m['id']})"):
                st.write(f"মোবাইল: {m['phone']} | স্থিতি: {m['status']}")
                if st.button("ডিলিট করুন", key=f"del_{m['id']}"):
                    delete_member(m['id'])
                    st.rerun()

    elif "টাকা জমা" in menu:
        st.markdown("### 💵 টাকা জমা নিন")
        unpaid = get_unpaid_members()
        for um in unpaid:
            with st.expander(f"❌ {um['name']} ({um['id']})"):
                monthly = int(float(um['monthly_savings']))
                amt = st.number_input("টাকার পরিমাণ", value=monthly, key=f"amt_{um['id']}")
                if st.button(f"জমা নিন", key=f"btn_{um['id']}"):
                    today = datetime.now()
                    add_transaction({
                        'member_id': um['id'], 'amount': int(amt), 'transaction_type': 'deposit',
                        'day': today.day, 'month': today.month, 'year': today.year,
                        'month_name': BANGLA_MONTHS[today.month], 'full_date': f"{today.day} {BANGLA_MONTHS[today.month]} {today.year}",
                        'created_at': today.strftime("%Y-%m-%d %H:%M:%S")
                    })
                    # Update Total Savings
                    mdf = load_df(MEMBERS_CSV, MEMBER_COLS)
                    mdf.loc[mdf['id'].astype(str) == str(um['id']), 'total_savings'] = int(float(um['total_savings'])) + amt
                    save_df(mdf, MEMBERS_CSV)
                    st.success("জমা সম্পন্ন!")
                    time.sleep(1)
                    st.rerun()

    # ==================== লেনদেন পরিবর্তন (FIXED) ====================
    elif "লেনদেন পরিবর্তন" in menu:
        st.markdown("### 🔄 লেনদেন পরিবর্তন ও ডিলিট")
        members = [m for m in get_all_members() if m['status'] == 'active']
        options = ["— সদস্য নির্বাচন করুন —"] + [f"{m['name']} ({m['id']})" for m in members]
        
        chosen = st.selectbox("সদস্য নির্বাচন করুন", options)
        
        if not chosen.startswith("—"):
            sel_id = chosen.split("(")[-1].rstrip(")")
            sel_member = get_member_by_id(sel_id)
            
            if sel_member:
                st.markdown(f"**নির্বাচিত সদস্য:** {sel_member['name']} | **মোট জমা:** {fmt(sel_member['total_savings'])} টাকা")
                trans = get_member_transactions(sel_id)
                
                if not trans:
                    st.info("এই সদস্যের কোনো লেনদেন নেই।")
                else:
                    t_options = [f"ID: {tr['id']} | {tr['full_date']} | {fmt(tr['amount'])} টাকা" for tr in trans]
                    sel_t_label = st.selectbox("কোন লেনদেনটি পরিবর্তন করবেন?", t_options)
                    
                    # Extract transaction data
                    sel_t = trans[t_options.index(sel_t_label)]
                    t_id = sel_t['id']
                    old_amt = int(float(sel_t['amount']))
                    
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("✏️ এডিট", use_container_width=True):
                            st.session_state['edit_t'] = t_id
                    with c2:
                        if st.button("🗑️ ডিলিট", use_container_width=True):
                            st.session_state['del_t'] = t_id

                    if st.session_state.get('edit_t') == t_id:
                        with st.form("edit_form"):
                            new_amt = st.number_input("নতুন পরিমাণ", value=old_amt)
                            if st.form_submit_button("আপডেট"):
                                diff = new_amt - old_amt
                                # Update member balance
                                mdf = load_df(MEMBERS_CSV, MEMBER_COLS)
                                cur_sav = int(float(mdf.loc[mdf['id'].astype(str) == str(sel_id), 'total_savings'].values[0]))
                                mdf.loc[mdf['id'].astype(str) == str(sel_id), 'total_savings'] = cur_sav + diff
                                save_df(mdf, MEMBERS_CSV)
                                # Update transaction
                                update_transaction(t_id, {'amount': int(new_amt)})
                                st.success("লেনদেন আপডেট হয়েছে!")
                                del st.session_state['edit_t']
                                time.sleep(1)
                                st.rerun()

                    if st.session_state.get('del_t') == t_id:
                        st.warning("আপনি কি নিশ্চিত?")
                        if st.button("হ্যাঁ, ডিলিট করুন"):
                            # Reduce member balance
                            mdf = load_df(MEMBERS_CSV, MEMBER_COLS)
                            cur_sav = int(float(mdf.loc[mdf['id'].astype(str) == str(sel_id), 'total_savings'].values[0]))
                            mdf.loc[mdf['id'].astype(str) == str(sel_id), 'total_savings'] = max(0, cur_sav - old_amt)
                            save_df(mdf, MEMBERS_CSV)
                            # Delete transaction
                            delete_transaction(t_id)
                            st.success("লেনদেন মুছে ফেলা হয়েছে!")
                            del st.session_state['del_t']
                            time.sleep(1)
                            st.rerun()
            else:
                st.error("সদস্যের তথ্য পাওয়া যায়নি।")

    elif "ব্যয় হিসাব" in menu:
        st.markdown("### 💸 ব্যয় হিসাব")
        with st.form("expense"):
            desc = st.text_input("বিবরণ")
            amt = st.number_input("পরিমাণ")
            if st.form_submit_button("খরচ যোগ করুন"):
                add_expense({'description': desc, 'amount': int(amt), 'date': datetime.now().strftime("%Y-%m-%d"), 'category': 'General'})
                st.success("খরচ যোগ হয়েছে!")
        
        exps = load_df(EXPENSES_CSV, EXPENSE_COLS)
        st.dataframe(exps, use_container_width=True)

    elif "ফান্ড ব্যবস্থাপনা" in menu:
        st.markdown("### 🏧 ফান্ড ব্যবস্থাপনা")
        st.write(f"বর্তমান ফান্ড: {fmt(get_fund_balance())} টাকা")
        with st.form("fund"):
            f_type = st.selectbox("ধরণ", ["deposit", "withdrawal"])
            f_amt = st.number_input("পরিমাণ")
            f_desc = st.text_input("বিবরণ")
            if st.form_submit_button("সাবমিট"):
                append_row(FUND_CSV, {
                    'id': get_next_id(FUND_CSV, FUND_COLS), 'type': f_type, 'amount': int(f_amt),
                    'description': f_desc, 'date': datetime.now().strftime("%Y-%m-%d"),
                    'current_balance': get_fund_balance() + (f_amt if f_type == 'deposit' else -f_amt)
                }, FUND_COLS)
                st.rerun()

def admin_login():
    apply_dark_theme()
    st.markdown('<div class="somiti-header"><h1>🌾 এডমিন লগইন 🌾</h1></div>', unsafe_allow_html=True)
    phone = st.text_input("মোবাইল")
    pwd = st.text_input("পাসওয়ার্ড", type="password")
    if st.button("প্রবেশ করুন"):
        if phone == ADMIN_MOBILE and pwd == ADMIN_PASSWORD:
            st.session_state.admin_logged_in = True
            st.rerun()
        else: st.error("ভুল তথ্য!")

def main():
    if 'admin_logged_in' not in st.session_state: st.session_state.admin_logged_in = False
    if st.session_state.admin_logged_in: admin_panel()
    else: admin_login()

if __name__ == "__main__":
    main()
