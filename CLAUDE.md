# Beyond the CV

Purpose: help Singaporeans aged 50+ build a one-page profile that shows what their CV does not.
Phase 1 is applicant-side only. No job pulling, matching or contact with hirers.

Stack: Python 3.11, Streamlit, Claude API (claude-haiku-5-5), pandas, pypdf, python-docx.

Rules:
- AI only extracts what is in the CV: skills (from skills.csv only), headline, transferable strengths, achievements.
- AI never guesses step-back willingness, pay, availability, health, age or family. The senior answers those.
- Never store or repeat NRIC numbers. Keep profile answers, not the CV file.
- Demo mode (no API key) must always keep working.
- Large text and plain English. Users may be new to apps.
- House style for any text shown: no em or en dashes, short sentences.
