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
FEEDBACK = setting("FEEDBACK_EMAIL")   # shown at the foot of the profile page; kept in Secrets, not in the code

S_STORY, S_WELCOME, S_UPLOAD, S_SKILLS = 0, 1, 2, 3   # step numbers
QPAGE0 = 4                      # first question page
PROFILE = QPAGE0 + len(PAGES)   # profile step
STEP_NAMES = ["My story", "Welcome", "Your CV", "Your skills"] + [f"Page {i + 1} of {len(PAGES)}" for i in range(len(PAGES))] + ["Your profile"]

ss = st.session_state
ss.setdefault("step", 0)
ss.setdefault("cv", None)
ss.setdefault("answers", {})
ss.setdefault("chosen_skills", [])
a = ss.answers


def save_typing():
    """Copy text boxes into the answers before changing page.

    A text box only sends its value when the user presses Enter or clicks away.
    If they click Next straight after typing, the value arrives with the click,
    so we save it here, before the page (and its boxes) disappear.
    """
    ans = ss.answers
    for k in list(ss.keys()):
        v = ss[k]
        if not isinstance(k, str) or not isinstance(v, str) or not k.startswith("w_"):
            continue
        if k in ("w_display_name", "w_strengths_text", "w_other_skills"):
            ans[k[2:]] = v
        elif k.startswith("w_outside_d_"):
            opt = Q["outside"]["options"][int(k.rsplit("_", 1)[1])]
            ans.setdefault("outside_detail", {})[opt] = v
        elif k.endswith("_text"):
            ans[k[2:]] = v


def go(n):
    save_typing()
    ss.step = n


# ---------- Test mode (for the project team only) ----------
# Open the app with ?test=<TEST_CODE> on the end of the link. TEST_CODE lives in Streamlit Secrets.
# Without the code, nothing here shows, so testers always go through every step.
TEST_CODE = setting("TEST_CODE")
if TEST_CODE and st.query_params.get("test") == TEST_CODE:
    ss.test_mode = True


def fill_sample():
    """Load the sample CV (keyword matching, no AI cost) and fill every empty answer."""
    if not ss.cv:
        f = HERE / "samples" / "sample_cv.docx"
        ss.cv = read_cv(f.name, f.read_bytes(), SKILLS, None)
        ss.chosen_skills = list(ss.cv.get("skills", []))
    ss.consent = True
    ans = ss.answers
    for qid, q in Q.items():
        if q["kind"] == "special" or ans.get(qid):
            continue
        first = list(q["options"])[0]
        ans[qid] = first if q["kind"] == "one" else [first]
    for opt in ans.get("outside", []):
        if opt in Q["outside"]["detail_hints"]:
            ans.setdefault("outside_detail", {}).setdefault(opt, "Sample answer for testing")
    ans.setdefault("display_name", "Test User")
    for k in [k for k in ss.keys() if isinstance(k, str) and k.startswith("w_")]:
        del ss[k]   # so every box shows the filled answers


if ss.get("test_mode"):
    with st.sidebar:
        st.markdown("### Test mode")
        st.caption("Only people with the test link see this.")
        st.button("Fill sample answers", on_click=fill_sample, type="primary")
        for n, name in enumerate(STEP_NAMES):
            if QPAGE0 <= n < PROFILE:
                nums = [Q[qid]["num"] for qid in PAGES[n - QPAGE0]["questions"]]
                name = f"{name}: Q{min(nums)} to Q{max(nums)}"
            st.button(f"Go to {name}", key=f"jump_{n}", on_click=go, args=(n,))


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
        ask_multi("strengths_pick", options=picks, max_sel=2, label="Choose from your answers to question 3")
    else:
        st.caption("Tick some answers in question 3 first, or add a strength below.")
        a["strengths_pick"] = []
    a["strengths_text"] = st.text_input("Add another strength", value=a.get("strengths_text", ""), key="w_strengths_text")


