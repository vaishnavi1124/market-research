# # utils/Report_Save_to_pdf.py

# # from reportlab.platypus import (
# #     SimpleDocTemplate, Paragraph, Spacer, PageBreak, ListFlowable, ListItem,
# #     Preformatted, Table, TableStyle
# # )
# # from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
# # from reportlab.lib.enums import TA_LEFT, TA_CENTER
# # from reportlab.lib.pagesizes import A4, landscape
# # from reportlab.lib.units import inch
# # from reportlab.lib import colors
# # from reportlab.pdfbase.pdfmetrics import stringWidth
# # from datetime import datetime
# # import os
# # import re

# # # -------------------------------
# # # Styles (unique names)
# # # -------------------------------
# # def _build_styles():
# #     styles = getSampleStyleSheet()

# #     def add_style(name, **kwargs):
# #         if name in styles:
# #             del styles[name]
# #         styles.add(ParagraphStyle(name=name, **kwargs))

# #     base = styles["Normal"]
# #     add_style(
# #         "ProBody",
# #         parent=base,
# #         fontName="Helvetica",
# #         fontSize=10.5,
# #         leading=15,
# #         spaceAfter=6,
# #         textColor=colors.HexColor("#1F2937"),
# #     )
# #     add_style(
# #         "ProH1",
# #         parent=base,
# #         fontName="Helvetica-Bold",
# #         fontSize=18,
# #         leading=24,
# #         spaceBefore=6,
# #         spaceAfter=10,
# #         alignment=TA_LEFT,
# #         textColor=colors.HexColor("#0F172A"),
# #     )
# #     add_style(
# #         "ProH2",
# #         parent=base,
# #         fontName="Helvetica-Bold",
# #         fontSize=14,
# #         leading=20,
# #         spaceBefore=12,
# #         spaceAfter=6,
# #         textColor=colors.HexColor("#111827"),
# #     )
# #     add_style(
# #         "ProH3",
# #         parent=base,
# #         fontName="Helvetica-Bold",
# #         fontSize=12.5,
# #         leading=18,
# #         spaceBefore=10,
# #         spaceAfter=6,
# #         textColor=colors.HexColor("#111827"),
# #     )
# #     add_style(
# #         "ProBullet",
# #         parent=base,
# #         fontName="Helvetica",
# #         fontSize=10.5,
# #         leading=15,
# #         leftIndent=14,
# #         bulletIndent=6,
# #         spaceAfter=3,
# #         textColor=colors.HexColor("#1F2937"),
# #     )
# #     add_style(
# #         "ProCode",
# #         parent=base,
# #         fontName="Courier",
# #         fontSize=9.5,
# #         leading=14,
# #         backColor=colors.whitesmoke,
# #         leftIndent=6,
# #         rightIndent=6,
# #         spaceBefore=6,
# #         spaceAfter=6,
# #         borderWidth=0.5,
# #         borderColor=colors.HexColor("#E5E7EB"),
# #         borderPadding=6,
# #     )
# #     add_style(
# #         "ProTitle",
# #         parent=base,
# #         fontName="Helvetica-Bold",
# #         fontSize=22,
# #         leading=28,
# #         alignment=TA_CENTER,
# #         spaceAfter=14,
# #         textColor=colors.HexColor("#0F172A"),
# #     )
# #     add_style(
# #         "ProSubtitle",
# #         parent=base,
# #         fontName="Helvetica",
# #         fontSize=11.5,
# #         leading=16,
# #         alignment=TA_CENTER,
# #         textColor=colors.HexColor("#4B5563"),
# #         spaceAfter=18,
# #     )
# #     add_style(
# #         "ProCaption",
# #         parent=base,
# #         fontName="Helvetica-Oblique",
# #         fontSize=9.5,
# #         leading=13,
# #         textColor=colors.HexColor("#374151"),
# #         spaceBefore=2,
# #         spaceAfter=6,
# #     )
# #     return styles

# # # -------------------------------
# # # Header / footer
# # # -------------------------------
# # def _header_footer(title):
# #     def draw(canvas, doc):
# #         canvas.saveState()
# #         canvas.setStrokeColor(colors.HexColor("#E5E7EB"))
# #         canvas.setLineWidth(0.5)
# #         y_top = doc.height + doc.topMargin + 18
# #         canvas.line(doc.leftMargin, y_top, doc.leftMargin + doc.width, y_top)
# #         canvas.setFont("Helvetica", 9)
# #         canvas.setFillColor(colors.HexColor("#6B7280"))
# #         canvas.drawString(doc.leftMargin, y_top + 4, title[:80])
# #         canvas.setStrokeColor(colors.HexColor("#E5E7EB"))
# #         canvas.line(doc.leftMargin, 36, doc.leftMargin + doc.width, 36)
# #         canvas.setFont("Helvetica", 9)
# #         canvas.setFillColor(colors.HexColor("#6B7280"))
# #         canvas.drawRightString(doc.leftMargin + doc.width, 24, f"Page {doc.page}")
# #         canvas.restoreState()
# #     return draw

# # # -------------------------------
# # # Helpers
# # # -------------------------------
# # def _first_heading(text: str):
# #     for ln in text.splitlines():
# #         if ln.startswith("# "):
# #             return ln[2:].strip()
# #     return None

# # def _escape_html(s: str) -> str:
# #     return (
# #         s.replace("&", "&amp;")
# #          .replace("<", "&lt;")
# #          .replace(">", "&gt;")
# #     )

# # def _mk_para(text: str, styles):
# #     return Paragraph(_escape_html(text), styles["ProBody"])

# # def _is_alignment_row(cells):
# #     # markdown alignment row: ---  :---  ---:  :---:
# #     return all(re.match(r"^:?-{3,}:?$", c) for c in cells)

# # def _string_width_pt(s: str, font="Helvetica", size=9.5):
# #     return stringWidth(s or "", font, size)

