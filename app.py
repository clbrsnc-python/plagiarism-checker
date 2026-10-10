import streamlit as st
import re
import requests
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

# --- Deep AI Detection Pipeline ---
def detect_ai_content(text, hf_token=None):
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]
    if not sentences:
        return 0, []

    ai_flagged_sentences = []
    
    # Optional: Hugging Face Neural Network API
    if hf_token:
        API_URL = "https://api-inference.huggingface.co/models/roberta-base-openai-detector"
        headers = {"Authorization": f"Bearer {hf_token}"}
        total_score = 0
        count = 0
        for sent in sentences:
            if len(sent.split()) < 6:
                continue
            try:
                res = requests.post(API_URL, headers=headers, json={"inputs": sent}, timeout=5)
                if res.status_code == 200:
                    data = res.json()
                    score = next((item['score'] for item in data[0] if item['label'] in ['Fake', 'LABEL_1']), 0)
                    total_score += score
                    count += 1
                    if score > 0.55:
                        ai_flagged_sentences.append(sent)
            except Exception:
                continue
        overall_score = (total_score / count * 100) if count > 0 else 0
        return round(overall_score, 1), ai_flagged_sentences

    # Fallback Heuristic Analysis (Burstiness & Vocabulary)
    words = re.findall(r'\b\w+\b', text.lower())
    if len(words) < 20:
        return 0, []
        
    sent_lengths = [len(s.split()) for s in sentences]
    avg_len = sum(sent_lengths) / max(1, len(sent_lengths))
    variance = sum((l - avg_len) ** 2 for l in sent_lengths) / max(1, len(sent_lengths))
    std_dev = math.sqrt(variance)
    
    # Flag overly uniform sentences
    for sent in sentences:
        words_in_sent = sent.split()
        if 8 <= len(words_in_sent) <= 25 and std_dev < 4.5:
            ai_flagged_sentences.append(sent)
            
    ttr = len(set(words)) / len(words)
    ai_score = max(5.0, min(95.0, 100 - (std_dev * 8 + ttr * 45)))
    return round(ai_score, 1), ai_flagged_sentences

