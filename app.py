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
        return 0.0, []

    ai_word_count = sum(1 for w in words if w in AI_SIGNATURE_WORDS)
    vocab_ai_density = (ai_word_count / len(words)) * 100

    sent_lengths = [len(s.split()) for s in sentences]
    avg_len = sum(sent_lengths) / len(sent_lengths)
    variance = sum((l - avg_len) ** 2 for l in sent_lengths) / len(sent_lengths)
    std_dev = math.sqrt(variance)

    ai_flagged_sentences = []
    for sent in sentences:
        sent_lower = sent.lower()
        has_ai_word = any(w in sent_lower for w in AI_SIGNATURE_WORDS)
        length_fits_ai = 12 <= len(sent.split()) <= 32
        
        if has_ai_word or (length_fits_ai and std_dev < 5.0):
            ai_flagged_sentences.append(sent)

    base_score = 30 if len(ai_flagged_sentences) > 0 else 5
    ai_sentence_ratio = (len(ai_flagged_sentences) / max(1, len(sentences))) * 50
    vocab_weight = min(30, vocab_ai_density * 15)
    uniformity_weight = max(0, (6.0 - std_dev) * 6)

    total_ai_prob = base_score + ai_sentence_ratio + vocab_weight + uniformity_weight
    final_score = round(max(5.0, min(98.0, total_ai_prob)), 1)

    return final_score, ai_flagged_sentences

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

    ddgs = DDGS()
    for query in selected_queries:
        try:
            results = list(ddgs.text(f'"{query}"', max_results=2))
            if results:
                matched_queries_count += 1
                for res in results:
                    title = res.get("title", "Public Web Match")
                    url = res.get("href", "#")
                    snippet = res.get("body", "")
                    matches.append({"phrase": query, "title": title, "url": url, "snippet": snippet})
                    flagged_phrases.append((query, url))
        except Exception:
            continue

    plagiarism_score = round((matched_queries_count / len(selected_queries)) * 100, 1)
    return plagiarism_score, matches, flagged_phrases

# --- HTML Inline Highlighting ---
def render_highlighted_document(full_text, ai_sentences, web_flagged_phrases):
    highlighted_text = full_text

    for phrase, url in web_flagged_phrases:
        escaped_phrase = re.escape(phrase)
        replacement = f'<mark style="background-color: #fee2e2; color: #991b1b; padding: 2px 6px; border-radius: 4px; border: 1px solid #fca5a5; font-weight: 500;"><b>[Web Match]</b> {phrase} <a href="{url}" target="_blank" style="color: #991b1b; text-decoration: underline; font-weight: bold;">(Source)</a></mark>'
        highlighted_text = re.sub(escaped_phrase, replacement, highlighted_text)

    for sent in ai_sentences:
        escaped_sent = re.escape(sent)
        replacement = f'<mark style="background-color: #fef3c7; color: #92400e; padding: 2px 6px; border-radius: 4px; border: 1px solid #fcd34d; font-weight: 500;"><b>[AI Flagged]</b> {sent}</mark>'
        highlighted_text = re.sub(escaped_sent, replacement, highlighted_text)

    return highlighted_text

# --- PDF String Sanitization & Word Wrapper (Prevents PDF Crashes) ---
def clean_pdf_str(text):
    if not text:
        return ""
    return text.encode('latin-1', 'replace').decode('latin-1')

def wrap_long_words(text, max_len=45):
    words = text.split(" ")
    wrapped = []
    for w in words:
        if len(w) > max_len:
            chunks = [w[i:i+max_len] for i in range(0, len(w), max_len)]
            wrapped.append(" ".join(chunks))
        else:
            wrapped.append(w)
    return " ".join(wrapped)

