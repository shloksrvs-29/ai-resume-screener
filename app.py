import re
import streamlit as st
import pdfplumber
import google.generativeai as genai

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel("gemini-2.5-flash")

# --------------------------------------------------
# PAGE CONFIG
# --------------------------------------------------

st.set_page_config(
    page_title="AI Resume Screener",
    page_icon="🚀",
    layout="wide"
)

# --------------------------------------------------
# CUSTOM CSS
# --------------------------------------------------

st.markdown("""
<style>

.stApp {
    background: linear-gradient(135deg, #0f172a 0%, #111827 30%, #1e293b 100%);
}

#MainMenu {visibility:hidden;}
footer {visibility:hidden;}
header {visibility:hidden;}

.hero-title {
    text-align: center;
    font-size: 4rem;
    font-weight: 800;
    background: linear-gradient(90deg, #38bdf8, #8b5cf6);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 0px;
}

.hero-subtitle {
    text-align: center;
    color: #cbd5e1;
    font-size: 1.1rem;
    margin-bottom: 30px;
}

.glass {
    background: rgba(255,255,255,0.06);
    backdrop-filter: blur(18px);
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 20px;
    padding: 20px;
}

.metric-card {
    background: rgba(255,255,255,0.05);
    backdrop-filter: blur(15px);
    padding: 20px;
    border-radius: 18px;
    text-align: center;
    border: 1px solid rgba(255,255,255,0.08);
}

.metric-value {
    font-size: 2rem;
    font-weight: bold;
    color: #38bdf8;
}

.metric-label {
    color: #94a3b8;
    font-size: 0.85rem;
}

.score-box {
    text-align: center;
    padding: 25px;
}

.score-number {
    font-size: 70px;
    font-weight: 900;
}

.score-high { color: #22c55e; }
.score-mid  { color: #f59e0b; }
.score-low  { color: #ef4444; }

textarea {
    border-radius: 15px !important;
}

div.stButton > button {
    width: 100%;
    background: linear-gradient(90deg, #38bdf8, #8b5cf6);
    color: white;
    font-size: 1.1rem;
    font-weight: 700;
    border: none;
    border-radius: 12px;
    padding: 14px 0;
    cursor: pointer;
    margin-top: 8px;
    transition: opacity 0.2s;
}

div.stButton > button:hover {
    opacity: 0.88;
}

</style>
""", unsafe_allow_html=True)

# --------------------------------------------------
# HERO
# --------------------------------------------------

st.markdown("""
    <h1 class="hero-title">🤖 AI Resume Screener</h1>
    <p class="hero-subtitle">Upload a Resume and paste a Job Description to get AI-powered ATS analysis.</p>
""", unsafe_allow_html=True)

# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------

with st.sidebar:
    st.title("⚙ Dashboard")
    st.info("Upload a PDF resume to begin analysis.")
    st.markdown("---")
    st.markdown("### Features")
    st.markdown("""
    - ✅ PDF Resume Parsing
    - 🎯 Real AI Match Score
    - 🔍 Skill Gap Detection
    - 💡 Tailored Suggestions
    - 📊 Resume Statistics
    """)
    st.markdown("---")
    st.caption("Powered by Google Gemini 2.5 Flash")

# --------------------------------------------------
# SESSION STATE — rate limiting
# --------------------------------------------------

if "analysis_count" not in st.session_state:
    st.session_state.analysis_count = 0

# --------------------------------------------------
# INPUTS
# --------------------------------------------------

uploaded_file = st.file_uploader("📄 Drag & Drop Resume Here", type=["pdf"])

# File size check — must happen right after upload
if uploaded_file and uploaded_file.size > 5 * 1024 * 1024:
    st.error("❌ File too large. Please upload a PDF under 5MB.")
    st.stop()

job_description = st.text_area(
    "📋 Paste Job Description",
    height=200,
    placeholder="Paste the job description here..."
)

analyze_clicked = st.button("🚀 Analyze Resume")

# --------------------------------------------------
# HELPER — extract score from Gemini response
# --------------------------------------------------

def extract_score_from_analysis(text: str):
    patterns = [
        r'match score[^\d]*(\d{1,3})\s*/\s*100',
        r'match score[^\d]*(\d{1,3})',
        r'ats score[^\d]*(\d{1,3})',
        r'\*\*(\d{1,3})\*\*\s*/\s*100',
        r'(\d{1,3})\s*/\s*100',
    ]
    lower = text.lower()
    for pat in patterns:
        m = re.search(pat, lower)
        if m:
            val = int(m.group(1))
            if 0 <= val <= 100:
                return val
    return None

# --------------------------------------------------
# ANALYSIS
# --------------------------------------------------

