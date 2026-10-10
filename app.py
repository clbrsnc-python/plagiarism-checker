import streamlit as st
import re
import math
from collections import Counter
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

# --- AI Content Detection Analysis ---
def analyze_ai_content(text):
    words = re.findall(r'\b\w+\b', text.lower())
    sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
    
    if len(words) < 30 or len(sentences) < 2:
        return 0, "Text is too short for reliable AI evaluation (minimum 30 words required)."
    
    # Sentence length variation (Burstiness)
    sent_lengths = [len(s.split()) for s in sentences]
    avg_sent_len = sum(sent_lengths) / len(sent_lengths)
    variance = sum((l - avg_sent_len) ** 2 for l in sent_lengths) / len(sent_lengths)
    std_dev = math.sqrt(variance)
    
    # Vocabulary diversity (Type-Token Ratio)
    unique_words = len(set(words))
    ttr = unique_words / len(words)
    
    # AI Probability score calculation
    ai_score = 100 - (std_dev * 8 + ttr * 50)
    ai_score = max(5.0, min(95.0, ai_score))
    
    return round(ai_score, 1), f"Average sentence length: {avg_sent_len:.1f} words. Variation index: {std_dev:.1f}."

# --- Web Search / Public Domain Plagiarism Checker ---
def check_web_plagiarism(text, max_queries=3):
    sentences = [s.strip() for s in re.split(r'[.!?]+', text) if len(s.split()) >= 6]
    if not sentences:
        return []
    
    results = []
    step = max(1, len(sentences) // max_queries)
    selected_sentences = sentences[::step][:max_queries]
    
    ddgs = DDGS()
    for query in selected_sentences:
        try:
            search_results = ddgs.text(f'"{query}"', max_results=2)
            if search_results:
                for res in search_results:
                    results.append({
                        "phrase": query,
                        "title": res.get("title", "Web Result"),
                        "url": res.get("href", ""),
                        "snippet": res.get("body", "")
                    })
        except Exception:
            continue
            
    return results

# --- PDF Report Generator ---
def create_pdf_report(ai_prob, ai_details, web_matches):
    pdf = FPDF()
    pdf.add_page()
    
    # Title Header
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Plagiarism & AI Analysis Report", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(5)
    
    # Section 1: AI Content Detection
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "1. AI Content Detection Summary", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"Estimated AI Probability Score: {ai_prob}%", new_x="LMARGIN", new_y="NEXT")
    pdf.multi_cell(0, 6, f"Details: {ai_details}")
    pdf.ln(5)
    
    # Section 2: Public Web Matches
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "2. Public Web Domain Search Results", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    
    if web_matches:
        for idx, match in enumerate(web_matches, 1):
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(0, 6, f"Match #{idx}: {match['title'][:60]}", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", "", 9)
            pdf.multi_cell(0, 5, f"Matched Phrase: \"{match['phrase']}\"")
            pdf.multi_cell(0, 5, f"URL: {match['url']}")
            pdf.multi_cell(0, 5, f"Snippet: {match['snippet'][:150]}...")
            pdf.ln(3)
    else:
        pdf.cell(0, 6, "No direct matching public web sources detected.", new_x="LMARGIN", new_y="NEXT")
        
    pdf.ln(10)
    pdf.set_font("Helvetica", "I", 8)
    pdf.cell(0, 5, "Report generated automatically by Plagiarism & AI Content Checker.", new_x="LMARGIN", new_y="NEXT", align="C")
    
    return bytes(pdf.output())

# --- App Interface ---
st.set_page_config(page_title="AI & Web Plagiarism Checker", layout="wide")
st.title("🔍 Web Plagiarism & AI Content Detector")
st.write("Upload a `.pdf`, `.docx`, or `.txt` document to search public domain web sources and evaluate AI content likelihood.")

uploaded_file = st.file_uploader("Upload Document", type=["pdf", "docx", "txt"])
pasted_text = st.text_area("Or paste text here", height=200)

document_text = extract_text(uploaded_file) if uploaded_file else pasted_text

if st.button("Run Full Analysis", type="primary"):
    if not document_text.strip():
        st.warning("Please upload a file or enter text first.")
    else:
        st.divider()
        
        # 1. AI Content Analysis
        st.subheader("🤖 AI Content Detection")
        ai_prob, details = analyze_ai_content(document_text)
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Estimated AI Probability", f"{ai_prob}%")
        with col2:
            if ai_prob > 65:
                st.error("⚠️ High likelihood of AI-generated content (e.g. ChatGPT/Gemini).")
            elif ai_prob > 35:
                st.warning("⚡ Moderate AI likelihood or mixed human/AI editing.")
            else:
                st.success("✅ Content displays natural human writing variation.")
            st.caption(details)
            
        st.divider()
        
        # 2. Public Web Domain Search
        st.subheader("🌐 Public Web Domain Plagiarism Search")
        with st.spinner("Searching public internet databases for matching sources..."):
            web_matches = check_web_plagiarism(document_text)
            
            if web_matches:
                st.warning(f"Found {len(web_matches)} potential matching sources on the web:")
                for match in web_matches:
                    with st.expander(f"Matched Phrase: \"{match['phrase']}\""):
                        st.write(f"**Source Title:** {match['title']}")
                        st.write(f"**URL:** [{match['url']}]({match['url']})")
                        st.write(f"**Snippet:** {match['snippet']}")
            else:
                st.success("✅ No direct phrase matches found in public search engine results.")

        st.divider()

        # 3. PDF Download Section
        st.subheader("📄 Export Results")
        pdf_bytes = create_pdf_report(ai_prob, details, web_matches)
        
        st.download_button(
            label="📥 Download PDF Summary Report",
            data=pdf_bytes,
            file_name="Plagiarism_AI_Analysis_Report.pdf",
            mime="application/pdf"
        )

# --- Footer Credit Section ---
st.markdown("---")
st.markdown(
    """
    <div style="text-align: center; color: #777; font-size: 14px; padding-top: 10px;">
        Plagiarism & AI Content Checker Software<br>
        <b>Created with ❤️ | Powered by Streamlit, DuckDuckGo Search & Python NLP</b>
    </div>
    """,
    unsafe_allow_html=True
)
