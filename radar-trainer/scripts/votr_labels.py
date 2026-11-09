import fitz

doc = fitz.open(r'D:\ATC\Airport Layouts\Tiruchirappalli\VOTR-ATC-SMAC.pdf')
page = doc[0]

words = page.get_text('words')
for w in words:
    if 'AREA' in w[4] or 'MVA' in w[4] or '4000' in w[4] or '2300' in w[4] or '3000' in w[4]:
        print(f'{w[4]} at bbox: ({w[0]:.1f}, {w[1]:.1f}, {w[2]:.1f}, {w[3]:.1f})')
