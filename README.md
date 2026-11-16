# Beyond the CV: Prototype 2

A senior uploads a CV or LinkedIn PDF. The app suggests skills from a fixed list. The senior confirms them, then answers 14 categories of questions a CV never asks, over 4 pages. The app produces a one-page PDF profile that leads with those answers.

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

## Run it on Windows

1. Install Python 3.11 or later from python.org. On the first installer screen, tick "Add python.exe to PATH".
2. Unzip this folder, then open PowerShell in it (Shift + right-click inside the folder, "Open PowerShell window here").
3. Run:

```
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

If PowerShell refuses to run the activate script, run this once, then try again:
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

## Next time

Open Terminal or PowerShell in the folder, activate the environment again (the second line above), then run `streamlit run app.py`. Press Control + C to stop it.

## Demo mode or AI mode

- **Without an API key** the app runs in demo mode. It matches skills by keywords. Good enough for Thursday.
- **With a key** it sends the CV to Claude (model `claude-haiku-5-5`) and gets skills, a headline, transferable strengths and achievements. PDFs go in whole, so scanned CVs work.
- To add a key: copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and paste your key from the Claude Console. Set a monthly spend limit in the Console first.
- The AI mode has not been tested yet, because no key was available when it was built. Test it with the sample CV before showing anyone.

## Put it online (free)

1. Push this folder to a private GitHub repository. `secrets.toml` is excluded by `.gitignore`.
2. At share.streamlit.io, choose "Create app" and pick the repository and `app.py`.
3. In the app's Settings, under Secrets, paste the `ANTHROPIC_API_KEY` line.

## Settings (Streamlit app settings, under Secrets)

```
ANTHROPIC_API_KEY = "sk-ant-..."     # switches on AI reading
HOST_NAME = "the Beyond the CV project team"   # who the consent screen names
CONTACT_EMAIL = "someone@example.org"          # who users contact about their data
```
All three are optional. Without them the app runs in demo mode with the default host name.

## Files

| File | What it does |
|---|---|
| `app.py` | The screens: consent, CV upload, skills, 4 question pages, profile and PDF |
| `questions.py` | All question wording and options. Edit here to change a question |
| `profile_builder.py` | Turns answers into profile sentences and the one-page PDF |
| `cv_reader.py` | Reads PDF, Word or text CVs. AI mode and demo mode |
| `skills.csv` | The skills list: 50 skills in 8 themes |
| `samples/sample_cv.docx` | A fictional CV for demos |

## Next, after Prototype 2

- AI-written narrative profile instead of the template wording
- Optional job description upload, to show fit (Phase 2)
- Save and return later (needs a database and login)
