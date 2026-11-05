# Beyond the CV: Prototype 1

A senior uploads a CV. The app suggests skills from a fixed list. The senior confirms them, then answers questions a CV never asks. The app shows a profile that leads with those answers.

## Run it on your Mac

1. Install Python 3.11 or later from python.org if `python3 --version` shows nothing.
2. Open Terminal in this folder and run:

```
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

3. Your browser opens at http://localhost:8501.

## Demo mode or AI mode

- **Without an API key** the app runs in demo mode. It matches skills by keywords. Good enough for Thursday.
- **With a key** it sends the CV to Claude (model `claude-haiku-5-5`) and gets skills, a headline, transferable strengths and achievements. PDFs go in whole, so scanned CVs work.
- To add a key: copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and paste your key from the Claude Console. Set a monthly spend limit in the Console first.
- The AI mode has not been tested yet, because no key was available when it was built. Test it with the sample CV before showing anyone.

## Put it online (free)

1. Push this folder to a private GitHub repository. `secrets.toml` is excluded by `.gitignore`.
2. At share.streamlit.io, choose "Create app" and pick the repository and `app.py`.
3. In the app's Settings, under Secrets, paste the `ANTHROPIC_API_KEY` line.

## Files

| File | What it does |
|---|---|
| `app.py` | The five screens: welcome and consent, CV upload, skills, beyond-the-CV questions, profile |
| `cv_reader.py` | Reads PDF, Word or text CVs. AI mode and demo mode |
| `skills.csv` | The drop-down list: 50 skills in 8 themes. Edit freely |
| `samples/sample_cv.docx` | A fictional CV for demos |

## Next, for Prototype 2 (12 Nov)

- One-page PDF profile to download and share
- Save profiles (with consent) so testers can come back
- Align `skills.csv` with SkillsFuture Skills Framework names
