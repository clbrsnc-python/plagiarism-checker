import streamlit as st
import re
import math
import os
import json
from datetime import datetime
from duckduckgo_search import DDGS
from pypdf import PdfReader
from docx import Document
from fpdf import FPDF

# --- User Management & Database Helper ---
USER_DB_FILE = "registered_users.json"

def load_registered_users():
    if os.path.exists(USER_DB_FILE):
        try:
            with open(USER_DB_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_user_registration(name, email):
    users = load_registered_users()
    existing = next((u for u in users if u["email"].lower() == email.lower()), None)
    if not existing:
        new_user = {
            "name": name.strip(),
            "email": email.strip().lower(),
            "registered_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "scans_count": 0
        }
        users.append(new_user)
        try:
            with open(USER_DB_FILE, "w") as f:
                json.dump(users, f, indent=4)
        except Exception:
            pass
    return users

def increment_user_scans(email):
    users = load_registered_users()
    for u in users:
        if u["email"].lower() == email.lower():
            u["scans_count"] = u.get("scans_count", 0) + 1
            u["last_active"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            break
    try:
        with open(USER_DB_FILE, "w") as f:
            json.dump(users, f, indent=4)
    except Exception:
        pass

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
    if user_email:
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
            pdf.multi_cell(0, 6, clean_pdf_str(f"Match #{idx}: {title}"), new_x="LMARGIN", new_y="NEXT")
            
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(71, 85, 105)
            phrase = wrap_long_words(clean_pdf_str(match.get('phrase', '')))
            url = wrap_long_words(clean_pdf_str(match.get('url', '')), max_len=30)
            
            pdf.multi_cell(0, 5, clean_pdf_str(f"Matched Phrase: \"{phrase}\""), new_x="LMARGIN", new_y="NEXT")
            pdf.multi_cell(0, 5, clean_pdf_str(f"Source URL: {url}"), new_x="LMARGIN", new_y="NEXT")
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
    
    .stApp {
        background-color: #0f172a;
        color: #f8fafc;
    }

    label, .stMarkdown, p, span, div, h1, h2, h3, h4, h5, h6, .stCaption {
        color: #f1f5f9 !important;
    }

    /* File Uploader Custom Styling */
    [data-testid="stFileUploader"] {
        background: #1e293b;
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
        background: linear-gradient(135deg, #0284c7 0%, #38bdf8 100%) !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 10px !important;
        font-weight: 700 !important;
    }

    /* Text Area Styling */
    .stTextArea textarea {
        background-color: #1e293b !important;
        color: #f8fafc !important;
        border: 1px solid #38bdf8 !important;
        border-radius: 14px !important;
        font-size: 15px !important;
    }
    .stTextArea label {
        color: #38bdf8 !important;
        font-weight: 700 !important;
        font-size: 15px !important;
    }

    /* Primary Buttons */
    .stButton button {
        background: linear-gradient(135deg, #0284c7 0%, #0369a1 50%, #0f766e 100%) !important;
        color: #ffffff !important;
        font-weight: 800 !important;
        font-size: 18px !important;
        border-radius: 14px !important;
        border: none !important;
        box-shadow: 0 10px 25px rgba(2, 132, 199, 0.3) !important;
        padding: 12px 24px !important;
    }

    /* Hero Banner */
    .palette-hero {
        background: linear-gradient(135deg, #0284c7 0%, #0369a1 40%, #0f766e 100%);
        padding: 34px 28px;
        border-radius: 22px;
        border: 2px solid #38bdf8;
        box-shadow: 0 15px 35px rgba(2, 132, 199, 0.25);
        margin-bottom: 28px;
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
        font-size: 38px;
        font-weight: 800;
        margin: 0;
        color: #ffffff !important;
        letter-spacing: -0.5px;
    }
    
    .palette-tagline {
        font-size: 16px;
        color: #e0f2fe !important;
        margin-top: 8px;
        font-weight: 600;
    }

    /* Metric Cards */
    .metric-card-palette {
        background: #1e293b;
        padding: 22px;
        border-radius: 18px;
        border: 1px solid #38bdf8;
        box-shadow: 0 10px 25px rgba(0, 0, 0, 0.3);
        text-align: center;
    }
    .metric-title-palette {
        font-size: 13px;
        color: #38bdf8 !important;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .metric-value-palette {
        font-size: 44px;
        font-weight: 800;
        margin: 8px 0;
    }

    /* Stats Bar */
    .palette-stats-bar {
        background: #1e293b;
        border-radius: 16px;
        border: 1px solid #38bdf8;
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
        background: #0f172a;
        padding: 30px;
        border-radius: 18px;
        border: 1px solid #38bdf8;
        line-height: 2.2;
        font-size: 16px;
        color: #f8fafc !important;
    }

    /* Sidebar Registration & Credit Card */
    .sidebar-credit-card {
        background: linear-gradient(135deg, #0369a1 0%, #0f766e 100%);
        border: 1px solid #f59e0b;
        padding: 14px;
        border-radius: 14px;
        color: #ffffff !important;
        font-size: 14px;
        font-weight: 700;
        text-align: center;
        margin-top: 12px;
        margin-bottom: 18px;
        box-shadow: 0 6px 15px rgba(245, 158, 11, 0.25);
    }

    .registration-box {
        background: #1e293b;
        border: 1px solid #38bdf8;
        padding: 24px;
        border-radius: 18px;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.4);
        margin-bottom: 25px;
    }
    </style>
""", unsafe_allow_html=True)

# --- Sidebar Header & Reordered Description / Credit Note ---
st.sidebar.markdown("""
    <div style="font-size: 24px; font-weight: 800; color: #38bdf8;">✨ WriteSafe Studio</div>
""", unsafe_allow_html=True)

st.sidebar.markdown("""
    <div style="font-size: 14px; color: #cbd5e1; margin-top: 10px; margin-bottom: 10px; line-height: 1.5;">
        WriteSafe evaluates research drafts, essays, and documents for AI generation patterns and searches public domain web databases in real-time.
    </div>
    <div class="sidebar-credit-card">
        👑 Crafted by: Dr. Joydip Chandra, BRSC
    </div>
""", unsafe_allow_html=True)

st.sidebar.caption("⚡ Fast • 🔒 Private • 🎓 Academic Ready")

# --- Authentication / Registration Logic (No Domain Restriction) ---
if "user_email" not in st.session_state:
    st.session_state["user_email"] = ""
if "user_name" not in st.session_state:
    st.session_state["user_name"] = ""

# Sidebar Account Status / Logout
if st.session_state["user_email"]:
    st.sidebar.markdown("---")
    st.sidebar.markdown(f"👤 **Account:** `{st.session_state['user_email']}`")
    if st.sidebar.button("🔒 Sign Out"):
        st.session_state["user_email"] = ""
        st.session_state["user_name"] = ""
        st.rerun()

# --- Main App Layout ---
st.markdown("""
    <div class="palette-hero">
        <div class="golden-badge">✨ REAL-TIME AI & PLAGIARISM AUDITOR</div>
        <div class="palette-title">🛡️ WriteSafe</div>
        <div class="palette-tagline">“Catch plagiarism and AI-sounding text before you submit.”</div>
    </div>
""", unsafe_allow_html=True)

# Check if User is Registered / Signed In
if not st.session_state["user_email"]:
    st.markdown("""
        <div class="registration-box">
            <h3 style="color: #38bdf8 !important; margin-top: 0;">🔑 Student & Faculty Access Gate</h3>
            <p style="color: #cbd5e1 !important;">Please register your email address below to unlock the WriteSafe scanning tool. Any valid email address is accepted!</p>
        </div>
    """, unsafe_allow_html=True)

    col_reg1, col_reg2 = st.columns(2)
    with col_reg1:
        reg_name = st.text_input("Full Name", placeholder="e.g. Rahul Sharma")
    with col_reg2:
        reg_email = st.text_input("Email Address (Any domain accepted)", placeholder="e.g. student@gmail.com or professor@brsc.ac.in")

    if st.button("🚀 Register & Access WriteSafe", type="primary"):
        if not reg_email.strip() or "@" not in reg_email or "." not in reg_email:
            st.error("Please enter a valid email address.")
        else:
            save_user_registration(reg_name or "User", reg_email)
            st.session_state["user_email"] = reg_email.strip().lower()
            st.session_state["user_name"] = reg_name.strip() or "User"
            st.success("✅ Access granted! Welcome to WriteSafe.")
            st.rerun()

else:
    # --- Authenticated User Workspace ---
    st.markdown(f"👋 **Welcome back, {st.session_state['user_name'] or st.session_state['user_email']}!** Ready to scan your document.")

    uploaded_file = st.file_uploader("📁 Upload Draft Document (.pdf, .docx, .txt)", type=["pdf", "docx", "txt"])
    pasted_text = st.text_area("📝 Or paste your draft text directly below:", height=170, placeholder="Paste your essay or research paper text here...")

    document_text = extract_text(uploaded_file) if uploaded_file else pasted_text

    if st.button("🚀 Run WriteSafe Audit", type="primary", use_container_width=True):
        if not document_text.strip():
            st.warning("Please upload a file or paste text first.")
        else:
            increment_user_scans(st.session_state["user_email"])
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
            tab1, tab2, tab3, tab4, tab5 = st.tabs([
                "🖍️ Marked Document Reader", 
                "🌐 Web Source Overlaps", 
                "📊 Sentence Analysis",
                "📄 Export PDF Report",
                "👑 Admin User Directory"
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
                    pdf_bytes = create_pdf_report(ai_score, plag_score, web_matches, doc_stats, st.session_state["user_email"])
                    st.download_button(
                        label="📥 Download WriteSafe PDF Summary Report",
                        data=pdf_bytes,
                        file_name="WriteSafe_Plagiarism_AI_Analysis_Report.pdf",
                        mime="application/pdf",
                        type="primary"
                    )
                except Exception as e:
                    st.error(f"Could not generate PDF: {e}")

            with tab5:
                st.subheader("👑 Registered Users Directory")
                registered_list = load_registered_users()
                st.write(f"Total Registered Users: **{len(registered_list)}**")
                if registered_list:
                    st.dataframe(registered_list, use_container_width=True)
                    json_str = json.dumps(registered_list, indent=4)
                    st.download_button(
                        label="📥 Export Registered Users List (JSON)",
                        data=json_str,
                        file_name="registered_users_export.json",
                        mime="application/json"
                    )
                else:
                    st.info("No registered users logged yet.")
