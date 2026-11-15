"""No flap sound at the boost start while the glide pose is used (2026-11-10).
The boost start of the ridden dragon (FUN_001C3EBC, the multiplier +0x3DE8 set at the L2 press) plays the dragon sound 7 with FUN_001C6CBC(1.0, 7, 0041C090) from 001C4D30 (jal). FLP (005B8740) replaces
that jal: it returns without a sound when the boost will use the glide pose, otherwise it jumps to FUN_001C6CBC as before. The glide decision follows the pose caves:
  aerial stage (marker 00340DFC != 0): glide unless she climbs steeply (dragon forward y 0041BFE4 below CLIMB = the regular boost animation with flapping, build_aerialboost.py BGL);
  ground stage, Caim rides her (003ACC94 == 2), L3 lock word 005BEDE4 == 0:
    fast mode (005BEE0C == 0): glide unless the left stick is pulled fully back (raw y 00342867 >= 0xF0) or the pose pitch 0041C084 is above 0.05 (GBL / GB2 of build_glideboost.py);
    brake mode (005BEE0C != 0): glide while she is not at the lowest point (FL word 005BEDEC == 0, GB3)."""
import sys, struct
sys.path.insert(0, r'C:\Users\shade\OneDrive\Documents\PCSX2\roms\drakengard_mod\src\lib'); sys.path.insert(0, r'C:\Users\shade\OneDrive\Documents\PCSX2\roms\drakengard_mod\src')
from mipsasm import Asm
import build_aerialboost as AB
FLP = 0x5B8740
HOOK = 0x1C4D30
def build():
    cl = struct.unpack('<I', struct.pack('<f', AB.CLIMB))[0]
    a = Asm(FLP)
    a.emit('lui', 't8', 0x41); a.emit('ori', 't8', 't8', 0xC090); a.emit('bne', 'a2', 't8', 'REAL'); a.emit('nop')                 # only the ridden dragon object 0041BFC0
    a.emit('lui', 't8', 0x34); a.emit('lw', 't9', 0xDFC, 't8'); a.emit('bne', 't9', 'zero', 'AIR'); a.emit('nop')
    # ground
    a.emit('lui', 't8', 0x3B); a.emit('lw', 't9', -0x336C, 't8'); a.emit('addiu', 't9', 't9', -2); a.emit('bne', 't9', 'zero', 'REAL'); a.emit('nop')     # Caim rides
    a.emit('lui', 't8', 0x5C); a.emit('lw', 't9', -0x121C, 't8'); a.emit('bne', 't9', 'zero', 'REAL'); a.emit('nop')                                    # L3 lock: no boost pose
    a.emit('lw', 't9', AB.TGB, 't8'); a.emit('bne', 't9', 'zero', 'BRKM'); a.emit('nop')
    a.emit('lui', 't9', 0x34); a.emit('lbu', 't9', 0x2867, 't9'); a.emit('sltiu', 't9', 't9', 0xF0); a.emit('beq', 't9', 'zero', 'REAL'); a.emit('nop')    # stick fully back: regular animation
    a.emit('lui', 't9', 0x42); a.emit('lw', 't9', -0x3F7C, 't9'); a.emit('lui', 'at', 0x3D4C); a.emit('ori', 'at', 'at', 0xCCCD); a.emit('slt', 'at', 'at', 't9'); a.emit('bne', 'at', 'zero', 'REAL'); a.emit('nop')   # climbing: regular
    a.emit('jr', 'ra'); a.emit('nop')
    a.label('BRKM')
    a.emit('lw', 't9', -0x1214, 't8'); a.emit('bne', 't9', 'zero', 'REAL'); a.emit('nop')                                                               # lowest point: regular animation
    a.emit('jr', 'ra'); a.emit('nop')
    a.label('AIR')
    a.emit('lui', 't8', 0x42); a.emit('lw', 't9', -0x401C, 't8')                                                                                   # dragon forward y 0041BFE4
    a.emit('srl', 'at', 't9', 31); a.emit('beq', 'at', 'zero', 'GL'); a.emit('nop')                                                                                                        # not climbing
    a.emit('lui', 'at', cl >> 16); a.emit('ori', 'at', 'at', cl & 0xFFFF); a.emit('sltu', 'at', 'at', 't9'); a.emit('bne', 'at', 'zero', 'REAL'); a.emit('nop')    # steeply up (more negative than CLIMB): regular
    a.label('GL'); a.emit('jr', 'ra'); a.emit('nop')
    a.label('REAL'); a.emit('j', 0x1C6CBC); a.emit('nop')
    return a
FLQ = 0x5B8840
HOOKQ = 0x1C90C8
def flq():
    """2026-11-10 (the real flap sound): the tail of FUN_001C868C (the blend setup, s0 = the dragon animation object 0041C140, s2 = the pitch parameter) plays the dragon sound 0 (the wing flap, random volume, FUN_001C6CBC
    from 001C9194) when the REAL pitch parameter p (001C90C8 lwc1 f0,0(s2)) is inside a range and the wing animation query FUN_002A2528 is non-zero. The glide pose is made by BGL feeding the blend a different p (SP, 005BEFF8);
    here the sound check gets the same p, so it sees the dive value and stays silent. FLQ replaces the lwc1 at 001C90C8: the dragon animation object, on an aerial stage or with Caim riding on the ground -> f0 = SP."""
    a = Asm(FLQ)
    a.emit('lui', 'v1', 0x41); a.emit('ori', 'v1', 'v1', 0xC140); a.emit('bne', 's0', 'v1', 'ORIG'); a.emit('nop')
    a.emit('lui', 'at', 0x34); a.emit('lw', 'v1', 0xDFC, 'at'); a.emit('bne', 'v1', 'zero', 'USE'); a.emit('nop')
    a.emit('lui', 'at', 0x3B); a.emit('lw', 'v1', -0x336C, 'at'); a.emit('addiu', 'v1', 'v1', -2); a.emit('bne', 'v1', 'zero', 'ORIG'); a.emit('nop')
    a.label('USE'); a.emit('lui', 'at', 0x5C); a.emit('lwc1', 'f0', AB.SP, 'at'); a.emit('j', 0x1C90CC); a.emit('nop')
    a.label('ORIG'); a.emit('lwc1', 'f0', 0, 's2'); a.emit('j', 0x1C90CC); a.emit('nop')
    return a
def patches():
    a = build(); w = a.assemble()
    q = flq().assemble()
    return [(FLP + 4 * i, x) for i, x in enumerate(w)] + [(HOOK, 0x0C000000 | (FLP >> 2))] + [(FLQ + 4 * i, x) for i, x in enumerate(q)] + [(HOOKQ, 0x08000000 | (FLQ >> 2))]
if __name__ == '__main__':
    for ad, x in patches(): print('%08X %08X' % (ad, x))


