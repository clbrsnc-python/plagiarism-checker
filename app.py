import streamlit as st
import re
import math
import json
import os
import hashlib
from datetime import datetime
from duckduckgo_search import DDGS
from pypdf import PdfReader
from docx import Document
from fpdf import FPDF

# --- Database & User Management Helpers ---
USERS_FILE = "registered_users.json"
ADMIN_PASSCODE = "Joydip.Chandra@1953"

SECURITY_QUESTIONS = [
    "What was the name of your first school?",
    "What is your mother's maiden name?",
    "What city were you born in?",
    "What was the name of your first pet?",
    "What is your favorite book or author?",
    "What was your childhood nickname?"
]

def load_users():
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_users(users):
    try:
        with open(USERS_FILE, "w") as f:
            json.dump(users, f, indent=2)
    except Exception as e:
        st.error(f"Error saving user data: {e}")

def hash_str(s):
    if not s:
        return ""
    return hashlib.sha256(s.strip().lower().encode("utf-8")).hexdigest()

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

# --- PDF Helpers ---
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

def create_pdf_report(ai_prob, plag_prob, web_matches, doc_stats, user_email="Anonymous"):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_margins(15, 15, 15)

    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 10, clean_pdf_str("WriteSafe Audit Report"), new_x="LMARGIN", new_y="NEXT", align="C")
    
    pdf.set_font("Helvetica", "I", 10)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(0, 6, clean_pdf_str("Catch plagiarism and AI-sounding text before you submit."), new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(4)

    pdf.set_draw_color(226, 232, 240)
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(6)

    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 8, clean_pdf_str("1. Executive Summary"), new_x="LMARGIN", new_y="NEXT")
    
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(51, 65, 85)
    pdf.multi_cell(0, 6, clean_pdf_str(f"- Verified User Account: {user_email}"), new_x="LMARGIN", new_y="NEXT")
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
st.set_page_config(page_title="WriteSafe", layout="wide", page_icon="✨")

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

    /* Streamlit Password Visibility Eye Icon Fix */
    [data-testid="stTextInput"] button,
    button[aria-label="Show password"],
    button[aria-label="Hide password"],
    [data-testid="stTextInput"] svg {
        color: #38bdf8 !important;
        fill: #38bdf8 !important;
        stroke: #38bdf8 !important;
        opacity: 1 !important;
        visibility: visible !important;
    }
    [data-testid="stTextInput"] button:hover {
        background-color: rgba(56, 189, 248, 0.25) !important;
        border-radius: 8px !important;
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
    [data-testid="stFileUploader"] button {
        background: linear-gradient(135deg, #0ea5e9 0%, #a855f7 100%) !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 10px !important;
        font-weight: 700 !important;
    }
    [data-testid="stFileUploader"] button:hover {
        background: linear-gradient(135deg, #0284c7 0%, #7e22ce 100%) !important;
        color: #ffffff !important;
    }

    /* Download Buttons Hover Fix */
    div[data-testid="stDownloadButton"] button {
        background: linear-gradient(135deg, #0ea5e9 0%, #8b5cf6 50%, #14b8a6 100%) !important;
        color: #ffffff !important;
        font-weight: 800 !important;
    }
    div[data-testid="stDownloadButton"] button:hover {
        background: linear-gradient(135deg, #0284c7 0%, #6d28d9 100%) !important;
        color: #ffffff !important;
    }

    /* Text Area & Input Styling */
    .stTextArea textarea, .stTextInput input, select {
        background-color: #1a1532 !important;
        color: #f8fafc !important;
        border: 1px solid #a855f7 !important;
        border-radius: 12px !important;
        font-size: 15px !important;
    }
    .stTextArea label, .stTextInput label, .stSelectbox label {
        color: #2dd4bf !important;
        font-weight: 700 !important;
        font-size: 15px !important;
    }

    /* Primary Buttons */
    .stButton button {
        background: linear-gradient(135deg, #0ea5e9 0%, #8b5cf6 50%, #14b8a6 100%) !important;
        color: #ffffff !important;
        font-weight: 800 !important;
        font-size: 18px !important;
        border-radius: 14px !important;
        border: none !important;
        box-shadow: 0 10px 25px rgba(14, 165, 233, 0.3) !important;
        padding: 12px 24px !important;
    }
    .stButton button:hover {
        background: linear-gradient(135deg, #0284c7 0%, #6d28d9 50%, #0d9488 100%) !important;
        color: #ffffff !important;
    }

    /* Hero Banner: Purple & Turquoise Gradient */
    .palette-hero {
        background: linear-gradient(135deg, #2e1065 0%, #581c87 40%, #0f766e 100%);
        padding: 30px 24px;
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
        font-size: 16px;
        color: #2dd4bf !important;
        margin-top: 8px;
        font-weight: 600;
    }

    /* Metric Cards */
    .metric-card-palette {
        background: #1a1532;
        padding: 22px;
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
        font-size: 44px;
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
        padding: 30px;
        border-radius: 18px;
        border: 1px solid #38bdf8;
        line-height: 2.2;
        font-size: 16px;
        color: #f8fafc !important;
    }

    /* Sidebar Credit Card */
    .sidebar-credit-card {
        background: linear-gradient(135deg, #3b0764 0%, #0f766e 100%);
        border: 1px solid #f59e0b;
        padding: 14px;
        border-radius: 14px;
        color: #ffffff !important;
        font-size: 14px;
        font-weight: 700;
        text-align: center;
        margin-top: 10px;
        margin-bottom: 20px;
        box-shadow: 0 6px 15px rgba(245, 158, 11, 0.25);
    }
    </style>
""", unsafe_allow_html=True)

# --- Mobile Banner Tip ---
st.markdown("""
    <div style="background: #1e1b4b; border: 1px solid #38bdf8; padding: 10px 16px; border-radius: 12px; text-align: center; font-weight: 700; color: #38bdf8; margin-bottom: 16px; font-size: 14px;">
        📱 Mobile Tip: Tap the <b>&gt;</b> icon at the top-left corner to open menu controls
    </div>
""", unsafe_allow_html=True)

# --- Sidebar Controls ---
st.sidebar.markdown("""
    <div style="font-size: 22px; font-weight: 800; color: #38bdf8;">✨ WriteSafe Studio</div>
    <div class="sidebar-credit-card">
        👑 Crafted by: Dr. Joydip Chandra, BRSC
    </div>
""", unsafe_allow_html=True)

# Admin Passcode Lock in Sidebar
st.sidebar.markdown("---")
with st.sidebar.expander("🔐 Secret Admin Access", expanded=False):
    admin_pass_input = st.text_input("Enter Admin Passcode:", type="password", key="admin_pass_field")
    if st.button("Unlock Admin Panel", key="unlock_admin_btn"):
        if admin_pass_input == ADMIN_PASSCODE:
            st.session_state["admin_unlocked"] = True
            st.success("Admin Panel Unlocked!")
        else:
            st.error("Invalid Admin Passcode")

if st.session_state.get("admin_unlocked"):
    st.sidebar.success("👑 Admin Mode Active")
    if st.sidebar.button("Lock Admin Panel"):
        st.session_state["admin_unlocked"] = False
        st.rerun()

st.sidebar.info("Upload research papers or essays to evaluate AI generation metrics and web similarity.")
st.sidebar.caption("⚡ Fast • 🔒 Private • 🎓 Academic Ready")

# --- Hero Banner ---
st.markdown("""
    <div class="palette-hero">
        <div class="golden-badge">✨ NO-CAP AI & PLAGIARISM CHECKER</div>
        <div class="palette-title">🛡️ WriteSafe</div>
        <div class="palette-tagline">“Catch plagiarism and AI-sounding text before you submit.”</div>
    </div>
""", unsafe_allow_html=True)

# Load current user records
users_db = load_users()

# --- ADMIN PANEL DISPLAY (If Unlocked via Passcode) ---
if st.session_state.get("admin_unlocked"):
    st.markdown("""
        <div style="background: #1e1538; border: 2px solid #f59e0b; padding: 22px; border-radius: 18px; margin-bottom: 24px;">
            <h3 style="color: #fbbf24 !important; margin-top: 0;">👑 SECRET ADMIN USER DIRECTORY & ACCESS LOGS</h3>
            <p style="color: #cbd5e1 !important;">View and manage registered user accounts across the institution.</p>
        </div>
    """, unsafe_allow_html=True)
    
    if users_db:
        user_list = []
        for email, udata in users_db.items():
            user_list.append({
                "Full Name": udata.get("name", "N/A"),
                "Email Address": email,
                "Registered Date": udata.get("registered_at", "N/A"),
                "Total Scans": udata.get("scans", 0),
                "Last Active": udata.get("last_login", "N/A")
            })
        
        st.dataframe(user_list, use_container_width=True)
        
        csv_data = "Full Name,Email Address,Registered Date,Total Scans,Last Active\n"
        for row in user_list:
            csv_data += f'"{row["Full Name"]}","{row["Email Address"]}","{row["Registered Date"]}",{row["Total Scans"]},"{row["Last Active"]}"\n'
            
        st.download_button(
            label="📥 Download Registered Users Directory (CSV)",
            data=csv_data,
            file_name=f"WriteSafe_Registered_Users_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    else:
        st.info("No registered users found in the database yet.")
    st.markdown("<hr style='border-color: #38bdf8;'>", unsafe_allow_html=True)

# --- USER AUTHENTICATION & GATE ---
if not st.session_state.get("logged_in_user"):
    st.subheader("🔐 User Login & Registration Gate")
    st.write("Please sign in or register to access the WriteSafe audit workspace.")

    auth_tab1, auth_tab2, auth_tab3 = st.tabs([
        "🔑 Sign In", 
        "📝 First-Time Registration", 
        "🔓 Forgot Password"
    ])

    with auth_tab1:
        st.markdown("#### Sign In to Your Account")
        login_email = st.text_input("Registered Email Address:", key="login_email_input").strip().lower()
        login_password = st.text_input("Password:", type="password", key="login_pass_input")

        if st.button("🚀 Sign In", type="primary", use_container_width=True):
            if not login_email or not login_password:
                st.warning("Please enter both email and password.")
            elif login_email not in users_db:
                st.error("No account found with this email. Please register first.")
            else:
                user_record = users_db[login_email]
                if user_record.get("password") == hash_str(login_password):
                    user_record["last_login"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    save_users(users_db)
                    st.session_state["logged_in_user"] = login_email
                    st.session_state["user_name"] = user_record.get("name", "User")
                    st.success(f"Welcome back, {user_record.get('name')}!")
                    st.rerun()
                else:
                    st.error("Incorrect password. Please try again or use Forgot Password.")

    with auth_tab2:
        st.markdown("#### First-Time Registration")
        reg_name = st.text_input("Full Name:", key="reg_name_input")
        reg_email = st.text_input("Email Address:", key="reg_email_input").strip().lower()
        reg_pass = st.text_input("Create Password:", type="password", key="reg_pass_input")
        reg_pass_confirm = st.text_input("Confirm Password:", type="password", key="reg_pass_confirm_input")
        
        reg_sq = st.selectbox("Select a Security Question:", SECURITY_QUESTIONS, key="reg_sq_input")
        reg_sa = st.text_input("Security Answer (for password resets):", type="password", key="reg_sa_input")

        if st.button("✨ Register Account", type="primary", use_container_width=True):
            if not reg_name or not reg_email or not reg_pass or not reg_sa:
                st.warning("Please fill in all registration fields.")
            elif "@" not in reg_email or "." not in reg_email:
                st.error("Please enter a valid email address.")
            elif reg_pass != reg_pass_confirm:
                st.error("Passwords do not match!")
            elif reg_email in users_db:
                st.error("An account with this email already exists. Please Sign In.")
            else:
                users_db[reg_email] = {
                    "name": reg_name.strip(),
                    "password": hash_str(reg_pass),
                    "security_question": reg_sq,
                    "security_answer": hash_str(reg_sa),
                    "registered_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "last_login": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "scans": 0
                }
                save_users(users_db)
                st.success("🎉 Registration successful! You can now Sign In using your credentials.")

    with auth_tab3:
        st.markdown("#### Reset Your Password")
        st.caption("Verify your registered email address first to view your security question.")
        
        forgot_email = st.text_input("Registered Email Address:", key="forgot_email_input").strip().lower()
        
        if st.button("🔍 Submit Email & Find Account", key="find_account_btn"):
            if not forgot_email:
                st.warning("Please enter your registered email address.")
            elif forgot_email not in users_db:
                st.error("No account found with this email address.")
                st.session_state["forgot_verified_email"] = None
            else:
                st.session_state["forgot_verified_email"] = forgot_email
                st.success("Account found! Please answer your security question below.")

        if st.session_state.get("forgot_verified_email"):
            active_email = st.session_state["forgot_verified_email"]
            user_data = users_db.get(active_email, {})
            
            st.info(f"Verified Account: **{active_email}**")
            st.markdown(f"**Security Question:** *{user_data.get('security_question', SECURITY_QUESTIONS[0])}*")
            
            forgot_sa = st.text_input("Your Security Answer:", type="password", key="forgot_sa_input")
            new_pass = st.text_input("New Password:", type="password", key="new_pass_input")
            new_pass_confirm = st.text_input("Confirm New Password:", type="password", key="new_pass_confirm_input")
            
            if st.button("Regenerate & Reset Password", type="primary", use_container_width=True):
                if not forgot_sa or not new_pass:
                    st.warning("Please fill in your security answer and new password.")
                elif hash_str(forgot_sa) != user_data.get("security_answer"):
                    st.error("Incorrect security answer!")
                elif new_pass != new_pass_confirm:
                    st.error("New passwords do not match!")
                else:
                    user_data["password"] = hash_str(new_pass)
                    save_users(users_db)
                    st.session_state["forgot_verified_email"] = None
                    st.success("🎉 Password reset successfully! Please sign in with your new password.")

# --- MAIN WORKSPACE (IF LOGGED IN) ---
else:
    current_email = st.session_state["logged_in_user"]
    current_name = st.session_state.get("user_name", "User")

    col_u1, col_u2 = st.columns([3, 1])
    with col_u1:
        st.markdown(f"<div style='font-size: 18px; font-weight: 700; color: #2dd4bf;'>👤 Active User: {current_name} ({current_email})</div>", unsafe_allow_html=True)
    with col_u2:
        if st.button("🚪 Sign Out"):
            st.session_state["logged_in_user"] = None
            st.session_state["user_name"] = None
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # --- Document Upload / Input ---
    uploaded_file = st.file_uploader("📁 Upload Draft Document (.pdf, .docx, .txt)", type=["pdf", "docx", "txt"])
    pasted_text = st.text_area("📝 Or paste your draft text directly below:", height=170, placeholder="Paste your essay or research paper text here...")

    document_text = extract_text(uploaded_file) if uploaded_file else pasted_text

    if st.button("🚀 Run WriteSafe Audit", type="primary", use_container_width=True):
        if not document_text.strip():
            st.warning("Please upload a file or paste text first.")
        else:
            # Update user scan count
            if current_email in users_db:
                users_db[current_email]["scans"] = users_db[current_email].get("scans", 0) + 1
                users_db[current_email]["last_login"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                save_users(users_db)

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
                            st.write(f"**Matched Text Fragment:** \"{match['phrase']}\"")
                            st.write(f"**Direct URL:** [{match['url']}]({match['url']})")
                            if match.get('snippet'):
                                st.caption(f"**Web Snippet:** {match['snippet']}")
                else:
                    st.success("🎉 No matching public domain sources detected for the sampled phrases.")

            with tab3:
                st.subheader("Sentence-by-Sentence AI Evaluation")
                for idx, item in enumerate(sentence_analysis, 1):
                    status_icon = "🔴 AI Flagged" if item["is_ai"] else "🟢 Human Flow"
                    with st.expander(f"Sentence #{idx} ({item['word_count']} words) — {status_icon}"):
                        st.write(f"\"{item['sentence']}\"")
                        st.caption(f"**Evaluation Detail:** {item['reason']}")

            with tab4:
                st.subheader("Download Verified Summary Report")
                st.write("Generate and download a formal audit report suitable for submission or records:")
                try:
                    pdf_bytes = create_pdf_report(ai_score, plag_score, web_matches, doc_stats, user_email=current_email)
                    st.download_button(
                        label="📥 Download WriteSafe PDF Summary Report",
                        data=pdf_bytes,
                        file_name=f"WriteSafe_Analysis_Report_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                        mime="application/pdf",
                        type="primary"
                    )
                except Exception as e:
                    st.error(f"Could not generate PDF: {e}")
