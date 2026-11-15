"""Caim leans into curves. Two caves:
TILTF (005BE520, hook 00321A74 -> TILTF -> j AUTO 005BD700, so it needs the Auto-attack section): every pad update frame, while Caim walks
(main state [+0x2D0] 2, sub state [+0x2DC] 2, walk timer [+0x6A0] >= 0x200) it takes the change of his yaw (the model block's float [+0x584]) since the last frame (wrapped
to +-pi), makes S = clamp(K * dyaw, +-SMAX) and glides the stored tilt (word 005BE1EC) towards it (A per frame). Not walking: tilt = 0 at once.
LEAN (005BE700, hook 0012A6D0 / 0012A6D4 = j LEAN / nop in FUN_0012A694, the lazy matrix getter of a transform block; s0 = the block): for Caim's block
(0x3AC610 = Caim + 0x30) the matrix rows (right at block + 0x20, up at + 0x30) are rotated about the forward row so that right.y (the y axis points
down in this game) equals the stored tilt. right.y is measured from the matrix, so the rotation is a no-op when the matrix is already tilted
(the matrix is only rebuilt from the yaw when the game flags it). Positive tilt = right side down = lean to the right (yaw increasing = turn right)."""
import sys, struct
sys.path.insert(0, r'C:\Users\shade\OneDrive\Documents\PCSX2\roms\drakengard_mod\src\lib')
from mipsasm import Asm
TILTF = 0x5B8400
LEAN = 0x5BE700
AUTO = 0x5BD700
YAWP, SS = -0x1E18, -0x1E14          # 005BE1E8 (previous yaw), 005BE1EC (stored tilt), lui 0x5C
K = 4.6 # sprint                             # tilt (sine of the roll angle) per radian of yaw change per frame
SMAX = 0.39 # sprint                         # limit (about 23 degrees)
A = 0.15                             # second glide per frame (tilt S towards D)
AR = 0.05                           # slower glide while the tilt shrinks (back to upright)
NOWK = 0.92                          # not walking: the tilt is multiplied by this each frame
KN, SMAXN, ARN, NOWKN = 3.1, 0.25, 0.09, 0.88   # regular movement (not sprinting): the earlier, weaker lean; K, SMAX, AR, NOWK above are for the sprint
A1 = 0.25                            # first glide per frame (D towards the clamped yaw change); one glide of 0.35 and of 0.12 were still jittery
DD = -0x1910                         # 005BE6F0: D (was 005BE900; moved so the aerial / ground caves can use the free area behind TILTF)
def fb(x): return struct.unpack('<I', struct.pack('<f', x))[0]
def lif(a, f, x):
    b = fb(x); a.emit('lui', 'at', b >> 16)
    if b & 0xFFFF: a.emit('ori', 'at', 'at', b & 0xFFFF)
    a.emit('mtc1', 'at', f)
_n = [0]
def pick(a, f, normal, sprint):
    # f = normal, or the sprint value when t9 (the sprint latch word) is not 0
    _n[0] += 1; lab = 'PK%d' % _n[0]
    lif(a, f, normal); a.emit('beq', 't9', 'zero', lab); a.emit('nop'); lif(a, f, sprint)
    a.label(lab)
def neutral(a, miss):
    # left stick at rest (raw pad bytes 00342866 x / 00342867 y within 0x70..0x8F): falls through; otherwise branches to miss (uses at, t4)
    a.emit('lui', 'at', 0x34)
    for off in (0x2866, 0x2867):
        a.emit('lbu', 't4', off, 'at'); a.emit('addiu', 't4', 't4', -112); a.emit('sltiu', 't4', 't4', 32)
        a.emit('beq', 't4', 'zero', miss); a.emit('nop')
