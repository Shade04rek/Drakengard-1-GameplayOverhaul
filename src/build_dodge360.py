import sys, struct, math
sys.path.insert(0, r'C:\Users\shade\AppData\Local\Temp\claude\C--Users-shade-AppData-Roaming-Claude-scratch-workspaces-d26a4a75-75f2-47d7-a5b0-73edfc757065-46ea55b4-1b40-4e1b-8e0f-1c92210c0291-scratch-2026-10-16-8e6b16\9242a4f5-61eb-4545-89bd-55b3ca05d106\scratchpad')
from mipsasm import Asm
# Version 3 (camera relative): at the roll start Caim is turned to face the camera's forward direction; the roll moves
# along the stick direction in the world; the L1 roll plays when that direction is on the camera's left (and with no
# stick, which rolls straight back), the R1 roll when it is on the camera's right. Like the vanilla rolls he ends
# facing forward (now: the camera's forward).
DG = 0x5AF400
SR = 0x5AF800
MV = 0x5AF500
RT = 0x5B7740
DPREV, DPEND = -0x0810, -0x080C          # 005AF7F0 / F4 (lui 0x5B)
DMV = -0x0808                             # 005AF7F8: 1 = override the movement of the roll that is starting
DDX, DDZ = -0x0820, -0x081C               # 005AF7E0 / E4: unit movement direction (world x, z)
L1_VALUE = 0x0FF0                         # +0x690 that plays the L1 roll (user test: 0xF010 plays R1)
R1_VALUE = 0xF010
CAIM = 0x3AC5E0
CAM = 0x3AD4F0                            # live camera block: +0x44 yaw (003AD534), +0x70 forward (003AD560 / 568)
def build():
    a = Asm(DG)
    # pad update, ground (aerial marker 0): mark the first frame of a Square (0x8000) / Circle (0x2000) press
    a.emit('lui', 't9', 0x3B); a.emit('lw', 't8', -0x30C0, 't9'); a.emit('addiu', 't7', 'zero', 5)
    a.emit('beq', 't8', 't7', 'GORT'); a.emit('nop')                 # riding Angelus: not Caim
    a.emit('lw', 't7', 0x2898, 't5'); a.emit('andi', 't7', 't7', 0xA000)
    a.emit('lui', 't9', 0x5B); a.emit('lw', 't8', DPREV, 't9'); a.emit('sw', 't7', DPREV, 't9')
    a.emit('bne', 't7', 'zero', 'HELD'); a.emit('nop')
    a.emit('sw', 'zero', DPEND, 't9')                                 # released: nothing pending
    a.emit('beq', 'zero', 'zero', 'GORT'); a.emit('nop')
    a.label('HELD')
    a.emit('bne', 't8', 'zero', 'GORT'); a.emit('nop')
    a.emit('ori', 't6', 'zero', 1); a.emit('sw', 't6', DPEND, 't9')
    a.label('GORT')
    a.emit('j', RT); a.emit('nop')
    return a
