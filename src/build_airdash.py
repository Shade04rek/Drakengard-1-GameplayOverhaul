import sys, struct
sys.path.insert(0, r'C:\Users\shade\AppData\Local\Temp\claude\C--Users-shade-AppData-Roaming-Claude-scratch-workspaces-d26a4a75-75f2-47d7-a5b0-73edfc757065-46ea55b4-1b40-4e1b-8e0f-1c92210c0291-scratch-2026-10-16-8e6b16\9242a4f5-61eb-4545-89bd-55b3ca05d106\scratchpad')
from mipsasm import Asm
AD = 0x5B7900
PREV, USED, DASHON, LASTY = 0x7AF0, 0x7AF4, 0x7AF8, 0x7AFC   # words 005B7AF0.. (lui 0x5B)
DLAND = 0x7AEC                         # 1 after a dash until the landing (or the next takeoff)
LANDC = 0x5B7B20                       # first ground frame after a dash: locomotion animation at once
STANDB = 0x5B2700
SPRINT = 1.9                           # normal sprint speed in air units (run 1.38 * 1.37)
SPEED_MUL = 2.0                        # dash speed = max(air speed, sprint) * 2  (100 % faster)
FALL_KEEP = 0.5                        # share of the downward movement kept while the dash slash plays
DJ2 = 0x342BE0
def fbits(x): return struct.unpack('<I', struct.pack('<f', x))[0]
def lif(a, f, x):
    b = fbits(x); a.emit('lui', 't9', b >> 16)
    if b & 0xFFFF: a.emit('ori', 't9', 't9', b & 0xFFFF)
    a.emit('mtc1', 't9', f)
