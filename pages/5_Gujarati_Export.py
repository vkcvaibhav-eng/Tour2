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

# --- DATA CONNECTION ---
if 'final_18_col_df' in st.session_state:
    df_ta = st.session_state['final_18_col_df']
    st.success(f"✅ Connected to Step 4 Final Table: {len(df_ta)} rows loaded.")
elif 'final_ta_data' in st.session_state:
    df_ta = st.session_state['final_ta_data']
    st.warning("⚠️ Using raw Step 2 data. (Tip: Run Step 4 for the fully merged table).")
else:
    st.error("⚠️ No data found. Please complete Step 4 (Final Table) first.")
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

def format_cell_text(cell, text, font_size=9, bold=False, color=None, align=WD_ALIGN_PARAGRAPH.CENTER):
    paragraph = cell.paragraphs[0]
    paragraph.alignment = align
    run = paragraph.runs[0] if paragraph.runs else paragraph.add_run()
    run.text = str(text)
    run.font.bold = bold
    run.font.size = Pt(font_size)
    run.font.name = 'Arial Unicode MS'  # Required for Gujarati
    
    if color:
        run.font.color.rgb = color
        
    cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER

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

    # 2. TITLE
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("મુસાફરી ભથ્થાનું બિલ (Travelling Allowance Bill)")
    run.bold = True
    run.font.size = Pt(22)
    run.font.name = 'Arial Unicode MS'

    # 3. CREATE TABLE (19 Columns)
    # We add 5 header rows immediately: 
    # Row 0: English Headers
    # Row 1: Arrows
    # Row 2: Gujarati Main Headers
    # Row 3: Gujarati Sub Headers
    # Row 4: Numbers (1-19)
    table = doc.add_table(rows=5, cols=19)
    table.style = 'Table Grid'
    table.autofit = False 
    
    # Define Column Widths (Total 19 cols)
    widths = [
        1.8, 1.8, 1.5,   # 1,2,3 Depart
        1.8, 1.8, 1.5,   # 4,5,6 Arrive
        2.5, 1.5,        # 7 Mode (Wide), 8 Class
        1.8, 1.8,        # 9 Rate, 10 Amt
        1.5, 1.5, 2.0,   # 11 KM, 12 Rate, 13 Total Road
        1.5, 1.5, 2.0,   # 14 Days, 15 Rate, 16 Amt
        2.0, 2.0, 2.0    # 17 Total, 18 Purpose, 19 Remarks
    ]
    
    for row in table.rows:
        for idx, width in enumerate(widths):
            if idx < 19:
                row.cells[idx].width = Cm(width)

    # ================= HEADER ROW 1: ENGLISH TEXT =================
    english_headers = [
        "1. Departure Place", "2. Departure Date", "3. Departure Time",
        "4. Arrival Place", "5. Arrival Date", "6. Arrival Time",
        "7. Mode", "8. Class", "9. Ticket Price/Rate (Rs.)", "10. Actual Total Amount of Ticket (Rs.)",
        "11. KM", "12. Rate (Rs.) (Auto/Taxi/Pvt)", "13. Total (Rs.)",
        "14. Days of daily allowance", "15. Daily allowance rate (Rs.)", "16. Amount of Allowance (Rs.)",
        "17. Total amount receivable (10+13+16)", "18. Purpose of Journey", "19. add new"
    ]
    
    r0 = table.rows[0].cells
    for i, text in enumerate(english_headers):
        format_cell_text(r0[i], text, font_size=8, bold=True)

    # ================= HEADER ROW 2: ARROWS (BLUE) =================
    r1 = table.rows[1].cells
    blue_color = RGBColor(46, 117, 182) # Excel Blue
    for i in range(19):
        # Unicode Arrow Down
        format_cell_text(r1[i], "🡻", font_size=24, bold=True, color=blue_color)
        r1[i].paragraphs[0].paragraph_format.space_after = Pt(0)
        r1[i].paragraphs[0].paragraph_format.space_before = Pt(0)

    # ================= HEADER ROW 3 & 4: GUJARATI TEXT & MERGING =================
    r2 = table.rows[2].cells # Top Gujarati
    r3 = table.rows[3].cells # Bottom Gujarati

    # 1. Departure (Cols 0-2) -> Horizontal Merge Top
    r2[0].merge(r2[2])
    format_cell_text(r2[0], "નીકળ્યા", bold=True)
    format_cell_text(r3[0], "સ્થળ", font_size=9)
    format_cell_text(r3[1], "તારીખ", font_size=9)
    format_cell_text(r3[2], "સમય", font_size=9)

    # 2. Arrival (Cols 3-5) -> Horizontal Merge Top
    r2[3].merge(r2[5])
    format_cell_text(r2[3], "આવ્યા", bold=True)
    format_cell_text(r3[3], "સ્થળ", font_size=9)
    format_cell_text(r3[4], "તારીખ", font_size=9)
    format_cell_text(r3[5], "સમય", font_size=9)

    # 3. Vertical Merges for Middle Columns
    # Helper to merge vertical (Row 2 to Row 3)
    def merge_vert(col_idx, text):
        r2[col_idx].merge(r3[col_idx])
        format_cell_text(r2[col_idx], text, bold=True, font_size=9)

    # Col 7: Mode (Specific Gujarati Text Requested)
    merge_vert(6, "મુસાફરીનો\nપ્રકાર\nરેલ/બસ/ખાનગી વાહન\nવગેરે")

    # Col 8: Class
    merge_vert(7, "વર્ગ")

    # Col 9: Rate/Count
    merge_vert(8, "ભાડાની સંખ્યા અને\nદર")

    # Col 10: Amount
    merge_vert(9, "રકમ")

    # 4. Road Journey (Cols 10-12 in index, 11-13 in logic) -> Horizontal Merge Top
    r2[10].merge(r2[12])
    format_cell_text(r2[10], "અન્ય વાહન દ્વારા રસ્તાની મુસાફરી માટે", bold=True, font_size=9)
    format_cell_text(r3[10], "કિ.મી.", font_size=9)
    format_cell_text(r3[11], "દર", font_size=9)
    format_cell_text(r3[12], "રકમ", font_size=9)

    # 5. Vertical Merges for DA and Totals
    merge_vert(13, "મળવાપાત્ર\nદૈનિક ભથ્થાના\nદિવસ") # DA Days
    merge_vert(14, "દૈનિક ભથ્થાનો દર") # DA Rate
    merge_vert(15, "ભથ્થાની રકમ") # DA Amount
    merge_vert(16, "કુલ મળવાપાત્ર રકમ\n(૧૦+ ૧૩+ ૧૬)") # Total
    merge_vert(17, "મુસાફરીનું કારણ") # Purpose
    merge_vert(18, "વિશેષ નોંધ") # Remarks

    # ================= HEADER ROW 5: NUMBERS 1-19 =================
    r4 = table.rows[4].cells
    for i in range(19):
        format_cell_text(r4[i], str(i+1), bold=True)

    # ================= DATA FILLING =================
    total_claim = 0.0

    if not ta_data.empty:
        for index, row in ta_data.iterrows():
            new_row = table.add_row().cells
            
            # Helper to get data safely
            def get_val(idx):
                if idx < len(row): return str(row.iloc[idx])
                return ""
            
            def get_num(idx):
                try:
                    val = str(row.iloc[idx]).replace('₹','').replace(',','')
                    return float(val)
                except:
                    return 0.0

            # 1. Depart (Place, Date, Time)
            format_cell_text(new_row[0], get_val(0))
            format_cell_text(new_row[1], get_val(1))
            format_cell_text(new_row[2], get_val(2))

            # 2. Arrive (Place, Date, Time)
            format_cell_text(new_row[3], get_val(3))
            format_cell_text(new_row[4], get_val(4))
            format_cell_text(new_row[5], get_val(5))

            # 3. Mode & Class
            format_cell_text(new_row[6], get_val(6)) # Mode
            format_cell_text(new_row[7], get_val(7)) # Class

            # 4. Ticket Details
            format_cell_text(new_row[8], get_val(8)) # Rate/No
            fare_amt = get_num(9)
            format_cell_text(new_row[9], f"{fare_amt:.2f}") # Ticket Amt

            # 5. Road Details
            km = get_num(10)
            rate = get_num(11)
            road_amt = get_num(12)
            format_cell_text(new_row[10], f"{km:.1f}" if km else "-")
            format_cell_text(new_row[11], f"{rate:.1f}" if rate else "-")
            format_cell_text(new_row[12], f"{road_amt:.2f}")

            # 6. DA Details
            da_days = get_num(13)
            da_rate = get_num(14)
            da_amt = get_num(15)
            format_cell_text(new_row[13], f"{da_days}" if da_days else "")
            format_cell_text(new_row[14], f"{da_rate}" if da_rate else "")
            format_cell_text(new_row[15], f"{da_amt:.2f}" if da_amt else "")

            # 7. Grand Total (Ticket + Road + DA)
            # Calculated fresh to match the header formula (10+13+16) -> Indices (9 + 12 + 15)
            row_total = fare_amt + road_amt + da_amt
            format_cell_text(new_row[16], f"{row_total:.2f}", bold=True)
            total_claim += row_total

            # 8. Purpose & Remarks
            format_cell_text(new_row[17], get_val(17)) # Purpose
            format_cell_text(new_row[18], "") # Remarks (Blank for user to fill)

    # --- FINAL TOTAL ROW ---
    tot_row = table.add_row().cells
    tot_row[0].merge(tot_row[15]) # Merge all up to Total Column
    format_cell_text(tot_row[0], "કુલ સરવાળો (Grand Total)", bold=True, align=WD_ALIGN_PARAGRAPH.RIGHT)
    format_cell_text(tot_row[16], f"₹ {total_claim:.2f}", bold=True)

    return doc

# --- MAIN UI ---
st.info("Generating Final Report (Exact 19-Col Format)")

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
