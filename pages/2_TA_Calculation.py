import streamlit as st
import pandas as pd
import utils
import os
import json
import glob

st.set_page_config(layout="wide", page_title="Step 2: TA Calculation")
st.title("🧮 Step 2: TA Calculation")

# --- VALIDATION ---
if 'final_tour_diary' not in st.session_state:
    st.error("⚠️ Please complete Step 1 (Tour Diary) first.")
    st.stop()
    
if not st.session_state.get('gemini_api_key'):
    st.error("⚠️ Please go to 'Home' and set your API Key.")
    st.stop()

# ==========================================
# SECTION 1: DOCUMENTS & RULES
# ==========================================
st.subheader("1. 📂 Documents & Rules")

col_rules, col_tickets = st.columns(2)

# --- A. PERMANENT RULES (Saved to Disk) ---
with col_rules:
    st.markdown("**📜 Rules & Statutes (Permanent)**")
    uploaded_rules = st.file_uploader("Upload New Rule (PDF)", accept_multiple_files=True, key="new_rules")
    
    if uploaded_rules:
        if st.button("💾 Save Rules Permanently"):
            for f in uploaded_rules:
                utils.save_permanent_rule(f)
            st.success("Rules saved!")
            st.rerun()

    # Show Saved Rules
    saved_rules = utils.list_saved_rules()
    if saved_rules:
        with st.expander(f"✅ Active Rules ({len(saved_rules)})"):
            for r in saved_rules:
                st.caption(f"📄 {r}")
    else:
        st.warning("No permanent rules found.")

# --- B. SESSION EVIDENCE (Tickets/Bills) ---
with col_tickets:
    st.markdown("**🎫 Trip Evidence (Tickets/Enquiry)**")
    session_tickets = st.file_uploader("Upload Tickets for THIS Tour", accept_multiple_files=True, key="current_tickets")

st.markdown("---")

# ==========================================
# SECTION 2: INITIALIZE TABLE
# ==========================================
diary_df = st.session_state['final_tour_diary']

if 'ta_calculation_df' not in st.session_state:
    # 1. Copy Diary Columns (1-7)
    ta_df = diary_df[["Departure_Place", "Departure_Date", "Departure_Time", 
                      "Arrival_Place", "Arrival_Date", "Arrival_Time", 
                      "Mode_of_Travel"]].copy()
    
    # 2. Add TA Columns (8-13)
    # Col 8: Class / Vehicle No
    ta_df["Class_of_Travel"] = ta_df.apply(
        lambda x: "Govt. Vehicle" if "University" in str(x["Mode_of_Travel"]) or "Govt" in str(x["Mode_of_Travel"]) else "Ordinary", 
        axis=1
    )
    ta_df["Ticket_Price_Rate"] = 0.0      # Col 9 (Fare or Bus Fare Equiv)
    ta_df["Actual_Ticket_Amount"] = 0.0   # Col 10 (Total Ticket)
    ta_df["Kilometer"] = 0.0              # Col 11 (Distance)
    ta_df["Rate_per_KM"] = 0.0            # Col 12 (Only for Auto)
    ta_df["Mileage_Total"] = 0.0          # Col 13 (Calculated)
    
    st.session_state['ta_calculation_df'] = ta_df

