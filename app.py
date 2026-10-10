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

# --- Advanced Zero-API AI Content Detector ---
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

    # 1. Signature AI Vocabulary Density
    ai_word_count = sum(1 for w in words if w in AI_SIGNATURE_WORDS)
    vocab_ai_density = (ai_word_count / len(words)) * 100

    # 2. Sentence Length Uniformity (Low variance = higher AI score)
    sent_lengths = [len(s.split()) for s in sentences]
    avg_len = sum(sent_lengths) / len(sent_lengths)
    variance = sum((l - avg_len) ** 2 for l in sent_lengths) / len(sent_lengths)
    std_dev = math.sqrt(variance)

    # 3. Flag Individual AI Sentences
    ai_flagged_sentences = []
    for sent in sentences:
        sent_lower = sent.lower()
        has_ai_word = any(w in sent_lower for w in AI_SIGNATURE_WORDS)
        length_fits_ai = 12 <= len(sent.split()) <= 32
        
        # High likelihood if contains AI keywords or fits uniform structural patterns
        if has_ai_word or (length_fits_ai and std_dev < 5.0):
            ai_flagged_sentences.append(sent)

    # Composite Probability Score Calculation
    base_score = 30 if len(ai_flagged_sentences) > 0 else 5
    ai_sentence_ratio = (len(ai_flagged_sentences) / max(1, len(sentences))) * 50
    vocab_weight = min(30, vocab_ai_density * 15)
    uniformity_weight = max(0, (6.0 - std_dev) * 6)

    total_ai_prob = base_score + ai_sentence_ratio + vocab_weight + uniformity_weight
    final_score = round(max(5.0, min(98.0, total_ai_prob)), 1)

    return final_score, ai_flagged_sentences

# --- Zero-API Web Plagiarism Search ---
def check_web_plagiarism(text, max_queries=4):
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if len(s.split()) >= 6]
    if not sentences:
        return [], []

    step = max(1, len(sentences) // max_queries)
    selected_queries = sentences[::step][:max_queries]

    matches = []
    flagged_phrases = []

    ddgs = DDGS()
    for query in selected_queries:
        try:
            results = list(ddgs.text(f'"{query}"', max_results=2))
            for res in results:
                title = res.get("title", "Public Web Match")
                url = res.get("href", "#")
                snippet = res.get("body", "")
                matches.append({"phrase": query, "title": title, "url": url, "snippet": snippet})
                flagged_phrases.append((query, url))
        except Exception:
            continue

    return matches, flagged_phrases

# --- Render Document with Inline HTML Highlighting ---
def render_highlighted_document(full_text, ai_sentences, web_flagged_phrases):
    highlighted_text = full_text

    # 1. Highlight Web Matches in Red/Pink
    for phrase, url in web_flagged_phrases:
        escaped_phrase = re.escape(phrase)
        replacement = f'<mark style="background-color: #f8d7da; color: #721c24; padding: 2px; border-radius: 3px;"><b>[Web Match]</b> {phrase} <a href="{url}" target="_blank" style="color: #721c24; text-decoration: underline;">(Source Link)</a></mark>'
        highlighted_text = re.sub(escaped_phrase, replacement, highlighted_text)

    # 2. Highlight AI Sentences in Yellow
    for sent in ai_sentences:
        escaped_sent = re.escape(sent)
        replacement = f'<mark style="background-color: #fff3cd; color: #856404; padding: 2px; border-radius: 3px;"><b>[AI Flagged]</b> {sent}</mark>'
        highlighted_text = re.sub(escaped_sent, replacement, highlighted_text)

    return highlighted_text

# --- PDF Summary Generator ---
def create_pdf_report(ai_prob, web_matches):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Plagiarism & AI Analysis Report", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(5)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "1. AI Content Evaluation", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"Estimated AI Probability Score: {ai_prob}%", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "2. Public Web Domain Search Results", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)

    if web_matches:
        for idx, match in enumerate(web_matches, 1):
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(0, 6, f"Match #{idx}: {match['title'][:60]}", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 9)
            pdf.multi_cell(0, 5, f"Matched Phrase: \"{match['phrase']}\"")
            pdf.multi_cell(0, 5, f"Source URL: {match['url']}")
            pdf.ln(3)
    else:
        pdf.cell(0, 6, "No direct matching public web sources detected.", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(10)
    pdf.set_font("Helvetica", "I", 8)
    pdf.cell(0, 5, "Report generated automatically by Plagiarism & AI Content Checker.", new_x="LMARGIN", new_y="NEXT", align="C")
    return bytes(pdf.output())

# --- Interface ---
st.set_page_config(page_title="Plagiarism & AI Detector", layout="wide")
st.title("🔍 Advanced Plagiarism & AI Content Detector")
st.write("Upload a document (`.pdf`, `.docx`, `.txt`) or paste text to perform an instant web search and AI content evaluation.")

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

        # 2. Web Search
        with st.spinner("Searching public web databases for matches..."):
            web_matches, web_phrases = check_web_plagiarism(document_text)

        # Display Metrics
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
            st.metric("Web Matches Found", f"{len(web_matches)}")
            if web_matches:
                st.warning(f"Found {len(web_matches)} matching web sources.")
            else:
                st.success("No direct web matches found.")

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
        pdf_bytes = create_pdf_report(ai_score, web_matches)
        st.download_button(
            label="📥 Download PDF Summary Report",
            data=pdf_bytes,
            file_name="Plagiarism_AI_Analysis_Report.pdf",
            mime="application/pdf"
        )

# --- Footer Credits ---
st.markdown("---")
st.markdown(
    """
    <div style="text-align: center; color: #777; font-size: 14px; padding-top: 10px;">
        Plagiarism & AI Content Checker Software<br>
        <b>Created with ❤️ | Powered by Streamlit & Python NLP</b>
    </div>
    """,
    unsafe_allow_html=True
)
