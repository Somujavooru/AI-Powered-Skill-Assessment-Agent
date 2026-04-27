import ast
import importlib
import io
import json
import re
import time
from typing import Dict, List, Tuple

import streamlit as st
from docx import Document
from pypdf import PdfReader
from fpdf import FPDF

# =====================================================================
# 1. CONFIGURATION & CONSTANTS
# =====================================================================

SKILL_LIBRARY = {
    "python", "java", "javascript", "typescript", "sql", "nosql", "aws", "azure", 
    "gcp", "docker", "kubernetes", "git", "ci/cd", "machine learning", "deep learning", 
    "nlp", "data analysis", "pandas", "numpy", "spark", "airflow", "streamlit", 
    "flask", "fastapi", "langchain", "llamaindex", "prompt engineering", 
    "system design", "rest api", "testing", "c++", "c", "c#", "linux", "embedded systems",
    "react", "node.js", "html", "css", "django", "pytorch", "tensorflow", "keras",
    "scikit-learn", "tableau", "power bi", "excel", "agile", "scrum", "jira",
    "mongodb", "postgresql", "mysql", "redis", "elasticsearch", "microcontrollers",
    "sensor integration", "vlsi design"
}

SYNONYM_MAP = {
    "ml": "machine learning", "dl": "deep learning", 
    "natural language processing": "nlp",
    "k8s": "kubernetes", "golang": "go", 
    "js": "javascript", "ts": "typescript",
    "artificial intelligence": "machine learning",
    "data science": "data analysis"
}

ADJACENT_SKILL_MAP = {
    "python": ["fastapi", "testing", "docker"],
    "java": ["system design", "testing", "rest api"],
    "javascript": ["typescript", "rest api", "testing"],
    "machine learning": ["nlp", "data analysis", "prompt engineering"],
    "nlp": ["langchain", "llamaindex", "prompt engineering"],
    "aws": ["docker", "kubernetes", "ci/cd"],
    "sql": ["data analysis", "spark", "airflow"],
}

RESUME_SUGGESTION_MAP = {
    "sql": "Consider adding SQL projects or coursework.",
    "data analysis": "Include data analysis projects using Python or Excel.",
    "machine learning": "Add ML projects with real datasets.",
    "numpy": "Mention numerical computation using NumPy.",
    "pandas": "Highlight data cleaning and manipulation using Pandas.",
}

SKILL_WEIGHTS = {
    "python": 3, "data analysis": 3, "machine learning": 3, 
    "pandas": 2, "numpy": 2, "sql": 1
}

REAL_LINKS = {
    "python": "https://docs.python.org/3/",
    "pandas": "https://pandas.pydata.org/docs/",
    "numpy": "https://numpy.org/doc/",
    "machine learning": "https://www.coursera.org/learn/machine-learning",
    "sql": "https://mode.com/sql-tutorial/",
    "data analysis": "https://www.kaggle.com/learn/data-cleaning"
}

ACTION_PLAN_MAP = {
    "machine learning": "Build 1 ML project using a real dataset (classification/regression).",
    "data analysis": "Perform EDA using Pandas on a Kaggle dataset.",
    "pandas": "Practice data cleaning, handling missing values, and transformation.",
    "numpy": "Strengthen vectorization and array manipulation skills.",
    "python": "Write Python automation scripts or build a small backend REST API.",
    "sql": "Practice SQL queries (focus on JOINs, Subqueries, and Aggregations)."
}

CAREER_ADVICE_MAP = {
    "machine learning": "Focus on algorithms, model building, and evaluating performance on real datasets.",
    "numpy": "Focus on arrays, vectorization, and optimizing numerical computations.",
    "pandas": "Focus on data cleaning, handling missing values, and data transformation.",
    "python": "Focus on OOP concepts, data structures, and building robust, scalable scripts.",
    "data analysis": "Focus on exploratory data analysis (EDA) and extracting actionable business insights.",
    "sql": "Focus on relational database design, aggregations, and writing complex reporting queries."
}

ADAPTIVE_TIME_MAP = {
    "machine learning": {"Beginner": "6–8 weeks", "Intermediate": "3–4 weeks", "weeks_val": {"Beginner": 7, "Intermediate": 3.5}},
    "numpy": {"Beginner": "1–2 weeks", "Intermediate": "3–5 days", "weeks_val": {"Beginner": 1.5, "Intermediate": 0.5}},
    "pandas": {"Beginner": "2 weeks", "Intermediate": "1 week", "weeks_val": {"Beginner": 2, "Intermediate": 1}},
    "python": {"Beginner": "4–6 weeks", "Intermediate": "2–3 weeks", "weeks_val": {"Beginner": 5, "Intermediate": 2.5}},
    "sql": {"Beginner": "3–4 weeks", "Intermediate": "1–2 weeks", "weeks_val": {"Beginner": 3.5, "Intermediate": 1.5}},
    "data analysis": {"Beginner": "4–5 weeks", "Intermediate": "2 weeks", "weeks_val": {"Beginner": 4.5, "Intermediate": 2}}
}

DIFFICULTY_MAP = {
    "machine learning": "Hard", "pandas": "Medium", "numpy": "Easy",
    "python": "Medium", "sql": "Medium", "data analysis": "Medium"
}

DEMO_JD = """Looking for a Data Scientist/AI Engineer. Required skills: Python, Machine Learning, Data Analysis, Pandas, and SQL. Candidate must be able to build predictive models, clean data, and write complex database queries."""
DEMO_RESUME = """Software Engineer with 2 years of experience. Strong background in Python and Java. Built scalable web applications using REST APIs and Docker. Familiar with SQL databases and Git. Basic understanding of Machine learning. No real-world Data Analysis experience. Interested in transitioning to AI."""


# =====================================================================
# 2. FILE PROCESSING
# =====================================================================

def extract_text_from_pdf(file_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(file_bytes))
    extracted_text = []
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            extracted_text.append(page_text)
    return "\n".join(extracted_text)

def extract_text_from_docx(file_bytes: bytes) -> str:
    doc = Document(io.BytesIO(file_bytes))
    extracted_text = []
    for paragraph in doc.paragraphs:
        if paragraph.text:
            extracted_text.append(paragraph.text)
    return "\n".join(extracted_text)

def parse_uploaded_file(uploaded_file) -> str:
    if uploaded_file is None:
        return ""
        
    raw_bytes = uploaded_file.getvalue()
    file_name = uploaded_file.name.lower()
    
    if file_name.endswith(".pdf"):
        return extract_text_from_pdf(raw_bytes)
    if file_name.endswith(".docx"):
        return extract_text_from_docx(raw_bytes)
    if file_name.endswith(".txt"):
        return raw_bytes.decode("utf-8", errors="ignore")
        
    return ""


# =====================================================================
# 3. DETERMINISTIC EXTRACTION & AI CLASSIFICATION
# =====================================================================