# ==========================================
# SECTION 3: AI AUTO-FILL (Using Rules & Tickets)
# ==========================================
if st.button("🤖 Auto-Fill Costs using AI"):
    if not session_tickets and not saved_rules:
        st.warning("Please upload Tickets or Rules first.")
    else:
        with st.spinner("AI is analyzing tickets against your Diary..."):
            
            # Prepare Data for Context
            diary_json = st.session_state['ta_calculation_df'].to_json(orient="records")
            
            # Prepare Prompt
            prompt = f"""
            I have a Tour Diary: {diary_json}
            
            Based on the attached Tickets and Rules:
            1. Match the tickets to the journey rows.
            2. For 'Private Vehicle', if a Fare Enquiry is attached, find the Bus Fare Equivalent.
            3. For 'Auto Rickshaw', look for distance or rate rules.
            4. For 'Bus/Rail', find the ticket price.
            
            Return a JSON object:
            {{
                "ta_updates": [
                    {{
                        "Departure_Place": "...",
                        "Arrival_Place": "...",
                        "Ticket_Price_Rate": 123.00,
                        "Kilometer": 45.5,
                        "Class_of_Travel": "First Class"
                    }}
                ]
            }}
            Only include rows where you found data.
            """
            
            # Collect all files (Rules + Tickets)
            all_files_to_send = session_tickets if session_tickets else []
            # We don't send rule paths here directly in this snippet for simplicity, 
            # but utils.call_gemini_extraction usually handles the rules folder automatically.
            
            response = utils.call_gemini_extraction(
                st.session_state['gemini_api_key'],
                all_files_to_send, 
                prompt
            )
            
            # Parse & Update DataFrame
            try:
                updates = utils.clean_and_parse_json(response).get("ta_updates", [])
                
                for update in updates:
                    # Find matching row
                    mask = (st.session_state['ta_calculation_df']["Departure_Place"] == update.get("Departure_Place")) & \
                           (st.session_state['ta_calculation_df']["Arrival_Place"] == update.get("Arrival_Place"))
                    
                    if mask.any():
                        if update.get("Ticket_Price_Rate"):
                            st.session_state['ta_calculation_df'].loc[mask, "Ticket_Price_Rate"] = float(update["Ticket_Price_Rate"])
                        if update.get("Kilometer"):
                            st.session_state['ta_calculation_df'].loc[mask, "Kilometer"] = float(update["Kilometer"])
                        if update.get("Class_of_Travel"):
                            st.session_state['ta_calculation_df'].loc[mask, "Class_of_Travel"] = update["Class_of_Travel"]
                            
                st.success("✅ Costs updated from documents!")
                st.rerun()
            except Exception as e:
                st.error(f"AI Update Failed: {e}")

# ==========================================
# SECTION 4: SMART FILL (The "Old Code" Logic)
# ==========================================
st.divider()
df = st.session_state['ta_calculation_df']

# Identify Missing Info
pvt_mask = df["Mode_of_Travel"].str.contains("Private|Car|Jeep", case=False, na=False)
missing_pvt = df[pvt_mask & ((df["Ticket_Price_Rate"] == 0) | (df["Kilometer"] == 0))]

auto_mask = df["Mode_of_Travel"].str.contains("Auto|Rickshaw|Taxi", case=False, na=False)
missing_auto = df[auto_mask & ((df["Kilometer"] == 0) | (df["Rate_per_KM"] == 0))]

attention = missing_pvt.index.union(missing_auto.index)

if not attention.empty:
    st.warning(f"⚠️ Found {len(attention)} rows needing manual Rates or Distances.")
    with st.expander("📝 Smart Fill: Add Missing Details", expanded=True):
        pending_df = df.loc[attention, ["Departure_Place", "Arrival_Place", "Mode_of_Travel"]].drop_duplicates()
        
        for i, row in pending_df.iterrows():
            dep, arr, mode = row["Departure_Place"], row["Arrival_Place"], row["Mode_of_Travel"]
            
            # Find current values
            current = df[(df["Departure_Place"]==dep) & (df["Arrival_Place"]==arr) & (df["Mode_of_Travel"]==mode)].iloc[0]
            
            c1, c2, c3, c4 = st.columns([3, 1.5, 1.5, 1])
            with c1:
                st.write(f"**{dep}** ➝ **{arr}** ({mode})")
            
            # Inputs
            km_val, fare_val, rate_val = 0.0, 0.0, 0.0
            
            with c2:
                if current["Kilometer"] == 0:
                    km_val = st.number_input(f"KM", key=f"km_{i}")
                else:
                    st.success(f"KM: {current['Kilometer']}")
            
            with c3:
                if "Private" in mode and current["Ticket_Price_Rate"] == 0:
                    fare_val = st.number_input(f"Bus Fare Equiv.", key=f"fare_{i}")
                elif "Auto" in mode and current["Rate_per_KM"] == 0:
                    rate_val = st.number_input(f"Rate/KM", value=12.0, key=f"rate_{i}")
                elif current["Ticket_Price_Rate"] > 0:
                    st.success(f"Fare: {current['Ticket_Price_Rate']}")

            with c4:
                if st.button("Apply", key=f"btn_{i}"):
                    mask = (st.session_state['ta_calculation_df']["Departure_Place"] == dep) & \
                           (st.session_state['ta_calculation_df']["Arrival_Place"] == arr) & \
                           (st.session_state['ta_calculation_df']["Mode_of_Travel"] == mode)
                    
                    if km_val > 0: st.session_state['ta_calculation_df'].loc[mask, "Kilometer"] = km_val
                    if fare_val > 0: st.session_state['ta_calculation_df'].loc[mask, "Ticket_Price_Rate"] = fare_val
                    if rate_val > 0: st.session_state['ta_calculation_df'].loc[mask, "Rate_per_KM"] = rate_val
                    st.rerun()

