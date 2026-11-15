import sys
sys.path.insert(0, r'C:\Users\shade\OneDrive\Documents\PCSX2\roms\drakengard_mod\src\lib')
from mipsasm import Asm
PRE = 0x5BB200
# EYEFIX (005B5E00, run at 001974B8 after the game's camera collision 001A1930 / 001A2B3C) used the full arm length
# [cam+0x14C] = 68 as its sphere radius, so it pushed a collision-shortened eye back out through walls. Its first word
# (lwc1 f4,0x6C(s1)) becomes j PRE; the lui at,0x4120 in the delay slot still runs. PRE sets f4 = the arm the collision
# left, |eye (sp+0..8) - aim (s1 = cam+0xE0)|, capped at [cam+0x14C], and returns to 005B5E08. Uses f1, f2, f4 only.
def build():
    a = Asm(PRE)
    a.emit('lwc1', 'f1', 0, 'sp'); a.emit('lwc1', 'f2', 0, 's1'); a.emit('sub.s', 'f1', 'f1', 'f2'); a.emit('mul.s', 'f4', 'f1', 'f1')
    for o in (4, 8):
        a.emit('lwc1', 'f1', o, 'sp'); a.emit('lwc1', 'f2', o, 's1'); a.emit('sub.s', 'f1', 'f1', 'f2')
        a.emit('mul.s', 'f1', 'f1', 'f1'); a.emit('add.s', 'f4', 'f4', 'f1')
    a.emit('sqrt.s', 'f4', 'f4')
    a.emit('lwc1', 'f2', 0x6C, 's1')
    a.emit('c.olt.s', 'f2', 'f4'); a.emit('bc1f', 'OK'); a.emit('nop')
    a.emit('mov.s', 'f4', 'f2')
    a.label('OK')
    a.emit('j', 0x5B5E08); a.emit('nop')
    return a
def patches():
    return [(PRE + 4 * i, w) for i, w in enumerate(build().assemble())] + [(0x5B5E00, 0x08000000 | (PRE >> 2))]
if __name__ == '__main__':
    for ad, w in patches(): print('patch=1,EE,%08X,word,%08X' % (ad, w))

