"""Verify gallery images exist for all 11 places across all categories."""
import urllib.request, json

# place IDs to test — we'll discover them via /api/places
r = urllib.request.urlopen('http://127.0.0.1:5000/api/places')
places = json.loads(r.read())

print(f"{'Place':<35} {'Category':<15} {'Images':>6}")
print('-' * 60)

for p in places:
    pid = p['id']
    try:
        r2   = urllib.request.urlopen(f'http://127.0.0.1:5000/api/place/{pid}/images')
        imgs = json.loads(r2.read())
        count = len(imgs)
        status = 'OK' if count > 0 else 'NONE'
    except Exception as e:
        count  = 0
        status = 'ERR'
    marker = 'OK' if count > 0 else '!!!'
    print(f"[{marker}] {p['name']:<33} {p['category']:<15} {count:>3} images")
