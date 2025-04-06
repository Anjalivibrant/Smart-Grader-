import streamlit as st
import pandas as pd
import google.generativeai as genai
import os
from dotenv import load_dotenv
from io import StringIO
from datetime import datetime
import base64
import pdfplumber
import easyocr
import matplotlib.pyplot as plt
import seaborn as sns

# Load environment variables
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TEACHER_PASSWORD = os.getenv("TEACHER_PASSWORD")

# Configure Gemini API
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("models/gemini-1.5-pro")

# Page config
st.set_page_config(
    page_title="AI Teaching Assistant",
    page_icon="📚",
    layout="wide",
)

# Styling
st.markdown("""
    <style>
    .main {
        background-color: #f9f9f9;
        font-family: 'Segoe UI', sans-serif;
    }
    .reportview-container .markdown-text-container {
        padding-top: 2rem;
    }
    .stButton>button {
        background-color: #4CAF50;
        color: white;
        border-radius: 8px;
        padding: 0.5em 1.5em;
        margin-top: 1em;
    }
    </style>
""", unsafe_allow_html=True)

# Authentication
st.sidebar.header("🔐 Teacher Login")
with st.sidebar.form("login_form"):
    password_input = st.text_input("Enter password", type="password")
    login_button = st.form_submit_button("Login")

# if not login_button or password_input != TEACHER_PASSWORD:
#     st.warning("Please log in with the correct password to access the app.")
#     st.stop()

# Header
st.title("📚 SmartGrader: AI-Powered Teaching Assistant")
st.markdown("""
This tool helps educators by automatically grading assignments and giving personalized feedback to students. It aligns with **UN SDG 4: Quality Education** to ensure inclusive, equitable, and high-quality education.
""")

# Upload and Rubric Input
col1, col2 = st.columns(2)

with col1:
    input_method = st.selectbox("Choose input method", ["Upload CSV", "Upload PDF", "Upload Handwritten Image"])
    rubric = st.text_area("📌 Enter Rubric or Model Answer", height=200, placeholder="Paste your grading rubric or model answer here...")

    if input_method == "Upload CSV":
        uploaded_file = st.file_uploader("📥 Upload CSV of Student Responses", type="csv")
    elif input_method == "Upload PDF":
        uploaded_file = st.file_uploader("📄 Upload PDF with Student Answers", type="pdf")
    elif input_method == "Upload Handwritten Image":
        uploaded_file = st.file_uploader("🖼️ Upload Image of Handwritten Answers", type=["png", "jpg", "jpeg"])

with col2:
    example_download = """Student Name,Answer\nJohn Doe,Photosynthesis is the process by which green plants make food using sunlight.\nJane Smith,It is how plants use sunlight to convert carbon dioxide and water into glucose.\n"""
    st.download_button("📄 Download Sample CSV", data=example_download, file_name="sample_responses.csv")

# Grading logic
if uploaded_file and rubric:
    st.markdown("---")
    st.subheader("🔍 Reviewing Student Answers")

    student_data = []

    if input_method == "Upload CSV":
        df = pd.read_csv(uploaded_file)
        if "Student Name" not in df.columns or "Answer" not in df.columns:
            st.error("❗ CSV must contain 'Student Name' and 'Answer' columns.")
            st.stop()
        student_data = df.to_dict("records")

    elif input_method == "Upload PDF":
        with pdfplumber.open(uploaded_file) as pdf:
            all_text = "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])
        student_data = [{"Student Name": f"Student {i+1}", "Answer": answer.strip()} for i, answer in enumerate(all_text.split("\n\n")) if answer.strip()]

    elif input_method == "Upload Handwritten Image":
        reader = easyocr.Reader(["en"])
        result = reader.readtext(uploaded_file.read(), detail=0, paragraph=True)
        joined_text = " ".join(result)
        student_data = [{"Student Name": "Student 1", "Answer": joined_text}]

    feedback_results = []

    with st.spinner("Analyzing student answers and generating feedback..."):
        for entry in student_data:
            prompt = f"""
            Act as a qualified teacher.
            Here is the rubric or model answer:

            {rubric}

            Evaluate the following student answer:
            """
            prompt += f"\nStudent Answer: {entry['Answer']}\n"
            prompt += "Provide: \n1. A score out of 10. \n2. Personalized feedback with suggestions. \n3. Positive reinforcement for good parts."

            try:
                response = model.generate_content(prompt)
                feedback_text = response.text
                score_line = next((line for line in feedback_text.split("\n") if "score" in line.lower()), "")
                score = int(''.join(filter(str.isdigit, score_line))) if score_line else 0
                feedback_results.append({
                    "Student Name": entry["Student Name"],
                    "Answer": entry["Answer"],
                    "Score": score,
                    "Feedback": feedback_text
                })
            except Exception as e:
                feedback_results.append({
                    "Student Name": entry["Student Name"],
                    "Answer": entry["Answer"],
                    "Score": 0,
                    "Feedback": f"Error: {str(e)}"
                })

    feedback_df = pd.DataFrame(feedback_results)

    st.success("✅ Feedback generated for all students!")
    st.dataframe(feedback_df, use_container_width=True)

    # Charts
    st.subheader("📊 Grading Insights")
    fig, ax = plt.subplots(figsize=(8, 4))
    sns.histplot(feedback_df["Score"], bins=10, kde=True, ax=ax, color="skyblue")
    ax.set_title("Distribution of Student Scores")
    ax.set_xlabel("Score (out of 10)")
    st.pyplot(fig)

    # Download feedback
    feedback_csv = feedback_df.to_csv(index=False)
    b64 = base64.b64encode(feedback_csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="student_feedback_{datetime.now().strftime('%Y%m%d')}.csv">📥 Download Feedback as CSV</a>'
    st.markdown(href, unsafe_allow_html=True)

else:
    st.info("Please upload student responses and enter a rubric to begin.")

# Footer
st.markdown("""
---
✅ This tool supports **UN SDG 4: Quality Education**
Developed using [Streamlit](https://streamlit.io), [Gemini API](https://deepmind.google/technologies/gemini/), EasyOCR, and PDFPlumber
""")