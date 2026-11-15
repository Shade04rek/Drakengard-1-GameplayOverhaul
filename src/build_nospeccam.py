"""Ridden ground Angelus: no scripted camera swing when the R1 special (spell) starts. FUN_0017EC04 (the special / breath start) calls the two camera transition setters once on the riding camera object
003ADC80 (a0 = s0): 0017EC60 jal 00199274 (a1 = 1, f12 = 1.0: +0x108 / +0x110 / +0x10C) and 0017EC78 jal 0019925C (a1 = 1, f12 = 5.0: +0x114 = 1, +0x118, +0x11C = 5.0, +0x120 = 0). The camera then blends towards a look-at
target (+0xE0..) and rotated about her (states 1 / 2 of 2026-11-10: +0x114 went from -1 to 1, +0xE0 from 1335 .. to -192 ..). On a ground stage (marker 00340DFC == 0) the two calls are skipped: CS1 / CS2 return at once
(the delay slot a0 = s0 has run); aerial stages tail-call the original setter, so they are unchanged."""
import sys
sys.path.insert(0, r'C:\Users\shade\OneDrive\Documents\PCSX2\roms\drakengard_mod\src\lib')
from mipsasm import Asm
CS1, CS2 = 0x5BCBC0, 0x5BCBE0
def cs(base, target):
    a = Asm(base)
    a.emit('lui', 't8', 0x34); a.emit('lw', 't9', 0xDFC, 't8'); a.emit('bne', 't9', 'zero', 'CALL'); a.emit('nop')
    a.emit('jr', 'ra'); a.emit('nop')
    a.label('CALL'); a.emit('j', target); a.emit('nop')
    return a
def patches():
    p = []
    for base, tgt in ((CS1, 0x199274), (CS2, 0x19925C)): p += [(base + 4 * i, w) for i, w in enumerate(cs(base, tgt).assemble())]
    p += [(0x17EC60, 0x0C000000 | (CS1 >> 2)), (0x17EC78, 0x0C000000 | (CS2 >> 2))]
    return p
if __name__ == '__main__':
    for ad, w in patches(): print('patch=1,EE,%08X,word,%08X' % (ad, w))
