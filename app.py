"""Beyond the CV: Prototype 2.

Flow: consent -> CV or LinkedIn PDF -> confirm skills -> 4 pages of beyond-the-CV questions
-> profile with a one-page PDF. Runs in demo mode (keyword matching) when no ANTHROPIC_API_KEY is set.
Answers are kept for the whole visit, so Back never wipes them. Nothing is saved after the page closes.
"""
import os
from pathlib import Path

import streamlit as st

from cv_reader import load_skills, read_cv
from profile_builder import build_sections, make_pdf
from questions import PAGES, Q

HERE = Path(__file__).parent
st.set_page_config(page_title="Beyond the CV", page_icon=":briefcase:", layout="centered")

st.markdown("""
<style>
html, body, [class*="css"], .stMarkdown p, label, .stRadio label, .stCheckbox label { font-size: 18px !important; }
h1 { font-size: 2.2rem !important; }
.stButton button, .stDownloadButton button { font-size: 18px; padding: 0.5rem 1.4rem; }
[data-testid="InputInstructions"] { display: none; }
</style>
""", unsafe_allow_html=True)


def setting(name, default=None):
    try:
        val = st.secrets.get(name)
    except Exception:
        val = None
    return val or os.environ.get(name) or default


SKILLS = load_skills(HERE / "skills.csv")
API_KEY = setting("ANTHROPIC_API_KEY")
HOST = setting("HOST_NAME", "the Beyond the CV project team")
CONTACT = setting("CONTACT_EMAIL")

QPAGE0 = 3                      # first question page
PROFILE = QPAGE0 + len(PAGES)   # profile step
STEP_NAMES = ["Welcome", "Your CV", "Your skills"] + [f"Beyond the CV, page {i + 1} of {len(PAGES)}" for i in range(len(PAGES))] + ["Your profile"]

ss = st.session_state
ss.setdefault("step", 0)
ss.setdefault("cv", None)
ss.setdefault("answers", {})
ss.setdefault("chosen_skills", [])
a = ss.answers


def go(n):
    ss.step = n


# ---------- Scroll to top on every step change ----------
ss.setdefault("_last_step", ss.step)
ss.setdefault("_scroll_runs", 0)
if ss._last_step != ss.step:
    ss._last_step = ss.step
    ss._scroll_runs += 1
    st.iframe(
        f"""<script>
        // step {ss.step}, run {ss._scroll_runs}
        const doc = window.parent.document;
        function toTop() {{
          [doc.querySelector('[data-testid="stMain"]'), doc.querySelector('[data-testid="stAppViewContainer"]'),
           doc.querySelector('section.main'), doc.scrollingElement, doc.documentElement, doc.body]
            .forEach(t => {{ if (t) t.scrollTop = 0; }});
          window.parent.scrollTo(0, 0);
        }}
        if (doc.activeElement) doc.activeElement.blur();
        toTop();
        let n = 0;
        const timer = setInterval(() => {{ toTop(); if (++n >= 15) clearInterval(timer); }}, 100);
        </script>""",
        height=1,
    )


# ---------- Question widgets that remember their answers ----------
def ask_one(qid):
    q = Q[qid]
    opts = list(q["options"])
    idx = opts.index(a[qid]) if a.get(qid) in opts else None
    label = q["label"] + (" (optional)" if q.get("optional") else "")
    a[qid] = st.radio(label, opts, index=idx, key=f"w_{qid}")


def ask_multi(qid, options=None, max_sel=None, label=None):
    q = Q.get(qid, {})
    options = options if options is not None else q["options"]
    max_sel = max_sel if max_sel is not None else q.get("max")
    label = label or (q["label"] + (" (optional)" if q.get("optional") else ""))
    st.markdown(f"**{label}**")
    stored = a.get(qid, [])
    # Use the latest tick state (from this click) where it exists, so the limit applies straight away.
    current = [opt for i, opt in enumerate(options) if ss.get(f"w_{qid}_{i}", opt in stored)]
    full = max_sel is not None and len(current) >= max_sel
    picked = []
    for i, opt in enumerate(options):
        on = st.checkbox(opt, value=opt in current, key=f"w_{qid}_{i}", disabled=full and opt not in current)
        if on:
            picked.append(opt)
    if max_sel is not None:
        st.caption(f"{len(picked)} of {max_sel} selected" + (". Untick one to change your choice." if len(picked) >= max_sel else ""))
    a[qid] = picked