# # # -------------------------------
# # # Table rendering with wrapping & horizontal splitting
# # # -------------------------------
# # def _render_markdown_table(story, rows_raw, styles, page_width_pt):
# #     """
# #     rows_raw: list[list[str]]
# #     If the table is too wide, split into column chunks that fit the available width.
# #     """
# #     if not rows_raw:
# #         return

# #     # Clean: drop alignment row if present as 2nd line
# #     rows = [list(r) for r in rows_raw]
# #     if len(rows) >= 2 and _is_alignment_row(rows[1]):
# #         rows = [rows[0]] + rows[2:]

# #     if not rows:
# #         return

# #     ncols = max(len(r) for r in rows)
# #     # normalize rows to same column count
# #     for r in rows:
# #         if len(r) < ncols:
# #             r += [""] * (ncols - len(r))

# #     # Convert to Paragraph cells to enable wrapping
# #     def rows_to_paragraphs(subcols):
# #         # subcols: list of column indices to include
# #         data = []
# #         for i, r in enumerate(rows):
# #             row_cells = []
# #             for j in subcols:
# #                 txt = r[j]
# #                 # header row stays normal; style will bold it
# #                 row_cells.append(_mk_para(str(txt), styles))
# #             data.append(row_cells)
# #         return data

# #     # Estimate how many columns fit: use minimal column width heuristic
# #     avail = page_width_pt  # doc.width
# #     min_col = 60  # points (~0.83in)
# #     max_cols_fit = max(1, int(avail // min_col))

# #     # If columns exceed what fits, split into chunks
# #     if ncols > max_cols_fit:
# #         chunks = []
# #         start = 0
# #         while start < ncols:
# #             end = min(start + max_cols_fit, ncols)
# #             chunks.append(list(range(start, end)))
# #             start = end
# #     else:
# #         # try finer sizing based on content width to avoid overly squished columns
# #         # compute naive widths using header + some row samples
# #         text_widths = [0] * ncols
# #         sample_rows = rows[: min(10, len(rows))]
# #         for r in sample_rows:
# #             for j, cell in enumerate(r):
# #                 text_widths[j] = max(text_widths[j], _string_width_pt(str(cell)))
# #         # add padding
# #         text_widths = [w + 20 for w in text_widths]  # padding per col
# #         total = sum(text_widths)
# #         # scale to available width if needed
# #         if total > avail:
# #             scale = avail / total
# #             col_widths = [max(min_col, w * scale) for w in text_widths]
# #         else:
# #             col_widths = text_widths
# #         chunks = [list(range(ncols))]
# #         chunk_widths = [col_widths]

# #     # Render each chunk as a separate table, repeating the header
# #     for idx, col_idx in enumerate(chunks):
# #         data = rows_to_paragraphs(col_idx)

# #         # Compute colWidths for this chunk if not computed above
# #         if ncols <= max_cols_fit:
# #             col_widths = chunk_widths[0]
# #             use_widths = [col_widths[j] for j in col_idx]
# #         else:
# #             # Even split for chunked tables
# #             even = avail / len(col_idx)
# #             use_widths = [even] * len(col_idx)

# #         tbl = Table(data, colWidths=use_widths, hAlign="LEFT")
# #         tbl.setStyle(TableStyle([
# #             ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#E5E7EB")),
# #             ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
# #             ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
# #             ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
# #             ('FONTSIZE', (0, 0), (-1, -1), 9.5),
# #             ('TOPPADDING', (0, 0), (-1, -1), 4),
# #             ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
# #             ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
# #             # Enable wrapping inside cells:
# #             ('WORDWRAP', (0, 0), (-1, -1), 'CJK'),
# #         ]))
# #         story.append(tbl)
# #         story.append(Spacer(1, 6))

# # # -------------------------------
# # # Parse content -> flowables
# # # -------------------------------
# # def _parse_content_to_story(content, styles, doc_title, page_width_pt):
# #     story = []
# #     lines = content.splitlines()
# #     in_code = False
# #     code_buffer = []

# #     bullet_buffer = []    # collect bullet lines
# #     numbered_buffer = []  # collect numbered lines
# #     table_buffer = []     # collect markdown table rows

# #     def flush_bullets():
# #         nonlocal bullet_buffer
# #         if bullet_buffer:
# #             items = []
# #             for t in bullet_buffer:
# #                 # strip bullet marker
# #                 text = re.sub(r"^[-*•]\s+", "", t).strip()
# #                 # if bold marker like **Title** :
# #                 m = re.match(r"^\*\*(.+?)\*\*\s*:?\s*$", text)
# #                 if m:
# #                     para = Paragraph(f"<b>{_escape_html(m.group(1))}</b>", styles["ProBody"])
# #                 else:
# #                     para = Paragraph(_escape_html(text), styles["ProBody"])
# #                 items.append(ListItem(para, bulletText="•"))
# #             story.append(ListFlowable(items, bulletType="bullet", leftIndent=18, bulletFontName="Helvetica"))
# #             bullet_buffer = []

# #     def flush_numbered():
# #         nonlocal numbered_buffer
# #         if numbered_buffer:
# #             items = []
# #             for t in numbered_buffer:
# #                 # strip "1. " or "1 "
# #                 text = re.sub(r"^\d+\.?\s+", "", t).strip()
# #                 m = re.match(r"^\*\*(.+?)\*\*\s*:?\s*$", text)
# #                 if m:
# #                     para = Paragraph(f"<b>{_escape_html(m.group(1))}</b>", styles["ProBody"])
# #                 else:
# #                     para = Paragraph(_escape_html(text), styles["ProBody"])
# #                 items.append(ListItem(para))
# #             story.append(ListFlowable(items, bulletType="1", start="1", leftIndent=18, bulletFontName="Helvetica"))
# #             numbered_buffer = []

# #     def flush_table():
# #         nonlocal table_buffer
# #         if table_buffer:
# #             _render_markdown_table(story, table_buffer, styles, page_width_pt)
# #             table_buffer = []

