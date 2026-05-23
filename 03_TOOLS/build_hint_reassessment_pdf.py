"""Minimal PDF generator for Zombie Quest New Hint Reassessment — readable color theme."""
from pathlib import Path
import re

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, Preformatted, KeepTogether
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER


SRC = Path(r"D:\Study\Project\zombie\02_WORKING_NOTES\ZOMBIE_QUEST_NEW_HINT_REASSESSMENT.md")
OUT_DIR = Path(r"D:\Study\Project\zombie\00_FINAL")
OUT_PDF = OUT_DIR / "Zombie_Quest_New_Hint_Reassessment.pdf"

# ── Color palette ─────────────────────────────────────────────────────────────
DARK   = colors.HexColor("#0f172a")   # dark navy text
ACCENT = colors.HexColor("#1d4ed8")   # strong blue for headers
GREEN  = colors.HexColor("#15803d")    # forest green for rules / positive
RED    = colors.HexColor("#b91c1c")    # deep red for warnings / negatives
CODEBG = colors.HexColor("#f1f5f9")    # light slate for code blocks
TABLE_HDR  = colors.HexColor("#1e3a5f")
TABLE_ALT  = colors.HexColor("#f8fafc")
WHITE = colors.white


def md_elements(text: str) -> list:
    lines = text.splitlines()
    elements = []
    styles = _styles()
    i = 0

    while i < len(lines):
        raw = lines[i]
        stripped = raw.strip()

        # ── Horizontal rule ────────────────────────────────────────────────
        if stripped == "---":
            elements.append(Spacer(1, 6))
            elements.append(HRFlowable(width="100%", thickness=0.5,
                                       color=colors.HexColor("#cbd5e1")))
            elements.append(Spacer(1, 6))
            i += 1
            continue

        # ── Code block ─────────────────────────────────────────────────────
        if stripped.startswith("```"):
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            # Determine if it's a "negative" block (Do Not list)
            code_text = "\n".join(code_lines)
            block_style = styles["code_bad"] if any(
                x in code_text for x in ["no ", "- no ", "return", "die", "invade",
                                          "Volt", "zombie action", "Quincy-only",
                                          "self-zombify", "cosplay"]
            ) else styles["code"]
            elements.append(Preformatted(code_text, block_style))
            elements.append(Spacer(1, 5))
            i += 1
            continue

        # ── Heading 1 ───────────────────────────────────────────────────────
        if stripped.startswith("# "):
            elements.append(Spacer(1, 8))
            elements.append(Paragraph(stripped[2:], styles["h1"]))
            elements.append(HRFlowable(width="100%", thickness=1.5,
                                       color=ACCENT))
            elements.append(Spacer(1, 6))
            i += 1
            continue

        # ── Heading 2 ───────────────────────────────────────────────────────
        if stripped.startswith("## "):
            elements.append(Spacer(1, 10))
            elements.append(Paragraph(stripped[3:], styles["h2"]))
            i += 1
            continue

        # ── Heading 3 ───────────────────────────────────────────────────────
        if stripped.startswith("### "):
            elements.append(Spacer(1, 6))
            elements.append(Paragraph(stripped[4:], styles["h3"]))
            i += 1
            continue

        # ── Table ───────────────────────────────────────────────────────────
        if stripped.startswith("|") and stripped.count("|") >= 2:
            table_data = []
            row_i = i
            while row_i < len(lines) and lines[row_i].strip().startswith("|"):
                cells = [c.strip() for c in lines[row_i].split("|")[1:-1]]
                table_data.append(cells)
                row_i += 1
            col_count = len(table_data[0])
            col_w = 160 * mm / col_count
            t = Table(table_data, colWidths=[col_w] * col_count)
            t.setStyle(TableStyle([
                # Header row
                ("BACKGROUND",   (0, 0), (-1, 0), TABLE_HDR),
                ("TEXTCOLOR",   (0, 0), (-1, 0), WHITE),
                ("FONTNAME",     (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE",     (0, 0), (-1, 0), 10),
                ("ALIGN",        (0, 0), (-1, 0), "CENTER"),
                ("BOTTOMPADDING",(0, 0), (-1, 0), 5),
                ("TOPPADDING",   (0, 0), (-1, 0), 5),
                # Data
                ("FONTNAME",     (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE",     (0, 1), (-1, -1), 9.5),
                ("TOPPADDING",   (0, 1), (-1, -1), 4),
                ("BOTTOMPADDING",(0, 1), (-1, -1), 4),
                ("LEFTPADDING",  (0, 0), (-1, -1), 6),
                # Alternating rows
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [TABLE_ALT, WHITE]),
                # Grid
                ("GRID",  (0, 0), (-1, -1), 0.4, colors.HexColor("#94a3b8")),
                ("BOX",   (0, 0), (-1, -1), 1,   colors.HexColor("#1e3a5f")),
                # First col bold
                ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 1), (0, -1), 9.5),
            ]))
            elements.append(Spacer(1, 4))
            elements.append(t)
            elements.append(Spacer(1, 6))
            i = row_i
            continue

        # ── Bullet ───────────────────────────────────────────────────────────
        if stripped.startswith("- "):
            body = stripped[2:]
            body = _inline(body)
            elements.append(Paragraph(f"<bullet>&ndash;</bullet> {body}",
                                     styles["bullet"]))
            i += 1
            continue

        # ── Empty line ───────────────────────────────────────────────────────
        if stripped == "":
            i += 1
            continue

        # ── Paragraph ────────────────────────────────────────────────────────
        body = _inline(stripped)
        elements.append(Paragraph(body, styles["para"]))
        elements.append(Spacer(1, 2))
        i += 1

    return elements


def _inline(text: str) -> str:
    """Apply bold and monospace inline formatting."""
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'`(.+?)`', r'<font face="Courier" color="#1e3a5f">\1</font>', text)
    return text