def build_tiltf():
    a = Asm(TILTF)
    a.emit('lui', 't4', 0x2F); a.emit('lw', 't9', 0x345C, 't4')                    # sprint latch
    a.emit('lui', 't3', 0x3B)
    a.emit('lw', 't4', -0x3750, 't3'); a.emit('xori', 't4', 't4', 2); a.emit('bne', 't4', 'zero', 'NOW'); a.emit('nop')
    a.emit('lw', 't4', -0x3744, 't3'); a.emit('xori', 't4', 't4', 2); a.emit('bne', 't4', 'zero', 'NOW'); a.emit('nop')
    a.emit('lw', 't4', -0x3380, 't3'); a.emit('sltiu', 't4', 't4', 0x200); a.emit('bne', 't4', 'zero', 'NOW'); a.emit('nop')
    a.emit('lwc1', 'f0', -0x349C, 't3')                     # yaw
    a.emit('lui', 't6', 0x5C); a.emit('lwc1', 'f1', YAWP, 't6'); a.emit('swc1', 'f0', YAWP, 't6')
    a.emit('sub.s', 'f2', 'f0', 'f1')
    lif(a, 'f3', 3.14159265)
    a.emit('c.olt.s', 'f3', 'f2'); a.emit('bc1f', 'W1'); a.emit('nop')
    lif(a, 'f4', 6.2831853); a.emit('sub.s', 'f2', 'f2', 'f4')
    a.label('W1')
    a.emit('neg.s', 'f5', 'f3'); a.emit('c.olt.s', 'f2', 'f5'); a.emit('bc1f', 'W2'); a.emit('nop')
    lif(a, 'f4', 6.2831853); a.emit('add.s', 'f2', 'f2', 'f4')
    a.label('W2')
    pick(a, 'f3', KN, K); a.emit('mul.s', 'f2', 'f2', 'f3')
    pick(a, 'f3', SMAXN, SMAX)
    a.emit('c.olt.s', 'f3', 'f2'); a.emit('bc1f', 'C1'); a.emit('nop'); a.emit('mov.s', 'f2', 'f3')
    a.label('C1')
    a.emit('neg.s', 'f3', 'f3'); a.emit('c.olt.s', 'f2', 'f3'); a.emit('bc1f', 'C2'); a.emit('nop'); a.emit('mov.s', 'f2', 'f3')
    a.label('C2')
    # two glides in a row (D, then S) take the step-to-step noise out of the yaw change
    a.emit('lwc1', 'f1', DD, 't6'); a.emit('sub.s', 'f2', 'f2', 'f1')
    lif(a, 'f3', A1); a.emit('mul.s', 'f2', 'f2', 'f3'); a.emit('add.s', 'f1', 'f1', 'f2'); a.emit('swc1', 'f1', DD, 't6')
    a.emit('lwc1', 'f2', SS, 't6')
    a.emit('mul.s', 'f5', 'f1', 'f1'); a.emit('mul.s', 'f6', 'f2', 'f2'); lif(a, 'f3', A)
    a.emit('c.olt.s', 'f5', 'f6'); a.emit('bc1f', 'RR'); a.emit('nop'); pick(a, 'f3', ARN, AR)         # the tilt is shrinking: the slower return glide
    a.label('RR')
    neutral(a, 'RRN')                                                                              # stick at rest: the glide is 4x faster (capped at 1)
    lif(a, 'f7', 4.0); a.emit('mul.s', 'f3', 'f3', 'f7'); lif(a, 'f7', 1.0); a.emit('c.olt.s', 'f7', 'f3'); a.emit('bc1f', 'RRN'); a.emit('nop'); a.emit('mov.s', 'f3', 'f7')
    a.label('RRN')
    a.emit('sub.s', 'f1', 'f1', 'f2'); a.emit('mul.s', 'f1', 'f1', 'f3'); a.emit('add.s', 'f2', 'f2', 'f1'); a.emit('swc1', 'f2', SS, 't6')
    a.emit('beq', 'zero', 'zero', 'DONE'); a.emit('nop')
    a.label('NOW')
    a.emit('lwc1', 'f0', -0x349C, 't3'); a.emit('lui', 't6', 0x5C); a.emit('swc1', 'f0', YAWP, 't6'); a.emit('sw', 'zero', DD, 't6')
    a.emit('lwc1', 'f1', SS, 't6'); pick(a, 'f3', NOWKN, NOWK)
    neutral(a, 'NWN')                                                                              # stick at rest: the upright correction is 4x faster (1 - 4 (1 - m))
    lif(a, 'f7', 1.0); a.emit('sub.s', 'f8', 'f7', 'f3'); lif(a, 'f3', 4.0); a.emit('mul.s', 'f8', 'f8', 'f3'); a.emit('sub.s', 'f3', 'f7', 'f8')
    a.label('NWN')
    a.emit('mul.s', 'f1', 'f1', 'f3'); a.emit('swc1', 'f1', SS, 't6')      # not walking: the tilt fades out
    a.label('DONE')
    # the model block's roll angle (Euler z, [+0x588]) = the tilt: the game's own matrix rebuild then includes it (a post-rebuild rotation of the matrix
    # rows was overwritten by the game's rebuild every frame)
    a.emit('lui', 't6', 0x5C); a.emit('lwc1', 'f4', SS, 't6')
    a.emit('lui', 't0', 0x3B); a.emit('swc1', 'f4', -0x3498, 't0')                  # model block roll [+0x588]
    a.emit('swc1', 'f4', -0x39D8, 't0')                                             # actor block roll [+0x48]
    a.emit('j', AUTO); a.emit('nop')
    return a