# #     # Cover page
# #     title = _first_heading(content) or doc_title
# #     story.append(Spacer(1, 0.6 * inch))
# #     story.append(Paragraph(title, styles["ProTitle"]))
# #     story.append(Paragraph(datetime.now().strftime("%B %d, %Y"), styles["ProSubtitle"]))
# #     story.append(Spacer(1, 0.2 * inch))

# #     for raw in lines:
# #         line = raw.rstrip()

# #         # Blank line => flush lists/tables and add space
# #         if not line.strip():
# #             flush_table()
# #             flush_bullets()
# #             flush_numbered()
# #             story.append(Spacer(1, 6))
# #             continue

# #         # Markdown table row?
# #         if line.strip().startswith("|") and "|" in line[1:]:
# #             cells = [c.strip() for c in line.strip().strip("|").split("|")]
# #             table_buffer.append(cells)
# #             continue
# #         else:
# #             # leaving table region
# #             flush_table()

# #         # Page break control
# #         if "\f" in line:
# #             flush_bullets(); flush_numbered()
# #             if in_code and code_buffer:
# #                 story.append(Preformatted("\n".join(code_buffer), styles["ProCode"]))
# #                 code_buffer = []
# #                 in_code = False
# #             story.append(PageBreak())
# #             continue

# #         # Code fences
# #         if line.strip().startswith("```"):
# #             if not in_code:
# #                 in_code = True
# #                 code_buffer = []
# #             else:
# #                 story.append(Preformatted("\n".join(code_buffer), styles["ProCode"]))
# #                 code_buffer = []
# #                 in_code = False
# #             continue
# #         if in_code:
# #             code_buffer.append(line)
# #             continue

# #         # Bold-only line, e.g., "**Indian Wind Energy Installed Capacity Projections (GW)** :"
# #         if re.match(r"^\*\*.+\*\*\s*:\s*$", line):
# #             flush_bullets(); flush_numbered()
# #             bold_text = re.sub(r"^\*\*(.+)\*\*.*", r"\1", line).strip()
# #             story.append(Paragraph(f"<b>{_escape_html(bold_text)}</b>", styles["ProBody"]))
# #             continue

# #         # Headings
# #         if line.startswith("# "):
# #             flush_bullets(); flush_numbered()
# #             story.append(Paragraph(line[2:].strip(), styles["ProH1"]))
# #             continue
# #         if line.startswith("## "):
# #             flush_bullets(); flush_numbered()
# #             story.append(Paragraph(line[3:].strip(), styles["ProH2"]))
# #             continue
# #         if line.startswith("### "):
# #             flush_bullets(); flush_numbered()
# #             story.append(Paragraph(line[4:].strip(": ").strip(), styles["ProH2"]))
# #             continue
# #         if line.startswith("#### "):
# #             flush_bullets(); flush_numbered()
# #             # e.g., "#### 4.1. Market Trends  :" -> bold subheader
# #             story.append(Paragraph(line[5:].strip(": ").strip(), styles["ProH3"]))
# #             continue

# #         # Bullets / Numbered
# #         if re.match(r"^[-*•]\s+\S", line):
# #             numbered_buffer = []
# #             bullet_buffer.append(line)
# #             continue
# #         if re.match(r"^\d+\.?\s+\S", line):
# #             bullet_buffer = []
# #             numbered_buffer.append(line)
# #             continue

# #         # Normal paragraph
# #         flush_bullets(); flush_numbered()
# #         story.append(Paragraph(_escape_html(line), styles["ProBody"]))

# #     # Tail flush
# #     flush_table()
# #     flush_bullets()
# #     flush_numbered()
# #     if in_code and code_buffer:
# #         story.append(Preformatted("\n".join(code_buffer), styles["ProCode"]))
# #     return story

# # # -------------------------------
# # # Public API
# # # -------------------------------
# # def save_to_pdf(content: str, filename: str) -> str:
# #     """Save provided content to a professionally formatted PDF file (Landscape A4)."""
# #     try:
# #         if not filename.lower().endswith(".pdf"):
# #             filename += ".pdf"

# #         # ensure parent folder exists
# #         parent = os.path.dirname(os.path.abspath(filename))
# #         if parent and not os.path.exists(parent):
# #             os.makedirs(parent, exist_ok=True)

# #         # Title from filename (fallback)
# #         title_from_name = os.path.splitext(os.path.basename(filename))[0].replace("_", " ").title()

# #         styles = _build_styles()

# #         # NOTE: Landscape A4 as requested
# #         doc = SimpleDocTemplate(
# #             filename,
# #             pagesize=landscape(A4),
# #             leftMargin=0.9 * inch,
# #             rightMargin=0.9 * inch,
# #             topMargin=0.8 * inch,
# #             bottomMargin=0.8 * inch,
# #             title=title_from_name,
# #             author="GenIntel Report Generator",
# #             subject="Analyst Report",
# #             creator="GenIntel MCP",
# #         )

# #         # Build story with doc width available for smart table splitting
# #         story = _parse_content_to_story(content, styles, title_from_name, doc.width)

# #         header_cb = _header_footer(title_from_name)
# #         doc.build(story, onFirstPage=header_cb, onLaterPages=header_cb)

# #         return f"✅ PDF saved as {filename}"
# #     except Exception as e:
# #         return f"❌ PDF Save Error: {str(e)}"



# # utils/Report_Save_to_pdf.py

# from reportlab.platypus import (
#     SimpleDocTemplate, Paragraph, Spacer, PageBreak, ListFlowable, ListItem,
#     Preformatted, Table, TableStyle
# )
# from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
# from reportlab.lib.enums import TA_LEFT, TA_CENTER
# from reportlab.lib.pagesizes import A4, landscape
# from reportlab.lib.units import inch
# from reportlab.lib import colors
# from reportlab.pdfbase.pdfmetrics import stringWidth
# from datetime import datetime
# import os
# import re

# # -------------------------------
# # Styles (unique names)
# # -------------------------------
# def _build_styles():
#     styles = getSampleStyleSheet()

