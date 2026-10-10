import streamlit as st
import re
import math
from duckduckgo_search import DDGS
from pypdf import PdfReader
from docx import Document
from fpdf import FPDF

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
            "reason": "AI Signature Keyword" if has_ai_word else ("Uniform Sentence Structure" if is_ai else "Natural Human Style")
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

# --- HTML Inline Document Renderer ---
def render_highlighted_document(full_text, ai_sentences, web_flagged_phrases):
    highlighted_text = full_text

    for phrase, url in web_flagged_phrases:
        escaped_phrase = re.escape(phrase)
        replacement = f'<mark style="background: rgba(244, 63, 94, 0.22); color: #fca5a5; padding: 3px 8px; border-radius: 6px; border: 1px solid rgba(244, 63, 94, 0.5); font-weight: 600;"><b>[Web Match]</b> {phrase} <a href="{url}" target="_blank" style="color: #38bdf8; text-decoration: underline; font-weight: 700;">(Source Link)</a></mark>'
        highlighted_text = re.sub(escaped_phrase, replacement, highlighted_text)

    for sent in ai_sentences:
        escaped_sent = re.escape(sent)
        replacement = f'<mark style="background: rgba(245, 158, 11, 0.22); color: #fef08a; padding: 3px 8px; border-radius: 6px; border: 1px solid rgba(245, 158, 11, 0.5); font-weight: 600;"><b>[AI Flagged]</b> {sent}</mark>'
        highlighted_text = re.sub(escaped_sent, replacement, highlighted_text)

    return highlighted_text

# --- PDF Helpers (Safe Margin Formatting) ---
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

def create_pdf_report(ai_prob, plag_prob, web_matches, doc_stats):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_margins(15, 15, 15)

    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 10, clean_pdf_str("WriteSafe Analysis Report"), new_x="LMARGIN", new_y="NEXT", align="C")
    
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

