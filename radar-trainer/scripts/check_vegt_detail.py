import fitz
import re

doc = fitz.open(r'D:\ATC\Airport Layouts\Guwahati\VEGT-ATC-SMAC.pdf')
page = doc[0]

# In VEGT, let's find all text blocks and coordinates
words = page.get_text('words')
coord_words = [w for w in words if re.search(r'N\d{6}|E09\d{5}|N\d{2}|E\d{2}', w[4])]
print('Coordinate words in VEGT:')
for w in coord_words:
    print(f'  {w[4]} at ({w[0]:.1f}, {w[1]:.1f})')

# Let's see how many sectors there are in VEGT:
# MVA 2500, MVA 3500, MVA 5000, MVA 6000, MVA 7000