#     def add_style(name, **kwargs):
#         if name in styles:
#             del styles[name]
#         styles.add(ParagraphStyle(name=name, **kwargs))

#     base = styles["Normal"]
#     add_style(
#         "ProBody",
#         parent=base,
#         fontName="Helvetica",
#         fontSize=10.5,
#         leading=15,
#         spaceAfter=6,
#         textColor=colors.HexColor("#1F2937"),
#     )
#     add_style(
#         "ProH1",
#         parent=base,
#         fontName="Helvetica-Bold",
#         fontSize=18,
#         leading=24,
#         spaceBefore=6,
#         spaceAfter=10,
#         alignment=TA_LEFT,
#         textColor=colors.HexColor("#0F172A"),
#     )
#     add_style(
#         "ProH2",
#         parent=base,
#         fontName="Helvetica-Bold",
#         fontSize=14,
#         leading=20,
#         spaceBefore=12,
#         spaceAfter=6,
#         textColor=colors.HexColor("#111827"),
#     )
#     add_style(
#         "ProH3",
#         parent=base,
#         fontName="Helvetica-Bold",
#         fontSize=12.5,
#         leading=18,
#         spaceBefore=10,
#         spaceAfter=6,
#         textColor=colors.HexColor("#111827"),
#     )
#     add_style(
#         "ProBullet",
#         parent=base,
#         fontName="Helvetica",
#         fontSize=10.5,
#         leading=15,
#         leftIndent=14,
#         bulletIndent=6,
#         spaceAfter=3,
#         textColor=colors.HexColor("#1F2937"),
#     )
#     add_style(
#         "ProCode",
#         parent=base,
#         fontName="Courier",
#         fontSize=9.5,
#         leading=14,
#         backColor=colors.whitesmoke,
#         leftIndent=6,
#         rightIndent=6,
#         spaceBefore=6,
#         spaceAfter=6,
#         borderWidth=0.5,
#         borderColor=colors.HexColor("#E5E7EB"),
#         borderPadding=6,
#     )
#     add_style(
#         "ProTitle",
#         parent=base,
#         fontName="Helvetica-Bold",
#         fontSize=22,
#         leading=28,
#         alignment=TA_CENTER,
#         spaceAfter=14,
#         textColor=colors.HexColor("#0F172A"),
#     )
#     add_style(
#         "ProSubtitle",
#         parent=base,
#         fontName="Helvetica",
#         fontSize=11.5,
#         leading=16,
#         alignment=TA_CENTER,
#         textColor=colors.HexColor("#4B5563"),
#         spaceAfter=18,
#     )
#     add_style(
#         "ProCaption",
#         parent=base,
#         fontName="Helvetica-Oblique",
#         fontSize=9.5,
#         leading=13,
#         textColor=colors.HexColor("#374151"),
#         spaceBefore=2,
#         spaceAfter=6,
#     )
#     return styles

# # -------------------------------
# # Header / footer
# # -------------------------------
# def _header_footer(title):
#     def draw(canvas, doc):
#         canvas.saveState()
#         # top rule
#         canvas.setStrokeColor(colors.HexColor("#E5E7EB"))
#         canvas.setLineWidth(0.5)
#         y_top = doc.height + doc.topMargin + 18
#         canvas.line(doc.leftMargin, y_top, doc.leftMargin + doc.width, y_top)
#         # header text
#         canvas.setFont("Helvetica", 9)
#         canvas.setFillColor(colors.HexColor("#6B7280"))
#         canvas.drawString(doc.leftMargin, y_top + 4, title[:80])
#         # bottom rule
#         canvas.setStrokeColor(colors.HexColor("#E5E7EB"))
#         canvas.line(doc.leftMargin, 36, doc.leftMargin + doc.width, 36)
#         # page number
#         canvas.setFont("Helvetica", 9)
#         canvas.setFillColor(colors.HexColor("#6B7280"))
#         canvas.drawRightString(doc.leftMargin + doc.width, 24, f"Page {doc.page}")
#         canvas.restoreState()
#     return draw

# # -------------------------------
# # Helpers
# # -------------------------------
# def _first_heading(text: str):
#     for ln in text.splitlines():
#         if ln.startswith("# "):
#             return ln[2:].strip()
#     return None

# def _escape_html(s: str) -> str:
#     return (
#         s.replace("&", "&amp;")
#          .replace("<", "&lt;")
#          .replace(">", "&gt;")
#     )

# def _inline_bold(md_text: str) -> str:
#     """
#     Convert **bold** markdown to <b>bold</b>.
#     Run AFTER HTML escaping.
#     """
#     # Replace **...** with <b>...</b> (non-greedy)
#     return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", md_text)

# def _to_paragraph_html(text: str) -> str:
#     return _inline_bold(_escape_html(text))

# def _mk_para(text: str, styles):
#     return Paragraph(_to_paragraph_html(text), styles["ProBody"])

# def _is_alignment_row(cells):
#     # markdown alignment row: ---  :---  ---:  :---:
#     return all(re.match(r"^:?-{3,}:?$", c) for c in cells)

# def _string_width_pt(s: str, font="Helvetica", size=9.5):
#     return stringWidth(s or "", font, size)

# # -------------------------------
# # Table rendering with wrapping & horizontal splitting
# # -------------------------------
# def _render_markdown_table(story, rows_raw, styles, page_width_pt):
#     """
#     rows_raw: list[list[str]]
#     If the table is too wide, split into column chunks that fit the available width.
#     Bold inside cells via **...** is supported.
#     """
#     if not rows_raw:
#         return

#     # Drop alignment row if present as 2nd line
#     rows = [list(r) for r in rows_raw]
#     if len(rows) >= 2 and _is_alignment_row(rows[1]):
#         rows = [rows[0]] + rows[2:]
#     if not rows:
#         return