def build():
    a = Asm(AD)
    a.emit('lui', 't0', 0x57)
    a.emit('lbu', 't1', -0x327E, 't0')         # pad byte 0056CD82, L3 = bit 1, active low
    a.emit('andi', 't1', 't1', 2)
    a.emit('xori', 't1', 't1', 2)              # 2 = L3 held
    a.emit('lui', 't0', 0x5B)
    a.emit('lw', 't2', PREV, 't0'); a.emit('sw', 't1', PREV, 't0')
    a.emit('bne', 'v1', 'zero', 'AIR'); a.emit('nop')
    a.emit('sw', 'zero', USED, 't0')           # takeoff frame (phase 0): one dash per jump
    a.emit('sw', 'zero', DASHON, 't0')
    a.emit('sw', 'zero', DLAND, 't0')
    a.emit('j', DJ2); a.emit('nop')
    a.label('AIR')
    a.emit('sltiu', 't3', 'v1', 3); a.emit('bne', 't3', 'zero', 'FLY'); a.emit('nop')
    a.emit('sw', 'zero', DASHON, 't0')         # landing phases: dash over
    a.emit('j', DJ2); a.emit('nop')
    a.label('FLY')
    # touchdown after a dash: the flight phase waits for the slash animation, so it kept Caim in the jump state on the
    # ground. From the 3rd frame after the dash, y (+0x84, down) within 1 of the ground height (+0x650) ends the jump:
    # phase 6 makes FUN_00174FC0 return 1 (finished) at once; LANDC then starts the run / idle animation.
    a.emit('lw', 't3', DLAND, 't0'); a.emit('beq', 't3', 'zero', 'NOTD'); a.emit('nop')
    a.emit('addiu', 't3', 't3', 1); a.emit('sw', 't3', DLAND, 't0')
    a.emit('sltiu', 't4', 't3', 4); a.emit('bne', 't4', 'zero', 'NOTD'); a.emit('nop')
    a.emit('lwc1', 'f4', 0x84, 's1'); a.emit('lwc1', 'f5', 0x650, 's1')
    lif(a, 'f6', 1.0); a.emit('sub.s', 'f5', 'f5', 'f6')
    a.emit('c.olt.s', 'f4', 'f5'); a.emit('bc1t', 'NOTD'); a.emit('nop')          # still above the ground
    a.emit('sw', 'zero', DASHON, 't0')
    a.emit('j', DJ2); a.emit('addiu', 'v1', 'zero', 6)
    a.label('NOTD')
    # slower fall while the dash slash plays (clip +0x120 == 0xAA, progress +0x122 < 0x1000; the first 3 frames always)
    a.emit('lw', 't3', DASHON, 't0'); a.emit('beq', 't3', 'zero', 'NOFALL'); a.emit('nop')
    a.emit('addiu', 't3', 't3', 1); a.emit('sw', 't3', DASHON, 't0')
    a.emit('sltiu', 't4', 't3', 5); a.emit('bne', 't4', 'zero', 'SLOW'); a.emit('nop')
    a.emit('lhu', 't4', 0x120, 's1'); a.emit('xori', 't4', 't4', 0xAA); a.emit('bne', 't4', 'zero', 'ENDD'); a.emit('nop')
    a.emit('lhu', 't4', 0x122, 's1'); a.emit('sltiu', 't4', 't4', 0x1000); a.emit('beq', 't4', 'zero', 'ENDD'); a.emit('nop')
    a.label('SLOW')
    a.emit('lwc1', 'f4', 0x84, 's1'); a.emit('lwc1', 'f5', LASTY, 't0')
    a.emit('sub.s', 'f6', 'f4', 'f5')          # y change since last frame (y grows downward)
    a.emit('mtc1', 'zero', 'f7'); a.emit('c.olt.s', 'f7', 'f6'); a.emit('bc1f', 'SKIPF'); a.emit('nop')
    lif(a, 'f7', 1.0 - FALL_KEEP); a.emit('mul.s', 'f6', 'f6', 'f7'); a.emit('sub.s', 'f4', 'f4', 'f6')
    a.emit('swc1', 'f4', 0x84, 's1')
    a.label('SKIPF')
    a.emit('swc1', 'f4', LASTY, 't0')
    a.emit('beq', 'zero', 'zero', 'NOFALL'); a.emit('nop')
    a.label('ENDD')
    a.emit('sw', 'zero', DASHON, 't0')
    a.label('NOFALL')
    a.emit('beq', 't1', 'zero', 'OUT'); a.emit('nop')
    a.emit('bne', 't2', 'zero', 'OUT'); a.emit('nop')                                   # new press only
    a.emit('lw', 't3', USED, 't0'); a.emit('bne', 't3', 'zero', 'OUT'); a.emit('nop')
    a.emit('ori', 't3', 'zero', 1); a.emit('sw', 't3', USED, 't0'); a.emit('sw', 't3', DASHON, 't0'); a.emit('sw', 't3', DLAND, 't0')
    a.emit('lw', 't3', 0x84, 's1'); a.emit('sw', 't3', LASTY, 't0')
    a.emit('addiu', 't3', 'zero', 0xEE); a.emit('sw', 't3', 0x560, 's1')               # wind burst slot
    a.emit('sw', 'zero', 0x564, 's1')
    a.emit('lui', 't3', 0x34); a.emit('ori', 't4', 'zero', 1)
    a.emit('sw', 't4', -0x1204, 't3')          # 0033EDFC: landing with the stick forward resumes the sprint (AUTOC)
    a.emit('daddu', 'a0', 's1', 'zero')
    a.emit('jal', 0x1767A8)                    # air slash (animation 0xAA), as TRC does it
    a.emit('addiu', 'a1', 'zero', 1)
    a.emit('addiu', 't2', 'zero', 1); a.emit('sw', 't2', 0x660, 's1')                  # jump type 1
    a.emit('lui', 't0', 0x34); a.emit('lwc1', 'f1', -0x1258, 't0')                     # AIRGS 0033EDA8
    lif(a, 'f2', SPRINT)
    a.emit('c.olt.s', 'f1', 'f2'); a.emit('bc1f', 'KEEP'); a.emit('nop')
    a.emit('mov.s', 'f1', 'f2')
    a.label('KEEP')
    lif(a, 'f2', SPEED_MUL); a.emit('mul.s', 'f1', 'f1', 'f2')
    a.emit('swc1', 'f1', -0x1258, 't0')
    a.emit('lwc1', 'f2', 0x5B0, 's1'); a.emit('lwc1', 'f3', 0x5B8, 's1')               # facing (forward x, z)
    a.emit('mul.s', 'f4', 'f2', 'f2'); a.emit('mul.s', 'f5', 'f3', 'f3')
    a.emit('add.s', 'f4', 'f4', 'f5'); a.emit('sqrt.s', 'f4', 'f4')
    a.emit('div.s', 'f1', 'f1', 'f4')
    a.emit('mul.s', 'f2', 'f2', 'f1'); a.emit('mul.s', 'f3', 'f3', 'f1')
    a.emit('swc1', 'f2', 0x300, 's1'); a.emit('swc1', 'f3', 0x308, 's1')               # momentum
    a.emit('lw', 'v1', 0x2EC, 's1')                                                    # v1 for DJ2 (jal clobbered it)
    a.label('OUT')
    a.emit('j', DJ2); a.emit('nop')
    return a
