import streamlit as st
import pandas as pd
from docx import Document
from docx.shared import Cm, Mm, Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_ALIGN_VERTICAL, WD_ROW_HEIGHT_RULE
from docx.enum.section import WD_SECTION, WD_ORIENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from io import BytesIO

# --- PAGE CONFIGURATION ---
st.set_page_config(layout="wide", page_title="Step 5: Final Gujarati Export")
st.title("🇮🇳 Step 5: Final Gujarati Export (Split Layout)")
st.markdown("---")

# --- 1. SMART INPUTS FOR HEADER DATA ---
st.sidebar.header("📝 Header Details")

# Defaults based on your prompt
emp_name = st.sidebar.text_input("Employee Name", "વી. કે. ચૌધરી")
designation = st.sidebar.text_input("Designation", "સીનીયર એક્રોલોજીસ્ટ")
basic_pay = st.sidebar.text_input("Basic Pay", "₹ 67,700") 
pay_level = st.sidebar.text_input("Pay Level", "Level-11")
pay_scale = st.sidebar.text_input("Pay Scale", "67700 - 208700")
office_name = st.sidebar.text_input("Office", "કીટકશાસ્ત્ર વિભાગ")
work_place = st.sidebar.text_input("Work Place", "કીટકશાસ્ત્ર વિભાગ, ન.મ.કૃ.મ.,ન.કૃ.યુ., નવસારી")
voucher_month = st.sidebar.text_input("Bill Month", "ફેબ્રુઆરી - ૨૦૨૬")

# --- DATA CONNECTION ---
if 'final_18_col_df' in st.session_state:
    df_ta = st.session_state['final_18_col_df'].copy()
    # Add Column 19 (Remarks) as empty if missing
    if len(df_ta.columns) == 18:
        df_ta["19. Remarks"] = ""
    st.success(f"✅ Connected to Final Table: {len(df_ta)} rows.")
else:
    df_ta = pd.DataFrame()
    st.warning("⚠️ No data found. Please complete previous steps.")

