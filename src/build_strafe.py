"""Brake toggle (R3) + right stick: while the ridden ground Angelus brake is toggled on (word 005BEE0C = 1) the right stick (raw pad bytes 00342864 x / 00342865 y, 0x7F centre) moves her in any direction at
her normal (non-boost) speed, relative to her heading, and tilts her slightly towards the stick; the right stick camera input is zeroed.
STRAFE (005BC800): reached from the end of GMOV (build_aerialboost.py: j STRAFE after the output vector at v1 is stored; f13 = |n|, the game's cruise movement, t0 = 00340000, t3 = 005C0000, s0 = dragon):
 toggle on and the stick outside a dead zone: direction d = (x, -y) / |(x, -y)| in her frame, strength min(1, |s| / 100); movement += (right * dx + forward * dy) * |n| * strength (horizontal: right axis +0x0 / +0x8,
 forward axis +0x20 / +0x28); the processed camera stick floats 00342F88 / 00342F8C are cleared. Returns to the GMOV label OUT.
TILT (005BC900, hook 001C5318 lwc1 f0,180(s0) in FUN_001C3EBC, delay slot harmless, returns to 001C5320 sub.s f0,f24,f0): the bank target f24 (stick x * 0.75, like the left stick) += rx / 128 * TILTK while
the toggle is on (dragon, ground, riding)."""
import sys, struct
sys.path.insert(0, r'C:\Users\shade\OneDrive\Documents\PCSX2\roms\drakengard_mod\src\lib'); sys.path.insert(0, r'C:\Users\shade\OneDrive\Documents\PCSX2\roms\drakengard_mod\src')
from mipsasm import Asm
import build_aerialboost as AB
STRAFE, TILT, YAWFIX, DOD = 0x5BC800, 0x5BC900, 0x5BCA40, AB.DOD
TV, TF = -0x11EC, -0x11E8        # 005BEE14 tilt applied this frame (rad of bank target), 005BEE18 its filtered copy (what the turn rate +0xB0 contains)
DEAD = 24
TILTK = 0.35
TGB = AB.TGB
def fb(x): return struct.unpack('<I', struct.pack('<f', x))[0]
def lif(a, f, x):
    b = fb(x); a.emit('lui', 'at', b >> 16)
    if b & 0xFFFF: a.emit('ori', 'at', 'at', b & 0xFFFF)
    a.emit('mtc1', 'at', f)
def absd(a, d, s, t):                       # d = |t|
    a.emit('sra', s, t, 31); a.emit('xor', d, t, s); a.emit('subu', d, d, s)
def strafe():
    specs, end = AB.layout()
    out = AB.LAB['GMOV']['OUT']
    a = Asm(STRAFE)
    a.emit('lui', 't4', 0x34); a.emit('sw', 'zero', 0x2F88, 't4'); a.emit('sw', 'zero', 0x2F8C, 't4')      # right stick camera off while riding on the ground (GMOV only runs then), brake mode or not
    a.emit('lw', 't2', TGB, 't3'); a.emit('beq', 't2', 'zero', 'OUT'); a.emit('nop')
    a.emit('lbu', 't4', 0x2864, 't0'); a.emit('lbu', 't5', 0x2865, 't0'); a.emit('addiu', 't4', 't4', -127); a.emit('addiu', 't5', 't5', -127)
    absd(a, 't9', 't8', 't4'); absd(a, 'at', 't8', 't5'); a.emit('addu', 't8', 't9', 'at'); a.emit('sltiu', 't8', 't8', DEAD); a.emit('bne', 't8', 'zero', 'OUT'); a.emit('nop')
    a.emit('mtc1', 't4', 'f4'); a.emit('cvt.s.w', 'f4', 'f4'); a.emit('mtc1', 't5', 'f5'); a.emit('cvt.s.w', 'f5', 'f5'); a.emit('neg.s', 'f5', 'f5')
    a.emit('mul.s', 'f6', 'f4', 'f4'); a.emit('mul.s', 'f7', 'f5', 'f5'); a.emit('add.s', 'f6', 'f6', 'f7'); a.emit('sqrt.s', 'f6', 'f6')
    lif(a, 'f7', 100.0); a.emit('div.s', 'f8', 'f6', 'f7'); lif(a, 'f9', 1.0); a.emit('c.olt.s', 'f9', 'f8'); a.emit('bc1f', 'ST'); a.emit('nop'); a.emit('mov.s', 'f8', 'f9')
    a.label('ST')
    a.emit('div.s', 'f4', 'f4', 'f6'); a.emit('div.s', 'f5', 'f5', 'f6'); a.emit('mul.s', 'f8', 'f8', 'f13')
    for off_r, off_f, off_o in ((0x0, 0x20, 0), (0x8, 0x28, 8)):
        a.emit('lwc1', 'f10', off_r, 's0'); a.emit('lwc1', 'f11', off_f, 's0'); a.emit('mul.s', 'f10', 'f10', 'f4'); a.emit('mul.s', 'f11', 'f11', 'f5')
        a.emit('add.s', 'f10', 'f10', 'f11'); a.emit('mul.s', 'f10', 'f10', 'f8'); a.emit('lwc1', 'f12', off_o, 'v1'); a.emit('add.s', 'f12', 'f12', 'f10'); a.emit('swc1', 'f12', off_o, 'v1')
    a.label('OUT'); a.emit('j', out); a.emit('nop')
    return a
