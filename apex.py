import streamlit as st
import google.generativeai as genai
import os
import PyPDF2 as pdf
from dotenv import load_dotenv
import json
import io
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

input_prompt = """
You are an intelligent and adaptive Applicant Tracking System (ATS) that can analyze resumes across various industries and domains, including but not limited to software development, data science, AI/ML, HR, finance, project management, marketing, and operations.

Your task is to:

1. Understand the candidate’s primary domain or area of expertise based on their resume.
2. Compare the resume against the provided job description.
3. Identify and list relevant **matching keywords** and **missing keywords**.
4. Assign a realistic **JD Match** percentage.
5. Write a concise, professional **Profile Summary** in paragraph form that reflects the candidate's strengths and alignment with the job.
6. Give a final **verdict** on whether the candidate is a good fit.
7. If not a good fit, provide a brief and specific **reason** why.
---

**Resume Text:**
{text}

**Job Description:**
{jd}

---

Respond strictly in **valid JSON** format (no explanations or formatting outside this structure):

{{
  "JD Match": "match_percentage%",
  "MatchingKeywords": ["keyword1", "keyword2"],
  "MissingKeywords": ["keyword3", "keyword4"],
  "Profile Summary": "A well-structured paragraph summarizing the candidate’s strengths and alignment with the job description.",
  "Final Verdict": "Recommended" or "Not Recommended",
  "Reason for Rejection": "Only if Not Recommended. Brief reason highlighting gaps or mismatch."
}}

Requirements:
- Output only the JSON — no markdown, comments, or extra text.
- Ensure 'JD Match' is a realistic percentage (e.g., 60–90% range).
- 'Profile Summary' must be in paragraph form — not bullet points or a list.
- The JSON should be clean and ready for programmatic parsing.
- If the candidate is Recommended, leave 'Reason for Rejection' as an empty string or null.
"""


@st.cache_data
def extract_text_from_pdf(uploaded_file):
    reader = pdf.PdfReader(uploaded_file)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text

def get_gemini_response(prompt):
    try:
        model = genai.GenerativeModel(model_name="models/gemini-2.5-pro")
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        st.error(f"Gemini API Error: {e}")
        return None

st.set_page_config(page_title="APEX", layout="centered")
st.title("APEX — Applicant Profile Evaluator using eXplainable AI")
st.caption("Evaluate your resume against a job description using Generative AI ~ Pavan.")

jd = st.text_area("Job Description", height=200)
uploaded_file = st.file_uploader("Upload Resume (PDF)", type="pdf")

submit = st.button("Submit")

if submit:
    if not uploaded_file or not jd.strip():
        st.warning("Please upload a resume and provide a job description.")
        st.stop()

    with st.spinner("Analyzing your resume..."):
        resume_text = extract_text_from_pdf(uploaded_file)
        prompt = input_prompt.format(text=resume_text, jd=jd)
        response_text = get_gemini_response(prompt)

    st.success("Done!")

    if response_text:
        try:
            cleaned = response_text.strip().strip("`").strip("json").strip()
            response_json = json.loads(cleaned)
            st.success("Analysis Complete")

            # --- JD Match ---
            st.subheader("JD Match")
            match_score = int(response_json["JD Match"].replace("%", "").strip())
            st.progress(match_score)

            if match_score >= 80:
                st.markdown(f"<span style='color: white; background-color: green; padding: 4px 10px; border-radius: 6px;'>High Match: {match_score}%</span>", unsafe_allow_html=True)
            elif match_score >= 50:
                st.markdown(f"<span style='color: black; background-color: orange; padding: 4px 10px; border-radius: 6px;'>Moderate Match: {match_score}%</span>", unsafe_allow_html=True)
            else:
                st.markdown(f"<span style='color: white; background-color: red; padding: 4px 10px; border-radius: 6px;'>Low Match: {match_score}%</span>", unsafe_allow_html=True)

            # --- Matching Keywords ---
            st.subheader("Matching Keywords")
            st.write(", ".join(response_json.get("MatchingKeywords", [])) or "None")

            st.subheader("Missing Keywords")
            st.write(", ".join(response_json.get("MissingKeywords", [])) or "None")

            st.subheader("Profile Summary")
            st.write(response_json.get("Profile Summary", "Not available."))

            st.subheader("Final Verdict")
            verdict = response_json.get("Final Verdict", "Not Available")
            st.write(verdict)

            if verdict == "Not Recommended":
                st.subheader("Reason for Rejection")
                st.write(response_json.get("Reason for Rejection", "No reason provided."))

            pdf_buffer = io.BytesIO()
            c = canvas.Canvas(pdf_buffer, pagesize=letter)
            width, height = letter

            c.setFont("Helvetica-Bold", 12)
            c.drawString(50, height - 50, "APEX - Applicant Profile Evaluator using eXplainable AI")

            c.setFont("Helvetica", 10)
            y = height - 80
            c.drawString(50, y, f"JD Match: {response_json['JD Match']}")
            y -= 20
            c.drawString(50, y, f"Final Verdict: {verdict}")
            if verdict == "Not Recommended":
                y -= 20
                c.drawString(50, y, f"Reason: {response_json.get('Reason for Rejection', '')}")
            y -= 30

            c.drawString(50, y, "Matching Keywords:")
            y -= 15
            for kw in response_json.get("MatchingKeywords", []):
                c.drawString(60, y, f"- {kw}")
                y -= 12

            y -= 10
            c.drawString(50, y, "Missing Keywords:")
            y -= 15
            for kw in response_json.get("MissingKeywords", []):
                c.drawString(60, y, f"- {kw}")
                y -= 12

            y -= 20
            text_obj = c.beginText(50, y)
            text_obj.setFont("Helvetica", 10)
            text_obj.textLines(f"Profile Summary:\n{response_json.get('Profile Summary', '')}")
            c.drawText(text_obj)

            c.showPage()
            c.save()
            pdf_buffer.seek(0)

            st.download_button(
                label="Download Report as PDF",
                data=pdf_buffer,
                file_name="resume_report.pdf",
                mime="application/pdf"
            )

        except json.JSONDecodeError:
            st.warning("The response format is not valid JSON.")
            st.code(response_text)
            st.markdown("""
            **Expected JSON format:**
            ```json
{
  "JD Match": "match_percentage%",
  "MatchingKeywords": ["keyword1", "keyword2"],
  "MissingKeywords": ["keyword3", "keyword4"],
  "Profile Summary": "A well-written paragraph summarizing the candidate’s strengths and alignment with the job description.",
  "Final Verdict": "Recommended" or "Not Recommended",
  "Reason for Rejection": "Only if Not Recommended"
}
Ensure the Profile Summary is a paragraph and all fields are properly enclosed in valid JSON.
""")