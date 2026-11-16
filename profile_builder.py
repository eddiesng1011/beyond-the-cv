"""Turn answers into profile sections, and sections into a one-page PDF.

Template wording for now. A flowing AI-written narrative can replace build_sections later.
"""
import io

from questions import Q


def _lc(s: str) -> str:
    """Lower-case the first letter for use mid-sentence, unless it starts an acronym (e.g. AI)."""
    if len(s) > 1 and s[1].isupper():
        return s
    return s[:1].lower() + s[1:]


def _one(a, qid):
    return Q[qid]["options"].get(a.get(qid)) if a.get(qid) else None


def _multi(a, qid):
    skip = set(Q[qid].get("skip_in_profile", []))
    items = [x for x in a.get(qid, []) if x not in skip]
    if not items:
        return None
    return f"{Q[qid]['lead']}: " + "; ".join(_lc(x) for x in items) + "."


def build_sections(a: dict, cv: dict, skills: list) -> list:
    """Return [(heading, [lines])]. Empty sections are dropped."""
    s1 = []
    step = _one(a, "step_back")
    if step:
        s1.append(step + (f' In my words: "{a["step_back_text"]}"' if a.get("step_back_text") else ""))
    s1 += [x for x in (_multi(a, "responsibilities"), _one(a, "pay"), _multi(a, "arrangements"),
                       _one(a, "days"), _one(a, "shifts"), _one(a, "schedule"), _one(a, "start"),
                       _multi(a, "location"), _one(a, "industry")) if x]

    s2 = [x for x in (_multi(a, "interests"), _multi(a, "activities")) if x]
    strengths = list(a.get("strengths_pick", []))
    if a.get("strengths_text"):
        strengths.append(a["strengths_text"])
    if strengths:
        s2.append("Strengths I want you to know about: " + "; ".join(_lc(x) for x in strengths) + ".")

    s3 = []
    if cv.get("headline"):
        s3.append(cv["headline"])
    if skills:
        s3.append("Skills: " + ", ".join(skills) + ".")
    if cv.get("transferable_skills"):
        s3.append("Strengths across industries: " + "; ".join(cv["transferable_skills"]) + ".")
    for ach in cv.get("achievements", [])[:3]:
        s3.append(ach)
    outside = _multi(a, "outside")
    if outside:
        s3.append(outside)
    if a.get("outside_text") and "Something else (please describe)" in a.get("outside", []):
        s3.append(f"Also: {a['outside_text']}")

    s4 = []
    ai = _one(a, "ai")
    if ai:
        s4.append(ai + (f" For example: {a['ai_text']}." if a.get("ai_text") else ""))
    s4 += [x for x in (_multi(a, "learning"), _multi(a, "learning_support")) if x]

    s5 = [x for x in (_multi(a, "motivation"),) if x]
    if a.get("motivation_text"):
        s5.append(f'In my words: "{a["motivation_text"]}"')

    sections = [("What my CV does not tell you", s1), ("Work I would like to do", s2), ("What I bring", s3),
                ("Learning and new tools", s4), ("What matters to me", s5)]
    return [(h, lines) for h, lines in sections if lines]


def make_pdf(sections: list, name: str = "") -> bytes:
    """One A4 page. Text shrinks to fit if a profile is unusually long."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import Frame, KeepInFrame, Paragraph, Spacer
    from reportlab.pdfgen import canvas
    from xml.sax.saxutils import escape

    teal, amber, grey = colors.HexColor("#17414F"), colors.HexColor("#B5651D"), colors.HexColor("#6B7B83")
    title = ParagraphStyle("t", fontName="Helvetica-Bold", fontSize=20, leading=24, textColor=teal)
    sub = ParagraphStyle("s", fontName="Helvetica", fontSize=9.5, leading=12, textColor=grey)
    head = ParagraphStyle("h", fontName="Helvetica-Bold", fontSize=11.5, leading=14, textColor=amber,
                          spaceBefore=9, spaceAfter=3)
    body = ParagraphStyle("b", fontName="Helvetica", fontSize=10, leading=13.2, leftIndent=9, bulletIndent=0,
                          spaceAfter=2.5)

    story = [Paragraph(escape(name) if name else "Candidate profile", title),
             Paragraph("Beyond the CV: what my CV does not tell you. This profile accompanies my CV.", sub),
             Spacer(1, 4)]
    for h, lines in sections:
        story.append(Paragraph(escape(h.upper()), head))
        story += [Paragraph(escape(line), body, bulletText="•") for line in lines]

    buf = io.BytesIO()
    W, H = A4
    c = canvas.Canvas(buf, pagesize=A4)
    c.setTitle(f"{name or 'Candidate'} profile")
    frame = Frame(18 * mm, 16 * mm, W - 36 * mm, H - 30 * mm, showBoundary=0)
    frame.addFromList([KeepInFrame(W - 36 * mm, H - 32 * mm, story, mode="shrink")], c)
    c.setFont("Helvetica", 8)
    c.setFillColor(grey)
    c.drawString(18 * mm, 10 * mm, "All answers are the candidate's own. Prepared with Beyond the CV, a What's Next alumni prototype.")
    c.showPage()
    c.save()
    return buf.getvalue()
