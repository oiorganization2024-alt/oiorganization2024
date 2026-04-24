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
import threading
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

# ==================== সেটিংস ====================
def load_settings():
    if os.path.exists(SETTINGS_JSON):
        with open(SETTINGS_JSON, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"start_date": SOMITI_START_DATE}

def save_settings(settings):
    with open(SETTINGS_JSON, 'w', encoding='utf-8') as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)

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
        for f, cols in [(MEMBERS_CSV, MEMBER_COLS), (TRANSACTIONS_CSV, TRANSACTION_COLS),
                        (EXPENSES_CSV, EXPENSE_COLS), (WITHDRAWALS_CSV, WITHDRAWAL_COLS), (FUND_CSV, FUND_COLS)]:
            pd.DataFrame(columns=cols).to_csv(f, index=False)
        settings['start_date'] = datetime.now().strftime("%Y-%m-%d")
        save_settings(settings)

# ==================== ইমেইল সিস্টেম ====================
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def _eh():  # email header
    return (f'<div style="background:linear-gradient(135deg,#1a5276,#2980b9);'
            f'padding:24px 30px;border-radius:10px 10px 0 0;text-align:center;">'
            f'<h2 style="color:white;margin:0;font-size:22px;">&#x1F33E; {SOMITI_NAME} &#x1F33E;</h2>'
            f'<p style="color:#cce4f7;margin:6px 0 0;font-size:13px;">'
            f'{SOMITI_NAME_EN} | সঞ্চয় ও ঋণ ব্যবস্থাপনা</p></div>')

def _ef():  # email footer
    return (f'<div style="background:#f8f9fa;padding:14px 30px;'
            f'border-radius:0 0 10px 10px;border-top:1px solid #e0e0e0;text-align:center;">'
            f'<p style="color:#aaa;font-size:11px;margin:0;">'
            f'এই ইমেইলটি স্বয়ংক্রিয়ভাবে প্রেরিত।<br>'
            f'{SOMITI_NAME_EN} | {datetime.now().strftime("%d-%m-%Y %H:%M")}'
            f'</p></div>')

def _wrap(body):
    return (f'<html><head><meta charset="UTF-8"></head>'
            f'<body style="font-family:Arial,sans-serif;background:#f0f2f5;padding:30px;">'
            f'<div style="max-width:600px;margin:auto;background:white;border-radius:10px;'
            f'box-shadow:0 4px 15px rgba(0,0,0,.1);overflow:hidden;">'
            f'{_eh()}<div style="padding:28px 30px;">{body}</div>{_ef()}'
            f'</div></body></html>')

def _box(rows):
    return (f'<div style="background:#f4f8fb;border:1px solid #d0e4f0;'
            f'border-radius:8px;padding:16px 20px;margin:16px 0;">{rows}</div>')

def _row(label, val, color="#333"):
    return (f'<p style="margin:6px 0;font-size:14px;">'
            f'<b style="color:#1a5276;">{label}:</b>'
            f' <span style="color:{color};">{val}</span></p>')

def _send_email_now(to, subject, html):
    """
    Gmail SMTP দিয়ে synchronous email পাঠায়।
    Returns (ok:bool, msg:str)
    """
    to = str(to or '').strip()
    if not to or '@' not in to:
        return False, "ইমেইল ঠিকানা নেই বা ভুল"
    try:
        msg = MIMEMultipart('alternative')
        msg['From']    = f"{SOMITI_NAME} <{SENDER_EMAIL}>"
        msg['To']      = to
        msg['Subject'] = subject
        msg.attach(MIMEText(html, 'html', 'utf-8'))
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, timeout=30) as srv:
            srv.login(SENDER_EMAIL, SENDER_PASSWORD)
            srv.send_message(msg)
        return True, "সফল"
    except smtplib.SMTPAuthenticationError:
        return False, "Gmail App Password ভুল"
    except smtplib.SMTPException as ex:
        return False, f"SMTP: {str(ex)[:80]}"
    except Exception as ex:
        return False, str(ex)[:80]

def _fire(label, to, subject, html, toast=True):
    """Email পাঠিয়ে optionally toast দেখায়। rerun-এর আগে call করুন।"""
    to = str(to or '').strip()
    if not to or '@' not in to:
        return False
    ok, msg = _send_email_now(to, subject, html)
    if toast:
        if ok:
            st.toast(f"📧 {label} পাঠানো হয়েছে ✅")
        else:
            st.toast(f"📧 {label} ব্যর্থ: {msg} ❌")
    return ok

# ── ১. স্বাগতম ইমেইল ─────────────────────────────────────
def email_welcome(member):
    em = str(member.get('email','') or '').strip()
    if '@' not in em: return False, "ইমেইল নেই"
    mid  = member.get('id','')
    name = member.get('name','')
    pw   = member.get('password','')
    mon  = fmt(int(float(member.get('monthly_savings',500) or 500)))
    url  = f"https://oiorganization2024.streamlit.app/?member={mid}"
    html = _wrap(
        f'<p style="font-size:15px;color:#333;">প্রিয় <b>{name}</b>,</p>'
        f'<p style="color:#555;">আপনাকে <b>{SOMITI_NAME}</b> পরিবারে স্বাগতম।'
        f' আপনার সদস্যতা সফলভাবে সম্পন্ন হয়েছে।</p>'
        + _box(_row("সদস্য আইডি", mid)
             + _row("নাম", name)
             + _row("পাসওয়ার্ড", f"<b>{pw}</b>", "#c0392b")
             + _row("মাসিক কিস্তি", f"{mon} টাকা"))
        + f'<div style="background:#e8f5e9;border:1px solid #a5d6a7;border-radius:8px;padding:14px 20px;margin:14px 0;">'
          f'<p style="margin:0 0 6px;font-size:13px;color:#2e7d32;"><b>লগইন লিংক:</b></p>'
          f'<a href="{url}" style="color:#1565c0;font-size:13px;">{url}</a></div>'
        + '<ul style="color:#555;font-size:13px;line-height:1.9;">'
          '<li>প্রতি মাসের ১০ তারিখের মধ্যে কিস্তি জমা দিন</li>'
          '<li>দেরিতে জমা দিলে লেট ফি প্রযোজ্য হবে</li>'
          '<li>প্রথম লগইনে পাসওয়ার্ড পরিবর্তন করুন</li></ul>'
        + f'<p style="color:#1a5276;font-weight:bold;margin-top:18px;">ধন্যবাদ — {SOMITI_NAME} পরিবার</p>')
    ok = _fire("স্বাগতম ইমেইল", em, f"স্বাগতম — সদস্যতা সম্পন্ন | {SOMITI_NAME}", html)
    return ok, "ok"

# ── ২. পাসওয়ার্ড পরিবর্তন (সদস্য নিজে) ─────────────────
def email_password_changed(member, new_pw):
    em = str(member.get('email','') or '').strip()
    if '@' not in em: return False, "ইমেইল নেই"
    html = _wrap(
        f'<p style="font-size:15px;color:#333;">প্রিয় <b>{member.get("name","")}</b>,</p>'
        f'<p style="color:#555;">আপনার পাসওয়ার্ড সফলভাবে পরিবর্তন হয়েছে।</p>'
        + _box(_row("নতুন পাসওয়ার্ড", f"<b>{new_pw}</b>", "#c0392b")
             + _row("পরিবর্তনের সময়", datetime.now().strftime('%d-%m-%Y %H:%M')))
        + '<div style="background:#fff3e0;border:1px solid #ffcc80;border-radius:8px;padding:12px 18px;margin:14px 0;">'
          '<p style="color:#e65100;margin:0;font-size:13px;">আপনি নিজে না করলে অবিলম্বে এডমিনকে জানান।</p></div>'
        + f'<p style="color:#1a5276;font-weight:bold;">ধন্যবাদ — {SOMITI_NAME} প্রশাসন</p>')
    ok = _fire("পাসওয়ার্ড পরিবর্তন", em, f"পাসওয়ার্ড পরিবর্তনের নোটিফিকেশন | {SOMITI_NAME}", html)
    return ok, "ok"

# ── ৩. এডমিন পাসওয়ার্ড রিসেট ────────────────────────────
def email_admin_password_reset(member, new_pw):
    em = str(member.get('email','') or '').strip()
    if '@' not in em: return False, "ইমেইল নেই"
    url = f"https://oiorganization2024.streamlit.app/?member={member.get('id','')}"
    html = _wrap(
        f'<p style="font-size:15px;color:#333;">প্রিয় <b>{member.get("name","")}</b>,</p>'
        f'<p style="color:#555;">এডমিন কর্তৃক আপনার পাসওয়ার্ড রিসেট হয়েছে।</p>'
        + _box(_row("নতুন পাসওয়ার্ড", f"<b>{new_pw}</b>", "#c0392b")
             + _row("রিসেটের সময়", datetime.now().strftime('%d-%m-%Y %H:%M')))
        + f'<a href="{url}" style="display:inline-block;background:#1a5276;color:white;'
          f'padding:10px 22px;border-radius:6px;text-decoration:none;font-size:13px;margin-top:8px;">লগইন করুন</a>'
        + f'<p style="color:#1a5276;font-weight:bold;margin-top:18px;">ধন্যবাদ — {SOMITI_NAME} প্রশাসন</p>')
    ok = _fire("পাসওয়ার্ড রিসেট", em, f"নতুন পাসওয়ার্ড দেওয়া হয়েছে | {SOMITI_NAME}", html)
    return ok, "ok"

