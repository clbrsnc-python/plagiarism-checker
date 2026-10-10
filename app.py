import streamlit as st
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import difflib
from pypdf import PdfReader
from docx import Document

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

st.set_page_config(page_title="Plagiarism Checker", layout="wide")
st.title("📄 Mobile & Desktop Plagiarism Checker")
st.write("Upload `.pdf`, `.docx`, or `.txt` files — or paste text directly to compare.")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Document A")
    file_a = st.file_uploader("Upload Document A", type=["txt", "pdf", "docx"], key="a")
    text_a_input = st.text_area("Or paste text for Document A", height=200)
    text_a = extract_text(file_a) if file_a else text_a_input

with col2:
    st.subheader("Document B")
    file_b = st.file_uploader("Upload Document B", type=["txt", "pdf", "docx"], key="b")
    text_b_input = st.text_area("Or paste text for Document B", height=200)
    text_b = extract_text(file_b) if file_b else text_b_input

if st.button("Check Plagiarism", type="primary"):
    if not text_a.strip() or not text_b.strip():
        st.warning("Please upload a file or paste text in both fields.")
    else:
        vectorizer = TfidfVectorizer(stop_words='english')
        tfidf_matrix = vectorizer.fit_transform([text_a, text_b])
        similarity_score = cosine_similarity(tfidf_matrix)[0][1] * 100

        st.metric(label="Overall Similarity Score", value=f"{similarity_score:.2f}%")

        if similarity_score > 60:
            st.error("⚠️ High similarity detected!")
        elif similarity_score > 30:
            st.warning("⚡ Moderate similarity detected.")
        else:
            st.success("✅ Content appears largely original.")

        st.subheader("Matching Sentence Fragments")
        matcher = difflib.SequenceMatcher(None, text_a, text_b)
        matching_blocks = [m for m in matcher.get_matching_blocks() if m.size >= 20]

        if matching_blocks:
            for block in matching_blocks:
                snippet = text_a[block.a : block.a + block.size].strip()
                if snippet:
                    st.info(f"**Exact Match:** \"{snippet}\"")
        else:
            st.write("No exact verbatim sentence fragments found.")