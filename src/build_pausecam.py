"""Pause camera: no camera movement from the sticks while the game is paused. While the pause flag 004EE29C is not 0 (pause menu opening / open, mission briefing; 0 in play) the two camera stick readers see 0:
CAMX1 (005BCB80, hook 0013E2A8 lwc1 f1,0x2F88(at) = the orbit yaw stick x of the world-fixed orbit; the delay slot 0013E2AC lwc1 f2 stays) and CAMX2 (005BCBA0, hook 005BB404 lwc1 f8,0x2F8C(at) = the pitch stick y;
the delay slot 005BB408 abs.s f8,f8 is redone inside the cave)."""
import sys
sys.path.insert(0, r'C:\Users\shade\OneDrive\Documents\PCSX2\roms\drakengard_mod\src\lib')
from mipsasm import Asm
CAMX1, CAMX2 = 0x5BCB80, 0x5BCBA0
def cx1():
    a = Asm(CAMX1)
    a.emit('lwc1', 'f1', 0x2F88, 'at')
    a.emit('lui', 't8', 0x4F); a.emit('lw', 't9', -0x1D64, 't8'); a.emit('beq', 't9', 'zero', 'OUT'); a.emit('nop'); a.emit('mtc1', 'zero', 'f1')
    a.label('OUT'); a.emit('j', 0x13E2B0); a.emit('nop')
    return a
def cx2():
    a = Asm(CAMX2)
    a.emit('lwc1', 'f8', 0x2F8C, 'at')
    a.emit('lui', 't8', 0x4F); a.emit('lw', 't9', -0x1D64, 't8'); a.emit('beq', 't9', 'zero', 'OUT'); a.emit('nop'); a.emit('mtc1', 'zero', 'f8')
    a.label('OUT'); a.emit('abs.s', 'f8', 'f8'); a.emit('j', 0x5BB40C); a.emit('nop')
    return a
def patches():
    p = []
    for base, b in ((CAMX1, cx1()), (CAMX2, cx2())): p += [(base + 4 * i, w) for i, w in enumerate(b.assemble())]
    p += [(0x13E2A8, 0x08000000 | (CAMX1 >> 2)), (0x5BB404, 0x08000000 | (CAMX2 >> 2))]
    return p
if __name__ == '__main__':
    for ad, w in patches(): print('patch=1,EE,%08X,word,%08X' % (ad, w))