#     ncols = max(len(r) for r in rows)
#     # normalize rows to uniform column count
#     for r in rows:
#         if len(r) < ncols:
#             r += [""] * (ncols - len(r))

#     # Convert to Paragraph cells with inline bold support
#     def rows_to_paragraphs(subcols):
#         data = []
#         for i, r in enumerate(rows):
#             row_cells = []
#             for j in subcols:
#                 txt = str(r[j])
#                 row_cells.append(Paragraph(_to_paragraph_html(txt), styles["ProBody"]))
#             data.append(row_cells)
#         return data

#     # Estimate how many columns fit using a minimal width heuristic
#     avail = page_width_pt
#     min_col = 60  # pt (~0.83in)
#     max_cols_fit = max(1, int(avail // min_col))

#     # Split into column chunks when needed
#     if ncols > max_cols_fit:
#         chunks = []
#         start = 0
#         while start < ncols:
#             end = min(start + max_cols_fit, ncols)
#             chunks.append(list(range(start, end)))
#             start = end
#         chunk_widths = None
#     else:
#         # Fit columns by content width (header + sample rows)
#         text_widths = [0] * ncols
#         sample_rows = rows[: min(10, len(rows))]
#         for r in sample_rows:
#             for j, cell in enumerate(r):
#                 # estimate width of raw text (approx)
#                 text_widths[j] = max(text_widths[j], _string_width_pt(str(cell)))
#         text_widths = [w + 20 for w in text_widths]  # padding per col
#         total = sum(text_widths)
#         if total > avail:
#             scale = avail / total
#             col_widths = [max(min_col, w * scale) for w in text_widths]
#         else:
#             col_widths = text_widths
#         chunks = [list(range(ncols))]
#         chunk_widths = [col_widths]

#     # Render each chunk as its own table, repeating header row
#     for idx, col_idx in enumerate(chunks):
#         data = rows_to_paragraphs(col_idx)
#         if chunk_widths:
#             col_widths = chunk_widths[0]
#             use_widths = [col_widths[j] for j in col_idx]
#         else:
#             even = avail / len(col_idx)
#             use_widths = [even] * len(col_idx)

#         tbl = Table(data, colWidths=use_widths, hAlign="LEFT")
#         tbl.setStyle(TableStyle([
#             ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#E5E7EB")),
#             ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
#             ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
#             ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
#             ('FONTSIZE', (0, 0), (-1, -1), 9.5),
#             ('TOPPADDING', (0, 0), (-1, -1), 4),
#             ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
#             ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
#             # Enable wrapping inside cells:
#             ('WORDWRAP', (0, 0), (-1, -1), 'CJK'),
#         ]))
#         story.append(tbl)
#         story.append(Spacer(1, 6))

# # -------------------------------
# # Parse content -> flowables
# # -------------------------------
# def _parse_content_to_story(content, styles, doc_title, page_width_pt):
#     story = []
#     lines = content.splitlines()
#     in_code = False
#     code_buffer = []

#     bullet_buffer = []    # collect bullet lines
#     numbered_buffer = []  # collect numbered lines
#     table_buffer = []     # collect markdown table rows

#     def flush_bullets():
#         nonlocal bullet_buffer
#         if bullet_buffer:
#             items = []
#             for t in bullet_buffer:
#                 # strip bullet marker
#                 text = re.sub(r"^[-*•]\s+", "", t).strip()
#                 # Convert inline bold anywhere in the line
#                 para = Paragraph(_to_paragraph_html(text), styles["ProBody"])
#                 items.append(ListItem(para, bulletText="•"))
#             story.append(ListFlowable(items, bulletType="bullet", leftIndent=18, bulletFontName="Helvetica"))
#             bullet_buffer = []

#     def flush_numbered():
#         nonlocal numbered_buffer
#         if numbered_buffer:
#             items = []
#             for t in numbered_buffer:
#                 # strip "1. " or "2 " etc.
#                 text = re.sub(r"^\d+\.?\s+", "", t).strip()
#                 para = Paragraph(_to_paragraph_html(text), styles["ProBody"])
#                 items.append(ListItem(para))
#             story.append(ListFlowable(items, bulletType="1", start="1", leftIndent=18, bulletFontName="Helvetica"))
#             numbered_buffer = []

#     def flush_table():
#         nonlocal table_buffer
#         if table_buffer:
#             _render_markdown_table(story, table_buffer, styles, page_width_pt)
#             table_buffer = []

#     # Cover page
#     title = _first_heading(content) or doc_title
#     story.append(Spacer(1, 0.6 * inch))
#     story.append(Paragraph(title, styles["ProTitle"]))
#     story.append(Paragraph(datetime.now().strftime("%B %d, %Y"), styles["ProSubtitle"]))
#     story.append(Spacer(1, 0.2 * inch))

#     for raw in lines:
#         line = raw.rstrip()

#         # Blank line => flush lists/tables and add space
#         if not line.strip():
#             flush_table()
#             flush_bullets()
#             flush_numbered()
#             story.append(Spacer(1, 6))
#             continue

#         # Markdown table row?
#         if line.strip().startswith("|") and "|" in line[1:]:
#             cells = [c.strip() for c in line.strip().strip("|").split("|")]
#             table_buffer.append(cells)
#             continue
#         else:
#             # leaving table region
#             flush_table()

#         # Page break control
#         if "\f" in line:
#             flush_bullets(); flush_numbered()
#             if in_code and code_buffer:
#                 story.append(Preformatted("\n".join(code_buffer), styles["ProCode"]))
#                 code_buffer = []
#                 in_code = False
#             story.append(PageBreak())
#             continue

#         # Code fences
#         if line.strip().startswith("```"):
#             if not in_code:
#                 in_code = True
#                 code_buffer = []
#             else:
#                 story.append(Preformatted("\n".join(code_buffer), styles["ProCode"]))
#                 code_buffer = []
#                 in_code = False
#             continue
#         if in_code:
#             code_buffer.append(line)
#             continue

