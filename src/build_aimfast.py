"""Ridden ground Angelus: faster aiming. The visible pitch is the pose (dragon +0xC4), which the game eases towards the target (+0xC8) at only about 4% per frame; FUN_001C3EBC returns the target delta
at 001C52D0 (lwc1 f0,200(s0)) / 001C52D8 (sub.s f0,f22,f0). Hook 001C52D0 -> j AIM (delay slot 001C52D4 lw v0,192(sp) harmless): for the dragon (s0 == 0041BFC0) while Caim rides her on a ground stage
(003ACC94 == 2, marker 00340DFC == 0) the pose is moved RATE of the way to the game's own target f22 (swc1 at 196(s0)); the target and the auto-centre are the game's (the aim still returns to level when the
stick is centred, but fast). Returns to 001C52D8 with f0 = +0xC8."""
import sys, struct
sys.path.insert(0, r'C:\Users\shade\OneDrive\Documents\PCSX2\roms\drakengard_mod\src\lib')
from mipsasm import Asm
AIM = 0x5BC600
RATE = 0.30
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
    a.emit('lwc1', 'f1', 196, 's0'); a.emit('sub.s', 'f2', 'f22', 'f1'); lif(a, 'f3', RATE); a.emit('mul.s', 'f2', 'f2', 'f3'); a.emit('add.s', 'f1', 'f1', 'f2'); a.emit('swc1', 'f1', 196, 's0')
    a.label('OUT'); a.emit('j', 0x1C52D8); a.emit('nop')
    return a
def patches():
    w = build().assemble()
    return [(AIM + 4 * i, x) for i, x in enumerate(w)] + [(0x1C52D0, 0x08000000 | (AIM >> 2))]
if __name__ == '__main__':
    p = patches(); print(len(p) - 1, 'words, ends %X' % (AIM + 4 * (len(p) - 1)))
