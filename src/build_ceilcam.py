"""Ground camera: the eye does not rise more than CAP units above its on-ground height while Caim is in the air (it clipped through low ceilings when he jumped). Hook 001974D4 (swc1 f2,4(s0): the final eye y, y is negative up;
its delay slot 001974D8 swc1 f3,8(s0) still runs) -> j CEIL. While Caim is on the ground (y within 2 of the ground height [Caim+0x650]) the eye y is saved in BASE; in the air the eye y is limited to BASE - CAP (not while he rides
Angelus: 003ACC94 == 2, and not before a first ground frame: BASE 0). Returns to 001974DC."""
import sys, struct
sys.path.insert(0, r'C:\Users\shade\OneDrive\Documents\PCSX2\roms\drakengard_mod\src\lib')
from mipsasm import Asm
CEIL = 0x5AF200
BASE = -0xD40            # 005AF2C0 (lui 0x5B)
CAP = 0.0
def fb(x): return struct.unpack('<I', struct.pack('<f', x))[0]
def build():
    a = Asm(CEIL)
    a.emit('lui', 't0', 0x3B); a.emit('lw', 't1', -0x336C, 't0'); a.emit('addiu', 't1', 't1', -2)
    a.emit('beq', 't1', 'zero', 'STORE'); a.emit('nop')
    a.emit('lui', 't2', 0x5B)
    a.emit('lwc1', 'f4', -14748, 't0'); a.emit('lwc1', 'f5', -13264, 't0')
    a.emit('lui', 'at', fb(2.0) >> 16); a.emit('mtc1', 'at', 'f6'); a.emit('add.s', 'f7', 'f4', 'f6')
    a.emit('c.olt.s', 'f7', 'f5'); a.emit('bc1t', 'AIR'); a.emit('nop')
    a.emit('swc1', 'f2', BASE, 't2'); a.emit('beq', 'zero', 'zero', 'STORE'); a.emit('nop')
    a.label('AIR')
    a.emit('lwc1', 'f6', BASE, 't2'); a.emit('mfc1', 't3', 'f6'); a.emit('beq', 't3', 'zero', 'STORE'); a.emit('nop')
    a.emit('lui', 'at', fb(CAP) >> 16); a.emit('mtc1', 'at', 'f7'); a.emit('sub.s', 'f6', 'f6', 'f7')
    a.emit('c.olt.s', 'f2', 'f6'); a.emit('bc1f', 'STORE'); a.emit('nop')
    a.emit('mov.s', 'f2', 'f6')
    a.label('STORE')
    a.emit('swc1', 'f2', 4, 's0'); a.emit('j', 0x1974DC); a.emit('nop')
    return a
def patches():
    w = build().assemble()
    return [(CEIL + 4 * i, x) for i, x in enumerate(w)] + [(0x1974D4, 0x08000000 | (CEIL >> 2))]
if __name__ == '__main__':
    for ad, x in patches(): print('patch=1,EE,%08X,word,%08X' % (ad, x))
