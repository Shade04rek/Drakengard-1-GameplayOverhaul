"""Ground Angelus vertical boost mechanics (stub 005BCF80 = VUP, called after the output vector at v1 is stored; t0 = 00340000, t3 = 005C0000, s0 = the dragon pose block 0041BFC0):
VUP2 (005BD000): x3 vertical multiplier (build_vmult.py VMULT). L1 held (raw pad 0056CD83 bit 2, active low): y = -ASC (ascend) and the forward speed x SLOW. Otherwise: FL (word 005BEDEC) = 1 when her y
(pose block +0xD4) did not increase by more than 0.1 since the previous frame (PY 005BEDE8): not descending / at the lowest point. L2 boost: brake mode: y = +DESC (the boost glide descent); fast mode: when the vector goes
down (y > 0) y = DESC as well. BON (005BD4D0, t8 = 1 while she descends under boost and FL = 0): the descent speed bonus SB (word 005BEDFC) follows 0.5 * (1 - height fraction) (0 at the highest, 0.5 at the lowest height; the height range is the one of
build_boostspeed.py: terrain height word VW, floor = terrain - 90, top y = -515), smoothed by SMOOTH per frame; when she is not descending (or is at the lowest point) SB falls by FADE per frame (1 s). The x and z of the vector are
multiplied by 1 + SB. GB3 (build_glideboost.py) picks the boost-glide pose in brake mode from FL. L1C (005BD200): clears the dodge bits of the pad struct while L1 is held."""
import sys, struct
sys.path.insert(0, r'C:\\Users\\shade\\OneDrive\\Documents\\PCSX2\\roms\\drakengard_mod\\src\\lib'); sys.path.insert(0, r'C:\\Users\\shade\\OneDrive\\Documents\\PCSX2\\roms\\drakengard_mod\\src')
from mipsasm import Asm
import build_aerialboost as AB
import build_vmult as V
VUP2 = 0x5BD000
BON = 0x5BD4D0
DESC = 1.0          # boost descent speed (was 2.0; halved 2026-11-10)
ASC = 2.0          # L1 held: she climbs at this speed (y points down, so the vector y is -ASC)
SLOW = 0.5         # forward speed (x and z of the vector) while she ascends (L1) = 50% slower
MAXB = 0.5         # descent speed bonus at the lowest height
SMOOTH = 0.1       # SB follows its target by this fraction per frame
FADE = 1.0         # SB falls by this per frame when she stops descending: 1.0 > MAXB, so the bonus is gone at once (was 0.5 / 60 = 1 s)
LOW_MARGIN, TOP = 90.0, -515.0
L1C = 0x5BD200
PY, FL = -0x1218, -0x1214      # 005BEDE8, 005BEDEC (lui 0x5C)
SB, VW = -0x1204, -0x1210      # 005BEDFC, 005BEDF0
def fb(x): return struct.unpack('<I', struct.pack('<f', x))[0]
def lif(a, f, x):
    b = fb(x); a.emit('lui', 'at', b >> 16)
    if b & 0xFFFF: a.emit('ori', 'at', 'at', b & 0xFFFF)
    a.emit('mtc1', 'at', f)
def slow(a):
    a.emit('lwc1', 'f1', 0, 'v1'); a.emit('lwc1', 'f2', 8, 'v1'); lif(a, 'f3', SLOW); a.emit('mul.s', 'f1', 'f1', 'f3'); a.emit('mul.s', 'f2', 'f2', 'f3'); a.emit('swc1', 'f1', 0, 'v1'); a.emit('swc1', 'f2', 8, 'v1')
def stub():
    a = Asm(AB.VUP); a.emit('j', VUP2); a.emit('nop'); return a
def build():
    a = Asm(VUP2)
    a.emit('lwc1', 'f0', 4, 'v1'); lif(a, 'f1', V.VMULT); a.emit('mul.s', 'f0', 'f0', 'f1'); a.emit('swc1', 'f0', 4, 'v1')
    # L1 held: ascend
    a.emit('lui', 't9', 0x57); a.emit('lbu', 't9', -0x327D, 't9'); a.emit('andi', 't9', 't9', 4); a.emit('bne', 't9', 'zero', 'NL1'); a.emit('nop')
    lif(a, 'f0', -ASC); a.emit('swc1', 'f0', 4, 'v1'); slow(a); a.emit('beq', 'zero', 'zero', 'VX'); a.emit('nop')
    a.label('NL1')
    a.emit('lwc1', 'f2', 0xD4, 's0'); a.emit('lwc1', 'f3', PY, 't3'); a.emit('swc1', 'f2', PY, 't3'); a.emit('sub.s', 'f4', 'f2', 'f3')
    lif(a, 'f5', 0.1); a.emit('ori', 't8', 'zero', 1); a.emit('c.olt.s', 'f5', 'f4'); a.emit('bc1f', 'FLS'); a.emit('nop'); a.emit('or', 't8', 'zero', 'zero')
    a.label('FLS'); a.emit('sw', 't8', FL, 't3')
    a.emit('lui', 't9', 0x57); a.emit('lbu', 't9', 0x47BA, 't9'); a.emit('addu', 't9', 't9', 't0'); a.emit('lbu', 't9', 0x2864, 't9'); a.emit('sltiu', 't9', 't9', 0x40)
    a.emit('bne', 't9', 'zero', 'NOB'); a.emit('nop')
    a.emit('lw', 't2', AB.TGB, 't3'); a.emit('beq', 't2', 'zero', 'FM'); a.emit('nop')
    lif(a, 'f0', DESC); a.emit('swc1', 'f0', 4, 'v1'); a.emit('beq', 'zero', 'zero', 'CHK'); a.emit('nop')
    a.label('FM')
    a.emit('lwc1', 'f0', 4, 'v1'); a.emit('mtc1', 'zero', 'f1'); a.emit('c.olt.s', 'f1', 'f0'); a.emit('bc1f', 'NOB'); a.emit('nop')
    lif(a, 'f0', DESC); a.emit('swc1', 'f0', 4, 'v1')
    a.label('CHK'); a.emit('lw', 't8', FL, 't3'); a.emit('sltiu', 't8', 't8', 1); a.emit('j', BON); a.emit('nop')
    a.label('NOB'); a.emit('or', 't8', 'zero', 'zero'); a.emit('j', BON); a.emit('nop')
    a.label('VX'); a.emit('j', AB.STRAFE); a.emit('nop')
    return a
