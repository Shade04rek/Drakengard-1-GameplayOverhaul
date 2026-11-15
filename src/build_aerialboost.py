"""Angelus aerial boost: while the boost action is held (pad action word 00342898 bit 0x100) the wings-out dive animation plays (aerial stages, marker 00340DFC != 0,
the dragon animation object s0 == 0041C140 only), except while she climbs steeply: forward y (dragon +0x24, y points down; s0 - 0x15C) below -sin(60 degrees) = -0.866,
i.e. 30 degrees or less from straight up. BGL (hook 001C8728, FUN_001C868C blend setup): the pitch parameter p is read as 0.0 (the steepest dive) in the normal case.
The wing wind effect caves of 2026-11-06 were removed (build_aerialboost.py.bak_wind)."""
import sys, struct, math
sys.path.insert(0, r'C:\Users\shade\OneDrive\Documents\PCSX2\roms\drakengard_mod\src\lib')
from mipsasm import Asm
DRT = 0x5BCC00        # build_angdodge.py
STRAFE = 0x5BC800     # build_strafe.py (returns to the GMOV label OUT)
VUP = 0x5BCF80        # build_vmult.py: the vertical movement x3, then j STRAFE
GBL = 0x5BCF00        # build_glideboost.py: ground stage branch of BGL (fast mode boost = the glide pose)
DOD = 0x5BCB00        # build_strafe.py: L3 dodge in brake mode (returns to the GMOV label NOE)
BASE = 0x5BE700
CLIMB = -math.sin(0.2866)                 # -0.2827: 16.42 degrees up (the user state 2): flapping and the climb speed start here
def fb(x): return struct.unpack('<I', struct.pack('<f', x))[0]
SP = -0x1008                               # 005BEFF8 (lui 0x5C): the pitch parameter the blend setup sees while boosting (smoothed)
RAMP = 0.07                                # share of the way to the target covered each frame
def bgl(base):
    # hook 001C8728 (lwc1 f0,0(s2) in FUN_001C868C, p = the pitch parameter). Not boosting: p as it is (and SP follows it). Boosting (action bit 0x100), dragon, aerial:
    # target = 0.0 (the dive pose), or p itself while she climbs above the CLIMB angle (flapping); SP moves towards the target by RAMP of the gap every frame and the
    # blend setup sees SP, so the wings change gradually (the blend weight of the dive pose is 1 - p / 0.3 below p = 0.3).
    a = Asm(base); a.emit('lwc1', 'f0', 0, 's2')
    a.emit('lui', 't8', 0x41); a.emit('ori', 't8', 't8', 0xC140); a.emit('bne', 's0', 't8', 'OUT'); a.emit('nop')
    a.emit('lui', 't8', 0x34); a.emit('lw', 't9', 0xDFC, 't8'); a.emit('beq', 't9', 'zero', 'GNDX'); a.emit('nop')                      # ground stage: GBL (build_glideboost.py)
    a.emit('lui', 't9', 0x5C)
    a.emit('lhu', 't8', 0x2898 - 0x10000 if False else 0x2898, 't8'); a.emit('andi', 't8', 't8', 0x100); a.emit('beq', 't8', 'zero', 'NB'); a.emit('nop')
    a.label('BCM')
    a.emit('mov.s', 'f6', 'f0')
    b_ = fb(CLIMB); a.emit('lwc1', 'f11', -0x15C, 's0'); a.emit('lui', 'at', b_ >> 16); a.emit('ori', 'at', 'at', b_ & 0xFFFF); a.emit('mtc1', 'at', 'f10')
    a.emit('c.olt.s', 'f11', 'f10'); a.emit('bc1t', 'SET'); a.emit('nop')
    a.emit('mtc1', 'zero', 'f6')
    a.label('SET')
    a.emit('lwc1', 'f7', SP, 't9'); a.emit('sub.s', 'f8', 'f6', 'f7')
    k = fb(RAMP); a.emit('lui', 'at', k >> 16); a.emit('ori', 'at', 'at', k & 0xFFFF); a.emit('mtc1', 'at', 'f9')
    a.emit('mul.s', 'f8', 'f8', 'f9'); a.emit('add.s', 'f7', 'f7', 'f8'); a.emit('swc1', 'f7', SP, 't9'); a.emit('mov.s', 'f0', 'f7')
    a.emit('beq', 'zero', 'zero', 'OUT'); a.emit('nop')
    a.label('NB'); a.emit('swc1', 'f0', SP, 't9')
    a.label('OUT'); a.emit('j', 0x1C872C); a.emit('nop')
    a.label('GNDX'); a.emit('j', GBL); a.emit('nop')
    return a