def _styles() -> dict:
    base = getSampleStyleSheet()

    def style(name, **kw):
        return ParagraphStyle(name, parent=base["Normal"], **kw)

    return {
        "h1": style("h1",
            fontName="Helvetica-Bold", fontSize=17,
            textColor=DARK, spaceBefore=4, spaceAfter=2, leading=22),

        "h2": style("h2",
            fontName="Helvetica-Bold", fontSize=13,
            textColor=ACCENT, spaceBefore=8, spaceAfter=3, leading=18),

        "h3": style("h3",
            fontName="Helvetica-Bold", fontSize=10.5,
            textColor=DARK, spaceBefore=6, spaceAfter=2, leading=15),

        "para": style("para",
            fontName="Helvetica", fontSize=10,
            textColor=DARK, spaceBefore=1, spaceAfter=1, leading=15),

        "bullet": style("bullet",
            fontName="Helvetica", fontSize=10,
            textColor=DARK, leftIndent=12, firstLineIndent=-12,
            spaceBefore=1, spaceAfter=1, leading=15),

        "code": style("code",
            fontName="Courier", fontSize=8.5,
            textColor=DARK, backColor=CODEBG,
            leftIndent=8, rightIndent=8,
            spaceBefore=3, spaceAfter=3, leading=13),

        "code_bad": style("code_bad",
            fontName="Courier", fontSize=8.5,
            textColor=RED, backColor=colors.HexColor("#fef2f2"),
            leftIndent=8, rightIndent=8,
            spaceBefore=3, spaceAfter=3, leading=13),
    }


def build_pdf():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    md_text = SRC.read_text(encoding="utf-8")

    doc = SimpleDocTemplate(
        str(OUT_PDF),
        pagesize=A4,
        leftMargin=18*mm, rightMargin=18*mm,
        topMargin=20*mm, bottomMargin=22*mm,
        title="Zombie Quest — New Hint Reassessment",
        author="Zombie Quest Research",
    )

    doc.build(md_elements(md_text))
    print(f"PDF written to: {OUT_PDF}")


if __name__ == "__main__":
    build_pdf()
