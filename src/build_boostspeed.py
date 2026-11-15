"""Ridden ground Angelus: L2 boost speed. The ground ride function FUN_001C3EBC (decompiled in tools/decomp_1c3f04.txt) sets, while the boost action (0x100) is held, the target multiplier
(dragon +0x3DEC) = the float at gp-0x626c (00567C84 = 1.8) with the ease rate +0x3DF0 = gp-0x6268 (0.08); a fresh press first jumps the current multiplier +0x3DE8 to 4.5 (gp-0x6270) which then eases to the target.
Hook 001C4D38 (lwc1 f0,-25196(gp)) -> j BST (delay slot 001C4D3C lwc1 f1 harmless): f0 = the multiplier, brake mode (word 005BEE0C != 0): BRAKE_MULT (1.7); FAST MODE: 2.0 at her lowest height (terrain
height + 90, the lower height clamp) rising linearly to 3.0 at her highest height (y = TOP, the stage bounding box minimum). The terrain height V (the float the height clamp compares with, [sp+0x44] at 0017FD6C
of the position caller) is stored by VH (005BD300, hook 0017FD6C -> j VH, the delay slot 0017FD70 is the lui of the lower clamp constant) into word VW (005BEDF0). f2 / f3 are saved in words 005BEDF4 / 005BEDF8."""
import sys, struct
sys.path.insert(0, r'C:\Users\shade\OneDrive\Documents\PCSX2\roms\drakengard_mod\src\lib')
from mipsasm import Asm
BST = 0x5BD400
VH = 0x5BD300
LOW_MARGIN = 90.0      # lowest height above the terrain (0017FD70)
TOP = -515.0           # highest y (the bounding box y minimum, 003AD164 / 003B0C44)
MIN_MULT, MAX_MULT = 2.0, 3.0
BRAKE_MULT = 1.7   # brake mode boost (vanilla 1.8)
VW, S2, S3 = -0x1210, -0x120C, -0x1208      # 005BEDF0, 005BEDF4, 005BEDF8 (lui 0x5C)
def fb(x): return struct.unpack('<I', struct.pack('<f', x))[0]
def lif(a, f, x):
    b = fb(x); a.emit('lui', 'at', b >> 16)
    if b & 0xFFFF: a.emit('ori', 'at', 'at', b & 0xFFFF)
    a.emit('mtc1', 'at', f)
def build():
    a = Asm(BST)
    a.emit('lwc1', 'f0', -25196, 'gp')
    a.emit('lui', 't8', 0x5C); a.emit('lw', 't9', -0x11F4, 't8'); a.emit('bne', 't9', 'zero', 'BRK'); a.emit('nop')        # brake mode (word 005BEE0C): BRAKE_MULT
    a.emit('swc1', 'f2', S2, 't8'); a.emit('swc1', 'f3', S3, 't8')
    a.emit('lwc1', 'f0', VW, 't8'); a.emit('lui', 't9', 0x42); a.emit('lwc1', 'f1', -0x3F6C, 't9')                       # f0 = terrain height, f1 = her y (0041C094)
    lif(a, 'f2', LOW_MARGIN); a.emit('sub.s', 'f0', 'f0', 'f2')                                                          # f0 = lowest y
    a.emit('sub.s', 'f1', 'f0', 'f1')                                                                                    # f1 = lowest y - y (>= 0 when she is above the floor)
    lif(a, 'f2', -TOP); a.emit('add.s', 'f0', 'f0', 'f2')                                                                # f0 = range
    lif(a, 'f3', 1.0); a.emit('c.olt.s', 'f0', 'f3'); a.emit('bc1f', 'RGO'); a.emit('nop'); a.emit('mtc1', 'zero', 'f1'); a.emit('mov.s', 'f0', 'f3')
    a.label('RGO')
    a.emit('div.s', 'f1', 'f1', 'f0')
    a.emit('mtc1', 'zero', 'f2'); a.emit('c.olt.s', 'f1', 'f2'); a.emit('bc1f', 'C1'); a.emit('nop'); a.emit('mov.s', 'f1', 'f2')
    a.label('C1')
    a.emit('c.olt.s', 'f3', 'f1'); a.emit('bc1f', 'C2'); a.emit('nop'); a.emit('mov.s', 'f1', 'f3')
    a.label('C2')
    lif(a, 'f2', MAX_MULT - MIN_MULT); a.emit('mul.s', 'f1', 'f1', 'f2'); lif(a, 'f2', MIN_MULT); a.emit('add.s', 'f0', 'f1', 'f2')
    a.emit('lui', 't8', 0x5C); a.emit('lwc1', 'f2', S2, 't8'); a.emit('lwc1', 'f3', S3, 't8')
    a.emit('beq', 'zero', 'zero', 'OUT'); a.emit('nop')
    a.label('BRK')
    lif(a, 'f0', BRAKE_MULT)
    a.label('OUT'); a.emit('j', 0x1C4D3C); a.emit('nop')
    return a
def vh():
    a = Asm(VH)
    a.emit('lwc1', 'f1', 0x44, 'sp'); a.emit('lui', 'v0', 0x5C); a.emit('swc1', 'f1', VW, 'v0')
    a.emit('j', 0x17FD74); a.emit('nop')
    return a
def patches():
    p = [(BST + 4 * i, x) for i, x in enumerate(build().assemble())] + [(0x1C4D38, 0x08000000 | (BST >> 2))]
    return p + [(VH + 4 * i, x) for i, x in enumerate(vh().assemble())] + [(0x17FD6C, 0x08000000 | (VH >> 2))]
if __name__ == '__main__':
    for ad, w in patches(): print('patch=1,EE,%08X,word,%08X' % (ad, w))
