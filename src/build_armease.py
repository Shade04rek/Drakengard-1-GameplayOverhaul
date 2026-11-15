"""Camera distance after a dismount. The main camera arm (CAMD, 005B8180; DA 005B6300 / DB 005B6340 load the ground arm 68.0 with lui t9,4288 at 005B6330 / 005B6370)
is held at 68 on foot. During the dismount jump the rendered camera (live camera 003AD4F0) is much closer to Caim (measured 48 units against 72 on foot: Caim looked bigger,
the 'field of view' jump the user saw). ARM (word 005BEFFC, float): while the jump runs (Caim +0x6B4 == 2 and +0x2D0 == 3) it is the distance of the live eye (003AD570) from
Caim (at most 68); on every other call it eases towards 68 by EASE of the gap, so after the landing the arm opens smoothly from the jump distance to 68.
The two ground loads become j ARMA / j ARMB (the mtc1 t9,f9 after them runs in the delay slot with a stale t9 and again after the cave)."""
import sys, struct
sys.path.insert(0, r'C:\Users\shade\OneDrive\Documents\PCSX2\roms\drakengard_mod\src\lib')
from mipsasm import Asm
BASE = 0x5BEE20
EASE = 0.07
ARMW = -0x1004                             # 005BEFFC (lui 0x5C)
def fb(x): return struct.unpack('<I', struct.pack('<f', x))[0]
def lif(a, f, x):
    b = fb(x); a.emit('lui', 'at', b >> 16)
    if b & 0xFFFF: a.emit('ori', 'at', 'at', b & 0xFFFF)
    a.emit('mtc1', 'at', f)
def arm(base, ret):
    a = Asm(base)
    a.emit('lui', 't0', 0x5C); a.emit('lwc1', 'f10', ARMW, 't0')
    lif(a, 'f11', 1.0); a.emit('c.olt.s', 'f10', 'f11'); a.emit('bc1f', 'HAVE'); a.emit('nop')
    lif(a, 'f10', 68.0)
    a.label('HAVE')
    a.emit('lui', 't1', 0x3A); a.emit('ori', 't1', 't1', 0xC5E0)
    a.emit('lw', 't9', 0x6B4, 't1'); a.emit('addiu', 't9', 't9', -2); a.emit('bne', 't9', 'zero', 'EASE'); a.emit('nop')
    a.emit('lw', 't9', 0x2D0, 't1'); a.emit('addiu', 't9', 't9', -3); a.emit('bne', 't9', 'zero', 'EASE'); a.emit('nop')
    a.emit('lui', 't9', 0x3B)
    a.emit('lwc1', 'f12', -0x2A90, 't9'); a.emit('lwc1', 'f13', -0x2A8C, 't9'); a.emit('lwc1', 'f14', -0x2A88, 't9')
    a.emit('lwc1', 'f15', 0x80, 't1'); a.emit('sub.s', 'f12', 'f12', 'f15')
    a.emit('lwc1', 'f15', 0x84, 't1'); a.emit('sub.s', 'f13', 'f13', 'f15')
    a.emit('lwc1', 'f15', 0x88, 't1'); a.emit('sub.s', 'f14', 'f14', 'f15')
    a.emit('mul.s', 'f12', 'f12', 'f12'); a.emit('mul.s', 'f13', 'f13', 'f13'); a.emit('mul.s', 'f14', 'f14', 'f14')
    a.emit('add.s', 'f12', 'f12', 'f13'); a.emit('add.s', 'f12', 'f12', 'f14'); a.emit('sqrt.s', 'f12', 'f12')
    lif(a, 'f13', 68.0); a.emit('c.olt.s', 'f13', 'f12'); a.emit('bc1f', 'SETA'); a.emit('nop'); a.emit('mov.s', 'f12', 'f13')
    a.label('SETA'); a.emit('mov.s', 'f10', 'f12'); a.emit('beq', 'zero', 'zero', 'EXIT'); a.emit('nop')
    a.label('EASE')
    lif(a, 'f12', 68.0); a.emit('sub.s', 'f13', 'f12', 'f10'); lif(a, 'f14', EASE); a.emit('mul.s', 'f13', 'f13', 'f14'); a.emit('add.s', 'f10', 'f10', 'f13')
    a.label('EXIT'); a.emit('swc1', 'f10', ARMW, 't0'); a.emit('mfc1', 't9', 'f10'); a.emit('j', ret); a.emit('nop')
    return a
def layout():
    out = []; cur = BASE
    for name, ret, hook in (('ARMA', 0x5B6334, 0x5B6330), ('ARMB', 0x5B6374, 0x5B6370)):
        a = arm(cur, ret); w = a.assemble(); out.append((name, cur, w, hook)); cur += 4 * len(w)
    return out, cur
def patches():
    p = []
    for name, base, w, hook in layout()[0]:
        p += [(base + 4 * i, x) for i, x in enumerate(w)]; p.append((hook, 0x08000000 | (base >> 2)))
    return p
if __name__ == '__main__':
    s, e = layout(); print([(n, hex(b), len(w), hex(h)) for n, b, w, h in s], hex(e))
