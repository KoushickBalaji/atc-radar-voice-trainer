import fitz
import math

doc = fitz.open('D:/ATC/Airport Layouts/Cochin/VOCI-ATC-SMAC.PDF')
page = doc[0]

segments = []
for d in page.get_drawings():
    c = d.get('color')
    if c and c[0] > 0.8 and c[1] < 0.2 and c[2] < 0.2:
        for it in d.get('items', []):
            if it[0] == 'l':
                p1, p2 = it[1], it[2]
                segments.append(((p1.x, p1.y), (p2.x, p2.y)))

print(f'Total red segments: {len(segments)}')

# Chain segments into paths
paths = []
used = [False] * len(segments)

for i in range(len(segments)):
    if used[i]:
        continue
    used[i] = True
    path = [segments[i][0], segments[i][1]]
    # Extend forward
    changed = True
    while changed:
        changed = False
        tail = path[-1]
        for j in range(len(segments)):
            if not used[j]:
                p1, p2 = segments[j]
                if math.hypot(tail[0] - p1[0], tail[1] - p1[1]) < 1.0:
                    path.append(p2)
                    used[j] = True
                    changed = True
                    break
                elif math.hypot(tail[0] - p2[0], tail[1] - p2[1]) < 1.0:
                    path.append(p1)
                    used[j] = True
                    changed = True
                    break
    # Extend backward
    changed = True
    while changed:
        changed = False
        head = path[0]
        for j in range(len(segments)):
            if not used[j]:
                p1, p2 = segments[j]
                if math.hypot(head[0] - p2[0], head[1] - p2[1]) < 1.0:
                    path.insert(0, p1)
                    used[j] = True
                    changed = True
                    break
                elif math.hypot(head[0] - p1[0], head[1] - p1[1]) < 1.0:
                    path.insert(0, p2)
                    used[j] = True
                    changed = True
                    break
    paths.append(path)

# Filter paths by length > 10 units
long_paths = [p for p in paths if len(p) > 5 or math.hypot(p[0][0]-p[-1][0], p[0][1]-p[-1][1]) > 20]
print(f'Total chained paths: {len(paths)}, long paths: {len(long_paths)}')

for idx, p in enumerate(long_paths):
    p_len = sum(math.hypot(p[k][0]-p[k+1][0], p[k][1]-p[k+1][1]) for k in range(len(p)-1))
    print(f'Path #{idx}: {len(p)} pts, total len={p_len:.1f}, start=({p[0][0]:.1f},{p[0][1]:.1f}), end=({p[-1][0]:.1f},{p[-1][1]:.1f})')