CLIMBSPEED = 1.2                           # movement x1.2 while boosting in the steep climb range (flapping, above 45 degrees up)
BRAKE_UP, BRAKE_DOWN = 0.15, 0.25          # ground brake: share of the gap to full braking per frame while Cross is held / share released per frame
TGB, RBP = -0x11F4, -0x11F0               # 005BEE0C / 005BEE10 (lui 0x5C): brake toggled on by R3 (1/0), R3 was down last frame
BK = -0x100C                               # 005BEFF4 (lui 0x5C): the brake amount 0 .. 1 (float)
def mov(base):
    # hook 001B73F4 (FUN_001B73C0, the collision move: the world movement vector is at s1 + 0xF0), dragon only; the ground brake is in GMOV (non-collision mover).
    # Aerial stage (marker 00340DFC != 0): while boosting and climbing above CLIMB the movement is x CLIMBSPEED.
    # Ground stage while Caim rides her (Angelus actor 003ACF20 +0x20 == 5 and +0x3A4 == 2): while Cross (pad pressure byte 0034286E = 00342864 + 0xA) is held the movement
    # is multiplied by 1 - brake, the brake amount (word 005BEFF4) rising to 1 by BRAKE_UP of the gap per frame and falling back by BRAKE_DOWN when Cross is let go:
    # she slows down to a halt quickly but not instantly; the rest of the controls are untouched.
    a = Asm(base); a.emit('addiu', 's2', 's1', 240)
    a.emit('lui', 't0', 0x41); a.emit('ori', 't0', 't0', 0xBFC0); a.emit('bne', 's1', 't0', 'OUT'); a.emit('nop')
    a.emit('lui', 't0', 0x34); a.emit('lw', 't1', 0xDFC, 't0'); a.emit('beq', 't1', 'zero', 'OUT'); a.emit('nop')
    a.emit('lhu', 't1', 0x2898, 't0'); a.emit('andi', 't1', 't1', 0x100); a.emit('beq', 't1', 'zero', 'OUT'); a.emit('nop')
    b = fb(CLIMB); a.emit('lwc1', 'f4', 0x24, 's1'); a.emit('lui', 'at', b >> 16); a.emit('ori', 'at', 'at', b & 0xFFFF); a.emit('mtc1', 'at', 'f5')
    a.emit('c.olt.s', 'f4', 'f5'); a.emit('bc1f', 'OUT'); a.emit('nop')
    k = fb(CLIMBSPEED); a.emit('lui', 'at', k >> 16); a.emit('ori', 'at', 'at', k & 0xFFFF); a.emit('mtc1', 'at', 'f10')
    for i in range(3):
        a.emit('lwc1', 'f%d' % i, 4 * i, 's2'); a.emit('mul.s', 'f%d' % i, 'f%d' % i, 'f10'); a.emit('swc1', 'f%d' % i, 4 * i, 's2')
    a.emit('beq', 'zero', 'zero', 'OUT'); a.emit('nop')
    a.label('OUT'); a.emit('j', 0x1B73FC); a.emit('nop'); return a
