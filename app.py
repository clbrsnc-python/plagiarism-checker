import streamlit as st
import re
import math
import os
import json
import hashlib
from datetime import datetime
from duckduckgo_search import DDGS
from pypdf import PdfReader
from docx import Document
from fpdf import FPDF

# --- User Management & JSON Storage Helper ---
USER_DB_FILE = "registered_users.json"
ADMIN_PASSCODE = "Joydip.Chandra@1953"

def load_user_db():
    if not os.path.exists(USER_DB_FILE):
        return {}
    try:
        with open(USER_DB_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}

def save_user_db(db):
    try:
        with open(USER_DB_FILE, "w") as f:
            json.dump(db, f, indent=2)
    except Exception:
        pass

def hash_str(val):
    return hashlib.sha256(val.strip().lower().encode("utf-8")).hexdigest()

# --- Text Extraction Helper ---
def extract_text(file):
    if file is None:
        return ""
    filename = file.name.lower()
    if filename.endswith(".txt"):
        return file.read().decode("utf-8", errors="ignore")
    elif filename.endswith(".pdf"):
        pdf = PdfReader(file)
        return " ".join([page.extract_text() or "" for page in pdf.pages])
    elif filename.endswith(".docx"):
        doc = Document(file)
        return " ".join([p.text for p in doc.paragraphs])
    return ""

# --- Zero-API AI Content Detector ---
AI_SIGNATURE_WORDS = [
    "delve", "tapestry", "pivotal", "testament", "fostering", "vibrant", 
    "underscore", "holistic", "paramount", "in conclusion", "furthermore", 
    "it is important to note", "crucial role", "multifaceted", "ever-evolving",
    "beacon", "synergy", "realm", "endeavor", "interplay", "garnered"
]

def analyze_ai_patterns(text):
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if len(s.strip()) > 10]
    words = re.findall(r'\b\w+\b', text.lower())
    
    if len(words) < 20 or not sentences:
        return 0.0, [], []

    ai_word_count = sum(1 for w in words if w in AI_SIGNATURE_WORDS)
    vocab_ai_density = (ai_word_count / len(words)) * 100

    sent_lengths = [len(s.split()) for s in sentences]
    avg_len = sum(sent_lengths) / len(sent_lengths)
    variance = sum((l - avg_len) ** 2 for l in sent_lengths) / len(sent_lengths)
    std_dev = math.sqrt(variance)

    ai_flagged_sentences = []
    sentence_analysis = []

    for sent in sentences:
        sent_lower = sent.lower()
        has_ai_word = any(w in sent_lower for w in AI_SIGNATURE_WORDS)
        length_fits_ai = 12 <= len(sent.split()) <= 32
        
        is_ai = has_ai_word or (length_fits_ai and std_dev < 5.0)
        if is_ai:
            ai_flagged_sentences.append(sent)
        
        sentence_analysis.append({
            "sentence": sent,
            "word_count": len(sent.split()),
            "is_ai": is_ai,
            "reason": "AI Signature Keyword" if has_ai_word else ("Uniform AI Rhythm" if is_ai else "Natural Human Flow")
        })

    base_score = 30 if len(ai_flagged_sentences) > 0 else 5
    ai_sentence_ratio = (len(ai_flagged_sentences) / max(1, len(sentences))) * 50
    vocab_weight = min(30, vocab_ai_density * 15)
    uniformity_weight = max(0, (6.0 - std_dev) * 6)

    total_ai_prob = base_score + ai_sentence_ratio + vocab_weight + uniformity_weight
    final_score = round(max(5.0, min(98.0, total_ai_prob)), 1)

    return final_score, ai_flagged_sentences, sentence_analysis

