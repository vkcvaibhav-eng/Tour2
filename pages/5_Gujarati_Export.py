import streamlit as st
import pandas as pd
from docx import Document
from docx.shared import Cm, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_ALIGN_VERTICAL
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from io import BytesIO

st.set_page_config(layout="wide", page_title="Step 5: Final Gujarati Export")
st.title("🇮🇳 Step 5: Final Gujarati Export (A2 Size)")
st.markdown("---")
st.info("Generates the final 1-19 column table with Gujarati Headers and English Data.")

# --- HELPER FUNCTIONS ---

def set_cell_margins(cell, top=0, start=0, bottom=0, end=0):
    """Removes margins from table cells to fit more text."""
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for m, val in [('top', top), ('start', start), ('bottom', bottom), ('end', end)]:
        node = OxmlElement(f'w:{m}')
        node.set(qn('w:w'), str(val))
        node.set(qn('w:type'), 'dxa')
        tcMar.append(node)
    tcPr.append(tcMar)

def create_gujarati_doc(ta_data, da_data):
    doc = Document()
    
    # 1. SETUP PAGE SIZE (A2: 42cm x 59.4cm)
    section = doc.sections[0]
    section.page_width = Cm(42)
    section.page_height = Cm(59.4)
    
    # Margins (Narrow to fit 19 columns)
    section.left_margin = Cm(1.0)
    section.right_margin = Cm(1.0)
    section.top_margin = Cm(1.5)
    section.bottom_margin = Cm(1.5)

    # 2. TITLE SECTION (Gujarati)
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Arial Unicode MS'  # Standard for Gujarati
    font.size = Pt(11)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("મુસાફરી ભથ્થાનું બિલ (TA/DA Bill)")
    run.bold = True
    run.font.size = Pt(22)

    # Employee Info Placeholders
    info_p = doc.add_paragraph()
    info_p.add_run("\nકર્મચારીનું નામ: _______________________      હોદ્દો: _______________________\n")
    info_p.add_run("હેડ ક્વાર્ટર: _______________________           પગાર: _______________________\n")

    # 3. CREATE THE 19-COLUMN TABLE
    table = doc.add_table(rows=3, cols=19)
    table.style = 'Table Grid'
    table.autofit = False 
    
    # Set rough column widths
    for col in table.columns:
        col.width = Cm(2.1) 

    # --- HEADERS (Gujarati) ---
    # Row 1: Main Group Headers
    # Row 2: Sub Headers
    # Row 3: Column Numbers (1-19)
    
    # Row 1 Cells (Merged Groups)
    r1 = table.rows[0].cells
    # Departure (1-3)
    r1[0].text = "ઉપડ્યા (Departure)"
    r1[0].merge(r1[2])
    # Arrival (4-6)
    r1[3].text = "પહોંચ્યા (Arrival)"
    r1[3].merge(r1[5])
    # Mode/Class (7-8)
    r1[6].text = "વિગત (Detail)"
    r1[6].merge(r1[8])
    # Fare (9-10)
    r1[9].text = "ભાડું (Fare)"
    # Road (11-13)
    r1[10].text = "રોડ મુસાફરી (Road Travel)"
    r1[10].merge(r1[12])
    # DA (14-18)
    r1[13].text = "દૈનિક ભથ્થું (Daily Allowance)"
    r1[13].merge(r1[17])
    # Total (19)
    r1[18].text = "કુલ (Total)"

    # Row 2 Cells (Specific Titles)
    r2 = table.rows[1].cells
    titles_guj = [
        "સ્થળ", "તારીખ", "સમય",          # 1-3
        "સ્થળ", "તારીખ", "સમય",          # 4-6
        "વાહન", "વર્ગ", "ટિકિટ નં",     # 7-9
        "રકમ (A)",                      # 10
        "કિ.મી.", "દર", "રકમ (B)",      # 11-13
        "દિવસ", "દર", "રકમ", "કપાત", "ચોખ્ખી (C)", # 14-18
        "રકમ (A+B+C)"                   # 19
    ]
    
    for i, title in enumerate(titles_guj):
        r2[i].text = title

    # Row 3 Cells (Numbers 1-19)
    r3 = table.rows[2].cells
    for i in range(19):
        r3[i].text = str(i + 1)
        
    # Formatting Headers
    for row in [table.rows[0], table.rows[1], table.rows[2]]:
        for cell in row.cells:
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            if p.runs:
                p.runs[0].font.bold = True
                p.runs[0].font.size = Pt(9)

    # --- POPULATE DATA (English) ---
    grand_total_claim = 0.0

    if not ta_data.empty:
        for idx, row in ta_data.iterrows():
            new_row = table.add_row().cells
            
            # --- 1-3: Departure ---
            new_row[0].text = str(row.get("1. Departure Place", ""))
            new_row[1].text = str(row.get("2. Departure Date", ""))
            new_row[2].text = str(row.get("3. Departure Time", ""))
            
            # --- 4-6: Arrival ---
            new_row[3].text = str(row.get("4. Arrival Place", ""))
            new_row[4].text = str(row.get("5. Arrival Date", ""))
            new_row[5].text = str(row.get("6. Arrival Time", ""))
            
            # --- 7-9: Details ---
            new_row[6].text = str(row.get("7. Mode", ""))
            new_row[7].text = str(row.get("8. Class", ""))
            # Assuming Ticket No is not in standard dataframe, using blank or placeholder
            new_row[8].text = "" 
            
            # --- 10: Ticket Fare (A) ---
            tkt_amt = pd.to_numeric(row.get("10. Actual Total Amount of Ticket (Rs.)", 0), errors='coerce')
            if pd.isna(tkt_amt): tkt_amt = 0
            new_row[9].text = f"{tkt_amt:.2f}" if tkt_amt > 0 else "-"
            
            # --- 11-13: Road (B) ---
            km = pd.to_numeric(row.get("11. KM", 0), errors='coerce')
            rate = pd.to_numeric(row.get("12. Rate (Rs.) (Auto/Taxi/Pvt)", 0), errors='coerce')
            
            road_amt = 0
            if km > 0 and rate > 0:
                road_amt = km * rate
            
            # Override if "13. Total" exists and is different
            calc_13 = pd.to_numeric(row.get("13. Total (Rs.)", 0), errors='coerce')
            if calc_13 > 0: road_amt = calc_13

            new_row[10].text = f"{km:.1f}" if km > 0 else "-"
            new_row[11].text = f"{rate:.1f}" if rate > 0 else "-"
            new_row[12].text = f"{road_amt:.2f}" if road_amt > 0 else "-"
            
            # --- 14-18: DA (C) ---
            # Try to match DA data if available, otherwise leave blank for manual fill
            da_days = ""
            da_rate = ""
            da_amt = 0
            da_less = 0
            da_net = 0 # This is Column 18
            
            # Simple Logic: If this row has a DA Claim in the separate dataframe, add it.
            # (Here we assume row-by-row matching isn't perfect, so we leave blank or fill 0)
            # You can manually fill these columns in the Word doc.
            
            new_row[13].text = da_days
            new_row[14].text = da_rate
            new_row[15].text = "-"
            new_row[16].text = "-"
            new_row[17].text = "-" # Col 18 (Net DA)
            
            # --- 19: Total (A+B+C) -> (10 + 13 + 18) ---
            row_total = tkt_amt + road_amt + da_net
            new_row[18].text = f"{row_total:.2f}"
            
            grand_total_claim += row_total
            
            # Center Align Data
            for cell in new_row:
                p = cell.paragraphs[0]
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p.style.font.size = Pt(10)
                set_cell_margins(cell, top=50, bottom=50)

    # --- SUMMARY ROW ---
    sum_row = table.add_row().cells
    sum_row[0].text = "GRAND TOTAL"
    sum_row[18].text = f"₹ {grand_total_claim:.2f}"
    
    # Merge label cells
    sum_row[0].merge(sum_row[17]) 
    sum_row[0].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.RIGHT
    sum_row[0].paragraphs[0].runs[0].bold = True

    return doc

# --- MAIN UI ---

if st.button("📄 Generate Gujarati 1-19 A2 Doc"):
    if 'final_ta_data' in st.session_state:
        
        ta_df = st.session_state['final_ta_data']
        da_df = st.session_state.get('final_da_data', pd.DataFrame())

        try:
            doc = create_gujarati_doc(ta_df, da_df)
            
            buffer = BytesIO()
            doc.save(buffer)
            buffer.seek(0)
            
            st.download_button(
                label="⬇️ Download Gujarati_1to19_A2.docx",
                data=buffer,
                file_name="Gujarati_TA_Bill_A2_Final.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
            st.success("✅ Document generated! Headers in Gujarati, Data in English. (Size: A2)")
            
        except Exception as e:
            st.error(f"Error: {e}")
    else:
        st.error("⚠️ No TA Data found. Please complete Step 2 first.")
