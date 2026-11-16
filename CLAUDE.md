# Beyond the CV

Purpose: help Singaporeans aged 50+ build a one-page profile that shows what their CV does not.
Phase 1 is applicant-side only. No job pulling, matching or contact with hirers.

Stack: Python 3.11+, Streamlit, Claude API (claude-haiku-5-5), pandas, pypdf, python-docx, reportlab.
Question wording lives in questions.py. Profile wording and PDF in profile_builder.py.

Rules:
- AI only extracts what is in the CV: skills (from skills.csv only), headline, transferable strengths, achievements.
- AI never guesses step-back willingness, pay, availability, health, age or family. The senior answers those.
- Never store or repeat NRIC numbers. Keep profile answers, not the CV file.
- Demo mode (no API key) must always keep working.
- Large text and plain English. Users may be new to apps.
- House style for any text shown: no em or en dashes, short sentences.
- Answers must survive Back and Next within a visit. Nothing is stored after the page closes.
- Multi-choice questions use tick boxes, never a dropdown with Select all.
- The profile leads with "What my CV does not tell you". Fit comes in Phase 2 with a job description.
