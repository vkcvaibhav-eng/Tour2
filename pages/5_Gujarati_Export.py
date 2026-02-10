import streamlit as st
import pandas as pd
from docx import Document
from docx.shared import Cm, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_ALIGN_VERTICAL
from docx.enum.section import WD_SECTION
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from io import BytesIO
import datetime

# --- PAGE CONFIGURATION ---
st.set_page_config(layout="wide", page_title="Step 5: Final Gujarati Export")
st.title("🇮🇳 Step 5: Final Gujarati Export (Dual Page Format)")
st.markdown("---")

# --- 1. SMART INPUTS FOR HEADER DATA ---
st.sidebar.header("📝 Header Details")
st.sidebar.info("Adjust these values to appear in the top header.")

# Defaults
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
    
    # Lakhs
    if num >= 100000:
        parts.append(convert_upto_99(num // 100000) + " લાખ")
        num %= 100000
    
    # Thousands
    if num >= 1000:
        parts.append(convert_upto_99(num // 1000) + " હજાર")
        num %= 1000
        
    # Hundreds
    if num >= 100:
        parts.append(convert_upto_99(num // 100) + " સો")
        num %= 100
        
    # Remaining
    if num > 0:
        parts.append(convert_upto_99(num))
        
    return " ".join(parts).strip()

def eng_to_guj_digits(n):
    mapping = {'0':'૦','1':'૧','2':'૨','3':'૩','4':'૪','5':'૫','6':'૬','7':'૭','8':'૮','9':'૯'}
    return "".join([mapping.get(c, c) for c in str(n)])

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
    
    # ================= PAGE 1: JOURNEY DETAILS (A3 Landscape) =================
    section = doc.sections[0]
    section.page_width = Cm(42)   # Width of 2 A4 Portrait pages
    section.page_height = Cm(29.7) # Height of A4 Portrait
    section.left_margin = Cm(1.27)
    section.right_margin = Cm(1.27)
    section.top_margin = Cm(1.27)
    section.bottom_margin = Cm(1.27)

    # --- HEADER SECTION ---
    header_table = doc.add_table(rows=3, cols=3)
    header_table.autofit = False
    
    total_w = 42 - 2.54 
    w_left = total_w * 0.35
    w_mid = total_w * 0.30
    w_right = total_w * 0.35
    
    for row in header_table.rows:
        row.cells[0].width = Cm(w_left)
        row.cells[1].width = Cm(w_mid)
        row.cells[2].width = Cm(w_right)

    format_cell_text(header_table.cell(0,0), "કાર્ય મથક : કીટકશાસ્ત્ર વિભાગ, ન.મ.કૃ.મ.,ન.કૃ.યુ., નવસારી", align=WD_ALIGN_PARAGRAPH.LEFT, bold=True, font_size=11)
    format_cell_text(header_table.cell(0,1), "કચેરી : કીટકશાસ્ત્ર વિભાગ", align=WD_ALIGN_PARAGRAPH.CENTER, bold=True, font_size=12)
    format_cell_text(header_table.cell(0,2), f"કર્મચારીનુ નામ: {emp_name}", align=WD_ALIGN_PARAGRAPH.RIGHT, bold=True, font_size=11)

    format_cell_text(header_table.cell(1,1), f"હોદ્દો: {designation}", align=WD_ALIGN_PARAGRAPH.CENTER, bold=True, font_size=11)
    format_cell_text(header_table.cell(1,2), f"મૂળ પગાર: {basic_pay}", align=WD_ALIGN_PARAGRAPH.RIGHT, font_size=11)

    format_cell_text(header_table.cell(2,2), f"Level: {pay_level}  |  Pay scale: {pay_scale}", align=WD_ALIGN_PARAGRAPH.RIGHT, font_size=11)

    doc.add_paragraph() 

    # --- MAIN TABLE (19 Cols) ---
    table = doc.add_table(rows=3, cols=19)
    table.style = 'Table Grid'
    table.autofit = False 
    
    widths = [1.8, 1.8, 1.5, 1.8, 1.8, 1.5, 2.5, 1.5, 1.5, 1.8, 1.5, 1.5, 2.0, 1.5, 1.5, 2.0, 2.2, 2.2, 2.0]
    
    for row in table.rows:
        for idx, width in enumerate(widths):
            if idx < 19: row.cells[idx].width = Cm(width)

    r0 = table.rows[0].cells
    r1 = table.rows[1].cells

    # Merges & Headers
    r0[0].merge(r0[2]); format_cell_text(r0[0], "નીકળ્યા", bold=True)
    format_cell_text(r1[0], "સ્થળ"); format_cell_text(r1[1], "તારીખ"); format_cell_text(r1[2], "સમય")

    r0[3].merge(r0[5]); format_cell_text(r0[3], "આવ્યા", bold=True)
    format_cell_text(r1[3], "સ્થળ"); format_cell_text(r1[4], "તારીખ"); format_cell_text(r1[5], "સમય")

    def merge_vert(col, text):
        r0[col].merge(r1[col])
        format_cell_text(r0[col], text, bold=True, font_size=9)

    merge_vert(6, "મુસાફરીનો\nપ્રકાર"); merge_vert(7, "વર્ગ"); merge_vert(8, "ભાડાની સંખ્યા\nઅને દર"); merge_vert(9, "રકમ")

    r0[10].merge(r0[12]); format_cell_text(r0[10], "અન્ય વાહન દ્વારા રસ્તાની મુસાફરી", bold=True, font_size=9)
    format_cell_text(r1[10], "કિ.મી."); format_cell_text(r1[11], "દર"); format_cell_text(r1[12], "રકમ")

    merge_vert(13, "ભથ્થાના\nદિવસ"); merge_vert(14, "ભથ્થાનો\nદર"); merge_vert(15, "ભથ્થાની\nરકમ")
    merge_vert(16, "કુલ રકમ\n(૧૦+૧૩+૧૬)"); merge_vert(17, "મુસાફરીનું કારણ"); merge_vert(18, "વિશેષ નોંધ")

    for i in range(19): format_cell_text(table.rows[2].cells[i], str(i+1), bold=True)

    # --- DATA FILLING ---
    total_claim = 0.0
    
    if not ta_data.empty:
        for index, row in ta_data.iterrows():
            new_row = table.add_row().cells
            def get_num(idx):
                try: return float(str(row.iloc[idx]).replace('₹','').replace(',',''))
                except: return 0.0
            
            for c in [0,1,2,3,4,5,6,7,8,17]: 
                val = str(row.iloc[c]) if c < len(row) else ""
                format_cell_text(new_row[c], val)
            
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
            
            row_tot = fare + r_amt + da_a
            format_cell_text(new_row[16], f"{row_tot:.2f}", bold=True)
            total_claim += row_tot
            format_cell_text(new_row[18], "")

    # Grand Total
    tot_row = table.add_row().cells
    tot_row[0].merge(tot_row[15])
    format_cell_text(tot_row[0], "કુલ સરવાળો (Grand Total)", bold=True, align=WD_ALIGN_PARAGRAPH.RIGHT)
    format_cell_text(tot_row[16], f"₹ {total_claim:.2f}", bold=True)

    # Footer Certificate
    doc.add_paragraph()
    footer_table = doc.add_table(rows=1, cols=2)
    footer_table.autofit = False
    footer_table.rows[0].cells[0].width = Cm(25) 
    footer_table.rows[0].cells[1].width = Cm(15) 
    
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

    # ================= PAGE 2: SANCTION ORDER (A4 Portrait) =================
    # Create new section for Page 2
    section2 = doc.add_section(WD_SECTION.NEW_PAGE)
    section2.page_width = Cm(21.0) 
    section2.page_height = Cm(29.7)
    section2.left_margin = Cm(1.27)
    section2.right_margin = Cm(1.27)

    # Helper for adding formatted lines
    def add_line(text, bold=False, align=WD_ALIGN_PARAGRAPH.LEFT, size=11):
        p = doc.add_paragraph()
        p.alignment = align
        run = p.add_run(text)
        run.bold = bold
        run.font.name = 'Arial Unicode MS'
        run.font.size = Pt(size)
        return p

    # Current Date
    today_date = datetime.datetime.now().strftime("%d/%m/%Y")
    
    # Top Right Header
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = p.add_run(f"હિસાબી પત્રક નંબર\nબીલ નંબર :\nતારીખ : {today_date}")
    run.font.name = 'Arial Unicode MS'
    run.font.size = Pt(10)

    # Center Title
    add_line("નવસારી કૃષિ વિશ્વવિધાલય", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, size=14)
    add_line("મુસાફરી ભથ્થા બીલ", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, size=12)

    # Info Grid
    info_table = doc.add_table(rows=2, cols=2)
    info_table.autofit = False
    info_table.rows[0].cells[0].width = Cm(10)
    info_table.rows[0].cells[1].width = Cm(8)
    
    format_cell_text(info_table.cell(0,0), "વાઉચર નં.", align=WD_ALIGN_PARAGRAPH.LEFT)
    format_cell_text(info_table.cell(0,1), "તારીખ", align=WD_ALIGN_PARAGRAPH.LEFT)
    format_cell_text(info_table.cell(1,0), "યુનિટ નંબર :", align=WD_ALIGN_PARAGRAPH.LEFT)
    format_cell_text(info_table.cell(1,1), "કોડ નંબર :", align=WD_ALIGN_PARAGRAPH.LEFT)
    
    doc.add_paragraph() # Spacer

    # Body Text
    body_text = f"""આચાર્ય અને ડીનશ્રી, નં. મ. કૃષિ મહાવિદ્યાલય, નકૃયું, નવસારી ની કચેરીનું માહે : __________ નું
મુસાફરી ભથ્થા બિલ
યુનિટ/સબયુનિટ : આચાર્ય અને ડીનશ્રી, ન. મ. કૃષિ મહાવિદ્યાલય, નકૃયું, નવસારી
ખર્ચ માટેનું બજેટ સદર :- ______________
યોજનાનું નામ :- _______________"""
    
    for line in body_text.split('\n'):
        add_line(line, size=11)

    doc.add_paragraph() 

    # Sanction Calculation
    total_words = num_to_gujarati_words(int(total_claim))
    
    # Sanction Statement
    p_sanc = doc.add_paragraph()
    p_sanc.paragraph_format.space_before = Pt(12)
    run_sanc = p_sanc.add_run(f"આથી રૂા. {total_claim:.2f} ( {total_words} પુરા )")
    run_sanc.font.name = 'Arial Unicode MS'
    run_sanc.font.size = Pt(11)
    
    p_sanc2 = doc.add_paragraph()
    run_sanc2 = p_sanc2.add_run(f"આ બીલમાં જણાવેલ રૂા. {total_claim:.2f} મંજુર કરવામાં આવે છે. અને તે રોકડા / ચેક નં. ____________ તા. ____________ થી ચુકવવામાં આવે છે.")
    run_sanc2.font.name = 'Arial Unicode MS'
    run_sanc2.font.size = Pt(11)

    doc.add_paragraph()
    doc.add_paragraph()

    # Signatures
    sig_table = doc.add_table(rows=1, cols=2)
    sig_table.autofit = False
    sig_table.rows[0].cells[0].width = Cm(9)
    sig_table.rows[0].cells[1].width = Cm(9)

    # Left Side: Place/Date & Amounts
    left_cell = sig_table.cell(0,0)
    lp = left_cell.paragraphs[0]
    lp.add_run(f"સ્થળ : નવસારી\nતારીખ : {today_date}\n\n").font.name = 'Arial Unicode MS'
    
    # Final Summary Table (Inside Left Cell)
    # The user wanted specific lines here
    lp.add_run(f"રૂ. ({total_claim:.2f})").bold = True
    lp.add_run(f"\nઅંકે રૂપિયા : {total_words} પુરા").font.name = 'Arial Unicode MS'

    # Right Side: Officer Signature
    right_cell = sig_table.cell(0,1)
    rp = right_cell.paragraphs[0]
    rp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    rp.add_run("\n\n\nબીલ મંજુર કરનાર અધિકારીની\nસહી અને હોદ્દો").font.name = 'Arial Unicode MS'

    doc.add_paragraph()
    
    # Bottom Summary Table
    sum_table = doc.add_table(rows=3, cols=2)
    sum_table.style = 'Table Grid'
    sum_table.autofit = False
    sum_table.rows[0].cells[0].width = Cm(12)
    sum_table.rows[0].cells[1].width = Cm(6)

    format_cell_text(sum_table.cell(0,0), "બીલની કુલ રકમ", align=WD_ALIGN_PARAGRAPH.LEFT)
    format_cell_text(sum_table.cell(0,1), f"{total_claim:.2f}", align=WD_ALIGN_PARAGRAPH.RIGHT)

    format_cell_text(sum_table.cell(1,0), "બાદ લીધેલ પેશગીની રકમ", align=WD_ALIGN_PARAGRAPH.LEFT)
    format_cell_text(sum_table.cell(1,1), "0.00", align=WD_ALIGN_PARAGRAPH.RIGHT)

    format_cell_text(sum_table.cell(2,0), "ચૂકવવાપાત્ર ચોખ્ખી રકમ", align=WD_ALIGN_PARAGRAPH.LEFT, bold=True)
    format_cell_text(sum_table.cell(2,1), f"{total_claim:.2f}", align=WD_ALIGN_PARAGRAPH.RIGHT, bold=True)

    doc.add_paragraph()
    add_line(f"બીલની રકમ રૂ. {total_claim:.2f}", bold=True)

    return doc

# --- MAIN UI ---
if st.button("📄 Generate Final Dual-Page File"):
    if not df_ta.empty:
        doc = create_gujarati_doc(df_ta)
        buffer = BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        st.download_button("⬇️ Download Final_TA_Bill.docx", buffer, "Final_TA_Bill.docx")
        st.balloons()