def tilt():
    a = Asm(TILT)
    a.emit('lwc1', 'f0', 180, 's0')
    a.emit('lui', 't7', 0x5C); a.emit('sw', 'zero', TV, 't7')                                    # no tilt unless set below
    a.emit('lui', 't8', 0x41); a.emit('ori', 't8', 't8', 0xBFC0); a.emit('bne', 's0', 't8', 'OUT'); a.emit('nop')
    a.emit('lui', 't8', 0x3B); a.emit('lw', 't9', -0x336C, 't8'); a.emit('addiu', 't9', 't9', -2); a.emit('bne', 't9', 'zero', 'OUT'); a.emit('nop')
    a.emit('lui', 't8', 0x34); a.emit('lw', 't9', 0xDFC, 't8'); a.emit('bne', 't9', 'zero', 'OUT'); a.emit('nop')
    a.emit('lui', 't9', 0x5C); a.emit('lw', 't9', TGB, 't9'); a.emit('beq', 't9', 'zero', 'OUT'); a.emit('nop')
    a.emit('lbu', 't4', 0x2864, 't8'); a.emit('addiu', 't4', 't4', -127)
    absd(a, 't9', 't5', 't4'); a.emit('sltiu', 't9', 't9', 20); a.emit('bne', 't9', 'zero', 'OUT'); a.emit('nop')
    a.emit('mtc1', 't4', 'f1'); a.emit('cvt.s.w', 'f1', 'f1'); lif(a, 'f2', TILTK / 128.0); a.emit('mul.s', 'f1', 'f1', 'f2'); a.emit('swc1', 'f1', TV, 't7'); a.emit('add.s', 'f24', 'f24', 'f1')
    a.label('OUT'); a.emit('j', 0x1C5320); a.emit('nop')
    return a
def yawfix():
    # hook 001C470C (lw v0,15708(s0) in FUN_001C3EBC, delay slot 001C4710 lwc1 f6,176(s0) runs first): the heading changes by the turn rate +0xB0 / 40 and +0xB0 follows the bank (+0xB4) with a lag of 8%
    # per frame, so the TILT bank also turned her. f6 -= TF, the filtered tilt (TF += (TV - TF) * 0.08 each frame), so the tilt banks her without turning her; the steering stick still turns her.
    a = Asm(YAWFIX)
    a.emit('lui', 't8', 0x5C); a.emit('lwc1', 'f9', TV, 't8'); a.emit('lwc1', 'f10', TF, 't8'); a.emit('sub.s', 'f9', 'f9', 'f10')
    lif(a, 'f11', 0.08); a.emit('mul.s', 'f9', 'f9', 'f11'); a.emit('add.s', 'f10', 'f10', 'f9'); a.emit('swc1', 'f10', TF, 't8')
    a.emit('sub.s', 'f6', 'f6', 'f10')
    a.emit('lw', 'v0', 15708, 's0'); a.emit('j', 0x1C4714); a.emit('nop')
    return a
def dod():
    # brake mode, L3 press edge (called from GMOV in place of the glide start; t0 = 00340000, s0 = dragon): the dodge buffer of the strafe stick's side is set to 5 frames like the dodge buttons do
    # (ride code 001C4E44..001C4E6C: +0x3DC4 = left, +0x3DC8 = right); stick x (raw 00342864) < 120 = left, otherwise right. The dodge direction itself comes from DRT (build_angdodge.py), which reads this stick in brake mode.
    a = Asm(DOD)
    a.emit('lw', 't2', 15800, 's0'); a.emit('bne', 't2', 'zero', 'DONE'); a.emit('nop')                       # no L3 dodge during the R1 special (build_specmove.py)
    a.emit('lbu', 't1', 0x2864, 't0'); a.emit('sltiu', 't2', 't1', 120); a.emit('ori', 't8', 'zero', 5); a.emit('beq', 't2', 'zero', 'RGT'); a.emit('nop')
    a.emit('sw', 't8', 15812, 's0'); a.emit('beq', 'zero', 'zero', 'DONE'); a.emit('nop')
    a.label('RGT'); a.emit('sw', 't8', 15816, 's0')
    a.label('DONE'); a.emit('j', AB.LAB['GMOV']['NOE']); a.emit('nop')
    return a
def patches():
    p = []
    for base, b in ((STRAFE, strafe()), (TILT, tilt()), (YAWFIX, yawfix()), (DOD, dod())): p += [(base + 4 * i, w) for i, w in enumerate(b.assemble())]
    p += [(0x1C5318, 0x08000000 | (TILT >> 2)), (0x1C470C, 0x08000000 | (YAWFIX >> 2))]
    return p
if __name__ == '__main__':
    p = patches(); print(len(p), 'words; STRAFE ends %X' % (STRAFE + 4 * len(strafe().assemble())), 'TILT ends %X' % (TILT + 4 * len(tilt().assemble())))
