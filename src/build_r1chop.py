"""R1 aerial chop chain (Caim on the ground stages): a copy of the R2 air slash chain, but with the game's own air attack (the chop, FUN_001767A8(Caim, 2), jump type 2) in place of the slash (Caim, 1 / type 1).
The R2 chain (slash jump double jump section): chain flag F (0033F6DC) 0 -> 0x800 (hop) -> 0xC00 (no hop) -> 0xE00 (no hop, stop value at 005B2548); NXT (005B2540) computes the next value, TRC (005B2500) starts the slash without a hop
for 0xC00 / 0xE00 and DJS (00342D1C -> 00342D60) starts it after the hop. New word CH (005BEE04) = 1 while the chain is an R1 chop chain (cleared at every real takeoff, CLR).
R1X (hook: 00342CA8 = j R1X, its delay slot li v0,0x800 stays): reached with t8 = (R1 double jump flag | previous spell bits) and t3 = held spell bits; on a NEW R1 press (t8 < t3):
  - the jump button double jump was used (JD flag 005BDF14 != 0) or the R2 chain is running (F != 0, CH = 0): the old R1 behaviour (jump heavy attack double jump, v0 = 0x800 -> 00342C3C);
  - CH = 1 (R1 chain running): the next chain step (NXT) when a jump attack has started (jump type [Caim+0x660] != 0);
  - otherwise: the chain starts: CH = 1, F = 1 (NXT then gives 0x800, a hop, as the 2nd R2 slash) and the first chop starts at once without a hop (TRX).
TRX (hook 005B2514 = j TRX) and DJX (hook 00342D74 = j DJX) are the slash starts of TRC / DJS with a1 = 1 + CH and the jump type = 1 + CH. CLR (hook 00342C28) clears CH at the takeoff frame (before: sw zero,0x13E530 / F)."""
import sys
sys.path.insert(0, r'C:\Users\shade\OneDrive\Documents\PCSX2\roms\drakengard_mod\src\lib')
from mipsasm import Asm
R1X, TRX, DJX, CLR, JDX = 0x5BDC20, 0x5BDCA0, 0x5BDD30, 0x5BDD80, 0x5BDDA0
FX, FY = 0x5BDDD0, 0x5BDE40
BUFC = 0x5BE500       # buffered R1 chop: forward speed x0.25
BUF_H = 5.0            # a chop that starts less than this high above the ground counts as buffered from the ground
BUF_K = 0.25           # forward speed factor
RISE = 0x5BE600       # R1 chop: cancel the rise of the jump and descend at once
CHOP_DESC = 3.0        # y units per frame (y grows downward) while the chop would still be rising
GRD = 0x5BD240        # R1 press guard: only Caim (003AC5E0) gets the R1 chop / heavy attack caves; allies keep the old R1 behaviour
HVX = 0x5BD190       # R1 double jump heavy attack WITHOUT the hop
HEAVY_TAKEOFF_RATE = 0x2400    # 0x1200 * 2
CHOP_FALL = 1.0     # extra fall factor of the chop = the heavy attack factor (0033F6F4, both 1.0 = 2x as fast)
CH = -0x11FC          # 005BEE04 (lui 0x5C)
JDF = -8428           # 005BDF14, the jump-button double jump flag (JD cave, base 005C0000)
def r1x():
    a = Asm(R1X)
    a.emit('beq', 't8', 'zero', 'NOP1'); a.emit('nop')
    a.emit('lui', 'k0', 0x5C)
    a.emit('lw', 'k1', JDF, 'k0'); a.emit('bne', 'k1', 'zero', 'HV'); a.emit('nop')
    a.emit('lw', 'k1', CH, 'k0'); a.emit('bne', 'k1', 'zero', 'CT'); a.emit('nop')
    a.emit('ori', 'k1', 'zero', 1); a.emit('sw', 'k1', CH, 'k0')      # F stays 0: a non-zero chain flag scales the jump arc by 0.25 (the chop fell to the ground at once)
    a.emit('j', 0x5B2514); a.emit('nop')
    a.label('CT'); a.emit('j', 0x342C4C); a.emit('nop')                       # single chop: later R1 presses do nothing
    a.label('HV'); a.emit('j', HVX); a.emit('nop')
    # no new R1 press: the R2 part of DJ2 (00342CB0) runs, unless the R1 chop was played in this jump (CH = 1): then R2 does nothing (an R1 chop is followed only by the jump-button double jump)
    a.label('NOP1'); a.emit('lui', 'k0', 0x5C); a.emit('lw', 'k1', CH, 'k0'); a.emit('bne', 'k1', 'zero', 'NOR2'); a.emit('nop')
    a.emit('j', 0x342CB0); a.emit('nop')
    a.label('NOR2'); a.emit('j', 0x342C4C); a.emit('nop')
    return a
