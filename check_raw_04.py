def check_raw_04():
    csv_path = r"C:\Users\prave\Downloads\XAUUSD\XAUUSD-2025_01_01-2026_02_11.csv"
    zeros = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        for line in f:
            if "04.02.2025" in line and ",0," in line:
                zeros.append(line.strip())
                
    print(f"Raw 04.02 zeroes: {len(zeros)}")
    for z in zeros[:5]:
        print(z)
        
if __name__ == "__main__":
    check_raw_04()