def build_sr():
    # roll mode FUN_00173E38, 00173E98 (lhu v1,0x690(s3)) -> j SR (addiu s1 runs in the delay slot); s3 = Caim
    a = Asm(SR)
    a.emit('beq', 'a1', 'zero', 'PLAIN'); a.emit('nop')
    a.emit('lui', 't9', 0x5B); a.emit('lw', 't0', DPEND, 't9'); a.emit('beq', 't0', 'zero', 'PLAIN'); a.emit('nop')
    a.emit('sw', 'zero', DPEND, 't9')
    a.emit('lui', 't8', CAM >> 16); a.emit('ori', 't8', 't8', CAM & 0xFFFF)
    a.emit('lwc1', 'f5', 0x70, 't8'); a.emit('lwc1', 'f6', 0x78, 't8')   # camera forward x, z
    # stick direction in the world from Caim's axes (before the turn)
    a.emit('lh', 't0', 0x67C, 's3'); a.emit('lh', 't1', 0x67E, 's3')
    a.emit('sra', 't2', 't0', 31); a.emit('xor', 't3', 't0', 't2'); a.emit('subu', 't3', 't3', 't2')
    a.emit('sra', 't2', 't1', 31); a.emit('xor', 't4', 't1', 't2'); a.emit('subu', 't4', 't4', 't2')
    a.emit('addu', 't3', 't3', 't4'); a.emit('slti', 't3', 't3', 0x400)
    a.emit('beq', 't3', 'zero', 'STK'); a.emit('nop')
    a.emit('neg.s', 'f7', 'f5'); a.emit('neg.s', 'f9', 'f6')        # no stick: straight back from the camera
    a.emit('beq', 'zero', 'zero', 'NORM'); a.emit('nop')
    a.label('STK')
    a.emit('mtc1', 't0', 'f1'); a.emit('cvt.s.w', 'f1', 'f1')
    a.emit('mtc1', 't1', 'f2'); a.emit('cvt.s.w', 'f2', 'f2')
    a.emit('lwc1', 'f3', 0x590, 's3'); a.emit('lwc1', 'f4', 0x598, 's3')          # right axis x, z
    a.emit('lwc1', 'f10', 0x5B0, 's3'); a.emit('lwc1', 'f11', 0x5B8, 's3')        # forward axis x, z
    a.emit('mul.s', 'f7', 'f1', 'f3'); a.emit('mul.s', 'f8', 'f2', 'f10'); a.emit('sub.s', 'f7', 'f7', 'f8')
    a.emit('mul.s', 'f9', 'f1', 'f4'); a.emit('mul.s', 'f8', 'f2', 'f11'); a.emit('sub.s', 'f9', 'f9', 'f8')
    a.label('NORM')
    a.emit('mul.s', 'f10', 'f7', 'f7'); a.emit('mul.s', 'f11', 'f9', 'f9'); a.emit('add.s', 'f10', 'f10', 'f11')
    a.emit('sqrt.s', 'f10', 'f10')
    a.emit('div.s', 'f7', 'f7', 'f10'); a.emit('div.s', 'f9', 'f9', 'f10')
    a.emit('swc1', 'f7', DDX, 't9'); a.emit('swc1', 'f9', DDZ, 't9')
    # side relative to the camera: camera right = (fz, -fx); dot > 0 = right -> R1, else L1
    a.emit('mul.s', 'f1', 'f7', 'f6'); a.emit('mul.s', 'f2', 'f9', 'f5'); a.emit('sub.s', 'f1', 'f1', 'f2')
    a.emit('ori', 't0', 'zero', L1_VALUE)
    a.emit('mtc1', 'zero', 'f2'); a.emit('c.olt.s', 'f2', 'f1'); a.emit('bc1f', 'SETS'); a.emit('nop')
    a.emit('ori', 't0', 'zero', R1_VALUE)
    a.label('SETS')
    a.emit('sh', 't0', 0x690, 's3')
    # face the camera's forward direction: yaw = live camera yaw; the roll rebuilds the matrix (00173F04)
    a.emit('lwc1', 'f1', 0x44, 't8')
    a.emit('swc1', 'f1', 0x44, 's3'); a.emit('swc1', 'f1', 0x584, 's3'); a.emit('sw', 'zero', 0x204, 's3')
    a.emit('lw', 't6', 0x570, 's3'); a.emit('ori', 't6', 't6', 2); a.emit('sw', 't6', 0x570, 's3')
    a.emit('ori', 't0', 'zero', 1); a.emit('sw', 't0', DMV, 't9')
    a.label('PLAIN')
    a.emit('lhu', 'v1', 0x690, 's3')
    a.emit('j', 0x173EA0); a.emit('nop')
    return a
def build_mv():
    # 00173F50 (swc1 f0,0x8(s0)) -> j MV, lh v0,0x690(s3) runs in the delay slot; s0 = Caim +0x300 (roll movement)
    a = Asm(MV)
    a.emit('swc1', 'f0', 0x8, 's0')
    a.emit('lui', 't9', 0x5B); a.emit('lw', 't0', DMV, 't9')
    a.emit('bne', 't0', 'zero', 'ARM'); a.emit('nop')
    a.emit('j', 0x173F58); a.emit('nop')
    a.label('ARM')
    a.emit('sw', 'zero', DMV, 't9')
    a.emit('lwc1', 'f7', DDX, 't9'); a.emit('lwc1', 'f9', DDZ, 't9')
    a.emit('swc1', 'f7', 0x0, 's0'); a.emit('mtc1', 'zero', 'f8'); a.emit('swc1', 'f8', 0x4, 's0'); a.emit('swc1', 'f9', 0x8, 's0')
    a.emit('lw', 'v0', 0, 's1')
    a.emit('j', 0x173F74); a.emit('nop')
    return a
def patches():
    p = [(DG + 4 * i, w) for i, w in enumerate(build().assemble())]
    p += [(SR + 4 * i, w) for i, w in enumerate(build_sr().assemble())]
    p += [(MV + 4 * i, w) for i, w in enumerate(build_mv().assemble())]
    p += [(0x3409F4, 0x08000000 | (DG >> 2)), (0x173E98, 0x08000000 | (SR >> 2)), (0x173F50, 0x08000000 | (MV >> 2))]
    return p
if __name__ == '__main__':
    for ad, w in patches(): print('patch=1,EE,%08X,word,%08X' % (ad, w))
