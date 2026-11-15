import sys, struct, math
sys.path.insert(0, r'C:\Users\shade\AppData\Local\Temp\claude\C--Users-shade-AppData-Roaming-Claude-scratch-workspaces-d26a4a75-75f2-47d7-a5b0-73edfc757065-46ea55b4-1b40-4e1b-8e0f-1c92210c0291-scratch-2026-10-16-8e6b16\9242a4f5-61eb-4545-89bd-55b3ca05d106\scratchpad')
from mipsasm import Asm
TR = 0x5BC000                          # moved 2026-10-28 from 005AF600 (grew); its data words stay at 005AF8F0..FC
RB = 0x5AF300                          # first ground frame after a roll: wind burst, backward roll -> turn right 90
LANDC = 0x5B7B20                       # air dash landing cave (the hook 001737C0 went there)
ROLLED, BACKF = -0x0710, -0x070C       # words 005AF8F0 / F4 (lui 0x5B)
SAVE = -0x0D20                         # 005AF2E0..EF: ra, a0, a1, a2 around the matrix rebuild
BR = 0x5AF200                          # burst updater hook: rotate the attached burst 90 right after the backward roll
BDELAY = -0x0D0C                       # 005AF2F4: frames until the delayed burst of the backward roll
BROT = -0x0D10                         # 005AF2F0: frames left to rotate the burst
BLKR = -0x0704                         # 005AF8FC: 1 = the roll started while blocking
CONE_HALF = 45                         # half the excluded cone straight forward / back (degrees); 2026-10-28: 15 -> 30 -> 45
TDIR = -0x0708                         # 005AF8F8: the way the roll travelled (yaw)
def fbits(x): return struct.unpack('<I', struct.pack('<f', x))[0]
def lif(a, f, x):
    b = fbits(x); a.emit('lui', 't6', b >> 16)
    if b & 0xFFFF: a.emit('ori', 't6', 't6', b & 0xFFFF)
    a.emit('mtc1', 't6', f)
def atan2_f1_f2(a, tag):
    # f7 = atan2(f1, f2) (polynomial atan as in TURNC / FACE); uses f3..f8, t4
    d1, d2, d3, d4, d5 = (tag + s for s in ('1', '2', '3', '4', '5'))
    a.emit('abs.s', 'f3', 'f1'); a.emit('abs.s', 'f4', 'f2')
    a.emit('daddu', 't4', 'zero', 'zero')
    a.emit('c.olt.s', 'f4', 'f3'); a.emit('bc1f', d1); a.emit('nop')
    a.emit('div.s', 'f5', 'f4', 'f3'); a.emit('ori', 't4', 'zero', 1)
    a.emit('beq', 'zero', 'zero', d2); a.emit('nop')
    a.label(d1); a.emit('div.s', 'f5', 'f3', 'f4')
    a.label(d2)
    a.emit('mul.s', 'f6', 'f5', 'f5')
    lif(a, 'f7', 0.0208351)
    for c in (-0.085133, 0.180141, -0.3302995, 0.999866):
        a.emit('mul.s', 'f7', 'f7', 'f6'); lif(a, 'f8', c); a.emit('add.s', 'f7', 'f7', 'f8')
    a.emit('mul.s', 'f7', 'f7', 'f5')
    a.emit('beq', 't4', 'zero', d3); a.emit('nop')
    lif(a, 'f8', math.pi / 2); a.emit('sub.s', 'f7', 'f8', 'f7')
    a.label(d3)
    a.emit('mtc1', 'zero', 'f8'); a.emit('c.olt.s', 'f2', 'f8'); a.emit('bc1f', d4); a.emit('nop')
    lif(a, 'f8', math.pi); a.emit('sub.s', 'f7', 'f8', 'f7')
    a.label(d4)
    a.emit('mtc1', 'zero', 'f8'); a.emit('c.olt.s', 'f1', 'f8'); a.emit('bc1f', d5); a.emit('nop')
    a.emit('neg.s', 'f7', 'f7')
    a.label(d5)# roll mode FUN_00173E38: 00173E98 (lhu v1,0x690(s3)) -> j TR (the addiu s1 behind it runs in the delay slot).