# --- Web & Academic Search Engine (Google / SerpApi / DuckDuckGo) ---
def search_web_plagiarism(text, google_key=None, google_cx=None, serpapi_key=None):
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if len(s.split()) >= 6]
    if not sentences:
        return [], []

    step = max(1, len(sentences) // 4)
    selected_queries = sentences[::step][:4]
    
    matches = []
    flagged_phrases = []

    # 1. Google Custom Search API
    if google_key and google_cx:
        for query in selected_queries:
            url = f"https://www.googleapis.com/customsearch/v1?q=\"{query}\"&key={google_key}&cx={google_cx}"
            try:
                res = requests.get(url, timeout=5).json()
                if "items" in res:
                    for item in res["items"][:2]:
                        matches.append({"phrase": query, "title": item["title"], "url": item["link"], "snippet": item.get("snippet", "")})
                        flagged_phrases.append((query, item["link"]))
            except Exception:
                continue

    # 2. SerpApi (Google Scholar & Academic Search)
    elif serpapi_key:
        for query in selected_queries:
            url = f"https://serpapi.com/search.json?engine=google_scholar&q={query}&api_key={serpapi_key}"
            try:
                res = requests.get(url, timeout=5).json()
                if "organic_results" in res:
                    for item in res["organic_results"][:2]:
                        matches.append({"phrase": query, "title": item.get("title", "Scholar Paper"), "url": item.get("link", "#"), "snippet": item.get("snippet", "")})
                        flagged_phrases.append((query, item.get("link", "#")))
            except Exception:
                continue

    # 3. Fallback: DuckDuckGo Search
    else:
        ddgs = DDGS()
        for query in selected_queries:
            try:
                res_list = list(ddgs.text(f'"{query}"', max_results=2))
                for item in res_list:
                    matches.append({"phrase": query, "title": item.get("title", "Web Match"), "url": item.get("href", ""), "snippet": item.get("body", "")})
                    flagged_phrases.append((query, item.get("href", "")))
            except Exception:
                continue

    return matches, flagged_phrases

# --- Render Document with Inline HTML Highlighting ---
def render_highlighted_document(full_text, ai_sentences, web_flagged_phrases):
    highlighted_text = full_text

    # Highlight Web Plagiarism in Red/Pink with Clickable Links
    for phrase, url in web_flagged_phrases:
        escaped_phrase = re.escape(phrase)
        replacement = f'<mark style="background-color: #f8d7da; color: #721c24; padding: 2px; border-radius: 3px;" title="Source: {url}"><b>[Web Match]</b> {phrase} <a href="{url}" target="_blank" style="color: #721c24; text-decoration: underline;">(Link)</a></mark>'
        highlighted_text = re.sub(escaped_phrase, replacement, highlighted_text)

    # Highlight AI Content in Yellow
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
    pdf.cell(0, 8, "1. AI Content Probability", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"Estimated AI Score: {ai_prob}%", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "2. Public Web & Academic Matches", new_x="LMARGIN", new_y="NEXT")
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

# --- Streamlit UI ---
st.set_page_config(page_title="Plagiarism & AI Detector", layout="wide")
st.title("🔍 Advanced Plagiarism & AI Content Detector")

# --- Sidebar Configuration ---
st.sidebar.header("⚙️ API Configuration (Optional)")
st.sidebar.caption("Provide API keys for Google Search, SerpApi (Google Scholar), or HuggingFace AI detection:")
google_api_key = st.sidebar.text_input("Google Custom Search API Key", type="password")
google_cx_id = st.sidebar.text_input("Google Search Engine ID (CX)", type="password")
serp_api_key = st.sidebar.text_input("SerpApi Key (Google Scholar)", type="password")
hf_api_token = st.sidebar.text_input("HuggingFace API Token (AI Model)", type="password")

# --- Main Interface ---
uploaded_file = st.file_uploader("Upload Document (.pdf, .docx, .txt)", type=["pdf", "docx", "txt"])
pasted_text = st.text_area("Or paste text here", height=200)

document_text = extract_text(uploaded_file) if uploaded_file else pasted_text

if st.button("Run Full Analysis", type="primary"):
    if not document_text.strip():
        st.warning("Please upload a file or paste text first.")
    else:
        st.divider()

        # 1. AI Analysis
        with st.spinner("Analyzing AI generation probability..."):
            ai_score, ai_sents = detect_ai_content(document_text, hf_token=hf_api_token)

        # 2. Web & Academic Search
        with st.spinner("Searching public web & Google Scholar databases..."):
            web_matches, web_phrases = search_web_plagiarism(
                document_text, 
                google_key=google_api_key, 
                google_cx=google_cx_id, 
                serpapi_key=serp_api_key
            )

        # Display Metrics
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Estimated AI Probability", f"{ai_score}%")
            if ai_score > 60:
                st.error("⚠️ High likelihood of AI content.")
            elif ai_score > 30:
                st.warning("⚡ Moderate AI influence.")
            else:
                st.success("✅ Predominantly human written.")

        with col2:
            st.metric("Web / Academic Matches Found", f"{len(web_matches)}")
            if web_matches:
                st.warning("Potential online matches detected.")
            else:
                st.success("No direct web matches found.")

        st.divider()

        # 3. Highlighted Document View
        st.subheader("🖍️ Marked Document View")
        st.caption("🟨 Yellow = AI-flagged sentences | 🟥 Red = Web / Academic matches (with URL links)")
        
        highlighted_html = render_highlighted_document(document_text, ai_sents, web_phrases)
        st.markdown(
            f'<div style="background-color: #ffffff; padding: 20px; border-radius: 8px; border: 1px solid #ddd; line-height: 1.8;">{highlighted_html}</div>', 
            unsafe_allow_html=True
        )

        st.divider()

        # 4. Download PDF
        st.subheader("📄 Export Analysis Report")
        pdf_bytes = create_pdf_report(ai_score, web_matches)
        st.download_button(
            label="📥 Download PDF Summary Report",
            data=pdf_bytes,
            file_name="Plagiarism_AI_Analysis_Report.pdf",
            mime="application/pdf"
        )

# --- Footer ---
st.markdown("---")
st.markdown(
    """
    <div style="text-align: center; color: #777; font-size: 14px; padding-top: 10px;">
        Plagiarism & AI Content Checker Software<br>
        <b>Created with ❤️ | Powered by Streamlit, Google Scholar & Python NLP</b>
    </div>
    """,
    unsafe_allow_html=True
)
