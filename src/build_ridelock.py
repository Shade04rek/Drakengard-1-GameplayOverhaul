"""R3 lock-on toggle skipped while Caim rides Angelus on a ground stage (R3 brakes her there, build_aerialboost.py).
Hook 00321CDC (xori t4,t4,1 in LK, the lock-on toggle) -> j LKR (delay slot 00321CE0 is harmless, run again on return). LKR: Angelus actor 003ACF40 == 5, 003AD2C4 == 2, aerial marker 00340DFC == 0 -> no toggle."""
import sys
sys.path.insert(0, r'C:\Users\shade\OneDrive\Documents\PCSX2\roms\drakengard_mod\src\lib')
from mipsasm import Asm
LKR = 0x5BD880
def build():
    a = Asm(LKR)
    a.emit('lui', 't5', 0x3B); a.emit('lw', 't6', -0x30C0, 't5'); a.emit('addiu', 't6', 't6', -5); a.emit('bne', 't6', 'zero', 'TOG'); a.emit('nop')
    a.emit('lw', 't6', -0x2D3C, 't5'); a.emit('addiu', 't6', 't6', -2); a.emit('bne', 't6', 'zero', 'TOG'); a.emit('nop')
    a.emit('lui', 't5', 0x34); a.emit('lw', 't6', 0xDFC, 't5'); a.emit('bne', 't6', 'zero', 'TOG'); a.emit('nop')
    a.emit('j', 0x321CE0); a.emit('nop')
    a.label('TOG'); a.emit('xori', 't4', 't4', 1); a.emit('j', 0x321CE0); a.emit('nop')
    return a
def patches():
    w = build().assemble()
    return [(LKR + 4 * i, x) for i, x in enumerate(w)] + [(0x321CDC, 0x08000000 | (LKR >> 2))]
if __name__ == '__main__':
    for ad, w in patches(): print('patch=1,EE,%08X,word,%08X' % (ad, w))