# --- Zero-API Web Plagiarism Search ---
def check_web_plagiarism(text, max_queries=8):
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if len(s.split()) >= 6]
    if not sentences:
        return 0.0, [], []

    step = max(1, len(sentences) // max_queries)
    selected_queries = sentences[::step][:max_queries]

    matches = []
    flagged_phrases = []
    matched_queries_count = 0

    try:
        ddgs = DDGS()
        for query in selected_queries:
            try:
                results = list(ddgs.text(f'"{query}"', max_results=2))
                if results:
                    matched_queries_count += 1
                    for res in results:
                        title = res.get("title", "Web Source Match")
                        url = res.get("href", "#")
                        snippet = res.get("body", "")
                        matches.append({"phrase": query, "title": title, "url": url, "snippet": snippet})
                        flagged_phrases.append((query, url))
            except Exception:
                continue
    except Exception:
        pass

    plagiarism_score = round((matched_queries_count / max(1, len(selected_queries))) * 100, 1)
    return plagiarism_score, matches, flagged_phrases

# --- High-Contrast Highlighting ---
def render_highlighted_document(full_text, ai_sentences, web_flagged_phrases):
    highlighted_text = full_text

    for phrase, url in web_flagged_phrases:
        escaped_phrase = re.escape(phrase)
        replacement = f'<mark style="background: rgba(239, 68, 68, 0.3); color: #fca5a5; padding: 3px 8px; border-radius: 6px; border: 1px solid #ef4444; font-weight: 600;"><b>[Web Match]</b> {phrase} <a href="{url}" target="_blank" style="color: #38bdf8; text-decoration: underline; font-weight: 700;">(Source 🔗)</a></mark>'
        highlighted_text = re.sub(escaped_phrase, replacement, highlighted_text)

    for sent in ai_sentences:
        escaped_sent = re.escape(sent)
        replacement = f'<mark style="background: rgba(245, 158, 11, 0.3); color: #fef08a; padding: 3px 8px; border-radius: 6px; border: 1px solid #f59e0b; font-weight: 600;"><b>[AI Flagged]</b> {sent}</mark>'
        highlighted_text = re.sub(escaped_sent, replacement, highlighted_text)

    return highlighted_text

# --- PDF Helpers (Bulletproof Margin Protection) ---
def clean_pdf_str(text):
    if not text:
        return ""
    replacements = {
        '“': '"', '”': '"', '‘': "'", '’': "'", '—': '-', '–': '-',
        '…': '...', '•': '*', '–': '-', '—': '-'
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text.encode('latin-1', 'replace').decode('latin-1')

def wrap_long_words(text, max_len=32):
    if not text:
        return ""
    words = text.split(" ")
    wrapped = []
    for w in words:
        if len(w) > max_len:
            chunks = [w[i:i+max_len] for i in range(0, len(w), max_len)]
            wrapped.append(" ".join(chunks))
        else:
            wrapped.append(w)
    return " ".join(wrapped)

def create_pdf_report(ai_prob, plag_prob, web_matches, doc_stats, user_email=""):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_margins(15, 15, 15)

    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 10, clean_pdf_str("WriteSafe Audit Report"), new_x="LMARGIN", new_y="NEXT", align="C")
    
    pdf.set_font("Helvetica", "I", 10)
    pdf.set_text_color(100, 116, 139)
    sub_title = "Catch plagiarism and AI-sounding text before you submit."
    if user_email:
        sub_title += f" | Verified User: {user_email}"
    pdf.cell(0, 6, clean_pdf_str(sub_title), new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(4)

    pdf.set_draw_color(226, 232, 240)
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(6)

    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 8, clean_pdf_str("1. Executive Summary"), new_x="LMARGIN", new_y="NEXT")
    
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(51, 65, 85)
    pdf.multi_cell(0, 6, clean_pdf_str(f"- Estimated AI Generation Probability: {ai_prob}%"), new_x="LMARGIN", new_y="NEXT")
    pdf.multi_cell(0, 6, clean_pdf_str(f"- Estimated Web Similarity / Plagiarism Score: {plag_prob}%"), new_x="LMARGIN", new_y="NEXT")
    pdf.multi_cell(0, 6, clean_pdf_str(f"- Total Words Analyzed: {doc_stats['word_count']}"), new_x="LMARGIN", new_y="NEXT")
    pdf.multi_cell(0, 6, clean_pdf_str(f"- Total Sentences Analyzed: {doc_stats['sentence_count']}"), new_x="LMARGIN", new_y="NEXT")
    pdf.multi_cell(0, 6, clean_pdf_str(f"- Public Web Sources Matched: {len(web_matches)}"), new_x="LMARGIN", new_y="NEXT")

    pdf.ln(6)
    pdf.set_draw_color(226, 232, 240)
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(6)

    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 8, clean_pdf_str("2. Public Web Matches Breakdown"), new_x="LMARGIN", new_y="NEXT")

    if web_matches:
        for idx, match in enumerate(web_matches, 1):
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(30, 58, 138)
            title = wrap_long_words(clean_pdf_str(match.get('title', 'Web Match')))
            pdf.multi_cell(0, 6, clean_pdf_str(f'Match #{idx}: {title}'), new_x="LMARGIN", new_y="NEXT")
            
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(71, 85, 105)
            phrase = wrap_long_words(clean_pdf_str(match.get('phrase', '')))
            url = wrap_long_words(clean_pdf_str(match.get('url', ''), max_len=30))
            
            pdf.multi_cell(0, 5, clean_pdf_str(f'Matched Phrase: "{phrase}"'), new_x="LMARGIN", new_y="NEXT")
            pdf.multi_cell(0, 5, clean_pdf_str(f'Source URL: {url}'), new_x="LMARGIN", new_y="NEXT")
            pdf.ln(3)
    else:
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(71, 85, 105)
        pdf.multi_cell(0, 6, clean_pdf_str("No direct matching public web sources detected."), new_x="LMARGIN", new_y="NEXT")

    pdf.ln(10)
    pdf.set_draw_color(226, 232, 240)
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(6)

    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 6, clean_pdf_str("Crafted by: Dr. Joydip Chandra, BRSC"), new_x="LMARGIN", new_y="NEXT", align="C")
    
    return bytes(pdf.output())

