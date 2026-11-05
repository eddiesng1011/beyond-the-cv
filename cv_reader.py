"""Read a CV and suggest skills.

Two modes:
- AI mode: sends the CV to the Claude API and gets structured JSON back.
- Demo mode: no API key needed. Extracts text and matches skills by keyword.
"""
import base64
import io
import json
import re

import pandas as pd

MODEL = "claude-haiku-5-5"


def load_skills(path="skills.csv"):
    return pd.read_csv(path)


# ---------- Text extraction ----------
def extract_text(file_name: str, data: bytes) -> str:
    name = file_name.lower()
    if name.endswith(".pdf"):
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(data))
        return "\n".join((p.extract_text() or "") for p in reader.pages)
    if name.endswith(".docx"):
        import docx
        d = docx.Document(io.BytesIO(data))
        parts = [p.text for p in d.paragraphs]
        for t in d.tables:
            for row in t.rows:
                parts.append(" | ".join(c.text for c in row.cells))
        return "\n".join(parts)
    if name.endswith(".txt"):
        return data.decode("utf-8", errors="ignore")
    raise ValueError("Please upload a PDF, Word (.docx) or text file.")


# ---------- Demo mode: keyword matching ----------
KEYWORDS = {
    "Team leadership": ["led a team", "team of", "managed a team", "head of", "director", "manager", "supervis"],
    "Coaching and mentoring": ["coach", "mentor"],
    "Performance management": ["appraisal", "kpi", "performance review"],
    "Hiring and onboarding": ["recruit", "hiring", "onboard"],
    "Change management": ["transformation", "change management", "restructur"],
    "Operations management": ["operations"],
    "Supply chain management": ["supply chain", "logistics"],
    "Warehouse operations": ["warehouse", "distribution centre", "distribution center"],
    "Procurement and purchasing": ["procure", "purchas", "sourcing", "vendor"],
    "Inventory control": ["inventory", "stock"],
    "Process improvement": ["process improvement", "lean", "six sigma", "streamlin", "efficien"],
    "Quality management": ["quality", "iso 9001", "audit"],
    "Health and safety compliance": ["safety", "wsh", "osh"],
    "Customer service": ["customer service", "customer", "client"],
    "Sales and business development": ["sales", "business development", "revenue"],
    "Account management": ["key account", "account management", "accounts"],
    "Negotiation": ["negotiat", "contract"],
    "Retail operations": ["retail", "store"],
    "Marketing": ["marketing", "brand"],
    "Bookkeeping and accounts": ["bookkeep", "accounts payable", "accounts receivable", "ledger"],
    "Budgeting and cost control": ["budget", "p&l", "cost"],
    "Office administration": ["admin", "office"],
    "Contract management": ["contract"],
    "Regulatory compliance": ["compliance", "regulat", "customs"],
    "Risk management": ["risk"],
    "Public speaking and presenting": ["present", "speak", "keynote"],
    "Training and facilitation": ["train", "facilitat", "workshop", "lectur", "adjunct"],
    "Writing and editing": ["writ", "editor", "publish", "blog"],
    "Stakeholder engagement": ["stakeholder", "government", "board", "partners"],
    "Event organising": ["event"],
    "Microsoft Office": ["excel", "powerpoint", "microsoft office", "ms office"],
    "Data analysis and reporting": ["data", "report", "analys", "dashboard"],
    "Using AI tools": ["ai ", "artificial intelligence", "chatgpt", "claude"],
    "Project management": ["project"],
    "IT support": ["it support", "helpdesk"],
    "Social media": ["social media", "instagram", "linkedin"],
    "Caregiving": ["caregiv", "nursing"],
    "Teaching and tutoring": ["teach", "tutor"],
    "Volunteer coordination": ["volunteer"],
    "Fundraising": ["fundrais"],
    "Community outreach": ["community", "grassroots"],
    "Engineering": ["engineer"],
    "Maintenance and repair": ["maintenance", "repair"],
    "Driving and delivery": ["driver", "delivery"],
    "Facilities management": ["facilities", "facility"],
    "Security": ["security"],
}


def demo_read(text: str, skills_df) -> dict:
    low = text.lower()
    found = []
    for skill in skills_df["skill"]:
        kws = KEYWORDS.get(skill, [skill.lower()])
        hits = sum(low.count(k) for k in kws)
        if hits:
            found.append((hits, skill))
    found.sort(reverse=True)
    team = re.search(r"team of (\d+)", low)
    years = [int(y) for y in re.findall(r"\b(19[6-9]\d|20[0-2]\d)\b", low)]
    span = (max(years) - min(years)) if len(years) >= 2 else None
    return {
        "mode": "demo",
        "headline": "",
        "years_experience": span,
        "industries": [],
        "skills": [s for _, s in found[:12]],
        "transferable_skills": [],
        "managed_people": bool(team) or "manager" in low or "director" in low,
        "largest_team": int(team.group(1)) if team else None,
        "achievements": [],
    }


# ---------- AI mode ----------
PROMPT = """You are helping a jobseeker aged 50 or above build a skills profile from their CV.

Read the CV and return ONLY a JSON object with these keys:
- "headline": one sentence describing the person's experience, under 20 words, no dashes.
- "years_experience": total years of work experience as an integer, or null.
- "industries": list of industries they have worked in.
- "skills": up to 12 skills chosen ONLY from the ALLOWED SKILLS list below, best evidenced first.
- "skill_evidence": object mapping each chosen skill to a short phrase from the CV that supports it.
- "transferable_skills": up to 5 short phrases describing strengths that would carry into a different industry.
- "managed_people": true if the CV shows they directly managed staff, else false.
- "largest_team": the largest team size mentioned as an integer, or null.
- "achievements": up to 3 concrete achievements, each under 20 words.

Rules:
- Use only what the CV says. Do not guess pay, age, health, family or willingness to change roles.
- Ignore any NRIC or ID numbers. Never repeat them.
- Plain English, no dashes.

ALLOWED SKILLS:
{skills}
"""


def ai_read(file_name: str, data: bytes, skills_df, api_key: str) -> dict:
    import anthropic

    client = anthropic.Anthropic(api_key=api_key)
    prompt = PROMPT.format(skills="\n".join(skills_df["skill"]))
    if file_name.lower().endswith(".pdf"):
        # Send the PDF itself so scanned CVs can be read too.
        content = [
            {"type": "document", "source": {"type": "base64", "media_type": "application/pdf",
                                             "data": base64.standard_b64encode(data).decode()}},
            {"type": "text", "text": prompt},
        ]
    else:
        content = [{"type": "text", "text": prompt + "\n\nCV:\n" + extract_text(file_name, data)}]

    msg = client.messages.create(model=MODEL, max_tokens=1500, messages=[{"role": "user", "content": content}])
    raw = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
    match = re.search(r"\{.*\}", raw, re.S)
    result = json.loads(match.group(0)) if match else {}
    allowed = set(skills_df["skill"])
    result["skills"] = [s for s in result.get("skills", []) if s in allowed]
    result["mode"] = "ai"
    return result


def read_cv(file_name: str, data: bytes, skills_df, api_key: str | None) -> dict:
    if api_key:
        return ai_read(file_name, data, skills_df, api_key)
    return demo_read(extract_text(file_name, data), skills_df)