def bon():
    a = Asm(BON)
    a.emit('beq', 't8', 'zero', 'FAD'); a.emit('nop')
    a.emit('lwc1', 'f0', VW, 't3'); lif(a, 'f3', LOW_MARGIN); a.emit('sub.s', 'f0', 'f0', 'f3')                       # f0 = lowest y, f2 = her y (VUP2)
    a.emit('sub.s', 'f1', 'f0', 'f2'); lif(a, 'f3', -TOP); a.emit('add.s', 'f0', 'f0', 'f3')                            # f1 = lowest y - y, f0 = range
    lif(a, 'f4', 1.0); a.emit('c.olt.s', 'f0', 'f4'); a.emit('bc1f', 'RGO'); a.emit('nop'); a.emit('mtc1', 'zero', 'f1'); a.emit('mov.s', 'f0', 'f4')
    a.label('RGO')
    a.emit('div.s', 'f1', 'f1', 'f0')                                                                                   # height fraction (0 lowest .. 1 highest)
    a.emit('mtc1', 'zero', 'f3'); a.emit('c.olt.s', 'f1', 'f3'); a.emit('bc1f', 'C1'); a.emit('nop'); a.emit('mov.s', 'f1', 'f3')
    a.label('C1')
    a.emit('c.olt.s', 'f4', 'f1'); a.emit('bc1f', 'C2'); a.emit('nop'); a.emit('mov.s', 'f1', 'f4')
    a.label('C2')
    a.emit('sub.s', 'f1', 'f4', 'f1'); lif(a, 'f3', MAXB); a.emit('mul.s', 'f1', 'f1', 'f3')                          # target = MAXB * (1 - fraction)
    a.emit('lwc1', 'f5', SB, 't3'); a.emit('sub.s', 'f1', 'f1', 'f5'); lif(a, 'f3', SMOOTH); a.emit('mul.s', 'f1', 'f1', 'f3'); a.emit('add.s', 'f5', 'f5', 'f1')
    a.emit('mtc1', 'zero', 'f3'); a.emit('c.olt.s', 'f5', 'f3'); a.emit('bc1f', 'SVB'); a.emit('nop'); a.emit('mov.s', 'f5', 'f3')
    a.emit('beq', 'zero', 'zero', 'SVB'); a.emit('nop')
    a.label('FAD')
    a.emit('lwc1', 'f5', SB, 't3'); lif(a, 'f3', FADE); a.emit('sub.s', 'f5', 'f5', 'f3'); a.emit('mtc1', 'zero', 'f3'); a.emit('c.olt.s', 'f5', 'f3'); a.emit('bc1f', 'SVB'); a.emit('nop'); a.emit('mov.s', 'f5', 'f3')
    a.label('SVB'); a.emit('swc1', 'f5', SB, 't3')
    lif(a, 'f6', 1.0); a.emit('add.s', 'f6', 'f6', 'f5'); a.emit('lwc1', 'f1', 0, 'v1'); a.emit('lwc1', 'f2', 8, 'v1')
    a.emit('mul.s', 'f1', 'f1', 'f6'); a.emit('mul.s', 'f2', 'f2', 'f6'); a.emit('swc1', 'f1', 0, 'v1'); a.emit('swc1', 'f2', 8, 'v1')
    a.emit('j', AB.STRAFE); a.emit('nop')
    return a
def l1c():
    import build_specmove as M
    a = Asm(L1C)
    a.emit('lui', 't9', 0x57); a.emit('lbu', 't9', -0x327D, 't9'); a.emit('andi', 't9', 't9', 4); a.emit('bne', 't9', 'zero', 'L1X'); a.emit('nop')
    a.emit('lui', 't2', 0xFCFF); a.emit('ori', 't2', 't2', 0xFFFF)
    a.emit('lw', 't9', 8, 'a1'); a.emit('and', 't9', 't9', 't2'); a.emit('sw', 't9', 8, 'a1')
    a.emit('lw', 't9', 12, 'a1'); a.emit('and', 't9', 't9', 't2'); a.emit('sw', 't9', 12, 'a1')
    a.label('L1X'); a.emit('j', M.PRE); a.emit('nop')
    return a
def patches():
    p = [(AB.VUP + 4 * i, w) for i, w in enumerate(stub().assemble())]
    p += [(VUP2 + 4 * i, w) for i, w in enumerate(build().assemble())]
    p += [(BON + 4 * i, w) for i, w in enumerate(bon().assemble())]
    return p + [(L1C + 4 * i, w) for i, w in enumerate(l1c().assemble())]
if __name__ == '__main__':
    for ad, x in patches(): print('patch=1,EE,%08X,word,%08X' % (ad, x))