def extract_skills_deterministic(text: str) -> List[str]:
    """
    100% Deterministic extraction based on predefined dictionary.
    Prevents AI hallucinations, UI breaking, and sentence extraction.
    """
    if not text or not isinstance(text, str):
        return []
        
    text_lower = text.lower()
    found_skills = set()
    
    # Check library
    for skill in SKILL_LIBRARY:
        pattern = rf"\b{re.escape(skill)}\b"
        if re.search(pattern, text_lower):
            found_skills.add(skill.title())
            
    # Check synonyms
    for syn, canonical in SYNONYM_MAP.items():
        pattern = rf"\b{re.escape(syn)}\b"
        if re.search(pattern, text_lower):
            found_skills.add(canonical.title())
            
    # Extract explicitly if comma separated list provided
    if "," in text and len(text) < 1000:
        parts = [p.strip().title() for p in text.split(",") if p.strip()]
        if parts and all(len(p.split()) <= 4 for p in parts):
            found_skills.update(parts)

    return sorted(list(found_skills))

def ai_call(prompt: str) -> str | None:
    provider = st.session_state.get("provider")
    api_key = st.session_state.get("api_key", "").strip()

    if provider != "gemini" or not api_key:
        return None

    try:
        genai = importlib.import_module("google.generativeai")
        genai.configure(api_key=api_key)
        
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        preferred = ["models/gemini-1.5-flash", "models/gemini-1.5-pro", "models/gemini-2.0-flash-exp", "models/gemini-pro", "models/gemini-1.0-pro"]
        models_to_try = [p for p in preferred if p in available_models]
        
        if not models_to_try:
            models_to_try = [m for m in available_models if "gemini" in m]
            
        if not models_to_try:
             return f"AI Error: No compatible Gemini models found for this API key. Available: {available_models}"

        last_error = None
        for model_name in models_to_try:
            try:
                # Model name from list_models already includes 'models/' prefix
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(prompt)
                return getattr(response, "text", None)
            except Exception as e:
                last_error = e
                continue
                
        return f"AI Error: Failed to generate content. Models tried: {models_to_try}. Last error: {str(last_error)}"
    except Exception as e:
        return f"AI Error: {str(e)}"

def classify_skill_with_ai(skill: str, resume_text: str) -> str:
    """Bulletproof AI classification with fallback."""
    prompt = f"""
You are an expert recruiter.
Skill: {skill}
Resume:
{resume_text[:3500]}
Classify the candidate's proficiency for this skill.
Rules:
"used in project", "worked on", "built", "implemented" → strong_match
"basic", "familiar", "learning" → basic_match
"no experience", "not used", "yet" → missing

Return ONLY JSON:
{{
"level": "strong_match" | "basic_match" | "missing"
}}
"""
    response = ai_call(prompt)
    
    if not response or response.startswith("AI Error"):
        return "missing"
    
    try:
        text = str(response).strip()
        # Extract JSON safely
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end != 0 and end > start:
            json_text = text[start:end]
            data = json.loads(json_text)
            return data.get("level", "missing").strip().lower()
    except Exception:
        pass
        
    return "missing"

def analyze_skills_with_llm(jd_text: str, resume_text: str) -> Dict:
    prompt = f"""
You are an AI Skill Gap Analyzer.

Your task is to compare a Job Description (JD) and a Candidate Resume and produce a highly accurate skill gap analysis.

STRICT INSTRUCTIONS:

STRICT RULES:
- Only consider skills explicitly mentioned in the Job Description.
- Do not generate or assume extra skills (e.g., dashboards, pipelines).
- If a skill is indirectly present (projects/experience), classify it as PARTIAL (Medium Priority).
- ATS score must be calculated only using core JD skills.

1. SKILL EXTRACTION:
- Extract ALL technical skills from both JD and Resume.
- Normalize skills (case-insensitive, remove duplicates).
- Map synonyms:
  - "Data Structures", "DSA", "Algorithms" -> "Data Structures & Algorithms"
  - "REST API", "RESTful APIs", "APIs" -> "REST APIs"
  - "SQL", "MySQL", "PostgreSQL" -> "SQL"
  - "HTML5", "CSS3" -> "HTML", "CSS"

2. CLASSIFICATION & NOISE REDUCTION:
- Matched Skills -> Present in both JD and Resume.
- Missing Skills -> MUST be explicitly mentioned in JD but NOT in Resume. Do NOT invent or add skills like "Dashboards" or "Data Pipelines" unless they are explicitly written in the JD. Only count core JD skills.
- Additional Skills -> Present in Resume but NOT in JD.

3. PRIORITY LOGIC (Divide Missing Skills):
- Critical -> Core/essential skills (e.g., Pandas, NumPy, Data Analysis, Python, SQL).
- Important -> Supporting skills (e.g., Data Visualization, Dashboards).
- Optional -> Bonus or less relevant skills.

4. CONFIDENCE SCORE:
- Assign confidence (0-100%) based on:
  - Explicit mention -> high
  - Weak or indirect mention -> medium
  - Not mentioned -> 0

5. ATS SCORE (WEIGHTED CALCULATION):
- ONLY count core JD skills.
- Calculate a weighted score:
  - Critical skills account for 50% of the maximum score.
  - Important skills account for 30% of the maximum score.
  - Optional skills account for 20% of the maximum score.
- Return an integer score between 0 and 100 based strictly on this weighted calculation representing the candidate's alignment.

6. RESUME SUGGESTIONS:
- Output SHORT, powerful bullet points. (e.g. "Learn Pandas & NumPy", "Build 1 dashboard project"). Do NOT write long paragraphs.

7. CAREER ROLE PREDICTION:
- Evaluate the resume and predict the best-suited career role for this candidate (e.g. "Data Analyst", "Backend Developer", "Embedded Engineer").

8. OUTPUT FORMAT (STRICT JSON):
{{
  "matched_skills": [],
  "missing_skills": [],
  "additional_skills": [],
  "priority": {{
    "critical": [],
    "important": [],
    "optional": []
  }},
  "confidence": {{
    "skill_name": 100
  }},
  "ats_score": 85,
  "predicted_role": "Data Analyst",
  "suggestions": [
    "Learn Pandas & NumPy",
    "Build 1 dashboard project"
  ]
}}

Job Description:
{jd_text}

Candidate Resume:
{resume_text}
"""
    response = ai_call(prompt)
    print(f"Raw LLM Response: {response}")
    if not response or response.startswith("AI Error"):
        return {"error": f"AI Error: {response}"}
    
    try:
        text = str(response).strip()
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end != 0 and end > start:
            return json.loads(text[start:end])
    except Exception as e:
        return {"error": f"JSON parsing failed: {e}", "raw": text}
    
    return {"error": "No JSON object found in response", "raw": response}


# =====================================================================
# 4. LLM LEARNING PLAN GENERATOR (JSON PARSING)
# =====================================================================

def _extract_json_object(raw_text: str) -> Dict:
    if not raw_text:
        return {}
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw_text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                return {}
    return {}