PRE = 0x5B7BA0                         # in front of AD: R1 after a dash, halved speed after the 2nd R2 slash
SAVGS, SAVMX, SAVMZ, HREF = 0x7CF0, 0x7CF4, 0x7CF8, 0x7CFC
SLOW_LIMIT = 1.85                      # air speed below this after the slowdown = no sprint on landing (sprint start ~1.89)
def build_pre():
    a = Asm(PRE)
    a.emit('lui', 't0', 0x5B)
    a.emit('beq', 'v1', 'zero', 'TOAD'); a.emit('nop')          # takeoff frame: leave everything to AD
    # --- R1 double jump attack after a dash: cancel the dash, put the speed back
    a.emit('lw', 't1', DLAND, 't0'); a.emit('bne', 't1', 'zero', 'DASHED'); a.emit('nop')
    a.emit('lui', 't2', 0x34); a.emit('lw', 't3', -0x1258, 't2'); a.emit('sw', 't3', SAVGS, 't0')   # pre-dash air speed
    a.emit('lw', 't3', 0x300, 's1'); a.emit('sw', 't3', SAVMX, 't0')
    a.emit('lw', 't3', 0x308, 's1'); a.emit('sw', 't3', SAVMZ, 't0')
    a.emit('beq', 'zero', 'zero', 'HALF'); a.emit('nop')
    a.label('DASHED')
    a.emit('lui', 't2', 0x14); a.emit('lw', 't2', -0x1AD0, 't2')  # 0013E530 = 0x800 after the R1 double jump
    a.emit('addiu', 't3', 'zero', 0x800); a.emit('bne', 't2', 't3', 'HALF'); a.emit('nop')
    a.emit('sw', 'zero', DLAND, 't0'); a.emit('sw', 'zero', DASHON, 't0')
    a.emit('lw', 't1', SAVGS, 't0'); a.emit('lui', 't2', 0x34); a.emit('sw', 't1', -0x1258, 't2')
    a.emit('sw', 'zero', -0x1204, 't2')                          # no sprint resume on that landing
    a.emit('lw', 't1', SAVMX, 't0'); a.emit('sw', 't1', 0x300, 's1')
    a.emit('lw', 't1', SAVMZ, 't0'); a.emit('sw', 't1', 0x308, 's1')
    a.label('HALF')
    # --- after the 2nd R2 slash (0033F6DC != 0 until the next takeoff): air speed and momentum at half, also any later raise
    a.emit('lui', 't2', 0x34); a.emit('lw', 't1', -0x924, 't2')
    a.emit('bne', 't1', 'zero', 'HON'); a.emit('nop')
    a.emit('sw', 'zero', HREF, 't0'); a.emit('beq', 'zero', 'zero', 'TOAD'); a.emit('nop')
    a.label('HON')
    a.emit('lwc1', 'f1', -0x1258, 't2')                         # AIRGS
    a.emit('lwc1', 'f2', HREF, 't0')
    lif(a, 'f3', 1.01); a.emit('mul.s', 'f2', 'f2', 'f3')
    a.emit('lw', 't1', HREF, 't0'); a.emit('beq', 't1', 'zero', 'DOH'); a.emit('nop')
    a.emit('c.olt.s', 'f2', 'f1'); a.emit('bc1f', 'SPR'); a.emit('nop')    # not raised since the last halving
    a.label('DOH')
    lif(a, 'f3', 0.5)
    a.emit('mul.s', 'f1', 'f1', 'f3'); a.emit('swc1', 'f1', -0x1258, 't2'); a.emit('swc1', 'f1', HREF, 't0')
    a.emit('lwc1', 'f2', 0x300, 's1'); a.emit('mul.s', 'f2', 'f2', 'f3'); a.emit('swc1', 'f2', 0x300, 's1')
    a.emit('lwc1', 'f2', 0x308, 's1'); a.emit('mul.s', 'f2', 'f2', 'f3'); a.emit('swc1', 'f2', 0x308, 's1')
    # slowed in the air: below normal sprint speed the sprint ends (latch 002F345C and the resume flag 0033EDFC cleared,
    # L3 has to be pressed again); at sprint speed or more it continues but the super sprint count 005B1F00 restarts
    a.label('SPR')
    a.emit('lwc1', 'f1', -0x1258, 't2')
    lif(a, 'f3', SLOW_LIMIT); a.emit('c.olt.s', 'f1', 'f3'); a.emit('bc1f', 'FAST'); a.emit('nop')
    a.emit('lui', 't3', 0x2F); a.emit('sw', 'zero', 0x345C, 't3'); a.emit('sw', 'zero', -0x1204, 't2')
    a.emit('beq', 'zero', 'zero', 'TOAD'); a.emit('nop')
    a.label('FAST')
    a.emit('lui', 't3', 0x5B); a.emit('sw', 'zero', 0x1F00, 't3')
    a.label('TOAD')
    a.emit('j', AD); a.emit('nop')
    return a
