def scan_lines():
    csv_path = r"C:\Users\prave\Downloads\XAUUSD\XAUUSD-2025_01_01-2026_02_11.csv"
    with open(csv_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    print("--- LINES 2821-2822 ---")
    print(f"Row 2821: {lines[2820].strip()}")
    print(f"Row 2822: {lines[2821].strip()}")
    
    # Find Feb 3, 4, 5
    feb3 = [i for i, l in enumerate(lines) if "03.02.2025" in l][:2]
    feb4 = [i for i, l in enumerate(lines) if "04.02.2025" in l][:2]
    feb5 = [i for i, l in enumerate(lines) if "05.02.2025" in l][:2]
    
    print("\n--- FEBRUARY DATES ---")
    print("03.02.2025 starts at:")
    for i in feb3: print(f"Row {i+1}: {lines[i].strip()}")
        
    print("\n04.02.2025 starts at:")
    for i in feb4: print(f"Row {i+1}: {lines[i].strip()}")
        
    print("\n05.02.2025 starts at:")
    for i in feb5: print(f"Row {i+1}: {lines[i].strip()}")

if __name__ == "__main__":
    scan_lines()
