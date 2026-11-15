"""Ridden ground Angelus: climb and descend 3x as far. Her altitude changes only by the vertical component of the movement vector (+0xF4; the forward axis follows the aim pitch; the ride code halves the vertical part
again at 001C5118 and the whole vector at 001C0AC4), so aiming up / down moved her only a little; there is no terrain follow or altitude clamp on ground stages that touches +0xF4 (write breakpoint stops: 001C4128,
001C51B4, 001C52CC, 001C0AC4, the mover 001B7824). VUP (005BCF80; GMOV now ends with j VUP instead of j STRAFE, after the output vector at v1 is stored) multiplies y (4(v1)) by VMULT and continues with STRAFE."""
import sys, struct
sys.path.insert(0, r'C:\Users\shade\OneDrive\Documents\PCSX2\roms\drakengard_mod\src\lib'); sys.path.insert(0, r'C:\Users\shade\OneDrive\Documents\PCSX2\roms\drakengard_mod\src')
from mipsasm import Asm
import build_aerialboost as AB
VMULT = 3.0
def fb(x): return struct.unpack('<I', struct.pack('<f', x))[0]
def build():
    a = Asm(AB.VUP)
    a.emit('lwc1', 'f0', 4, 'v1')
    b = fb(VMULT); a.emit('lui', 'at', b >> 16)
    if b & 0xFFFF: a.emit('ori', 'at', 'at', b & 0xFFFF)
    a.emit('mtc1', 'at', 'f1'); a.emit('mul.s', 'f0', 'f0', 'f1'); a.emit('swc1', 'f0', 4, 'v1')
    a.emit('j', AB.STRAFE); a.emit('nop')
    return a
def patches():
    w = build().assemble()
    return [(AB.VUP + 4 * i, x) for i, x in enumerate(w)]
if __name__ == '__main__':
    for ad, x in patches(): print('patch=1,EE,%08X,word,%08X' % (ad, x))