# ==========================================
# SECTION 5: CALCULATION LOGIC & EDITOR
# ==========================================

# Apply Logic Loop
for index, row in st.session_state['ta_calculation_df'].iterrows():
    mode = str(row["Mode_of_Travel"]).lower()
    
    # 1. Govt/Uni Vehicle = 0
    if "university" in mode or ("govt" in mode and "private" not in mode):
        st.session_state['ta_calculation_df'].at[index, "Actual_Ticket_Amount"] = 0.0
        st.session_state['ta_calculation_df'].at[index, "Mileage_Total"] = 0.0
    
    # 2. Private Car = Bus Fare (Col 9)
    elif "private" in mode or "car" in mode:
        st.session_state['ta_calculation_df'].at[index, "Actual_Ticket_Amount"] = row["Ticket_Price_Rate"]
        st.session_state['ta_calculation_df'].at[index, "Mileage_Total"] = 0.0
        
    # 3. Auto/Taxi = KM * Rate
    elif "auto" in mode or "taxi" in mode or "rickshaw" in mode:
        st.session_state['ta_calculation_df'].at[index, "Mileage_Total"] = row["Kilometer"] * row["Rate_per_KM"]
        st.session_state['ta_calculation_df'].at[index, "Actual_Ticket_Amount"] = 0.0
        
    # 4. Public (Bus/Rail) = Ticket Price
    else:
        st.session_state['ta_calculation_df'].at[index, "Actual_Ticket_Amount"] = row["Ticket_Price_Rate"]
        st.session_state['ta_calculation_df'].at[index, "Mileage_Total"] = 0.0

st.subheader("2. TA Calculation Matrix (Columns 1-13)")

edited_ta = st.data_editor(
    st.session_state['ta_calculation_df'],
    use_container_width=True,
    hide_index=True,
    column_config={
        # COLS 1-7 (From Diary - Read Only)
        "Departure_Place": st.column_config.TextColumn("1. From", disabled=True),
        "Departure_Date": st.column_config.DateColumn("2. Dep Date", format="DD-MM-YYYY", disabled=True),
        "Departure_Time": st.column_config.TimeColumn("3. Dep Time", format="HH:mm", disabled=True),
        "Arrival_Place": st.column_config.TextColumn("4. To", disabled=True),
        "Arrival_Date": st.column_config.DateColumn("5. Arr Date", format="DD-MM-YYYY", disabled=True),
        "Arrival_Time": st.column_config.TimeColumn("6. Arr Time", format="HH:mm", disabled=True),
        "Mode_of_Travel": st.column_config.TextColumn("7. Mode", disabled=True),
        
        # COLS 8-13 (TA - Editable)
        "Class_of_Travel": st.column_config.TextColumn("8. Class/Veh No"),
        "Ticket_Price_Rate": st.column_config.NumberColumn("9. Fare/Rate", format="₹ %.2f"),
        "Actual_Ticket_Amount": st.column_config.NumberColumn("10. Total Ticket", format="₹ %.2f", disabled=True),
        "Kilometer": st.column_config.NumberColumn("11. KM", format="%.1f km"),
        "Rate_per_KM": st.column_config.NumberColumn("12. Rate/KM", format="₹ %.2f"),
        "Mileage_Total": st.column_config.NumberColumn("13. Total Mileage", format="₹ %.2f", disabled=True)
    }
)

st.session_state['ta_calculation_df'] = edited_ta

# Totals
total_ticket = edited_ta["Actual_Ticket_Amount"].sum()
total_mileage = edited_ta["Mileage_Total"].sum()
grand_total = total_ticket + total_mileage

st.divider()
c1, c2, c3 = st.columns(3)
c1.metric("Total Ticket (Col 10)", f"₹ {total_ticket:,.2f}")
c2.metric("Total Mileage (Col 13)", f"₹ {total_mileage:,.2f}")
c3.metric("💰 Net TA Claim", f"₹ {grand_total:,.2f}")

if st.button("💾 Save Final TA Data"):
    st.session_state['final_ta_data'] = edited_ta
    st.success("Saved!")
