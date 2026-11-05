"""Beyond the CV: Prototype 1.

Flow: consent -> upload CV -> confirm skills -> beyond-the-CV questions -> profile preview.
Runs in demo mode (keyword matching) when no ANTHROPIC_API_KEY is set.
"""
import os
from pathlib import Path

import streamlit as st

from cv_reader import load_skills, read_cv

HERE = Path(__file__).parent
st.set_page_config(page_title="Beyond the CV", page_icon=":briefcase:", layout="centered")

# Larger, calmer text for older users.
st.markdown("""
<style>
html, body, [class*="css"], .stMarkdown p, label, .stRadio label, .stCheckbox label { font-size: 18px !important; }
h1 { font-size: 2.2rem !important; }
.stButton button { font-size: 18px; padding: 0.5rem 1.4rem; }
[data-testid="InputInstructions"] { display: none; }
</style>
""", unsafe_allow_html=True)


def get_api_key():
    try:
        key = st.secrets.get("ANTHROPIC_API_KEY")
    except Exception:
        key = None
    return key or os.environ.get("ANTHROPIC_API_KEY")


SKILLS = load_skills(HERE / "skills.csv")
API_KEY = get_api_key()
STEPS = ["Welcome", "Your CV", "Your skills", "Beyond the CV", "Your profile"]

ss = st.session_state
ss.setdefault("step", 0)
ss.setdefault("cv", None)
ss.setdefault("answers", {})


def go(n):
    ss.step = n


def scroll_to_top():
    """Streamlit keeps the scroll position between screens. Reset it when the step changes.
    The page can keep growing for a moment after it loads, so keep resetting for about 1.5 seconds."""
    st.iframe(
        f"""<script>
        // step {ss.step}, run {ss._scroll_runs}
        const doc = window.parent.document;
        function toTop() {{
          const targets = [doc.querySelector('[data-testid="stMain"]'),
                           doc.querySelector('[data-testid="stAppViewContainer"]'),
                           doc.querySelector('section.main'),
                           doc.scrollingElement, doc.documentElement, doc.body];
          targets.forEach(t => {{ if (t) t.scrollTop = 0; }});
          window.parent.scrollTo(0, 0);
        }}
        if (doc.activeElement) doc.activeElement.blur();
        toTop();
        let n = 0;
        const timer = setInterval(() => {{ toTop(); if (++n >= 15) clearInterval(timer); }}, 100);
        </script>""",
        height=1,
    )


ss.setdefault("_last_step", ss.step)
ss.setdefault("_scroll_runs", 0)
if ss._last_step != ss.step:
    ss._last_step = ss.step
    ss._scroll_runs += 1
    scroll_to_top()

# ---------- Header ----------
st.title("Beyond the CV")
st.caption(f"Step {ss.step + 1} of {len(STEPS)}: {STEPS[ss.step]}")
st.progress((ss.step + 1) / len(STEPS))
if not API_KEY:
    st.info("Demo mode: skills are suggested by keyword matching. Add an API key for AI reading.")

# ---------- Step 0: welcome and consent ----------
if ss.step == 0:
    st.markdown(
        "Your CV shows where you have been. It rarely shows what you would accept, "
        "or what you want next. This tool helps you say both, in one page."
    )
    st.markdown("**How it works**\n\n1. Upload your CV.\n2. We suggest skills from it. You confirm them.\n"
                "3. You answer a few questions a CV never asks.\n4. You get a one-page profile.")
    st.markdown("**Before you start**")
    st.markdown(
        "- Your CV is read by an AI service to suggest skills.\n"
        "- Please remove your NRIC number from your CV first.\n"
        "- We keep your profile answers, not your CV file.\n"
        "- You can ask us to delete your profile at any time."
    )
    agree = st.checkbox("I understand and agree to continue")
    st.button("Start", disabled=not agree, on_click=go, args=(1,), type="primary")

