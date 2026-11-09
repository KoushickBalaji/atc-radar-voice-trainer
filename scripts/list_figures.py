import pypdfium2 as pdfium
import re

pdf = pdfium.PdfDocument('d:/ATC/design/MANUAL_SDD_2014.pdf')

figures = []
for p in range(len(pdf)):
    text = pdf[p].get_textpage().get_text_range()
    matches = re.findall(r'(Figure\s+\d+:?[^\n\r]+)', text, re.IGNORECASE)
    for m in matches:
        figures.append((p + 1, m.strip()))

with open('d:/ATC/design/figures_list.txt', 'w', encoding='utf-8') as f:
    for page_num, title in figures:
        f.write(f"Page {page_num}: {title}\n")

print(f"Extracted {len(figures)} figures to figures_list.txt")