#         # Bold-only line, e.g., "**Title** :" — render bold paragraph
#         if re.match(r"^\*\*.+\*\*\s*:\s*$", line):
#             flush_bullets(); flush_numbered()
#             # Keep inline bold conversion to preserve any **...** span
#             story.append(Paragraph(_to_paragraph_html(line.strip().rstrip(":")), styles["ProBody"]))
#             continue

#         # Headings
#         if line.startswith("# "):
#             flush_bullets(); flush_numbered()
#             story.append(Paragraph(_to_paragraph_html(line[2:].strip()), styles["ProH1"]))
#             continue
#         if line.startswith("## "):
#             flush_bullets(); flush_numbered()
#             story.append(Paragraph(_to_paragraph_html(line[3:].strip()), styles["ProH2"]))
#             continue
#         if line.startswith("### "):
#             flush_bullets(); flush_numbered()
#             # e.g., "### 2. Market Overview and Growth Projections:"
#             story.append(Paragraph(_to_paragraph_html(line[4:].strip(": ").strip()), styles["ProH2"]))
#             continue
#         if line.startswith("#### "):
#             flush_bullets(); flush_numbered()
#             # e.g., "#### 4.1. Market Trends  :"
#             story.append(Paragraph(_to_paragraph_html(line[5:].strip(": ").strip()), styles["ProH3"]))
#             continue

#         # Bullets / Numbered (with inline bold support)
#         if re.match(r"^[-*•]\s+\S", line):
#             numbered_buffer = []
#             bullet_buffer.append(line)
#             continue
#         if re.match(r"^\d+\.?\s+\S", line):
#             bullet_buffer = []
#             numbered_buffer.append(line)
#             continue

#         # Normal paragraph (with inline bold support)
#         flush_bullets(); flush_numbered()
#         story.append(Paragraph(_to_paragraph_html(line), styles["ProBody"]))

#     # Tail flushes
#     flush_table()
#     flush_bullets()
#     flush_numbered()
#     if in_code and code_buffer:
#         story.append(Preformatted("\n".join(code_buffer), styles["ProCode"]))
#     return story

# # -------------------------------
# # Public API
# # -------------------------------
# def save_to_pdf(content: str, filename: str) -> str:
#     """Save provided content to a professionally formatted PDF file (Landscape A4)."""
#     try:
#         if not filename.lower().endswith(".pdf"):
#             filename += ".pdf"

#         # ensure parent folder exists
#         parent = os.path.dirname(os.path.abspath(filename))
#         if parent and not os.path.exists(parent):
#             os.makedirs(parent, exist_ok=True)

#         # Title from filename (fallback)
#         title_from_name = os.path.splitext(os.path.basename(filename))[0].replace("_", " ").title()

#         styles = _build_styles()

#         # Landscape A4
#         doc = SimpleDocTemplate(
#             filename,
#             pagesize=landscape(A4),
#             leftMargin=0.9 * inch,
#             rightMargin=0.9 * inch,
#             topMargin=0.8 * inch,
#             bottomMargin=0.8 * inch,
#             title=title_from_name,
#             author="GenIntel Report Generator",
#             subject="Analyst Report",
#             creator="GenIntel MCP",
#         )

#         # Build story with doc width (for table splitting)
#         story = _parse_content_to_story(content, styles, title_from_name, doc.width)

#         header_cb = _header_footer(title_from_name)
#         doc.build(story, onFirstPage=header_cb, onLaterPages=header_cb)

#         return f"✅ PDF saved as {filename}"
#     except Exception as e:
#         return f"❌ PDF Save Error: {str(e)}"



# utils/Report_Save_to_pdf.py

from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, ListFlowable, ListItem,
    Preformatted, Table, TableStyle, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.pdfbase.pdfmetrics import stringWidth
from datetime import datetime
import os
import re

# -------------------------------
# Styles (unique names)
# -------------------------------
def _build_styles():
    styles = getSampleStyleSheet()

    def add_style(name, **kwargs):
        if name in styles:
            del styles[name]
        styles.add(ParagraphStyle(name=name, **kwargs))

    base = styles["Normal"]
    add_style(
        "ProBody",
        parent=base,
        fontName="Helvetica",
        fontSize=10.5,
        leading=15,
        spaceAfter=6,
        textColor=colors.HexColor("#1F2937"),
    )
    add_style(
        "ProH1",
        parent=base,
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=24,
        spaceBefore=6,
        spaceAfter=10,
        alignment=TA_LEFT,
        textColor=colors.HexColor("#0F172A"),
    )
    add_style(
        "ProH2",
        parent=base,
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=20,
        spaceBefore=12,
        spaceAfter=6,
        textColor=colors.HexColor("#111827"),
    )
    add_style(
        "ProH3",
        parent=base,
        fontName="Helvetica-Bold",
        fontSize=12.5,
        leading=18,
        spaceBefore=10,
        spaceAfter=6,
        textColor=colors.HexColor("#111827"),
    )
    add_style(
        "ProBullet",
        parent=base,
        fontName="Helvetica",
        fontSize=10.5,
        leading=15,
        leftIndent=14,
        bulletIndent=6,
        spaceAfter=3,
        textColor=colors.HexColor("#1F2937"),
    )
    add_style(
        "ProCode",
        parent=base,
        fontName="Courier",
        fontSize=9.5,
        leading=14,
        backColor=colors.whitesmoke,
        leftIndent=6,
        rightIndent=6,
        spaceBefore=6,
        spaceAfter=6,
        borderWidth=0.5,
        borderColor=colors.HexColor("#E5E7EB"),
        borderPadding=6,
    )
    add_style(
        "ProTitle",
        parent=base,
        fontName="Helvetica-Bold",
        fontSize=22,
        leading=28,
        alignment=TA_CENTER,
        spaceAfter=14,
        textColor=colors.HexColor("#0F172A"),
    )
    add_style(
        "ProSubtitle",
        parent=base,
        fontName="Helvetica",
        fontSize=11.5,
        leading=16,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#4B5563"),
        spaceAfter=18,
    )
    add_style(
        "ProCaption",
        parent=base,
        fontName="Helvetica-Oblique",
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor("#374151"),
        spaceBefore=2,
        spaceAfter=6,
    )
    return styles