def generate_learning_plan(skill: str, score: float) -> Dict:
    score_out_of_5 = (score / 100) * 5
    default_level = score_to_level(score)
    
    if default_level == "Beginner":
        default_path = "Beginner -> Intermediate"
    else:
        default_path = "Intermediate -> Advanced"
        
    default_plan = {
        "current_level": default_level,
        "progression_path": default_path,
        "time_to_competency": time_to_competency_from_score(score),
        "adjacent_skills": ADJACENT_SKILL_MAP.get(skill.lower(), ["communication", "problem solving", "testing"])[:2],
        "weekly_roadmap": build_weekly_roadmap(skill, score),
        "resources": module_resources(skill),
    }

    prompt = f"""
Create a concise 4-week learning plan for the skill: {skill}
Current proficiency score: {score}/100

Return ONLY JSON in this format:
{{
  "current_level": "Beginner|Intermediate|Advanced",
  "progression_path": "Beginner -> Intermediate",
  "time_to_competency": "4-6 weeks",
  "adjacent_skills": ["skill1", "skill2"],
  "weekly_roadmap": [
    {{"week": "Week 1", "stage": "Beginner", "focus": "...", "outcome": "..."}},
    {{"week": "Week 2", "stage": "Beginner -> Intermediate", "focus": "...", "outcome": "..."}},
    {{"week": "Week 3", "stage": "Intermediate", "focus": "...", "outcome": "..."}},
    {{"week": "Week 4", "stage": "Intermediate", "focus": "...", "outcome": "..."}}
  ],
  "resources": [
    {{"title": "Resource 1", "link": "https://example.com"}},
    {{"title": "Resource 2", "link": "https://example.com"}}
  ]
}}
"""

    ai_response = ai_call(prompt)
    if not ai_response or ai_response.startswith("AI Error:"):
        return default_plan

    try:
        parsed = _extract_json_object(ai_response)
        if not isinstance(parsed, dict) or "weekly_roadmap" not in parsed:
            start = ai_response.find("{")
            end = ai_response.rfind("}") + 1
            if start != -1 and end > start:
                parsed = json.loads(ai_response[start:end])
            else:
                return default_plan
            
        parsed_current_level = str(parsed.get("current_level", default_plan["current_level"]))
        parsed_prog_path = str(parsed.get("progression_path", default_plan["progression_path"]))
        parsed_time = str(parsed.get("time_to_competency", default_plan["time_to_competency"]))
        parsed_adj_skills = parsed.get("adjacent_skills", default_plan["adjacent_skills"])
        if not isinstance(parsed_adj_skills, list):
            parsed_adj_skills = default_plan["adjacent_skills"]
            
        parsed_roadmap = parsed.get("weekly_roadmap", default_plan["weekly_roadmap"])
        if not isinstance(parsed_roadmap, list):
            parsed_roadmap = default_plan["weekly_roadmap"]
            
        parsed_resources = parsed.get("resources", default_plan["resources"])
        
        return {
            "current_level": parsed_current_level,
            "progression_path": parsed_prog_path,
            "time_to_competency": parsed_time,
            "adjacent_skills": parsed_adj_skills,
            "weekly_roadmap": parsed_roadmap,
            "resources": parsed_resources,
        }
    except Exception:
        pass
    
    return default_plan


# =====================================================================
# 5. CHATBOT ASSESSMENT WORKFLOW FUNCTIONS (UPDATED)
# =====================================================================

def build_assessment_questions(skill: str) -> List[str]:
    """Generates exactly 2 deep assessment questions per skill."""
    q1 = f"Explain a real-world project where you used {skill.title()}. Include specific tools used, technical challenges faced, and the outcomes achieved."
    q2 = f"How do you handle advanced scenarios or optimize performance specifically when working with {skill.title()}?"
    return [q1, q2]

def start_assessment(missing_skills: List[str], max_skills: int = 2) -> Dict:
    """Initializes the deep assessment for the top 2 missing skills."""
    selected = missing_skills[:max_skills]
    
    if not selected:
        return {
            "queue": [],
            "current_skill_idx": 0,
            "current_question_idx": 0,
            "questions_map": {},
            "scores": {},
            "history": [],
            "completed": True
        }

    questions_map = {skill: build_assessment_questions(skill) for skill in selected}
    first_skill = selected[0]
    first_question = questions_map[first_skill][0]
    tip_msg = "*Tip: Mention project + tools + challenge + result to improve your score.*"

    initial_history = [
        {
            "role": "assistant", 
            "content": f"Let's deeply assess your missing skills to update your profile. First skill: **{first_skill}**.\n\n{first_question}\n\n{tip_msg}"
        }
    ]

    return {
        "queue": selected,
        "current_skill_idx": 0,
        "current_question_idx": 0,
        "questions_map": questions_map,
        "scores": {skill: [] for skill in selected},
        "history": initial_history,
        "completed": False
    }

def compute_final_proficiency(assessment_scores: Dict[str, List[float]]) -> Dict[str, float]:
    final_scores = {}
    for skill, scores in assessment_scores.items():
        if not scores:
            final_scores[skill] = 0.0
        else:
            average_score = sum(scores) / len(scores)
            final_scores[skill] = round(average_score, 2)
    return final_scores

# =====================================================================
# 6. UI HELPER & LABELING FUNCTIONS
# =====================================================================

def score_to_percentage(score: float) -> int:
    clamped_score = max(0.0, min(100.0, score))
    return int(round(clamped_score))

def score_to_level(score: float) -> str:
    if score >= 80.0:
        return "Strong"
    if score >= 50.0:
        return "Partial"
    return "Weak"

def skill_label(skill: str) -> str:
    emoji_map = {
        "data analysis": "📊 Data Analysis",
        "machine learning": "⚙️ Machine Learning",
        "numpy": "🧮 NumPy",
        "pandas": "📈 Pandas",
        "python": "🐍 Python",
        "sql": "🗄️ SQL",
        "java": "☕ Java",
        "aws": "☁️ AWS",
        "docker": "🐳 Docker"
    }
    skill_key = skill.lower().strip()
    if skill_key in emoji_map:
        return emoji_map[skill_key]
    return skill.title()

