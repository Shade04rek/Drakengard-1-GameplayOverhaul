import struct
def f2w(x): return struct.unpack('<I', struct.pack('<f', x))[0]
fade = [
    (0x5B7600, 0x00052880),   # FADE4: sll a1,a1,2   (fade step x4)
    (0x5B7604, 0x080CF5AE),   # j 0033D6B8 (TFader<int>::update)
    (0x5B7608, 0x00000000),   # nop
    (0x276CAC, 0x0C16DD80),   # CFadeMan::Execute: jal 0033D6B8 -> jal FADE4
]
title = []
for a, v in ((0x569F80, 0.12), (0x569F84, 8.96), (0x569F8C, 0.12), (0x569F90, 12.8), (0x569F94, 3.84),
             (0x569F98, 12.8), (0x569F9C, 0.48), (0x569FA0, 3.84), (0x569FA8, 0.48), (0x569FAC, 8.96)):
    title.append((a, f2w(v)))
for a in (0x2DD670, 0x2DD68C, 0x2DD6A4, 0x2DD740, 0x2DD758, 0x2DD770): title.append((a, 0x2442FFF8))   # alpha -2 -> -8
for a in (0x2DDC50, 0x2DDC74, 0x2DDC98): title.append((a, 0x24420008))                                   # alpha +2 -> +8
title.append((0x2DD9A4, 0x24420010))   # popup fade-in +4 -> +16
title.append((0x2DDA88, 0x2442FFF0))   # popup fade-out -4 -> -16
open('snappy_fade.txt', 'w').write('\n'.join('%08X %08X' % p for p in fade))
open('snappy_title.txt', 'w').write('\n'.join('%08X %08X' % p for p in title))
print(len(fade), len(title))
