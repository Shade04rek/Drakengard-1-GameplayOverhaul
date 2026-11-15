"""Brake mode (R3 toggle on, word 005BEE0C = 1) swaps the two sticks for the ridden ground Angelus: the pad bytes 00342864 / 00342865 (right stick x / y) and 00342866 / 00342867 (left stick x / y) are swapped
at the start of every ground pad update, so the game's steering, aim pitch and dodge direction read the right stick, while STRAFE / TILT (build_strafe.py, which read 00342864 / 5) get the original left stick.
SWAP (005BC9A0): entered instead of TILTF from 00321A74 (the ground path of the pad update chain T2; the delay slot lui t8,0034 still runs): Caim rides (003ACC94 == 2), ground stage (00340DFC == 0), toggle on -> swap.
Then j TILTF (005B8400) as before. Registers used: t0, t1, t3 (the chain sets them again); t2 / t5 / t8 are kept. Buttons (R3 / L3 ...) are untouched."""
import sys
sys.path.insert(0, r'C:\Users\shade\OneDrive\Documents\PCSX2\roms\drakengard_mod\src\lib'); sys.path.insert(0, r'C:\Users\shade\OneDrive\Documents\PCSX2\roms\drakengard_mod\src')
from mipsasm import Asm
import build_aerialboost as AB
SWAP = 0x5BC9A0
TILTF = 0x5B8400
def build():
    a = Asm(SWAP)
    a.emit('lui', 't0', 0x3B); a.emit('lw', 't1', -0x336C, 't0'); a.emit('addiu', 't1', 't1', -2); a.emit('bne', 't1', 'zero', 'OUT'); a.emit('nop')
    a.emit('lui', 't0', 0x34); a.emit('lw', 't1', 0xDFC, 't0'); a.emit('bne', 't1', 'zero', 'OUT'); a.emit('nop')
    # the reticle's core colour (RGBAQ word 005A07A0 of the star packet): white in brake mode, the red 802030F0 otherwise
    a.emit('lui', 't1', 0x5C); a.emit('lw', 't1', AB.TGB, 't1'); a.emit('lui', 't3', 0x5A); a.emit('beq', 't1', 'zero', 'RED'); a.emit('nop')
    a.emit('lui', 't4', 0x80FF); a.emit('ori', 't4', 't4', 0xFFFF); a.emit('sw', 't4', 0x7A0, 't3'); a.emit('beq', 'zero', 'zero', 'SWP'); a.emit('nop')
    a.label('RED'); a.emit('lui', 't4', 0x8020); a.emit('ori', 't4', 't4', 0x30F0); a.emit('sw', 't4', 0x7A0, 't3'); a.emit('beq', 'zero', 'zero', 'OUT'); a.emit('nop')
    a.label('SWP')
    for o in (0, 1):
        a.emit('lbu', 't1', 0x2864 + o, 't0'); a.emit('lbu', 't3', 0x2866 + o, 't0'); a.emit('sb', 't3', 0x2864 + o, 't0'); a.emit('sb', 't1', 0x2866 + o, 't0')
    a.emit('lbu', 't1', 0x2867, 't0'); a.emit('xori', 't1', 't1', 0xFF); a.emit('sb', 't1', 0x2867, 't0')          # the steering stick (now in the left slot): up / down inverted
    a.label('OUT'); a.emit('j', TILTF); a.emit('nop')
    return a
def patches():
    w = build().assemble()
    return [(SWAP + 4 * i, x) for i, x in enumerate(w)] + [(0x321A74, 0x08000000 | (SWAP >> 2))]
if __name__ == '__main__':
    p = patches(); print(len(p) - 1, 'words, ends %X' % (SWAP + 4 * (len(p) - 1)))
