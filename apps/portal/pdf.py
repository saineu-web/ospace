"""Render a signed agreement to PDF with reportlab (no HTML engine needed)."""
import io
from xml.sax.saxutils import escape

from django.conf import settings
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

PURPLE = colors.HexColor("#6d28d9")
GREY = colors.HexColor("#6b7280")


def build_agreement_pdf(signed) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        leftMargin=0.9 * inch,
        rightMargin=0.9 * inch,
        topMargin=0.9 * inch,
        bottomMargin=0.9 * inch,
        title=signed.title,
        author=settings.SITE["legal_name"],
    )
    ss = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=ss["Title"], fontSize=18, textColor=PURPLE, spaceAfter=4, alignment=TA_CENTER)
    sub = ParagraphStyle("sub", parent=ss["Normal"], fontSize=9, textColor=GREY, alignment=TA_CENTER, spaceAfter=18)
    h2 = ParagraphStyle("h2", parent=ss["Heading3"], fontSize=11.5, textColor=PURPLE, spaceBefore=10, spaceAfter=4)
    body = ParagraphStyle("body", parent=ss["Normal"], fontSize=10, leading=14, spaceAfter=7)
    small = ParagraphStyle("small", parent=ss["Normal"], fontSize=8, textColor=GREY, leading=11)

    story = [
        Paragraph(escape(signed.title), h1),
        Paragraph(f"{escape(settings.SITE['legal_name'])} · Version {signed.template_version} · Reference {signed.reference}", sub),
    ]
    for block in signed.rendered_body.replace("\r\n", "\n").split("\n\n"):
        block = block.strip()
        if not block:
            continue
        if block.startswith("# "):
            story.append(Paragraph(escape(block[2:]), h2))
        else:
            story.append(Paragraph(escape(block).replace("\n", "<br/>"), body))

    story.append(Spacer(1, 18))
    story.append(Paragraph("Electronic signature", h2))
    signed.signature_image.open("rb")
    sig = Image(signed.signature_image, width=2.6 * inch, height=1.0 * inch, kind="proportional")
    signed_local = timezone.localtime(signed.signed_at)
    meta = [
        ["Signed by", signed.typed_name],
        ["Email", signed.driver.email],
        ["Date & time", signed_local.strftime("%B %d, %Y at %I:%M %p %Z")],
        ["IP address", signed.ip_address or "—"],
        ["Document hash", Paragraph(signed.content_hash, ParagraphStyle("hash", parent=small, fontSize=7.5, leading=10, textColor=colors.black))],
    ]
    t = Table([[sig, Table(meta, colWidths=[1.1 * inch, 3.2 * inch])]], colWidths=[2.8 * inch, 4.4 * inch])
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (0, 0), 0.6, colors.black)]))
    story.append(t)
    story.append(Spacer(1, 10))
    story.append(
        Paragraph(
            "This document was signed electronically through the Ospace driver portal. The signer typed their name, "
            "drew their signature and confirmed their consent to sign electronically. The SHA-256 hash above covers the "
            "exact document text, the typed name and the timestamp, so any later change to the text can be detected.",
            small,
        )
    )
    doc.build(story)
    return buf.getvalue()
