
file_path = r"d:\GİTPLUS\VERTİCAL16\barcode_wms\static\src\stock_barcodev19.js"

try:
    with open(file_path, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f, 1):
            if "odoo.define('@barcode_wms/barcode_object'" in line:
                print(f"Found at line: {i}")
                print(line.strip())
                # Read a few more lines to see context/length if needed, but just location is enough to start view_file
                break
        else:
            print("Not found.")
except Exception as e:
    print(f"Error: {e}")
