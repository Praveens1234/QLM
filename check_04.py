import pandas as pd
from backend.core.data import DataManager

def check_04():
    data_manager = DataManager("data/datasets")
    csv_path = r"C:\Users\prave\Downloads\XAUUSD\XAUUSD-2025_01_01-2026_02_11.csv"
    
    # Process
    meta = data_manager._process_csv(csv_path, "XAUUSD", "1m")
    parquet_path = f"data/datasets/{meta['id']}.parquet"
    
    df = data_manager.load_dataset(parquet_path)
    # Detect TF
    diffs = df['dtv'].diff().dropna() / 1e9
    mode_diff = diffs.mode()
    detected_tf = int(mode_diff.iloc[0]) if not mode_diff.empty else 0
    
    # Scan ALL without 100 limit manually to see what's actually under the hood for 04.02 and 06.02
    discrepancies = data_manager.scan_discrepancies(parquet_path, detected_tf)
    
    # We will override the scan_discrepancies output by doing it raw
    import numpy as np
    
    zero_mask = (df['open'] == 0) | (df['high'] == 0) | (df['low'] == 0) | (df['close'] == 0)
    gap_mask = diffs > (detected_tf * 1.5)
    
    all_discs = []
    
    for idx in np.where(zero_mask)[0]:
        all_discs.append({
            "type": "ZERO_VALUE",
            "index": int(idx),
            "timestamp": df['datetime'].iloc[idx].isoformat(),
        })
        
    for idx in np.where(gap_mask)[0]:
        all_discs.append({
            "type": "TIME_GAP",
            "index": int(idx),
            "timestamp": df['datetime'].iloc[idx].isoformat(),
        })
        
    feb4_discs = [d for d in all_discs if '2025-02-04' in d['timestamp']]
    print(f"Total Discrepancies on 2025-02-04: {len(feb4_discs)}")
    for d in feb4_discs[:5]:
        print(d)
        
if __name__ == "__main__":
    check_04()
