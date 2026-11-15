"""Aerial: the Cross hold-to-lock only works while gliding, and L3 (glide) never targets by itself.
Hooks in the per-frame aerial update (dragon s0 = 0041BFC0, input struct s1; held-action word s1+0xC, bit 0x800000 = the Cross
action = mapping byte 005747BC; dragon +0x3D54 = glide counter, +0x3CD0 = target):
  A (jal 001C1BCC at 001C073C): not gliding -> the Cross action bit is removed from the held-action word (and remembered in CRX).
  B (jal 001BEDEC at 001C076C): gliding without a target at the start of the glide (GST): the target is dropped every frame unless
    the Cross action or the target-switch button (mapping entry 005747B0, R3) is held; not gliding with Cross held and no target
    before this frame: the target is dropped too."""
import sys
sys.path.insert(0, r'C:\Users\shade\OneDrive\Documents\PCSX2\roms\drakengard_mod\src\lib')
from mipsasm import Asm
A = 0x5BD900
B = 0x5BD980
CRX, GST, PREV = -0x400C, -0x4008, -0x4004     # 005BBFF4 / 005BBFF8 / 005BBFFC (lui 0x5C)
def build_a():
    a = Asm(A)
    a.emit('lui', 't7', 0x5C)
    a.emit('lw', 't0', 0x3D54, 's0'); a.emit('slt', 't1', 'zero', 't0')
    a.emit('beq', 't1', 'zero', 'NG'); a.emit('nop')
    a.emit('sw', 'zero', CRX, 't7'); a.emit('j', 0x1C1BCC); a.emit('nop')
    a.label('NG')
    a.emit('lw', 't3', 0xC, 's1'); a.emit('lui', 't4', 0x80); a.emit('and', 't5', 't3', 't4'); a.emit('sltu', 't5', 'zero', 't5')
    a.emit('sw', 't5', CRX, 't7')
    a.emit('nor', 't4', 't4', 'zero'); a.emit('and', 't3', 't3', 't4'); a.emit('sw', 't3', 0xC, 's1')
    a.emit('j', 0x1C1BCC); a.emit('nop')
    return a
def r3_held(a, yes):
    a.emit('lui', 't4', 0x57); a.emit('lhu', 't4', 0x47B0, 't4'); a.emit('lui', 't5', 0x34); a.emit('lw', 't5', 0x2898, 't5')
    a.emit('and', 't4', 't4', 't5'); a.emit('bne', 't4', 'zero', yes); a.emit('nop')
def drop(a):
    a.emit('sw', 'zero', 0x3CC8, 's0'); a.emit('sw', 'zero', 0x3CD0, 's0'); a.emit('sw', 'zero', 0x3CD8, 's0')
def build_b():
    a = Asm(B)
    a.emit('lui', 't7', 0x5C)
    a.emit('lw', 't0', 0x3D54, 's0'); a.emit('slt', 't1', 'zero', 't0')
    a.emit('beq', 't1', 'zero', 'BNG'); a.emit('nop')
    a.emit('lw', 't2', PREV, 't7'); a.emit('bne', 't2', 'zero', 'B1'); a.emit('nop')
    a.emit('lui', 't3', 0x34); a.emit('lw', 't3', 0x0DE0, 't3'); a.emit('sltiu', 't3', 't3', 1); a.emit('sw', 't3', GST, 't7')
    a.label('B1')
    a.emit('sw', 't1', PREV, 't7')
    a.emit('lw', 't2', GST, 't7'); a.emit('beq', 't2', 'zero', 'BTAIL'); a.emit('nop')
    a.emit('lw', 't3', 0xC, 's1'); a.emit('lui', 't4', 0x80); a.emit('and', 't3', 't3', 't4'); a.emit('bne', 't3', 'zero', 'ALLOW'); a.emit('nop')
    r3_held(a, 'ALLOW')
    drop(a); a.emit('j', 'BTAIL'); a.emit('nop')
    a.label('ALLOW')
    a.emit('sw', 'zero', GST, 't7'); a.emit('j', 'BTAIL'); a.emit('nop')
    a.label('BNG')
    a.emit('sw', 'zero', PREV, 't7'); a.emit('sw', 'zero', GST, 't7')
    a.emit('lw', 't2', CRX, 't7'); a.emit('beq', 't2', 'zero', 'BTAIL'); a.emit('nop')
    a.emit('lui', 't3', 0x34); a.emit('lw', 't3', 0x0DE0, 't3'); a.emit('bne', 't3', 'zero', 'BTAIL'); a.emit('nop')
    r3_held(a, 'BTAIL')
    drop(a)
    a.label('BTAIL')
    a.emit('j', 0x1BEDEC); a.emit('nop')
    return a
def patches():
    out = [(A + 4 * i, w) for i, w in enumerate(build_a().assemble())] + [(B + 4 * i, w) for i, w in enumerate(build_b().assemble())]
    out += [(0x1C073C, 0x0C000000 | (A >> 2)), (0x1C076C, 0x0C000000 | (B >> 2))]
    return out
if __name__ == '__main__':
    for ad, w in patches(): print('patch=1,EE,%08X,word,%08X' % (ad, w))