MX, MY, MZ, MFL, GT = -0x1020, -0x101C, -0x1018, -0x1014, -0x1010   # 005BEFE0 .. 005BEFF0: momentum vector (floats), flags (bit0 boost flag, bit1 L3 was held, bit2 L2 was held), glide frames left (int)
D_NORMAL, D_BOOST = 0.93, 0.975            # momentum kept per frame while braking (without / with the L2 boost before the brake)
ENGAGE, RELEASE = 0.35, 0.12               # brake weight: share of the gap per frame while Cross is held / let go
TG = 120                                   # glide frames: 2 seconds at 60 movement updates per second
def gmov(base):
    # hook 001B7810 (addiu v1,s0,240 in the non-collision mover 001B77E0, which the ridden ground Angelus uses: a write breakpoint on her position stopped at 001B7820 with
    # ra 001B7808; s0 = the object, v1 = its movement vector +0xF0 that the following vadd adds to the position +0xD0; the lqc2 in the delay slot, 001B7814, is harmless;
    # a0 = s0 + 208 must survive). Ground stage (marker 00340DFC == 0), dragon (0041BFC0), Caim rides her (Angelus actor 003ACF20 +0x20 == 5 and +0x3A4 == 2).
    # Every free frame (no brake, no glide, weight gone) the movement vector n is stored as the momentum M (005BEFE0..E8) and the L2 boost button held (pressure byte at
    # 00342864 + the index byte 005747BA) as the boost flag (bit 0 of 005BEFEC; bit 1 L3 held last frame, bit 2 L2 held, bit 3 a dodge bit held, bit 4 ramp-down running).
    # The movement is n (1 - w) + M w with the weight w (005BEFF4).
    #  Cross (pressure byte 0034286E): M * D every frame (D_BOOST if she was boosting), w up by ENGAGE of the gap per frame: she slides on in the old direction.
    #  L3 (byte 0056CD82 bit 1, active low, press edge, not while a glide or its ramp-down runs): glide frames GT (005BEFF0) = TG (3 s). Each frame with GT > 0 w = 1 and M stays
    #  as it was (cruise or boost movement): direction and speed locked whatever she does. A FRESH L2 boost press (down now, not on the last frame) or a fresh dodge (the ground ride code buffers a dodge press for 5 frames in the dragon words +0x3DC4 / +0x3DC8 when the pad action word of its pad pointer has the bit 0x01000000 / 0x02000000: 1C4E44..1C4E6C; the first version read 0034289C instead, which is not that word) ends it at once (w = 0, M = n: the boost / the dodge
    #  takes over). If GT runs out uninterrupted the RAMP-DOWN starts: w stays 1 and M * D every frame (D_BOOST after a boost) until |M| < 1: a full stop; then w falls by
    #  RELEASE per frame and the normal movement (cruising speed) takes over. A fresh L2 or dodge during the ramp-down ends it at once as well.
    a = Asm(base); a.emit('addiu', 'v1', 's0', 240)
    a.emit('lui', 't0', 0x41); a.emit('ori', 't0', 't0', 0xBFC0); a.emit('bne', 's0', 't0', 'OUT'); a.emit('nop')
    a.emit('lui', 't0', 0x34); a.emit('lw', 't1', 0xDFC, 't0'); a.emit('bne', 't1', 'zero', 'OUT'); a.emit('nop')
    a.emit('lui', 't3', 0x5C)
    a.emit('lui', 't1', 0x3B); a.emit('lw', 't2', -12480, 't1'); a.emit('addiu', 't2', 't2', -5); a.emit('bne', 't2', 'zero', 'GNO'); a.emit('nop')
    a.emit('lw', 't2', -11580, 't1'); a.emit('addiu', 't2', 't2', -2); a.emit('bne', 't2', 'zero', 'GNO'); a.emit('nop')
    # stick-angle dodge direction (DRT, build_angdodge.py): rotates the sideways dodge movement in the vector at v1; returns to CONT (t0, t3, v1, s0 kept)
    a.emit('j', DRT); a.emit('nop'); a.label('CONT')
    # R3 toggles the brake (words TGB 005BEE0C = brake on, RBP 005BEE10 = R3 was down last frame): press edge flips TGB
    a.emit('lui', 't2', 0x57); a.emit('lbu', 't2', -0x327E, 't2'); a.emit('andi', 't2', 't2', 4); a.emit('sltiu', 't2', 't2', 1)           # 1 when R3 is down
    a.emit('lw', 't8', RBP, 't3'); a.emit('sw', 't2', RBP, 't3'); a.emit('beq', 't2', 'zero', 'NR3'); a.emit('nop'); a.emit('bne', 't8', 'zero', 'NR3'); a.emit('nop')
    a.emit('lw', 't8', TGB, 't3'); a.emit('xori', 't8', 't8', 1); a.emit('sw', 't8', TGB, 't3')
    a.label('NR3')
    # t6 = flags, t7 = glide frames, t5 = L2 boost button held (1/0), t4 = L3 held (1/0), t9 = a dodge action bit set (1/0)
    a.emit('lw', 't6', MFL, 't3'); a.emit('lw', 't7', GT, 't3')
    a.emit('lui', 't4', 0x57); a.emit('lbu', 't4', -0x327E, 't4'); a.emit('andi', 't4', 't4', 2); a.emit('sltiu', 't4', 't4', 1)          # 1 when L3 is down
    a.emit('lui', 't5', 0x57); a.emit('lbu', 't5', 0x47BA, 't5'); a.emit('addu', 't5', 't5', 't0'); a.emit('lbu', 't5', 0x2864, 't5'); a.emit('sltiu', 't5', 't5', 0x40); a.emit('xori', 't5', 't5', 1)
    a.emit('lw', 't9', 0x3DC4, 's0'); a.emit('lw', 'at', 0x3DC8, 's0'); a.emit('or', 't9', 't9', 'at'); a.emit('sltu', 't9', 'zero', 't9')       # a dodge input buffered by the ground ride code (5 frames)
    # L3 press edge starts the glide (not while a glide or its ramp-down runs)
    a.emit('andi', 't2', 't6', 2); a.emit('bne', 't2', 'zero', 'NOE'); a.emit('nop')
    a.emit('beq', 't4', 'zero', 'NOE'); a.emit('nop')
    a.emit('lw', 't2', TGB, 't3'); a.emit('beq', 't2', 'zero', 'GL3'); a.emit('nop'); a.emit('j', DOD); a.emit('nop')          # brake mode: the L3 press is a dodge (build_strafe.py DOD, returns to NOE)
    a.label('GL3')
    a.emit('bne', 't7', 'zero', 'NOE'); a.emit('nop')
    a.emit('andi', 't2', 't6', 0x10); a.emit('bne', 't2', 'zero', 'NOE'); a.emit('nop')
    a.emit('ori', 't7', 'zero', TG)
    a.label('NOE')
    # a fresh L2 press or a fresh dodge ends the glide / the ramp-down: w = 0 at once, M = n again
    a.emit('or', 't8', 't7', 'zero'); a.emit('andi', 't2', 't6', 0x10); a.emit('or', 't8', 't8', 't2')                  # t8 != 0 while a glide or its ramp-down runs
    a.emit('beq', 't8', 'zero', 'BDC'); a.emit('nop')
    a.emit('andi', 't2', 't6', 4); a.emit('bne', 't2', 'zero', 'NOL2'); a.emit('nop')
    a.emit('bne', 't5', 'zero', 'CNC'); a.emit('nop')
    a.label('NOL2')
    a.emit('andi', 't2', 't6', 8); a.emit('bne', 't2', 'zero', 'BDC'); a.emit('nop')
    a.emit('beq', 't9', 'zero', 'BDC'); a.emit('nop')
    a.label('CNC')
    a.emit('or', 't7', 'zero', 'zero'); a.emit('andi', 't6', 't6', 0x2F); a.emit('sw', 'zero', BK, 't3')
    a.label('BDC')
    # a fresh dodge while Cross is held ends the brake slide too: w = 0, and the brake stays off (flag bit 5, 0x20) while the dodge lasts and is back at once when it is over (Cross still held)
    a.emit('andi', 't2', 't6', 8); a.emit('bne', 't2', 'zero', 'NOF'); a.emit('nop')
    a.emit('beq', 't9', 'zero', 'NOF'); a.emit('nop')
    a.emit('j', XCB1); a.emit('nop'); a.label('XR1')                                                                       # t2 = 1 when no brake (toggle off and Cross up), XCB1 005B8700
    a.emit('bne', 't2', 'zero', 'NOF'); a.emit('nop')
    a.emit('ori', 't6', 't6', 0x20); a.emit('sw', 'zero', BK, 't3')
    a.label('NOF')
    a.emit('andi', 't6', 't6', 0x31); a.emit('sll', 't2', 't4', 1); a.emit('or', 't6', 't6', 't2'); a.emit('sll', 't2', 't5', 2); a.emit('or', 't6', 't6', 't2')
    a.emit('sll', 't2', 't9', 3); a.emit('or', 't6', 't6', 't2')                                                          # prev bits: L3 (1), L2 (2), dodge (3)
    a.emit('lwc1', 'f0', 0, 'v1'); a.emit('lwc1', 'f1', 4, 'v1'); a.emit('lwc1', 'f2', 8, 'v1')                    # n
    a.emit('lwc1', 'f6', BK, 't3'); a.emit('lui', 'at', 0x3F80); a.emit('mtc1', 'at', 'f7')                           # w, 1.0
    a.emit('lwc1', 'f3', MX, 't3'); a.emit('lwc1', 'f4', MY, 't3'); a.emit('lwc1', 'f5', MZ, 't3')                    # M
    a.emit('j', XCB2); a.emit('nop'); a.label('XR2')                                                                       # 1 = brake off (toggle off and Cross up), XCB2 005B8720
    a.emit('andi', 't1', 't6', 0x20); a.emit('beq', 't1', 'zero', 'NSUP'); a.emit('nop')
    # the brake is off while the dodge lasts (the dodge timer +0x3D7C, set to at least 15 by the dodge start 001C4E98..001C4EB4 and counted down by the dragon update, or a buffered dodge
    # press in +0x3DC4 / +0x3DC8) and comes back at once when it is over, as long as Cross is held
    a.emit('lw', 't1', 0x3D7C, 's0'); a.emit('lw', 'at', 0x3DC4, 's0'); a.emit('or', 't1', 't1', 'at'); a.emit('lw', 'at', 0x3DC8, 's0'); a.emit('or', 't1', 't1', 'at')
    a.emit('bne', 't1', 'zero', 'SUPH'); a.emit('nop'); a.emit('andi', 't6', 't6', 0x1F); a.emit('beq', 'zero', 'zero', 'NSUP'); a.emit('nop')     # the dodge is over: the brake is allowed again
    a.label('SUPH'); a.emit('ori', 't2', 'zero', 1)                                                                      # during the dodge: no brake
    a.label('NSUP')
    a.emit('beq', 't2', 'zero', 'BRK'); a.emit('nop')                                                                    # Cross held
    a.emit('bne', 't7', 'zero', 'GLD'); a.emit('nop')
    a.emit('andi', 't2', 't6', 0x10); a.emit('bne', 't2', 'zero', 'RDN'); a.emit('nop')
    a.emit('beq', 'zero', 'zero', 'REL'); a.emit('nop')
    a.label('BRK')
    a.emit('beq', 't7', 'zero', 'BRK2'); a.emit('nop'); a.emit('addiu', 't7', 't7', -1)                               # the glide timer runs on during the brake
    a.emit('bne', 't7', 'zero', 'BRK2'); a.emit('nop'); a.emit('ori', 't6', 't6', 0x10)
    a.label('BRK2')
    a.emit('sub.s', 'f8', 'f7', 'f6'); ke = fb(ENGAGE); a.emit('lui', 'at', ke >> 16); a.emit('ori', 'at', 'at', ke & 0xFFFF); a.emit('mtc1', 'at', 'f9')
    a.emit('mul.s', 'f8', 'f8', 'f9'); a.emit('add.s', 'f6', 'f6', 'f8')
    a.emit('beq', 'zero', 'zero', 'DEC'); a.emit('nop')
    a.label('GLD')
    a.emit('addiu', 't7', 't7', -1); a.emit('mov.s', 'f6', 'f7')                                                         # w = 1, M kept
    a.emit('bne', 't7', 'zero', 'STO'); a.emit('nop'); a.emit('ori', 't6', 't6', 0x10)                                  # the timer ran out: the ramp-down starts next frame
    a.emit('beq', 'zero', 'zero', 'STO'); a.emit('nop')
    a.label('RDN')
    a.emit('mov.s', 'f6', 'f7')                                                                                           # w = 1
    a.emit('mul.s', 'f8', 'f3', 'f3'); a.emit('mul.s', 'f9', 'f4', 'f4'); a.emit('add.s', 'f8', 'f8', 'f9'); a.emit('mul.s', 'f9', 'f5', 'f5'); a.emit('add.s', 'f8', 'f8', 'f9')
    a.emit('c.olt.s', 'f8', 'f7'); a.emit('bc1f', 'DEC'); a.emit('nop')                                                   # |M|^2 < 1: stopped
    a.emit('andi', 't6', 't6', 0x2F)
    a.emit('beq', 'zero', 'zero', 'DEC'); a.emit('nop')
    a.label('REL')
    kr = fb(RELEASE); a.emit('lui', 'at', kr >> 16); a.emit('ori', 'at', 'at', kr & 0xFFFF); a.emit('mtc1', 'at', 'f9')
    a.emit('mul.s', 'f8', 'f6', 'f9'); a.emit('sub.s', 'f6', 'f6', 'f8')
    a.emit('lui', 'at', 0x3B03); a.emit('ori', 'at', 'at', 0x126F); a.emit('mtc1', 'at', 'f9')                          # 0.002
    a.emit('c.olt.s', 'f6', 'f9'); a.emit('bc1f', 'DEC'); a.emit('nop')
    a.emit('mtc1', 'zero', 'f6'); a.emit('mov.s', 'f3', 'f0'); a.emit('mov.s', 'f4', 'f1'); a.emit('mov.s', 'f5', 'f2')
    a.emit('andi', 't6', 't6', 0x3E); a.emit('or', 't6', 't6', 't5')                                                      # refresh the boost flag (bit 0), keep the other bits
    a.emit('beq', 'zero', 'zero', 'STO'); a.emit('nop')
    a.label('DEC')
    # M *= D
    a.emit('andi', 't2', 't6', 1); dn = fb(D_NORMAL); a.emit('lui', 'at', dn >> 16); a.emit('ori', 'at', 'at', dn & 0xFFFF); a.emit('mtc1', 'at', 'f9')
    a.emit('beq', 't2', 'zero', 'DD'); a.emit('nop')
    db = fb(D_BOOST); a.emit('lui', 'at', db >> 16); a.emit('ori', 'at', 'at', db & 0xFFFF); a.emit('mtc1', 'at', 'f9')
    a.label('DD')
    a.emit('mul.s', 'f3', 'f3', 'f9'); a.emit('mul.s', 'f4', 'f4', 'f9'); a.emit('mul.s', 'f5', 'f5', 'f9')
    a.label('STO')
    a.emit('swc1', 'f6', BK, 't3'); a.emit('swc1', 'f3', MX, 't3'); a.emit('swc1', 'f4', MY, 't3'); a.emit('swc1', 'f5', MZ, 't3'); a.emit('sw', 't6', MFL, 't3'); a.emit('sw', 't7', GT, 't3')
    # f13 = |n| (the game's cruise movement this frame, used by the strafe block STRAFE of build_strafe.py)
    a.emit('mul.s', 'f9', 'f0', 'f0'); a.emit('mul.s', 'f10', 'f1', 'f1'); a.emit('add.s', 'f9', 'f9', 'f10'); a.emit('mul.s', 'f10', 'f2', 'f2'); a.emit('add.s', 'f9', 'f9', 'f10'); a.emit('sqrt.s', 'f13', 'f9')
    # during a dodge |n| contains the dodge's own speed (about 20 more than the cruise): the strafe would add that on top and double the dodge, so f13 is held at the cruise value of the last frame without a dodge (word 005BEE1C)
    a.emit('lw', 't1', 0x3D7C, 's0'); a.emit('lui', 't2', 0x5C); a.emit('bne', 't1', 'zero', 'VOLD'); a.emit('nop'); a.emit('swc1', 'f13', -0x11E4, 't2'); a.emit('beq', 'zero', 'zero', 'VDN'); a.emit('nop')
    a.label('VOLD'); a.emit('lwc1', 'f13', -0x11E4, 't2')
    a.label('VDN')
    # out = n (1 - w) + M w
    a.emit('sub.s', 'f8', 'f7', 'f6')
    for i, (n, m) in enumerate((('f0', 'f3'), ('f1', 'f4'), ('f2', 'f5'))):
        a.emit('mul.s', n, n, 'f8'); a.emit('mul.s', m, m, 'f6'); a.emit('add.s', n, n, m); a.emit('swc1', n, 4 * i, 'v1')
    a.emit('j', VUP); a.emit('nop')                                                                                   # right stick strafe while the brake toggle is on (build_strafe.py), returns to OUT
    a.label('GNO'); a.emit('sw', 'zero', BK, 't3'); a.emit('ori', 't2', 'zero', 1); a.emit('sw', 't2', TGB, 't3'); a.emit('sw', 'zero', RBP, 't3'); a.emit('sw', 'zero', GT, 't3'); a.emit('lw', 't6', MFL, 't3'); a.emit('andi', 't6', 't6', 0xF); a.emit('sw', 't6', MFL, 't3')
    a.label('OUT'); a.emit('j', 0x1B7818); a.emit('nop'); return a
