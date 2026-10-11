import streamlit as st
import re
import math
import json
import os
from datetime import datetime
from duckduckgo_search import DDGS
from pypdf import PdfReader
from docx import Document
from fpdf import FPDF

# --- User Database Helper (Local JSON) ---
DB_FILE = "registered_users.json"

def load_users():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_user(email, name):
    users = load_users()
    email_clean = email.strip().lower()
    if email_clean not in users:
        users[email_clean] = {
            "name": name,
            "email": email_clean,
            "registered_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "scans_count": 0,
            "last_active": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    else:
        users[email_clean]["last_active"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    with open(DB_FILE, "w") as f:
        json.dump(users, f, indent=2)
    return users[email_clean]

def increment_user_scan(email):
    users = load_users()
    email_clean = email.strip().lower()
    if email_clean in users:
        users[email_clean]["scans_count"] = users[email_clean].get("scans_count", 0) + 1
        users[email_clean]["last_active"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(DB_FILE, "w") as f:
            json.dump(users, f, indent=2)

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
        replacement = f'<mark style="background: rgba(239, 68, 68, 0.3); color: #fca5a5; padding: 3px 8px; border-radius: 6px; border: 1px solid #ef4444; font-weight: 600;"><b>[Web Match]</b> {phrase} <a href="{url}" target="_blank" style="color: #38bdf8; text-decoration: underline; font-weight: 700;">(Source)</a></mark>'
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
    
    if user_email:
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(14, 116, 144)
        pdf.cell(0, 5, clean_pdf_str(f"Verified Audit User: {user_email}"), new_x="LMARGIN", new_y="NEXT", align="C")

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
            pdf.multi_cell(0, 6, clean_pdf_str(f"Match #{idx}: {title}"), new_x="LMARGIN", new_y="NEXT")
            
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(71, 85, 105)
            phrase = wrap_long_words(clean_pdf_str(match.get('phrase', '')))
            url = wrap_long_words(clean_pdf_str(match.get('url', '')), max_len=30)
            
            pdf.multi_cell(0, 5, clean_pdf_str(f"Matched Phrase: '{phrase}'"), new_x="LMARGIN", new_y="NEXT")
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

# --- Page Config & Custom Palette CSS (Sky Blue, Purple, Golden, Turquoise) ---
st.set_page_config(page_title="WriteSafe", layout="wide", page_icon="✨")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    
    .stApp {
        background-color: #0b0817;
        color: #f8fafc;
    }

    label, .stMarkdown, p, span, div, h1, h2, h3, h4, h5, h6, .stCaption {
        color: #f1f5f9 !important;
    }

    [data-testid="stSidebar"] {
        background-color: #130e2a !important;
        border-right: 1px solid #38bdf8 !important;
    }

    [data-testid="stFileUploader"] {
        background: #181330;
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

    .stTextArea textarea, .stTextInput input {
        background-color: #181330 !important;
        color: #f8fafc !important;
        border: 1px solid #38bdf8 !important;
        border-radius: 12px !important;
        font-size: 15px !important;
    }
    .stTextArea label, .stTextInput label {
        color: #38bdf8 !important;
        font-weight: 700 !important;
        font-size: 15px !important;
    }

    .stButton button {
        background: linear-gradient(135deg, #0ea5e9 0%, #0284c7 50%, #14b8a6 100%) !important;
        color: #ffffff !important;
        font-weight: 800 !important;
        font-size: 17px !important;
        border-radius: 12px !important;
        border: none !important;
        box-shadow: 0 10px 25px rgba(14, 165, 233, 0.3) !important;
        padding: 12px 24px !important;
    }

    .sidebar-desc-box {
        background: #1a1538;
        border: 1px solid #38bdf8;
        border-radius: 12px;
        padding: 14px;
        color: #f8fafc !important;
        font-size: 13px;
        line-height: 1.6;
        margin-top: 10px;
        margin-bottom: 12px;
    }

    .sidebar-credit-card {
        background: linear-gradient(135deg, #2e1065 0%, #0f766e 100%);
        border: 1px solid #fbbf24;
        padding: 12px;
        border-radius: 12px;
        color: #ffffff !important;
        font-size: 13px;
        font-weight: 700;
        text-align: center;
        margin-bottom: 20px;
        box-shadow: 0 6px 15px rgba(245, 158, 11, 0.2);
    }

    .palette-hero {
        background: linear-gradient(135deg, #0284c7 0%, #1e1b4b 60%, #0f766e 100%);
        padding: 32px 28px;
        border-radius: 20px;
        border: 2px solid #38bdf8;
        box-shadow: 0 15px 35px rgba(14, 165, 233, 0.25);
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
    }
    
    .palette-title {
        font-size: 38px;
        font-weight: 800;
        margin: 0;
        color: #ffffff !important;
    }
    
    .palette-tagline {
        font-size: 16px;
        color: #38bdf8 !important;
        margin-top: 8px;
        font-weight: 600;
    }

    .metric-card-palette {
        background: #181330;
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

    .palette-stats-bar {
        background: #181330;
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

    .palette-marked-canvas {
        background: #100b22;
        padding: 30px;
        border-radius: 18px;
        border: 1px solid #38bdf8;
        line-height: 2.2;
        font-size: 16px;
        color: #f8fafc !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- Sidebar Header, Description, & Credit Note ---
st.sidebar.markdown("""
    <div style="font-size: 22px; font-weight: 800; color: #38bdf8; margin-bottom: 6px;">✨ WriteSafe Studio</div>
    <div class="sidebar-desc-box">
        WriteSafe evaluates research drafts, essays, and documents for AI generation patterns and searches public domain web databases in real-time.
    </div>
    <div class="sidebar-credit-card">
        👑 Crafted by: Dr. Joydip Chandra, BRSC
    </div>
""", unsafe_allow_html=True)

# --- Registration / Login Gate ---
if "user_email" not in st.session_state:
    st.session_state.user_email = ""

if not st.session_state.user_email:
    st.markdown("""
        <div class="palette-hero">
            <div class="golden-badge">🔐 REGISTRATION GATE</div>
            <div class="palette-title">🛡️ Welcome to WriteSafe</div>
            <div class="palette-tagline">Please enter your details to access the AI & Plagiarism Audit Workspace.</div>
        </div>
    """, unsafe_allow_html=True)

    col_a, col_b = st.columns([1, 1])
    with col_a:
        user_name_input = st.text_input("Your Full Name", placeholder="e.g. Dr. Joydip Chandra")
        user_email_input = st.text_input("Your Email Address", placeholder="e.g. joydip@brsc.ac.in")
        
        if st.button("Unlock WriteSafe Workspace 🚀", use_container_width=True):
            if not user_email_input.strip() or "@" not in user_email_input:
                st.error("Please enter a valid email address.")
            elif not user_name_input.strip():
                st.error("Please enter your full name.")
            else:
                user_info = save_user(user_email_input, user_name_input)
                st.session_state.user_email = user_info["email"]
                st.session_state.user_name = user_info["name"]
                st.rerun()
else:
    # Sidebar logout / user indicator
    st.sidebar.caption(f"Logged in as: **{st.session_state.user_email}**")
    if st.sidebar.button("Switch / Change Account"):
        st.session_state.user_email = ""
        st.rerun()

    # --- Main Hero Banner ---
    st.markdown("""
        <div class="palette-hero">
            <div class="golden-badge">✨ REAL-TIME AI & PLAGIARISM AUDITOR</div>
            <div class="palette-title">🛡️ WriteSafe</div>
            <div class="palette-tagline">“Catch plagiarism and AI-sounding text before you submit.”</div>
        </div>
    """, unsafe_allow_html=True)

    # --- Document Upload / Input ---
    uploaded_file = st.file_uploader("📁 Upload Draft Document (.pdf, .docx, .txt)", type=["pdf", "docx", "txt"])
    pasted_text = st.text_area("📝 Or paste your draft text directly below:", height=170, placeholder="Paste your essay or research paper text here...")

    document_text = extract_text(uploaded_file) if uploaded_file else pasted_text

    if st.button("🚀 Run WriteSafe Audit", type="primary", use_container_width=True):
        if not document_text.strip():
            st.warning("Please upload a file or paste text first.")
        else:
            increment_user_scan(st.session_state.user_email)
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

            # Store results in session state for tabs
            st.session_state.audit_results = {
                "ai_score": ai_score,
                "ai_sents": ai_sents,
                "sentence_analysis": sentence_analysis,
                "plag_score": plag_score,
                "web_matches": web_matches,
                "web_phrases": web_phrases,
                "doc_stats": doc_stats,
                "document_text": document_text
            }

    if "audit_results" in st.session_state:
        res = st.session_state.audit_results

        # --- Score Dashboard ---
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(f"""
                <div class="metric-card-palette">
                    <div class="metric-title-palette">🤖 Estimated AI Probability</div>
                    <div class="metric-value-palette" style="color: {'#ef4444' if res['ai_score'] > 60 else '#f59e0b' if res['ai_score'] > 35 else '#2dd4bf'};">{res['ai_score']}%</div>
                </div>
            """, unsafe_allow_html=True)
            if res['ai_score'] > 60:
                st.error("⚠️ High likelihood of machine-generated text.")
            elif res['ai_score'] > 35:
                st.warning("⚡ Moderate AI influence or mixed editing.")
            else:
                st.success("✅ Content displays natural human writing variation.")

        with col2:
            st.markdown(f"""
                <div class="metric-card-palette">
                    <div class="metric-title-palette">🌐 Estimated Plagiarism / Web Score</div>
                    <div class="metric-value-palette" style="color: {'#ef4444' if res['plag_score'] > 50 else '#f59e0b' if res['plag_score'] > 20 else '#2dd4bf'};">{res['plag_score']}%</div>
                </div>
            """, unsafe_allow_html=True)
            if res['plag_score'] > 50:
                st.error(f"⚠️ High similarity across {len(res['web_matches'])} web sources.")
            elif res['plag_score'] > 20:
                st.warning(f"⚡ Moderate similarity across {len(res['web_matches'])} web sources.")
            else:
                st.success("✅ Low or no public web overlap detected.")

        st.markdown("<br>", unsafe_allow_html=True)

        # --- Document Stats Bar ---
        st.markdown(f"""
            <div class="palette-stats-bar">
                <div style="text-align: center;"><div class="palette-stat-num">{res['doc_stats']['word_count']}</div><div class="palette-stat-lbl">Words</div></div>
                <div style="text-align: center;"><div class="palette-stat-num">{res['doc_stats']['sentence_count']}</div><div class="palette-stat-lbl">Sentences</div></div>
                <div style="text-align: center;"><div class="palette-stat-num" style="color: #f59e0b !important;">{res['doc_stats']['ai_flagged_count']}</div><div class="palette-stat-lbl">AI Sentences</div></div>
                <div style="text-align: center;"><div class="palette-stat-num" style="color: #ef4444 !important;">{res['doc_stats']['web_matches_count']}</div><div class="palette-stat-lbl">Web Matches</div></div>
            </div>
        """, unsafe_allow_html=True)

        # --- Check if Admin ---
        is_admin = st.session_state.get("user_email", "").strip().lower() == "joydip@brsc.ac.in"

        tab_list = ["🖍️ Marked Document Reader", "🌐 Web Source Overlaps", "📊 Sentence Analysis", "📄 Export PDF Report"]
        if is_admin:
            tab_list.append("👑 Admin User Directory")

        tabs = st.tabs(tab_list)

        with tabs[0]:
            st.caption("🟨 **Golden Highlight** = AI-flagged sentence pattern | 🟥 **Red Highlight** = Web source match (with source link)")
            highlighted_html = render_highlighted_document(res['document_text'], res['ai_sents'], res['web_phrases'])
            st.markdown(f'<div class="palette-marked-canvas">{highlighted_html}</div>', unsafe_allow_html=True)

        with tabs[1]:
            if res['web_matches']:
                st.subheader(f"Found {len(res['web_matches'])} Matching Web Sources")
                for idx, match in enumerate(res['web_matches'], 1):
                    with st.expander(f"Match #{idx}: {match['title']}"):
                        st.write(f"**Matched Text Fragment:** \"{match['phrase']}\"")
                        st.write(f"**Direct URL:** [{match['url']}]({match['url']})")
                        if match.get('snippet'):
                            st.caption(f"**Web Snippet:** {match['snippet']}")
            else:
                st.success("🎉 No matching public domain sources detected for the sampled phrases.")

        with tabs[2]:
            st.subheader("Sentence-by-Sentence AI Evaluation")
            for idx, item in enumerate(res['sentence_analysis'], 1):
                status_icon = "🔴 AI Flagged" if item["is_ai"] else "🟢 Human Flow"
                with st.expander(f"Sentence #{idx} ({item['word_count']} words) — {status_icon}"):
                    st.write(f"\"{item['sentence']}\"")
                    st.caption(f"**Evaluation Detail:** {item['reason']}")

        with tabs[3]:
            st.subheader("Download Verified Summary Report")
            st.write("Generate and download a formal audit report suitable for submission or records:")
            try:
                pdf_bytes = create_pdf_report(res['ai_score'], res['plag_score'], res['web_matches'], res['doc_stats'], st.session_state.user_email)
                st.download_button(
                    label="📥 Download WriteSafe PDF Summary Report",
                    data=pdf_bytes,
                    file_name="WriteSafe_Plagiarism_AI_Analysis_Report.pdf",
                    mime="application/pdf",
                    type="primary"
                )
            except Exception as e:
                st.error(f"Could not generate PDF: {e}")

        if is_admin:
            with tabs[4]:
                st.subheader("👑 Admin User Directory & Activity Log")
                st.write("Restricted View: Accessible only to `joydip@brsc.ac.in`")
                users_data = load_users()
                if users_data:
                    user_list = list(users_data.values())
                    st.dataframe(user_list, use_container_width=True)
                    
                    csv_data = "Name,Email,Registered At,Scans Count,Last Active\n"
                    for u in user_list:
                        csv_data += f'"{u.get("name")}","{u.get("email")}","{u.get("registered_at")}","{u.get("scans_count",0)}","{u.get("last_active")}"\n'
                    
                    st.download_button(
                        label="📥 Download Registered Users CSV",
                        data=csv_data,
                        file_name="registered_users.csv",
                        mime="text/csv"
                    )
                else:
                    st.info("No registered users recorded yet.")