# ---------- Step 1: upload ----------
elif ss.step == 1:
    st.markdown("Upload your CV as a PDF or Word file. A scanned PDF is fine.")
    up = st.file_uploader("Your CV", type=["pdf", "docx", "txt"])
    sample = HERE / "samples" / "sample_cv.docx"
    use_sample = st.checkbox("No CV handy? Use a sample CV (fictional person)") if sample.exists() else False

    if st.button("Read my CV", type="primary", disabled=not (up or use_sample)):
        name, data = (up.name, up.getvalue()) if up else (sample.name, sample.read_bytes())
        with st.spinner("Reading your CV..."):
            try:
                ss.cv = read_cv(name, data, SKILLS, API_KEY)
                ss.chosen_skills = list(ss.cv.get("skills", []))
                go(2)
                st.rerun()
            except Exception as e:  # show a friendly message, keep the detail for us
                st.error("Sorry, we could not read that file. Please try a PDF or Word version.")
                st.caption(f"Detail: {e}")
    st.button("Back", on_click=go, args=(0,))

# ---------- Step 2: confirm skills ----------
elif ss.step == 2:
    cv = ss.cv or {}
    if cv.get("headline"):
        st.markdown(f"**In one line:** {cv['headline']}")
    st.markdown("We found these skills in your CV. Untick any that are wrong. Add any we missed.")

    chosen = []
    for theme, group in SKILLS.groupby("theme", sort=False):
        options = list(group["skill"])
        pre = [s for s in options if s in ss.get("chosen_skills", [])]
        with st.expander(f"{theme} ({len(pre)} selected)", expanded=bool(pre)):
            chosen += st.multiselect(theme, options, default=pre, key=f"ms_{theme}", label_visibility="collapsed")
    other = st.text_input("Other skills not in the list (separate with commas)", value=ss.answers.get("other_skills", ""))

    if cv.get("transferable_skills"):
        st.markdown("**Strengths that could carry into another industry**")
        for t in cv["transferable_skills"]:
            st.markdown(f"- {t}")

    c1, c2 = st.columns(2)
    c1.button("Back", on_click=go, args=(1,))
    if c2.button("Next", type="primary"):
        ss.chosen_skills = chosen
        ss.answers["other_skills"] = other
        go(3)
        st.rerun()

# ---------- Step 3: beyond the CV ----------
elif ss.step == 3:
    cv, a = ss.cv or {}, ss.answers
    st.markdown("These questions are what a CV never asks. There are no wrong answers.")

    st.subheader("1. Taking a step back")
    if cv.get("managed_people"):
        team = f" of up to {cv['largest_team']} people" if cv.get("largest_team") else ""
        st.markdown(f"Your CV shows you have led teams{team}.")
    a["step_back"] = st.radio("Would you take a role at a lower level than your last one?",
                              ["Yes, happily", "Yes, for the right role", "Prefer not to"], index=None, key="q_step")
    a["step_back_why"] = st.text_input("In a sentence, why? (optional)", value=a.get("step_back_why", ""), key="q_step_why")

    st.subheader("2. Leading people or doing the work")
    a["people_or_tasks"] = st.radio("Which suits you now?",
                                    ["I want to lead a team", "I prefer to do the work myself", "Either is fine"],
                                    index=None, key="q_people")

    st.subheader("3. Pay")
    a["pay_floor"] = st.number_input("The lowest monthly pay you would accept for the right role (S$)",
                                     min_value=0, step=100, value=a.get("pay_floor", 0), key="q_pay")
    a["pay_flexible"] = st.checkbox("I am flexible on pay for meaningful work", value=a.get("pay_flexible", False), key="q_payflex")

    st.subheader("4. Time")
    a["days"] = st.radio("How much do you want to work?",
                         ["Full time", "3 to 4 days a week", "1 to 2 days a week", "Project by project"],
                         index=None, key="q_days")

    st.subheader("5. Switching industry")
    a["open_industries"] = st.radio("Are you open to a different industry?",
                                    ["Yes", "Maybe, if the role fits", "No, I want to stay in my field"],
                                    index=None, key="q_ind")

    st.subheader("6. Life outside work")
    a["outside"] = st.text_area("Hobbies, volunteering or community roles that show what you can do",
                                value=a.get("outside", ""), key="q_out",
                                placeholder="e.g. I run a residents' committee, coach youth football, mend watches")

    st.subheader("7. Trying new things")
    a["ai_use"] = st.radio("Have you used AI tools such as ChatGPT, Claude, Copilot or Gemini?",
                           ["Yes, I use them regularly", "Yes, I have tried them a few times",
                            "Not yet, but I would like to learn", "Not for me"],
                           index=None, key="q_ai")
    if a.get("ai_use") in ("Yes, I use them regularly", "Yes, I have tried them a few times"):
        a["ai_example"] = st.text_input("Give one example of what you used AI for",
                                        value=a.get("ai_example", ""), key="q_ai_ex",
                                        placeholder="e.g. drafting emails, planning a trip, summarising a report")
    else:
        a["ai_example"] = ""

    st.subheader("8. What matters now")
    a["motives"] = st.multiselect("Pick up to three",
                                  ["Income", "Purpose", "Learning something new", "Staying active",
                                   "Being with people", "Flexibility", "Passing on what I know"],
                                  max_selections=3, key="q_mot")
    a["purpose"] = st.text_input("In one sentence, what do you want your next role to give you?",
                                 value=a.get("purpose", ""), key="q_purpose")

    required = ["step_back", "people_or_tasks", "days", "open_industries"]
    missing = [k for k in required if not a.get(k)]
    c1, c2 = st.columns(2)
    c1.button("Back", on_click=go, args=(2,))
    if c2.button("See my profile", type="primary", disabled=bool(missing)):
        go(4)
        st.rerun()
    if missing:
        st.caption("Please answer questions 1, 2, 4 and 5 to continue.")

