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
        return 0, []

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

# --- Zero-API Web Plagiarism Search & Percentage Calculation ---
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

    # Calculate Plagiarism Percentage based on proportion of matched queries
    plagiarism_score = round((matched_queries_count / len(selected_queries)) * 100, 1)

    return plagiarism_score, matches, flagged_phrases

# --- Render Document with Inline HTML Highlighting ---
def render_highlighted_document(full_text, ai_sentences, web_flagged_phrases):
    highlighted_text = full_text

    # Highlight Web Matches in Red/Pink
    for phrase, url in web_flagged_phrases:
        escaped_phrase = re.escape(phrase)
        replacement = f'<mark style="background-color: #f8d7da; color: #721c24; padding: 2px; border-radius: 3px;"><b>[Web Match]</b> {phrase} <a href="{url}" target="_blank" style="color: #721c24; text-decoration: underline;">(Source Link)</a></mark>'
        highlighted_text = re.sub(escaped_phrase, replacement, highlighted_text)

    # Highlight AI Sentences in Yellow
    for sent in ai_sentences:
        escaped_sent = re.escape(sent)
        replacement = f'<mark style="background-color: #fff3cd; color: #856404; padding: 2px; border-radius: 3px;"><b>[AI Flagged]</b> {sent}</mark>'
        highlighted_text = re.sub(escaped_sent, replacement, highlighted_text)

    return highlighted_text

# --- Helper to sanitize text for PDF export ---
def clean_pdf_str(text):
    if not text:
        return ""
    # Encode to latin-1 replacing unsupported characters to prevent PDF crashes
    return text.encode('latin-1', 'replace').decode('latin-1')

# --- Robust PDF Summary Generator ---
def create_pdf_report(ai_prob, plag_prob, web_matches):
    pdf = FPDF()
    pdf.add_page()
    
    # Header
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 10, clean_pdf_str("WriteSafe Analysis Report"), new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_font("Helvetica", "I", 10)
    pdf.cell(0, 6, clean_pdf_str("Catch plagiarism and AI-sounding text before you submit."), new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(6)

    # Metrics Summary Box
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, clean_pdf_str("1. Executive Summary"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, clean_pdf_str(f"Estimated AI Probability: {ai_prob}%"), new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 6, clean_pdf_str(f"Estimated Web Similarity / Plagiarism Score: {plag_prob}%"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    # Web Matches Section
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, clean_pdf_str("2. Web & Public Domain Matches"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)

    if web_matches:
        for idx, match in enumerate(web_matches, 1):
            pdf.set_font("Helvetica", "B", 10)
            title_text = clean_pdf_str(f"Match #{idx}: {match['title'][:70]}")
            pdf.cell(0, 6, title_text, new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 9)
            pdf.multi_cell(0, 5, clean_pdf_str(f"Matched Phrase: \"{match['phrase']}\""))
            pdf.multi_cell(0, 5, clean_pdf_str(f"Source URL: {match['url']}"))
            pdf.ln(3)
    else:
        pdf.cell(0, 6, clean_pdf_str("No direct matching public web sources detected."), new_x="LMARGIN", new_y="NEXT")

    pdf.ln(10)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(0, 5, clean_pdf_str("Crafted by: Dr. Joydip Chandra, BRSC"), new_x="LMARGIN", new_y="NEXT", align="C")
    
    return bytes(pdf.output())

# --- Streamlit UI ---
st.set_page_config(page_title="WriteSafe", layout="wide", page_icon="🛡️")

st.title("🛡️ WriteSafe")
st.caption("“Catch plagiarism and AI-sounding text before you submit.”")
st.write("Upload a document (`.pdf`, `.docx`, `.txt`) or paste text to evaluate AI content probability and search public domain sources.")

uploaded_file = st.file_uploader("Upload Document", type=["pdf", "docx", "txt"])
pasted_text = st.text_area("Or paste text here", height=200)

document_text = extract_text(uploaded_file) if uploaded_file else pasted_text

if st.button("Run Full Analysis", type="primary"):
    if not document_text.strip():
        st.warning("Please upload a file or paste text first.")
    else:
        st.divider()

        # 1. AI Analysis
        with st.spinner("Analyzing text for AI generation patterns..."):
            ai_score, ai_sents = analyze_ai_patterns(document_text)

        # 2. Web Search & Similarity Score
        with st.spinner("Searching public web databases for matches..."):
            plag_score, web_matches, web_phrases = check_web_plagiarism(document_text)

        # Display Summary Metrics Side-by-Side
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Estimated AI Probability", f"{ai_score}%")
            if ai_score > 60:
                st.error("⚠️ High likelihood of AI-generated content.")
            elif ai_score > 35:
                st.warning("⚡ Moderate AI influence or mixed editing.")
            else:
                st.success("✅ Content appears predominantly human written.")

        with col2:
            st.metric("Estimated Plagiarism Score", f"{plag_score}%")
            if plag_score > 50:
                st.error(f"⚠️ High similarity found across {len(web_matches)} web source matches.")
            elif plag_score > 20:
                st.warning(f"⚡ Moderate similarity found across {len(web_matches)} web source matches.")
            else:
                st.success("✅ Low or no public web plagiarism detected.")

        st.divider()

        # 3. Marked Document View
        st.subheader("🖍️ Marked Document View")
        st.caption("🟨 Yellow = AI-flagged sentences | 🟥 Red = Public Web matches (with clickable source links)")

        highlighted_html = render_highlighted_document(document_text, ai_sents, web_phrases)
        st.markdown(
            f'<div style="background-color: #ffffff; padding: 20px; border-radius: 8px; border: 1px solid #ddd; line-height: 1.8; color: #222;">{highlighted_html}</div>', 
            unsafe_allow_html=True
        )

        st.divider()

        # 4. Download PDF
        st.subheader("📄 Export Results")
        try:
            pdf_bytes = create_pdf_report(ai_score, plag_score, web_matches)
            st.download_button(
                label="📥 Download PDF Summary Report",
                data=pdf_bytes,
                file_name="WriteSafe_Plagiarism_AI_Analysis_Report.pdf",
                mime="application/pdf"
            )
        except Exception as e:
            st.error(f"Could not generate PDF: {e}")

# --- Footer Credits ---
st.markdown("---")
st.markdown(
    """
    <div style="text-align: center; color: #555; font-size: 15px; font-weight: 500; padding-top: 10px;">
        <b>Crafted by: Dr. Joydip Chandra, BRSC</b>
    </div>
    """,
    unsafe_allow_html=True
)
