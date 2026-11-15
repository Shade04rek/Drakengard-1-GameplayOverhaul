"""Ridden ground Angelus: the dodge goes along the stick angle (mirrored to the button side), like Caim's rolls (cave DRT at 005BCC00, entered from GMOV in build_aerialboost.py).
While the dragon dodge timer (+0x3D7C) runs, the movement vector n at v1 (+0xF0) holds the sideways dodge movement s = n . right (right axis +0x0 / +0x8)
besides the cruise along her heading. It becomes n' = n - s right + |s| (ux right + uf forward) with (ux, uf) the stick direction (raw pad bytes 00342866 x /
00342867 y, 0x80 centre, up = smaller y) in her frame: inside the 90 degree cones straight forward and straight back (|x| < |forward|) it is pushed out to the
45 degree line on the stick's side (x = 0 counts as right, forward component keeps its sign), outside them it is the stick direction. Stick at rest
(|x| + |y| < 16): the vanilla sideways dodge of the button. Each dodge button keeps its own side (the sign of s): a stick held to the other side is mirrored (ux = |ux| on the button side). Same distance as the vanilla dodge."""
import sys, struct
sys.path.insert(0, r'C:\Users\shade\OneDrive\Documents\PCSX2\roms\drakengard_mod\src\lib')
sys.path.insert(0, r'C:\Users\shade\OneDrive\Documents\PCSX2\roms\drakengard_mod\src')
from mipsasm import Asm
import build_aerialboost as AB
DRT = AB.DRT
DEAD = 16
def build():
    specs, end = AB.layout()
    cont = AB.LAB['GMOV']['CONT']
    a = Asm(DRT)
    a.emit('lw', 't1', 0x3D7C, 's0'); a.emit('beq', 't1', 'zero', 'RET'); a.emit('nop')
    a.emit('lwc1', 'f0', 0, 'v1'); a.emit('lwc1', 'f2', 8, 'v1'); a.emit('lwc1', 'f8', 0, 's0'); a.emit('lwc1', 'f9', 8, 's0')
    a.emit('mul.s', 'f1', 'f0', 'f8'); a.emit('mul.s', 'f10', 'f2', 'f9'); a.emit('add.s', 'f1', 'f1', 'f10')                  # s = n . right
    a.emit('abs.s', 'f3', 'f1'); a.emit('lui', 'at', 0x3F80); a.emit('mtc1', 'at', 'f10'); a.emit('c.olt.s', 'f3', 'f10'); a.emit('bc1t', 'RET'); a.emit('nop')   # |s| < 1: nothing
    a.emit('lw', 't9', AB.TGB, 't3'); a.emit('beq', 't9', 'zero', 'LST'); a.emit('nop'); a.emit('lbu', 't4', 0x2864, 't0'); a.emit('lbu', 't5', 0x2865, 't0'); a.emit('beq', 'zero', 'zero', 'LSD'); a.emit('nop')   # brake mode: the stick of the strafe
    a.label('LST'); a.emit('lbu', 't4', 0x2866, 't0'); a.emit('lbu', 't5', 0x2867, 't0')
    a.label('LSD'); a.emit('addiu', 't4', 't4', -128); a.emit('addiu', 't5', 't5', -128); a.emit('subu', 't5', 'zero', 't5')   # x right, y forward
    a.emit('sra', 't8', 't4', 31); a.emit('xor', 't9', 't4', 't8'); a.emit('subu', 't9', 't9', 't8')                              # |x|
    a.emit('sra', 't8', 't5', 31); a.emit('xor', 'at', 't5', 't8'); a.emit('subu', 'at', 'at', 't8')                              # |y|
    a.emit('addu', 't8', 't9', 'at'); a.emit('slti', 't8', 't8', DEAD); a.emit('bne', 't8', 'zero', 'RET'); a.emit('nop')        # stick at rest: vanilla
    a.emit('slt', 't8', 't9', 'at')                                                                                               # |x| < |forward|: inside the cones
    a.emit('mtc1', 't4', 'f4'); a.emit('cvt.s.w', 'f4', 'f4'); a.emit('mtc1', 't5', 'f5'); a.emit('cvt.s.w', 'f5', 'f5')
    a.emit('bne', 't8', 'zero', 'CONE'); a.emit('nop')
    a.emit('mul.s', 'f6', 'f4', 'f4'); a.emit('mul.s', 'f7', 'f5', 'f5'); a.emit('add.s', 'f6', 'f6', 'f7'); a.emit('sqrt.s', 'f6', 'f6')
    a.emit('div.s', 'f4', 'f4', 'f6'); a.emit('div.s', 'f5', 'f5', 'f6'); a.emit('beq', 'zero', 'zero', 'APPLY'); a.emit('nop')
    a.label('CONE')
    a.emit('lui', 'at', 0x3F35); a.emit('ori', 'at', 'at', 0x04F3); a.emit('mtc1', 'at', 'f10')                                    # sqrt(0.5)
    a.emit('slt', 't8', 't4', 'zero'); a.emit('mov.s', 'f4', 'f10'); a.emit('beq', 't8', 'zero', 'CX'); a.emit('nop'); a.emit('neg.s', 'f4', 'f10')
    a.label('CX')
    a.emit('slt', 't8', 't5', 'zero'); a.emit('mov.s', 'f5', 'f10'); a.emit('beq', 't8', 'zero', 'CF'); a.emit('nop'); a.emit('neg.s', 'f5', 'f10')
    a.label('CF')
    a.label('APPLY')
    a.emit('abs.s', 'f4', 'f4'); a.emit('mtc1', 'zero', 'f6'); a.emit('c.olt.s', 'f1', 'f6'); a.emit('bc1f', 'SGN'); a.emit('nop'); a.emit('neg.s', 'f4', 'f4')   # the side is the button's: a stick on the other side is mirrored
    a.label('SGN')
    a.emit('mul.s', 'f6', 'f3', 'f4'); a.emit('sub.s', 'f6', 'f6', 'f1'); a.emit('mul.s', 'f7', 'f3', 'f5')                        # change along right / along forward
    a.emit('lwc1', 'f10', 0x20, 's0'); a.emit('lwc1', 'f11', 0x28, 's0')
    a.emit('mul.s', 'f12', 'f6', 'f8'); a.emit('mul.s', 'f13', 'f7', 'f10'); a.emit('add.s', 'f12', 'f12', 'f13'); a.emit('add.s', 'f0', 'f0', 'f12'); a.emit('swc1', 'f0', 0, 'v1')
    a.emit('mul.s', 'f12', 'f6', 'f9'); a.emit('mul.s', 'f13', 'f7', 'f11'); a.emit('add.s', 'f12', 'f12', 'f13'); a.emit('add.s', 'f2', 'f2', 'f12'); a.emit('swc1', 'f2', 8, 'v1')
    a.label('RET'); a.emit('j', cont); a.emit('nop')
    return a.assemble()
def patches():
    w = build(); assert DRT + 4 * len(w) <= 0x5BD000
    return [(DRT + 4 * i, x) for i, x in enumerate(w)]
if __name__ == '__main__':
    p = patches(); print(len(p), 'words, end', hex(DRT + 4 * len(p)))
    if '-v' in sys.argv:
        for ad, x in p: print('patch=1,EE,%08X,word,%08X' % (ad, x))
