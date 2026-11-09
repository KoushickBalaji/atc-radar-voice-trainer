import fitz

doc = fitz.open(r'D:\ATC\Airport Layouts\Lucknow\VILK-ATC-SMAC.pdf')
page = doc[0]

# Inspect all drawings
drawings = page.get_drawings()
print(f'VILK drawings count: {len(drawings)}')

# Inspect text in drawings or words
# Are there any other numbers like 10NM, 20NM?
words = page.get_text('words')
print('Words in VILK:', [w[4] for w in words])