# First roll frame (a1 != 0): the roll animation itself carries Caim to his side, so he is turned 90 degrees so that
# side points the way he faced: +0x690 sign bit set (0xF010, the right roll) -> turn left 90, else (the left roll) ->
# turn right 90. Yaw +0x44 / rotation yaw +0x584, accumulator +0x204 = 0, +0x570 |= 2, so the roll rebuilds his matrix
# (00173F04) before it reads the right axis for its own direction.
def build():
    a = Asm(TR)
    a.emit('beq', 'a1', 'zero', 'PLAIN'); a.emit('nop')
    a.emit('lw', 't0', 0x66C, 's3'); a.emit('andi', 't0', 't0', 0x80)
    a.emit('bne', 't0', 'zero', 'BLK'); a.emit('nop')                 # block held: the block dodge below
    a.emit('lui', 't9', 0x5B); a.emit('sw', 'zero', BLKR, 't9'); a.emit('sw', 'zero', BACKF, 't9')
    # 2026-10-28: the roll goes along the stick direction, except inside the 30 degree cones straight forward and
    # straight back (15 degrees each side of the stick's up / down line), where it is pushed out to the 15 degree line on
    # the stick's side (x = 0 counts as right, like the Square / Circle mapping). Stick at rest: the vanilla roll (no
    # turn, no burst / turn after it). The cone is measured on the raw stick (pad copy 00342866 x / 00342867 y, 0x80
    # centre, up = smaller y, i.e. camera relative); the clamped raw direction is carried into Caim's frame with the same
    # rotation the game applied to the stick (raw u0 -> Caim-frame v at +0x67C / +0x67E): P = u0.v, Q = u0 x v,
    # v' = (P u'x - Q u'y, Q u'x + P u'y), then D = v'x * right - v'y * forward as in the block dodge.
    a.emit('lui', 't2', 0x34)
    a.emit('lbu', 't0', 0x2866, 't2'); a.emit('addiu', 't0', 't0', -0x80)
    a.emit('lbu', 't1', 0x2867, 't2'); a.emit('addiu', 't1', 't1', -0x80)
    a.emit('sra', 't3', 't0', 31); a.emit('xor', 't4', 't0', 't3'); a.emit('subu', 't4', 't4', 't3')   # |sx|
    a.emit('sra', 't3', 't1', 31); a.emit('xor', 't5', 't1', 't3'); a.emit('subu', 't5', 't5', 't3')   # |sy|
    a.emit('slti', 't4', 't4', 0x30); a.emit('slti', 't5', 't5', 0x30); a.emit('and', 't4', 't4', 't5')
    a.emit('bne', 't4', 'zero', 'PLAIN'); a.emit('nop')                # stick at rest: vanilla roll
    a.emit('daddu', 't8', 'zero', 'zero')                              # 0 = normal roll, 1 = block dodge
    a.label('CLAMP')
    a.emit('lh', 't1', 0x67C, 's3'); a.emit('lh', 't2', 0x67E, 's3')
    a.emit('sra', 't3', 't1', 31); a.emit('xor', 't4', 't1', 't3'); a.emit('subu', 't4', 't4', 't3')
    a.emit('sra', 't3', 't2', 31); a.emit('xor', 't5', 't2', 't3'); a.emit('subu', 't5', 't5', 't3')
    a.emit('addu', 't4', 't4', 't5'); a.emit('slti', 't4', 't4', 0x100)
    a.emit('bne', 't4', 'zero', 'PLAIN'); a.emit('nop')                # game sees no stick yet: vanilla roll
    a.emit('mtc1', 't1', 'f11'); a.emit('cvt.s.w', 'f11', 'f11')       # v = Caim-frame stick
    a.emit('mtc1', 't2', 'f12'); a.emit('cvt.s.w', 'f12', 'f12')
    a.emit('lui', 't2', 0x34)
    a.emit('lbu', 't0', 0x2866, 't2'); a.emit('addiu', 't0', 't0', -0x80)
    a.emit('lbu', 't1', 0x2867, 't2'); a.emit('addiu', 't1', 't1', -0x80)
    a.emit('mtc1', 't0', 'f9'); a.emit('cvt.s.w', 'f9', 'f9')          # u0 = raw stick
    a.emit('mtc1', 't1', 'f10'); a.emit('cvt.s.w', 'f10', 'f10')
    a.emit('mov.s', 'f1', 'f9'); a.emit('mov.s', 'f2', 'f10')          # u' = clamped raw stick
    a.emit('abs.s', 'f3', 'f9'); a.emit('abs.s', 'f4', 'f10')
    lif(a, 'f5', math.tan(math.radians(CONE_HALF)))
    a.emit('mul.s', 'f4', 'f4', 'f5')
    a.emit('c.olt.s', 'f3', 'f4'); a.emit('bc1f', 'NOCL'); a.emit('nop')
    a.emit('mov.s', 'f1', 'f4')                                       # inside a cone: x = +-tan15 * |y|
    a.emit('slt', 't3', 't0', 'zero'); a.emit('beq', 't3', 'zero', 'NOCL'); a.emit('nop')
    a.emit('neg.s', 'f1', 'f1')
    a.label('NOCL')
    a.emit('mul.s', 'f3', 'f9', 'f11'); a.emit('mul.s', 'f4', 'f10', 'f12'); a.emit('add.s', 'f13', 'f3', 'f4')   # P
    a.emit('mul.s', 'f3', 'f9', 'f12'); a.emit('mul.s', 'f4', 'f10', 'f11'); a.emit('sub.s', 'f14', 'f3', 'f4')   # Q
    a.emit('mul.s', 'f3', 'f13', 'f1'); a.emit('mul.s', 'f4', 'f14', 'f2'); a.emit('sub.s', 'f5', 'f3', 'f4')     # v'x
    a.emit('mul.s', 'f3', 'f14', 'f1'); a.emit('mul.s', 'f4', 'f13', 'f2'); a.emit('add.s', 'f6', 'f3', 'f4')     # v'y
    a.emit('lwc1', 'f10', 0x5B0, 's3'); a.emit('lwc1', 'f11', 0x5B8, 's3')       # forward axis x, z
    a.emit('lwc1', 'f3', 0x590, 's3'); a.emit('lwc1', 'f4', 0x598, 's3')         # right axis x, z
    a.emit('mul.s', 'f1', 'f5', 'f3'); a.emit('mul.s', 'f8', 'f6', 'f10'); a.emit('sub.s', 'f1', 'f1', 'f8')
    a.emit('mul.s', 'f2', 'f5', 'f4'); a.emit('mul.s', 'f8', 'f6', 'f11'); a.emit('sub.s', 'f2', 'f2', 'f8')
    atan2_f1_f2(a, 'NA')                                              # f7 = yaw the roll travels
    a.emit('bne', 't8', 'zero', 'SIDE'); a.emit('nop')                 # block dodge: keeps its own TDIR (pre-roll facing)
    a.emit('lui', 't9', 0x5B); a.emit('swc1', 'f7', TDIR, 't9')
    a.emit('ori', 't6', 'zero', 1); a.emit('sw', 't6', ROLLED, 't9')   # for RB: burst / facing after this roll
    a.emit('beq', 'zero', 'zero', 'SIDE'); a.emit('nop')
    a.label('APPLY')
    lif(a, 'f10', math.pi); lif(a, 'f11', 2 * math.pi); a.emit('neg.s', 'f12', 'f10')
    a.emit('c.olt.s', 'f10', 'f9'); a.emit('bc1f', 'W1'); a.emit('nop'); a.emit('sub.s', 'f9', 'f9', 'f11')
    a.label('W1')
    a.emit('c.olt.s', 'f9', 'f12'); a.emit('bc1f', 'W2'); a.emit('nop'); a.emit('add.s', 'f9', 'f9', 'f11')
    a.label('W2')
    a.emit('swc1', 'f9', 0x44, 's3'); a.emit('swc1', 'f9', 0x584, 's3'); a.emit('sw', 'zero', 0x204, 's3')
    a.emit('lw', 't6', 0x570, 's3'); a.emit('ori', 't6', 't6', 2); a.emit('sw', 't6', 0x570, 's3')
    a.emit('beq', 'zero', 'zero', 'PLAIN'); a.emit('nop')
    a.label('BLK')
    # blocking: the roll goes along the stick direction in the world (same cone clamp as the normal rolls), the side
    # (animation) is the one the Square mapping picked by the stick half. 2026-10-28: stick at rest = the vanilla roll
    # of the button (Square left, Circle right), like the normal rolls (it used to roll straight back).
    a.emit('lui', 't2', 0x34)
    a.emit('lbu', 't0', 0x2866, 't2'); a.emit('addiu', 't0', 't0', -0x80)
    a.emit('lbu', 't1', 0x2867, 't2'); a.emit('addiu', 't1', 't1', -0x80)
    a.emit('sra', 't3', 't0', 31); a.emit('xor', 't4', 't0', 't3'); a.emit('subu', 't4', 't4', 't3')
    a.emit('sra', 't3', 't1', 31); a.emit('xor', 't5', 't1', 't3'); a.emit('subu', 't5', 't5', 't3')
    a.emit('slti', 't4', 't4', 0x30); a.emit('slti', 't5', 't5', 0x30); a.emit('and', 't4', 't4', 't5')
    a.emit('bne', 't4', 'zero', 'PLAIN'); a.emit('nop')
    a.emit('lui', 't9', 0x5B); a.emit('ori', 't6', 'zero', 1)
    a.emit('sw', 't6', ROLLED, 't9'); a.emit('sw', 'zero', BACKF, 't9'); a.emit('sw', 't6', BLKR, 't9')
    a.emit('lwc1', 'f13', 0x44, 's3'); a.emit('swc1', 'f13', TDIR, 't9')
    a.emit('lh', 't1', 0x67C, 's3'); a.emit('lh', 't2', 0x67E, 's3')
    a.emit('sra', 't3', 't1', 31); a.emit('xor', 't4', 't1', 't3'); a.emit('subu', 't4', 't4', 't3')
    a.emit('sra', 't3', 't2', 31); a.emit('xor', 't5', 't2', 't3'); a.emit('subu', 't5', 't5', 't3')
    a.emit('addu', 't4', 't4', 't5'); a.emit('slti', 't4', 't4', 0x400)
    a.emit('lwc1', 'f10', 0x5B0, 's3'); a.emit('lwc1', 'f11', 0x5B8, 's3')       # forward axis x, z
    a.emit('ori', 't8', 'zero', 1)
    a.emit('beq', 't4', 'zero', 'CLAMP'); a.emit('nop')               # stick pushed: same cone clamp as the normal rolls
    a.emit('neg.s', 'f1', 'f10'); a.emit('neg.s', 'f2', 'f11')                # no stick: straight back
    a.emit('beq', 'zero', 'zero', 'BANG'); a.emit('nop')
    a.label('BSTK')
    a.emit('mtc1', 't1', 'f5'); a.emit('cvt.s.w', 'f5', 'f5')                 # x
    a.emit('mtc1', 't2', 'f6'); a.emit('cvt.s.w', 'f6', 'f6')                 # y (forward = -)
    a.emit('lwc1', 'f3', 0x590, 's3'); a.emit('lwc1', 'f4', 0x598, 's3')       # right axis x, z
    a.emit('mul.s', 'f1', 'f5', 'f3'); a.emit('mul.s', 'f8', 'f6', 'f10'); a.emit('sub.s', 'f1', 'f1', 'f8')
    a.emit('mul.s', 'f2', 'f5', 'f4'); a.emit('mul.s', 'f8', 'f6', 'f11'); a.emit('sub.s', 'f2', 'f2', 'f8')
    a.label('BANG')
    atan2_f1_f2(a, 'BA')                                              # f7 = yaw of the dodge direction
    a.label('SIDE')
    lif(a, 'f8', math.pi / 2)
    a.emit('lhu', 't0', 0x690, 's3'); a.emit('andi', 't0', 't0', 0x8000)
    a.emit('beq', 't0', 'zero', 'BL'); a.emit('nop')
    a.emit('add.s', 'f9', 'f7', 'f8')                                 # 0xF010 roll travels yaw - 90
    a.emit('beq', 'zero', 'zero', 'APPLY'); a.emit('nop')
    a.label('BL')
    a.emit('sub.s', 'f9', 'f7', 'f8')                                 # 0x0FF0 roll travels yaw + 90
    a.emit('beq', 'zero', 'zero', 'APPLY'); a.emit('nop')
    a.label('PLAIN')
    a.emit('lhu', 'v1', 0x690, 's3')
    a.emit('j', 0x173EA0); a.emit('nop')
    return a
