"""Double jump air slash: half the jump force. The jump arc function FUN_001756B0 (jump types 1 / 2, called from the jump state at
0017503C / 00175050) loads its arc height f21 = -28.0 (gp-30532) at 001756EC; the vertical movement of each frame is
sin(angle) * f21 minus the last frame's part. While the slash double jump flag 0033F6DC is 0x800 (the 2nd air slash; 0xC00 = 3rd) the height is halved."""
import sys
sys.path.insert(0, r'C:\Users\shade\OneDrive\Documents\PCSX2\roms\drakengard_mod\src\lib')
from mipsasm import Asm
CAVE = 0x5BDD00
HOOK = 0x1756EC
def build():
    a = Asm(CAVE)
    a.emit('lwc1', 'f21', -30532, 'gp')                                  # the replaced instruction
    a.emit('lui', 't8', 0x34); a.emit('lw', 't8', -0x924, 't8')          # 0033F6DC: 0 / 0x800 / 0xC00
    a.emit('nop'); a.emit('beq', 't8', 'zero', 'OUT'); a.emit('nop')
    a.emit('lui', 't9', 0x3E80); a.emit('mtc1', 't9', 'f4'); a.emit('mul.s', 'f21', 'f21', 'f4')
    a.label('OUT')
    a.emit('j', 0x1756F4); a.emit('nop')
    return a
def patches():
    return [(CAVE + 4 * i, w) for i, w in enumerate(build().assemble())] + [(HOOK, 0x08000000 | (CAVE >> 2))]
if __name__ == '__main__':
    for ad, w in patches(): print('patch=1,EE,%08X,word,%08X' % (ad, w))


