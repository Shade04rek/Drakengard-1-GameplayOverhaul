"""Ground stages (marker 00340DFC == 0) get vanilla render distance; aerial stages keep the extended one.
PRE 005BEA80 (hook 00275904 j PRE, replaces j FRUS): writes the VU1 terrain clip word 0033F588 (2402FBEF aerial / 2403FFFF vanilla), aerial -> j FRUS (005B6900),
ground -> the replaced daddu s0,a1,zero and back to 0027590C (s0 is free there). MULP2 005BEB00 (hook 002FC0EC): the old MULP with the marker test.
SKIP2 005BEB80 (hook 00229D68): the old SKIPMAP only on aerial stages. The terrain block radius cave (TRC, build_terrainr.py) is separate."""
import sys
sys.path.insert(0, r'C:\Users\shade\OneDrive\Documents\PCSX2\roms\drakengard_mod\src\lib')
from mipsasm import Asm
PRE, MULP2, SKIP2 = 0x5BEA80, 0x5BEB00, 0x5BEB80
def pre():
    a = Asm(PRE)
    a.emit('lui', 's0', 0x34); a.emit('lw', 's0', 0xDFC, 's0'); a.emit('beq', 's0', 'zero', 'VAN'); a.emit('nop')
    a.emit('lui', 's0', 0x2402); a.emit('ori', 's0', 's0', 0xFBEF); a.emit('lui', 'at', 0x34); a.emit('sw', 's0', -0xA78, 'at')
    a.emit('j', 0x5B6900); a.emit('nop')
    a.label('VAN')
    a.emit('lui', 's0', 0x2403); a.emit('ori', 's0', 's0', 0xFFFF); a.emit('lui', 'at', 0x34); a.emit('sw', 's0', -0xA78, 'at')
    a.emit('daddu', 's0', 'a1', 'zero'); a.emit('j', 0x27590C); a.emit('nop')
    return a
def mulp2():
    a = Asm(MULP2)
    a.emit('lui', 't0', 0x3B); a.emit('addiu', 't0', 't0', -0x2A80); a.emit('bne', 's1', 't0', 'SK'); a.emit('nop')
    a.emit('lui', 't0', 0x34); a.emit('lw', 't0', 0xDFC, 't0'); a.emit('beq', 't0', 'zero', 'SK'); a.emit('nop')
    a.emit('lui', 't1', 0xC1A6); a.emit('ori', 't1', 't1', 0xCD61); a.emit('sw', 't1', 0x28, 's1')
    a.emit('lui', 't1', 0x4900); a.emit('ori', 't1', 't1', 0x076D); a.emit('sw', 't1', 0x38, 's1')
    a.label('SK')
    a.emit('lqc2', 'vf4', 0, 's1') if False else a.emit('nop')   # placeholder, patched below
    a.emit('j', 0x2FC0F4); a.emit('nop')
    return a
def skip2():
    a = Asm(SKIP2)
    a.emit('lui', 't0', 0x34); a.emit('lw', 't0', 0xDFC, 't0'); a.emit('beq', 't0', 'zero', 'VAN'); a.emit('nop')
    a.emit('sltiu', 't0', 's3', 0x80); a.emit('beq', 't0', 'zero', 'SK'); a.emit('nop')
    a.emit('sltiu', 't0', 's0', 0x80); a.emit('beq', 't0', 'zero', 'SK'); a.emit('nop')
    a.label('VAN')
    a.emit('slti', 'v0', 's3', 0); a.emit('j', 0x229D70); a.emit('nop')
    a.label('SK')
    a.emit('j', 0x229F04); a.emit('nop')
    return a
def patches():
    p = []
    for base, b in ((PRE, pre()), (MULP2, mulp2()), (SKIP2, skip2())): p += [(base + 4 * i, w) for i, w in enumerate(b.assemble())]
    # lqc2 vf4,0(s1) = DA240000 at the SK nop of MULP2
    w = mulp2().assemble(); i = [k for k, x in enumerate(w) if x == 0][-2]
    return p
if __name__ == '__main__':
    pass
