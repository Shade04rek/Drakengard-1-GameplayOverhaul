"""Ridden ground Angelus: the dodge side follows the left stick (caves SIDE 005BCE00 / SIDE2 005BCEA0, hooks 001C4E10 (fp) and 001C3658 (s6; the second copy of the same dodge input code) = lw v1,0xC(fp) in the ground dragon dodge input code; the lui v0,0x100 behind it runs in the delay slot).
The action word [fp+0xC] holds the dodge bits 0x1000000 (left dodge, buffer +0x3DC4) and 0x2000000 (right dodge, buffer +0x3DC8). One bit set, ground stage, stick pushed (|x| + |y| >= 16 around 0x80):
the bit becomes the stick side (x < 0 left, otherwise right, like the cones of DRT); stick at rest: the button's own side. Both bits set (the Triangle U-turn) are left alone."""
import sys
sys.path.insert(0, r'C:\Users\shade\OneDrive\Documents\PCSX2\roms\drakengard_mod\src\lib')
from mipsasm import Asm
SIDE = 0x5BCE00
SIDE2 = 0x5BCEA0
HOOK = 0x1C4E10
HOOK2 = 0x1C3658
def build(base=SIDE, reg='fp', ret=0x1C4E18):
    a = Asm(base)
    a.emit('lw', 'v1', 0xC, reg)
    a.emit('lui', 'at', 0x0300); a.emit('and', 't8', 'v1', 'at'); a.emit('beq', 't8', 'zero', 'DONE'); a.emit('nop')
    a.emit('xor', 't9', 't8', 'at'); a.emit('beq', 't9', 'zero', 'DONE'); a.emit('nop')                       # both bits: U-turn
    a.emit('lui', 'k0', 0x34); a.emit('lw', 'k1', 0xDFC, 'k0'); a.emit('bne', 'k1', 'zero', 'DONE'); a.emit('nop')      # ground stages only
    a.emit('lbu', 't9', 0x2866, 'k0'); a.emit('lbu', 'k1', 0x2867, 'k0'); a.emit('addiu', 't9', 't9', -128); a.emit('addiu', 'k1', 'k1', -128)
    a.emit('sra', 'k0', 't9', 31); a.emit('xor', 'at', 't9', 'k0'); a.emit('subu', 'at', 'at', 'k0')                  # |x|
    a.emit('sra', 'k0', 'k1', 31); a.emit('xor', 'k1', 'k1', 'k0'); a.emit('subu', 'k1', 'k1', 'k0')                  # |y|
    a.emit('addu', 'at', 'at', 'k1'); a.emit('slti', 'at', 'at', 16); a.emit('bne', 'at', 'zero', 'DONE'); a.emit('nop')   # stick at rest: the button's side
    a.emit('lui', 'at', 0x0300); a.emit('nor', 'at', 'at', 'zero'); a.emit('and', 'v1', 'v1', 'at')                    # clear both bits
    a.emit('lui', 't8', 0x0200); a.emit('slt', 't9', 't9', 'zero'); a.emit('beq', 't9', 'zero', 'SET'); a.emit('nop'); a.emit('lui', 't8', 0x0100)
    a.label('SET'); a.emit('or', 'v1', 'v1', 't8'); a.emit('sw', 'v1', 0xC, reg)
    a.label('DONE'); a.emit('j', ret); a.emit('nop')
    return a.assemble()
def patches():
    w = build(); w2 = build(SIDE2, 's6', 0x1C3660); assert SIDE + 4 * len(w) <= SIDE2 and SIDE2 + 4 * len(w2) <= 0x5BCF80
    return [(SIDE + 4 * i, x) for i, x in enumerate(w)] + [(HOOK, 0x08000000 | (SIDE >> 2))] + [(SIDE2 + 4 * i, x) for i, x in enumerate(w2)] + [(HOOK2, 0x08000000 | (SIDE2 >> 2))]
if __name__ == '__main__':
    for ad, x in patches(): print('patch=1,EE,%08X,word,%08X' % (ad, x))



