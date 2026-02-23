import asyncio
import os
import sys
import pandas as pd
from backend.core.data import DataManager
from backend.core.store import MetadataStore

async def verify():
    print("Starting verification...")
    # Initialize Core
    data_manager = DataManager("data/datasets")
    metadata_store = MetadataStore()
    
    csv_path = r"C:\Users\prave\Downloads\XAUUSD\XAUUSD-2025_01_01-2026_02_11.csv"
    if not os.path.exists(csv_path):
        print(f"File not found: {csv_path}")
        return

    print("Processing CSV...")
    try:
        # We manually call _process_csv to get the parquet ID
        meta = data_manager._process_csv(csv_path, "XAUUSD", "1m")
        dataset_id = meta['id']
        parquet_path = os.path.join(data_manager.data_dir, f"{dataset_id}.parquet")
        
        print(f"Successfully processed to Parquet: {parquet_path}")
        
        # Detected TF
        df = data_manager.load_dataset(parquet_path)
        print(f"Dataset has {len(df)} rows.")
        
        diffs = df['dtv'].diff().dropna() / 1e9
        mode_diff = diffs.mode()
        detected_tf = int(mode_diff.iloc[0]) if not mode_diff.empty else 0
        print(f"Detected TF: {detected_tf}s")
        
        print("Scanning discrepancies...")
        discrepancies = data_manager.scan_discrepancies(parquet_path, detected_tf)
        
        print(f"Total Discrepancies Found: {len(discrepancies)}")
        
        # Summary counts
        counts = {}
        for d in discrepancies:
            counts[d['type']] = counts.get(d['type'], 0) + 1
        print("Counts by Type:", counts)
        
        # Print first few of each type
        for t in counts.keys():
            print(f"\n--- First 3 of {t} ---")
            t_discs = [d for d in discrepancies if d['type'] == t][:3]
            for d in t_discs:
                print(f"[{d['timestamp']}] Row: {d['index']} - {d['details']}")
                
        # Let's also raw-check the CSV for the zeroes the user mentioned like 02.01.2025
        print("\nChecking raw CSV for 02.01.2025 zeros...")
        with open(csv_path, 'r') as f:
            lines = f.readlines()
            zero_lines = [l for l in lines if ",0," in l and "02.01.2025" in l]
            print(f"Found {len(zero_lines)} lines with zeros on 02.01.2025 in raw CSV.")
            if zero_lines:
                print(f"First raw zero line: {zero_lines[0].strip()}")
                
        # Compare with discrepancy output
        tz_discs = [d for d in discrepancies if d['type'] == "ZERO_VALUE" and "2025-01-02" in d['timestamp']]
        print(f"Found {len(tz_discs)} ZERO_VALUE discrepancies on 2025-01-02.")
        if tz_discs:
            print(f"First ZERO_VALUE discrepancy on 2025-01-02: {tz_discs[0]}")
            
    except Exception as e:
        print(f"Error during verification: {e}")

if __name__ == "__main__":
    asyncio.run(verify())