def ask_outside_details():
    """One required box under each ticked option in question 14."""
    hints = Q["outside"]["detail_hints"]
    details = {}
    for i, opt in enumerate(Q["outside"]["options"]):
        if opt not in a.get("outside", []) or opt not in hints:
            continue
        label = "Something else: please describe" if opt == OTHER else f"{opt}: tell us more"
        details[opt] = st.text_input(label, value=a.get("outside_detail", {}).get(opt, ""), key=f"w_outside_d_{i}",
                                     placeholder=hints[opt], max_chars=100)
        if not has_words(details[opt]):
            short = "Something else" if opt == OTHER else opt
            st.caption(f"Please fill this in and press Enter, or untick {short}.")
    a["outside_detail"] = details


def answered(qid):
    q = Q[qid]
    if q.get("optional") or q["kind"] == "special":
        return True
    v = a.get(qid)
    if qid == "outside":
        # Every ticked option that opens a box needs a few words in it.
        hints, detail = Q["outside"]["detail_hints"], a.get("outside_detail", {})
        return bool(v) and all(has_words(detail.get(o)) for o in v if o in hints)
    return bool(v)


OTHER = "Something else (please describe)"


def has_words(text):
    """True only if the text has at least one letter or number. Spaces and full stops do not count."""
    return any(ch.isalnum() for ch in (text or ""))


# ---------- Header ----------
BANNER = HERE / "banner.jpg"
# Eddie's story, shown first. Edit the words here; keep sentences short.
STORY_TEXT = """At 58, I was retrenched. I had spent my whole working life in corporations, \
over 30 years in logistics and supply chain. Then one day, it ended.

The hardest question was not how to find a job. It was what I wanted to do next. \
I had never really thought about it. Whether you are let go or leave by choice, \
you may face the same question.

So I went back to learning. I joined the What's Next programme and reskilled at Republic Polytechnic. \
I learned to work with AI tools, and I used them to build this app.

What I learned is simple. My past did not have to limit me. \
My experience was my strength, once I learned how to use it and repackage it. \
But first, I had to know what I wanted. Only then could anyone help me find it.

This app helps you think that through, in about 12 minutes. At the end, you will know what you now \
want to be doing. You will also have a one-page profile to share with hirers."""
if ss.step == S_STORY and BANNER.exists():
    # The banner already carries the title, so it replaces st.title on the first screen.
    st.image(str(BANNER), width="stretch",
             alt="Beyond the CV. Helping people over 50 show what they can contribute now.")
else:
    st.title("Beyond the CV")
st.caption(f"Step {ss.step + 1} of {len(STEP_NAMES)}")
st.progress((ss.step + 1) / len(STEP_NAMES))
if QPAGE0 <= ss.step < PROFILE:
    st.subheader(STEP_NAMES[ss.step])
if not API_KEY:
    st.info("Demo mode: skills are suggested by keyword matching. AI reading is switched off.")

# ---------- Step 0: Eddie's story ----------
if ss.step == S_STORY:
    st.markdown("## What's next for me?")
    st.markdown(STORY_TEXT)
    st.caption("Eddie Sng, What's Next alumnus and builder of this app")
    st.button("Next", on_click=go, args=(S_WELCOME,), type="primary")

# ---------- Step 1: welcome and consent ----------
elif ss.step == S_WELCOME:
    st.markdown("Your CV shows where you have been. It rarely shows what you would accept, "
                "or what you want next. This tool helps you say both, in one page.")
    st.markdown("**How it works**\n\n1. Upload your CV, or your LinkedIn profile as a PDF.\n"
                "2. We suggest skills from it. You confirm them.\n"
                f"3. You answer questions a CV never asks, over {len(PAGES)} short pages.\n"
                "4. You get a one-page profile to download.")
    st.markdown("**Please finish in one sitting. It takes about 12 minutes.** If your computer goes to sleep, "
                "or you switch to another app on your phone, your answers may be lost.")

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
    c1, c2 = st.columns(2)
    c1.button("Back", on_click=go, args=(S_STORY,), key="back_welcome")
    c2.button("Start", disabled=not agree, on_click=go, args=(S_UPLOAD,), type="primary")

