import fitz
import re
import numpy as np

doc = fitz.open(r'D:\ATC\Airport Layouts\Bengaluru (HAL)\VOBG-ATC-SMAC.pdf')
page = doc[0]

# Let's find point markers in the PDF drawings or text
# For each point A-S, we have the label position
words = page.get_text('words')
pts_coords = {
    'A': [12.80952222, 76.99754722],
    'B': [12.81838056, 77.43491111],
    'C': [13.23545556, 77.32495556],
    'D': [13.24606389, 77.89386111],
    'E': [12.88005, 77.94270833],
    'F': [12.88345, 78.14308611],
    'G': [12.71668611, 78.14595833],
    'H': [12.62533056, 78.25991111],
    'I': [12.41669167, 78.073925],
    'J': [12.54909167, 77.97364444],
    'K': [12.56739167, 77.76018611],
    'L': [12.57659167, 77.65211389],
    'M': [12.65587222, 77.5712],
    'N': [12.65265556, 77.40407778],
    'O': [12.60346111, 77.08196944],
    'P': [12.28617222, 77.73534444],
    'Q': [13.25246111, 78.27501667],
    'R': [13.61443333, 77.56345],
    'S': [13.24019444, 77.57079167]
}

# In VOBG-ATC-SMAC.pdf, each point has text like "A\n12°48'34.28\"N\n076°59'51.17\"E"
# Let's inspect the lines/paths that connect points
# Let's inspect the drawing objects in the PDF
# Are there paths that connect these points?
drawings = page.get_drawings()
print(f'Inspecting {len(drawings)} drawing objects...')

# Find lines where endpoints match point label locations
