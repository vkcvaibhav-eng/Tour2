import streamlit as st
import pandas as pd
from docx import Document
from docx.shared import Cm, Mm, Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.enum.section import WD_SECTION
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from io import BytesIO
import datetime

# --- PAGE CONFIGURATION ---
st.set_page_config(layout="wide", page_title="Step 5: Final Gujarati Export")
st.title("🇮🇳 Step 5: Final Gujarati Export")
st.markdown("---")

# --- 1. SMART INPUTS FOR HEADER DATA ---
st.sidebar.header("📝 Header Details")

# Defaults
emp_name = st.sidebar.text_input("Employee Name", "વી. કે. ચૌધરી")
designation = st.sidebar.text_input("Designation", "સીનીયર એક્રોલોજીસ્ટ")
basic_pay = st.sidebar.text_input("Basic Pay (મૂળ પગાર)", "₹ 67,700") 
pay_level = st.sidebar.text_input("Pay Level", "Level-11")
pay_scale = st.sidebar.text_input("Pay Scale", "67700 - 208700")
voucher_month = st.sidebar.text_input("Bill Month (e.g., ઓક્ટોમ્બર - ૨૦૨૫)", "ફેબ્રુઆરી - ૨૦૨૬")

# --- DATA CONNECTION ---
if 'final_18_col_df' in st.session_state:
    df_ta = st.session_state['final_18_col_df'].copy()
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

