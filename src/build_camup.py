"""Ground ridden Angelus: the camera sits higher (same tilt). The ridden Angelus camera (object 003ADC80, writes found with a write breakpoint on 003ADD04: pc 00198894, ra 00198870)
stores the eye position in FUN_0019880x: 00198884 addiu v0,s4,128 / 00198888 lwc1 f0,4(sp) (eye y) / 0019888C lwc1 f1,8(sp) / 00198890 swc1 f2,0(v0) / 00198894 swc1 f0,4(v0).
The orientation rows (cam+0x30..) are built separately (210B74), so moving only the eye keeps the view tilt. Hook 00198888 -> j CAMY (the delay slot 0019888C lwc1 f1 runs); CAMY loads f0 = eye y
plus the smoothed offset SMT (word 005BEDC8): UP units up (y is negative up) while Caim rides Angelus on a ground stage (Caim 003ACC94 == 2, aerial marker 00340DFC == 0), else 0; SMT eases
to that by EASE of the gap per frame (smooth mount / dismount). Saves f3..f5 in 005BEDCC.., returns to 00198890."""
import sys, struct
sys.path.insert(0, r'C:\Users\shade\OneDrive\Documents\PCSX2\roms\drakengard_mod\src\lib')
from mipsasm import Asm
CAMY = 0x5BD900
UP = 50.0
EASE = 0.1
SMT = -0x1238          # 005BEDC8 (lui 0x5C)
SV = -0x1234           # 005BEDCC .. 005BEDD4 saved f3, f4, f5
def fb(x): return struct.unpack('<I', struct.pack('<f', x))[0]
def build():
    a = Asm(CAMY)
    a.emit('lwc1', 'f0', 4, 'sp')
    a.emit('lui', 'a0', 0x3B); a.emit('lw', 'a1', -0x336C, 'a0'); a.emit('addiu', 'a1', 'a1', -2); a.emit('bne', 'a1', 'zero', 'OFF'); a.emit('nop')
    a.emit('lui', 'a1', 0x34); a.emit('lw', 'a1', 0xDFC, 'a1'); a.emit('bne', 'a1', 'zero', 'OFF'); a.emit('nop')
    a.emit('lui', 'a0', 0x5C)
    a.emit('swc1', 'f3', SV, 'a0'); a.emit('swc1', 'f4', SV + 4, 'a0'); a.emit('swc1', 'f5', SV + 8, 'a0')
    a.emit('lui', 'at', fb(-UP) >> 16); a.emit('mtc1', 'at', 'f3'); a.emit('beq', 'zero', 'zero', 'EAS'); a.emit('nop')
    a.label('OFF')
    a.emit('lui', 'a0', 0x5C)
    a.emit('swc1', 'f3', SV, 'a0'); a.emit('swc1', 'f4', SV + 4, 'a0'); a.emit('swc1', 'f5', SV + 8, 'a0')
    a.emit('mtc1', 'zero', 'f3')
    a.label('EAS')
    a.emit('lwc1', 'f4', SMT, 'a0'); a.emit('sub.s', 'f3', 'f3', 'f4')
    k = fb(EASE); a.emit('lui', 'at', k >> 16); a.emit('ori', 'at', 'at', k & 0xFFFF); a.emit('mtc1', 'at', 'f5')
    a.emit('mul.s', 'f3', 'f3', 'f5'); a.emit('add.s', 'f4', 'f4', 'f3'); a.emit('swc1', 'f4', SMT, 'a0'); a.emit('add.s', 'f0', 'f0', 'f4')
    a.emit('lwc1', 'f3', SV, 'a0'); a.emit('lwc1', 'f4', SV + 4, 'a0'); a.emit('lwc1', 'f5', SV + 8, 'a0')
    a.emit('j', 0x198890); a.emit('nop')
    return a
def patches():
    w = build().assemble()
    assert CAMY + 4 * len(w) <= 0x5BDA00
    return [(CAMY + 4 * i, x) for i, x in enumerate(w)] + [(0x198888, 0x08000000 | (CAMY >> 2))]
if __name__ == '__main__':
    for ad, w in patches(): print('patch=1,EE,%08X,word,%08X' % (ad, w))
