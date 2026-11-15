"""Ridden Angelus: every hit does normal (1x) damage; Caim is knocked off by chance depending on his health after the hit (> 50% of +0x284: never; 26-50%: 25%; 1-25%: 50%).
DMG rolls (xorshift word 005BEE04) on every hit and leaves the result in word 005BEE00; CLAMP turns it into s3 = 1 with the gauge set to 0x5001 (like the game's own gauge knock-off).
00179214 (invulnerability 0x800 at zero health) is nopped so Caim stays hittable at 1 HP. Older description:
FUN_00179100 (Caim = s1, the rider damage function; Angelus = Caim +0x6B0, its hit flag +0x424 is set by the Angelus hit function 0017E8C8) subtracts the damage s0
(from FUN_00194D80, called at 001791A8) from Caim's health (+0x280) and adds a stability value to the gauge +0x770; it returns 1 (= knocked off) when the health
runs out (001791F8..00179204, addiu s3,zero,1) or the gauge goes above 0x5000 (movz s3 at 00179260).
- 001791A8 jal 00194D80 -> jal DMG: calls the real function and leaves its result unchanged (ra saved in word 005BEBF4).
- 00179204 and 00179260 become nops (s3 stays 0: never knocked off). Health still stops at 1 (the game's own floor), so Caim cannot die while riding.
- 00179264 (lw v0,0x770(s1)) -> j CLAMP: the gauge is held at 0x5000 at most (so the flag +0x428 and the gauge test of the mount code stay 'normal')."""
import sys
sys.path.insert(0, r'C:\Users\shade\OneDrive\Documents\PCSX2\roms\drakengard_mod\src\lib')
from mipsasm import Asm
DMG = 0x5BEC80
CLAMP = 0x5BED80
FLG = -0x1200        # 005BEE00 (lui 0x5C): 1 = this hit knocks Caim off
SEED = -0x11FC       # 005BEE04 xorshift state
RAW = -0x11F8        # 005BEE08 saved ra
def dmg():
    a = Asm(DMG)
    a.emit('lui', 't0', 0x5C); a.emit('sw', 'ra', RAW, 't0')
    a.emit('jal', 0x194D80); a.emit('nop')
    a.emit('lui', 't0', 0x5C); a.emit('lw', 'ra', RAW, 't0')
    a.emit('nop'); a.emit('nop')
    a.emit('beq', 'v0', 'zero', 'DONE'); a.emit('nop')
    # health after this hit (floor 1) against the maximum (+0x284)
    a.emit('lw', 't2', 0x280, 's1'); a.emit('subu', 't2', 't2', 'v0'); a.emit('slti', 't3', 't2', 1); a.emit('beq', 't3', 'zero', 'H1'); a.emit('nop')
    a.emit('ori', 't2', 'zero', 1)
    a.label('H1')
    a.emit('lw', 't3', 0x284, 's1'); a.emit('sll', 't4', 't2', 1); a.emit('slt', 't5', 't3', 't4'); a.emit('bne', 't5', 'zero', 'DONE'); a.emit('nop')
    a.emit('lui', 't6', 0x5C); a.emit('lw', 't7', SEED, 't6'); a.emit('bne', 't7', 'zero', 'SOK'); a.emit('nop')
    a.emit('lui', 't7', 0x2F6B); a.emit('ori', 't7', 't7', 0x1D35)
    a.label('SOK')
    a.emit('sll', 't8', 't7', 13); a.emit('xor', 't7', 't7', 't8'); a.emit('srl', 't8', 't7', 17); a.emit('xor', 't7', 't7', 't8')
    a.emit('sll', 't8', 't7', 5); a.emit('xor', 't7', 't7', 't8'); a.emit('sw', 't7', SEED, 't6')
    a.emit('srl', 't7', 't7', 8); a.emit('andi', 't7', 't7', 3)
    a.emit('sll', 't4', 't2', 2); a.emit('slt', 't5', 't3', 't4'); a.emit('bne', 't5', 'zero', 'MID'); a.emit('nop')
    a.emit('sltiu', 't8', 't7', 2); a.emit('beq', 'zero', 'zero', 'SETF'); a.emit('nop')
    a.label('MID')
    a.emit('sltiu', 't8', 't7', 1)
    a.label('SETF')
    a.emit('sw', 't8', FLG, 't6')
    a.label('DONE')
    a.emit('jr', 'ra'); a.emit('nop')
    return a.assemble()
def clamp():
    a = Asm(CLAMP)
    a.emit('lui', 't6', 0x5C); a.emit('lw', 't2', FLG, 't6'); a.emit('sw', 'zero', FLG, 't6')
    a.emit('beq', 't2', 'zero', 'NORM'); a.emit('nop')
    a.emit('ori', 'v0', 'zero', 0x5001); a.emit('sw', 'v0', 0x770, 's1'); a.emit('ori', 's3', 'zero', 1); a.emit('j', 0x179268); a.emit('nop')
    a.label('NORM')
    a.emit('lw', 'v0', 0x770, 's1'); a.emit('slti', 'v1', 'v0', 0x5001); a.emit('bne', 'v1', 'zero', 'OK'); a.emit('nop')
    a.emit('ori', 'v0', 'zero', 0x5000); a.emit('sw', 'v0', 0x770, 's1')
    a.label('OK'); a.emit('j', 0x179268); a.emit('nop')
    return a.assemble()
def patches():
    d = dmg(); c = clamp(); assert DMG + 4 * len(d) <= CLAMP and CLAMP + 4 * len(c) <= 0x5BEE00
    p = [(DMG + 4 * i, x) for i, x in enumerate(d)] + [(CLAMP + 4 * i, x) for i, x in enumerate(c)]
    p += [(0x1791A8, 0x0C000000 | (DMG >> 2)), (0x179204, 0), (0x179214, 0), (0x179260, 0), (0x179264, 0x08000000 | (CLAMP >> 2))]
    return p
if __name__ == '__main__':
    for ad, x in patches(): print('patch=1,EE,%08X,word,%08X' % (ad, x))
