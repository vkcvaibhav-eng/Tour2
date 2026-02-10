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
st.title("🇮🇳 Step 5: Final Gujarati Export (A2 Size)")
st.markdown("---")

# --- DATA CONNECTION & MERGING LOGIC ---
if 'final_18_col_df' in st.session_state:
    df_ta = st.session_state['final_18_col_df'].copy()
    st.success(f"✅ Connected to Step 4 Final Table: {len(df_ta)} rows loaded.")
    
    # LOGIC TO FILL COLUMN 18 (PURPOSE) FROM TOUR DIARY PAGE 1
    if 'tour_data' in st.session_state:
        st.info("🔄 Found Tour Diary Data... Attempting to merge Purpose of Journey date-wise.")
        try:
            diary_df = st.session_state['tour_data']
            # Create dictionary mapping: { Date_String : Purpose_Text }
            purpose_map = dict(zip(
                diary_df.iloc[:, 0].astype(str).str.strip(), 
                diary_df.iloc[:, 1].astype(str).str.strip()
            ))
            
            def get_purpose(row):
                dept_date = str(row.iloc[1]).strip()
                return purpose_map.get(dept_date, "")

            df_ta.iloc[:, 17] = df_ta.apply(get_purpose, axis=1)
            st.success("✅ Column 18 (Purpose) successfully populated!")
        except Exception as e:
            st.error(f"⚠️ Could not auto-fill Purpose: {e}")
    else:
        st.warning("⚠️ 'tour_data' not found in session state.")
elif 'final_ta_data' in st.session_state:
    df_ta = st.session_state['final_ta_data']
    st.warning("⚠️ Using raw Step 2 data.")
else:
    st.error("⚠️ No data found.")
    df_ta = pd.DataFrame()

# --- HELPER FUNCTIONS ---

def set_cell_margins(cell, top=10, start=10, bottom=10, end=10):
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
    
    if color:
        run.font.color.rgb = color
        
    cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER

def remove_table_borders(table):
    tbl = table._tbl
    for cell in tbl.iter_tcs():
        tcPr = cell.get_or_add_tcPr()
        tcBorders = OxmlElement('w:tcBorders')
        for border in ['top', 'left', 'bottom', 'right', 'insideH', 'insideV']:
            node = OxmlElement(f'w:{border}')
            node.set(qn('w:val'), 'nil')
            tcBorders.append(node)
        tcPr.append(tcBorders)