# -------------------------------
# Header / footer
# -------------------------------
def _header_footer(title):
    def draw(canvas, doc):
        canvas.saveState()
        # top rule
        canvas.setStrokeColor(colors.HexColor("#E5E7EB"))
        canvas.setLineWidth(0.5)
        y_top = doc.height + doc.topMargin + 18
        canvas.line(doc.leftMargin, y_top, doc.leftMargin + doc.width, y_top)
        # header text
        canvas.setFont("Helvetica", 9)
        canvas.setFillColor(colors.HexColor("#6B7280"))
        canvas.drawString(doc.leftMargin, y_top + 4, title[:80])
        # bottom rule
        canvas.setStrokeColor(colors.HexColor("#E5E7EB"))
        canvas.line(doc.leftMargin, 36, doc.leftMargin + doc.width, 36)
        # page number
        canvas.setFont("Helvetica", 9)
        canvas.setFillColor(colors.HexColor("#6B7280"))
        canvas.drawRightString(doc.leftMargin + doc.width, 24, f"Page {doc.page}")
        canvas.restoreState()
    return draw

# -------------------------------
# Helpers
# -------------------------------
def _first_heading(text: str):
    for ln in text.splitlines():
        if ln.startswith("# "):
            return ln[2:].strip()
    return None

def _escape_html(s: str) -> str:
    return (
        s.replace("&", "&amp;")
         .replace("<", "&lt;")
         .replace(">", "&gt;")
    )

def _inline_bold(md_text: str) -> str:
    """
    Convert **bold** markdown to <b>bold</b>.
    Run AFTER HTML escaping.
    """
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", md_text)

# def _to_paragraph_html(text: str) -> str:
#     return _inline_bold(_escape_html(text))

def _normalize_currency(text: str) -> str:
    return text.replace("₹", "₹ ")

def _to_paragraph_html(text: str) -> str:
    text = _normalize_currency(text)
    return _inline_bold(_escape_html(text))

def _mk_para(text: str, styles):
    return Paragraph(_to_paragraph_html(text), styles["ProBody"])

def _is_alignment_row(cells):
    # markdown alignment row: ---  :---  ---:  :---:
    return all(re.match(r"^:?-{3,}:?$", c) for c in cells)

def _string_width_pt(s: str, font="Helvetica", size=9.5):
    return stringWidth(s or "", font, size)

# -------------------------------
# Table rendering with wrapping & horizontal splitting
# -------------------------------
def _render_markdown_table(story, rows_raw, styles, page_width_pt):
    """
    rows_raw: list[list[str]]
    If the table is too wide, split into column chunks that fit the available width.
    Bold inside cells via **...** is supported.
    """
    if not rows_raw:
        return

    # Drop alignment row if present as 2nd line
    rows = [list(r) for r in rows_raw]
    if len(rows) >= 2 and _is_alignment_row(rows[1]):
        rows = [rows[0]] + rows[2:]
    if not rows:
        return

    ncols = max(len(r) for r in rows)
    # normalize rows to uniform column count
    for r in rows:
        if len(r) < ncols:
            r += [""] * (ncols - len(r))

    # Convert to Paragraph cells with inline bold support
    def rows_to_paragraphs(subcols):
        data = []
        for i, r in enumerate(rows):
            row_cells = []
            for j in subcols:
                txt = str(r[j])
                row_cells.append(Paragraph(_to_paragraph_html(txt), styles["ProBody"]))
            data.append(row_cells)
        return data

    # Estimate how many columns fit using a minimal width heuristic
    avail = page_width_pt
    min_col = 60  # pt (~0.83in)
    max_cols_fit = max(1, int(avail // min_col))

    # Split into column chunks when needed
    if ncols > max_cols_fit:
        chunks = []
        start = 0
        while start < ncols:
            end = min(start + max_cols_fit, ncols)
            chunks.append(list(range(start, end)))
            start = end
        chunk_widths = None
    else:
        # Fit columns by content width (header + sample rows)
        text_widths = [0] * ncols
        sample_rows = rows[: min(10, len(rows))]
        for r in sample_rows:
            for j, cell in enumerate(r):
                text_widths[j] = max(text_widths[j], _string_width_pt(str(cell)))
        text_widths = [w + 20 for w in text_widths]  # padding per col
        total = sum(text_widths)
        if total > avail:
            scale = avail / total
            col_widths = [max(min_col, w * scale) for w in text_widths]
        else:
            col_widths = text_widths
        chunks = [list(range(ncols))]
        chunk_widths = [col_widths]

    # Render each chunk as its own table, repeating header row
    for idx, col_idx in enumerate(chunks):
        data = rows_to_paragraphs(col_idx)
        if chunk_widths:
            col_widths = chunk_widths[0]
            use_widths = [col_widths[j] for j in col_idx]
        else:
            even = avail / len(col_idx)
            use_widths = [even] * len(col_idx)

        tbl = Table(data, colWidths=use_widths, hAlign="LEFT")
        tbl.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#E5E7EB")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9.5),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            # Enable wrapping inside cells:
            ('WORDWRAP', (0, 0), (-1, -1), 'CJK'),
        ]))
        story.append(tbl)
        story.append(Spacer(1, 6))

