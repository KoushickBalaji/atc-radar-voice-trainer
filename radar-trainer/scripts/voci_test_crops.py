from PIL import Image

im = Image.open('D:/ATC/radar-trainer/scratch/VOCI_overlay_test.png')
w, h = im.size

# Let's crop:
# 1. North-West: points A, B, R, S, T, Q, J, H
crop_nw = im.crop((int(0.1*w), int(0.05*h), int(0.6*w), int(0.55*h)))
crop_nw.save('D:/ATC/radar-trainer/scratch/voci_test_nw.png')

# 2. North-East: points B, C, U, P, K, D, V
crop_ne = im.crop((int(0.45*w), int(0.05*h), int(0.95*w), int(0.55*h)))
crop_ne.save('D:/ATC/radar-trainer/scratch/voci_test_ne.png')

# 3. South-East: points D, V, O, E, I, L, M, W, X, F
crop_se = im.crop((int(0.45*w), int(0.45*h), int(0.95*w), int(0.95*h)))
crop_se.save('D:/ATC/radar-trainer/scratch/voci_test_se.png')

# 4. South-West: points G, N, H, J, center
crop_sw = im.crop((int(0.05*w), int(0.45*h), int(0.55*w), int(0.95*h)))
crop_sw.save('D:/ATC/radar-trainer/scratch/voci_test_sw.png')

print('Saved 4 detailed overlay crops')
