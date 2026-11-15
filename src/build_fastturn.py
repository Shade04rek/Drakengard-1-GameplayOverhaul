"""Fast mode turns a bit slower: the heading step of the ridden ground Angelus is (turn rate +0xB0) / D with D = 26.6 (001C471C, patched lui 41D5) or 14.6 (001C47F8, lui 416A) = 1.5x the vanilla 40 / 22 (see the pnach
section on the yaw divisors). FIX1 (005BCE00, hook 001C4720 mtc1 at,f5, delay slot nop, returns to 001C4728) and FIX2 (005BCE40, hook 001C47FC mtc1 at,f0, returns to 001C4800) load the divisor themselves: in fast mode
(toggle word 005BEE0C == 0) 32.0 / 17.625 (= 1.25x vanilla), otherwise the existing 26.6 / 14.6 (1.5x)."""
import sys, struct
sys.path.insert(0, r'C:\Users\shade\OneDrive\Documents\PCSX2\roms\drakengard_mod\src\lib')
from mipsasm import Asm
FIX1, FIX2 = 0x5BCE00, 0x5BCE40
FAST1, FAST2 = 0x4200, 0x418D       # 32.0 and 17.625 (vanilla 40 / 22 divided by 1.25)
STD1, STD2 = 0x41D5, 0x416A         # 26.6 and 14.6 (1.5x), as patched at 001C471C / 001C47F8
def fix(base, fast, std, ret, reg):
    a = Asm(base)
    a.emit('lui', 't8', 0x5C); a.emit('lw', 't9', -0x11F4, 't8'); a.emit('bne', 't9', 'zero', 'STD'); a.emit('nop')
    a.emit('lui', 'at', fast); a.emit('beq', 'zero', 'zero', 'SET'); a.emit('nop')
    a.label('STD'); a.emit('lui', 'at', std)
    a.label('SET'); a.emit('mtc1', 'at', reg); a.emit('j', ret); a.emit('nop')
    return a
def patches():
    p = []
    for base, b in ((FIX1, fix(FIX1, FAST1, STD1, 0x1C4728, 'f5')), (FIX2, fix(FIX2, FAST2, STD2, 0x1C4800, 'f0'))):
        p += [(base + 4 * i, w) for i, w in enumerate(b.assemble())]
    p += [(0x1C4720, 0x08000000 | (FIX1 >> 2)), (0x1C47FC, 0x08000000 | (FIX2 >> 2))]
    return p
if __name__ == '__main__':
    for ad, w in patches(): print('patch=1,EE,%08X,word,%08X' % (ad, w))
