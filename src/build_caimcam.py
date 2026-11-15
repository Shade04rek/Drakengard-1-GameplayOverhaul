"""Caim on foot (ground stages): the camera eye sits higher AND follows his jumps. The live camera (object 003AD4F0 / main camera 003ADAC0) gets its eye from FUN_00196DB4; its last part stores the eye (sp+0..8) with
001974C0 lwc1 f1,0(sp) / 001974C4 lwc1 f2,4(sp) (eye y) / 001974C8 lwc1 f3,8(sp) / 001974D0.. swc1 into the camera (s0). The view orientation rows are built separately, so moving only the eye height keeps the tilt (same method as
the ridden Angelus camera, build_camup.py). The look-at anchor can not be used for the jump follow: the anchor is overwritten with the ground projected target (1967D0 sd v0,272(s1)) and its y offset stayed at -8 while Caim jumped.
Hook 001974C4 -> j CAME (the delay slot 001974C8 lwc1 f3 runs): CAME loads f2 = eye y plus the smoothed offset SMT2 (word 005BEE08), whose target is, while Caim is not riding Angelus (003ACC94 != 2) on a ground stage (00340DFC == 0):
-UP + (Caim y [003AC664] - ground height [003ACC30], negative in the air) (+ -DJ_UP in the air after the jump-button double jump, JD flag 005BDF14); else 0. SMT2 eases to its target by EASE of the gap per frame.
Returns to 001974CC."""
import sys, struct
sys.path.insert(0, r'C:\Users\shade\OneDrive\Documents\PCSX2\roms\drakengard_mod\src\lib')
from mipsasm import Asm
CAME = 0x5BE560
UP = 2.5
DJ_UP = 0.0
EASE = 0.1
SMT2 = -0x11F8          # 005BEE08 (lui 0x5C)
JDF = -8428             # 005BDF14 (lui 0x5C)
def fb(x): return struct.unpack('<I', struct.pack('<f', x))[0]
def lif(a, f, x):
    b = fb(x); a.emit('lui', 'at', b >> 16)
    if b & 0xFFFF: a.emit('ori', 'at', 'at', b & 0xFFFF)
    a.emit('mtc1', 'at', f)
def build():
    a = Asm(CAME)
    a.emit('lwc1', 'f2', 4, 'sp')
    a.emit('lui', 't0', 0x3B); a.emit('lw', 't1', -0x336C, 't0'); a.emit('addiu', 't1', 't1', -2); a.emit('beq', 't1', 'zero', 'OFF'); a.emit('lui', 't1', 0x34)
    a.emit('lw', 't1', 0xDFC, 't1'); a.emit('bne', 't1', 'zero', 'OFF'); a.emit('lwc1', 'f6', -14748, 't0')
    a.emit('lwc1', 'f7', -13264, 't0'); a.emit('sub.s', 'f6', 'f6', 'f7')              # jump height (negative in the air)
    lif(a, 'f4', -UP); a.emit('add.s', 'f4', 'f4', 'f6')
    a.emit('mtc1', 'zero', 'f8'); a.emit('c.olt.s', 'f6', 'f8'); a.emit('bc1f', 'EAS'); a.emit('nop')                        # on the ground: no double jump lift
    a.emit('lui', 't1', 0x5C); a.emit('lw', 't1', JDF, 't1'); a.emit('beq', 't1', 'zero', 'EAS'); a.emit('nop')
    lif(a, 'f9', -DJ_UP); a.emit('add.s', 'f4', 'f4', 'f9'); a.emit('beq', 'zero', 'zero', 'EAS'); a.emit('nop')
    a.label('OFF'); a.emit('mtc1', 'zero', 'f4')
    a.label('EAS')
    a.emit('lui', 't2', 0x5C); a.emit('lwc1', 'f5', SMT2, 't2'); a.emit('sub.s', 'f4', 'f4', 'f5')
    lif(a, 'f6', EASE); a.emit('mul.s', 'f4', 'f4', 'f6'); a.emit('add.s', 'f5', 'f5', 'f4'); a.emit('swc1', 'f5', SMT2, 't2'); a.emit('add.s', 'f2', 'f2', 'f5')
    a.emit('j', 0x1974CC); a.emit('nop')
    return a
def patches():
    w = build().assemble()
    return [(CAME + 4 * i, x) for i, x in enumerate(w)] + [(0x1974C4, 0x08000000 | (CAME >> 2))]
if __name__ == '__main__':
    for ad, x in patches(): print('patch=1,EE,%08X,word,%08X' % (ad, x))