def apply_block(a, br):
    # rotate the right (+0x20) and up (+0x30) rows of the block at register br about its forward row until right.y == f4 (the tilt)
    a.emit('lwc1', 'f5', 0x24, br); a.emit('sub.s', 'f6', 'f4', 'f5')                               # delta = tilt - right.y
    a.emit('mul.s', 'f7', 'f6', 'f6'); lif(a, 'f8', 0.5); a.emit('mul.s', 'f7', 'f7', 'f8'); lif(a, 'f9', 1.0); a.emit('sub.s', 'f7', 'f9', 'f7')   # c = 1 - delta^2 / 2
    for k in range(3):
        r, u = 0x20 + 4 * k, 0x30 + 4 * k
        a.emit('lwc1', 'f0', r, br); a.emit('lwc1', 'f1', u, br)
        a.emit('mul.s', 'f2', 'f0', 'f7'); a.emit('mul.s', 'f3', 'f1', 'f6'); a.emit('add.s', 'f2', 'f2', 'f3')      # right' = right c + up delta
        a.emit('mul.s', 'f3', 'f1', 'f7'); a.emit('mul.s', 'f10', 'f0', 'f6'); a.emit('sub.s', 'f3', 'f3', 'f10')    # up' = up c - right delta
        a.emit('swc1', 'f2', r, br); a.emit('swc1', 'f3', u, br)
SAV = -0x1700                       # 005BE900..: f0..f10 saved around LEAN (it runs inside callers that may keep floats)
def build_lean():
    # hook 0012A680 / 0012A684 (the two ld of the epilogue of FUN_0012A644, the matrix rebuild; s1 = the transform block): after every rebuild of
    # Caim's blocks the tilt is applied again
    a = Asm(LEAN)
    a.emit('lui', 't0', 0x3A); a.emit('ori', 't0', 't0', 0xC610); a.emit('beq', 's1', 't0', 'GO'); a.emit('nop')
    a.emit('lui', 't0', 0x3A); a.emit('ori', 't0', 't0', 0xCB50); a.emit('bne', 's1', 't0', 'OUT'); a.emit('nop')
    a.label('GO')
    a.emit('lui', 't1', 0x5C)
    for k in range(11): a.emit('swc1', 'f%d' % k, SAV + 4 * k, 't1')
    a.emit('lwc1', 'f4', SS, 't1')
    apply_block(a, 's1')
    a.emit('lui', 't1', 0x5C)
    for k in range(11): a.emit('lwc1', 'f%d' % k, SAV + 4 * k, 't1')
    a.label('OUT')
    a.label('RAW1'); a.emit('nop')                                  # the original ld s0,16(sp)
    a.label('RAW2'); a.emit('nop')                                  # the original ld s1,24(sp)
    a.emit('j', 0x12A688); a.emit('nop')
    return a
def patches():
    p = [(TILTF + 4 * i, w) for i, w in enumerate(build_tiltf().assemble())]
    p += [(0x321A74, 0x08000000 | (TILTF >> 2))]
    return p
if __name__ == '__main__':
    for ad, w in patches(): print('patch=1,EE,%08X,word,%08X' % (ad, w))
