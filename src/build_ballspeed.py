"""Enemy spell (magic ball) travel speed: the ball item's flight function (FUN_0018FE18, called through the item's state table at 00521CB0)
moves it each frame by velocity ([s0+0x1B0], 3 floats) x dt (lwc1 f0,44(a1) with a1 = 003A9300, i.e. 003A932C): 18FE70 lwc1 f5,0(sp); 18FE74 lwc1 f0,44(a1);
18FE84 / 18FE88 / 18FE90 mul.s by f0; the sum is stored to the position by the swc1 at 18FF18 (found with a write breakpoint on 003E5CF0).
The word at 0018FE70 becomes j SPEED; its delay slot (the original lwc1 f0,44(a1)) still runs, the cave redoes lwc1 f5,0(sp) and doubles f0."""
import sys
sys.path.insert(0, r'C:\Users\shade\OneDrive\Documents\PCSX2\roms\drakengard_mod\src\lib')
from mipsasm import Asm
SPEED = 0x5BDE80
FACTOR_HI = 0x4000      # 2.0
def build():
    a = Asm(SPEED)
    a.emit('lwc1', 'f5', 0, 'sp')                       # the replaced instruction
    a.emit('lui', 'at', FACTOR_HI); a.emit('mtc1', 'at', 'f6'); a.emit('mul.s', 'f0', 'f0', 'f6')
    a.emit('j', 0x18FE78); a.emit('nop')
    return a
def patches():
    return [(SPEED + 4 * i, w) for i, w in enumerate(build().assemble())] + [(0x18FE70, 0x08000000 | (SPEED >> 2))]
if __name__ == '__main__':
    for ad, w in patches(): print('patch=1,EE,%08X,word,%08X' % (ad, w))