# -------------------------------
# Parse content -> flowables
# -------------------------------
def _parse_content_to_story(content, styles, doc_title, page_width_pt):
    story = []
    lines = content.splitlines()
    in_code = False
    code_buffer = []

    bullet_buffer = []    # collect bullet lines
    numbered_buffer = []  # collect numbered lines
    table_buffer = []     # collect markdown table rows

    def flush_bullets():
        nonlocal bullet_buffer
        if bullet_buffer:
            items = []
            for t in bullet_buffer:
                # strip bullet marker
                text = re.sub(r"^[-*•]\s+", "", t).strip()
                # inline bold conversion anywhere
                para = Paragraph(_to_paragraph_html(text), styles["ProBody"])
                items.append(ListItem(para, bulletText="•"))
            story.append(ListFlowable(items, bulletType="bullet", leftIndent=18, bulletFontName="Helvetica"))
            bullet_buffer = []

    def flush_numbered():
        nonlocal numbered_buffer
        if numbered_buffer:
            items = []
            for t in numbered_buffer:
                # strip "1. " or "2 " etc.
                text = re.sub(r"^\d+\.?\s+", "", t).strip()
                para = Paragraph(_to_paragraph_html(text), styles["ProBody"])
                items.append(ListItem(para))
            story.append(ListFlowable(items, bulletType="1", start="1", leftIndent=18, bulletFontName="Helvetica"))
            numbered_buffer = []

    def flush_table():
        nonlocal table_buffer
        if table_buffer:
            _render_markdown_table(story, table_buffer, styles, page_width_pt)
            table_buffer = []

    # Cover page
    title = _first_heading(content) or doc_title
    story.append(Spacer(1, 0.6 * inch))
    story.append(Paragraph(title, styles["ProTitle"]))
    story.append(Paragraph(datetime.now().strftime("%B %d, %Y"), styles["ProSubtitle"]))
    story.append(Spacer(1, 0.2 * inch))

    for raw in lines:
        line = raw.rstrip()

        # Blank line => flush lists/tables and add space
        if not line.strip():
            flush_table()
            flush_bullets()
            flush_numbered()
            story.append(Spacer(1, 6))
            continue

        # Markdown table row?
        if line.strip().startswith("|") and "|" in line[1:]:
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            table_buffer.append(cells)
            continue
        else:
            # leaving table region
            flush_table()

        # Horizontal rule: line "---" -> draw a light line
        if re.match(r"^\s*---\s*$", line):
            flush_bullets(); flush_numbered()
            story.append(HRFlowable(width="100%", thickness=0.6,
                                    color=colors.HexColor("#E5E7EB"),
                                    spaceBefore=6, spaceAfter=6))
            continue

        # Page break control
        if "\f" in line:
            flush_bullets(); flush_numbered()
            if in_code and code_buffer:
                story.append(Preformatted("\n".join(code_buffer), styles["ProCode"]))
                code_buffer = []
                in_code = False
            story.append(PageBreak())
            continue

        # Code fences
        if line.strip().startswith("```"):
            if not in_code:
                in_code = True
                code_buffer = []
            else:
                story.append(Preformatted("\n".join(code_buffer), styles["ProCode"]))
                code_buffer = []
                in_code = False
            continue
        if in_code:
            code_buffer.append(line)
            continue

        # Bold-only line, e.g., "**Title** :" — render bold paragraph
        if re.match(r"^\*\*.+\*\*\s*:\s*$", line):
            flush_bullets(); flush_numbered()
            story.append(Paragraph(_to_paragraph_html(line.strip().rstrip(":")), styles["ProBody"]))
            continue

        # Headings
        if line.startswith("# "):
            flush_bullets(); flush_numbered()
            story.append(Paragraph(_to_paragraph_html(line[2:].strip()), styles["ProH1"]))
            continue
        if line.startswith("## "):
            flush_bullets(); flush_numbered()
            story.append(Paragraph(_to_paragraph_html(line[3:].strip()), styles["ProH2"]))
            continue
        if line.startswith("### "):
            flush_bullets(); flush_numbered()
            story.append(Paragraph(_to_paragraph_html(line[4:].strip(": ").strip()), styles["ProH2"]))
            continue
        if line.startswith("#### "):
            flush_bullets(); flush_numbered()
            story.append(Paragraph(_to_paragraph_html(line[5:].strip(": ").strip()), styles["ProH3"]))
            continue

        # Bullets / Numbered (with inline bold support)
        if re.match(r"^[-*•]\s+\S", line):
            numbered_buffer = []
            bullet_buffer.append(line)
            continue
        if re.match(r"^\d+\.?\s+\S", line):
            bullet_buffer = []
            numbered_buffer.append(line)
            continue

        # Normal paragraph (with inline bold support)
        flush_bullets(); flush_numbered()
        story.append(Paragraph(_to_paragraph_html(line), styles["ProBody"]))

    # Tail flushes
    flush_table()
    flush_bullets()
    flush_numbered()
    if in_code and code_buffer:
        story.append(Preformatted("\n".join(code_buffer), styles["ProCode"]))
    return story

# -------------------------------
# Public API
# -------------------------------
def save_to_pdf(content: str, filename: str) -> str:
    """Save provided content to a professionally formatted PDF file (Landscape A4)."""
    try:
        if not filename.lower().endswith(".pdf"):
            filename += ".pdf"

        # ensure parent folder exists
        parent = os.path.dirname(os.path.abspath(filename))
        if parent and not os.path.exists(parent):
            os.makedirs(parent, exist_ok=True)

        # Title from filename (fallback)
        title_from_name = os.path.splitext(os.path.basename(filename))[0].replace("_", " ").title()

        styles = _build_styles()

        # Landscape A4
        doc = SimpleDocTemplate(
            filename,
            pagesize=landscape(A4),
            leftMargin=0.9 * inch,
            rightMargin=0.9 * inch,
            topMargin=0.8 * inch,
            bottomMargin=0.8 * inch,
            title=title_from_name,
            author="GenIntel Report Generator",
            subject="Analyst Report",
            creator="GenIntel MCP",
        )

        # Build story with doc width (for table splitting)
        story = _parse_content_to_story(content, styles, title_from_name, doc.width)

        header_cb = _header_footer(title_from_name)
        doc.build(story, onFirstPage=header_cb, onLaterPages=header_cb)

        return f"✅ PDF saved as {filename}"
    except Exception as e:
        return f"❌ PDF Save Error: {str(e)}"