# ── ৪. কিস্তি জমার রসিদ ──────────────────────────────────
def email_deposit_receipt(member, amount, late_fee, month_name, year, deposit_date, total_sav):
    em = str(member.get('email','') or '').strip()
    if '@' not in em: return False, "ইমেইল নেই"
    total = amount + late_fee
    html = _wrap(
        f'<p style="font-size:15px;color:#333;">প্রিয় <b>{member.get("name","")}</b>,</p>'
        f'<p style="color:#555;">আপনার কিস্তি জমার রসিদ।</p>'
        + _box(_row("সদস্যের নাম", member.get('name',''))
             + _row("সদস্য আইডি", str(member.get('id','')))
             + _row("কিস্তির মাস", f"{month_name} {year}")
             + _row("কিস্তির পরিমাণ", f"{fmt(amount)} টাকা")
             + _row("লেট ফি", f"{fmt(late_fee)} টাকা")
             + _row("মোট জমা", f"<b>{fmt(total)} টাকা</b>", "#1e8449")
             + _row("জমার তারিখ", deposit_date))
        + f'<div style="background:#e8f5e9;border-radius:8px;padding:14px 20px;margin:14px 0;text-align:center;">'
          f'<p style="margin:0;color:#2e7d32;font-size:16px;">মোট সঞ্চয়: <b>{fmt(total_sav)} টাকা</b></p></div>'
        + f'<p style="color:#1a5276;font-weight:bold;">ধন্যবাদ — {SOMITI_NAME} পরিবার</p>')
    ok = _fire("কিস্তি রসিদ", em, f"কিস্তি জমার রসিদ — {month_name} {year} | {SOMITI_NAME}", html)
    return ok, "ok"

# ── ৫. মাসিক রিমাইন্ডার ──────────────────────────────────
def email_monthly_reminder(member, month_name, year, monthly_amount):
    em = str(member.get('email','') or '').strip()
    if '@' not in em: return False, "ইমেইল নেই"
    url = f"https://oiorganization2024.streamlit.app/?member={member.get('id','')}"
    html = _wrap(
        f'<p style="font-size:15px;color:#333;">প্রিয় <b>{member.get("name","")}</b>,</p>'
        f'<p style="color:#555;"><b>{month_name} {year}</b> মাসের কিস্তি এখনও জমা হয়নি।</p>'
        + _box(_row("কিস্তির মাস", f"{month_name} {year}")
             + _row("কিস্তির পরিমাণ", f"{fmt(monthly_amount)} টাকা")
             + _row("শেষ তারিখ", f"১০ {month_name} {year}")
             + _row("আজকের তারিখ", datetime.now().strftime('%d-%m-%Y')))
        + '<div style="background:#fff3e0;border:1px solid #ffcc80;border-radius:8px;padding:12px 18px;margin:14px 0;">'
          '<p style="color:#e65100;margin:0;font-size:13px;">দেরিতে জমা দিলে লেট ফি যুক্ত হবে।</p></div>'
        + f'<a href="{url}" style="display:inline-block;background:#e67e22;color:white;'
          f'padding:10px 22px;border-radius:6px;text-decoration:none;font-size:13px;">এখনই জমা দিন</a>'
        + f'<p style="color:#1a5276;font-weight:bold;margin-top:18px;">ধন্যবাদ — {SOMITI_NAME} প্রশাসন</p>')
    ok = _fire(f"রিমাইন্ডার ({member.get('name','')})", em,
               f"কিস্তি রিমাইন্ডার — {month_name} {year} | {SOMITI_NAME}", html, toast=False)
    return ok, "ok"

# ── ৬. লেট ফি নোটিফিকেশন ────────────────────────────────
def email_late_fee(member, amount, late_fee, month_name, year, deposit_date):
    em = str(member.get('email','') or '').strip()
    if '@' not in em: return False, "ইমেইল নেই"
    total = amount + late_fee
    html = _wrap(
        f'<p style="font-size:15px;color:#333;">প্রিয় <b>{member.get("name","")}</b>,</p>'
        f'<p style="color:#555;"><b>{month_name} {year}</b> মাসে লেট ফি যুক্ত হয়েছে।</p>'
        + _box(_row("কিস্তির মাস", f"{month_name} {year}")
             + _row("কিস্তির পরিমাণ", f"{fmt(amount)} টাকা")
             + _row("লেট ফি", f"<b>{fmt(late_fee)} টাকা</b>", "#c0392b")
             + _row("মোট প্রদেয়", f"<b>{fmt(total)} টাকা</b>", "#1e8449")
             + _row("জমার তারিখ", deposit_date))
        + f'<p style="color:#1a5276;font-weight:bold;">ধন্যবাদ — {SOMITI_NAME} প্রশাসন</p>')
    ok = _fire("লেট ফি নোটিফিকেশন", em,
               f"লেট ফি নোটিফিকেশন — {month_name} {year} | {SOMITI_NAME}", html)
    return ok, "ok"

# ── ৭. বার্ষিক রিপোর্ট ────────────────────────────────────
def email_annual_report(member, year, trans_list, total_sav):
    em = str(member.get('email','') or '').strip()
    if '@' not in em: return False, "ইমেইল নেই"
    yr_t = [tr for tr in trans_list if str(tr.get('year','')) == str(year)]
    total_dep = sum(int(float(tr.get('amount',0))) for tr in yr_t)
    total_lf  = sum(int(float(tr.get('late_fee',0))) for tr in yr_t)
    month_rows = ''.join(
        _row(mname, f"{fmt(sum(int(float(tr.get('amount',0))) for tr in yr_t if str(tr.get('month',''))==str(mn)))} টাকা")
        for mn, mname in BANGLA_MONTHS.items()
        if any(str(tr.get('month',''))==str(mn) for tr in yr_t))
    html = _wrap(
        f'<p style="font-size:15px;color:#333;">প্রিয় <b>{member.get("name","")}</b>,</p>'
        f'<p style="color:#555;"><b>{year}</b> সালের বার্ষিক সঞ্চয় রিপোর্ট।</p>'
        + _box(_row("সদস্যের নাম", member.get('name',''))
             + _row("সদস্য আইডি", str(member.get('id','')))
             + _row("বছর", str(year)))
        + '<p style="font-size:14px;color:#1a5276;font-weight:bold;margin:14px 0 4px;">মাসওয়ারি জমা:</p>'
        + _box(month_rows or "<p style='color:#999;'>কোনো লেনদেন নেই</p>")
        + _box(_row("মোট কিস্তি জমা", f"<b>{fmt(total_dep)} টাকা</b>", "#1e8449")
             + _row("মোট লেট ফি", f"{fmt(total_lf)} টাকা", "#c0392b")
             + _row("বর্তমান মোট সঞ্চয়", f"<b>{fmt(total_sav)} টাকা</b>", "#1565c0"))
        + f'<p style="color:#1a5276;font-weight:bold;">ধন্যবাদ — {SOMITI_NAME} পরিবার</p>')
    ok = _fire(f"বার্ষিক রিপোর্ট ({member.get('name','')})", em,
               f"বার্ষিক রিপোর্ট — {year} | {SOMITI_NAME}", html, toast=False)
    return ok, "ok"

# ── ৮. লটারি বিজয়ী ──────────────────────────────────────
def email_lottery_winner(member, month_name, year):
    em = str(member.get('email','') or '').strip()
    if '@' not in em: return False, "ইমেইল নেই"
    html = _wrap(
        '<div style="text-align:center;padding:10px 0 18px;">'
        '<div style="font-size:48px;">&#x1F3C6;</div>'
        '<h2 style="color:#e67e22;margin:8px 0;">অভিনন্দন!</h2></div>'
        + f'<p style="font-size:15px;color:#333;text-align:center;">প্রিয় <b>{member.get("name","")}</b>,<br>'
          f'আপনি <b>{month_name} {year}</b> মাসের লটারিতে বিজয়ী!</p>'
        + _box(_row("বিজয়ী সদস্য", member.get('name',''))
             + _row("সদস্য আইডি", str(member.get('id','')))
             + _row("লটারির মাস", f"{month_name} {year}")
             + _row("তারিখ", datetime.now().strftime('%d-%m-%Y')))
        + f'<p style="color:#1a5276;font-weight:bold;text-align:center;">ধন্যবাদ — {SOMITI_NAME} পরিবার</p>')
    ok = _fire("লটারি বিজয়ী", em, f"অভিনন্দন! লটারি বিজয়ী | {SOMITI_NAME}", html)
    return ok, "ok"

# ── ৯. ফান্ড ট্রান্সফার ──────────────────────────────────
def email_fund_transfer(tx_type, amount, description, prev_bal, new_bal, date_str, to_emails):
    type_label = "জমা" if tx_type == 'deposit' else "উত্তোলন"
    html = _wrap(
        f'<p style="font-size:15px;color:#333;">প্রিয় সদস্যবৃন্দ / এডমিন,</p>'
        f'<p style="color:#555;">সংস্থার ফান্ডে লেনদেন সম্পন্ন হয়েছে।</p>'
        + _box(_row("লেনদেনের ধরন", type_label)
             + _row("পরিমাণ", f"<b>{fmt(amount)} টাকা</b>", "#1565c0")
             + _row("তারিখ", date_str)
             + _row("বিবরণ", description)
             + _row("পূর্বের ব্যালেন্স", f"{fmt(prev_bal)} টাকা")
             + _row("বর্তমান ব্যালেন্স", f"<b>{fmt(new_bal)} টাকা</b>", "#1e8449"))
        + f'<p style="color:#1a5276;font-weight:bold;">ধন্যবাদ — {SOMITI_NAME} প্রশাসন</p>')
    subject = f"ফান্ড লেনদেন ({type_label}) | {SOMITI_NAME}"
    for em in to_emails:
        em = str(em).strip()
        if '@' in em:
            _fire("ফান্ড নোটিফিকেশন", em, subject, html, toast=False)

