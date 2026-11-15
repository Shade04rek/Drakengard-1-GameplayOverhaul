"""Ridden ground Angelus: movement stays controllable during the R1 special (spell), boost / dodges / attacks do not. FUN_001C09C8 (the ground ride update): while the special timer (+0x3DB8) runs it
(1) zeroes the lean +0xB4 (001C0A04 swc1 f13,180(s0)), (2) forces the pitch +0xC8 = -0.25 (001C0A08), (3) zeroes the movement vector +0xF0 (001C0A0C sqc2 f0,0(v1)) and (4) zeroes the three angle deltas +0x100 / 104 / 108 (001C0A14
sqc2 f0,0(v0)), so she stood still and could not turn. Now (1) and (3) are nops and (4) is sw zero,256(s0): only the pitch delta is zeroed (the pitch stays at -0.25 for the spell), she moves, turns and banks as usual.
PRE (005BCD80, hook 001C09DC jal 001C3EBC -> jal PRE, delay slot daddu s1,a1,zero has run): while the special timer runs the pad action words a1+8 (L2 held, bit 0x100) and a1+0xC (0x100, and the dodge bits
0x01000000 / 0x02000000) are cleared and the dodge buffers +0x3DC4 / +0x3DC8 zeroed, so the boost and the dodge buttons do nothing; then j 001C3EBC. The L3 dodge of brake mode (DOD) checks the timer too."""
import sys
sys.path.insert(0, r'C:\Users\shade\OneDrive\Documents\PCSX2\roms\drakengard_mod\src\lib')
from mipsasm import Asm
PRE = 0x5BCD80
LP = 0x5BC680        # build_glideboost.py: L3 boost cancel (fast mode), then j PRE
def build():
    a = Asm(PRE)
    a.emit('lw', 't8', 15800, 's0'); a.emit('beq', 't8', 'zero', 'GO'); a.emit('nop')
    a.emit('lw', 't9', 8, 'a1'); a.emit('lui', 't8', 0xFFFF); a.emit('ori', 't8', 't8', 0xFEFF); a.emit('and', 't9', 't9', 't8'); a.emit('sw', 't9', 8, 'a1')
    a.emit('lw', 't9', 12, 'a1'); a.emit('lui', 't8', 0xFCFF); a.emit('ori', 't8', 't8', 0xFEFF); a.emit('and', 't9', 't9', 't8'); a.emit('sw', 't9', 12, 'a1')
    a.emit('sw', 'zero', 15812, 's0'); a.emit('sw', 'zero', 15816, 's0')
    a.label('GO'); a.emit('j', 0x1C3EBC); a.emit('nop')
    return a
def patches():
    w = build().assemble()
    p = [(PRE + 4 * i, x) for i, x in enumerate(w)]
    p += [(0x1C09DC, 0x0C000000 | (LP >> 2)), (0x1C0A04, 0), (0x1C0A0C, 0), (0x1C0A14, 0xAE000100)]
    return p
if __name__ == '__main__':
    for ad, w in patches(): print('patch=1,EE,%08X,word,%08X' % (ad, w))

