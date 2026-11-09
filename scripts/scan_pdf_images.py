import pypdfium2 as pdfium
import re

pdf = pdfium.PdfDocument('d:/ATC/design/MANUAL_SDD_2014.pdf')

results = []
for pno in range(len(pdf)):
    page = pdf[pno]
    image_objs = [obj for obj in page.get_objects() if obj.type == 3] # image type
    if not image_objs:
        continue
    
    # get text on page to find figure title
    text = page.get_textpage().get_text_range()
    figs = re.findall(r'(Figure\s+[\d\-]+:?[^\n\r]+)', text)
    
    # calculate bounding box of all image objects combined
    min_x = min(obj.get_bounds()[0] for obj in image_objs)
    min_y = min(obj.get_bounds()[1] for obj in image_objs)
    max_x = max(obj.get_bounds()[2] for obj in image_objs)
    max_y = max(obj.get_bounds()[3] for obj in image_objs)
    
    width = max_x - min_x
    height = max_y - min_y
    
    # ignore tiny decorative logos/lines (e.g. Indra logo at header)
    if width > 100 and height > 40:
        results.append({
            'page': pno + 1,
            'figs': figs,
            'bbox': (min_x, min_y, max_x, max_y),
            'w': width,
            'h': height,
            'num_objs': len(image_objs)
        })

print(f"Found {len(results)} substantial images across the manual:")
for r in results[:35]:
    print(f"Page {r['page']:3d} | WxH: {r['w']:5.1f}x{r['h']:5.1f} | Figs: {r['figs']}")