# --- DOCX HELPER FUNCTIONS ---
def format_cell_text(cell, text, font_size=9, bold=False, align=WD_ALIGN_PARAGRAPH.CENTER, font_name='Arial Unicode MS'):
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
    
    # Calculate Totals
    total_claim = 0.0
    if not ta_data.empty:
        # Col 17 is usually the total
        total_claim = pd.to_numeric(ta_data.iloc[:, 16], errors='coerce').sum()
    
    total_words = num_to_gujarati_words(int(total_claim))

    # ================= PAGE 1: JOURNEY DETAILS (A3 Landscape) =================
    # This keeps your original detailed table
    section = doc.sections[0]
    section.page_width = Cm(42)   
    section.page_height = Cm(29.7) 
    section.left_margin = Cm(1.27)
    section.right_margin = Cm(1.27)
    section.top_margin = Cm(1.27)
    section.bottom_margin = Cm(1.27)

    # --- HEADER SECTION ---
    header_table = doc.add_table(rows=3, cols=3)
    header_table.autofit = False
    total_w = 42 - 2.54 
    w_left = total_w * 0.35; w_mid = total_w * 0.30; w_right = total_w * 0.35
    for row in header_table.rows:
        row.cells[0].width = Cm(w_left); row.cells[1].width = Cm(w_mid); row.cells[2].width = Cm(w_right)

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

    r0 = table.rows[0].cells; r1 = table.rows[1].cells
    r0[0].merge(r0[2]); format_cell_text(r0[0], "નીકળ્યા", bold=True)
    format_cell_text(r1[0], "સ્થળ"); format_cell_text(r1[1], "તારીખ"); format_cell_text(r1[2], "સમય")
    r0[3].merge(r0[5]); format_cell_text(r0[3], "આવ્યા", bold=True)
    format_cell_text(r1[3], "સ્થળ"); format_cell_text(r1[4], "તારીખ"); format_cell_text(r1[5], "સમય")
    
    def merge_vert(col, text):
        r0[col].merge(r1[col]); format_cell_text(r0[col], text, bold=True, font_size=9)
    merge_vert(6, "મુસાફરીનો\nપ્રકાર"); merge_vert(7, "વર્ગ"); merge_vert(8, "ભાડાની સંખ્યા\nઅને દર"); merge_vert(9, "રકમ")
    r0[10].merge(r0[12]); format_cell_text(r0[10], "અન્ય વાહન દ્વારા રસ્તાની મુસાફરી", bold=True, font_size=9)
    format_cell_text(r1[10], "કિ.મી."); format_cell_text(r1[11], "દર"); format_cell_text(r1[12], "રકમ")
    merge_vert(13, "ભથ્થાના\nદિવસ"); merge_vert(14, "ભથ્થાનો\nદર"); merge_vert(15, "ભથ્થાની\nરકમ")
    merge_vert(16, "કુલ રકમ\n(૧૦+૧૩+૧૬)"); merge_vert(17, "મુસાફરીનું કારણ"); merge_vert(18, "વિશેષ નોંધ")
    for i in range(19): format_cell_text(table.rows[2].cells[i], str(i+1), bold=True)

    # Fill Data
    if not ta_data.empty:
        for index, row in ta_data.iterrows():
            new_row = table.add_row().cells
            def get_num(idx):
                try: return float(str(row.iloc[idx]).replace('₹','').replace(',',''))
                except: return 0.0
            for c in [0,1,2,3,4,5,6,7,8,17]: 
                val = str(row.iloc[c]) if c < len(row) else ""
                format_cell_text(new_row[c], val)
            fare = get_num(9); format_cell_text(new_row[9], f"{fare:.2f}")
            km, r_rate, r_amt = get_num(10), get_num(11), get_num(12)
            format_cell_text(new_row[10], f"{km:.1f}" if km else "-"); format_cell_text(new_row[11], f"{r_rate:.1f}" if r_rate else "-"); format_cell_text(new_row[12], f"{r_amt:.2f}")
            da_d, da_r, da_a = get_num(13), get_num(14), get_num(15)
            format_cell_text(new_row[13], f"{da_d}" if da_d else ""); format_cell_text(new_row[14], f"{da_r}" if da_r else ""); format_cell_text(new_row[15], f"{da_a:.2f}" if da_a else "")
            row_tot = fare + r_amt + da_a
            format_cell_text(new_row[16], f"{row_tot:.2f}", bold=True); format_cell_text(new_row[18], "")

    tot_row = table.add_row().cells; tot_row[0].merge(tot_row[15])
    format_cell_text(tot_row[0], "કુલ સરવાળો (Grand Total)", bold=True, align=WD_ALIGN_PARAGRAPH.RIGHT)
    format_cell_text(tot_row[16], f"₹ {total_claim:.2f}", bold=True)

    # ================= PAGE 2 & 3: SANCTION & RECEIPT (NEW LAYOUT) =================
    section2 = doc.add_section(WD_SECTION.NEW_PAGE)
    section2.page_height = Mm(297)
    section2.page_width = Mm(210)
    section2.left_margin = Mm(20)
    section2.right_margin = Mm(15)
    section2.top_margin = Mm(15)
    section2.bottom_margin = Mm(15)

    style = doc.styles['Normal']
    font = style.font
    font.name = 'Arial Unicode MS' 
    font.size = Pt(11)

    # Top Right: Hisabi Patrak
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = p.add_run("હિસાબી પત્રક નંબર ____________")
    
    # Center Header
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("નવસારી કૃષિ વિશ્વવિધાલય\n")
    run.bold = True
    run.font.size = Pt(16)
    run = p.add_run("મુસાફરી ભથ્થા બીલ")
    run.bold = True
    run.font.size = Pt(14)

    # Info Table (Bill No vs Voucher No)
    table = doc.add_table(rows=1, cols=2)
    table.width = Mm(175)
    table.autofit = False
    
    # Left Column
    cell_l = table.cell(0, 0)
    cell_l.width = Mm(80)
    p = cell_l.paragraphs[0]
    p.add_run("બીલ નંબર :\nતારીખ        :")
    p.runs[0].bold = True

    # Right Column
    cell_r = table.cell(0, 1)
    cell_r.width = Mm(95)
    p = cell_r.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p.add_run("વાઉચર નં. ____________________\n")
    p.add_run("તારીખ ____________________\n")
    p.add_run("યુનિટ નંબર : __________________\n")
    p.add_run("કોડ નંબર : ____________________")

    doc.add_paragraph() # Spacer

    # Main Body Text
    p = doc.add_paragraph(f"આચાર્ય અને ડીનશ્રી, નં. મ. કૃષિ મહાવિદ્યાલય, નકૃયું, નવસારી ની કચેરીનું માહે: {voucher_month} નું")
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.runs[0].bold = True

    p = doc.add_paragraph("મુસાફરી ભથ્થા બિલ")
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.runs[0].bold = True
    p.runs[0].underline = True
    p.runs[0].font.size = Pt(14)

    p = doc.add_paragraph("યુનિટ/સબયુનિટ : આચાર્ય અને ડીનશ્રી, ન. મ. કૃષિ મહાવિદ્યાલય, નકૃયું, નવસારી")
    p = doc.add_paragraph("ખર્ચ માટેનું બજેટ સદર :- ____________________")
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p = doc.add_paragraph("યોજનાનું નામ :- ____________________")
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    doc.add_paragraph() # Spacer

    # Claim Amount
    p = doc.add_paragraph()
    p.add_run("આથી રૂ।. ")
    r = p.add_run(f" {total_claim:.0f} ")
    r.bold = True
    r.underline = True
    p.add_run(" નો દાવો મંજુર કરી ગ્રાહય રાખવામાં આવે છે.")

    # Boxed Amount Area (Simulated with borders)
    tbl_amt = doc.add_table(rows=1, cols=1)
    tbl_amt.style = 'Table Grid'
    cell = tbl_amt.cell(0,0)
    p = cell.paragraphs[0]
    p.add_run("આ બીલમાં જણાવેલ રૂા  ")
    p.add_run(f"{total_claim:.0f}").bold = True
    p.add_run("  ( અંકે રૂપિયા ")
    p.add_run(f"{total_words} પુરા").bold = True
    p.add_run(" પૈસા )\n\n")
    p.add_run("મંજુર કરવામાં આવે છે. અને તે રોકડા / ચેક નં. ______________ તા. ___________ થી ચુકવવામાં આવે છે.")

    doc.add_paragraph() # Spacer

    # Signatures
    sig_table = doc.add_table(rows=1, cols=2)
    sig_table.width = Mm(175)
    
    l_cell = sig_table.cell(0, 0)
    l_cell.text = "સ્થળ :    નવસારી\nતારીખ :"
    
    r_cell = sig_table.cell(0, 1)
    p = r_cell.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run("____________________\n")
    p.add_run("બીલ મંજુર કરનાર અધિકારીની\nસહી અને હોદ્દો")

    doc.add_paragraph() # Spacer

    # Budget Table
    b_table = doc.add_table(rows=4, cols=3)
    b_table.style = 'Table Grid'
    hdr_cells = b_table.rows[0].cells
    hdr_cells[0].text = ""
    hdr_cells[1].text = "રૂ."
    hdr_cells[2].text = "પૈસા"
    
    b_table.cell(1, 0).text = "(૧) સને ૨૦૨૪-૨૫ માટે બજેટમાં મંજુર થયેલ રકમ"
    b_table.cell(2, 0).text = "(૨) આ બીલ સાથે થયેલ કુલ ખર્ચ"
    b_table.cell(3, 0).text = "(૩) ખર્ચ માટે બાકી રહેતી રકમ"

    doc.add_paragraph() # Spacer

    # Bottom Signature
    p = doc.add_paragraph()
    p.add_run(f"રૂા ( {total_claim:.0f} ) અંકે રૂપિયા : {total_words} પુરા મંજુર કર્યા")
    
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p.add_run("નિયંત્રણ અધિકારીની સહી___________").bold = True

    doc.add_page_break()

    # --- PAGE 3: CERTIFICATES & RECEIPT ---

    p = doc.add_paragraph("નોંધ :-")
    p.runs[0].bold = True
    
    notes = [
        "કોલમ નં. ૭ માં મુસાફરી પ્રકાર રેલ્વે/એસ.ટી./હવાઈ/સ્ટીમર/ભાડાનું યુનિવર્સિટી કે સરકારી કે પોતાનું વાહન ઈત્યાદી મારફત કરેલ મુસાફરીની સ્પષ્ટ નોંધ આપવી.",
        "કોલમ નં. ૧૧ થી ૧૩ માઈલેજ મેળવતા અધિકારીઓ કે સભ્યોએ ભરવી.",
        "કોલમ નં. ૧૬ માં માત્ર દૈનિક ભથ્થાની રકમ લેવી જેથી કોલમ (૧૪ X ૧૫= ૧૬) થઈ રહેવું જોઈએ.",
        "જયારે મુસાફરી ભથ્થા બીલમાં શરૂઆતમાં મુસાફરીને બદલે 'હોલ્ટ' દર્શાવવામાં આવેલ હોય તેવા કિસ્સામાં 'હોલ્ટ' ની શરૂઆત થયાની તારીખ કો.નં. ૧૯ માં દર્શાવવી."
    ]
    for note in notes:
        doc.add_paragraph(note, style='List Number')

    doc.add_paragraph()
    p = doc.add_paragraph("યુનિવર્સિટી કર્મચારીએ આપવાનું પ્રમાણપત્ર")
    p.runs[0].bold = True
    
    certs = [
        "આથી પ્રમાણપત્ર આપવામાં આવે છે કે, આ બીલમાં આકારેલ રકમ બીજા કોઈ બીલમાં આકારેલ નથી.",
        "આથી પ્રમાણીત કરવામાં આવે છે કે સદર મુસાફરી ભથ્થ બીલમાં દર્શાવેલ હકીકત સાચી છે અને સદર મુસાફરી ભથ્થા બીલમાં કરવામાં આવેલ દાવો વખતો વખત સુધારવામાં આવેલ ગુજરાત કૃષિ વિશ્વવિધાલય મુસાફરી ભથ્થા નિયમોના ૬૫-૧ ના અનુમાનોને આધારે સાચો છે.",
        "આથી પ્રમાણપત્ર આપવામાં આવે છે કે બીલમાં દર્શાવેલ પ્રવાસ માટે મેં આ અગાઉ પેશગી લીધેલ નથી. / મે પેશગી લીધેલ છે જેની વિગત નીચે દર્શાવેલ છે.  (લાગુ ન પડતી બાબત છેકી નાખવી અને તે બદલ સહી કરવી.)",
        "આ બીલમાં જણાવેલ યુનિવર્સિટી સિવાયની અન્ય સંસ્થાની કામગીરીના પ્રવાસ માટે જે તે સંસ્થા તરફથી પ્રવાસ ભથ્થના નાણાં મને મળેલ નથી અને જે તે સંસ્થા તરફથી નાણાં મળશે તો તે રકમ થુનિવર્સિટી ફંડમાં જમા કરાવવામાં આવશે.",
        "આથી પ્રમાણપત્ર આપવામાં આવે છે કે, પ્રવાસ ડાયરીમાં દર્શાવવામાં આવેલ સ્થળ, તારીખ, સમય, કિલોમીટર કચેરીના વાહન લોગબુક મુજબ આકારવામાં આવેલ છે."
    ]
    for cert in certs:
        doc.add_paragraph(cert, style='List Number')

    # Employee Signature
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p.add_run(f"({emp_name})\n").bold = True
    p.add_run(f"{designation}\nકર્મચારીની સહી નામ અને હોદ્દો")

    doc.add_paragraph("_" * 50) # Horizontal Line simulation

    # Officer Cert
    p = doc.add_paragraph("યુનિવર્સિટી અધિકારીઓ અને અન્ય સભ્યોએ આપવાનું પ્રમાણપત્ર")
    p.runs[0].bold = True
    doc.add_paragraph("આથી પ્રમાણિત કરવામાં આવે છે કે સદર બીલમાં કરેલ મુસાફરી ભથ્થાનો દાવો આ અંગેના નિયમોની જોગવાઈઓના આધારે ખરો અને યોગ્ય છે.")

    # Officer Signature
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p.add_run("_______________________\n")
    p.add_run("પ્રાધ્યાપક અને વડા\nકિટકશાત્ર વિભાગ\nનં. મ. કૃષિ મહાવિદ્યાલય\nનકૃયું, નવસારી").bold = True

    doc.add_paragraph()

    # --- FINAL SPLIT TABLE (CALCULATION & RECEIPT) ---
    p = doc.add_paragraph("કર્મચારી / અધિકારી / સભ્યશ્રીએ નીચેની વિગત ભરવી.")
    p.runs[0].bold = True

    final_table = doc.add_table(rows=1, cols=2)
    final_table.style = 'Table Grid'
    final_table.allow_autofit = False
    
    # Left Cell (Calculation)
    c1 = final_table.cell(0, 0)
    c1.width = Mm(90)
    p = c1.paragraphs[0]
    p.add_run(f"બીલની કુલ રકમ\t= {total_claim:.0f}\n")
    p.add_run("બાદ બીલની પેશગીની રકમ\t=\n")
    p.add_run(f"ચૂકવવા પાત્ર ચોખ્ખી રકમ\t= {total_claim:.0f}\n\n")
    p.add_run("પેશગીના નાણાં મળ્યાની તા.\n")
    p.add_run("પેશગી કયા ઝોન /યુનિટમાંથી\t નીલ\nઉપાડવામાં આવી.\n\n")
    p.add_run("પેશગી ઉપાડવાના વાઉચર નંબર ______ તારીખ _____")

    # Right Cell (Receipt)
    c2 = final_table.cell(0, 1)
    c2.width = Mm(90)
    p = c2.paragraphs[0]
    p.add_run(f"બીલની રકમ રૂ. {total_claim:.0f}\n").bold = True
    p.add_run(f"અંકે રૂપિયા {total_words} પુરા\n").bold = True
    p.add_run("મને મળ્યા છે.\n\n")
    p.add_run("સ્થળ : નવસારી\n")
    p.add_run("તારીખ :\n\n\n")
    p.add_run(f"                                ({emp_name})\n").bold = True
    p.add_run(f"                                {designation}")

    return doc