# --- Page Config & Styling ---
st.set_page_config(page_title="WriteSafe", layout="wide", page_icon="🛡️")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    
    .stApp {
        background-color: #0d111d;
        color: #f1f5f9;
    }
    
    /* High Legibility Labels & Uploader */
    label, p, span, div {
        color: #f1f5f9 !important;
    }
    
    .stTextArea textarea {
        background-color: #1e1b4b !important;
        color: #ffffff !important;
        border: 1px solid #8b5cf6 !important;
        border-radius: 12px !important;
        font-size: 15px !important;
    }
    
    [data-testid="stFileUploadDropzone"] {
        background-color: #1e1b4b !important;
        border: 2px dashed #38bdf8 !important;
        border-radius: 14px !important;
    }
    
    [data-testid="stFileUploadDropzone"] button {
        background: linear-gradient(135deg, #0ea5e9 0%, #2563eb 100%) !important;
        color: #ffffff !important;
        border: none !important;
        font-weight: 700 !important;
        border-radius: 8px !important;
    }

    /* Primary Action Button */
    div.stButton > button {
        background: linear-gradient(135deg, #0ea5e9 0%, #7c3aed 100%) !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        font-size: 16px !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 12px 24px !important;
        box-shadow: 0 4px 15px rgba(14, 165, 233, 0.3) !important;
    }

    /* Hero Banner */
    .app-hero {
        background: linear-gradient(135deg, #1e1b4b 0%, #2e1065 50%, #0f766e 100%);
        padding: 32px 28px;
        border-radius: 20px;
        border: 1px solid #8b5cf6;
        box-shadow: 0 15px 30px rgba(139, 92, 246, 0.25);
        margin-bottom: 28px;
    }
    
    .hero-badge-tag {
        background-color: #f59e0b;
        color: #0f172a !important;
        font-size: 12px;
        font-weight: 800;
        padding: 4px 14px;
        border-radius: 20px;
        display: inline-block;
        margin-bottom: 10px;
        letter-spacing: 0.8px;
        text-transform: uppercase;
    }
    
    .hero-title-text {
        font-size: 38px;
        font-weight: 800;
        letter-spacing: -0.5px;
        margin: 0;
        color: #ffffff !important;
    }
    
    .hero-tagline-text {
        font-size: 16px;
        color: #2dd4bf !important;
        margin-top: 6px;
        font-weight: 600;
    }

    /* Sidebar Author Card */
    .sidebar-author-card {
        background: linear-gradient(135deg, #1e1b4b 0%, #0f766e 100%);
        border: 1px solid #2dd4bf;
        padding: 12px 16px;
        border-radius: 12px;
        color: #ffffff !important;
        font-weight: 700;
        font-size: 14px;
        margin-top: 10px;
        margin-bottom: 20px;
        text-align: center;
        box-shadow: 0 4px 12px rgba(45, 212, 191, 0.2);
    }

    /* Score Cards */
    .card-container {
        background: #1e1b4b;
        padding: 22px;
        border-radius: 16px;
        border: 1px solid #8b5cf6;
        box-shadow: 0 8px 20px rgba(0, 0, 0, 0.4);
        text-align: center;
    }
    .card-title {
        font-size: 13px;
        color: #2dd4bf !important;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.8px;
    }
    .card-val {
        font-size: 42px;
        font-weight: 800;
        margin: 8px 0;
    }

    /* Stats Strip */
    .stats-strip-bar {
        background: #13192b;
        border-radius: 14px;
        border: 1px solid #38bdf8;
        padding: 14px 20px;
        display: flex;
        justify-content: space-around;
        margin-bottom: 24px;
    }
    .stat-val-num {
        font-size: 20px;
        font-weight: 800;
        color: #38bdf8 !important;
    }
    .stat-val-lbl {
        font-size: 12px;
        color: #cbd5e1 !important;
        font-weight: 600;
    }

    /* Marked Reader Canvas */
    .paper-canvas {
        background: #0f172a;
        padding: 30px;
        border-radius: 18px;
        border: 1px solid #38bdf8;
        line-height: 2.1;
        font-size: 16px;
        color: #f8fafc !important;
        box-shadow: inset 0 2px 8px rgba(0, 0, 0, 0.6);
    }
    </style>
""", unsafe_allow_html=True)

# --- Sidebar ---
st.sidebar.title("🛡️ WriteSafe Studio")
st.sidebar.markdown(
    """
    <div class="sidebar-author-card">
        👑 Crafted by: Dr. Joydip Chandra, BRSC
    </div>
    """,
    unsafe_allow_html=True
)
st.sidebar.info(
    "**WriteSafe** evaluates research drafts, essays, and documents for AI generation patterns and searches public domain web databases in real-time."
)
st.sidebar.caption("High Precision • Confidential • Submission Ready")

# --- Hero Header ---
st.markdown("""
    <div class="app-hero">
        <div class="hero-badge-tag">REAL-TIME AI & PLAGIARISM AUDITOR</div>
        <div class="hero-title-text">🛡️ WriteSafe</div>
        <div class="hero-tagline-text">“Catch plagiarism and AI-sounding text before you submit.”</div>
    </div>
""", unsafe_allow_html=True)

# --- Document Upload / Input ---
uploaded_file = st.file_uploader("Upload Document (.pdf, .docx, .txt)", type=["pdf", "docx", "txt"])
pasted_text = st.text_area("Or paste draft text directly", height=170, placeholder="Paste your essay or research paper here...")

document_text = extract_text(uploaded_file) if uploaded_file else pasted_text

if st.button("🚀 Run WriteSafe Analysis", type="primary", use_container_width=True):
    if not document_text.strip():
        st.warning("Please upload a document or paste text first.")
    else:
        st.markdown("<br>", unsafe_allow_html=True)

        with st.spinner("Analyzing writing style patterns & querying web databases..."):
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
                <div class="card-container">
                    <div class="card-title">🤖 AI Generation Probability</div>
                    <div class="card-val" style="color: {'#f43f5e' if ai_score > 60 else '#f59e0b' if ai_score > 35 else '#2dd4bf'};">{ai_score}%</div>
                </div>
            """, unsafe_allow_html=True)
            if ai_score > 60:
                st.error("⚠️ High likelihood of AI-generated content detected.")
            elif ai_score > 35:
                st.warning("⚡ Moderate AI influence or mixed editing detected.")
            else:
                st.success("✅ Content displays natural human writing variation.")

        with col2:
            st.markdown(f"""
                <div class="card-container">
                    <div class="card-title">🌐 Web Plagiarism Score</div>
                    <div class="card-val" style="color: {'#f43f5e' if plag_score > 50 else '#f59e0b' if plag_score > 20 else '#2dd4bf'};">{plag_score}%</div>
                </div>
            """, unsafe_allow_html=True)
            if plag_score > 50:
                st.error(f"⚠️ High similarity found across {len(web_matches)} web sources.")
            elif plag_score > 20:
                st.warning(f"⚡ Moderate similarity found across {len(web_matches)} web sources.")
            else:
                st.success("✅ Zero public web plagiarism detected.")

        st.markdown("<br>", unsafe_allow_html=True)

        # --- Document Stats Strip ---
        st.markdown(f"""
            <div class="stats-strip-bar">
                <div style="text-align: center;"><div class="stat-val-num">{doc_stats['word_count']}</div><div class="stat-val-lbl">Total Words</div></div>
                <div style="text-align: center;"><div class="stat-val-num">{doc_stats['sentence_count']}</div><div class="stat-val-lbl">Sentences</div></div>
                <div style="text-align: center;"><div class="stat-val-num" style="color: #fbbf24;">{doc_stats['ai_flagged_count']}</div><div class="stat-val-lbl">AI Sentences</div></div>
                <div style="text-align: center;"><div class="stat-val-num" style="color: #f43f5e;">{doc_stats['web_matches_count']}</div><div class="stat-val-lbl">Web Matches</div></div>
            </div>
        """, unsafe_allow_html=True)

        # --- Tabbed Workspace ---
        tab1, tab2, tab3, tab4 = st.tabs([
            "🔍 Marked Document Reader", 
            "🌐 Web Source Overlaps", 
            "📊 Sentence-by-Sentence Breakdown",
            "📄 Export Verified PDF"
        ])

        with tab1:
            st.caption("🟨 **Yellow Highlight** = AI-flagged sentence | 🟥 **Red Highlight** = Exact public web match (with source link)")
            highlighted_html = render_highlighted_document(document_text, ai_sents, web_phrases)
            st.markdown(f'<div class="paper-canvas">{highlighted_html}</div>', unsafe_allow_html=True)

        with tab2:
            if web_matches:
                st.subheader(f"Found {len(web_matches)} Matching Web Sources")
                for idx, match in enumerate(web_matches, 1):
                    with st.expander(f"Match #{idx}: {match['title']}"):
                        st.write(f"**Matched Phrase:** \"{match['phrase']}\"")
                        st.write(f"**Direct URL:** [{match['url']}]({match['url']})")
                        if match.get('snippet'):
                            st.caption(f"**Web Snippet:** {match['snippet']}")
            else:
                st.success("✅ No matching public domain sources detected for the checked phrases.")

        with tab3:
            st.subheader("Sentence-by-Sentence Analysis")
            for idx, item in enumerate(sentence_analysis, 1):
                status_icon = "🔴 AI Flagged" if item["is_ai"] else "🟢 Natural Style"
                with st.expander(f"Sentence #{idx} ({item['word_count']} words) — {status_icon}"):
                    st.write(f"\"{item['sentence']}\"")
                    st.caption(f"**Evaluation Reason:** {item['reason']}")

        with tab4:
            st.subheader("Export PDF Audit Report")
            st.write("Download an official summary report for your records:")
            try:
                pdf_bytes = create_pdf_report(ai_score, plag_score, web_matches, doc_stats)
                st.download_button(
                    label="📥 Download WriteSafe PDF Summary Report",
                    data=pdf_bytes,
                    file_name="WriteSafe_Plagiarism_AI_Analysis_Report.pdf",
                    mime="application/pdf",
                    type="primary"
                )
            except Exception as e:
                st.error(f"Could not generate PDF: {e}")
