"""Caim's attacks block enemy spell balls (no damage). FUN_00179598 (a0 = Caim, a1 = hit record) copies the hit data into Caim
(+0x188..0x1E8) and then, at 00179890 (addiu v0,zero,5, right before the L2 block test 'state == 5 ...'), looks at the state. The hook there
(j DEFL) returns v0 = 2 (blocked, no damage; the function's epilogue 00179934) when the hit's attack id (lhu [s1+0x24]) is 0x28D (the enemy
spell ball) or 0x289 (arrow) and Caim is in an attack (main state 2, sub state [+0x2DC] 4 ground attack / 5 air attack), so that the hit data copy still ran
as for the real L2 block, after spawning the block's spark effect. Otherwise it runs the replaced instruction and continues at 00179894. v1 (= [Caim+0x2D0]) is left untouched."""
import sys
sys.path.insert(0, r'C:\Users\shade\OneDrive\Documents\PCSX2\roms\drakengard_mod\src\lib')
from mipsasm import Asm
DEFL = 0x5BE100
HOOK = 0x179890
IDS = (0x28D, 0x289)
GAIR = 0x3F00           # c^2 for the air attack arc (0.5 = 270 degrees); the ground arc uses 0.25 (240 degrees)
def build():
    a = Asm(DEFL)
    a.emit('lhu', 't0', 0x24, 's1')
    for i in IDS:
        a.emit('xori', 't1', 't0', i); a.emit('beq', 't1', 'zero', 'ID'); a.emit('nop')
    a.emit('beq', 'zero', 'zero', 'NORM'); a.emit('nop')
    a.label('ID')
    a.emit('lw', 't0', 0x2D0, 's0'); a.emit('xori', 't0', 't0', 2); a.emit('bne', 't0', 'zero', 'NORM'); a.emit('nop')
    a.emit('lw', 't0', 0x2DC, 's0'); a.emit('addiu', 't0', 't0', -4); a.emit('sltiu', 't0', 't0', 2); a.emit('beq', 't0', 'zero', 'NORM'); a.emit('nop')
    # arc of protection: the projectile (record +0x80/+0x88) relative to Caim (+0x80/+0x88), against his facing (+0x70/+0x78). dot >= 0 is always in front;
    # behind that line it still blocks while dot^2 <= c^2 * dist^2 (angle from the facing <= 120 deg ground: c = cos 60 = 0.5, c^2 = 0.25; 135 deg air: c^2 = 0.5)
    a.emit('lwc1', 'f4', 0x80, 's1'); a.emit('lwc1', 'f5', 0x80, 's0'); a.emit('sub.s', 'f4', 'f4', 'f5')
    a.emit('lwc1', 'f6', 0x88, 's1'); a.emit('lwc1', 'f5', 0x88, 's0'); a.emit('sub.s', 'f6', 'f6', 'f5')
    a.emit('lwc1', 'f8', 0x70, 's0'); a.emit('mul.s', 'f8', 'f4', 'f8'); a.emit('lwc1', 'f9', 0x78, 's0'); a.emit('mul.s', 'f9', 'f6', 'f9')
    a.emit('add.s', 'f10', 'f8', 'f9'); a.emit('mtc1', 'zero', 'f5'); a.emit('c.olt.s', 'f10', 'f5'); a.emit('bc1f', 'INARC'); a.emit('nop')
    a.emit('mul.s', 'f11', 'f10', 'f10'); a.emit('mul.s', 'f12', 'f4', 'f4'); a.emit('mul.s', 'f13', 'f6', 'f6'); a.emit('add.s', 'f12', 'f12', 'f13')
    a.emit('lw', 't0', 0x2DC, 's0'); a.emit('xori', 't0', 't0', 5); a.emit('lui', 'at', 0x3E80); a.emit('bne', 't0', 'zero', 'GRDC'); a.emit('nop')
    a.emit('lui', 'at', GAIR)
    a.label('GRDC')
    a.emit('mtc1', 'at', 'f13'); a.emit('mul.s', 'f12', 'f12', 'f13'); a.emit('c.olt.s', 'f12', 'f11'); a.emit('bc1t', 'NORM'); a.emit('nop')
    a.label('INARC')
    # enter the real L2 block like the game's own guard path: s3 = 2, a0 = Caim, continue at 00179918 (jal 00179954 -> state 5 with the block callback 001799F8, v0 = 2)
    a.emit('lui', 't3', 0x5C); a.emit('ori', 't4', 'zero', 2); a.emit('sw', 't4', -0x1E0C, 't3')    # DFB (005BE1F4) = 2: the next BH2 call (cave in the sprint combo builder) makes it 1 = a deflect block
    a.emit('addiu', 's3', 'zero', 2); a.emit('daddu', 'a0', 's0', 'zero'); a.emit('j', 0x179918); a.emit('nop')
    a.label('NORM')
    a.emit('addiu', 'v0', 'zero', 5); a.emit('j', 0x179894); a.emit('nop')
    return a
def patches():
    return [(DEFL + 4 * i, w) for i, w in enumerate(build().assemble())] + [(HOOK, 0x08000000 | (DEFL >> 2))]
if __name__ == '__main__':
    for ad, w in patches(): print('patch=1,EE,%08X,word,%08X' % (ad, w))