# ---------- Step 4: profile preview ----------
elif ss.step == 4:
    cv, a = ss.cv or {}, ss.answers
    skills = ss.get("chosen_skills", []) + [s.strip() for s in a.get("other_skills", "").split(",") if s.strip()]
    pay = f"From S${a['pay_floor']:,} a month" if a.get("pay_floor") else "Open to discuss"
    if a.get("pay_flexible"):
        pay += ", flexible for meaningful work"

    st.markdown("### What my CV does not tell you")
    st.markdown(f"- **Stepping back:** {a.get('step_back')}" + (f". {a['step_back_why']}" if a.get("step_back_why") else ""))
    st.markdown(f"- **Leading or doing:** {a.get('people_or_tasks')}")
    st.markdown(f"- **Availability:** {a.get('days')}")
    st.markdown(f"- **Pay:** {pay}")
    st.markdown(f"- **New industries:** {a.get('open_industries')}")
    if a.get("motives"):
        st.markdown(f"- **What matters now:** {', '.join(a['motives'])}")
    if a.get("purpose"):
        st.markdown(f"- **In my words:** {a['purpose']}")
    if a.get("outside"):
        st.markdown(f"- **Outside work:** {a['outside']}")
    ai_line = {"Yes, I use them regularly": "Uses AI tools regularly",
               "Yes, I have tried them a few times": "Has tried AI tools",
               "Not yet, but I would like to learn": "Keen to learn AI tools"}.get(a.get("ai_use"))
    if ai_line:
        st.markdown(f"- **New tools and AI:** {ai_line}" + (f". For example: {a['ai_example']}" if a.get("ai_example") else ""))

    st.markdown("### What I bring")
    if cv.get("headline"):
        st.markdown(cv["headline"])
    if cv.get("transferable_skills"):
        st.markdown("**Across industries:** " + "; ".join(cv["transferable_skills"]))
    st.markdown("**Skills:** " + (", ".join(skills) if skills else "None selected"))
    for ach in cv.get("achievements", []):
        st.markdown(f"- {ach}")

    st.info("Prototype 1 shows a preview. Prototype 2 will turn this into a one-page PDF you can share.")
    c1, c2 = st.columns(2)
    c1.button("Edit answers", on_click=go, args=(3,))
    if c2.button("Start again"):
        for k in list(ss.keys()):
            del ss[k]
        st.rerun()
