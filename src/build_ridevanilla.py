"""Enemy projectile speed is vanilla while Caim rides Angelus (ground: Angelus actor 003ACF20 +0x20 == 5 and +0x3A4 == 2; aerial stages: marker 00340DFC != 0).
ARROW (005BAE80, hook 00193F20): the parabola shot advances f1 += f0 once (vanilla) and once more (2x) when not riding.
BALL (005BDE80, hook 0018FE70): the magic ball step f0 is doubled only when not riding. t0..t3 are free in both places."""
import sys
sys.path.insert(0, r'C:\Users\shade\OneDrive\Documents\PCSX2\roms\drakengard_mod\src\lib')
from mipsasm import Asm
def chk(a):
    a.emit('lui', 't0', 0x3B); a.emit('lw', 't1', -0x30C0, 't0'); a.emit('addiu', 't1', 't1', -5)
    a.emit('lw', 't2', -0x2D3C, 't0'); a.emit('addiu', 't2', 't2', -2); a.emit('or', 't1', 't1', 't2')
    a.emit('lui', 't3', 0x34); a.emit('lw', 't3', 0xDFC, 't3')
    a.emit('bne', 't3', 'zero', 'VAN'); a.emit('nop'); a.emit('beq', 't1', 'zero', 'VAN'); a.emit('nop')
def arrow():
    a = Asm(0x5BAE80); a.emit('add.s', 'f1', 'f1', 'f0'); chk(a)
    a.emit('add.s', 'f1', 'f1', 'f0')
    a.label('VAN'); a.emit('j', 0x193F28); a.emit('nop'); return a.assemble()
def ball():
    a = Asm(0x5BDE80); a.emit('lwc1', 'f5', 0, 'sp'); chk(a)
    a.emit('lui', 'at', 0x4000); a.emit('mtc1', 'at', 'f6'); a.emit('mul.s', 'f0', 'f0', 'f6')
    a.label('VAN'); a.emit('j', 0x18FE78); a.emit('nop'); return a.assemble()
def patches():
    return [(0x5BAE80 + 4 * i, x) for i, x in enumerate(arrow())] + [(0x5BDE80 + 4 * i, x) for i, x in enumerate(ball())]
if __name__ == '__main__':
    for ad, x in patches(): print('patch=1,EE,%08X,word,%08X' % (ad, x))
