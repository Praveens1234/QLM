import pandas as pd
import numpy as np
from backend.core.data import DataManager

def deep_debug():
    csv_path = r"C:\Users\prave\Downloads\XAUUSD\XAUUSD-2025_01_01-2026_02_11.csv"
    
    print("--- 1. RAW CSV ANALYSIS ---")
    raw_04 = 0
    raw_06 = 0
    zeros_06 = 0
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        for line in f:
            if "04.02.2025" in line:
                raw_04 += 1
            if "06.02.2025" in line:
                raw_06 += 1
                if ",0," in line:
                    zeros_06 += 1
                    
    print(f"Raw CSV contains {raw_04} rows for 04.02.2025")
    print(f"Raw CSV contains {raw_06} rows for 06.02.2025, of which {zeros_06} have ZERO values.")

    print("\n--- 2. PANDAS PARSING ANALYSIS ---")
    data_manager = DataManager("data/datasets")
    
    # Process just like DataManager does
    df = pd.read_csv(csv_path, skipinitialspace=True, engine='c')
    df.columns = df.columns.str.strip().str.lower()
    
    date_col_candidates = ['date', 'time', 'timestamp', 'datetime', 'dt', 'ts', 'utc']
    for col in date_col_candidates:
        if col in df.columns:
            df.rename(columns={col: 'datetime'}, inplace=True)
            break
            
    print(f"Original DataFrame length: {len(df)}")
    
    # Check what Pandas natively thinks the first 5 datetime rows are
    print("\nFirst 5 raw datetime strings:")
    print(df['datetime'].head(5).tolist())

    # Try parsing
    df['parsed_dt'] = pd.to_datetime(df['datetime'], utc=True, dayfirst=True, format='mixed', errors='coerce')
    
    # Let's see if 04.02.2025 parsed as Feb 4 or April 2
    feb4_parsed = df[df['parsed_dt'].dt.strftime('%Y-%m-%d') == '2025-02-04']
    apr2_parsed = df[df['parsed_dt'].dt.strftime('%Y-%m-%d') == '2025-04-02']
    feb6_parsed = df[df['parsed_dt'].dt.strftime('%Y-%m-%d') == '2025-02-06']
    
    print(f"\nParsed DataFrame contains {len(feb4_parsed)} rows for 2025-02-04")
    print(f"Parsed DataFrame contains {len(apr2_parsed)} rows for 2025-04-02")
    print(f"Parsed DataFrame contains {len(feb6_parsed)} rows for 2025-02-06")
    
    if len(feb6_parsed) > 0:
        zero_mask = (feb6_parsed['open'] == 0) | (feb6_parsed['high'] == 0) | (feb6_parsed['low'] == 0) | (feb6_parsed['close'] == 0)
        print(f"Of parsed 2025-02-06 rows, {zero_mask.sum()} have ZERO values.")
        
    print("\n--- 3. SCANNER DISCREPANCY ANALYSIS ---")
    # Simulate scanner logic without the [:100] cap
    df_clean = df.dropna(subset=['parsed_dt']).copy()
    df_clean['dtv'] = df_clean['parsed_dt'].astype('int64')
    df_clean.sort_values('dtv', inplace=True)
    df_clean.drop_duplicates(subset=['dtv'], keep='first', inplace=True)
    
    zero_mask_full = (df_clean['open'] == 0) | (df_clean['high'] == 0) | (df_clean['low'] == 0) | (df_clean['close'] == 0)
    zero_indices = np.where(zero_mask_full)[0]
    print(f"Total globally detected ZERO_VALUE rows: {len(zero_indices)}")
    
    # Check if a zero index is on Feb 6
    sample_zeros_feb6 = [idx for idx in zero_indices if df_clean.iloc[idx]['parsed_dt'].strftime('%Y-%m-%d') == '2025-02-06']
    print(f"Zero values explicitly found on 2025-02-06 via scanner logic: {len(sample_zeros_feb6)}")

if __name__ == "__main__":
    deep_debug()
