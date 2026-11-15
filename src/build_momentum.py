"""Angelus (aerial stages) flies faster while the L2 boost is held. F = the collision move FUN_001B73C0 (s1 = object; the world delta vector at s1 + 0xF0
is added to the position at s1 + 0xD0 and cleared). Hook 001B73F4 (addiu s2,s1,240 -> j MOM; the delay slot sd v0,0(sp) is harmless). MOM (005B6E80): only for
the dragon (s1 == 0041BFC0) on aerial stages (marker 00340DFC != 0) while the L2 action is held (pad action word 00342898 bit 0x100): the delta is multiplied by BOOST.
The dive speed carry was removed again (build_momentum.py.bak_dive)."""
import sys, struct
sys.path.insert(0, r'C:\Users\shade\OneDrive\Documents\PCSX2\roms\drakengard_mod\src\lib')
from mipsasm import Asm
MOM = 0x5B6E80
BOOST = 1.20
def fb(x): return struct.unpack('<I', struct.pack('<f', x))[0]
def build():
    a = Asm(MOM)
    a.emit('addiu', 's2', 's1', 240)
    a.emit('lui', 't0', 0x41); a.emit('ori', 't0', 't0', 0xBFC0); a.emit('bne', 's1', 't0', 'OUT'); a.emit('nop')
    a.emit('lui', 't0', 0x34); a.emit('lw', 't0', 0xDFC, 't0'); a.emit('beq', 't0', 'zero', 'OUT'); a.emit('nop')
    a.emit('lui', 't0', 0x34); a.emit('lhu', 't0', 0x2898, 't0'); a.emit('andi', 't0', 't0', 0x100); a.emit('beq', 't0', 'zero', 'OUT'); a.emit('nop')
    b = fb(BOOST); a.emit('lui', 'at', b >> 16)
    if b & 0xFFFF: a.emit('ori', 'at', 'at', b & 0xFFFF)
    a.emit('mtc1', 'at', 'f10')
    for k in range(3):
        a.emit('lwc1', 'f%d' % k, 4 * k, 's2'); a.emit('mul.s', 'f%d' % k, 'f%d' % k, 'f10'); a.emit('swc1', 'f%d' % k, 4 * k, 's2')
    a.label('OUT')
    a.emit('j', 0x1B73FC); a.emit('nop')
    return a
def patches():
    return [(MOM + 4 * i, w) for i, w in enumerate(build().assemble())] + [(0x1B73F4, 0x08000000 | (MOM >> 2))]
if __name__ == '__main__':
    for ad, w in patches(): print('patch=1,EE,%08X,word,%08X' % (ad, w))
