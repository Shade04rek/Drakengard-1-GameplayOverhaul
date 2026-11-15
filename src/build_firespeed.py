"""Ridden Angelus fire stream faster. The flame stream spawns particles through FUN_0022DDDC (called at 0018D438 by the effect update); FUN_0022D63C initialises them: for type 0 the speed (+8) is
rand * 4.0 + 5.0 (lui at,4080 at 0022D6B8, lui at,40A0 at 0022D6C4), i.e. 5..9 per frame. WRAP (005BC700, 0018D438 jal 0022DDDC -> jal WRAP) sets the word FLG (005BEE14) while that call runs. SPD (005BC740, hook 0022D6BC
mtc1 at,f1 -> j SPD, delay slot 0022D6C0 addiu v1,zero,8 harmless, returns to 0022D6CC) uses 8.0 / 10.0 instead of 4.0 / 5.0 (twice the speed: +0x00800000 on the exponent) while FLG is set; other particles are untouched."""
import sys
sys.path.insert(0, r'C:\Users\shade\OneDrive\Documents\PCSX2\roms\drakengard_mod\src\lib')
from mipsasm import Asm
WRAP, SPD = 0x5BC700, 0x5BC740
FLG, RAW = -0x11EC, -0x11E8        # 005BEE14 / 005BEE18 (lui 0x5C)
RANGE_HI, BASE_HI = 0x4100, 0x4120  # 8.0 and 10.0 (2x); vanilla 0x4080 / 0x40A0
def wrap():
    a = Asm(WRAP)
    a.emit('lui', 't9', 0x5C); a.emit('sw', 'ra', RAW, 't9'); a.emit('ori', 't8', 'zero', 1); a.emit('sw', 't8', FLG, 't9')
    a.emit('jal', 0x22DDDC); a.emit('nop')
    a.emit('lui', 't9', 0x5C); a.emit('sw', 'zero', FLG, 't9'); a.emit('lw', 'ra', RAW, 't9'); a.emit('jr', 'ra'); a.emit('nop')
    return a
def spd():
    a = Asm(SPD)
    a.emit('lui', 't8', 0x5C); a.emit('lw', 't9', FLG, 't8'); a.emit('bne', 't9', 'zero', 'FAST'); a.emit('nop')
    a.emit('mtc1', 'at', 'f1'); a.emit('lui', 'at', 0x40A0); a.emit('mtc1', 'at', 'f2'); a.emit('j', 0x22D6CC); a.emit('nop')
    a.label('FAST')
    a.emit('lui', 'at', RANGE_HI); a.emit('mtc1', 'at', 'f1'); a.emit('lui', 'at', BASE_HI); a.emit('mtc1', 'at', 'f2'); a.emit('j', 0x22D6CC); a.emit('nop')
    return a
def patches():
    p = []
    for base, b in ((WRAP, wrap()), (SPD, spd())): p += [(base + 4 * i, w) for i, w in enumerate(b.assemble())]
    p += [(0x18D438, 0x0C000000 | (WRAP >> 2)), (0x22D6BC, 0x08000000 | (SPD >> 2))]
    return p
if __name__ == '__main__':
    for ad, w in patches(): print('patch=1,EE,%08X,word,%08X' % (ad, w))