# --- MAIN UI ---

# Calculate totals for preview
total_claim_val = 0.0
total_words_str = "શૂન્ય"
if not df_ta.empty:
    total_claim_val = pd.to_numeric(df_ta.iloc[:, 16], errors='coerce').sum()
    total_words_str = num_to_gujarati_words(int(total_claim_val))

# HTML PREVIEW OF THE NEW LAYOUT
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+Gujarati:wght@400;600;700&display=swap');
    .a4-page {
        background-color: white; color: black; width: 210mm; min-height: 297mm;
        padding: 15mm 20mm; margin: 10px auto;
        font-family: 'Noto Sans Gujarati', sans-serif; font-size: 13px; line-height: 1.5;
        box-shadow: 0 0 15px rgba(0,0,0,0.5);
    }
    .input-line { border-bottom: 1px solid black; display: inline-block; padding: 0 5px; }
    table.budget-table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 12px; }
    table.budget-table th, table.budget-table td { border: 1px solid black; padding: 8px; vertical-align: middle; }
    table.budget-table th { text-align: center; font-weight: bold; }
    table.budget-table td { height: 35px; }
    .flex-row { display: flex; justify-content: space-between; align-items: flex-end; }
    .center { text-align: center; }
    .right { text-align: right; }
</style>
""", unsafe_allow_html=True)

page2_preview = f"""
<div class="a4-page">
    <div class="right" style="margin-bottom: 10px; font-size: 12px;">
    હિસાબી પત્રક નંબર <span class="input-line" style="width:100px;"></span>
    </div>
    <div class="center">
    <div style="font-size: 22px; font-weight: 700;">નવસારી કૃષિ વિશ્વવિધાલય</div>
    <div style="font-size: 16px; font-weight: 700; margin-top: 5px;">મુસાફરી ભથ્થા બીલ</div>
    </div>
    <div class="flex-row" style="margin-top: 20px;">
    <div style="width: 40%; font-weight: 700; font-size: 14px;">
    <div style="margin-bottom: 10px;">બીલ નંબર :</div>
    <div>તારીખ &nbsp;&nbsp;&nbsp;:</div>
    </div>
    <div style="width: 50%; text-align: right; font-size: 12px;">
    <div style="margin-bottom: 5px;">વાઉચર નં. <span class="input-line" style="width:180px;"></span></div>
    <div style="margin-bottom: 5px;">તારીખ <span class="input-line" style="width:180px;"></span></div>
    <div style="margin-bottom: 5px;">યુનિટ નંબર : <span class="input-line" style="width:165px;"></span></div>
    <div>કોડ નંબર : <span class="input-line" style="width:180px;"></span></div>
    </div>
    </div>
    <div class="center" style="margin-top: 20px; font-weight: 700; font-size: 12px;">
    આચાર્ય અને ડીનશ્રી, નં. મ. કૃષિ મહાવિદ્યાલય, નકૃયું, નવસારી ની કચેરીનું માહે: {voucher_month} નું
    </div>
    <div class="center" style="margin-top: 5px;">
    <span style="font-size: 16px; font-weight: 700; border-bottom: 2px solid black; padding-bottom: 2px;">મુસાફરી ભથ્થા બિલ</span>
    </div>
    <div style="margin-top: 20px; font-weight: 600; font-size: 12px;">
    યુનિટ/સબયુનિટ : આચાર્ય અને ડીનશ્રી, ન. મ. કૃષિ મહાવિદ્યાલય, નકૃયું, નવસારી
    </div>
    <div class="center" style="margin-top: 15px; font-weight: 600;">
    ખર્ચ માટેનું બજેટ સદર :-
    </div>
    <div class="center" style="margin-top: 5px; font-weight: 600;">
    યોજનાનું નામ :-
    </div>
    <div style="margin-top: 15px; font-size: 14px;">
    આથી રૂા. <span class="input-line" style="width: 150px; text-align:center; font-weight:bold;">{total_claim_val:.0f}</span> ના દાવો મંજુર કરી ગ્રાહય રાખવામાં આવે છે.
    </div>
    <div style="margin-top: 10px; border-top: 1px solid black; padding-top: 10px;">
    <div style="line-height: 2;">
    આ બીલમાં જણાવેલ રૂા <span class="input-line" style="width: 80px; text-align:center; font-weight:bold;">{total_claim_val:.0f}</span> (
    <span style="margin-left: 20px;">અંકે રૂપિયા <span style="font-weight:bold; font-size:14px;">{total_words_str} પુરા</span></span>
    <span style="float:right;">પૈસા)</span>
    <br>
    મંજુર કરવામાં આવે છે. અને તે રોકડા / ચેક નં. <span class="input-line" style="width: 150px;"></span> તા. <span class="input-line" style="width: 100px;"></span> થી ચુકવવામાં આવે છે.
    </div>
    </div>
    <hr style="border-top: 2px solid black; margin: 15px 0;">
    <table class="budget-table">
    <colgroup><col style="width: 70%;"><col style="width: 15%;"><col style="width: 15%;"></colgroup>
    <thead>
    <tr><th rowspan="2" style="text-align:left; border-bottom: none;"></th><th>રૂ.</th><th>પૈસા</th></tr>
    <tr><th style="height:20px;"></th><th style="height:20px;"></th></tr>
    </thead>
    <tbody>
    <tr><td>(૧) સને ૨૦૨૪-૨૫ માટે બજેટમાં મંજુર થયેલ રકમ</td><td></td><td></td></tr>
    <tr><td>(૨) આ બીલ સાથે થયેલ કુલ ખર્ચ</td><td></td><td></td></tr>
    <tr><td>(૩) ખર્ચ માટે બાકી રહેતી રકમ</td><td></td><td></td></tr>
    </tbody>
    </table>