if analyze_clicked:
    if not uploaded_file:
        st.warning("⚠️ Please upload a PDF resume first.")
    elif not job_description.strip():
        st.warning("⚠️ Please paste a job description first.")
    elif st.session_state.analysis_count >= 3:
        st.warning("⚠️ You've reached the limit of 3 analyses per session. Please refresh the page to start again.")
    else:

        # --- Parse PDF ---
        with st.spinner("📄 Extracting resume text..."):
            resume_text = ""
            with pdfplumber.open(uploaded_file) as pdf:
                total_pages = len(pdf.pages)
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        resume_text += text + "\n"

        if not resume_text.strip():
            st.error("❌ No text could be extracted. The PDF may be scanned as an image.")
            st.stop()

        st.success("Resume Processed Successfully ✅")

        # --- Gemini prompt ---
        prompt = f"""
You are an expert ATS (Applicant Tracking System) recruiter and career coach.

Analyze the candidate's resume against the job description below.

Resume:
{resume_text}

Job Description:
{job_description}

Respond with the following sections in order. Start EACH section with its exact heading on its own line.

**Match Score:** <number from 0 to 100>/100
(A single integer reflecting how well this resume matches the job description.)

**Matched Skills:**
(Bullet list of skills/keywords in the resume that match the JD)

**Missing Skills:**
(Bullet list of important skills/keywords from the JD absent from the resume)

**Strengths:**
(What makes this candidate a good fit for this specific role)

**Weaknesses:**
(What holds this resume back for this specific role)

**Tailored Suggestions:**
(Concrete, specific actions to improve this resume FOR this exact job description — not generic advice)

**Final Recommendation:**
(One of: Strong Match / Good Match / Weak Match / Not a Match — with a 2–3 sentence justification)

Be professional, honest, and specific.
"""

        ai_analysis = None
        with st.spinner("🤖 Gemini AI Analyzing..."):
            try:
                response = model.generate_content(prompt)
                ai_analysis = response.text
                st.session_state.analysis_count += 1
                st.success("✅ Gemini Analysis Complete")
            except Exception as e:
                st.error(f"Gemini API Error: {e}")

        # --- Score ---
        words = len(resume_text.split())
        chars = len(resume_text)

        ai_score = extract_score_from_analysis(ai_analysis) if ai_analysis else None
        score = ai_score if ai_score is not None else min(100, int(words / 6))
        score_source = "AI Match Score" if ai_score is not None else "ATS Score (estimated)"

        if score > 75:
            score_class = "score-high"
        elif score > 50:
            score_class = "score-mid"
        else:
            score_class = "score-low"

        # --------------------------------------------------
        # METRICS
        # --------------------------------------------------

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{total_pages}</div>
                <div class="metric-label">Pages</div>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{words}</div>
                <div class="metric-label">Words</div>
            </div>
            """, unsafe_allow_html=True)

        with col3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{chars}</div>
                <div class="metric-label">Characters</div>
            </div>
            """, unsafe_allow_html=True)

        with col4:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{score}</div>
                <div class="metric-label">{score_source}</div>
            </div>
            """, unsafe_allow_html=True)

        st.write("")

        # --------------------------------------------------
        # DASHBOARD
        # --------------------------------------------------

        left, right = st.columns([2, 1])

        with left:
            st.markdown('<div class="glass">', unsafe_allow_html=True)
            st.subheader("📑 Resume Preview")
            st.text_area("", resume_text, height=500)
            st.markdown('</div>', unsafe_allow_html=True)

        with right:
            st.markdown('<div class="glass score-box"><h3>ATS Match Score</h3>', unsafe_allow_html=True)
            st.progress(score / 100)
            st.markdown(f'<div class="score-number {score_class}">{score}</div>', unsafe_allow_html=True)

            if score > 75:
                st.success("Strong Match ✅")
            elif score > 50:
                st.warning("Moderate Match ⚠️")
            else:
                st.error("Weak Match ❌")

            if ai_score is not None:
                st.caption("Score generated by Gemini AI based on resume–JD match.")
            else:
                st.caption("⚠️ AI score unavailable. Showing word-count estimate.")

            st.markdown("</div>", unsafe_allow_html=True)

        # --------------------------------------------------
        # AI ANALYSIS
        # --------------------------------------------------

        if ai_analysis:
            st.divider()
            st.subheader("🤖 AI Resume Analysis")
            st.markdown(ai_analysis)

        # Show remaining analyses
        remaining = 3 - st.session_state.analysis_count
        st.caption(f"ℹ️ {remaining} analysis/analyses remaining this session.")

else:
    st.markdown("""
    <div class="glass" style="text-align:center;padding:60px;">
        <h2>📤 Upload Your Resume</h2>
        <p>Get a real AI-powered ATS score and tailored feedback instantly.</p>
    </div>
    """, unsafe_allow_html=True)
