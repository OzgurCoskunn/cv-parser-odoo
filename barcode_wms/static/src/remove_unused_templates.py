import re
import os

INPUT_FILE = r"d:\GİTPLUS\VERTİCAL16\barcode_wms\static\src\stock_barcodev19.js"
OUTPUT_FILE = r"d:\GİTPLUS\VERTİCAL16\barcode_wms\static\src\stock_barcodev19_cleaned.js"

def process_file():
    print(f"Processing {INPUT_FILE}...")
    
    if not os.path.exists(INPUT_FILE):
        print(f"Error: {INPUT_FILE} not found.")
        return

    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    output_lines = []
    buffer = []
    in_template_block = False
    
    # Regex to detect start of registerTemplate call (ignoring whitespace)
    start_pattern = re.compile(r'^\s*registerTemplate\(')
    # Regex to detect end of registerTemplate call: ");" or similar, usually on its own line
    end_pattern = re.compile(r'^\s*\);\s*$')

    removed_count = 0
    kept_count = 0

    for line in lines:
        if in_template_block:
            buffer.append(line)
            if end_pattern.match(line):
                # End of block, decide whether to keep or discard
                block_content = "".join(buffer)
                if "barcode_wms" in block_content:
                    output_lines.extend(buffer)
                    kept_count += 1
                else:
                    removed_count += 1
                    # print(f"Removing block starting: {buffer[0].strip()[:50]}...") # Debug info
                
                buffer = []
                in_template_block = False
        else:
            if start_pattern.match(line):
                in_template_block = True
                buffer.append(line)
                # Check for one-line calls where start and end are on the same line
                if end_pattern.search(line) and not line.strip().endswith('`'): # A simple check, might need refinement if one-liners exist
                     # Ensure it's actually a complete call. 
                     # However, based on file view, they seem to be multiline with backticks.
                     # If there is a case like registerTemplate(..., ...); on one line:
                     if line.strip().endswith(');'):
                        block_content = "".join(buffer)
                        if "barcode_wms" in block_content:
                            output_lines.extend(buffer)
                            kept_count += 1
                        else:
                            removed_count += 1
                        buffer = []
                        in_template_block = False
            else:
                output_lines.append(line)

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.writelines(output_lines)

    print(f"Done. Kept {kept_count} blocks. Removed {removed_count} blocks.")
    print(f"Output saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    process_file()