</div>
"""

page3_preview = f"""
<div class="a4-page">
    <div style="font-size: 11px;">
    <strong>નોંધ :-</strong>
    <ol style="margin-top: 5px; padding-left: 20px; margin-bottom: 10px;">
    <li>કોલમ નં. ૭ માં મુસાફરી પ્રકાર રેલ્વે/એસ.ટી./હવાઈ/સ્ટીમર/ભાડાનું યુનિવર્સિટી કે સરકારી કે પોતાનું વાહન ઈત્યાદી મારફત કરેલ મુસાફરીની સ્પષ્ટ નોંધ આપવી.</li>
    <li>કોલમ નં. ૧૧ થી ૧૩ માઈલેજ મેળવતા અધિકારીઓ કે સભ્યોએ ભરવી.</li>
    </ol>
    </div>
    <div style="margin-top: 10px;">
    <strong>યુનિવર્સિટી કર્મચારીએ આપવાનું પ્રમાણપત્ર</strong>
    <ol style="margin-top: 5px; padding-left: 20px;">
    <li>આથી પ્રમાણપત્ર આપવામાં આવે છે કે, આ બીલમાં આકારેલ રકમ બીજા કોઈ બીલમાં આકારેલ નથી.</li>
    <li>આથી પ્રમાણીત કરવામાં આવે છે કે સદર મુસાફરી ભથ્થા બીલમાં દર્શાવેલ હકીકત સાચી છે...</li>
    <li>આથી પ્રમાણપત્ર આપવામાં આવે છે કે બીલમાં દર્શાવેલ પ્રવાસ માટે મેં આ અગાઉ પેશગી લીધેલ નથી...</li>
    </ol>
    </div>
    <div class="flex-row" style="margin-top: 20px;">
    <div></div>
    <div style="text-align: center;">
    <strong>({emp_name})</strong><br>
    {designation}<br>
    કર્મચારીની સહી નામ અને હોદ્દો
    </div>
    </div>
    <div style="margin-top: 20px; font-weight: 700; font-size: 13px; border-bottom: 2px solid black; padding-bottom: 2px;">
    કર્મચારી / અધિકારી / સભ્યશ્રીએ નીચેની વિગત ભરવી.
    </div>
    <div style="display: flex; border-bottom: 2px solid black;">
    <div style="width: 50%; border-right: 2px solid black; padding: 10px 10px 10px 0; font-weight: 600;">
    <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
    <span>બીલની કુલ રકમ</span><span style="font-weight: 700; font-size: 14px;">= &nbsp;&nbsp; {total_claim_val:.0f}</span>
    </div>
    <div style="display: flex; justify-content: space-between; margin-bottom: 15px;">
    <span>ચૂકવવા પાત્ર ચોખ્ખી રકમ</span><span style="font-weight: 700; font-size: 14px;">= &nbsp;&nbsp; {total_claim_val:.0f}</span>
    </div>
    </div>
    <div style="width: 50%; padding: 10px 0 10px 10px; position: relative; font-weight: 600;">
    <div style="margin-bottom: 5px;">બીલની રકમ રૂ. <span style="font-weight: 700; border-bottom: 1px solid black; font-size: 14px;">{total_claim_val:.0f}</span></div>
    <div style="margin-bottom: 15px;">અંકે રૂપિયા <span style="font-weight: 700; border-bottom: 1px solid black; font-size: 14px;">{total_words_str} પુરા</span></div>
    <div style="margin-bottom: 20px;">મને મળ્યા છે.</div>
    <div style="text-align: center; position: absolute; bottom: 10px; right: 10px;">
    <div style="font-weight: 700;">({emp_name})</div>
    </div>
    </div>
    </div>
</div>
"""

st.subheader("📄 Preview: Final Bill Layout (Pages 2 & 3)")
c1, c2 = st.columns(2)
with c1: st.markdown(page2_preview, unsafe_allow_html=True)
with c2: st.markdown(page3_preview, unsafe_allow_html=True)

if st.button("📄 Generate Final Dual-Page File", type="primary"):
    if not df_ta.empty:
        doc = create_gujarati_doc(df_ta)
        buffer = BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        st.download_button("⬇️ Download Final_TA_Bill.docx", buffer, "Final_TA_Bill.docx")
        st.balloons()
