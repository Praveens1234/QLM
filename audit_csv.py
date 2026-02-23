import pandas as pd
import numpy as np

def audit_raw_csv():
    csv_path = r"C:\Users\prave\Downloads\XAUUSD\XAUUSD-2025_01_01-2026_02_11.csv"
    
    print("Loading CSV for RAW Audit...")
    try:
        # Load CSV using C engine for speed
        df = pd.read_csv(csv_path, skipinitialspace=True, engine='c')
    except Exception:
        df = pd.read_csv(csv_path, skipinitialspace=True, sep=None, engine='python')
        
    df.columns = df.columns.str.strip().str.lower()
    
    # Standardize column name
    for col in ['date', 'time', 'timestamp', 'datetime']:
        if col in df.columns:
            df.rename(columns={col: 'datetime'}, inplace=True)
            break

    # Parse dates explicitly using dayfirst to respect the DD.MM.YYYY format
    df['parsed_dt'] = pd.to_datetime(df['datetime'], utc=True, dayfirst=True, format='mixed', errors='coerce')
    df = df.dropna(subset=['parsed_dt']).copy()
    
    # Ensure numeric types
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
        
    df.sort_values('parsed_dt', inplace=True)
    df.reset_index(drop=True, inplace=True)

    print("\n" + "="*40)
    print("RAW CSV ANOMALY REPORT")
    print("="*40)
    print(f"Total Rows Analyzed: {len(df):,}")
    print(f"Date Range: {df['parsed_dt'].min().strftime('%Y-%m-%d')} to {df['parsed_dt'].max().strftime('%Y-%m-%d')}")

    # 1. Zero Values
    zero_mask = (df['open'] == 0) | (df['high'] == 0) | (df['low'] == 0) | (df['close'] == 0)
    zero_count = zero_mask.sum()
    print(f"\n1. CORRUPT ZERO VALUES: {zero_count:,} rows")
    if zero_count > 0:
        zero_dates = df[zero_mask]['parsed_dt'].dt.date.unique()
        print(f"   - Found empty 0.0 prices across {len(zero_dates)} different days.")
        print(f"   - Example affected dates: {[str(d) for d in zero_dates[:5]]}...")

    # 2. Logic Errors
    logic_mask = (df['high'] < df['low']) | (df['close'] > df['high']) | (df['close'] < df['low']) | (df['open'] > df['high']) | (df['open'] < df['low'])
    # Only count rows that aren't already zeros (we know zeros have bad logic)
    pure_logic_errors = logic_mask & ~zero_mask
    logic_count = pure_logic_errors.sum()
    print(f"\n2. MATHEMATICAL LOGIC ERRORS: {logic_count:,} rows")
    if logic_count > 0:
        print("   - Rows where prices defy physics (e.g. High > Low, or Close is outside the body).")

    # 3. Massive Spikes
    with np.errstate(divide='ignore', invalid='ignore'):
        spike_mask = (np.abs(df['high'] - df['low']) / df['open']) > 0.05  # >5% in a single minute is massive for Gold
    pure_spikes = spike_mask & ~zero_mask
    spike_count = pure_spikes.sum()
    print(f"\n3. ANOMALOUS PRICE SPIKES (>5% in 1 minute): {spike_count:,} rows")
    if spike_count > 0:
        print("   - Likely bad API ticks creating massive artificial candle wicks.")

    # 4. Missing Trading Days (Time Gaps)
    print("\n4. MISSING TRADING DAYS (TIME GAPS):")
    # Generate a perfect calendar of expected trading days (Mon-Fri)
    start_date = df['parsed_dt'].min().floor('D')
    end_date = df['parsed_dt'].max().floor('D')
    expected_days = pd.date_range(start=start_date, end=end_date, freq='B') # 'B' is Business days
    
    actual_days = df['parsed_dt'].dt.floor('D').unique()
    
    missing_days = expected_days.difference(actual_days)
    print(f"   - Total physical days missing from continuous timeline: {len(missing_days)} days")
    if len(missing_days) > 0:
        print("   - These dates are entirely skipped in your CSV:")
        for d in missing_days[:10]:
            print(f"     * {d.strftime('%Y-%m-%d')} ({d.day_name()})")
        if len(missing_days) > 10:
            print(f"     * ... and {len(missing_days)-10} more.")

    # 5. Missing Intraday Minutes
    df['diff'] = df['parsed_dt'].diff().dt.total_seconds()
    # A gap of > 60 seconds (but less than a day to ignore weekends) is a missing bar
    intraday_gap_mask = (df['diff'] > 60) & (df['diff'] < 86400)
    intraday_gap_count = intraday_gap_mask.sum()
    print(f"\n5. INTRADAY MISSING MINUTES: {intraday_gap_count:,} gaps detected.")
    if intraday_gap_count > 0:
        print("   - The time skips forward randomly during a trading day, missing several 1-minute bars entirely.")

    print("\n" + "="*40)
    
if __name__ == "__main__":
    audit_raw_csv()
