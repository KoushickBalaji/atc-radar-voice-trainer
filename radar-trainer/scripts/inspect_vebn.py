import fitz

doc = fitz.open(r'D:\ATC\Airport Layouts\Varanasi\VEBN-ATC-SMAC.pdf')
page = doc[0]

words = page.get_text('words')
print('=== VEBN Words ===')
for w in words:
    if any(k in w[4] for k in ['MVA', '2300', '2500', '2700', '3300', 'ARP', '25NM', '10NM', '5NM', 'MADHO', 'RAJWARI', 'JHINGURA']):
        print(f'{w[4]:20s} at ({w[0]:.1f}, {w[1]:.1f})')