# ── ১০. টেস্ট ইমেইল ─────────────────────────────────────
def send_test_email(to_email):
    html = _wrap(
        f'<p style="font-size:16px;color:#333;">ইমেইল কনফিগারেশন সঠিকভাবে কাজ করছে!</p>'
        + _box(_row("SMTP সার্ভার", SMTP_SERVER)
             + _row("Port", str(SMTP_PORT))
             + _row("প্রেরক", SENDER_EMAIL)
             + _row("পাঠানোর সময়", datetime.now().strftime('%d-%m-%Y %H:%M')))
        + f'<p style="color:#1a5276;font-weight:bold;">ধন্যবাদ — {SOMITI_NAME}</p>')
    return _send_email_now(to_email, f"ইমেইল টেস্ট | {SOMITI_NAME}", html)

# ── কাস্টম নোটিফিকেশন ────────────────────────────────────
def send_notification_email(to_emails, subject, message, sender_name="Admin"):
    html = _wrap(
        f'<p style="font-size:15px;color:#333;white-space:pre-wrap;">{message}</p>'
        + f'<p style="color:#888;font-size:12px;margin-top:20px;">পাঠিয়েছেন: {sender_name}</p>')
    results = []
    for em in to_emails:
        em = str(em).strip()
        if '@' in em:
            ok, msg = _send_email_now(em, subject, html)
            results.append({'email': em, 'ok': ok, 'msg': msg})
    return results

# Legacy aliases
def send_email(to, subject, html): return _send_email_now(to, subject, html)
def send_emails_bulk(tos, subj, html):
    return [{'email': str(e).strip(), 'ok': _fire("bulk", str(e).strip(), subj, html, toast=False), 'msg': ''} for e in tos if '@' in str(e)]
def process_email_queue(): pass  # no-op
def _email_header(): return _eh()
def _email_footer(): return _ef()
def _wrap_email(b): return _wrap(b)
def _info_box(r): return _box(r)

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
    """FIX #6: সব পরিমাণ পূর্ণ সংখ্যায় দেখাবে, দশমিক নয়"""
    try:
        return f"{int(float(val)):,}"
    except:
        return "0"

def get_total_savings():
    df = load_df(MEMBERS_CSV, MEMBER_COLS)
    if len(df) == 0:
        return 0
    active = df[df['status'] == 'active']
    if len(active) == 0:
        return 0
    return int(active['total_savings'].astype(float).sum())

def get_total_expenses():
    df = load_df(EXPENSES_CSV, EXPENSE_COLS)
    if len(df) == 0:
        return 0
    return int(df['amount'].astype(float).sum())

def get_total_withdrawals():
    df = load_df(WITHDRAWALS_CSV, WITHDRAWAL_COLS)
    if len(df) == 0:
        return 0
    return int(df['amount'].astype(float).sum())

def get_fund_balance():
    df = load_df(FUND_CSV, FUND_COLS)
    if len(df) == 0:
        return 0
    deposits = df[df['type'] == 'deposit']['amount'].astype(float).sum()
    withdrawals = df[df['type'] == 'withdrawal']['amount'].astype(float).sum()
    return int(deposits - withdrawals)

def get_cash_balance():
    return int(get_total_savings() + get_fund_balance() - get_total_expenses() - get_total_withdrawals())

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
    data['total_savings'] = int(data.get('total_savings', 0))
    data['monthly_savings'] = int(data.get('monthly_savings', 500))
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

# FIX #1: সদস্য ডিলিট - সঠিকভাবে str তুলনা করে ফিল্টার করবে
def delete_member(member_id):
    member_id_str = str(member_id)
    # ট্রানজেকশন ডিলিট
    trans_df = load_df(TRANSACTIONS_CSV, TRANSACTION_COLS)
    if len(trans_df) > 0:
        trans_df['member_id'] = trans_df['member_id'].astype(str)
        trans_df = trans_df[trans_df['member_id'] != member_id_str]
        save_df(trans_df, TRANSACTIONS_CSV)
    # মেম্বার ডিলিট
    mem_df = load_df(MEMBERS_CSV, MEMBER_COLS)
    if len(mem_df) > 0:
        mem_df['id'] = mem_df['id'].astype(str)
        mem_df = mem_df[mem_df['id'] != member_id_str]
        save_df(mem_df, MEMBERS_CSV)
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

def get_all_expenses():
    df = load_df(EXPENSES_CSV, EXPENSE_COLS)
    return df.to_dict('records')

def add_expense(data):
    data['id'] = get_next_id(EXPENSES_CSV, EXPENSE_COLS)
    data['amount'] = int(data['amount'])
    append_row(EXPENSES_CSV, data, EXPENSE_COLS)

# FIX #4: খরচ ডিলিট - শুধু রেকর্ড মুছবে, ব্যালেন্সে কিছু যোগ হবে না
def delete_expense(exp_id):
    df = load_df(EXPENSES_CSV, EXPENSE_COLS)
    df = df[df['id'] != int(exp_id)]
    save_df(df, EXPENSES_CSV)
    return True

def get_all_withdrawals():
    df = load_df(WITHDRAWALS_CSV, WITHDRAWAL_COLS)
    return df.to_dict('records')

def add_withdrawal(data):
    data['id'] = get_next_id(WITHDRAWALS_CSV, WITHDRAWAL_COLS)
    data['amount'] = int(data['amount'])
    append_row(WITHDRAWALS_CSV, data, WITHDRAWAL_COLS)

def get_fund_transactions():
    df = load_df(FUND_CSV, FUND_COLS)
    if len(df) == 0:
        return []
    df = df.sort_values('id', ascending=False)
    return df.to_dict('records')