# --- PDF Summary Generator ---
def create_pdf_report(ai_prob, plag_prob, web_matches):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_margins(15, 15, 15)

    # Header
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 10, clean_pdf_str("WriteSafe Analysis Report"), new_x="LMARGIN", new_y="NEXT", align="C")
    
    pdf.set_font("Helvetica", "I", 10)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(0, 6, clean_pdf_str("Catch plagiarism and AI-sounding text before you submit."), new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(6)

    pdf.set_draw_color(226, 232, 240)
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(6)

    # Executive Summary
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 8, clean_pdf_str("1. Executive Summary"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(51, 65, 85)
    pdf.cell(0, 6, clean_pdf_str(f"Estimated AI Probability: {ai_prob}%"), new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, clean_pdf_str(f"Estimated Web Similarity / Plagiarism Score: {plag_prob}%"), new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, clean_pdf_str(f"Total Public Web Matches Detected: {len(web_matches)}"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)

    # Web Matches Section
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 8, clean_pdf_str("2. Public Web Matches Breakdown"), new_x="LMARGIN", new_y="NEXT")

    if web_matches:
        for idx, match in enumerate(web_matches, 1):
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(30, 58, 138)
            title = wrap_long_words(clean_pdf_str(match['title']))
            pdf.multi_cell(0, 6, f"Match #{idx}: {title[:80]}")
            
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(71, 85, 105)
            phrase = wrap_long_words(clean_pdf_str(match['phrase']))
            url = wrap_long_words(clean_pdf_str(match['url']), max_len=40)
            
            pdf.multi_cell(0, 5, f"Matched Phrase: \"{phrase}\"")
            pdf.multi_cell(0, 5, f"Source URL: {url}")
            pdf.ln(3)
    else:
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(71, 85, 105)
        pdf.cell(0, 6, clean_pdf_str("No direct matching public web sources detected."), new_x="LMARGIN", new_y="NEXT")

    pdf.ln(10)
    pdf.set_draw_color(226, 232, 240)
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(6)

    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 6, clean_pdf_str("Crafted by: Dr. Joydip Chandra, BRSC"), new_x="LMARGIN", new_y="NEXT", align="C")
    
    return bytes(pdf.output())

# --- Page Configuration & Custom CSS Styling ---
st.set_page_config(page_title="WriteSafe", layout="wide", page_icon="🛡️")

st.markdown("""
    <style>
    /* Global styles */
    .stApp {
        background-color: #f8fafc;
    }
    
    /* Hero Banner */
    .hero-banner {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        padding: 30px 25px;
        border-radius: 16px;
        color: #ffffff;
        margin-bottom: 25px;
        box-shadow: 0 10px 25px -5px rgba(15, 23, 42, 0.25);
    }
    .hero-title {
        font-size: 32px;
        font-weight: 800;
        letter-spacing: -0.5px;
        margin: 0;
        color: #ffffff;
    }
    .hero-tagline {
        font-size: 16px;
        color: #94a3b8;
        margin-top: 6px;
        font-weight: 400;
    }

    /* Metric Cards */
    .metric-card {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        text-align: center;
    }
    .metric-label {
        font-size: 14px;
        color: #64748b;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .metric-value {
        font-size: 36px;
        font-weight: 800;
        color: #0f172a;
        margin: 8px 0;
    }

    /* Document Marking Box */
    .marked-box {
        background-color: #ffffff;
        padding: 24px;
        border-radius: 12px;
        border: 1px solid #cbd5e1;
        line-height: 2.0;
        font-size: 16px;
        color: #1e293b;
        box-shadow: 0 4px 12px rgba(0,0,0,0.03);
    }

    /* Footer */
    .footer-card {
        background: linear-gradient(90deg, #0f172a 0%, #1e293b 100%);
        color: #f8fafc;
        padding: 16px;
        border-radius: 12px;
        text-align: center;
        font-size: 15px;
        font-weight: 500;
        margin-top: 30px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    }
    </style>
""", unsafe_allow_html=True)

# --- Hero Header ---
st.markdown("""
    <div class="hero-banner">
        <div class="hero-title">🛡️ WriteSafe</div>
        <div class="hero-tagline">“Catch plagiarism and AI-sounding text before you submit.”</div>
    </div>
""", unsafe_allow_html=True)

# --- Sidebar ---
st.sidebar.title("🛡️ About WriteSafe")
st.sidebar.info(
    "**WriteSafe** evaluates your research papers, essays, and documents for "
    "unintentional AI generation patterns and searches public domain web databases for exact word overlaps."
)
st.sidebar.caption("Designed for academic integrity and student submission prep.")

# --- Document Upload / Input ---
uploaded_file = st.file_uploader("Upload Document (.pdf, .docx, .txt)", type=["pdf", "docx", "txt"])
pasted_text = st.text_area("Or paste text directly", height=180, placeholder="Paste your draft text here...")

document_text = extract_text(uploaded_file) if uploaded_file else pasted_text

if st.button("🚀 Run WriteSafe Scan", type="primary", use_container_width=True):
    if not document_text.strip():
        st.warning("Please upload a file or paste text first.")
    else:
        st.markdown("<br>", unsafe_allow_html=True)

        with st.spinner("Analyzing AI vocabulary patterns and searching public web databases..."):
            ai_score, ai_sents = analyze_ai_patterns(document_text)
            plag_score, web_matches, web_phrases = check_web_plagiarism(document_text)

        # --- Score Metrics Section ---
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">Estimated AI Probability</div>
                    <div class="metric-value">{ai_score}%</div>
                </div>
            """, unsafe_allow_html=True)
            if ai_score > 60:
                st.error("⚠️ High likelihood of AI-generated phrasing.")
            elif ai_score > 35:
                st.warning("⚡ Moderate AI influence or mixed editing.")
            else:
                st.success("✅ Predominantly human written.")

        with col2:
            st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">Estimated Plagiarism / Web Score</div>
                    <div class="metric-value">{plag_score}%</div>
                </div>
            """, unsafe_allow_html=True)
            if plag_score > 50:
                st.error(f"⚠️ High similarity across {len(web_matches)} web matches.")
            elif plag_score > 20:
                st.warning(f"⚡ Moderate similarity across {len(web_matches)} web matches.")
            else:
                st.success("✅ Low or no public web overlap detected.")

        st.markdown("<br>", unsafe_allow_html=True)

        # --- Tabs View ---
        tab1, tab2, tab3 = st.tabs(["🖍️ Marked Original Document", "🌐 Detected Web Sources", "📄 Export PDF Report"])

        with tab1:
            st.caption("🟨 **Yellow** = AI-flagged sentence structures | 🟥 **Red** = Public web matches (with clickable source links)")
            highlighted_html = render_highlighted_document(document_text, ai_sents, web_phrases)
            st.markdown(f'<div class="marked-box">{highlighted_html}</div>', unsafe_allow_html=True)

        with tab2:
            if web_matches:
                st.subheader(f"Found {len(web_matches)} Web Source Overlaps")
                for idx, match in enumerate(web_matches, 1):
                    with st.expander(f"Match #{idx}: {match['title']}"):
                        st.write(f"**Matched Phrase:** \"{match['phrase']}\"")
                        st.write(f"**Source URL:** [{match['url']}]({match['url']})")
                        if match.get('snippet'):
                            st.caption(f"**Web Snippet:** {match['snippet']}")
            else:
                st.success("🎉 No matching public domain sources found for the checked phrases.")

        with tab3:
            st.subheader("Download Verified Summary Report")
            try:
                pdf_bytes = create_pdf_report(ai_score, plag_score, web_matches)
                st.download_button(
                    label="📥 Download WriteSafe PDF Report",
                    data=pdf_bytes,
                    file_name="WriteSafe_Plagiarism_AI_Analysis_Report.pdf",
                    mime="application/pdf",
                    type="primary"
                )
            except Exception as e:
                st.error(f"Could not generate PDF: {e}")

# --- Footer Credits ---
st.markdown("""
    <div class="footer-card">
        Crafted by: Dr. Joydip Chandra, BRSC
    </div>
""", unsafe_allow_html=True)