# --- HELPER: GUJARATI NUMBER TO WORDS ---
def num_to_gujarati_words(num):
    try:
        num = int(num)
    except:
        return ""
    
    ones = ["", "એક", "બે", "ત્રણ", "ચાર", "પાંચ", "છ", "સાત", "આઠ", "નવ"]
    teens = ["દસ", "અગિયાર", "બાર", "તેર", "ચૌદ", "પંદર", "સોળ", "સત્તર", "અઢાર", "ઓગણીસ"]
    tens = ["", "", "વીસ", "ત્રીસ", "ચાલીસ", "પચાસ", "સાઈઠ", "સિત્તેર", "એંસી", "નેવું"]
    
    def convert_upto_99(n):
        if n < 10: return ones[n]
        if 10 <= n < 20: return teens[n-10]
        return tens[n // 10] + (" " + ones[n % 10] if n % 10 != 0 else "")

    parts = []
    if num >= 100000:
        parts.append(convert_upto_99(num // 100000) + " લાખ")
        num %= 100000
    if num >= 1000:
        parts.append(convert_upto_99(num // 1000) + " હજાર")
        num %= 1000
    if num >= 100:
        parts.append(convert_upto_99(num // 100) + " સો")
        num %= 100
    if num > 0:
        parts.append(convert_upto_99(num))
        
    return " ".join(parts).strip()

# --- DOCX FORMATTING HELPERS ---
def set_cell_margins(cell, top=0, bottom=0, left=50, right=50):
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for m in ['top', 'bottom', 'left', 'right']:
        node = OxmlElement(f'w:{m}')
        node.set(qn('w:w'), str(eval(m)))
        node.set(qn('w:type'), 'dxa')
        tcMar.append(node)
    tcPr.append(tcMar)

def format_cell(cell, text, font_size=10, bold=False, align=WD_ALIGN_PARAGRAPH.CENTER):
    # Ensure paragraph exists
    if not cell.paragraphs:
        cell.add_paragraph()
    p = cell.paragraphs[0]
    p.alignment = align
    
    # Clear existing runs
    for run in p.runs:
        run._element.getparent().remove(run._element)
        
    run = p.add_run(str(text))
    run.font.name = 'Arial Unicode MS'
    run.font.size = Pt(font_size)
    run.font.bold = bold
    cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER

def set_row_height(row, height_cm):
    row.height = Cm(height_cm)
    row.height_rule = WD_ROW_HEIGHT_RULE.EXACTLY

# --- MAIN GENERATOR FUNCTION ---
def create_split_layout_doc(ta_data):
    doc = Document()
    
    # GLOBAL STYLES
    style = doc.styles['Normal']
    style.font.name = 'Arial Unicode MS'
    style.font.size = Pt(10)

    # PAGE SETUP (A4 Portrait default)
    section = doc.sections[0]
    section.page_width = Mm(210)
    section.page_height = Mm(297)
    section.left_margin = Mm(15)
    section.right_margin = Mm(15)
    section.top_margin = Mm(15)
    section.bottom_margin = Mm(15)

    # ================= PAGE 1: HEADER & TITLE =================
    
    # 1. Main Title
    p_title = doc.add_paragraph("નવસારી કૃષિ વિશ્વવિધાલય")
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_title.runs[0].font.size = Pt(16)
    p_title.runs[0].font.bold = True
    
    p_sub = doc.add_paragraph("મુસાફરી ભથ્થા બીલ")
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_sub.runs[0].font.size = Pt(14)
    p_sub.runs[0].font.bold = True
    p_sub.runs[0].underline = True

    doc.add_paragraph() # Spacer

    # 2. Header Details Table (Exact formatting requested)
    # 4 Rows, 2 Columns (Left aligned keys, Right aligned values mostly)
    hdr_table = doc.add_table(rows=4, cols=2)
    hdr_table.autofit = False
    hdr_table.columns[0].width = Mm(100)
    hdr_table.columns[1].width = Mm(80)

    # Row 1
    r0 = hdr_table.rows[0].cells
    format_cell(r0[0], f"કાર્ય મથક : {work_place}", align=WD_ALIGN_PARAGRAPH.LEFT, bold=True)
    format_cell(r0[1], f"કર્મચારીનુ નામ: {emp_name}", align=WD_ALIGN_PARAGRAPH.RIGHT, bold=True)
    
    # Row 2
    r1 = hdr_table.rows[1].cells
    format_cell(r1[0], f"કચેરી : {office_name}", align=WD_ALIGN_PARAGRAPH.LEFT, bold=True)
    format_cell(r1[1], " ", align=WD_ALIGN_PARAGRAPH.RIGHT) # Empty spacer
    
    # Row 3
    r2 = hdr_table.rows[2].cells
    format_cell(r2[0], " ", align=WD_ALIGN_PARAGRAPH.LEFT) # Empty spacer
    format_cell(r2[1], f"હોદ્દો: {designation}", align=WD_ALIGN_PARAGRAPH.RIGHT, bold=True)
    
    # Row 4
    r3 = hdr_table.rows[3].cells
    format_cell(r3[0], f"મૂળ પગાર: {basic_pay}", align=WD_ALIGN_PARAGRAPH.LEFT)
    format_cell(r3[1], f"Level: {pay_level} | Pay scale: {pay_scale}", align=WD_ALIGN_PARAGRAPH.RIGHT)

    # Remove borders for header table to look like text
    for row in hdr_table.rows:
        for cell in row.cells:
            tcPr = cell._tc.get_or_add_tcPr()
            tcBorders = OxmlElement('w:tcBorders')
            for border in ['top', 'left', 'bottom', 'right', 'insideH', 'insideV']:
                node = OxmlElement(f'w:{border}')
                node.set(qn('w:val'), 'nil')
                tcBorders.append(node)
            tcPr.append(tcBorders)

    doc.add_page_break()

    # ================= PAGE 2: TABLE PART 1 (Cols 1-10) =================
    
    # Page 2 Section Setup
    # Note: We keep Portrait, but maybe reduce margins slightly for table width
    
    p = doc.add_paragraph("મુસાફરી વિગત (ભાગ-૧)")
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.runs[0].bold = True

    # Columns: 1.DepPlace, 2.Date, 3.Time, 4.ArrPlace, 5.Date, 6.Time, 7.Mode, 8.Class, 9.Price, 10.Total
    table_left = doc.add_table(rows=3, cols=10)
    table_left.style = 'Table Grid'
    table_left.autofit = False
    
    # Set Column Widths (Approx to fit A4 width ~18cm)
    col_widths_L = [2.0, 1.8, 1.3, 2.0, 1.8, 1.3, 2.5, 1.5, 1.8, 2.0] # Total ~18cm
    for r in table_left.rows:
        for i, w in enumerate(col_widths_L):
            r.cells[i].width = Cm(w)

    # --- HEADER ROWS ---
    # Row 0
    r0 = table_left.rows[0].cells
    r0[0].merge(r0[2]); format_cell(r0[0], "નીકળ્યા (Departure)", bold=True)
    r0[3].merge(r0[5]); format_cell(r0[3], "આવ્યા (Arrival)", bold=True)
    
    # Vertical Merges for Mode, Class, Ticket
    for i in range(6, 10):
        table_left.cell(0, i).merge(table_left.cell(1, i))
    
    format_cell(table_left.cell(0, 6), "મુસાફરીનો\nપ્રકાર", bold=True, font_size=9)
    format_cell(table_left.cell(0, 7), "વર્ગ", bold=True, font_size=9)
    format_cell(table_left.cell(0, 8), "ભાડા દર", bold=True, font_size=9)
    format_cell(table_left.cell(0, 9), "ટિકિટ રકમ\n(Col 10)", bold=True, font_size=9)

    # Row 1 (Sub headers for Dep/Arr)
    r1 = table_left.rows[1].cells
    headers_sub = ["સ્થળ", "તારીખ", "સમય", "સ્થળ", "તારીખ", "સમય"]
    for i, txt in enumerate(headers_sub):
        format_cell(r1[i], txt, font_size=9)

    # Row 2 (Numbers)
    for i in range(10):
        format_cell(table_left.rows[2].cells[i], str(i+1), bold=True)

    # --- DATA ROWS PART 1 ---
    row_height_cm = 1.0 # STRICT HEIGHT
    
    for index, row in ta_data.iterrows():
        new_row = table_left.add_row()
        set_row_height(new_row, row_height_cm) # SYNCHRONIZATION KEY
        
        cells = new_row.cells
        # Col 1-6
        for i in range(6):
            val = str(row.iloc[i]) if pd.notnull(row.iloc[i]) else ""
            format_cell(cells[i], val, font_size=9)
        # Col 7 Mode
        format_cell(cells[6], str(row.iloc[6]), font_size=9)
        # Col 8 Class
        format_cell(cells[7], str(row.iloc[7]), font_size=9)
        # Col 9 Price
        try: pr = float(str(row.iloc[8]).replace('₹','').replace(',',''))
        except: pr = 0.0
        format_cell(cells[8], f"{pr:.0f}", font_size=9)
        # Col 10 Total
        try: tot = float(str(row.iloc[9]).replace('₹','').replace(',',''))
        except: tot = 0.0
        format_cell(cells[9], f"{tot:.0f}", font_size=9, bold=True)

    # Add Total Row
    tot_row_L = table_left.add_row()
    set_row_height(tot_row_L, row_height_cm)
    tot_row_L.cells[0].merge(tot_row_L.cells[8])
    format_cell(tot_row_L.cells[0], "સરવાળો (Page Total)", align=WD_ALIGN_PARAGRAPH.RIGHT, bold=True)
    
    # Sum Col 10
    sum_10 = pd.to_numeric(ta_data.iloc[:, 9].astype(str).str.replace(r'[^\d.]', '', regex=True), errors='coerce').sum()
    format_cell(tot_row_L.cells[9], f"{sum_10:.0f}", bold=True)

    doc.add_page_break()

    # ================= PAGE 3: TABLE PART 2 (Cols 11-19) =================
    
    p = doc.add_paragraph("મુસાફરી વિગત (ભાગ-૨)")
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.runs[0].bold = True

    # Columns: 11.KM, 12.Rate, 13.Total, 14.Days, 15.DA_Rate, 16.DA_Amt, 17.GrandTotal, 18.Purpose, 19.Remarks
    table_right = doc.add_table(rows=3, cols=9)
    table_right.style = 'Table Grid'
    table_right.autofit = False

    # Widths
    col_widths_R = [1.5, 1.5, 2.0, 1.5, 1.5, 2.0, 2.5, 3.5, 2.0]
    for r in table_right.rows:
        for i, w in enumerate(col_widths_R):
            r.cells[i].width = Cm(w)

    # --- HEADER ROWS ---
    # Row 0
    r0 = table_right.rows[0].cells
    r0[0].merge(r0[2]); format_cell(r0[0], "અન્ય વાહન મુસાફરી (Road)", bold=True, font_size=9)
    r0[3].merge(r0[5]); format_cell(r0[3], "દૈનિક ભથ્થું (DA)", bold=True, font_size=9)
    
    # Vertical Merges
    for i in range(6, 9):
        table_right.cell(0, i).merge(table_right.cell(1, i))
        
    format_cell(table_right.cell(0, 6), "કુલ રકમ\n(૧૦+૧૩+૧૬)", bold=True, font_size=9)
    format_cell(table_right.cell(0, 7), "મુસાફરીનું કારણ", bold=True, font_size=9)
    format_cell(table_right.cell(0, 8), "વિશેષ નોંધ", bold=True, font_size=9)

    # Row 1 (Sub headers)
    r1 = table_right.rows[1].cells
    sub_headers_R = ["કિ.મી.", "દર", "રકમ", "દિવસ", "દર", "રકમ"]
    for i, txt in enumerate(sub_headers_R):
        format_cell(r1[i], txt, font_size=9)

    # Row 2 (Numbers 11-19)
    for i in range(9):
        format_cell(table_right.rows[2].cells[i], str(i+11), bold=True)

    # --- DATA ROWS PART 2 ---
    # Iterate same data again to keep rows matched
    for index, row in ta_data.iterrows():
        new_row = table_right.add_row()
        set_row_height(new_row, row_height_cm) # CRITICAL SYNC
        
        cells = new_row.cells
        
        # Helper to clean numbers
        def clean(idx): 
            try: return float(str(row.iloc[idx]).replace('₹','').replace(',',''))
            except: return 0.0

        # Col 11-13 (Road)
        km = clean(10); rt = clean(11); r_tot = clean(12)
        format_cell(cells[0], f"{km:.1f}" if km else "-")
        format_cell(cells[1], f"{rt:.1f}" if rt else "-")
        format_cell(cells[2], f"{r_tot:.0f}" if r_tot else "-")
        
        # Col 14-16 (DA)
        d_day = row.iloc[13]; d_rate = clean(14); d_amt = clean(15)
        format_cell(cells[3], str(d_day) if str(d_day)!="0" else "-")
        format_cell(cells[4], f"{d_rate:.0f}" if d_rate else "-")
        format_cell(cells[5], f"{d_amt:.0f}" if d_amt else "-")
        
        # Col 17 (Total)
        g_tot = clean(16)
        format_cell(cells[6], f"{g_tot:.0f}", bold=True)
        
        # Col 18 Purpose
        format_cell(cells[7], str(row.iloc[17]), font_size=8, align=WD_ALIGN_PARAGRAPH.LEFT)
        
        # Col 19 Remarks
        format_cell(cells[8], "", font_size=8)

    # Total Row
    tot_row_R = table_right.add_row()
    set_row_height(tot_row_R, row_height_cm)
    tot_row_R.cells[0].merge(tot_row_R.cells[5])
    format_cell(tot_row_R.cells[0], "કુલ સરવાળો (Grand Total)", align=WD_ALIGN_PARAGRAPH.RIGHT, bold=True)
    
    # Grand Total Calculation
    grand_sum = pd.to_numeric(ta_data.iloc[:, 16].astype(str).str.replace(r'[^\d.]', '', regex=True), errors='coerce').sum()
    format_cell(tot_row_R.cells[6], f"₹ {grand_sum:.0f}", bold=True)
    
    doc.add_page_break()

    # ================= PAGE 4: NOTES & CERTIFICATES =================
    
    p = doc.add_paragraph("નોંધ :-")
    p.runs[0].bold = True
    p.runs[0].font.size = Pt(11)
    
    # Numbered List
    notes = [
        "કોલમ નં. ૭ માં મુસાફરી પ્રકાર રેલ્વે/એસ.ટી./હવાઈ/સ્ટીમર/ભાડાનું યુનિવર્સિટી કે સરકારી કે પોતાનું વાહન ઈત્યાદી મારફત કરેલ મુસાફરીની સ્પષ્ટ નોંધ આપવી.",
        "કોલમ નં. ૧૧ થી ૧૩ માઈલેજ મેળવતા અધિકારીઓ કે સભ્યોએ ભરવી.",
        "કોલમ નં. ૧૬ માં માત્ર દૈનિક ભથ્થાની રકમ લેવી જેથી કોલમ (૧૪ X ૧૫= ૧૬) થઈ રહેવું જોઈએ.",
        "જયારે મુસાફરી ભથ્થા બીલમાં શરૂઆતમાં મુસાફરીને બદલે 'હોલ્ટ' દર્શાવવામાં આવેલ હોય તેવા કિસ્સામાં 'હોલ્ટ' ની શરૂઆત થયાની તારીખ કો.નં. ૧૯ માં દર્શાવવી."
    ]
    
    for i, note in enumerate(notes, 1):
        p = doc.add_paragraph(f"{i}. {note}")
        p.paragraph_format.left_indent = Cm(1.0)
        p.paragraph_format.first_line_indent = Cm(-0.6)

    doc.add_paragraph() # Spacer
    
    # Certificate Title
    p = doc.add_paragraph("યુનિવર્સિટી કર્મચારીએ આપવાનું પ્રમાણપત્ર")
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.runs[0].bold = True
    p.runs[0].underline = True

    certs = [
        "આથી પ્રમાણપત્ર આપવામાં આવે છે કે, આ બીલમાં આકારેલ રકમ બીજા કોઈ બીલમાં આકારેલ નથી.",
        "આથી પ્રમાણીત કરવામાં આવે છે કે સદર મુસાફરી ભથ્થા બીલમાં દર્શાવેલ હકીકત સાચી છે.",
        "આથી પ્રમાણપત્ર આપવામાં આવે છે કે બીલમાં દર્શાવેલ પ્રવાસ માટે મેં આ અગાઉ પેશગી લીધેલ નથી.",
        "આ બીલમાં જણાવેલ યુનિવર્સિટી સિવાયની અન્ય સંસ્થાની કામગીરીના પ્રવાસ માટે જે તે સંસ્થા તરફથી પ્રવાસ ભથ્થના નાણાં મને મળેલ નથી."
    ]
    
    for i, cert in enumerate(certs, 1):
        p = doc.add_paragraph(f"{i}. {cert}")
        p.paragraph_format.left_indent = Cm(1.0)
        p.paragraph_format.first_line_indent = Cm(-0.6)

    doc.add_paragraph()
    
    # Signatures
    sig_table = doc.add_table(rows=1, cols=2)
    sig_table.width = Mm(180)
    
    # Left: Place/Date
    l = sig_table.cell(0, 0)
    l.text = "સ્થળ : નવસારી\nતારીખ :"
    
    # Right: Name
    r = sig_table.cell(0, 1)
    p = r.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p.add_run(f"({emp_name})\n").bold = True
    p.add_run(f"{designation}\nકર્મચારીની સહી")

    doc.add_paragraph("_" * 70)

    # Approval Section
    p = doc.add_paragraph("મંજૂરી આદેશ")
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.runs[0].bold = True
    
    total_words = num_to_gujarati_words(int(grand_sum))
    
    p = doc.add_paragraph()
    p.add_run("સદરહુ મુસાફરી ભથ્થા બીલની કુલ રકમ રૂ. ")
    p.add_run(f"{grand_sum:.0f}").bold = True
    p.add_run(f" (અંકે રૂપિયા {total_words} પુરા) મંજુર કરવામાં આવે છે.")

    # Final Sig
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p.add_run("\n\n_______________________\n")
    p.add_run("ઉપાડ અને વહેંચણી અધિકારી\n").bold = True
    p.add_run("(સહી અને સિક્કો)")

    return doc

# --- UI PREVIEW ---
st.markdown("### 📄 Layout Preview")

col1, col2, col3, col4 = st.columns(4)
col1.info("Page 1: Header Info")
col2.info("Page 2: Table (1-10)")
col3.info("Page 3: Table (11-19)")
col4.info("Page 4: Notes & Sig")

# Button
if st.button("📄 Generate & Download Final Word File", type="primary"):
    if not df_ta.empty:
        # Generate
        doc = create_split_layout_doc(df_ta)
        
        # Save to buffer
        buffer = BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        
        st.download_button(
            label="⬇️ Download Final_TA_Bill_Split.docx",
            data=buffer,
            file_name="Final_TA_Bill_Split.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        st.balloons()
