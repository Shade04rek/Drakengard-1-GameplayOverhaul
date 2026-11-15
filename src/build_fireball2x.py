"""Ridden ground Angelus: faster fireball. The fireball is an effect object (update FUN_0018D36C: every frame position (+0x80) += velocity (+0xC0); found with three consecutive-frame states: the velocity,
e.g. (-7.26, -0.55, 3.97) = 8.3 per frame, is constant and set when the object is created by FUN_0017EA0C -> 0018C960; start point +0xD0 = the mouth). The epilogue of FUN_0017EA0C (0017EBE4 ld s0,144(sp), also the
target of its 'no object' branch, s3 = the object or 0) is hooked: FB (005BC780): for a ground stage (marker 00340DFC == 0) with Caim riding (003ACC94 == 2) and s3 != 0 the velocity at s3 + 0xC0 is multiplied by MULT.
The delay slot 0017EBE8 ld s1 is harmless. Returns to 0017EBEC. The reticle (RIDE speed constant, build_ride.py: lui r25,4109 / ori 1EB8 = 8.57 at 005B7108) is scaled by the same factor."""
import sys, struct
sys.path.insert(0, r'C:\Users\shade\OneDrive\Documents\PCSX2\roms\drakengard_mod\src\lib')
from mipsasm import Asm
FB = 0x5BC780
MULT = 2.0
def fb(x): return struct.unpack('<I', struct.pack('<f', x))[0]
def build():
    a = Asm(FB)
    a.emit('beq', 's3', 'zero', 'OUT'); a.emit('nop')
    a.emit('lui', 't8', 0x3B); a.emit('lw', 't9', -0x336C, 't8'); a.emit('addiu', 't9', 't9', -2); a.emit('bne', 't9', 'zero', 'OUT'); a.emit('nop')
    a.emit('lui', 't8', 0x34); a.emit('lw', 't9', 0xDFC, 't8'); a.emit('bne', 't9', 'zero', 'OUT'); a.emit('nop')
    a.emit('lwc1', 'f0', 0xC0, 's3'); a.emit('lwc1', 'f1', 0xC4, 's3'); a.emit('lwc1', 'f2', 0xC8, 's3')
    b = fb(MULT); a.emit('lui', 'at', b >> 16)
    if b & 0xFFFF: a.emit('ori', 'at', 'at', b & 0xFFFF)
    a.emit('mtc1', 'at', 'f3')
    a.emit('mul.s', 'f0', 'f0', 'f3'); a.emit('mul.s', 'f1', 'f1', 'f3'); a.emit('mul.s', 'f2', 'f2', 'f3')
    a.emit('swc1', 'f0', 0xC0, 's3'); a.emit('swc1', 'f1', 0xC4, 's3'); a.emit('swc1', 'f2', 0xC8, 's3')
    a.label('OUT'); a.emit('ld', 's0', 144, 'sp'); a.emit('j', 0x17EBEC); a.emit('nop')
    return a
def patches():
    w = build().assemble()
    p = [(FB + 4 * i, x) for i, x in enumerate(w)] + [(0x17EBE4, 0x08000000 | (FB >> 2))]
    v = fb(8.57 * MULT)        # reticle speed
    p += [(0x5B7108, 0x3C190000 | (v >> 16)), (0x5B710C, 0x37390000 | (v & 0xFFFF))]
    return p
if __name__ == '__main__':
    for ad, w in patches(): print('patch=1,EE,%08X,word,%08X' % (ad, w))
