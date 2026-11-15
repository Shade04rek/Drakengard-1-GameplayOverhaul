"""Caim on foot: the camera follows his jumps, smoothly. The main camera (object 003ADAC0) eases its anchor ([cam+0x110..0x118]) towards the target position quad that [cam+0x100] points to (+0x50): 00196694 / 00196698 copy
it to sp+0xC0 (x), 0xC4 (y), 0xC8 (z). That target is Caim's position projected on the ground (y stays 0 in the air: states with Caim at y = -21.9 had the anchor and the eye at the same height as on the ground), so the camera never rose
with a jump. Hook 001966AC (lwc1 f0,196(sp): the target y) -> j CAMF (the delay slot 001966B0 lwc1 f1,200(sp) runs, so f1 is not free): CAMF takes f0 = SMY, a smoothed copy of Caim's real y ([Caim+0x84] = 003AC664): SMY eases to
Caim's y by K of the gap per frame (a gap of more than 100 snaps at once: stage start, teleport). While Caim rides Angelus (003ACC94 == 2) f0 stays the original target y and SMY follows it. The anchor follows the target at factor 1.0 (rigid follow
section). Word SMY = 005BEE00. Returns to 001966B4. Walking on the ground: SMY tracks the ground height with a short lag."""
import sys, struct
sys.path.insert(0, r'C:\Users\shade\OneDrive\Documents\PCSX2\roms\drakengard_mod\src\lib')
from mipsasm import Asm
CAMF = 0x5BE560
K = 0.15
SNAP = 100.0
DJ_UP = 15.0           # extra camera lift (units, y is negative up) while Caim is in the air after the jump-button double jump (the double jump itself barely rises above the first jump)
JDF = -8428            # 005BDF14 (lui 0x5C): the double jump flag of the JD cave
SMY = -0x1200           # 005BEE00 (lui 0x5C)
def fb(x): return struct.unpack('<I', struct.pack('<f', x))[0]
def lif(a, f, x):
    b = fb(x); a.emit('lui', 'at', b >> 16)
    if b & 0xFFFF: a.emit('ori', 'at', 'at', b & 0xFFFF)
    a.emit('mtc1', 'at', f)
def build():
    a = Asm(CAMF)
    a.emit('lui', 't0', 0x3B); a.emit('lw', 't1', -0x336C, 't0'); a.emit('addiu', 't1', 't1', -2); a.emit('lui', 't2', 0x5C)
    a.emit('lwc1', 'f0', 196, 'sp')
    a.emit('beq', 't1', 'zero', 'STO'); a.emit('nop')
    a.emit('lwc1', 'f6', -14748, 't0')
    # double jump lift: in the air (y above the ground height [Caim+0x650] = 003ACC30) and the JD flag set: the target is DJ_UP higher
    a.emit('lwc1', 'f11', -13264, 't0'); a.emit('c.olt.s', 'f6', 'f11'); a.emit('bc1f', 'NOX'); a.emit('nop')
    a.emit('lui', 't3', 0x5C); a.emit('lw', 't3', JDF, 't3'); a.emit('beq', 't3', 'zero', 'NOX'); a.emit('nop')
    lif(a, 'f12', -DJ_UP); a.emit('add.s', 'f6', 'f6', 'f12')
    a.label('NOX'); a.emit('lwc1', 'f7', SMY, 't2'); a.emit('sub.s', 'f8', 'f6', 'f7'); a.emit('abs.s', 'f9', 'f8')
    lif(a, 'f10', SNAP); a.emit('c.olt.s', 'f10', 'f9'); a.emit('bc1t', 'DONE'); a.emit('nop')
    lif(a, 'f10', K); a.emit('mul.s', 'f8', 'f8', 'f10'); a.emit('add.s', 'f6', 'f7', 'f8')
    a.label('DONE'); a.emit('mov.s', 'f0', 'f6')
    a.label('STO'); a.emit('swc1', 'f0', SMY, 't2'); a.emit('j', 0x1966B4); a.emit('nop')
    return a
def patches():
    w = build().assemble()
    return [(CAMF + 4 * i, x) for i, x in enumerate(w)] + [(0x1966AC, 0x08000000 | (CAMF >> 2))]
if __name__ == '__main__':
    for ad, x in patches(): print('patch=1,EE,%08X,word,%08X' % (ad, x))
