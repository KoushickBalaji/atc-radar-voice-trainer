import fitz

doc = fitz.open(r'D:\ATC\Airport Layouts\Calicut\VOCL-ATC-SMAC.PDF')
page = doc[0]

words = page.get_text('words')
# filter words in the map area
pts = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'A1', 'B1', 'C1', 'D1', 'E1', 'F1']
for w in words:
    if w[4] in pts:
        print(f'Point {w[4]:5s} at ({w[0]:.1f}, {w[1]:.1f})')