def create_gujarati_doc(ta_data):
    doc = Document()
    
    # 1. PAGE SETUP: A2 PORTRAIT
    section = doc.sections[0]
    section.page_width = Cm(42)
    section.page_height = Cm(59.4)
    section.left_margin = Cm(1.0)
    section.right_margin = Cm(1.0)
    section.top_margin = Cm(1.0)
    section.bottom_margin = Cm(1.0)

    # ================= HEADER SECTION (Top Details) =================
    # We use a 4x3 table with invisible borders to align Left, Center, and Right text
    header_table = doc.add_table(rows=4, cols=3)
    header_table.autofit = False
    
    # Set widths (Left: 35%, Center: 30%, Right: 35%)
    total_width = section.page_width - section.left_margin - section.right_margin
    for row in header_table.rows:
        row.cells[0].width = total_width * 0.35
        row.cells[1].width = total_width * 0.30
        row.cells[2].width = total_width * 0.35

    # --- Row 1 ---
    # Left
    format_cell_text(header_table.cell(0,0), "કાર્ય મથક : કીટકશાસ્ત્ર વિભાગ, ન.મ.કૃ.મ.,ન.કૃ.યુ., નવસારી", align=WD_ALIGN_PARAGRAPH.LEFT, bold=True, font_size=11)
    # Center
    format_cell_text(header_table.cell(0,1), "કચેરી : કીટકશાસ્ત્ર વિભાગ", align=WD_ALIGN_PARAGRAPH.CENTER, bold=True, font_size=12)
    # Right
    format_cell_text(header_table.cell(0,2), "કર્મચારીનુ નામ: વી. કે. ચૌધરી", align=WD_ALIGN_PARAGRAPH.RIGHT, bold=True, font_size=11)

    # --- Row 2 ---
    # Center
    format_cell_text(header_table.cell(1,1), "હોદ્દો: સીનીયર એક્રોલોજીસ્ટ", align=WD_ALIGN_PARAGRAPH.CENTER, bold=True, font_size=11)
    # Right
    format_cell_text(header_table.cell(1,2), "મૂળ પગાર: ________", align=WD_ALIGN_PARAGRAPH.RIGHT, font_size=11)

    # --- Row 3 ---
    # Right
    format_cell_text(header_table.cell(2,2), "Level:____", align=WD_ALIGN_PARAGRAPH.RIGHT, font_size=11)

    # --- Row 4 ---
    # Right
    format_cell_text(header_table.cell(3,2), "Pay scale:______________", align=WD_ALIGN_PARAGRAPH.RIGHT, font_size=11)

    doc.add_paragraph() # Spacer

    # ================= MAIN DATA TABLE =================
    # Removed English Row and Arrow Row.
    # New Structure:
    # Row 0: Gujarati Top
    # Row 1: Gujarati Bottom
    # Row 2: Numbers (1-19)
    
    table = doc.add_table(rows=3, cols=19) # Started with 3 rows
    table.style = 'Table Grid'
    table.autofit = False 
    
    # Define Column Widths (Total 19 cols)
    widths = [
        1.8, 1.8, 1.5,   # 1,2,3 Depart
        1.8, 1.8, 1.5,   # 4,5,6 Arrive
        2.5, 1.5,        # 7 Mode, 8 Class
        1.8, 1.8,        # 9 Rate, 10 Amt
        1.5, 1.5, 2.0,   # 11 KM, 12 Rate, 13 Total Road
        1.5, 1.5, 2.0,   # 14 Days, 15 Rate, 16 Amt
        2.0, 2.0, 2.0    # 17 Total, 18 Purpose, 19 Remarks
    ]
    
    for row in table.rows:
        for idx, width in enumerate(widths):
            if idx < 19:
                row.cells[idx].width = Cm(width)

    # ================= HEADERS (GUJARATI) =================
    r0 = table.rows[0].cells # Top Gujarati (Previously Row 2)
    r1 = table.rows[1].cells # Bottom Gujarati (Previously Row 3)

    # 1. Departure (Cols 0-2) -> Horizontal Merge Top
    r0[0].merge(r0[2])
    format_cell_text(r0[0], "નીકળ્યા", bold=True)
    format_cell_text(r1[0], "સ્થળ", font_size=9)
    format_cell_text(r1[1], "તારીખ", font_size=9)
    format_cell_text(r1[2], "સમય", font_size=9)

    # 2. Arrival (Cols 3-5) -> Horizontal Merge Top
    r0[3].merge(r0[5])
    format_cell_text(r0[3], "આવ્યા", bold=True)
    format_cell_text(r1[3], "સ્થળ", font_size=9)
    format_cell_text(r1[4], "તારીખ", font_size=9)
    format_cell_text(r1[5], "સમય", font_size=9)

    # 3. Vertical Merges for Middle Columns
    def merge_vert(col_idx, text):
        r0[col_idx].merge(r1[col_idx])
        format_cell_text(r0[col_idx], text, bold=True, font_size=9)

    merge_vert(6, "મુસાફરીનો\nપ્રકાર\nરેલ/બસ/ખાનગી વાહન\nવગેરે") # Mode
    merge_vert(7, "વર્ગ") # Class
    merge_vert(8, "ભાડાની સંખ્યા અને\nદર") # Rate
    merge_vert(9, "રકમ") # Amount

    # 4. Road Journey (Cols 10-12)
    r0[10].merge(r0[12])
    format_cell_text(r0[10], "અન્ય વાહન દ્વારા રસ્તાની મુસાફરી માટે", bold=True, font_size=9)
    format_cell_text(r1[10], "કિ.મી.", font_size=9)
    format_cell_text(r1[11], "દર", font_size=9)
    format_cell_text(r1[12], "રકમ", font_size=9)

    # 5. Vertical Merges for DA and Totals
    merge_vert(13, "મળવાપાત્ર\nદૈનિક ભથ્થાના\nદિવસ") # DA Days
    merge_vert(14, "દૈનિક ભથ્થાનો દર") # DA Rate
    merge_vert(15, "ભથ્થાની રકમ") # DA Amount
    merge_vert(16, "કુલ મળવાપાત્ર રકમ\n(૧૦+ ૧૩+ ૧૬)") # Total
    merge_vert(17, "મુસાફરીનું કારણ") # Purpose
    merge_vert(18, "વિશેષ નોંધ") # Remarks

    # ================= ROW 3: NUMBERS 1-19 =================
    r2 = table.rows[2].cells
    for i in range(19):
        format_cell_text(r2[i], str(i+1), bold=True)

    # ================= DATA FILLING =================
    total_claim = 0.0

    if not ta_data.empty:
        for index, row in ta_data.iterrows():
            new_row = table.add_row().cells
            
            def get_val(idx):
                return str(row.iloc[idx]) if idx < len(row) else ""
            
            def get_num(idx):
                try:
                    return float(str(row.iloc[idx]).replace('₹','').replace(',',''))
                except:
                    return 0.0

            # Fill Text Columns
            format_cell_text(new_row[0], get_val(0))
            format_cell_text(new_row[1], get_val(1))
            format_cell_text(new_row[2], get_val(2))
            format_cell_text(new_row[3], get_val(3))
            format_cell_text(new_row[4], get_val(4))
            format_cell_text(new_row[5], get_val(5))
            format_cell_text(new_row[6], get_val(6))
            format_cell_text(new_row[7], get_val(7))
            format_cell_text(new_row[8], get_val(8))
            format_cell_text(new_row[17], get_val(17)) # Purpose
            format_cell_text(new_row[18], "")

            # Fill Number Columns
            fare_amt = get_num(9)
            format_cell_text(new_row[9], f"{fare_amt:.2f}")

            km = get_num(10)
            rate = get_num(11)
            road_amt = get_num(12)
            format_cell_text(new_row[10], f"{km:.1f}" if km else "-")
            format_cell_text(new_row[11], f"{rate:.1f}" if rate else "-")
            format_cell_text(new_row[12], f"{road_amt:.2f}")

            da_days = get_num(13)
            da_rate = get_num(14)
            da_amt = get_num(15)
            format_cell_text(new_row[13], f"{da_days}" if da_days else "")
            format_cell_text(new_row[14], f"{da_rate}" if da_rate else "")
            format_cell_text(new_row[15], f"{da_amt:.2f}" if da_amt else "")

            # Row Total
            row_total = fare_amt + road_amt + da_amt
            format_cell_text(new_row[16], f"{row_total:.2f}", bold=True)
            total_claim += row_total

    # --- FINAL TOTAL ROW ---
    tot_row = table.add_row().cells
    tot_row[0].merge(tot_row[15])
    format_cell_text(tot_row[0], "કુલ સરવાળો (Grand Total)", bold=True, align=WD_ALIGN_PARAGRAPH.RIGHT)
    format_cell_text(tot_row[16], f"₹ {total_claim:.2f}", bold=True)

    # ================= FOOTER / CERTIFICATE SECTION =================
    doc.add_paragraph() # Spacer
    
    # Create a 1x2 table for layout (Left half empty, Right half certificate)
    footer_table = doc.add_table(rows=1, cols=2)
    footer_table.autofit = False
    footer_table.rows[0].cells[0].width = section.page_width * 0.4
    footer_table.rows[0].cells[1].width = section.page_width * 0.6
    
    # Right Cell Content
    cert_cell = footer_table.rows[0].cells[1]
    
    # 1. Heading "Certificate"
    p = cert_cell.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("Certificate")
    run.bold = True
    run.font.size = Pt(12)
    
    # 2. Disclaimer Text
    p2 = cert_cell.add_paragraph()
    p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run2 = p2.add_run("This is to certify that above said TA bill is prepared based on actual journey and actual destination with shortest routes")
    run2.font.size = Pt(10)
    
    # 3. Signature Space
    p3 = cert_cell.add_paragraph()
    p3.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run3 = p3.add_run("\n\n\n(વી.કે ચૌધરી)")
    run3.bold = True
    run3.font.size = Pt(11)
    run3.font.name = 'Arial Unicode MS'

    return doc

# --- MAIN UI ---
st.info("Generating Final Report (Modified Header/Footer Format)")

if st.button("📄 Generate & Download Final A2 File"):
    if not df_ta.empty:
        try:
            doc = create_gujarati_doc(df_ta)
            
            buffer = BytesIO()
            doc.save(buffer)
            buffer.seek(0)
            
            st.download_button(
                label="⬇️ Download Gujarati_Final_A2.docx",
                data=buffer,
                file_name="Gujarati_Final_A2.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
            st.balloons()
        except Exception as e:
            st.error(f"Error generating file: {e}")
