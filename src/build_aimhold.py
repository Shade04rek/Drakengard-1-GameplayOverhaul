"""Ridden ground Angelus: the aim (pitch) stays where the stick leaves it and stops at once when the stick is centred. FUN_001C3EBC computes a target pitch f22 from the stick and returns the DELTA
f22 - pitch (dragon +0xC8) through its output pointer (001C52D0 lwc1 f0,200(s0) / 001C52D8 sub.s f0,f22,f0). The pose follows the target with a lag (+0xC4 = the pose pitch, +0xC8 = the target), so a target
that runs ahead of the pose (the K = 1 version: pitch + stick) kept the aim moving after the stick was let go. Hook 001C52D0 -> j AIM (the delay slot 001C52D4 lw v0,192(sp) is harmless): for the dragon
(s0 == 0041BFC0) while Caim rides her on a ground stage (003ACC94 == 2, marker 00340DFC == 0) AIM reads the raw left stick Y (pad byte 00342867; down = larger): inside the dead zone the target is the POSE pitch
(+0xC4), so the aim stops where it is; outside it the target is the pose pitch + (Y - 128) / 128 * LEAD (clamped to LO .. HI), a lead of at most LEAD rad ahead of the pose. Returns to 001C52D8 with
f0 = +0xC8 for the game's delta."""
import sys, struct
sys.path.insert(0, r'C:\Users\shade\OneDrive\Documents\PCSX2\roms\drakengard_mod\src\lib')
from mipsasm import Asm
AIM = 0x5BC600
LEAD = 0.12           # rad the target runs ahead of the pose at full stick
DEAD = 10             # dead zone of the stick (raw units)
LO, HI = -0.25, 0.25
RATE = 0.35          # share of the gap the POSE pitch (+0xC4, the visible one) covers per frame (the game's own ease is about 4%)
def fb(x): return struct.unpack('<I', struct.pack('<f', x))[0]
def lif(a, f, x):
    b = fb(x); a.emit('lui', 'at', b >> 16)
    if b & 0xFFFF: a.emit('ori', 'at', 'at', b & 0xFFFF)
    a.emit('mtc1', 'at', f)
def build():
    a = Asm(AIM)
    a.emit('lwc1', 'f0', 200, 's0')
    a.emit('lui', 't8', 0x41); a.emit('ori', 't8', 't8', 0xBFC0); a.emit('bne', 's0', 't8', 'OUT'); a.emit('nop')
    a.emit('lui', 't8', 0x3B); a.emit('lw', 't9', -0x336C, 't8'); a.emit('addiu', 't9', 't9', -2); a.emit('bne', 't9', 'zero', 'OUT'); a.emit('nop')
    a.emit('lui', 't8', 0x34); a.emit('lw', 't9', 0xDFC, 't8'); a.emit('bne', 't9', 'zero', 'OUT'); a.emit('nop')
    a.emit('lwc1', 'f22', 196, 's0')                                   # target = pose pitch (stops the aim)
    a.emit('lbu', 't9', 0x2867, 't8'); a.emit('addiu', 't9', 't9', -128)
    a.emit('sra', 't8', 't9', 31); a.emit('xor', 'at', 't9', 't8'); a.emit('subu', 'at', 'at', 't8')   # |d|
    a.emit('sltiu', 'at', 'at', DEAD); a.emit('bne', 'at', 'zero', 'OUT'); a.emit('nop')                # dead zone: stay
    a.emit('mtc1', 't9', 'f1'); a.emit('cvt.s.w', 'f1', 'f1')
    lif(a, 'f2', LEAD / 128.0); a.emit('mul.s', 'f1', 'f1', 'f2'); a.emit('add.s', 'f22', 'f22', 'f1')
    lif(a, 'f1', HI); a.emit('c.olt.s', 'f1', 'f22'); a.emit('bc1f', 'L1'); a.emit('nop'); a.emit('mov.s', 'f22', 'f1')
    a.label('L1')
    lif(a, 'f1', LO); a.emit('c.olt.s', 'f22', 'f1'); a.emit('bc1f', 'APPLY'); a.emit('nop'); a.emit('mov.s', 'f22', 'f1')
    a.label('APPLY')                                                    # the pose follows the target quickly (the game's own ease is slow)
    a.emit('lwc1', 'f1', 196, 's0'); a.emit('sub.s', 'f2', 'f22', 'f1'); lif(a, 'f3', RATE); a.emit('mul.s', 'f2', 'f2', 'f3'); a.emit('add.s', 'f1', 'f1', 'f2'); a.emit('swc1', 'f1', 196, 's0')
    a.label('OUT'); a.emit('j', 0x1C52D8); a.emit('nop')
    return a
def patches():
    w = build().assemble()
    return [(AIM + 4 * i, x) for i, x in enumerate(w)] + [(0x1C52D0, 0x08000000 | (AIM >> 2))]
if __name__ == '__main__':
    p = patches(); print(len(p) - 1, 'words, ends %X' % (AIM + 4 * (len(p) - 1)))