def ask_text(qid):
    q = Q[qid]
    if "text" not in q:
        return
    if "text_when" in q:
        chosen = a.get(qid) if isinstance(a.get(qid), list) else [a.get(qid)]
        if not set(chosen) & set(q["text_when"]):
            return
    label, hint = q["text"]
    a[f"{qid}_text"] = st.text_input(label, value=a.get(f"{qid}_text", ""), key=f"w_{qid}_text", placeholder=hint)


def ask_strengths():
    picks = a.get("activities", [])
    st.markdown(f"**{Q['strengths']['label']} (optional)**")
    if picks:
        ask_multi("strengths_pick", options=picks, max_sel=2, label="Choose from the activities you selected")
    else:
        st.caption("Select some activities above first, or add a strength below.")
        a["strengths_pick"] = []
    a["strengths_text"] = st.text_input("Add another strength", value=a.get("strengths_text", ""), key="w_strengths_text")
    a["strengths_help"] = st.checkbox("I would like help identifying my strengths", value=a.get("strengths_help", False), key="w_strengths_help")


def answered(qid):
    q = Q[qid]
    if q.get("optional") or q["kind"] == "special":
        return True
    v = a.get(qid)
    return bool(v)


# ---------- Header ----------
st.title("Beyond the CV")
st.caption(f"Step {ss.step + 1} of {len(STEP_NAMES)}")
st.progress((ss.step + 1) / len(STEP_NAMES))
if QPAGE0 <= ss.step < PROFILE:
    st.subheader(STEP_NAMES[ss.step])
if not API_KEY:
    st.info("Demo mode: skills are suggested by keyword matching. AI reading is switched off.")

# ---------- Step 0: welcome and consent ----------
if ss.step == 0:
    st.markdown("Your CV shows where you have been. It rarely shows what you would accept, "
                "or what you want next. This tool helps you say both, in one page.")
    st.markdown("**How it works**\n\n1. Upload your CV, or your LinkedIn profile as a PDF.\n"
                "2. We suggest skills from it. You confirm them.\n"
                f"3. You answer questions a CV never asks, over {len(PAGES)} short pages.\n"
                "4. You get a one-page profile to download.")

    st.markdown("### Your personal data")
    ai_line = ("- **AI reading:** your CV is sent to an AI service (Claude, by Anthropic) to suggest your skills.\n"
               if API_KEY else
               "- **Reading your CV:** this demo version reads your CV inside the app. It is not sent to an AI service.\n")
    contact_line = (f"For questions about your data, contact {CONTACT}." if CONTACT
                    else "For questions about your data, contact the person who invited you to try this app.")
    st.markdown(
        f"This is a prototype built by {HOST}. Please read how we handle your personal data.\n\n"
        "- **What we use:** the CV or LinkedIn PDF you upload, and your answers in this app.\n"
        "- **Why:** only to build your one-page profile.\n"
        + ai_line +
        "- **What we keep:** nothing. Your CV and answers are not saved. They are cleared when you close this page, "
        "so download your profile before you leave.\n"
        "- **Your NRIC:** we do not need your NRIC or any other identification number. "
        "Please remove them from your CV before you upload it.\n"
        f"- **Changing your mind:** you can stop at any time by closing this page. {contact_line}"
    )
    agree = st.checkbox(f"I have read the above. I consent to {HOST} using my personal data in this way, "
                        "in line with the Personal Data Protection Act 2012.", value=ss.get("consent", False))
    ss.consent = agree
    st.button("Start", disabled=not agree, on_click=go, args=(1,), type="primary")

# ---------- Step 1: upload ----------
elif ss.step == 1:
    if API_KEY:
        st.markdown("Upload your CV as a PDF or Word file. A scanned PDF is fine.")
    else:
        st.markdown("Upload your CV as a Word file, or a PDF with text you can select. "
                    "Scanned PDFs need AI reading, which is switched off in this demo.")
    up = st.file_uploader("Your CV", type=["pdf", "docx", "txt"])

    with st.expander("No CV? Use your LinkedIn profile instead"):
        st.markdown(
            "1. On the LinkedIn home page, click **Me** at the top right corner.\n"
            "2. Select **View Profile**.\n"
            "3. Find the **three dots** underneath your name and click on them.\n"
            "4. Select **Save to PDF**. The file goes to your Downloads folder.\n"
            "5. Upload that PDF in the box above."
        )

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
            except Exception as e:
                st.error("Sorry, we could not read that file. Please try a PDF or Word version.")
                st.caption(f"Detail: {e}")
    if ss.cv:
        st.button("Keep my earlier CV and continue", on_click=go, args=(2,))
    st.button("Back", on_click=go, args=(0,))

