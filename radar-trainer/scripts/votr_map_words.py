import fitz

doc = fitz.open(r'D:\ATC\Airport Layouts\Tiruchirappalli\VOTR-ATC-SMAC.pdf')
page = doc[0]

words = page.get_text('words')
# filter words in the map area: y between 100 and 550
map_words = [w for w in words if 100 <= w[1] <= 550]
for w in map_words:
    if any(k in w[4] for k in ['AREA', 'MVA', 'TR', '2300', '3000', '4000', '25NM', '20NM', '15NM', '10NM', '5NM', 'VOR']):
        print(f'{w[4]:15s} at ({w[0]:.1f}, {w[1]:.1f})')
