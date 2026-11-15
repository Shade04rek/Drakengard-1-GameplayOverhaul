"""Caim keeps facing the enemy / the block direction during a jump while the block is held. The jump state wrapper JW (005B8230, section 'Lock-on: air attacks face the target') calls FUN_00174FC0 and then, only with the R3 lock-on on and a jump
attack running (jump type [+0x660] != 0), calls ISOJW (005BAE40 -> FACE 00341E00, which turns Caim to the nearest / locked enemy through SEL; 005A0900 = the remembered enemy, 0 = none). The game's own block faces the nearest enemy on the ground but not
in the air. The word 005B8254 (beq t0,zero,005B8284: no R3 lock-on) is j BLK (005B8300; the delay slot nop stays); t0 = R3 lock-on bit, a0 is at 20(sp).
BLK: block held ([Caim+0x66C] & 0x80) while Caim is in the jump state ([+0x2DC] == 5): the yaw ([+0x44] and [+0x584]) at the first such frame is kept (words HY / HY2, flag HF 005BED40..48); then ISOJW is called every frame (FACE: the locked enemy
with the R3 lock-on, else the nearest one); when there is no enemy (005A0900 == 0) the kept yaw is written back (+0x44 / +0x584, +0x570 |= 2 = rebuild the matrix), so Caim keeps facing the block's forward direction. Block released or not in the jump
state: HF = 0, then the old rule (R3 lock-on on: 005B825C, else skip 005B8284)."""
import sys
sys.path.insert(0, r'C:\Users\shade\OneDrive\Documents\PCSX2\roms\drakengard_mod\src\lib')
from mipsasm import Asm
BLK = 0x5B8300
HF, HY, HY2 = -0x12C0, -0x12BC, -0x12B8      # 005BED40 / 44 / 48 (lui 0x5C)
def build():
    a = Asm(BLK)
    a.emit('lw', 'a0', 20, 'sp'); a.emit('lui', 't1', 0x3A); a.emit('ori', 't1', 't1', 0xC5E0); a.emit('bne', 'a0', 't1', 'NOBLK'); a.emit('nop')      # only Caim (an ally keeps the old rule)
    a.emit('lw', 't1', 1644, 'a0'); a.emit('andi', 't1', 't1', 0x80); a.emit('beq', 't1', 'zero', 'NOBLK'); a.emit('nop')
    a.emit('lw', 't1', 732, 'a0'); a.emit('xori', 't1', 't1', 5); a.emit('bne', 't1', 'zero', 'NOBLK'); a.emit('nop')
    a.emit('lui', 't2', 0x5C); a.emit('lw', 't3', HF, 't2'); a.emit('bne', 't3', 'zero', 'HAVE'); a.emit('nop')
    a.emit('lw', 't4', 0x44, 'a0'); a.emit('sw', 't4', HY, 't2'); a.emit('lw', 't4', 0x584, 'a0'); a.emit('sw', 't4', HY2, 't2'); a.emit('ori', 't3', 'zero', 1); a.emit('sw', 't3', HF, 't2')
    a.label('HAVE')
    a.emit('jal', 0x5BAE40); a.emit('nop')
    a.emit('lui', 't2', 0x5A); a.emit('lw', 't3', 0x900, 't2'); a.emit('beq', 'zero', 'zero', 'DONE'); a.emit('nop')     # no enemy: nothing (the kept yaw write-back below is disabled: it did not work well)
    a.emit('lw', 'a0', 20, 'sp'); a.emit('lui', 't2', 0x5C); a.emit('lw', 't4', HY, 't2'); a.emit('sw', 't4', 0x44, 'a0'); a.emit('lw', 't4', HY2, 't2'); a.emit('sw', 't4', 0x584, 'a0')
    a.emit('lw', 't4', 0x570, 'a0'); a.emit('ori', 't4', 't4', 2); a.emit('sw', 't4', 0x570, 'a0')
    a.label('DONE'); a.emit('j', 0x5B8284); a.emit('nop')
    a.label('NOBLK'); a.emit('lui', 't2', 0x5C); a.emit('sw', 'zero', HF, 't2'); a.emit('bne', 't0', 'zero', 'ORIG'); a.emit('nop')
    a.emit('j', 0x5B8284); a.emit('nop')
    a.label('ORIG'); a.emit('j', 0x5B825C); a.emit('nop')
    return a
def patches():
    w = build().assemble()
    return [(BLK + 4 * i, x) for i, x in enumerate(w)] + [(0x5B8254, 0x08000000 | (BLK >> 2))]
if __name__ == '__main__':
    for ad, x in patches(): print('patch=1,EE,%08X,word,%08X' % (ad, x))