XCB1, XCB2 = 0x5B8700, 0x5B8720      # Cross brake 2026-11-10: the dedicated brake on Cross (pressure byte 0034286E, >= 0x40) in the fast mode (R3 toggle off), like the toggle
LAB = {}
def xcb(base, ret):
    a = Asm(base)
    a.emit('lw', 't2', TGB, 't3'); a.emit('sltiu', 't2', 't2', 1)
    a.emit('lbu', 't1', 0x286E, 't0'); a.emit('sltiu', 't1', 't1', 0x40); a.emit('and', 't2', 't2', 't1')                # Cross up and the toggle off = no brake
    a.emit('j', ret); a.emit('nop'); return a
def layout():
    specs = []; cur = BASE
    for name, mk, hook in (('BGL', bgl, 0x1C8728), ('MOV', mov, 0x1B73F4), ('GMOV', gmov, 0x1B7810)):
        a = mk(cur); w = a.assemble(); LAB[name] = dict(a.labels); specs.append((name, cur, w, hook)); cur += 4 * len(w)
    for nm, xb, rl in (('XCB1', XCB1, 'XR1'), ('XCB2', XCB2, 'XR2')):
        g = LAB['GMOV'][rl]; a = xcb(xb, g); w = a.assemble(); LAB[nm] = dict(a.labels); specs.append((nm, xb, w, None))
    assert cur <= 0x5BEC00        # the camera / ally voice caves start there; the lean data word D is at 005BE6F0 (build_lean.py DD), the caves start at BASE = 005BE700
    return specs, cur
def patches():
    p = []
    for name, base, w, hook in layout()[0]:
        p += [(base + 4 * i, x) for i, x in enumerate(w)]
        if hook: p.append((hook, 0x08000000 | (base >> 2)))
    return p
if __name__ == '__main__':
    specs, end = layout(); print(len(specs[0][2]), 'words, end', hex(end), '%08X' % fb(CLIMB))