def _trx_asm():
    return trx()
def trx():
    a = Asm(TRX)
    a.emit('daddu', 'a0', 's1', 'zero'); a.emit('lui', 't8', 0x5C); a.emit('lw', 'a1', CH, 't8'); a.emit('addiu', 'a1', 'a1', 1)
    a.emit('jal', 0x1767A8); a.emit('nop')
    a.emit('lui', 't8', 0x5C); a.emit('lw', 't2', CH, 't8')
    # only the R1 chop (CH = 1) plays at 3x: the same two starts also begin the R2 slashes (CH = 0), which keep their speed
    a.emit('beq', 't2', 'zero', 'NR'); a.emit('nop')
    a.emit('lhu', 't3', 0x174, 's1'); a.emit('sll', 't3', 't3', 1); a.emit('sh', 't3', 0x174, 's1')
    a.emit('j', BUFC); a.emit('nop')
    a.label('NR'); a.emit('addiu', 't2', 't2', 1); a.emit('sw', 't2', 1632, 's1')
    a.emit('lw', 'v1', 748, 's1'); a.emit('j', 0x174FE4); a.emit('nop')
    return a
def djx():
    a = Asm(DJX)
    a.emit('daddu', 'a0', 's1', 'zero'); a.emit('lui', 't8', 0x5C); a.emit('lw', 'a1', CH, 't8'); a.emit('addiu', 'a1', 'a1', 1)
    a.emit('jal', 0x1767A8); a.emit('nop')
    a.emit('lui', 't8', 0x5C); a.emit('lw', 't2', CH, 't8')
    # only the R1 chop (CH = 1) plays at 3x: the same two starts also begin the R2 slashes (CH = 0), which keep their speed
    a.emit('beq', 't2', 'zero', 'NR'); a.emit('nop')
    a.emit('lhu', 't3', 0x174, 's1'); a.emit('sll', 't3', 't3', 1); a.emit('sh', 't3', 0x174, 's1')
    a.label('NR'); a.emit('addiu', 't2', 't2', 1); a.emit('sw', 't2', 1632, 's1')
    a.emit('j', 0x3419F0); a.emit('nop')
    return a
def clr():
    a = Asm(CLR)
    a.emit('lui', 'k0', 0x5C); a.emit('sw', 'zero', CH, 'k0'); a.emit('j', 0x174FE4); a.emit('nop')
    return a
def jdx():
    # hook 005BDFA4 (bne at,zero,5BDFC0 in JD: the jump-button double jump is refused while the chain flag F (at) is not 0): allowed after any air slash of the R2 chain; F is cleared (so the double jump is a plain hop, not a slash)
    a = Asm(JDX)
    a.emit('beq', 'at', 'zero', 'OK'); a.emit('nop')
    a.emit('lui', 'k1', 0x34); a.emit('sw', 'zero', -2340, 'k1')
    a.label('OK'); a.emit('j', 0x5BDFAC); a.emit('nop')
    return a
def fx():
    # hook 00321E68 (bne t7,zero,321EB8 in FALL: the jump heavy attack needs 0013E530 == 0x800): the R1 chop (CH = 1) falls faster too
    a = Asm(FX)
    a.emit('beq', 't7', 'zero', 'GO7'); a.emit('nop')
    a.emit('lui', 't7', 0x5C); a.emit('lw', 't7', CH, 't7'); a.emit('beq', 't7', 'zero', 'NO'); a.emit('nop')
    a.emit('j', 0x321E6C); a.emit('nop')
    a.label('NO'); a.emit('j', 0x321EB8); a.emit('nop')
    a.label('GO7'); a.emit('j', 0x321E6C); a.emit('nop')
    return a
