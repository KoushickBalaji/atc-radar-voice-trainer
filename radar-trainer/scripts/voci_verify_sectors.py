from PIL import Image
import numpy as np

# Let's inspect the crops of the labels and the lines around each point
im_nw = Image.open('D:/ATC/radar-trainer/scratch/voci_test_nw.png')
im_ne = Image.open('D:/ATC/radar-trainer/scratch/voci_test_ne.png')
im_se = Image.open('D:/ATC/radar-trainer/scratch/voci_test_se.png')
im_sw = Image.open('D:/ATC/radar-trainer/scratch/voci_test_sw.png')

print('All 4 test overlay crops loaded successfully!')