def build_land():
    # hook 001737C0 (jal STANDB, right after the mode machine stored the new mode; s0 = Caim) -> LANDC -> j STANDB
    a = Asm(LANDC)
    a.emit('lui', 't0', 0x5B); a.emit('lw', 't1', DLAND, 't0')
    a.emit('beq', 't1', 'zero', 'GO'); a.emit('nop')
    a.emit('lw', 't1', 0x2DC, 's0'); a.emit('addiu', 't2', 'zero', 2)
    a.emit('bne', 't1', 't2', 'GO'); a.emit('nop')                    # only once he is in the ground mode
    a.emit('sw', 'zero', DLAND, 't0')
    a.emit('lh', 't1', 0x67E, 's0'); a.emit('lh', 't2', 0x67C, 's0')  # stick y / x in Caim's frame
    a.emit('addiu', 't1', 't1', 0x400); a.emit('sltiu', 't1', 't1', 0x800)
    a.emit('addiu', 't2', 't2', 0x400); a.emit('sltiu', 't2', 't2', 0x800)
    a.emit('and', 't1', 't1', 't2')                                   # 1 = stick at rest
    a.emit('addiu', 't3', 'zero', 0x2C)                               # run
    a.emit('beq', 't1', 'zero', 'REQ'); a.emit('nop')
    a.emit('addiu', 't3', 'zero', 0x21)                               # idle
    a.label('REQ')
    a.emit('addiu', 't2', 'zero', 1); a.emit('sh', 't2', 0x170, 's0')  # request type 1
    a.emit('sh', 't3', 0x172, 's0')                                   # animation id
    a.emit('addiu', 't2', 'zero', 0x1000); a.emit('sh', 't2', 0x174, 's0')  # rate 1.0
    a.emit('sh', 'zero', 0x176, 's0'); a.emit('sh', 'zero', 0x178, 's0'); a.emit('sh', 'zero', 0x17A, 's0')
    a.label('GO')
    a.emit('j', STANDB); a.emit('nop')
    return a
if __name__ == '__main__':
    a = build()
    for i, w in enumerate(a.assemble()): print('patch=1,EE,%08X,word,%08X' % (AD + 4 * i, w))
    p = build_pre()
    for i, w in enumerate(p.assemble()): print('patch=1,EE,%08X,word,%08X' % (PRE + 4 * i, w))
    print('patch=1,EE,0033ED38,word,%08X' % (0x08000000 | (PRE >> 2)))
    l = build_land()
    for i, w in enumerate(l.assemble()): print('patch=1,EE,%08X,word,%08X' % (LANDC + 4 * i, w))
    print('patch=1,EE,001737C0,word,%08X' % (0x0C000000 | (LANDC >> 2)))