def render_skill_card(title: str, skills: List[str], variant: str) -> None:
    css_class = f"skill-card-{variant}"
    badge_class = f"skill-badge-{variant}"
    
    html_items = []
    if skills:
        for s in skills:
            label = skill_label(s)
            html_items.append(f"<span class='skill-badge {badge_class}'>{label}</span>")
        body = "".join(html_items)
    else:
        body = "<div class='skill-card-empty'>No skills in this category.</div>"

    card_html = f"""
        <div class="skill-card {css_class}">
            <h4>{title}</h4>
            <ul>{body}</ul>
        </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)

def module_resources(skill: str) -> List[Tuple[str, str]]:
    return [
        (f"{skill.title()} Fundamentals", "https://example.com/fundamentals"),
        (f"Hands-on {skill.title()} Project", "https://example.com/project"),
        (f"Advanced {skill.title()} Patterns", "https://example.com/advanced"),
    ]

def time_to_competency_from_score(score: float) -> str:
    if score >= 80.0:
        return "1-2 weeks"
    if score >= 50.0:
        return "3-4 weeks"
    return "6-8 weeks"

def build_weekly_roadmap(skill: str, score: float) -> List[Dict[str, str]]:
    title = skill.title()
    return [
        {
            "week": "Week 1",
            "stage": "Beginner",
            "focus": f"Basics: core concepts and setup for {title}",
            "outcome": f"Understand fundamentals and run basic {title} examples.",
        },
        {
            "week": "Week 2",
            "stage": "Beginner -> Intermediate",
            "focus": f"Practice: guided exercises and real scenarios in {title}",
            "outcome": f"Solve routine tasks in {title} with confidence.",
        },
        {
            "week": "Week 3",
            "stage": "Intermediate",
            "focus": f"Mini Project: build a focused project using {title}",
            "outcome": f"Deliver a small end-to-end {title} project.",
        },
        {
            "week": "Week 4",
            "stage": "Intermediate",
            "focus": f"Advanced Topics: optimization, edge cases, and best practices in {title}",
            "outcome": f"Apply {title} effectively to more complex tasks.",
        },
    ]

def generate_plan(gap_report: Dict[str, List[str]], proficiency: Dict[str, float]) -> List[Dict]:
    missing_skills = gap_report.get("missing_skills", [])
    plan = []

    for skill in missing_skills:
        score = proficiency.get(skill, 0.0)
        percentage = score_to_percentage(score)
        llm_plan = generate_learning_plan(skill, score)
        
        plan_dict = {
            "skill": skill,
            "current_proficiency": score,
            "percentage": percentage,
            "current_level": llm_plan["current_level"],
            "progression_path": llm_plan["progression_path"],
            "adjacent_skills": llm_plan["adjacent_skills"],
            "time_to_competency": llm_plan["time_to_competency"],
            "weekly_roadmap": llm_plan["weekly_roadmap"],
            "resources": llm_plan["resources"],
        }
        plan.append(plan_dict)

    return plan

def generate_pdf_report(report: Dict, ats_score: int) -> bytes:
    pdf = FPDF()
    pdf.add_page()
    
    def safe_text(txt):
        return str(txt).encode('latin-1', 'replace').decode('latin-1')
    
    pdf.set_font("Arial", "B", 18)
    pdf.cell(200, 10, "AI Skill Assessment Report", ln=True, align="C")
    pdf.ln(10)
    
    pdf.set_font("Arial", "B", 14)
    pdf.cell(200, 10, f"ATS Match Score: {ats_score}%", ln=True)
    pdf.ln(5)
    
    pdf.set_font("Arial", "B", 12)
    pdf.cell(200, 10, "Matched Skills (Strong):", ln=True)
    pdf.set_font("Arial", "", 12)
    for s in report.get("matched_skills", []):
        pdf.cell(200, 8, safe_text(f"- {s}"), ln=True)
    pdf.ln(5)
    
    pdf.set_font("Arial", "B", 12)
    pdf.cell(200, 10, "Missing & Partial Skills:", ln=True)
    pdf.set_font("Arial", "", 12)
    for s in report.get("missing_skills", []):
        pdf.cell(200, 8, safe_text(f"- {s}"), ln=True)
    pdf.ln(10)
    
    pdf.set_font("Arial", "B", 14)
    pdf.cell(200, 10, "Career Recommendation:", ln=True)
    pdf.set_font("Arial", "", 12)
    
    if ats_score < 40:
        advice = "Focus on building strong fundamentals and beginner projects for your missing skills."
    elif ats_score < 80:
        advice = "Work on intermediate projects and strengthen weak areas to become job-ready."
    else:
        advice = "Your profile is very strong. Prepare for interviews and focus on advanced concepts."
        
    pdf.multi_cell(0, 8, safe_text(advice))

    return pdf.output(dest="S").encode("latin-1")


# =====================================================================
# 7. APP STATE & UI INJECTION
# =====================================================================

def ensure_session_state() -> None:
    defaults = {
        "gap_report": None,
        "assessment": None,
        "proficiency": None,
        "learning_plan": None,
        "provider": "gemini",
        "api_key": "",
        "use_llm": False,
        "assessment_answers": {},
        "assessment_scores": {},
        "assessment_feedback": {},
        "demo_mode": False,
        "jd_text_input": "",
        "resume_text_input": "",
        "parsed_jd_content": "",
        "parsed_resume_content": "",
        "run_deep_assess": False
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

def inject_custom_ui() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

        :root {
            --bg-deep: #050b14;
            --bg-mid: #0a192f;
            --accent-cyan: #64ffda;
            --accent-purple: #b392f0;
            --accent-green: #10b981;
            --accent-red: #ef4444;
            --accent-yellow: #fbbf24;
            --text-main: #ccd6f6;
            --glass-bg: rgba(17, 34, 64, 0.4);
            --glass-border: rgba(100, 255, 218, 0.1);
        }

        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif !important;
            color: var(--text-main);
        }

        .stApp {
            background: linear-gradient(135deg, #0f2027, #203a43, #2c5364);
            background-size: 400% 400%;
            animation: gradientBG 10s ease infinite;
            background-attachment: fixed;
        }

        @keyframes gradientBG {
            0% {background-position: 0% 50%;}
            50% {background-position: 100% 50%;}
            100% {background-position: 0% 50%;}
        }

        .stApp::before, .stApp::after {
            content: "";
            position: fixed;
            width: 400px;
            height: 400px;
            border-radius: 50%;
            filter: blur(80px);
            z-index: 0;
            pointer-events: none;
            animation: pulseGlow 15s infinite alternate ease-in-out;
        }

        .stApp::before {
            background: rgba(100, 255, 218, 0.05);
            top: -100px;
            right: -100px;
        }

        .stApp::after {
            background: rgba(179, 146, 240, 0.05);
            bottom: -100px;
            left: -100px;
            animation-delay: -5s;
        }

        @keyframes pulseGlow {
            0% { transform: scale(0.8) translate(0px, 0px); opacity: 0.5; }
            50% { transform: scale(1) translate(-20px, 20px); opacity: 0.8; }
            100% { transform: scale(1.2) translate(20px, -20px); opacity: 0.6; }
        }

        [data-testid="stAppViewContainer"] > .main {
            position: relative;
            z-index: 1;
        }

        /* CARDS & GLASSMORPHISM */
        .hero-card, [data-testid="stFileUploader"], [data-testid="stTextArea"], [data-testid="stSelectbox"], .skill-card {
            background: var(--glass-bg) !important;
            backdrop-filter: blur(12px) !important;
            -webkit-backdrop-filter: blur(12px) !important;
            border: 1px solid var(--glass-border) !important;
            border-radius: 16px !important;
            box-shadow: 0 4px 30px rgba(0, 0, 0, 0.3) !important;
            transition: all 0.3s ease !important;
            animation: fadeInUp 0.6s ease forwards;
        }

        @keyframes fadeInUp {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .hero-card:hover, .skill-card:hover {
            transform: translateY(-4px) !important;
            box-shadow: 0 10px 40px rgba(100, 255, 218, 0.08) !important;
            border: 1px solid rgba(100, 255, 218, 0.2) !important;
        }

        /* Typography */
        .hero-title, h1, h2, h3, h4, h5 {
            font-weight: 600 !important;
            color: #e6f1ff !important;
            letter-spacing: -0.5px;
        }

        [data-testid="stSidebar"] {
            background: rgba(10, 25, 47, 0.85) !important;
            backdrop-filter: blur(16px);
            border-right: 1px solid var(--glass-border);
        }

        .stButton > button {
            background: linear-gradient(90deg, #64ffda, #10b981) !important;
            color: #0a192f !important;
            border: none !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
            letter-spacing: 0.5px;
            transition: all 0.3s ease !important;
            text-transform: uppercase;
            font-size: 0.9rem !important;
            box-shadow: 0 4px 15px rgba(100, 255, 218, 0.3) !important;
        }
        
        .stButton > button:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 6px 20px rgba(100, 255, 218, 0.5) !important;
        }

        /* SKILL TAGS */
        .skill-badge {
            display: inline-flex;
            align-items: center;
            border-radius: 999px;
            padding: 6px 14px;
            margin: 4px 2px;
            font-size: 0.85rem;
            font-weight: 500;
            letter-spacing: 0.3px;
            transition: all 0.3s ease;
            cursor: default;
        }
        .skill-badge:hover {
            transform: scale(1.05);
        }

        .skill-badge-matched {
            background: rgba(16, 185, 129, 0.1) !important;
            border: 1px solid rgba(16, 185, 129, 0.4) !important;
            color: var(--accent-green) !important;
            box-shadow: 0 0 10px rgba(16, 185, 129, 0.15) !important;
        }
        .skill-badge-matched:hover {
            box-shadow: 0 0 15px rgba(16, 185, 129, 0.4) !important;
        }

        .skill-badge-missing {
            background: rgba(239, 68, 68, 0.1) !important;
            border: 1px solid rgba(239, 68, 68, 0.4) !important;
            color: var(--accent-red) !important;
            box-shadow: 0 0 10px rgba(239, 68, 68, 0.15) !important;
        }
        .skill-badge-missing:hover {
            box-shadow: 0 0 15px rgba(239, 68, 68, 0.4) !important;
        }

        .skill-badge-partial {
            background: rgba(251, 191, 36, 0.1) !important;
            border: 1px solid rgba(251, 191, 36, 0.4) !important;
            color: var(--accent-yellow) !important;
            box-shadow: 0 0 10px rgba(251, 191, 36, 0.15) !important;
        }
        .skill-badge-partial:hover {
            box-shadow: 0 0 15px rgba(251, 191, 36, 0.4) !important;
        }

        .skill-badge-additional {
            background: rgba(179, 146, 240, 0.1) !important;
            border: 1px solid rgba(179, 146, 240, 0.4) !important;
            color: var(--accent-purple) !important;
            box-shadow: 0 0 10px rgba(179, 146, 240, 0.15) !important;
        }
        .skill-badge-additional:hover {
            box-shadow: 0 0 15px rgba(179, 146, 240, 0.4) !important;
        }

        [data-testid="stAlert"] {
            border-radius: 12px !important;
            border: 1px solid var(--glass-border) !important;
            background: rgba(17, 34, 64, 0.6) !important;
            backdrop-filter: blur(10px) !important;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2) !important;
        }

        hr {
            border-top: 1px solid rgba(255, 255, 255, 0.08) !important;
            margin: 2rem 0 !important;
        }
        .role-prediction-banner {
            background: rgba(100, 255, 218, 0.1);
            border: 1px solid var(--accent-cyan);
            padding: 15px;
            border-radius: 12px;
            margin: 20px 0;
            backdrop-filter: blur(10px);
            text-align: center;
        }

        .role-prediction-banner span {
            font-weight: 700;
            color: var(--accent-cyan);
            font-size: 1.2rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# =====================================================================
# 8. MAIN APP ROUTING & EXECUTION
# =====================================================================

def main() -> None:
    st.set_page_config(page_title="AI Skill Assessment Agent", layout="wide")
    ensure_session_state()
    inject_custom_ui()

    st.title("🎯 AI Skill Gap Analyzer")
    st.markdown(
        """
        <div class="hero-card">
            <div class="hero-title">AI-Powered Skill Assessment and Personalized Learning Plan Agent</div>
            <div class="hero-sub">Hackathon PoC with robust deterministic extraction and AI-driven classification.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.header("LLM Configuration")
        
        use_llm_val = st.session_state["use_llm"]
        use_llm = st.checkbox("Enable AI (LLM) Processing", value=use_llm_val)
        st.session_state["use_llm"] = use_llm
        
        provider = st.selectbox("Select Provider", ["openai", "gemini"])
        st.session_state["provider"] = provider
        
        api_key = st.text_input("Enter API Key", type="password")
        if api_key: 
            st.session_state["api_key"] = api_key.strip()
            
        if use_llm and not st.session_state.get("api_key", "").strip():
            st.error("Please enter API key to use AI features")
            
        st.divider()
        st.header("🚀 Quick Start")
        if st.button("Run Demo"):
            st.session_state["demo_mode"] = True
            st.session_state["jd_text_input"] = DEMO_JD
            st.session_state["resume_text_input"] = DEMO_RESUME
            st.rerun()

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📄 Job Description Input")
        jd_file = st.file_uploader("Upload JD (PDF/DOCX/TXT)", type=["pdf", "docx", "txt"], key="jd_file")
        jd_text = st.text_area("Or paste JD text", value=st.session_state.get("jd_text_input", ""), height=220, key="jd_text")
        
    with col2:
        st.subheader("📝 Candidate Resume Input")
        resume_file = st.file_uploader("Upload Resume (PDF/DOCX/TXT)", type=["pdf", "docx", "txt"], key="resume_file")
        resume_text = st.text_area("Or paste Resume text", value=st.session_state.get("resume_text_input", ""), height=220, key="resume_text")


    # =========================================================
    # CORE: RUN GAP ANALYSIS
    # =========================================================
    if st.button("Run Gap Analysis", type="primary") or st.session_state.get("demo_mode"):
        st.session_state["demo_mode"] = False
        
        with st.spinner("Analyzing skills with AI... Please wait..."):
            jd_content = parse_uploaded_file(jd_file) or jd_text
            resume_content = parse_uploaded_file(resume_file) or resume_text

            if not jd_content.strip() or not resume_content.strip():
                st.error("Please provide both JD and Resume inputs.")
            else:
                provider = st.session_state.get("provider")
                api_key = st.session_state.get("api_key", "").strip()

                # Step 1: Extract Skills Deterministically
                required_skills_list = extract_skills_deterministic(jd_content)
                resume_skills_list = extract_skills_deterministic(resume_content)
                
                matched = []
                medium = []
                missing = []
                
                gap_report = None
                
                if provider == "gemini" and api_key and st.session_state["use_llm"]:
                    with st.spinner("Running deep AI skill gap analysis..."):
                        llm_report = analyze_skills_with_llm(jd_content, resume_content)
                        if llm_report and "error" not in llm_report:
                            matched = [s for s in llm_report.get("matched_skills", [])]
                            missing_all = [s for s in llm_report.get("missing_skills", [])]
                            additional_skills = [s for s in llm_report.get("additional_skills", [])]
                            
                            priority = llm_report.get("priority", {})
                            strict_missing = [s for s in priority.get("critical", [])]
                            basic_skills = [s for s in priority.get("important", [])]
                            
                            # Ensure medium priority skills that are matched don't bleed into missing
                            combined_missing = sorted([s for s in list(set(strict_missing + missing_all)) if s not in matched])
                                
                            combined_required = sorted(list(set(matched + combined_missing)))
                            
                            # Process confidence
                            raw_confidence = llm_report.get("confidence", {})
                            confidence = {k: v for k, v in raw_confidence.items()} if isinstance(raw_confidence, dict) else {}
                            
                            gap_report = {
                                "required_skills": combined_required,
                                "claimed_skills": sorted(list(set(matched + basic_skills + additional_skills))),
                                "matched_skills": sorted(matched),
                                "missing_skills": combined_missing,
                                "basic_skills": sorted(basic_skills),
                                "strict_missing": sorted(strict_missing),
                                "additional_skills": sorted(additional_skills),
                                "confidence": confidence,
                                "ats_score": llm_report.get("ats_score", None),
                                "suggestions": llm_report.get("suggestions", [])
                            }
                        else:
                            err_msg = llm_report.get("error") if llm_report else "Unknown Error"
                            st.warning(f"AI Analysis failed. Falling back to deterministic matching. Error: {err_msg}")

                if not gap_report:
                    if required_skills_list:
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        # Step 2: Classify Each Skill Deterministically
                        for i, skill in enumerate(required_skills_list):
                            status_text.text(f"Evaluating skill: {skill}...")
                            
                            if skill in resume_skills_list:
                                level = "strong_match"
                            else:
                                level = "missing"
                            
                            if level == "strong_match":
                                matched.append(skill)
                            elif level == "basic_match":
                                medium.append(skill)
                            else:
                                missing.append(skill)
                                
                            progress_bar.progress((i + 1) / len(required_skills_list))
                            
                        status_text.text("Finalizing report...")
                        
                        # Step 3: Identify Additional Skills
                        additional_skills = sorted([s for s in resume_skills_list if s not in required_skills_list])
                                
                        combined_missing = sorted(list(set(medium + missing)))
                        combined_required = sorted(list(set(matched + combined_missing)))
                        
                        gap_report = {
                            "required_skills": combined_required,
                            "claimed_skills": sorted(list(set(matched + medium + additional_skills))),
                            "matched_skills": sorted(matched),
                            "missing_skills": combined_missing,
                            "basic_skills": sorted(medium),
                            "strict_missing": sorted(missing),
                            "additional_skills": sorted(additional_skills),
                        }
                        
                        progress_bar.empty()
                        status_text.empty()
                    
                if gap_report:
                    st.session_state["gap_report"] = gap_report
                    if gap_report["missing_skills"]:
                        st.session_state["assessment"] = start_assessment(gap_report["missing_skills"])
                    else:
                        st.session_state["assessment"] = None

                    st.session_state["proficiency"] = None
                    st.session_state["learning_plan"] = None
                    st.session_state["assessment_answers"] = {s: [] for s in gap_report["missing_skills"]}
                    st.session_state["assessment_scores"] = {s: [] for s in gap_report["missing_skills"]}
                    st.session_state["assessment_feedback"] = {s: [] for s in gap_report["missing_skills"]}
                    st.session_state["parsed_jd_content"] = jd_content
                    st.session_state["parsed_resume_content"] = resume_content
                    
                    st.success("Skill Gap Analysis Completed Successfully.")
                else:
                    st.warning("No specific technical skills could be extracted from the Job Description. Please check your text.")

    # =========================================================
    # CORE: DISPLAY RESULTS
    # =========================================================
    if st.session_state["gap_report"]:
        st.markdown("---")
        st.header("📊 Skill Gap Analysis")
        report = st.session_state["gap_report"]

        g1, g2, g3, g4 = st.columns(4)
        with g1: render_skill_card("✅ Matched Skills", report["matched_skills"], "matched")
        with g2: render_skill_card("🟡 Partial Skills", report.get("basic_skills", []), "partial")
        with g3: render_skill_card("🔴 Missing Skills", report.get("strict_missing", []), "missing")
        with g4: render_skill_card("ℹ️ Additional Skills", report.get("additional_skills", []), "additional")

        st.markdown("---")

        st.markdown("#### 🚨 Missing Skill Priorities")
        if report["missing_skills"]:
            high = report.get("strict_missing", [])
            medium = report.get("basic_skills", [])
            
            if high:
                st.markdown("🔴 **Critical Gaps (Must Have):**")
                st.markdown(f"- {', '.join(high)}")
                
            if medium:
                st.markdown("🟡 **Important Gaps (Needed):**")
                st.markdown(f"- {', '.join(medium)}")
        else:
            st.write("No missing skills detected.")
            
        st.markdown("---")

        st.markdown("#### 📊 Matched Skill Confidence")
        if report["matched_skills"]:
            confidence_dict = report.get("confidence", {})
            for skill in report["matched_skills"]:
                confidence = confidence_dict.get(skill, 85)
                st.write(f"**{skill}**")
                st.progress(confidence / 100)
        else:
            st.write("No matched skills.")
            
        st.markdown("---")

        ats_score = report.get("ats_score")
        if ats_score is None:
            total_weight = 0
            matched_weight = 0
            for req_skill in report.get("required_skills", []):
                skill_key = req_skill.lower()
                weight = SKILL_WEIGHTS.get(skill_key, 1)
                total_weight += weight
                if req_skill in report.get("matched_skills", []):
                    matched_weight += weight
            ats_score = int((matched_weight / total_weight) * 100) if total_weight > 0 else 0
            
        st.markdown(f"### 🎯 ATS Score: {ats_score}%")
        
        predicted_role = report.get("predicted_role")
        if predicted_role:
            st.markdown(f"""
                <div class='role-prediction-banner'>
                    🔥 Killer Insight: <span>Best Suited Role: {predicted_role}</span>
                </div>
            """, unsafe_allow_html=True)

        st.markdown("#### 📝 Resume Improvement Suggestions")
        ai_suggestions = report.get("suggestions", [])
        if ai_suggestions:
            for sug in ai_suggestions:
                st.info(f"💡 {sug}")
        elif report["missing_skills"]:
            for skill in report["missing_skills"]:
                st.warning(f"⚠️ {skill_label(skill)}: Build real-world projects and showcase measurable results to move this out of the gaps list.")
        else:
            st.success("✅ Resume is well aligned. Add more advanced projects to stand out.")

        st.markdown("#### 💡 Candidate Alignment Summary")
        missing_text = ""
        if report.get('missing_skills'):
            missing_text += f"Missing: {', '.join(report['missing_skills'])}. "
        if report.get('basic_skills'):
            missing_text += f"Partial / Needs Improvement: {', '.join(report['basic_skills'])}"
            
        if ats_score < 40:
            st.error(f"Critical gaps in key skills. {missing_text.strip()}")
        elif ats_score < 80 and (report.get('missing_skills') or report.get('basic_skills')):
            st.warning(f"Candidate meets several requirements but needs improvement. {missing_text.strip()}")
        else:
            st.success("Candidate meets all key requirements and is a strong fit.")

        st.markdown("---")

        if report["missing_skills"]:
            st.markdown("#### 🚀 Top 3 Immediate Actions")
            actions_shown = 0
            for skill in report["missing_skills"]:
                if actions_shown >= 3: 
                    break
                sk = skill.lower().strip()
                action_text = ACTION_PLAN_MAP.get(sk, f"Complete a hands-on guided tutorial for {skill}.")
                st.markdown(f"- {action_text}")
                actions_shown += 1
            st.markdown("---")

        st.markdown("#### 🗺️ Adaptive Learning Roadmap")
        
        total_weeks = 0
        missing_skills_list = report.get("missing_skills", [])
        
        for skill in missing_skills_list:
            sk = skill.lower().strip()
            if skill.title() in report.get("basic_skills", []):
                lvl = "Intermediate"
            else:
                lvl = "Beginner"
                
            time_info = ADAPTIVE_TIME_MAP.get(sk, {"Beginner": "3-4 weeks", "Intermediate": "1-2 weeks", "weeks_val": {"Beginner": 3.5, "Intermediate": 1.5}})
            total_weeks += time_info["weeks_val"].get(lvl, 3.5)

        if missing_skills_list:
            min_w = max(1, int(total_weeks * 0.5))
            max_w = max(min_w + 1, int(total_weeks * 0.7))
            st.info(f"⏳ **Estimated Learning Duration: {min_w}–{max_w} weeks**")

        if missing_skills_list:
            st.markdown("##### 📅 Weekly Learning Timeline")
            def get_diff_score(diff):
                return {"Easy": 1, "Medium": 2, "Hard": 3}.get(diff, 2)
            
            sorted_missing = sorted(missing_skills_list, key=lambda s: get_diff_score(DIFFICULTY_MAP.get(s.lower().strip(), "Medium")))
            
            current_week = 1
            for skill in sorted_missing:
                sk = skill.lower().strip()
                if skill.title() in report.get("basic_skills", []):
                    lvl = "Intermediate"
                else:
                    lvl = "Beginner"
                    
                time_info = ADAPTIVE_TIME_MAP.get(sk, {"weeks_val": {"Beginner": 3, "Intermediate": 1}})
                weeks = time_info["weeks_val"].get(lvl, 3)
                weeks = max(1, int(round(weeks)))
                
                end_week = current_week + weeks - 1
                if current_week == end_week:
                    week_str = f"Week {current_week}"
                else:
                    week_str = f"Week {current_week}–{end_week}"
                
                st.markdown(f"- **{week_str}** → {skill.title()}")
                current_week = end_week + 1
            st.write("")

        seen_skills = set()
        for skill in missing_skills_list:
            skill_name = skill.title()
            skill_key = skill.lower().strip()
            
            if skill_key in seen_skills: 
                continue
            seen_skills.add(skill_key)

            if skill_name in report.get("basic_skills", []):
                c_level = "Intermediate"
                level_msg = "You already have some foundation. Focus on real-world projects to improve."
            else:
                c_level = "Beginner"
                level_msg = "You are starting from basics. Focus on fundamentals before advanced projects."

            time_info = ADAPTIVE_TIME_MAP.get(skill_key, {"Beginner": "3-4 weeks", "Intermediate": "1-2 weeks"})
            time_str = time_info.get(c_level, "3-4 weeks")
            difficulty = DIFFICULTY_MAP.get(skill_key, "Medium")

            project_idea = ACTION_PLAN_MAP.get(skill_key, f"Build an end-to-end {skill_name} project.")
            specific_advice = CAREER_ADVICE_MAP.get(skill_key, f"Review official documentation for {skill_name} and build functional examples.")
            real_link = REAL_LINKS.get(skill_key, f"https://www.google.com/search?q=learn+{skill_key.replace(' ', '+')}")
            link_label = f"📚 Learn {skill_name}"
            
            st.markdown(f"**📍 {skill_name}**")
            st.markdown(f"- 🔥 **Difficulty:** {difficulty}")
            st.markdown(f"- ⏱ **Time:** {time_str}")
            st.markdown(f"- 📚 **Resource:** [{link_label}]({real_link})")
            st.markdown(f"- 💡 **Project:** {project_idea}")
            st.markdown(f"- 💬 **Advice:** {level_msg} {specific_advice}")
            st.write("")

        if not missing_skills_list:
            st.markdown("- No learning roadmap is needed because the candidate already matches all requirements.")

        st.markdown("---")

        st.markdown("### 🧭 Dynamic Career Advice")
        if report["missing_skills"]:
            for skill in report["missing_skills"]:
                sl = skill.lower()
                advice = CAREER_ADVICE_MAP.get(sl, f"Review official documentation for {skill} and build small functional examples.")
                st.info(f"Since **{skill}** is a gap area: {advice}")
        else:
            st.success("You have no missing core skills! Focus on advanced interview prep.")

        st.markdown("---")

        st.markdown("### 🚦 Final Readiness")
        if ats_score >= 80:
            st.success("✅ **Ready for this role!**")
        elif ats_score >= 50:
            st.warning("⚠️ **Almost ready – improve key skills.**")
        else:
            st.error("🚫 **Not ready – major skill gaps. Focus on core skills.**")

        st.markdown("---")
        
        pdf_bytes = generate_pdf_report(report, ats_score)
        st.download_button(label="📥 Download Assessment PDF", data=pdf_bytes, file_name="Skill_Gap_Report.pdf", mime="application/pdf")

    # ==================================================
    # DEEP ASSESSMENT MODE (CHATBOT)
    # ==================================================
    if st.session_state["gap_report"] and st.session_state["gap_report"]["missing_skills"]:
        st.markdown("---")
        if not st.session_state.get("run_deep_assess", False):
            if st.button("🤖 Run Deep Assessment", type="primary"):
                if not st.session_state.get("api_key"):
                    st.error("API Key required to run the Deep Assessment.")
                else:
                    st.session_state["run_deep_assess"] = True
                    st.session_state["assessment"] = start_assessment(st.session_state["gap_report"]["missing_skills"])
                    st.rerun()

    if st.session_state.get("run_deep_assess", False) and st.session_state["assessment"]:
        st.markdown("---")
        st.header("💬 Deep Assessment Mode")
        assessment_state = st.session_state["assessment"]

        with st.container(border=True):
            for msg in assessment_state["history"]:
                with st.chat_message(msg["role"]):
                    st.write(msg["content"])

            if not assessment_state["completed"]:
                user_answer = st.text_area(
                    "Answer the current technical question here...",
                    key="answer_input"
                )

                if st.button("Evaluate Answer"):
                    answer_text = st.session_state.get("answer_input", "").strip()

                    if not answer_text:
                        st.warning("⚠️ Please enter an answer before evaluating.")
                    elif len(answer_text.split()) < 5:
                        st.error("🔴 Your answer is too short to evaluate. Please provide more detail.")
                    else:
                        with st.spinner("Analyzing your answer with AI..."):
                            current_skill = assessment_state["queue"][assessment_state["current_skill_idx"]]
                            current_q = assessment_state["questions_map"][current_skill][assessment_state["current_question_idx"]]
                            
                            prompt = f"""
You are an expert technical evaluator.

Evaluate the candidate's answer for the skill: {current_skill}.
Question asked: "{current_q}"
Candidate's Answer: "{answer_text}"

Evaluate based on the following criteria:
1. Project clarity (Is the project clearly explained?)
2. Tools & technologies (Python, libraries like NumPy, Pandas, Scikit-learn, TensorFlow, etc.)
3. Algorithm understanding (Did they mention ML models like regression, classification, etc.?)
4. Problem-solving (Did they explain challenges faced and how they solved them?)
5. Results & impact (Did they mention accuracy, outcome, or improvements?)

Scoring rules:
- Give a score out of 10
- 0–3 → Poor (no real project or vague answer)
- 4–6 → متوسط (basic understanding, limited details)
- 7–8 → Good (clear project, tools, some depth)
- 9–10 → Excellent (detailed, structured, strong technical clarity)

Return STRICT JSON:
{{
  "score": X, 
  "level": "Strong" | "متوسط" | "Weak",
  "feedback_strengths": ["point1", "point2"],
  "feedback_missing": ["point1", "point2"]
}}
"""
                            ai_response = ai_call(prompt)
                            
                            match = re.search(r"\{.*\}", str(ai_response), re.DOTALL)
                            if match:
                                json_text = match.group(0)
                                try:
                                    result = json.loads(json_text)
                                    score = int(result.get("score", 5)) * 10
                                    level = str(result.get("level", "متوسط"))
                                    strengths = result.get("feedback_strengths", [])
                                    missing = result.get("feedback_missing", [])
                                    
                                    feedback = "**Strengths:**\n" + "\n".join([f"- {s}" for s in strengths]) + "\n\n**Missing Areas:**\n" + "\n".join([f"- {m}" for m in missing])
                                    
                                    if not (0 <= score <= 100):
                                        score = max(0, min(100, score))
                                except Exception:
                                    score = 50
                                    level = "Partial"
                                    feedback = "Basic understanding detected. Needs more practical experience."
                            else:
                                score = 50
                                level = "Partial"
                                feedback = "Basic understanding detected. Needs more practical experience."

                            # Record response
                            assessment_state["history"].append({"role": "user", "content": answer_text})
                            
                            log_msg = f"**{level} Match**\n\n{feedback}\n\n**Score: {score}%**"
                            assessment_state["history"].append({"role": "assistant", "content": log_msg})
                            
                            # Store Data
                            if current_skill not in st.session_state["assessment_answers"]:
                                st.session_state["assessment_answers"][current_skill] = []
                                st.session_state["assessment_scores"][current_skill] = []
                                st.session_state["assessment_feedback"][current_skill] = []

                            st.session_state["assessment_answers"][current_skill].append(answer_text)
                            st.session_state["assessment_scores"][current_skill].append(score)
                            assessment_state["scores"][current_skill].append(score)
                            st.session_state["assessment_feedback"][current_skill].append(feedback)

                            # Move to Next Question or Skill
                            assessment_state["current_question_idx"] += 1
                            if assessment_state["current_question_idx"] < 2:
                                next_q_text = assessment_state["questions_map"][current_skill][assessment_state["current_question_idx"]]
                                assessment_state["history"].append({
                                    "role": "assistant", 
                                    "content": f"Thanks. Next question on {current_skill}:\n\n{next_q_text}"
                                })
                            else:
                                # Completed both questions for this skill. Evaluate average and UPGRADE if Strong.
                                avg_score = sum(assessment_state["scores"][current_skill]) / len(assessment_state["scores"][current_skill])
                                final_level = score_to_level(avg_score)
                                
                                if final_level == "Strong":
                                    assessment_state["history"].append({
                                        "role": "assistant", 
                                        "content": f"🎉 Excellent! You scored an average of {avg_score}%. **{current_skill}** has been upgraded to **Matched Skills**!"
                                    })
                                    # Dynamically update the Gap Report
                                    if current_skill in st.session_state["gap_report"]["missing_skills"]:
                                        st.session_state["gap_report"]["missing_skills"].remove(current_skill)
                                    if current_skill not in st.session_state["gap_report"]["matched_skills"]:
                                        st.session_state["gap_report"]["matched_skills"].append(current_skill)
                                        st.session_state["gap_report"]["matched_skills"].sort()
                                else:
                                    assessment_state["history"].append({
                                        "role": "assistant", 
                                        "content": f"📝 You scored an average of {avg_score}%. **{current_skill}** remains marked as a **{final_level}** skill."
                                    })

                                assessment_state["current_skill_idx"] += 1
                                assessment_state["current_question_idx"] = 0
                                
                                if assessment_state["current_skill_idx"] >= len(assessment_state["queue"]):
                                    assessment_state["completed"] = True
                                    assessment_state["history"].append({
                                        "role": "assistant", 
                                        "content": "✅ **Deep Assessment Complete!** Scroll up to view your newly updated ATS score and Skill Matches."
                                    })
                                    st.session_state["proficiency"] = compute_final_proficiency(assessment_state["scores"])
                                else:
                                    next_skill = assessment_state["queue"][assessment_state["current_skill_idx"]]
                                    next_q_text = assessment_state["questions_map"][next_skill][0]
                                    assessment_state["history"].append({
                                        "role": "assistant", 
                                        "content": f"Great. Moving to the next skill: **{next_skill}**.\n\n{next_q_text}"
                                    })

                        time.sleep(1.0)
                        st.rerun()

            else:
                st.success("Assessment complete. UI has been updated.")

    # ==================================================
    # ENHANCED LEARNING PLAN
    # ==================================================
    if st.session_state["gap_report"] and st.session_state["proficiency"] is not None:
        st.markdown("---")
        st.header("🗺️ 4-Week Detailed Learning Plan")

        if st.session_state["learning_plan"] is None:
            with st.spinner("Generating personalized learning plan..."):
                st.session_state["learning_plan"] = generate_plan(
                    st.session_state["gap_report"],
                    st.session_state["proficiency"],
                )

        if st.button("Regenerate Learning Plan"):
            with st.spinner("Generating personalized learning plan..."):
                st.session_state["learning_plan"] = generate_plan(
                    st.session_state["gap_report"],
                    st.session_state["proficiency"],
                )

        if st.session_state["learning_plan"]:
            for idx, module in enumerate(st.session_state["learning_plan"], start=1):
                skill_name = module['skill'].title()
                skill_key = skill_name.lower()
                
                st.markdown(f"### Module {idx}: {skill_name} ({module['current_level']})")
                
                real_link = REAL_LINKS.get(skill_key, f"https://www.google.com/search?q=learn+{skill_key.replace(' ', '+')}")
                link_label = f"📚 Learn {skill_name}"
                
                st.markdown(
                    f"**Current Score:** {module['current_proficiency']}/100 ({module['percentage']}%)  \n"
                    f"**Progression Path:** {module['progression_path']}  \n"
                    f"**Estimated Time-to-Competency:** {module['time_to_competency']}  \n"
                )
                
                st.markdown(f"- **Resource:** [{link_label}]({real_link})")

                with st.expander(f"View Detailed 4-Week Roadmap for {skill_name}", expanded=False):
                    for week_item in module["weekly_roadmap"]:
                        st.markdown(
                            f"**{week_item['week']} ({week_item['stage']})** \n"
                            f"- Focus: {week_item['focus']}  \n"
                            f"- Outcome: {week_item['outcome']}"
                        )

if __name__ == "__main__":
    main()