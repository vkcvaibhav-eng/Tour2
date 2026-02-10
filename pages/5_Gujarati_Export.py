import streamlit as st
import pandas as pd
from docx import Document
from docx.shared import Cm, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_ALIGN_VERTICAL
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from io import BytesIO

# --- PAGE CONFIGURATION ---
st.set_page_config(layout="wide", page_title="Step 5: Final Gujarati Export")
st.title("🇮🇳 Step 5: Final Gujarati Export (A3 / Dual-A4 Format)")
st.markdown("---")

# --- 1. SMART INPUTS FOR HEADER DATA ---
st.sidebar.header("📝 Header Details")
st.sidebar.info("Adjust these values to appear in the top header.")

# Defaults based on Senior Scientist/Acarologist levels (User can change these)
emp_name = st.sidebar.text_input("Employee Name", "વી. કે. ચૌધરી")
designation = st.sidebar.text_input("Designation", "સીનીયર એક્રોલોજીસ્ટ")
basic_pay = st.sidebar.text_input("Basic Pay (મૂળ પગાર)", "₹ 67,700") 
pay_level = st.sidebar.text_input("Pay Level", "Level-11")
pay_scale = st.sidebar.text_input("Pay Scale", "67700 - 208700")

# --- DATA CONNECTION ---
if 'final_18_col_df' in st.session_state:
    df_ta = st.session_state['final_18_col_df'].copy()
    st.success(f"✅ Connected to Final Table: {len(df_ta)} rows.")
    
    # AUTO-FILL COLUMN 18 LOGIC
    if 'tour_data' in st.session_state:
        try:
            diary_df = st.session_state['tour_data']
            purpose_map = dict(zip(
                diary_df.iloc[:, 0].astype(str).str.strip(), 
                diary_df.iloc[:, 1].astype(str).str.strip()
            ))
            def get_purpose(row):
                return purpose_map.get(str(row.iloc[1]).strip(), "")
            
            df_ta.iloc[:, 17] = df_ta.apply(get_purpose, axis=1)
            st.info("✅ Column 18 (Purpose) auto-filled from Tour Diary.")
        except:
            pass
else:
    df_ta = pd.DataFrame()
    st.warning("⚠️ No data found. Please complete previous steps.")

# --- DOCX HELPER FUNCTIONS ---

def set_cell_margins(cell, top=5, start=5, bottom=5, end=5):
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for m, val in [('top', top), ('start', start), ('bottom', bottom), ('end', end)]:
        node = OxmlElement(f'w:{m}')
        node.set(qn('w:w'), str(val))
        node.set(qn('w:type'), 'dxa')
        tcMar.append(node)
    tcPr.append(tcMar)

def format_cell_text(cell, text, font_size=9, bold=False, color=None, align=WD_ALIGN_PARAGRAPH.CENTER, font_name='Arial Unicode MS'):
    paragraph = cell.paragraphs[0]
    paragraph.alignment = align
    run = paragraph.runs[0] if paragraph.runs else paragraph.add_run()
    run.text = str(text)
    run.font.bold = bold
    run.font.size = Pt(font_size)
    run.font.name = font_name
    cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER

