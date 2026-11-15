"""Sprint attack and jump sprint attack deal half damage. The enemy hit function (FUN_00184A18; s0 = the enemy, a0 of the damage lookup
FUN_00194D80 = the hit's attack id, halfword [s0+0x18E]) gets the damage in v0 and keeps it in s1. The word at 00184C84 (lhu v1,0x188(s0),
whose delay-slot partner 00184C88 = daddu s1,v0,zero still runs) becomes j SPR: the cave redoes the lhu and, when the attack id is 0x235
(565: both the sprint attack and the jump sprint attack, measured with an execution breakpoint on 00194D80), scales s1 by 0.25 (it was 0.1, then 0.2, 2026-10-30)."""
import sys
sys.path.insert(0, r'C:\Users\shade\OneDrive\Documents\PCSX2\roms\drakengard_mod\src\lib')
from mipsasm import Asm
SPR = 0x5BDE00
ATTACK_ID = 0x235
def build():
    a = Asm(SPR)
    a.emit('lhu', 'v1', 0x188, 's0')                                      # the replaced instruction
    a.emit('lhu', 't0', 0x18E, 's0'); a.emit('xori', 't0', 't0', ATTACK_ID)
    a.emit('bne', 't0', 'zero', 'OUT'); a.emit('nop')
    a.emit('mtc1', 's1', 'f4'); a.emit('cvt.s.w', 'f4', 'f4'); a.emit('lui', 'at', 0x3E80); a.emit('ori', 'at', 'at', 0x0000); a.emit('mtc1', 'at', 'f5')
    a.emit('mul.s', 'f4', 'f4', 'f5'); a.emit('cvt.w.s', 'f4', 'f4'); a.emit('mfc1', 's1', 'f4')
    a.label('OUT')
    a.emit('j', 0x184C8C); a.emit('nop')
    return a
def patches():
    return [(SPR + 4 * i, w) for i, w in enumerate(build().assemble())] + [(0x184C84, 0x08000000 | (SPR >> 2))]
if __name__ == '__main__':
    for ad, w in patches(): print('patch=1,EE,%08X,word,%08X' % (ad, w))