# --- Page Config & Custom Palette CSS ---
st.set_page_config(page_title="WriteSafe Studio", layout="wide", page_icon="✨")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    
    /* Background: Deep Purple-Slate */
    .stApp {
        background-color: #0f0b1e;
        color: #f8fafc;
    }

    /* Force all Streamlit labels, uploaders, instructions & texts to be crystal clear */
    label, .stMarkdown, p, span, div, h1, h2, h3, h4, h5, h6, .stCaption {
        color: #f1f5f9 !important;
    }

    /* File Uploader Custom Styling */
    [data-testid="stFileUploader"] {
        background: #1a1532;
        border: 2px dashed #38bdf8;
        border-radius: 16px;
        padding: 20px;
        box-shadow: 0 8px 20px rgba(56, 189, 248, 0.15);
    }
    [data-testid="stFileUploader"] section {
        background-color: transparent !important;
    }
    [data-testid="stFileUploader"] label {
        color: #38bdf8 !important;
        font-size: 16px !important;
        font-weight: 700 !important;
    }

    /* Text Area & Text Inputs Styling */
    .stTextArea textarea, .stTextInput input {
        background-color: #1a1532 !important;
        color: #f8fafc !important;
        border: 1px solid #38bdf8 !important;
        border-radius: 12px !important;
        font-size: 15px !important;
    }

    /* Primary & Custom Buttons (Includes Hover Contrast Protection) */
    .stButton button, [data-testid="stFileUploader"] button, div[data-testid="stDownloadButton"] button {
        background: linear-gradient(135deg, #0ea5e9 0%, #8b5cf6 50%, #14b8a6 100%) !important;
        color: #ffffff !important;
        font-weight: 800 !important;
        font-size: 16px !important;
        border-radius: 14px !important;
        border: none !important;
        box-shadow: 0 10px 25px rgba(14, 165, 233, 0.3) !important;
        padding: 12px 24px !important;
        transition: all 0.3s ease !important;
    }

    .stButton button:hover, [data-testid="stFileUploader"] button:hover, div[data-testid="stDownloadButton"] button:hover {
        background: linear-gradient(135deg, #0284c7 0%, #7e22ce 50%, #0d9488 100%) !important;
        color: #ffffff !important;
        box-shadow: 0 12px 28px rgba(2, 132, 199, 0.5) !important;
        border: 1px solid #38bdf8 !important;
    }

    /* Hero Banner: Purple & Sky Blue Gradient */
    .palette-hero {
        background: linear-gradient(135deg, #2e1065 0%, #581c87 40%, #0f766e 100%);
        padding: 30px 28px;
        border-radius: 22px;
        border: 2px solid #38bdf8;
        box-shadow: 0 15px 35px rgba(168, 85, 247, 0.25);
        margin-bottom: 24px;
    }
    
    .golden-badge {
        background: linear-gradient(90deg, #f59e0b 0%, #fbbf24 100%);
        color: #0f172a;
        font-size: 12px;
        font-weight: 800;
        padding: 5px 14px;
        border-radius: 20px;
        display: inline-block;
        margin-bottom: 10px;
        letter-spacing: 0.8px;
        box-shadow: 0 4px 12px rgba(245, 158, 11, 0.4);
    }
    
    .palette-title {
        font-size: 36px;
        font-weight: 800;
        margin: 0;
        color: #ffffff !important;
        letter-spacing: -0.5px;
    }
    
    .palette-tagline {
        font-size: 15px;
        color: #2dd4bf !important;
        margin-top: 8px;
        font-weight: 600;
    }

    /* Mobile Tip Banner */
    .mobile-tip-banner {
        background: #1e1b4b;
        border: 1px solid #38bdf8;
        border-radius: 12px;
        padding: 10px 16px;
        color: #38bdf8 !important;
        font-size: 13px;
        font-weight: 600;
        margin-bottom: 18px;
    }

    /* Metric Cards */
    .metric-card-palette {
        background: #1a1532;
        padding: 20px;
        border-radius: 18px;
        border: 1px solid #38bdf8;
        box-shadow: 0 10px 25px rgba(0, 0, 0, 0.3);
        text-align: center;
    }
    .metric-title-palette {
        font-size: 13px;
        color: #2dd4bf !important;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .metric-value-palette {
        font-size: 42px;
        font-weight: 800;
        margin: 8px 0;
    }

    /* Document Stats Bar */
    .palette-stats-bar {
        background: #1a1532;
        border-radius: 16px;
        border: 1px solid #8b5cf6;
        padding: 16px 20px;
        display: flex;
        justify-content: space-around;
        margin-bottom: 24px;
    }
    .palette-stat-num {
        font-size: 22px;
        font-weight: 800;
        color: #38bdf8 !important;
    }
    .palette-stat-lbl {
        font-size: 12px;
        color: #fbbf24 !important;
        font-weight: 600;
    }

    /* Marked Reader Canvas */
    .palette-marked-canvas {
        background: #130f26;
        padding: 26px;
        border-radius: 18px;
        border: 1px solid #38bdf8;
        line-height: 2.2;
        font-size: 16px;
        color: #f8fafc !important;
    }

    /* Sidebar Custom Containers */
    [data-testid="stSidebar"] {
        background-color: #130e2a !important;
        border-right: 1px solid #38bdf8;
    }
    .sidebar-brand-card {
        background: #1a1538;
        border: 1px solid #38bdf8;
        padding: 16px;
        border-radius: 16px;
        margin-bottom: 16px;
        color: #f8fafc !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- Session State Initialization ---
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "user_email" not in st.session_state:
    st.session_state["user_email"] = ""
if "user_name" not in st.session_state:
    st.session_state["user_name"] = ""
if "admin_unlocked" not in st.session_state:
    st.session_state["admin_unlocked"] = False

db = load_user_db()

# --- Sidebar Content ---
st.sidebar.markdown("""
    <div class="sidebar-brand-card">
        <div style="font-size: 22px; font-weight: 800; color: #38bdf8;">✨ WriteSafe Studio</div>
        <div style="font-size: 13px; color: #2dd4bf; margin-top: 6px; font-weight: 600;">
            Evaluates research drafts, essays, and documents for AI generation patterns and searches public domain web databases in real-time.
        </div>
        <div style="margin-top: 12px; font-size: 13px; font-weight: 800; color: #fbbf24;">
            👑 Crafted by: Dr. Joydip Chandra, BRSC
        </div>
    </div>
""", unsafe_allow_html=True)

st.sidebar.caption("⚡ Fast • 🔒 Private • 🎓 Academic Ready")
st.sidebar.markdown("<hr style='border-color: #38bdf8;'>", unsafe_allow_html=True)

# --- Sidebar Admin Passcode Input ---
with st.sidebar.expander("🔐 Secret Admin Access", expanded=False):
    passcode_input = st.text_input("Enter Admin Passcode:", type="password", key="admin_passcode_field")
    if st.button("Unlock Admin Panel", key="btn_unlock_admin"):
        if passcode_input == ADMIN_PASSCODE:
            st.session_state["admin_unlocked"] = True
            st.success("✅ Admin Access Granted!")
            st.rerun()
        else:
            st.error("❌ Invalid Admin Passcode.")

if st.session_state["logged_in"]:
    st.sidebar.success(f"👤 Logged in as: **{st.session_state['user_name']}**")
    if st.sidebar.button("🚪 Sign Out"):
        st.session_state["logged_in"] = False
        st.session_state["user_email"] = ""
        st.session_state["user_name"] = ""
        st.rerun()

# --- Main App Header Banner ---
st.markdown("""
    <div class="palette-hero">
        <div class="golden-badge">✨ NO-CAP AI & PLAGIARISM CHECKER</div>
        <div class="palette-title">🛡️ WriteSafe</div>
        <div class="palette-tagline">“Catch plagiarism and AI-sounding text before you submit.”</div>
    </div>
""", unsafe_allow_html=True)

# Mobile responsiveness guidance tip
st.markdown("""
    <div class="mobile-tip-banner">
        📱 <b>Mobile Tip:</b> If using a mobile device, tap the <b>&gt;</b> icon at the top-left of your screen to open the menu.
    </div>
""", unsafe_allow_html=True)

# --- Admin Panel View (If Admin Passcode Unlocked) ---
if st.session_state["admin_unlocked"]:
    st.markdown("---")
    st.subheader("👑 Secret Admin User Directory & App Usage Stats")
    st.caption("Protected Admin View — Active User Database")

    if db:
        user_data_list = []
        for email, info in db.items():
            user_data_list.append({
                "Full Name": info.get("name", "N/A"),
                "Email Address": email,
                "Registered Date": info.get("created_at", "N/A"),
                "Total Scans": info.get("scan_count", 0),
                "Last Active": info.get("last_active", "N/A")
            })

        st.dataframe(user_data_list, use_container_width=True)

        csv_lines = ["Full Name,Email Address,Registered Date,Total Scans,Last Active\n"]
        for row in user_data_list:
            csv_lines.append(f'"{row["Full Name"]}","{row["Email Address"]}","{row["Registered Date"]}",{row["Total Scans"]},"{row["Last Active"]}"\n')
        csv_data = "".join(csv_lines)

        st.download_button(
            label="📥 Download Registered Users Directory (CSV)",
            data=csv_data,
            file_name="WriteSafe_Registered_Users_Directory.csv",
            mime="text/csv"
        )
    else:
        st.info("No registered users logged in the database yet.")

    st.markdown("---")

# --- Authentication Gate (If Not Logged In) ---
if not st.session_state["logged_in"]:
    st.subheader("🔑 User Account Authentication")
    st.write("Please sign in or create an account to access WriteSafe:")

    auth_tab1, auth_tab2, auth_tab3 = st.tabs(["🔑 Sign In", "📝 First-Time Registration", "🔓 Forgot Password"])

    # --- TAB 1: SIGN IN ---
    with auth_tab1:
        login_email = st.text_input("Email Address:", key="login_email_input").strip().lower()
        login_pass = st.text_input("Password:", type="password", key="login_pass_input")

        if st.button("🚀 Sign In & Unlock Workspace", type="primary", key="btn_signin"):
            if not login_email or not login_pass:
                st.warning("Please enter both your email and password.")
            elif login_email not in db:
                st.error("No account found with this email. Please register first.")
            else:
                user_info = db[login_email]
                if user_info.get("password_hash") == hash_str(login_pass):
                    st.session_state["logged_in"] = True
                    st.session_state["user_email"] = login_email
                    st.session_state["user_name"] = user_info.get("name", "User")
                    
                    # Update last active
                    db[login_email]["last_active"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    save_user_db(db)

                    st.success(f"Welcome back, {st.session_state['user_name']}!")
                    st.rerun()
                else:
                    st.error("Incorrect password. Please try again or use Forgot Password.")

    # --- TAB 2: REGISTRATION ---
    with auth_tab2:
        reg_name = st.text_input("Full Name:", key="reg_name_input").strip()
        reg_email = st.text_input("Email Address:", key="reg_email_input").strip().lower()
        reg_pass = st.text_input("Create Password:", type="password", key="reg_pass_input")
        reg_pass_confirm = st.text_input("Confirm Password:", type="password", key="reg_pass_confirm_input")
        
        st.caption("🔒 Security Question (for password recovery):")
        sec_question = st.selectbox("Select a Security Question:", [
            "What was the name of your first school?",
            "What is your favorite subject or topic?",
            "In what city or town were you born?",
            "What is the name of your favorite book or paper?"
        ], key="reg_sec_q")
        sec_answer = st.text_input("Your Security Answer:", key="reg_sec_a").strip().lower()

        if st.button("✨ Register Account", type="primary", key="btn_register"):
            if not reg_name or not reg_email or not reg_pass or not sec_answer:
                st.warning("Please fill out all registration fields.")
            elif "@" not in reg_email or "." not in reg_email:
                st.error("Please enter a valid email address.")
            elif reg_pass != reg_pass_confirm:
                st.error("Passwords do not match.")
            elif len(reg_pass) < 6:
                st.error("Password should be at least 6 characters long.")
            else:
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                db[reg_email] = {
                    "name": reg_name,
                    "password_hash": hash_str(reg_pass),
                    "sec_question": sec_question,
                    "sec_answer_hash": hash_str(sec_answer),
                    "created_at": now_str,
                    "last_active": now_str,
                    "scan_count": 0
                }
                save_user_db(db)

                st.session_state["logged_in"] = True
                st.session_state["user_email"] = reg_email
                st.session_state["user_name"] = reg_name
                st.success(f"🎉 Account created successfully! Welcome, {reg_name}!")
                st.rerun()

    # --- TAB 3: FORGOT PASSWORD ---
    with auth_tab3:
        fp_email = st.text_input("Registered Email Address:", key="fp_email_input").strip().lower()
        
        if fp_email in db:
            q_text = db[fp_email].get("sec_question", "Security Answer")
            st.info(f"Security Question: **{q_text}**")
            fp_answer = st.text_input("Enter Security Answer:", key="fp_answer_input").strip().lower()
            new_pass = st.text_input("Enter New Password:", type="password", key="fp_new_pass")
            new_pass_confirm = st.text_input("Confirm New Password:", type="password", key="fp_new_pass_confirm")

            if st.button("🔑 Reset Password", key="btn_reset_pass"):
                if not fp_answer or not new_pass:
                    st.warning("Please fill out all required fields.")
                elif db[fp_email].get("sec_answer_hash") != hash_str(fp_answer):
                    st.error("Incorrect security answer.")
                elif new_pass != new_pass_confirm:
                    st.error("New passwords do not match.")
                elif len(new_pass) < 6:
                    st.error("Password must be at least 6 characters long.")
                else:
                    db[fp_email]["password_hash"] = hash_str(new_pass)
                    save_user_db(db)
                    st.success("✅ Password reset successfully! You can now Sign In with your new password.")
        elif fp_email:
            st.error("No account found with this email address.")

    st.stop()

# --- MAIN WORKSPACE (Accessible After Sign In) ---
st.subheader("📄 Document Audit Workspace")

uploaded_file = st.file_uploader("📁 Upload Draft Document (.pdf, .docx, .txt)", type=["pdf", "docx", "txt"])
pasted_text = st.text_area("📝 Or paste your draft text directly below:", height=170, placeholder="Paste your essay or research paper text here...")

document_text = extract_text(uploaded_file) if uploaded_file else pasted_text

if st.button("🚀 Run WriteSafe Audit", type="primary", use_container_width=True):
    if not document_text.strip():
        st.warning("Please upload a file or paste text first.")
    else:
        # Increment scan count
        curr_user = st.session_state.get("user_email")
        if curr_user and curr_user in db:
            db[curr_user]["scan_count"] = db[curr_user].get("scan_count", 0) + 1
            db[curr_user]["last_active"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            save_user_db(db)

        st.markdown("<br>", unsafe_allow_html=True)

        with st.spinner("Auditing AI vocabulary patterns & searching public web sources..."):
            ai_score, ai_sents, sentence_analysis = analyze_ai_patterns(document_text)
            plag_score, web_matches, web_phrases = check_web_plagiarism(document_text)

        words = re.findall(r'\b\w+\b', document_text)
        sentences = [s.strip() for s in re.split(r'[.!?]+', document_text) if s.strip()]
        doc_stats = {
            "word_count": len(words),
            "sentence_count": len(sentences),
            "ai_flagged_count": len(ai_sents),
            "web_matches_count": len(web_matches)
        }

        # --- Score Dashboard ---
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(f"""
                <div class="metric-card-palette">
                    <div class="metric-title-palette">🤖 Estimated AI Probability</div>
                    <div class="metric-value-palette" style="color: {'#ef4444' if ai_score > 60 else '#f59e0b' if ai_score > 35 else '#2dd4bf'};">{ai_score}%</div>
                </div>
            """, unsafe_allow_html=True)
            if ai_score > 60:
                st.error("⚠️ High likelihood of machine-generated text.")
            elif ai_score > 35:
                st.warning("⚡ Moderate AI influence or mixed editing.")
            else:
                st.success("✅ Content displays natural human writing variation.")

        with col2:
            st.markdown(f"""
                <div class="metric-card-palette">
                    <div class="metric-title-palette">🌐 Estimated Plagiarism / Web Score</div>
                    <div class="metric-value-palette" style="color: {'#ef4444' if plag_score > 50 else '#f59e0b' if plag_score > 20 else '#2dd4bf'};">{plag_score}%</div>
                </div>
            """, unsafe_allow_html=True)
            if plag_score > 50:
                st.error(f"⚠️ High similarity across {len(web_matches)} web sources.")
            elif plag_score > 20:
                st.warning(f"⚡ Moderate similarity across {len(web_matches)} web sources.")
            else:
                st.success("✅ Low or no public web overlap detected.")

        st.markdown("<br>", unsafe_allow_html=True)

        # --- Document Stats Bar ---
        st.markdown(f"""
            <div class="palette-stats-bar">
                <div style="text-align: center;"><div class="palette-stat-num">{doc_stats['word_count']}</div><div class="palette-stat-lbl">Words</div></div>
                <div style="text-align: center;"><div class="palette-stat-num">{doc_stats['sentence_count']}</div><div class="palette-stat-lbl">Sentences</div></div>
                <div style="text-align: center;"><div class="palette-stat-num" style="color: #f59e0b !important;">{doc_stats['ai_flagged_count']}</div><div class="palette-stat-lbl">AI Sentences</div></div>
                <div style="text-align: center;"><div class="palette-stat-num" style="color: #ef4444 !important;">{doc_stats['web_matches_count']}</div><div class="palette-stat-lbl">Web Matches</div></div>
            </div>
        """, unsafe_allow_html=True)

        # --- Tabs View ---
        tab1, tab2, tab3, tab4 = st.tabs([
            "🖍️ Marked Document Reader", 
            "🌐 Web Source Overlaps", 
            "📊 Sentence Analysis",
            "📄 Export PDF Report"
        ])

        with tab1:
            st.caption("🟨 **Golden Highlight** = AI-flagged sentence pattern | 🟥 **Red Highlight** = Web source match (with source link)")
            highlighted_html = render_highlighted_document(document_text, ai_sents, web_phrases)
            st.markdown(f'<div class="palette-marked-canvas">{highlighted_html}</div>', unsafe_allow_html=True)

        with tab2:
            if web_matches:
                st.subheader(f"Found {len(web_matches)} Matching Web Sources")
                for idx, match in enumerate(web_matches, 1):
                    with st.expander(f"Match #{idx}: {match['title']}"):
                        st.write(f'**Matched Text Fragment:** "{match["phrase"]}"')
                        st.write(f'**Direct URL:** [{match["url"]}]({match["url"]})')
                        if match.get('snippet'):
                            st.caption(f'**Web Snippet:** {match["snippet"]}')
            else:
                st.success("🎉 No matching public domain sources detected for the sampled phrases.")

        with tab3:
            st.subheader("Sentence-by-Sentence AI Evaluation")
            for idx, item in enumerate(sentence_analysis, 1):
                status_icon = "🔴 AI Flagged" if item["is_ai"] else "🟢 Human Flow"
                with st.expander(f"Sentence #{idx} ({item['word_count']} words) — {status_icon}"):
                    st.write(f'"{item["sentence"]}"')
                    st.caption(f'**Evaluation Detail:** {item["reason"]}')

        with tab4:
            st.subheader("Download Verified Summary Report")
            st.write("Generate and download a formal audit report suitable for submission or records:")
            try:
                pdf_bytes = create_pdf_report(ai_score, plag_score, web_matches, doc_stats, st.session_state.get('user_email', ''))
                st.download_button(
                    label="📥 Download WriteSafe PDF Summary Report",
                    data=pdf_bytes,
                    file_name="WriteSafe_Plagiarism_AI_Analysis_Report.pdf",
                    mime="application/pdf",
                    type="primary"
                )
            except Exception as e:
                st.error(f"Could not generate PDF: {e}")