def fy():
    # hook 00321E94 / 00321E98 (lwc1 f6 + mul.s f3 in FALL): the extra fall factor is CHOP_FALL for the chop (CH = 1 and not the heavy attack flag), else the stored value
    import struct
    b = struct.unpack('<I', struct.pack('<f', CHOP_FALL))[0]
    a = Asm(FY)
    a.emit('lwc1', 'f6', -2316, 't0')
    a.emit('lui', 't7', 0x5C); a.emit('lw', 't7', CH, 't7'); a.emit('beq', 't7', 'zero', 'DN'); a.emit('nop')
    a.emit('lui', 't7', 0x14); a.emit('lw', 't7', -6864, 't7'); a.emit('xori', 't7', 't7', 0x800); a.emit('beq', 't7', 'zero', 'DN'); a.emit('nop')
    a.emit('lui', 't7', b >> 16); a.emit('mtc1', 't7', 'f6')
    a.label('DN'); a.emit('mul.s', 'f3', 'f3', 'f6'); a.emit('j', 0x321E9C); a.emit('nop')
    return a
def hvx():
    # R1 in the air (heavy attack case of R1X, v0 = 0x800, t0 = 0x00140000, s1 = Caim): no re-entry of the takeoff (no hop). Sets the double jump flag 0013E530 = 0x800, the takeoff rate in the animation table (entry 63, the
    # rate cave ARATE runs a frame too late), and starts the jump heavy attack directly as DJS (00342D38..00342D5C) does: FUN_001767A8(Caim, 2), jump type 3, counter 005B2F00 = 0x28 (auto attack hold), 005B1F00 = 0, then back to the jump state
    # the way TRX does (v1 = [Caim+0x2EC], j 00174FE4).
    a = Asm(HVX)
    a.emit('ori', 'k1', 'zero', HEAVY_TAKEOFF_RATE); a.emit('lui', 'k0', 0x3C); a.emit('sh', 'k1', -20062, 'k0')
    a.emit('sw', 'v0', -6864, 't0')
    a.emit('daddu', 'a0', 's1', 'zero'); a.emit('jal', 0x1767A8); a.emit('ori', 'a1', 'zero', 2)
    a.emit('ori', 't2', 'zero', 3); a.emit('sw', 't2', 1632, 's1')
    a.emit('lui', 't3', 0x5B); a.emit('ori', 't2', 'zero', 0x28); a.emit('sw', 't2', 12032, 't3'); a.emit('sw', 'zero', 7936, 't3')
    a.emit('lw', 'v1', 748, 's1'); a.emit('j', 0x174FE4); a.emit('nop')
    return a
def rise():
    # hook 00321EA4 (swc1 f1,-2324(t0) of FALL: the last y word; the delay slot 00321EA8 ori t1,1 stays). While the R1 chop is on (CH = 1, not the heavy attack) and the last y is valid (word 0033F6F0), a y that is not below the last y
    # (the jump arc is still rising or flat; y grows downward: f1 = y, f2 = last y) becomes last y + CHOP_DESC: the rise is cut and she descends at once. Caim's y is [Caim+0x84] = 003AC664 (t8 = 003B0000, t0 = 00340000).
    import struct
    b = struct.unpack('<I', struct.pack('<f', CHOP_DESC))[0]
    a = Asm(RISE)
    a.emit('lui', 't7', 0x5C); a.emit('lw', 't7', CH, 't7')
    a.emit('beq', 't7', 'zero', 'GO'); a.emit('lw', 't7', -2320, 't0')
    a.emit('beq', 't7', 'zero', 'GO'); a.emit('lui', 't9', 0x14)
    a.emit('lw', 't9', -6864, 't9'); a.emit('xori', 't9', 't9', 0x800)
    a.emit('beq', 't9', 'zero', 'GO'); a.emit('c.olt.s', 'f2', 'f1')
    a.emit('bc1t', 'GO'); a.emit('lui', 't7', b >> 16)
    a.emit('mtc1', 't7', 'f5'); a.emit('add.s', 'f1', 'f2', 'f5')
    # never below the ground / bridge surface: the ground height [Caim+0x650] = 003ACC30 (t8 = 003B0000); a flat y (landed on a bridge) was pushed under the surface and she fell through
    a.emit('lwc1', 'f4', -13264, 't8'); a.emit('c.olt.s', 'f4', 'f1'); a.emit('bc1f', 'SETG'); a.emit('nop'); a.emit('mov.s', 'f1', 'f4')
    a.label('SETG'); a.emit('swc1', 'f1', -14748, 't8')
    a.label('GO'); a.emit('swc1', 'f1', -2324, 't0'); a.emit('j', 0x321EAC); a.emit('nop')
    return a
