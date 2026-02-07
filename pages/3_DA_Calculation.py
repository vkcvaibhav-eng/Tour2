import streamlit as st
import pandas as pd
from datetime import datetime

# ==========================================
# ⚙️ UPDATED DA CALCULATION LOGIC
# ==========================================

def calculate_da_statute(total_hours):
    """Calculates DA based on the 6/12/24 hour rule (Statute S.119)"""
    if total_hours < 6: return 0.0
    full_days = int(total_hours // 24)
    remaining_hours = total_hours % 24
    
    # Fractional DA logic
    extra = 0.0
    if 6 <= remaining_hours < 12:
        extra = 0.5
    elif remaining_hours >= 12:
        extra = 1.0
        
    return full_days + extra

def apply_merged_da(df, daily_rate):
    # 1. Convert columns to proper datetime format to avoid errors
    df['2. Departure Date'] = pd.to_datetime(df['2. Departure Date'])
    df['5. Arrival Date'] = pd.to_datetime(df['5. Arrival Date'])
    
    # 2. Sort by date and time to ensure tour order
    df = df.sort_values(by=['2. Departure Date', '3. Departure Time'])
    
    # 3. Group by Departure Date to merge same-day tours
    for date, group in df.groupby('2. Departure Date'):
        # Get the first departure and the last arrival of the day
        start_time = group['3. Departure Time'].iloc[0]
        end_time = group['6. Arrival Time'].iloc[-1]
        last_arrival_date = group['5. Arrival Date'].iloc[-1]

        try:
            # Combine Date and Time for math
            start_dt = datetime.combine(date, pd.to_datetime(start_time).time())
            end_dt = datetime.combine(last_arrival_date, pd.to_datetime(end_time).time())
            
            duration = end_dt - start_dt
            total_hrs = duration.total_seconds() / 3600
            da_days = calculate_da_statute(total_hrs)
            
            # 4. Fill Column 14, 15, 16
            # We put the calculation only in the FIRST row of that day
            first_idx = group.index[0]
            df.at[first_idx, "14. Days of DA"] = da_days
            df.at[first_idx, "15. DA Rate (Rs.)"] = daily_rate
            df.at[first_idx, "16. Amount (Rs.)"] = da_days * daily_rate
            
            # Set other rows for the same day to zero so they don't add extra money
            for other_idx in group.index[1:]:
                df.at[other_idx, "14. Days of DA"] = 0
                df.at[other_idx, "15. DA Rate (Rs.)"] = daily_rate
                df.at[other_idx, "16. Amount (Rs.)"] = 0
                
        except Exception as e:
            st.error(f"Error on date {date}: Check time format (HH:MM:SS)")
            
    return df

# ==========================================
# 📑 STREAMLIT INTERFACE
# ==========================================
st.title("📅 Step 3: Merged DA Calculation")

if 'ta_rearranged_df' in st.session_state:
    df = st.session_state['ta_rearranged_df'].copy()
    
    rate = st.number_input("Enter your Daily Allowance Rate (Rs.)", value=400)
    
    if st.button("Calculate & Merge Same-Day Tours"):
        final_df = apply_merged_da(df, rate)
        st.write("### Final TA/DA Bill Table")
        st.dataframe(final_df)
else:
    st.warning("Please complete the TA step first.")