def build_rb():
    # hook 001737C0 (jal, per frame in the ground mode, s0 = Caim, ra already points behind the jal) -> RB -> j LANDC
    a = Asm(RB)
    # delayed burst after the backward roll: started 2 frames after the roll end, once his turn is in his matrix (+0x50),
    # so STANDB creates it facing the way he does
    a.emit('lui', 't9', 0x5B); a.emit('lw', 't0', BDELAY, 't9')
    a.emit('beq', 't0', 'zero', 'NODL'); a.emit('addiu', 't0', 't0', -1)
    a.emit('sw', 't0', BDELAY, 't9'); a.emit('bne', 't0', 'zero', 'NODL'); a.emit('nop')
    a.emit('ori', 't3', 'zero', 1); a.emit('sw', 't3', 0x6CC, 's0')
    a.label('NODL')
    a.emit('lw', 't0', ROLLED, 't9')
    a.emit('beq', 't0', 'zero', 'GO'); a.emit('nop')
    a.emit('lw', 't0', 0x2DC, 's0'); a.emit('addiu', 't1', 'zero', 2)
    a.emit('bne', 't0', 't1', 'GO'); a.emit('nop')                   # only once he is back in the ground mode
    a.emit('sw', 'zero', ROLLED, 't9')
    # wind burst in every case: STANDB (005B2700, runs after LANDC in this frame) creates the burst directly when
    # +0x6CC is set (the burst slot alone only plays while he moves)
    a.emit('lw', 't5', BACKF, 't9'); a.emit('sw', 'zero', BACKF, 't9')
    # stick held forward / back (pad copy left stick 00342866 x / 00342867 y, 0x7F centre; the vertical part 0x30 or more
    # from the centre and at least the horizontal part): face the way the roll travelled
    a.emit('lui', 't2', 0x34)
    a.emit('lbu', 't0', 0x2866, 't2'); a.emit('addiu', 't0', 't0', -0x7F)
    a.emit('sra', 't3', 't0', 31); a.emit('xor', 't0', 't0', 't3'); a.emit('subu', 't0', 't0', 't3')   # |x|
    a.emit('lbu', 't1', 0x2867, 't2'); a.emit('addiu', 't1', 't1', -0x7F)
    a.emit('sra', 't3', 't1', 31); a.emit('xor', 't1', 't1', 't3'); a.emit('subu', 't1', 't1', 't3')   # |y|
    # burst: always after the backward roll; after a left / right roll only when he is still moving (stick held at the end)
    a.emit('lw', 't3', BLKR, 't9'); a.emit('bne', 't3', 'zero', 'NOBU'); a.emit('nop')   # block dodge: no burst
    a.emit('bne', 't5', 'zero', 'DLB'); a.emit('nop')
    a.emit('slti', 't3', 't0', 0x30); a.emit('beq', 't3', 'zero', 'BURST'); a.emit('nop')
    a.emit('slti', 't3', 't1', 0x30); a.emit('bne', 't3', 'zero', 'NOBU'); a.emit('nop')
    a.label('BURST')
    a.emit('ori', 't3', 'zero', 1); a.emit('sw', 't3', 0x6CC, 's0')
    a.emit('beq', 'zero', 'zero', 'NOBU'); a.emit('nop')
    a.label('DLB')
    a.emit('addiu', 't3', 'zero', 2); a.emit('sw', 't3', BDELAY, 't9')    # backward roll: burst 2 frames later
    a.label('NOBU')
    # after a block dodge: back to the facing he had before it
    a.emit('lw', 't3', BLKR, 't9'); a.emit('beq', 't3', 'zero', 'NOBK'); a.emit('nop')
    a.emit('sw', 'zero', BLKR, 't9')
    # 2026-10-28: no turn after a block dodge any more; he keeps the facing the dodge left him with
    a.emit('beq', 'zero', 'zero', 'GO'); a.emit('nop')
    a.label('NOBK')
    a.emit('slti', 't3', 't1', 0x30); a.emit('bne', 't3', 'zero', 'NOFB'); a.emit('nop')
    a.emit('slt', 't3', 't1', 't0'); a.emit('bne', 't3', 'zero', 'NOFB'); a.emit('nop')
    a.emit('lwc1', 'f9', TDIR, 't9')                                  # face the roll direction
    a.emit('lwc1', 'f8', 0x44, 's0'); a.emit('sub.s', 'f7', 'f9', 'f8')
    a.emit('beq', 'zero', 'zero', 'FACE'); a.emit('nop')
    a.label('NOFB')
    a.emit('beq', 't5', 'zero', 'GO'); a.emit('nop')
    # after the backward roll: turn 90 to the right AT ONCE (yaw + matrix rebuilt now), so the wind burst STANDB
    # creates from his matrix (+0x50) later in this frame is turned with him
    lif(a, 'f7', math.pi / 2)
    a.emit('lwc1', 'f9', 0x44, 's0'); a.emit('add.s', 'f9', 'f9', 'f7')
    lif(a, 'f10', math.pi); lif(a, 'f11', 2 * math.pi); a.emit('neg.s', 'f12', 'f10')
    a.emit('c.olt.s', 'f10', 'f9'); a.emit('bc1f', 'N1'); a.emit('nop'); a.emit('sub.s', 'f9', 'f9', 'f11')
    a.label('N1')
    a.emit('c.olt.s', 'f9', 'f12'); a.emit('bc1f', 'N2'); a.emit('nop'); a.emit('add.s', 'f9', 'f9', 'f11')
    a.label('N2')
    a.emit('swc1', 'f9', 0x44, 's0'); a.emit('swc1', 'f9', 0x584, 's0'); a.emit('sw', 'zero', 0x204, 's0')
    a.emit('lw', 't0', 0x570, 's0'); a.emit('ori', 't0', 't0', 2); a.emit('sw', 't0', 0x570, 's0')
    a.emit('sw', 'ra', SAVE + 0, 't9'); a.emit('sw', 'a0', SAVE + 4, 't9')
    a.emit('sw', 'a1', SAVE + 8, 't9'); a.emit('sw', 'a2', SAVE + 12, 't9')
    a.emit('jal', 0x12A644); a.emit('addiu', 'a0', 's0', 0x570)      # rebuild his matrix from +0x580 (as TURNC does)
    a.emit('lui', 't9', 0x5B)
    a.emit('lw', 'ra', SAVE + 0, 't9'); a.emit('lw', 'a0', SAVE + 4, 't9')
    a.emit('lw', 'a1', SAVE + 8, 't9'); a.emit('lw', 'a2', SAVE + 12, 't9')
    a.emit('beq', 'zero', 'zero', 'GO'); a.emit('nop')
    a.label('FACE')
    lif(a, 'f10', math.pi); lif(a, 'f11', 2 * math.pi); a.emit('neg.s', 'f12', 'f10')
    a.emit('c.olt.s', 'f10', 'f7'); a.emit('bc1f', 'D1'); a.emit('nop'); a.emit('sub.s', 'f7', 'f7', 'f11')
    a.label('D1')
    a.emit('c.olt.s', 'f7', 'f12'); a.emit('bc1f', 'D2'); a.emit('nop'); a.emit('add.s', 'f7', 'f7', 'f11')
    a.label('D2')
    a.emit('lwc1', 'f9', 0x44, 's0'); a.emit('add.s', 'f9', 'f9', 'f7')
    a.emit('c.olt.s', 'f10', 'f9'); a.emit('bc1f', 'R1'); a.emit('nop'); a.emit('sub.s', 'f9', 'f9', 'f11')
    a.label('R1')
    a.emit('c.olt.s', 'f9', 'f12'); a.emit('bc1f', 'R2'); a.emit('nop'); a.emit('add.s', 'f9', 'f9', 'f11')
    a.label('R2')
    a.emit('swc1', 'f9', 0x584, 's0'); a.emit('swc1', 'f7', 0x204, 's0')
    a.emit('lw', 't0', 0x210, 's0'); a.emit('ori', 't0', 't0', 2); a.emit('sw', 't0', 0x210, 's0')
    a.emit('lw', 't0', 0x570, 's0'); a.emit('ori', 't0', 't0', 1); a.emit('sw', 't0', 0x570, 's0')
    a.label('GO')
    a.emit('j', LANDC); a.emit('nop')
    return a