# ---------- Step 2: upload ----------
elif ss.step == S_UPLOAD:
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
                go(S_SKILLS)
                st.rerun()
            except Exception as e:
                st.error("Sorry, we could not read that file. Please try a PDF or Word version.")
                st.caption(f"Detail: {e}")
    if ss.cv:
        st.button("Keep my earlier CV and continue", on_click=go, args=(S_SKILLS,))
    st.button("Back", on_click=go, args=(S_WELCOME,))

# ---------- Step 3: confirm skills ----------
elif ss.step == S_SKILLS:
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
        # Count from the latest widget state, so the header updates on the same click.
        count = len(ss.get(f"ms_{theme}", pre))
        with st.expander(f"{theme} ({count} selected)", expanded=bool(pre) or count > 0):
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
    c1.button("Back", on_click=go, args=(S_UPLOAD,))
    c2.button("Next", type="primary", on_click=go, args=(QPAGE0,))

# ---------- Steps 4 to 7: question pages ----------
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
            if qid == "outside":
                ask_outside_details()
        elif qid == "strengths":
            ask_strengths()
        ask_text(qid)
        st.write("")

    missing = [Q[qid]["num"] for qid in page["questions"] if not answered(qid)]
    last = ss.step == PROFILE - 1
    if last:
        # Asked here, not on the profile page, so the name is saved before the PDF is made.
        st.markdown("##### Your name on the profile")
        a["display_name"] = st.text_input("Name to show on your profile (optional)", value=a.get("display_name", ""),
                                          key="w_display_name", placeholder="e.g. Tan Ah Beng",
                                          help="Leave blank to show 'Profile of Candidate'.")
        st.write("")
    c1, c2 = st.columns(2)
    c1.button("Back", on_click=go, args=(ss.step - 1,))
    c2.button("See my profile" if last else "Next page", type="primary", disabled=bool(missing),
              on_click=go, args=(ss.step + 1,))
    if missing:
        nums = ", ".join(str(n) for n in sorted(set(missing)))
        st.caption(f"Please answer question{'s' if len(set(missing)) > 1 else ''} {nums} to continue.")

# ---------- Step 8: profile ----------
elif ss.step == PROFILE:
    cv = ss.cv or {}
    skills = ss.chosen_skills + [s.strip() for s in a.get("other_skills", "").split(",") if s.strip()]
    sections = build_sections(a, cv, skills)

    shown = (a.get("display_name") or "").strip() or "Candidate"
    st.markdown(f"## Profile of {shown}")
    st.caption("To change the name, click Edit answers below.")
    for heading, lines in sections:
        st.markdown(f"### {heading}")
        st.markdown("\n".join(f"- {line}" for line in lines))

    pdf = make_pdf(sections, a.get("display_name", ""))
    fname = "Profile_of_" + "_".join(shown.split()) + ".pdf"
    st.download_button("Download my one-page profile (PDF)", pdf, file_name=fname, mime="application/pdf", type="primary")
    st.caption("Your answers are not saved after you close this page. Download your profile first.")

    c1, c2 = st.columns(2)
    c1.button("Edit answers", on_click=go, args=(PROFILE - 1,))
    if c2.button("Start again"):
        for k in list(ss.keys()):
            del ss[k]
        st.rerun()

    if FEEDBACK:
        st.divider()
        st.markdown(f"We value your feedback. If you have any, please email "
                    f"[{FEEDBACK}](mailto:{FEEDBACK}?subject=Beyond%20the%20CV%20feedback).")

# ---------- Feedback line on every page before the profile ----------
# The profile page has its own fuller message above, so it is skipped there.
if FEEDBACK and ss.step != PROFILE:
    st.write("")
    st.caption(f"Questions or feedback? Email "
               f"[{FEEDBACK}](mailto:{FEEDBACK}?subject=Beyond%20the%20CV%20feedback).")