def create_gujarati_doc(ta_data):
    doc = Document()
    
    # 1. PAGE SETUP: A3 LANDSCAPE (Equivalent to 2x A4 Pages Side-by-Side)
    section = doc.sections[0]
    section.page_width = Cm(42)   # Width of 2 A4 Portrait pages
    section.page_height = Cm(29.7) # Height of A4 Portrait
    section.left_margin = Cm(1.27)
    section.right_margin = Cm(1.27)
    section.top_margin = Cm(1.27)
    section.bottom_margin = Cm(1.27)

    # ================= HEADER SECTION =================
    # Invisible table for perfect alignment
    header_table = doc.add_table(rows=3, cols=3)
    header_table.autofit = False
    
    # Column Widths (Left: 35%, Center: 30%, Right: 35%)
    total_w = 42 - 2.54 # Page width minus margins
    w_left = total_w * 0.35
    w_mid = total_w * 0.30
    w_right = total_w * 0.35
    
    for row in header_table.rows:
        row.cells[0].width = Cm(w_left)
        row.cells[1].width = Cm(w_mid)
        row.cells[2].width = Cm(w_right)

    # Row 1: Location | Dept Name | Name
    format_cell_text(header_table.cell(0,0), "કાર્ય મથક : કીટકશાસ્ત્ર વિભાગ, ન.મ.કૃ.મ.,ન.કૃ.યુ., નવસારી", align=WD_ALIGN_PARAGRAPH.LEFT, bold=True, font_size=11)
    format_cell_text(header_table.cell(0,1), "કચેરી : કીટકશાસ્ત્ર વિભાગ", align=WD_ALIGN_PARAGRAPH.CENTER, bold=True, font_size=12)
    format_cell_text(header_table.cell(0,2), f"કર્મચારીનુ નામ: {emp_name}", align=WD_ALIGN_PARAGRAPH.RIGHT, bold=True, font_size=11)

    # Row 2: Empty | Designation | Basic Pay
    format_cell_text(header_table.cell(1,1), f"હોદ્દો: {designation}", align=WD_ALIGN_PARAGRAPH.CENTER, bold=True, font_size=11)
    format_cell_text(header_table.cell(1,2), f"મૂળ પગાર: {basic_pay}", align=WD_ALIGN_PARAGRAPH.RIGHT, font_size=11)

    # Row 3: Empty | Empty | Level & Pay Scale (Merged for neatness)
    format_cell_text(header_table.cell(2,2), f"Level: {pay_level}  |  Pay scale: {pay_scale}", align=WD_ALIGN_PARAGRAPH.RIGHT, font_size=11)

    doc.add_paragraph() # Spacer

    # ================= MAIN TABLE (19 Cols) =================
    table = doc.add_table(rows=3, cols=19)
    table.style = 'Table Grid'
    table.autofit = False 
    
    # Optimized Widths for A3 (Total ~39.5 cm)
    widths = [
        1.8, 1.8, 1.5,   # Depart
        1.8, 1.8, 1.5,   # Arrive
        2.5, 1.5,        # Mode, Class
        1.5, 1.8,        # Rate, Amt
        1.5, 1.5, 2.0,   # Road: KM, Rate, Amt
        1.5, 1.5, 2.0,   # DA: Days, Rate, Amt
        2.2, 2.2, 2.0    # Total, Purpose, Remarks (Wider)
    ]
    
    for row in table.rows:
        for idx, width in enumerate(widths):
            if idx < 19:
                row.cells[idx].width = Cm(width)

    # --- HEADERS (GUJARATI) ---
    r0 = table.rows[0].cells
    r1 = table.rows[1].cells

    # Merges & Text
    # Depart
    r0[0].merge(r0[2])
    format_cell_text(r0[0], "નીકળ્યા", bold=True)
    format_cell_text(r1[0], "સ્થળ", font_size=9)
    format_cell_text(r1[1], "તારીખ", font_size=9)
    format_cell_text(r1[2], "સમય", font_size=9)

    # Arrive
    r0[3].merge(r0[5])
    format_cell_text(r0[3], "આવ્યા", bold=True)
    format_cell_text(r1[3], "સ્થળ", font_size=9)
    format_cell_text(r1[4], "તારીખ", font_size=9)
    format_cell_text(r1[5], "સમય", font_size=9)

    # Vertical Merges
    def merge_vert(col, text):
        r0[col].merge(r1[col])
        format_cell_text(r0[col], text, bold=True, font_size=9)

    merge_vert(6, "મુસાફરીનો\nપ્રકાર")
    merge_vert(7, "વર્ગ")
    merge_vert(8, "ભાડાની સંખ્યા\nઅને દર")
    merge_vert(9, "રકમ")

    # Road
    r0[10].merge(r0[12])
    format_cell_text(r0[10], "અન્ય વાહન દ્વારા રસ્તાની મુસાફરી", bold=True, font_size=9)
    format_cell_text(r1[10], "કિ.મી.", font_size=9)
    format_cell_text(r1[11], "દર", font_size=9)
    format_cell_text(r1[12], "રકમ", font_size=9)

    # DA & Rest
    merge_vert(13, "ભથ્થાના\nદિવસ")
    merge_vert(14, "ભથ્થાનો\nદર")
    merge_vert(15, "ભથ્થાની\nરકમ")
    merge_vert(16, "કુલ રકમ\n(૧૦+૧૩+૧૬)")
    merge_vert(17, "મુસાફરીનું કારણ")
    merge_vert(18, "વિશેષ નોંધ")

    # Row 3: Numbers
    for i in range(19):
        format_cell_text(table.rows[2].cells[i], str(i+1), bold=True)

    # --- DATA FILLING ---
    total_claim = 0.0
    
    if not ta_data.empty:
        for index, row in ta_data.iterrows():
            new_row = table.add_row().cells
            
            # Helper to safely get floats
            def get_num(idx):
                try: return float(str(row.iloc[idx]).replace('₹','').replace(',',''))
                except: return 0.0
            
            # Text Cols
            for c in [0,1,2,3,4,5,6,7,8,17]: # Added 17 (Purpose)
                val = str(row.iloc[c]) if c < len(row) else ""
                format_cell_text(new_row[c], val)
            
            # Numeric Cols
            fare = get_num(9)
            format_cell_text(new_row[9], f"{fare:.2f}")
            
            km, r_rate, r_amt = get_num(10), get_num(11), get_num(12)
            format_cell_text(new_row[10], f"{km:.1f}" if km else "-")
            format_cell_text(new_row[11], f"{r_rate:.1f}" if r_rate else "-")
            format_cell_text(new_row[12], f"{r_amt:.2f}")

            da_d, da_r, da_a = get_num(13), get_num(14), get_num(15)
            format_cell_text(new_row[13], f"{da_d}" if da_d else "")
            format_cell_text(new_row[14], f"{da_r}" if da_r else "")
            format_cell_text(new_row[15], f"{da_a:.2f}" if da_a else "")
            
            # Total
            row_tot = fare + r_amt + da_a
            format_cell_text(new_row[16], f"{row_tot:.2f}", bold=True)
            total_claim += row_tot
            
            # Remarks blank
            format_cell_text(new_row[18], "")

    # Grand Total
    tot_row = table.add_row().cells
    tot_row[0].merge(tot_row[15])
    format_cell_text(tot_row[0], "કુલ સરવાળો (Grand Total)", bold=True, align=WD_ALIGN_PARAGRAPH.RIGHT)
    format_cell_text(tot_row[16], f"₹ {total_claim:.2f}", bold=True)

    # ================= CERTIFICATE FOOTER =================
    doc.add_paragraph()
    footer_table = doc.add_table(rows=1, cols=2)
    footer_table.autofit = False
    footer_table.rows[0].cells[0].width = Cm(25) # Left side empty
    footer_table.rows[0].cells[1].width = Cm(15) # Right side certificate
    
    cert_cell = footer_table.rows[0].cells[1]
    
    p = cert_cell.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run("Certificate").bold = True
    
    p2 = cert_cell.add_paragraph("This is to certify that above said TA bill is prepared based on actual journey and actual destination with shortest routes")
    p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p2.runs[0].font.size = Pt(9)
    
    p3 = cert_cell.add_paragraph(f"\n\n({emp_name})")
    p3.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p3.runs[0].bold = True

    return doc

# --- MAIN UI ---
if st.button("📄 Generate Final A3 File"):
    if not df_ta.empty:
        doc = create_gujarati_doc(df_ta)
        buffer = BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        st.download_button("⬇️ Download Final_A3_Report.docx", buffer, "Final_A3_Report.docx")
        st.balloons()