# FIX #5: ফান্ড উত্তোলন - ব্যালেন্স ০ বা কম হলে হবে না
def add_fund_transaction(data):
    current_balance = get_fund_balance()
    if data['type'] == 'withdrawal':
        if current_balance <= 0 or data['amount'] > current_balance:
            return False
    data['id'] = get_next_id(FUND_CSV, FUND_COLS)
    data['amount'] = int(data['amount'])
    append_row(FUND_CSV, data, FUND_COLS)
    return True

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
        return 0
    month_df = df[(df['month'] == current.month) & (df['year'] == current.year)]
    return int(month_df['amount'].astype(float).sum())

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
    .stDataFrame { border-radius: 10px; overflow: hidden; border: 1px solid #30363d; max-height: 400px; }
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
        st.markdown(f'<div class="total-box"><h2>💰 {fmt(total)} {t("টাকা", "Taka")}</h2><p>{t("মোট জমা", "Total Savings")}</p></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="cash-box"><h2>💵 {fmt(cash)} {t("টাকা", "Taka")}</h2><p>{t("ক্যাশ ব্যালেন্স", "Cash Balance")}</p></div>', unsafe_allow_html=True)

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
        monthly = int(float(m.get('monthly_savings', 500)))
        savings = int(float(m.get('total_savings', 0)))
        data.append([m['id'], m['name'], m['phone'], f"{monthly:,}", f"{savings:,}"])
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
            amount = int(float(tr.get('amount', 0)))
            data.append([tr['full_date'], f"{amount:,}", tr['month_name'], str(tr['year'])])
    else:
        trans_df = load_df(TRANSACTIONS_CSV, TRANSACTION_COLS)
        mem_df = load_df(MEMBERS_CSV, MEMBER_COLS)
        if len(trans_df) > 0 and len(mem_df) > 0:
            merged = trans_df.merge(mem_df[['id', 'name']], left_on='member_id', right_on='id')
            merged = merged.sort_values(['year', 'month', 'day'], ascending=[False, False, False]).head(100)
            data = [['Date', 'Member', 'Amount', 'Month', 'Year']]
            for _, tr in merged.iterrows():
                amount = int(float(tr['amount']))
                data.append([tr['full_date'], tr['name'], f"{amount:,}", tr['month_name'], str(tr['year'])])
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
    <div class="total-box"><h2>💰 {fmt(total)} {t('টাকা', 'Taka')}</h2><p>{t('মোট জমা', 'Total Savings')}</p></div>
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
    process_email_queue()   # ← প্রতিটি render-এ pending ইমেইল পাঠায়
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
                f"🔄 {t('লেনদেন পরিবর্তন', 'Transactions')}",
                f"💸 {t('ব্যয় হিসাব', 'Expenses')}",
                f"📒 {t('ব্যয় তালিকা', 'Expense List')}",
                f"🏧 {t('ফান্ড ব্যবস্থাপনা', 'Fund Management')}",
                f"📊 {t('রিপোর্ট', 'Reports')}",
                f"📥 {t('পিডিএফ ডাউনলোড', 'PDF Download')}",
                f"📧 {t('ইমেইল ব্যবস্থাপনা', 'Email Management')}",
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
            st.markdown(f"""<div class="kpi-card"><h3>💰 {t('মোট জমা', 'Total')}</h3><h2>{fmt(total_savings)}</h2></div>""", unsafe_allow_html=True)
        with col3:
            st.markdown(f"""<div class="kpi-card"><h3>📅 {t('এই মাস', 'This Month')}</h3><h2>{fmt(this_month)}</h2></div>""", unsafe_allow_html=True)
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
                password = generate_password()
                member_id = add_member({
                    'name': name, 'phone': phone, 'email': email,
                    'password': password, 'monthly_savings': int(monthly)
                })
                st.success(f"✅ {t('সদস্য তৈরি', 'Member created')}!")
                st.info(f"{t('আইডি', 'ID')}: {member_id} | {t('পাস', 'Pass')}: {password}")
                # ── স্বাগতম ইমেইল ──
                if email and '@' in str(email):
                    new_mem = get_member_by_id(member_id)
                    if new_mem:
                        ok_em, msg_em = email_welcome(new_mem)
                        if ok_em:
                            st.success("📧 স্বাগতম ইমেইল পাঠানো হয়েছে!")
                        else:
                            st.warning(f"📧 ইমেইল পাঠানো যায়নি: {msg_em}")
                st.balloons()
            else:
                st.error(t("❌ নাম ও মোবাইল আবশ্যক", "❌ Name and mobile required"))

    # FIX #1: সদস্য ডিলিট সমস্যা ঠিক করা হয়েছে
    elif f"✏️ {t('সদস্য ব্যবস্থাপনা', 'Manage Members')}" in menu:
        st.markdown(f"### ✏️ {t('সদস্য ব্যবস্থাপনা', 'Member Management')}")
        members = get_all_members()
        if members:
            for m in members:
                member_id = str(m['id'])
                name = m['name']
                phone = m['phone']
                email = m.get('email', '')
                status = m.get('status', 'active')
                monthly = int(float(m.get('monthly_savings', 500))) if m.get('monthly_savings') else 500
                savings = int(float(m.get('total_savings', 0))) if m.get('total_savings') else 0

                with st.expander(f"👤 {name} - {member_id}"):
                    st.write(f"📱 {phone} | 📧 {email or 'N/A'} | 💰 {fmt(savings)} {t('টাকা', 'Taka')}")

                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        if st.button(f"📝 {t('এডিট', 'Edit')}", key=f"e_{member_id}"):
                            st.session_state[f"edit_{member_id}"] = True
                    with col2:
                        if st.button(f"🔐 {t('পাসওয়ার্ড', 'Password')}", key=f"p_{member_id}"):
                            st.session_state[f"pass_{member_id}"] = True
                    with col3:
                        new_status = 'inactive' if status == 'active' else 'active'
                        btn_text = t('নিষ্ক্রিয়', 'Inactive') if status == 'active' else t('সক্রিয়', 'Active')
                        if st.button(f"🔄 {btn_text}", key=f"s_{member_id}"):
                            update_member(member_id, {'status': new_status})
                            st.rerun()
                    with col4:
                        if st.button(f"🗑️ {t('ডিলিট', 'Delete')}", key=f"del_{member_id}"):
                            st.session_state[f"delete_confirm_{member_id}"] = True

                    # FIX #1: কনফার্মেশন key আলাদা রাখা হয়েছে যাতে clash না হয়
                    if st.session_state.get(f"delete_confirm_{member_id}"):
                        st.warning(f"⚠️ {t('আপনি কি নিশ্চিত? এই সদস্যের সকল ডাটা মুছে যাবে!', 'Are you sure? All data will be deleted!')}")
                        c1, c2 = st.columns(2)
                        with c1:
                            if st.button(f"✅ {t('হ্যাঁ, ডিলিট করুন', 'Yes, Delete')}", key=f"yes_confirm_{member_id}"):
                                result = delete_member(member_id)
                                if result:
                                    st.session_state.pop(f"delete_confirm_{member_id}", None)
                                    st.success(f"✅ {t('ডিলিট সম্পন্ন!', 'Deleted successfully!')}")
                                    time.sleep(0.5)
                                    st.rerun()
                        with c2:
                            if st.button(f"❌ {t('না', 'No')}", key=f"no_confirm_{member_id}"):
                                st.session_state.pop(f"delete_confirm_{member_id}", None)
                                st.rerun()

                    if st.session_state.get(f"edit_{member_id}"):
                        with st.form(f"edit_form_{member_id}"):
                            new_name = st.text_input(t("নাম", "Name"), value=name)
                            new_phone = st.text_input(t("মোবাইল", "Mobile"), value=phone)
                            new_email = st.text_input(t("ইমেইল", "Email"), value=email)
                            new_mon = st.number_input(t("কিস্তি", "Monthly"), value=monthly, step=50)
                            if st.form_submit_button("💾"):
                                update_member(member_id, {
                                    'name': new_name, 'phone': new_phone,
                                    'email': new_email, 'monthly_savings': int(new_mon)
                                })
                                st.success("✅ আপডেট সম্পন্ন!")
                                st.session_state.pop(f"edit_{member_id}", None)
                                st.rerun()

                    if st.session_state.get(f"pass_{member_id}"):
                        if st.button(f"✅ {t('নতুন পাসওয়ার্ড জেনারেট করুন', 'Generate New Password')}", key=f"gen_{member_id}"):
                            new_pass = generate_password()
                            update_member(member_id, {'password': new_pass})
                            st.success(f"✅ {t('নতুন পাস', 'New Pass')}: {new_pass}")
                            # ── এডমিন রিসেট ইমেইল ──
                            mem_for_email = get_member_by_id(member_id)
                            if mem_for_email and mem_for_email.get('email') and '@' in str(mem_for_email.get('email','')):
                                ok_em, msg_em = email_admin_password_reset(mem_for_email, new_pass)
                                if ok_em:
                                    st.info("📧 পাসওয়ার্ড রিসেট ইমেইল পাঠানো হয়েছে।")
                            st.session_state.pop(f"pass_{member_id}", None)
                            st.rerun()
        else:
            st.info(t("কোনো সদস্য নেই", "No members"))

    # FIX #2: জমা দেওয়া সদস্য তালিকা - লুকানো অবস্থায় থাকবে
    elif f"💵 {t('টাকা জমা', 'Deposit')}" in menu:
        st.markdown(f"### 💵 {t('সদস্যের টাকা জমা', 'Member Deposit')}")
        tab1, tab2 = st.tabs([f"✅ {t('জমা দিয়েছে', 'Paid')}", f"❌ {t('জমা দেয়নি', 'Unpaid')}"])

        with tab1:
            paid = get_paid_members()
            if paid:
                # FIX #2: expanded=False দিয়ে ডিফল্ট লুকানো
                with st.expander(f"📋 {t('জমা দেওয়া সদস্য তালিকা দেখুন', 'View Paid Members List')} ({len(paid)} জন)", expanded=False):
                    table_data = []
                    for pm in paid:
                        table_data.append({
                            t('নাম', 'Name'): pm['name'],
                            t('আইডি', 'ID'): pm['id'],
                            t('মোবাইল', 'Mobile'): pm['phone'],
                            t('মোট জমা', 'Savings'): fmt(pm.get('total_savings', 0))
                        })
                    df = pd.DataFrame(table_data)
                    st.dataframe(df, use_container_width=True, hide_index=True, height=350)
            else:
                st.info(t("এই মাসে কেউ এখনও জমা দেয়নি", "No one paid this month yet"))

        with tab2:
            unpaid = get_unpaid_members()
            if unpaid:
                for um in unpaid:
                    savings_val = int(float(um.get('total_savings', 0))) if um.get('total_savings') else 0
                    monthly_val = int(float(um.get('monthly_savings', 500))) if um.get('monthly_savings') else 500
                    with st.expander(f"❌ {um['name']} ({um['id']}) - বকেয়া: {fmt(monthly_val)} টাকা"):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("মোট জমা", f"{fmt(savings_val)} টাকা")
                        with col2:
                            st.metric("মাসিক কিস্তি", f"{fmt(monthly_val)} টাকা")

                        deposit_date = st.date_input(t("জমার তারিখ", "Deposit Date"), datetime.now(), key=f"date_{um['id']}")
                        day = deposit_date.day
                        month = deposit_date.month
                        year = deposit_date.year

                        c1, c2 = st.columns(2)
                        with c1:
                            months_count = st.number_input(t("কত মাস", "Months"), 1, 12, 1, key=f"count_{um['id']}")
                        with c2:
                            late_fee = st.number_input(t("লেট ফি", "Late Fee"), 0, step=10, key=f"fee_{um['id']}")

                        total = monthly_val * months_count + late_fee

                        if st.button(f"✅ {t('জমা নিন', 'Deposit')} ({fmt(total)} টাকা)", key=f"dep_{um['id']}", type="primary"):
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

                            df = load_df(MEMBERS_CSV, MEMBER_COLS)
                            idx = df[df['id'] == um['id']].index
                            if len(idx) > 0:
                                current_sav = int(float(df.loc[idx[0], 'total_savings'])) if pd.notna(df.loc[idx[0], 'total_savings']) else 0
                                new_sav = int(current_sav + total)
                                df.loc[idx[0], 'total_savings'] = new_sav
                                save_df(df, MEMBERS_CSV)
                            else:
                                new_sav = total

                            st.success(f"✅ {fmt(total)} {t('টাকা জমা হয়েছে', 'Taka deposited')}!")

                            # ── কিস্তি রসিদ ইমেইল ──
                            mem_up = get_member_by_id(um['id'])
                            if mem_up and mem_up.get('email') and '@' in str(mem_up.get('email','')):
                                ok_r, _ = email_deposit_receipt(
                                    mem_up, monthly_val, int(late_fee),
                                    BANGLA_MONTHS[month], year, full_date, new_sav
                                )
                                if ok_r:
                                    st.info("📧 কিস্তির রসিদ ইমেইল পাঠানো হয়েছে।")
                                # ── লেট ফি ইমেইল (যদি লেট ফি > ০) ──
                                if int(late_fee) > 0:
                                    email_late_fee(mem_up, monthly_val, int(late_fee),
                                                   BANGLA_MONTHS[month], year, full_date)
                            st.balloons()
                            time.sleep(1)
                            st.rerun()
            else:
                st.success(f"🎉 {t('সবাই জমা দিয়েছেন', 'All paid')}!")

    # ==================== লেনদেন পরিবর্তন ====================
    elif f"🔄 {t('লেনদেন পরিবর্তন', 'Transactions')}" in menu:
        st.markdown(f"### 🔄 {t('লেনদেন পরিবর্তন', 'Transaction Management')}")

        # session_state initialize
        if 'tx_sel_member' not in st.session_state:
            st.session_state['tx_sel_member'] = None
        if 'tx_sel_tr_id' not in st.session_state:
            st.session_state['tx_sel_tr_id'] = None
        if 'tx_mode' not in st.session_state:
            st.session_state['tx_mode'] = None

        # ── STEP 1: সদস্য নির্বাচন ──────────────────────────
        all_members = get_all_members()
        active_members = [m for m in all_members if str(m.get('status','')) == 'active']

        if not active_members:
            st.info(t("⚠️ কোনো সক্রিয় সদস্য নেই।", "⚠️ No active members found."))
        else:
            member_labels = [f"{m['name']}  ({m['id']})" for m in active_members]
            member_ids    = [str(m['id']) for m in active_members]

            # বর্তমান নির্বাচিত index বের করো
            cur_mid = st.session_state['tx_sel_member']
            cur_idx = member_ids.index(cur_mid) if cur_mid in member_ids else 0

            chosen_idx = st.selectbox(
                t("👤 সদস্য নির্বাচন করুন", "Select Member"),
                range(len(member_labels)),
                format_func=lambda i: member_labels[i],
                index=cur_idx,
                key="tx_member_sb"
            )

            # সদস্য পরিবর্তন হলে লেনদেন selection রিসেট করো
            new_mid = member_ids[chosen_idx]
            if new_mid != st.session_state['tx_sel_member']:
                st.session_state['tx_sel_member'] = new_mid
                st.session_state['tx_sel_tr_id']  = None
                st.session_state['tx_mode']        = None

            sel_id     = st.session_state['tx_sel_member']
            sel_member = get_member_by_id(sel_id)

            if not sel_member:
                st.error(t("সদস্য পাওয়া যায়নি।", "Member not found."))
            else:
                savings_val = int(float(sel_member.get('total_savings', 0) or 0))
                monthly_val = int(float(sel_member.get('monthly_savings', 500) or 500))

                # ── সদস্য তথ্য কার্ড ────────────────────────────
                st.markdown(f"""
                <div style="background:#21262d;padding:12px 16px;border-radius:10px;
                            border:1px solid #30363d;margin-bottom:16px;">
                    <b>👤 {sel_member['name']}</b> &nbsp;|&nbsp;
                    🆔 {sel_member['id']} &nbsp;|&nbsp;
                    📱 {sel_member['phone']} &nbsp;|&nbsp;
                    💰 <b style="color:#58a6ff;">{fmt(savings_val)} টাকা মোট জমা</b> &nbsp;|&nbsp;
                    📅 মাসিক কিস্তি: <b>{fmt(monthly_val)} টাকা</b>
                </div>
                """, unsafe_allow_html=True)

                # ── STEP 2: লেনদেন লোড ──────────────────────────
                trans = get_member_transactions(sel_id)

                if not trans:
                    st.info(t("⚠️ এই সদস্যের কোনো লেনদেন নেই।", "⚠️ No transactions for this member."))
                else:
                    # ── লেনদেন তালিকা টেবিল ────────────────────
                    st.markdown(f"#### 📋 {t('লেনদেন তালিকা', 'Transaction List')} ({len(trans)} টি)")
                    tbl = []
                    for tr in trans:
                        a  = int(float(tr['amount']))    if tr.get('amount')   else 0
                        lf = int(float(tr['late_fee']))  if tr.get('late_fee') else 0
                        tbl.append({
                            "ID": str(tr['id']),
                            t('তারিখ','Date'):   tr.get('full_date',''),
                            t('মাস','Month'):    f"{tr.get('month_name','')} {tr.get('year','')}",
                            t('পরিমাণ','Amount'): fmt(a),
                            t('লেট ফি','Late Fee'): fmt(lf),
                        })
                    st.dataframe(pd.DataFrame(tbl), use_container_width=True, hide_index=True, height=240)

                    st.markdown("---")

                    # ── STEP 3: লেনদেন নির্বাচন (selectbox) ────
                    tr_labels = [
                        f"#{tr['id']}  |  {tr.get('full_date','')}  |  "
                        f"{fmt(int(float(tr['amount'])) if tr.get('amount') else 0)} টাকা  |  "
                        f"{tr.get('month_name','')} {tr.get('year','')}"
                        for tr in trans
                    ]
                    tr_ids = [str(tr['id']) for tr in trans]

                    cur_trid = st.session_state['tx_sel_tr_id']
                    tr_cur_idx = tr_ids.index(cur_trid) if cur_trid in tr_ids else 0

                    chosen_tr_idx = st.selectbox(
                        t("✏️ পরিবর্তন করতে লেনদেন নির্বাচন করুন", "Select transaction to edit/delete"),
                        range(len(tr_labels)),
                        format_func=lambda i: tr_labels[i],
                        index=tr_cur_idx,
                        key="tx_trans_sb"
                    )

                    new_trid = tr_ids[chosen_tr_idx]
                    if new_trid != st.session_state['tx_sel_tr_id']:
                        st.session_state['tx_sel_tr_id'] = new_trid
                        st.session_state['tx_mode']      = None

                    sel_tr     = trans[chosen_tr_idx]
                    sel_tr_id  = sel_tr['id']
                    sel_amount = int(float(sel_tr['amount']))    if sel_tr.get('amount')   else 0
                    sel_late   = int(float(sel_tr['late_fee']))  if sel_tr.get('late_fee') else 0

                    # নির্বাচিত লেনদেন হাইলাইট
                    st.markdown(f"""
                    <div style="background:#1c2d1c;padding:10px 16px;border-radius:8px;
                                border:1px solid #2ea043;margin:8px 0 14px 0;">
                        ✅ <b>নির্বাচিত লেনদেন:</b> &nbsp;
                        ID #{sel_tr_id} &nbsp;|&nbsp;
                        📅 {sel_tr.get('full_date','')} &nbsp;|&nbsp;
                        💰 <b style="color:#58a6ff;">{fmt(sel_amount)} টাকা</b> &nbsp;|&nbsp;
                        🗓️ {sel_tr.get('month_name','')} {sel_tr.get('year','')} &nbsp;|&nbsp;
                        লেট ফি: {fmt(sel_late)} টাকা
                    </div>
                    """, unsafe_allow_html=True)

                    # ── STEP 4: এডিট / ডিলিট বাটন ──────────────
                    bc1, bc2 = st.columns(2)
                    with bc1:
                        if st.button(f"✏️ {t('এডিট করুন', 'Edit')}", key="btn_tx_edit", use_container_width=True, type="primary"):
                            st.session_state['tx_mode'] = 'edit'
                    with bc2:
                        if st.button(f"🗑️ {t('ডিলিট করুন', 'Delete')}", key="btn_tx_del", use_container_width=True):
                            st.session_state['tx_mode'] = 'delete'

                    tx_mode = st.session_state.get('tx_mode')

                    # ── এডিট প্যানেল ────────────────────────────
                    if tx_mode == 'edit':
                        st.markdown(f"#### ✏️ {t('লেনদেন এডিট', 'Edit Transaction')}")
                        with st.form("form_tx_edit", clear_on_submit=False):
                            st.caption(f"ID #{sel_tr_id} | {sel_tr.get('full_date','')} | {sel_tr.get('month_name','')} {sel_tr.get('year','')}")
                            new_amt  = st.number_input(t("নতুন পরিমাণ (টাকা)", "New Amount"), value=sel_amount, min_value=0, step=50)
                            new_lf   = st.number_input(t("লেট ফি (টাকা)", "Late Fee"),        value=sel_late,   min_value=0, step=10)
                            fc1, fc2 = st.columns(2)
                            with fc1:
                                save_btn   = st.form_submit_button(f"💾 {t('সংরক্ষণ', 'Save')}", use_container_width=True)
                            with fc2:
                                cancel_btn = st.form_submit_button(f"❌ {t('বাতিল', 'Cancel')}", use_container_width=True)

                        if save_btn:
                            diff = int(new_amt) - sel_amount
                            mdf  = load_df(MEMBERS_CSV, MEMBER_COLS)
                            ix   = mdf[mdf['id'] == str(sel_id)].index
                            if len(ix) > 0:
                                old_bal = int(float(mdf.loc[ix[0], 'total_savings'] or 0))
                                mdf.loc[ix[0], 'total_savings'] = max(0, old_bal + diff)
                                save_df(mdf, MEMBERS_CSV)
                            update_transaction(sel_tr_id, {'amount': int(new_amt), 'late_fee': int(new_lf)})
                            st.session_state['tx_mode'] = None
                            st.success(t(
                                f"✅ লেনদেন আপডেট হয়েছে! পরিমাণ {fmt(sel_amount)} → {fmt(int(new_amt))} টাকা। ব্যালেন্স স্বয়ংক্রিয়ভাবে আপডেট হয়েছে।",
                                f"✅ Updated! Amount {fmt(sel_amount)} → {fmt(int(new_amt))} Taka. Balance auto-adjusted."
                            ))
                            time.sleep(0.5)
                            st.rerun()
                        if cancel_btn:
                            st.session_state['tx_mode'] = None
                            st.rerun()

                    # ── ডিলিট কনফার্মেশন ────────────────────────
                    elif tx_mode == 'delete':
                        st.warning(
                            f"⚠️ **{t('সতর্কতা:', 'Warning:')}** "
                            f"ID #{sel_tr_id} — **{fmt(sel_amount)} টাকা**র লেনদেন "
                            f"স্থায়ীভাবে মুছে যাবে এবং সদস্যের ব্যালেন্স {fmt(sel_amount)} টাকা কমবে।"
                        )
                        dd1, dd2 = st.columns(2)
                        with dd1:
                            if st.button(f"✅ {t('হ্যাঁ, ডিলিট করুন', 'Yes, Delete')}", key="btn_tx_del_yes", use_container_width=True):
                                mdf2 = load_df(MEMBERS_CSV, MEMBER_COLS)
                                ix2  = mdf2[mdf2['id'] == str(sel_id)].index
                                if len(ix2) > 0:
                                    old_b2 = int(float(mdf2.loc[ix2[0], 'total_savings'] or 0))
                                    mdf2.loc[ix2[0], 'total_savings'] = max(0, old_b2 - sel_amount)
                                    save_df(mdf2, MEMBERS_CSV)
                                delete_transaction(sel_tr_id)
                                st.session_state['tx_mode']     = None
                                st.session_state['tx_sel_tr_id'] = None
                                st.success(t("✅ লেনদেন মুছে গেছে এবং ব্যালেন্স আপডেট হয়েছে।",
                                             "✅ Deleted and balance updated."))
                                time.sleep(0.5)
                                st.rerun()
                        with dd2:
                            if st.button(f"❌ {t('না, বাতিল', 'No, Cancel')}", key="btn_tx_del_no", use_container_width=True):
                                st.session_state['tx_mode'] = None
                                st.rerun()

    # ==================== ব্যয় হিসাব (নতুন খরচ যোগ) ====================
    elif f"💸 {t('ব্যয় হিসাব', 'Expenses')}" in menu:
        st.markdown(f"### 💸 {t('ব্যয় হিসাব', 'Expense Management')}")
        st.info(f"💰 {t('নতুন খরচ যোগ করলে মেইন ক্যাশ ব্যালেন্স থেকে টাকা কমে যাবে।', 'Adding a new expense will reduce the main cash balance.')}")

        # ফাংশন ১: নতুন খরচ যোগ (বিবরণ, টাকা, ক্যাটাগরি)
        with st.form("exp_form_new"):
            desc = st.text_input(t("বিবরণ *", "Description *"), placeholder=t("যেমন: চা-নাস্তা, স্টেশনারি কেনা...", "e.g. Tea, stationery..."))
            amt = st.number_input(t("পরিমাণ (টাকা) *", "Amount (Taka) *"), min_value=0, step=10)
            cat = st.selectbox(t("ক্যাটাগরি", "Category"), [
                t("অফিস", "Office"),
                t("চা-নাস্তা", "Tea/Snacks"),
                t("স্টেশনারি", "Stationery"),
                t("পরিবহন", "Transport"),
                t("অন্যান্য", "Others")
            ])
            submitted = st.form_submit_button(f"💾 {t('খরচ যোগ করুন', 'Add Expense')}", type="primary", use_container_width=True)
            if submitted:
                if desc and amt > 0:
                    add_expense({
                        'description': desc,
                        'amount': int(amt),
                        'date': datetime.now().strftime("%Y-%m-%d"),
                        'category': cat
                    })
                    st.success(f"✅ {fmt(amt)} {t('টাকার খরচ যোগ হয়েছে। ক্যাশ ব্যালেন্স কমেছে।', 'Taka expense added. Cash balance reduced.')}")
                    st.rerun()
                else:
                    st.error(t("❌ বিবরণ ও পরিমাণ দেওয়া আবশ্যক।", "❌ Description and amount are required."))

    # FIX #5: ফান্ড উত্তোলন — ব্যালেন্স ০ হলে হবে না
    elif f"📒 {t('ব্যয় তালিকা', 'Expense List')}" in menu:
        st.markdown(f"### 📒 {t('ব্যয় তালিকা', 'Expense List')}")
        st.caption(t("এই তালিকা শুধু দেখার জন্য। এখান থেকে ডিলিট করা যাবে না।",
                     "This list is read-only. Expenses cannot be deleted from here."))
        expenses = get_all_expenses()
        if not expenses:
            st.info(t("📭 কোনো খরচ নেই। 'ব্যয় হিসাব' মেনু থেকে নতুন খরচ যোগ করুন।",
                      "📭 No expenses. Add from 'Expenses' menu."))
        else:
            total_exp = sum(int(float(e.get('amount', 0))) for e in expenses)
            c1, c2 = st.columns(2)
            c1.metric(f"📊 {t('মোট খরচ', 'Total Expenses')}", f"{fmt(total_exp)} টাকা")
            c2.metric(f"📋 {t('মোট রেকর্ড', 'Total Records')}", f"{len(expenses)} টি")
            st.markdown("---")
            tbl_exp = []
            for exp in expenses:
                av = int(float(exp['amount'])) if exp.get('amount') else 0
                tbl_exp.append({
                    t('তারিখ','Date'):        exp.get('date',''),
                    t('ক্যাটাগরি','Category'): exp.get('category',''),
                    t('বিবরণ','Description'):  str(exp.get('description',''))[:50],
                    t('পরিমাণ','Amount'):      f"{fmt(av)} টাকা"
                })
            st.dataframe(pd.DataFrame(tbl_exp), use_container_width=True, hide_index=True, height=400)

    elif f"🏧 {t('ফান্ড ব্যবস্থাপনা', 'Fund Management')}" in menu:
        st.markdown(f"### 🏧 {t('ফান্ড ব্যবস্থাপনা', 'Fund Management')}")
        cash = get_cash_balance()
        fund_balance = get_fund_balance()
        st.info(f"💰 {t('ক্যাশ ব্যালেন্স', 'Cash')}: {fmt(cash)} | 🏦 {t('ফান্ড ব্যালেন্স', 'Fund')}: {fmt(fund_balance)}")

        tab1, tab2, tab3 = st.tabs([f"➕ {t('জমা', 'Deposit')}", f"➖ {t('উত্তোলন', 'Withdrawal')}", f"📋 {t('ইতিহাস', 'History')}"])

        with tab1:
            with st.form("fund_deposit"):
                amount = st.number_input(t("পরিমাণ (টাকা)", "Amount (Taka)"), min_value=0, step=100)
                desc = st.text_area(t("বিবরণ", "Description"))
                if st.form_submit_button("✅ জমা দিন"):
                    if amount > 0 and desc:
                        cur_bal = get_fund_balance()
                        new_bal = int(cur_bal + amount)
                        add_fund_transaction({
                            'type': 'deposit', 'amount': int(amount), 'description': desc,
                            'date': datetime.now().strftime("%Y-%m-%d"),
                            'previous_balance': cur_bal, 'current_balance': new_bal,
                            'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
                        st.success(f"✅ {fmt(amount)} {t('টাকা জমা হয়েছে!', 'Taka deposited!')}!")
                        # ── ফান্ড ইমেইল ──
                        all_em = [m.get('email','') for m in get_all_members() if m.get('email') and '@' in str(m.get('email',''))]
                        all_em.append(SENDER_EMAIL)
                        email_fund_transfer('deposit', int(amount), desc, cur_bal, new_bal,
                                            datetime.now().strftime('%d-%m-%Y'), list(set(all_em)))
                        st.balloons()
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(t("❌ পরিমাণ ও বিবরণ দিন", "❌ Enter amount and description"))

        with tab2:
            current_fund_balance = get_fund_balance()
            if current_fund_balance <= 0:
                st.error(f"❌ {t('ফান্ড ব্যালেন্স শূন্য। উত্তোলন সম্ভব নয়।', 'Fund balance is zero. Withdrawal not possible.')}")
            else:
                st.info(f"🏦 {t('বর্তমান ফান্ড ব্যালেন্স', 'Current Fund Balance')}: {fmt(current_fund_balance)} {t('টাকা', 'Taka')}")
                with st.form("fund_withdraw"):
                    amount = st.number_input(t("উত্তোলন পরিমাণ (টাকা)", "Withdrawal Amount"), min_value=0, max_value=current_fund_balance, step=100)
                    desc = st.text_area(t("বিবরণ", "Description"))
                    date = st.date_input(t("তারিখ", "Date"), datetime.now())
                    if st.form_submit_button("✅ উত্তোলন করুন"):
                        if amount <= 0:
                            st.error(t("❌ সঠিক পরিমাণ দিন", "❌ Enter valid amount"))
                        elif amount > current_fund_balance:
                            st.error(f"❌ {t('পর্যাপ্ত ব্যালেন্স নেই', 'Insufficient balance')}! ({fmt(current_fund_balance)} {t('টাকা আছে', 'Taka available')})")
                        elif not desc:
                            st.error(t("❌ বিবরণ দিন", "❌ Enter description"))
                        else:
                            success = add_fund_transaction({
                                'type': 'withdrawal', 'amount': int(amount), 'description': desc,
                                'date': date.strftime("%Y-%m-%d"),
                                'previous_balance': current_fund_balance,
                                'current_balance': int(current_fund_balance - amount),
                                'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            })
                            if success:
                                add_withdrawal({
                                    'date': date.strftime("%Y-%m-%d"), 'amount': int(amount), 'description': desc,
                                    'withdrawn_by': 'Admin', 'previous_balance': current_fund_balance,
                                    'current_balance': int(current_fund_balance - amount),
                                    'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                })
                                st.success(f"✅ {fmt(amount)} {t('টাকা উত্তোলন সম্পন্ন!', 'Taka withdrawn!')}!")
                                # ── ফান্ড উত্তোলন ইমেইল ──
                                all_em2 = [m.get('email','') for m in get_all_members() if m.get('email') and '@' in str(m.get('email',''))]
                                all_em2.append(SENDER_EMAIL)
                                email_fund_transfer('withdrawal', int(amount), desc, current_fund_balance,
                                                    int(current_fund_balance - amount),
                                                    date.strftime('%d-%m-%Y'), list(set(all_em2)))
                                st.rerun()
                            else:
                                st.error(t("❌ উত্তোলন সম্ভব হয়নি!", "❌ Withdrawal failed!"))

        with tab3:
            fund_trans = get_fund_transactions()
            if fund_trans:
                with st.expander(f"📋 {t('ফান্ড লেনদেন ইতিহাস দেখুন', 'View Fund Transaction History')} ({len(fund_trans[:30])} টি)", expanded=False):
                    table_data = []
                    for ft in fund_trans[:30]:
                        amt_v = int(float(ft['amount'])) if ft.get('amount') else 0
                        bal_v = int(float(ft['current_balance'])) if ft.get('current_balance') else 0
                        table_data.append({
                            t('তারিখ', 'Date'): ft['date'],
                            t('ধরন', 'Type'): "➕ জমা" if ft['type'] == 'deposit' else "➖ উত্তোলন",
                            t('পরিমাণ', 'Amount'): fmt(amt_v),
                            t('বিবরণ', 'Description'): str(ft.get('description', ''))[:30],
                            t('ব্যালেন্স', 'Balance'): fmt(bal_v)
                        })
                    df_ft = pd.DataFrame(table_data)
                    st.dataframe(df_ft, use_container_width=True, hide_index=True, height=350)
            else:
                st.info(t("কোনো ফান্ড লেনদেন নেই", "No fund transactions"))

    elif f"📊 {t('রিপোর্ট', 'Reports')}" in menu:
        st.markdown(f"### 📊 {t('রিপোর্ট', 'Reports')}")
        tab1, tab2 = st.tabs([f"📈 {t('মাসিক', 'Monthly')}", f"⚠️ {t('বকেয়া', 'Due')}"])
        with tab1:
            monthly_data = get_monthly_report()
            if monthly_data:
                df_m = pd.DataFrame(monthly_data)
                df_m['amount'] = df_m['amount'].apply(lambda x: int(float(x)))
                df_chart = df_m.set_index('month_year')[['amount']]
                st.bar_chart(df_chart)
                with st.expander(f"📋 {t('মাসিক সংগ্রহ তালিকা দেখুন', 'View Monthly Collection Table')}", expanded=False):
                    df_show = df_m.copy()
                    df_show['amount'] = df_show['amount'].apply(lambda x: fmt(x))
                    df_show.columns = [t('মাস', 'Month'), t('জমা (টাকা)', 'Collection')]
                    st.dataframe(df_show, use_container_width=True, hide_index=True)
            else:
                st.info(t("কোনো ডাটা নেই", "No data"))
        with tab2:
            unpaid = get_unpaid_members()
            if unpaid:
                with st.expander(f"⚠️ {t('বকেয়া সদস্য তালিকা দেখুন', 'View Due Members List')} ({len(unpaid)} জন)", expanded=False):
                    table_data = []
                    for mu in unpaid:
                        mon_v = int(float(mu.get('monthly_savings', 500))) if mu.get('monthly_savings') else 500
                        sav_v = int(float(mu.get('total_savings', 0))) if mu.get('total_savings') else 0
                        table_data.append({
                            t('নাম', 'Name'): mu['name'],
                            t('মোবাইল', 'Mobile'): mu['phone'],
                            t('কিস্তি', 'Monthly'): fmt(mon_v),
                            t('মোট জমা', 'Savings'): fmt(sav_v)
                        })
                    df_u = pd.DataFrame(table_data)
                    st.dataframe(df_u, use_container_width=True, hide_index=True, height=350)
            else:
                st.success(f"🎉 {t('কোনো বকেয়া নেই!', 'No dues!')}")

    elif f"📥 {t('পিডিএফ ডাউনলোড', 'PDF Download')}" in menu:
        st.markdown(f"### 📥 {t('পিডিএফ ডাউনলোড', 'PDF Download')}")
        report_type = st.selectbox(t("রিপোর্ট নির্বাচন", "Select Report"), ["সদস্য তালিকা", "সব লেনদেন", "নির্দিষ্ট সদস্য"])
        if "নির্দিষ্ট" in report_type:
            members = get_all_members()
            if members:
                options = {f"{m['name']} ({m['id']})": m['id'] for m in members}
                selected = st.selectbox(t("সদস্য নির্বাচন", "Select Member"), list(options.keys()))
                if st.button("📥 PDF তৈরি করুন", type="primary"):
                    pdf = generate_pdf_transactions(options[selected])
                    st.download_button("📥 Download PDF", pdf, f"{options[selected]}_transactions.pdf", "application/pdf")
        else:
            if st.button("📥 PDF তৈরি করুন", type="primary"):
                if "সদস্য" in report_type:
                    pdf = generate_pdf_member_list()
                    st.download_button("📥 Download PDF", pdf, "member_list.pdf", "application/pdf")
                else:
                    pdf = generate_pdf_transactions()
                    st.download_button("📥 Download PDF", pdf, "all_transactions.pdf", "application/pdf")

    elif f"📧 {t('ইমেইল ব্যবস্থাপনা', 'Email Management')}" in menu:
        st.markdown(f"### 📧 {t('ইমেইল ব্যবস্থাপনা', 'Email Management')}")

        tab_test, tab_remind, tab_annual, tab_notify = st.tabs([
            f"🧪 {t('টেস্ট', 'Test')}",
            f"⏰ {t('মাসিক রিমাইন্ডার', 'Monthly Reminder')}",
            f"📊 {t('বার্ষিক রিপোর্ট', 'Annual Report')}",
            f"📢 {t('নোটিফিকেশন', 'Notification')}"
        ])

        # ── টেস্ট ──────────────────────────────────────────────────
        with tab_test:
            st.markdown(f"#### 🧪 {t('টেস্ট ইমেইল', 'Test Email')}")
            st.caption("ইমেইল সিস্টেম সঠিকভাবে কাজ করছে কিনা যাচাই করুন।")
            with st.form("form_test_email"):
                test_em = st.text_input(t("প্রাপকের ইমেইল", "Recipient Email"), placeholder="example@gmail.com")
                send_t = st.form_submit_button(f"📨 {t('পাঠান', 'Send')}", type="primary", use_container_width=True)
            if send_t:
                if not test_em or '@' not in test_em:
                    st.error(t("❌ সঠিক ইমেইল দিন।", "❌ Enter valid email."))
                else:
                    with st.spinner(t("পাঠানো হচ্ছে...", "Sending...")):
                        ok_t, msg_t = send_test_email(test_em)
                    if ok_t:
                        st.success(f"✅ {test_em} — সফলভাবে পাঠানো হয়েছে!")
                    else:
                        st.error(f"❌ ব্যর্থ: {msg_t}")

        # ── মাসিক রিমাইন্ডার ────────────────────────────────────────
        with tab_remind:
            st.markdown(f"#### ⏰ {t('মাসিক কিস্তি রিমাইন্ডার', 'Monthly Installment Reminder')}")
            st.caption("যেসব সদস্য এখনও এই মাসের কিস্তি দেননি তাদের রিমাইন্ডার ইমেইল পাঠান।")

            cur_now   = datetime.now()
            cur_mon   = BANGLA_MONTHS[cur_now.month]
            cur_year  = cur_now.year
            unpaid_em = get_unpaid_members()
            unpaid_with_email = [m for m in unpaid_em if m.get('email') and '@' in str(m.get('email',''))]

            st.info(f"📋 এই মাসে বকেয়া: **{len(unpaid_em)} জন** | ইমেইল আছে: **{len(unpaid_with_email)} জন**")

            if unpaid_with_email:
                with st.expander(f"👥 প্রাপকদের তালিকা ({len(unpaid_with_email)} জন)", expanded=False):
                    for m in unpaid_with_email:
                        st.write(f"👤 {m['name']} — {m['email']}")

            if st.button(f"📨 {len(unpaid_with_email)} জনকে রিমাইন্ডার পাঠান",
                         type="primary", use_container_width=True,
                         disabled=(len(unpaid_with_email) == 0)):
                sent_ok = sent_fail = 0
                for mem_r in unpaid_with_email:
                    mon_val = int(float(mem_r.get('monthly_savings', 500) or 500))
                    ok_r, _ = email_monthly_reminder(mem_r, cur_mon, cur_year, mon_val)
                    if ok_r: sent_ok += 1
                    else:    sent_fail += 1
                if sent_ok:
                    st.success(f"✅ {sent_ok} জনকে রিমাইন্ডার পাঠানো হয়েছে!")
                if sent_fail:
                    st.warning(f"⚠️ {sent_fail} জনকে পাঠানো যায়নি।")

            if not unpaid_with_email and unpaid_em:
                st.warning("⚠️ বকেয়া সদস্যদের ইমেইল ঠিকানা নেই।")
            elif not unpaid_em:
                st.success("🎉 এই মাসে সবাই কিস্তি দিয়েছেন!")

        # ── বার্ষিক রিপোর্ট ─────────────────────────────────────────
        with tab_annual:
            st.markdown(f"#### 📊 {t('বার্ষিক সঞ্চয় রিপোর্ট', 'Annual Savings Report')}")
            st.caption("নির্বাচিত বছরের সঞ্চয় রিপোর্ট সকল সক্রিয় সদস্যদের ইমেইলে পাঠান।")

            sel_year  = st.selectbox("বছর নির্বাচন করুন",
                                     list(range(datetime.now().year, datetime.now().year - 5, -1)),
                                     key="annual_year_sel")
            act_mems  = [m for m in get_all_members() if str(m.get('status','')) == 'active']
            em_mems   = [m for m in act_mems if m.get('email') and '@' in str(m.get('email',''))]
            all_trans = load_df(TRANSACTIONS_CSV, TRANSACTION_COLS).to_dict('records') if os.path.exists(TRANSACTIONS_CSV) else []

            st.info(f"📋 সক্রিয় সদস্য: **{len(act_mems)} জন** | ইমেইল আছে: **{len(em_mems)} জন**")

            if st.button(f"📊 {sel_year} সালের রিপোর্ট {len(em_mems)} জনকে পাঠান",
                         type="primary", use_container_width=True,
                         disabled=(len(em_mems) == 0)):
                sent_ok2 = sent_fail2 = 0
                prog = st.progress(0)
                for i, mem_a in enumerate(em_mems):
                    sav = int(float(mem_a.get('total_savings', 0) or 0))
                    ok_a, _ = email_annual_report(mem_a, sel_year, all_trans, sav)
                    if ok_a: sent_ok2 += 1
                    else:    sent_fail2 += 1
                    prog.progress((i + 1) / len(em_mems))
                if sent_ok2:
                    st.success(f"✅ {sent_ok2} জনকে বার্ষিক রিপোর্ট পাঠানো হয়েছে!")
                if sent_fail2:
                    st.warning(f"⚠️ {sent_fail2} জনকে পাঠানো যায়নি।")

        # ── কাস্টম নোটিফিকেশন ──────────────────────────────────────
        with tab_notify:
            st.markdown(f"#### 📢 {t('কাস্টম নোটিফিকেশন', 'Custom Notification')}")
            all_mems_n = get_all_members()
            em_mems_n  = [m for m in all_mems_n if m.get('email') and '@' in str(m.get('email',''))]

            recv_type = st.radio(
                t("প্রাপক", "Recipients"),
                [t("সব সদস্য", "All members"), t("নির্দিষ্ট সদস্য", "Specific member"), t("কাস্টম ইমেইল", "Custom email")],
                key="notif_recv"
            )
            target_emails = []
            if t("সব সদস্য", "All members") in recv_type:
                st.info(f"📋 {len(em_mems_n)} জন সদস্যের ইমেইল পাওয়া গেছে।")
                target_emails = [m['email'] for m in em_mems_n]
            elif t("নির্দিষ্ট সদস্য", "Specific member") in recv_type:
                if em_mems_n:
                    opts = {f"{m['name']} ({m['id']}) — {m['email']}": m['email'] for m in em_mems_n}
                    sel_n = st.selectbox(t("সদস্য নির্বাচন", "Select"), list(opts.keys()), key="notif_mem")
                    target_emails = [opts[sel_n]]
                else:
                    st.warning("⚠️ কোনো সদস্যের ইমেইল নেই।")
            else:
                raw = st.text_area(t("ইমেইল (প্রতিটি আলাদা লাইনে)", "Emails (one per line)"),
                                   placeholder="a@gmail.com\nb@gmail.com", key="notif_custom")
                if raw.strip():
                    target_emails = [e.strip() for e in raw.splitlines() if '@' in e]

            with st.form("form_notif"):
                n_subj = st.text_input(t("বিষয়", "Subject"), value=f"📢 {SOMITI_NAME} — বিজ্ঞপ্তি")
                n_body = st.text_area(t("বার্তা", "Message"), height=150,
                                      placeholder="এখানে বার্তা লিখুন...")
                send_n = st.form_submit_button(f"📨 {t('পাঠান', 'Send')}", type="primary", use_container_width=True)

            if send_n:
                if not target_emails:
                    st.error("❌ কোনো প্রাপক নেই।")
                elif not n_body.strip():
                    st.error("❌ বার্তা লিখুন।")
                else:
                    with st.spinner(f"{len(target_emails)} জনকে পাঠানো হচ্ছে..."):
                        res = send_notification_email(target_emails, n_subj, n_body)
                    ok_n  = [r for r in res if r['ok']]
                    bad_n = [r for r in res if not r['ok']]
                    if ok_n:
                        st.success(f"✅ {len(ok_n)} জনকে পাঠানো হয়েছে!")
                    if bad_n:
                        st.error(f"❌ {len(bad_n)} জনকে পাঠানো যায়নি।")
                        with st.expander("ব্যর্থ তালিকা"):
                            for r in bad_n:
                                st.write(f"❌ {r['email']} — {r['msg']}")

    elif f"🎲 {t('লটারি', 'Lottery')}" in menu:
        st.markdown(f"### 🎲 {t('লটারি', 'Lottery')}")
        if st.button("🎲 বিজয়ী নির্বাচন করুন", type="primary"):
            winner = pick_lottery_winner()
            if winner:
                st.balloons()
                st.success(f"🎉 বিজয়ী: {winner['name']} (আইডি: {winner['id']})")
                # ── লটারি বিজয়ী ইমেইল ──
                if winner.get('email') and '@' in str(winner.get('email','')):
                    cur_m = datetime.now()
                    ok_l, _ = email_lottery_winner(winner, BANGLA_MONTHS[cur_m.month], cur_m.year)
                    if ok_l:
                        st.info(f"📧 বিজয়ী {winner['name']}-কে অভিনন্দন ইমেইল পাঠানো হয়েছে।")
            else:
                st.error(t("কোনো সক্রিয় সদস্য নেই", "No active members"))

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
    process_email_queue()   # ← pending ইমেইল পাঠায়
    member = get_member_by_id(st.session_state.member_id)
    if not member:
        st.error("Member not found")
        return

    total_savings = int(float(member.get('total_savings', 0))) if member.get('total_savings') else 0
    monthly = int(float(member.get('monthly_savings', 500))) if member.get('monthly_savings') else 500

    st.markdown(f"""
    <div class="somiti-header">
        <h1>🌾 {SOMITI_NAME} 🌾</h1>
        <p>{t('সদস্য ড্যাশবোর্ড', 'Member Dashboard')}</p>
    </div>
    <div class="total-box">
        <h2>💰 {fmt(total_savings)} {t('টাকা', 'Taka')}</h2>
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
        col1.metric("বর্তমান জমা", f"{fmt(total_savings)} টাকা")
        col2.metric("মাসিক কিস্তি", f"{fmt(monthly)} টাকা")

        current = datetime.now()
        trans = get_member_transactions(member['id'])
        paid_amt = sum(int(float(tr['amount'])) for tr in trans if tr.get('month') == current.month and tr.get('year') == current.year)

        if paid_amt >= monthly:
            st.success(f"✅ {BANGLA_MONTHS[current.month]} {current.year} মাসের কিস্তি পরিশোধ করেছেন")
        else:
            st.warning(f"⚠️ বকেয়া: {fmt(monthly - paid_amt)} টাকা")

        st.markdown("---")
        st.markdown("#### 📋 লেনদেন ইতিহাস")
        if trans:
            table_data = []
            for tr in trans[:20]:
                amount = int(float(tr['amount'])) if tr.get('amount') else 0
                table_data.append({
                    "তারিখ": tr.get('full_date', ''),
                    "পরিমাণ": fmt(amount),
                    "মাস": tr.get('month_name', '')
                })
            df_tr = pd.DataFrame(table_data)
            st.dataframe(df_tr, use_container_width=True, hide_index=True, height=350)
        else:
            st.info("কোনো লেনদেন নেই")

    with tab2:
        new_pass = st.text_input("নতুন পাসওয়ার্ড", type="password")
        confirm = st.text_input("নিশ্চিত করুন", type="password")
        if st.button("আপডেট করুন", type="primary"):
            if new_pass and new_pass == confirm:
                update_member(member['id'], {'password': new_pass})
                st.success("✅ পাসওয়ার্ড পরিবর্তন হয়েছে!")
                # ── পাসওয়ার্ড পরিবর্তন ইমেইল ──
                if member.get('email') and '@' in str(member.get('email','')):
                    email_password_changed(member, new_pass)
            else:
                st.error("❌ পাসওয়ার্ড মিলছে না")

    with tab3:
        if st.button("📥 পিডিএফ ডাউনলোড করুন", type="primary"):
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
