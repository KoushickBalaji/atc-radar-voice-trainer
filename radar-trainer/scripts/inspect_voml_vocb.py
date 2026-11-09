import json

for code in ['VOML', 'VOCB']:
    d = json.load(open(rf'D:\ATC\radar-trainer\data\airports\{code}.json'))
    msaw = d.get('msaw')
    print(f'=== {code} MSAW ===')
    print('Points count:', len(msaw['points']))
    print('Regions count:', len(msaw['regions']))
    for r in msaw['regions']:
        print(f"  Region '{r['id']}': min={r['minimum_ft']} ft, boundary len={len(r['boundary'])}")
        for b in r['boundary']:
            if isinstance(b, dict):
                print(f"    arc to {b['to']}, center={b['center']}")
            else:
                print(f"    pt {b}")
