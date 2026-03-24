"""Generate minimal PWA icons using only stdlib (no Pillow needed)."""
import struct, zlib, os

def png(size, bg=(10,14,26), fg=(245,158,11)):
    """Create a square PNG with a centred lightning bolt icon."""
    W = H = size
    # Build raw RGBA pixel rows
    rows = []
    cx, cy, r = W//2, H//2, int(W * 0.38)

    def in_circle(x, y):
        return (x-cx)**2 + (y-cy)**2 <= r*r

    def in_bolt(x, y):
        # Simple lightning bolt shape (polygon approximation)
        # Scale from reference 100x100
        s = W / 100
        pts = [
            (58*s, 10*s), (30*s, 52*s), (50*s, 52*s),
            (42*s, 90*s), (70*s, 48*s), (50*s, 48*s),
        ]
        # Ray-casting inside polygon
        n = len(pts)
        inside = False
        j = n - 1
        for i in range(n):
            xi, yi = pts[i]; xj, yj = pts[j]
            if ((yi > y) != (yj > y)) and (x < (xj-xi)*(y-yi)/(yj-yi)+xi):
                inside = not inside
            j = i
        return inside

    for y in range(H):
        row = bytearray()
        for x in range(W):
            if in_circle(x, y):
                if in_bolt(x, y):
                    row += bytes([*fg, 255])
                else:
                    row += bytes([20, 30, 60, 255])
            else:
                row += bytes([*bg, 0])
        rows.append(bytes([0]) + row)  # filter byte

    raw = zlib.compress(b''.join(rows))

    def chunk(tag, data):
        c = struct.pack('>I', len(data)) + tag + data
        return c + struct.pack('>I', zlib.crc32(tag+data) & 0xffffffff)

    sig = b'\x89PNG\r\n\x1a\n'
    ihdr = chunk(b'IHDR', struct.pack('>IIBBBBB', W, H, 8, 6, 0, 0, 0))
    idat = chunk(b'IDAT', raw)
    iend = chunk(b'IEND', b'')
    return sig + ihdr + idat + iend

out = os.path.join(os.path.dirname(__file__), '..', 'dashboard')
for size in (192, 512):
    path = os.path.join(out, f'icon-{size}.png')
    with open(path, 'wb') as f:
        f.write(png(size))
    print(f'Created {path}')