def build_br():
    # burst slot updater (FUN at 00178Dxx, fp = the actor): it copies the actor's transform block (+0x30..; yaw at +0x44)
    # to sp+0x30 every frame and places the attached burst from that copy. 00178D64 (addiu a1,sp,0x90) -> j BR: while
    # BROT runs and the actor is Caim, the copy's yaw gets +90 degrees (to the right) and its rebuild flag (bit 2).
    a = Asm(BR)
    a.emit('lui', 't9', 0x5B); a.emit('lw', 't0', BROT, 't9')
    a.emit('beq', 't0', 'zero', 'OUT'); a.emit('nop')
    a.emit('lui', 't1', 0x3A); a.emit('ori', 't1', 't1', 0xC5E0)
    a.emit('bne', 'fp', 't1', 'OUT'); a.emit('nop')
    a.emit('addiu', 't0', 't0', -1); a.emit('sw', 't0', BROT, 't9')
    a.emit('lwc1', 'f3', 0x44, 'sp'); lif(a, 'f4', math.pi / 2); a.emit('add.s', 'f3', 'f3', 'f4'); a.emit('swc1', 'f3', 0x44, 'sp')
    a.emit('lw', 't0', 0x30, 'sp'); a.emit('ori', 't0', 't0', 2); a.emit('sw', 't0', 0x30, 'sp')
    a.label('OUT')
    a.emit('addiu', 'a1', 'sp', 0x90)
    a.emit('j', 0x178D68); a.emit('nop')
    return a
def patches():
    p = [(TR + 4 * i, w) for i, w in enumerate(build().assemble())] + [(0x173E98, 0x08000000 | (TR >> 2))]
    p += [(RB + 4 * i, w) for i, w in enumerate(build_rb().assemble())] + [(0x1737C0, 0x0C000000 | (RB >> 2))]
    return p
if __name__ == '__main__':
    for ad, w in patches(): print('patch=1,EE,%08X,word,%08X' % (ad, w))