# ---------- Step 2: confirm skills ----------
elif ss.step == 2:
    cv = ss.cv or {}
    if cv.get("headline"):
        st.markdown(f"**In one line:** {cv['headline']}")
    st.markdown("These are skills you have **used**, based on your CV. Untick any that are wrong. Add any we missed. "
                "Later pages ask what you would **like** to do next.")
    if not ss.chosen_skills:
        st.warning("We could not pick out skills from this CV. Please open the groups below and tick the skills "
                   "you have used. They will appear on your profile under What I bring.")
    elif cv.get("fallback"):
        st.caption("Skills were matched by keywords for this CV. Please check them carefully.")

    chosen = []
    for theme, group in SKILLS.groupby("theme", sort=False):
        options = list(group["skill"])
        pre = [s for s in options if s in ss.chosen_skills]
        with st.expander(f"{theme} ({len(pre)} selected)", expanded=bool(pre)):
            chosen += st.multiselect(theme, options, default=pre, key=f"ms_{theme}",
                                     label_visibility="collapsed", select_all=False)
    ss.chosen_skills = chosen
    a["other_skills"] = st.text_input("Other skills not in the list (separate with commas)",
                                      value=a.get("other_skills", ""), key="w_other_skills")

    if cv.get("transferable_skills"):
        st.markdown("**Strengths that could carry into another industry**")
        for t in cv["transferable_skills"]:
            st.markdown(f"- {t}")

    c1, c2 = st.columns(2)
    c1.button("Back", on_click=go, args=(1,))
    c2.button("Next", type="primary", on_click=go, args=(3,))

# ---------- Steps 3 to 6: question pages ----------
elif QPAGE0 <= ss.step < PROFILE:
    page = PAGES[ss.step - QPAGE0]
    cv = ss.cv or {}
    if ss.step == QPAGE0:
        st.markdown("These questions are what a CV never asks. There are no wrong answers. "
                    "Questions marked optional can be skipped.")
    st.markdown(f"#### {page['title']}")

    for qid in page["questions"]:
        q = Q[qid]
        if q["category"]:
            st.markdown(f"##### {q['num']}. {q['category']}")
        if qid == "step_back" and cv.get("managed_people"):
            team = f" of up to {cv['largest_team']} people" if cv.get("largest_team") else ""
            st.markdown(f"Your CV shows you have led teams{team}.")
        if q["kind"] == "one":
            ask_one(qid)
        elif q["kind"] == "multi":
            ask_multi(qid)
        elif qid == "strengths":
            ask_strengths()
        ask_text(qid)
        st.write("")

    missing = [Q[qid]["num"] for qid in page["questions"] if not answered(qid)]
    last = ss.step == PROFILE - 1
    c1, c2 = st.columns(2)
    c1.button("Back", on_click=go, args=(ss.step - 1,))
    c2.button("See my profile" if last else "Next page", type="primary", disabled=bool(missing),
              on_click=go, args=(ss.step + 1,))
    if missing:
        nums = ", ".join(str(n) for n in sorted(set(missing)))
        st.caption(f"Please answer question{'s' if len(set(missing)) > 1 else ''} {nums} to continue.")

# ---------- Step 7: profile ----------
elif ss.step == PROFILE:
    cv = ss.cv or {}
    skills = ss.chosen_skills + [s.strip() for s in a.get("other_skills", "").split(",") if s.strip()]
    sections = build_sections(a, cv, skills)

    a["display_name"] = st.text_input("Name to show on your profile (optional)", value=a.get("display_name", ""),
                                      key="w_display_name")
    st.markdown(f"## {a['display_name'] or 'Candidate profile'}")
    for heading, lines in sections:
        st.markdown(f"### {heading}")
        st.markdown("\n".join(f"- {line}" for line in lines))

    pdf = make_pdf(sections, a.get("display_name", ""))
    fname = (a.get("display_name") or "my").strip().replace(" ", "_") + "_beyond_the_cv.pdf"
    st.download_button("Download my one-page profile (PDF)", pdf, file_name=fname, mime="application/pdf", type="primary")
    st.caption("Your answers are not saved after you close this page. Download your profile first.")

    c1, c2 = st.columns(2)
    c1.button("Edit answers", on_click=go, args=(PROFILE - 1,))
    if c2.button("Start again"):
        for k in list(ss.keys()):
            del ss[k]
        st.rerun()