def bufc():
    # called from TRX (the first chop of the R1 chain, CH = 1; the floats are free after the FUN_001767A8 call) and returns to the TRX label NR. Buffered from the ground = the height above the ground ([Caim+0x650] - y [Caim+0x84], y grows
    # downward) is below BUF_H: Caim's horizontal momentum [+0x300] / [+0x308] and the air speed AIRGS (word 0033EDA8) are multiplied by BUF_K once (the speed of the jump stays like that to the landing).
    import struct
    fbits = lambda x: struct.unpack('<I', struct.pack('<f', x))[0]
    nr = trx_labels()['NR']
    a = Asm(BUFC)
    a.emit('lwc1', 'f4', 0x650, 's1'); a.emit('lwc1', 'f5', 0x84, 's1'); a.emit('sub.s', 'f4', 'f4', 'f5')
    a.emit('lui', 't9', fbits(BUF_H) >> 16); a.emit('mtc1', 't9', 'f5'); a.emit('c.olt.s', 'f4', 'f5'); a.emit('bc1f', 'OUT'); a.emit('nop')
    a.emit('lui', 't9', fbits(BUF_K) >> 16); a.emit('mtc1', 't9', 'f5')
    a.emit('lwc1', 'f4', 0x300, 's1'); a.emit('mul.s', 'f4', 'f4', 'f5'); a.emit('swc1', 'f4', 0x300, 's1')
    a.emit('lwc1', 'f4', 0x308, 's1'); a.emit('mul.s', 'f4', 'f4', 'f5'); a.emit('swc1', 'f4', 0x308, 's1')
    a.emit('lui', 't8', 0x34); a.emit('lwc1', 'f4', -4696, 't8'); a.emit('mul.s', 'f4', 'f4', 'f5'); a.emit('swc1', 'f4', -4696, 't8')
    a.label('OUT'); a.emit('j', nr); a.emit('nop')
    return a
def trx_labels():
    # label addresses of TRX (assembled with BUFC at a dummy return address first)
    import types
    return dict(_trx_asm().labels)
def grd():
    # hook 00342CA8 = j GRD (delay slot li v0,0x800 stays). Caim: R1X. Another actor (an ally the player controls): the old code: a new R1 press (t8 != 0) -> 00342C3C, else the R2 part 00342CB0.
    a = Asm(GRD)
    a.emit('lui', 'k0', 0x3A); a.emit('ori', 'k0', 'k0', 0xC5E0); a.emit('beq', 's1', 'k0', 'CAIM'); a.emit('nop')
    a.emit('bne', 't8', 'zero', 'OLDH'); a.emit('nop'); a.emit('j', 0x342CB0); a.emit('nop')
    a.label('OLDH'); a.emit('j', 0x342C3C); a.emit('nop')
    a.label('CAIM'); a.emit('j', R1X); a.emit('nop')
    return a
def j(t): return 0x08000000 | (t >> 2)
def patches():
    p = []
    for base, mk in ((R1X, r1x), (TRX, trx), (DJX, djx), (CLR, clr), (JDX, jdx), (FX, fx), (FY, fy), (HVX, hvx), (RISE, rise), (BUFC, bufc), (GRD, grd)):
        p += [(base + 4 * i, w) for i, w in enumerate(mk().assemble())]
    p += [(0x342CA8, j(GRD)), (0x5B2514, j(TRX)), (0x5B2518, 0), (0x342D74, j(DJX)), (0x342D78, 0), (0x342C28, j(CLR)), (0x5BDFA4, j(JDX)), (0x321EA4, j(RISE)), (0x321E68, j(FX)), (0x321E94, j(FY)), (0x321E98, 0)]
    return p
if __name__ == '__main__':
    for ad, w in patches(): print('patch=1,EE,%08X,word,%08X' % (ad, w))
