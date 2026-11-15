import sys, struct, math
sys.path.insert(0, r'C:\Users\shade\AppData\Local\Temp\claude\C--Users-shade-AppData-Roaming-Claude-scratch-workspaces-d26a4a75-75f2-47d7-a5b0-73edfc757065-46ea55b4-1b40-4e1b-8e0f-1c92210c0291-scratch-2026-10-16-8e6b16\9242a4f5-61eb-4545-89bd-55b3ca05d106\scratchpad')
from mipsasm import Asm, CPU

SP = r'C:\Users\shade\AppData\Local\Temp\claude\C--Users-shade--claude-spares-spare-lRXJwn\fc7fa988-ea8f-4fa2-b5eb-1c7f92e06e80\scratchpad'

RIDE = 0x5B7000
BEH = 0x5B7300
CAM = 0x5B7340
HEIGHT = 0x5B7200
FLAG = 0x5B7F00          # lui 0x5b, offset 0x7F00

def fconst(a, reg, val):
    bits = struct.unpack('<I', struct.pack('<f', val))[0]
    a.emit('lui', 't9', bits >> 16)
    if bits & 0xFFFF:
        a.emit('ori', 't9', 't9', bits & 0xFFFF)
    a.emit('mtc1', 't9', reg)

def build_ride(speed=8.57, down_deg=18.0, max_frames=130.0):
    # Ground stages: the fireball flies straight at constant speed along Angelus' body forward vector (+0x70..+0x78, y positive = down)
    # pitched down by a fixed 18 degrees (measured: level shots drop 0.309 of the speed per frame, shots fired while climbing 14.3 degrees
    # drop 0.067), starts at her mouth point (ext point 0 of the dragon, 0041CF20) and explodes at y >= 0 or after 130 frames.
    import math
    cd = math.cos(math.radians(down_deg)); sd = math.sin(math.radians(down_deg))
    a = Asm(RIDE)
    # t0 = lock bit (andi result) when we arrive from the hooked beq at 003420C8
    # pause menu opening or open (004EE29C != 0): no dot or star at all, so the pause menu text is not cut off
    a.emit('lui', 't1', 0x4F)
    a.emit('lw', 't2', -0x1D64, 't1')            # 004EE29C
    a.emit('bne', 't2', 'zero', 'PAUSED')
    a.emit('nop')
    a.emit('lui', 't1', 0x3B)
    a.emit('lw', 't2', -0x30C0, 't1')          # Angelus +0x20
    a.emit('addiu', 't3', 'zero', 5)
    a.emit('bne', 't2', 't3', 'NOT')
    a.emit('nop')
    a.emit('lw', 't2', -0x2D3C, 't1')          # Angelus +0x3A4
    a.emit('addiu', 't3', 'zero', 2)
    a.emit('bne', 't2', 't3', 'NOT')
    a.emit('nop')
    # Caim must really be mounted: Caim (003AC5E0) +0x6B4 = 2 while riding in every state (1 on foot).
    # (+0x668 is 1 only while the stick is neutral, so it must not be tested.)
    a.emit('lw', 't2', -0x336C, 't1')
    a.emit('addiu', 't3', 'zero', 2)
    a.emit('bne', 't2', 't3', 'NOT')
    a.emit('nop')
    # levels only: the actors keep their riding state after the stage ends, so require the title, chapter map,
    # result, title call and weapon select tasks to be inactive (state word nonzero), like the HUD cave
    for hi, lo in ((0x3C, -0x6890), (0x3C, -0x6750), (0x3C, -0x6C48), (0x3C, -0x69C0), (0x34, 0x2E38)):
        a.emit('lui', 't2', hi)
        a.emit('lw', 't3', lo, 't2')
        a.emit('beq', 't3', 'zero', 'NOT')
        a.emit('nop')
    # wait until the screen fade is fully clear: CFadeMan (004861A8) fader value at +0x124 (004862CC), 0 = no darkening
    a.emit('lui', 't2', 0x48)
    a.emit('lw', 't3', 0x62CC, 't2')
    a.emit('bne', 't3', 'zero', 'NOT')
    a.emit('nop')
    a.emit('addiu', 't1', 't1', -0x30E0)       # t1 = Angelus actor 003ACF20
    a.emit('lui', 't2', 0x42)
    a.emit('lwc1', 'f10', -0x30E0, 't2')       # mouth x (0041CF20)
    a.emit('lwc1', 'f1', -0x30DC, 't2')        # mouth y
    a.emit('lwc1', 'f11', -0x30D8, 't2')       # mouth z
    a.emit('lwc1', 'f3', 0x70, 't1')           # forward x
    a.emit('lwc1', 'f12', 0x74, 't1')          # forward y
    a.emit('lwc1', 'f13', 0x78, 't1')          # forward z
    a.emit('mul.s', 'f4', 'f3', 'f3')
    a.emit('mul.s', 'f5', 'f13', 'f13')
    a.emit('add.s', 'f4', 'f4', 'f5')
    a.emit('sqrt.s', 'f4', 'f4')               # cos(pitch) = horizontal length of the forward vector
    fconst(a, 'f14', 0.1)
    a.emit('c.olt.s', 'f4', 'f14')
    a.emit('bc1f', 'CP')
    a.emit('nop')
    a.emit('mov.s', 'f4', 'f14')
    a.label('CP')
    fconst(a, 'f5', cd)
    fconst(a, 'f6', sd)
    fconst(a, 'f7', speed)
    a.emit('mul.s', 'f8', 'f12', 'f6')
    a.emit('div.s', 'f8', 'f8', 'f4')
    a.emit('sub.s', 'f8', 'f5', 'f8')
    a.emit('mul.s', 'f8', 'f8', 'f7')          # horizontal factor = speed * (cos d - fy sin d / cos p)
    a.emit('mul.s', 'f3', 'f3', 'f8')          # dx per frame
    a.emit('mul.s', 'f13', 'f13', 'f8')        # dz per frame
    a.emit('mul.s', 'f9', 'f12', 'f5')
    a.emit('mul.s', 'f14', 'f4', 'f6')
    a.emit('add.s', 'f9', 'f9', 'f14')
    a.emit('mul.s', 'f9', 'f9', 'f7')          # dy per frame = speed * (fy cos d + cos p sin d)
    a.emit('mtc1', 'zero', 'f2')
    a.emit('sub.s', 'f4', 'f2', 'f1')          # height above the ground (0 - y)
    a.emit('c.olt.s', 'f4', 'f2')
    a.emit('bc1f', 'HP')
    a.emit('nop')
    a.emit('mov.s', 'f4', 'f2')
    a.label('HP')
    fconst(a, 'f15', max_frames)
    fconst(a, 'f14', 0.05)
    a.emit('c.olt.s', 'f9', 'f14')
    a.emit('bc1t', 'NG')
    a.emit('nop')
    a.emit('div.s', 'f4', 'f4', 'f9')          # frames to the ground
    a.emit('c.olt.s', 'f15', 'f4')
    a.emit('bc1f', 'OK')
    a.emit('nop')
    a.label('NG')
    a.emit('mov.s', 'f4', 'f15')               # not going down or too far: the fireball dies after 130 frames
    a.label('OK')
    a.emit('mul.s', 'f3', 'f3', 'f4')
    a.emit('add.s', 'f10', 'f10', 'f3')
    a.emit('mul.s', 'f13', 'f13', 'f4')
    a.emit('add.s', 'f11', 'f11', 'f13')
    a.emit('mul.s', 'f9', 'f9', 'f4')
    a.emit('add.s', 'f1', 'f1', 'f9')
    # DOT's projection (from 00342120) wants f2/f3/f4 = target x / y (minus the 10 unit lift) / z and t0 = camera object.
    # While riding the camera object 003ADAC0 only holds the field of view (identity matrix); the live matrix and position are at 003AD4F0 (+0x50 right, +0x60 down, +0x70 forward, +0x80 position).
    a.emit('mov.s', 'f2', 'f10')
    a.emit('mov.s', 'f4', 'f11')
    fconst(a, 'f14', 10.0)
    a.emit('sub.s', 'f3', 'f1', 'f14')
    a.emit('lui', 't1', 0x5B)
    a.emit('addiu', 't2', 'zero', 1)
    a.emit('sw', 't2', 0x7F00, 't1')
    a.emit('lui', 't0', 0x3A)
    a.emit('ori', 't0', 't0', 0xD4F0)
    a.emit('j', 0x342120)
    a.emit('nop')
    a.label('NOT')
    a.emit('lui', 't1', 0x5B)
    a.emit('sw', 'zero', 0x7F00, 't1')
    a.emit('bne', 't0', 'zero', 'LOCKED')
    a.emit('nop')
    a.emit('j', 0x34253C)
    a.emit('nop')
    a.label('LOCKED')
    a.emit('j', 0x3420D0)
    a.emit('nop')
    a.label('PAUSED')
    a.emit('lui', 't1', 0x5B)
    a.emit('sw', 'zero', 0x7F00, 't1')
    a.emit('j', 0x34253C)
    a.emit('nop')
    return a
def build_beh():
    a = Asm(BEH)
    a.emit('lui', 't0', 0x5B)
    a.emit('lw', 't0', 0x7F00, 't0')
    a.emit('beq', 't0', 'zero', 'B1')
    a.emit('nop')
    a.emit('j', 0x342544)
    a.emit('nop')
    a.label('B1')
    a.emit('lui', 't9', 0x3DA3)
    a.emit('ori', 't9', 't9', 0xD70A)
    a.emit('j', 0x3421B4)
    a.emit('nop')
    return a

def build_cam():
    a = Asm(CAM)
    a.emit('lui', 't0', 0x5B)
    a.emit('lw', 't0', 0x7F00, 't0')
    a.emit('bne', 't0', 'zero', 'SK')
    a.emit('nop')
    a.emit('lui', 't9', 0x3B0A)
    a.emit('ori', 't9', 't9', 0x1DAC)
    a.emit('j', 0x3423CC)
    a.emit('nop')
    a.label('SK')
    a.emit('j', 0x34246C)
    a.emit('nop')
    return a

def height_words():
    words = []
    for line in open(SP + r'\terc_words.txt'):
        p = line.split()
        ad = int(p[0], 16)
        if 0x5B6524 <= ad <= 0x5B6668:
            words.append(int(p[1], 16))
    assert len(words) == (0x5B6668 - 0x5B6524) // 4 + 1, len(words)
    return words

HOOKS = {
    0x3420C8: 0x08000000 | (RIDE >> 2),
    0x3421AC: 0x08000000 | (BEH >> 2),
    0x3423C4: 0x08000000 | (CAM >> 2),
}

def all_patches():
    out = []
    for a in (build_ride(), build_beh(), build_cam()):
        for i, w in enumerate(a.assemble()):
            out.append((a.base + 4 * i, w))
    for ad, w in HOOKS.items():
        out.append((ad, w))
    return out


# ---------------------------------------------------------------- star reticle (second GIF packet)
SEL = 0x5B7400
TAG = 0x5B7480
UND = 0x5B74C0
PK2 = 0x5A0600       # copy of the dot packet 005A0000 (0x2E0 bytes)
TB2 = 0x5A0900       # star offset tables: layer 1 at TB2, layer 2 at TB2 + 0x80

def star_tables():
    import math
    def poly(rt, ri, down=1.2):
        pts = []
        def P(r, deg, k=1.0):
            a = math.radians(deg)
            return (int(round(r * k * math.cos(a))), int(round(r * k * math.sin(a))))
        tip90 = P(rt, 90, down)
        seq = [tip90, P(ri, 150), P(rt, 210), P(ri, 270), P(rt, 330), P(ri, 30), tip90]
        v = [(0, 0)] + seq
        while len(v) < 18:
            v.append(tip90)
        return v
    def pack(v):
        return [(((y << 16) + x) & 0xFFFFFFFF) for (x, y) in v]
    outline = pack(poly(14.5 * 16, 3.8 * 16, 1.25))
    fill = pack(poly(11.5 * 16, 1.9 * 16, 1.25))
    return outline, fill

def build_sel():
    a = Asm(SEL)
    a.emit('lui', 't0', 0x5B)
    a.emit('lw', 't0', 0x7F00, 't0')
    a.emit('bne', 't0', 'zero', 'STAR')
    a.emit('nop')
    a.emit('ori', 't8', 't8', 0x400)
    a.emit('lui', 't3', 0x5A)
    a.emit('ori', 't3', 't3', 0x70)
    a.emit('lui', 't2', 0x5A)
    a.emit('ori', 't2', 't2', 0x1B0)
    a.emit('j', 0x3424CC)
    a.emit('nop')
    a.label('STAR')
    a.emit('ori', 't8', 't8', TB2 & 0xFFFF)
    a.emit('lui', 't3', 0x5A)
    a.emit('ori', 't3', 't3', (PK2 + 0x70) & 0xFFFF)
    a.emit('lui', 't2', 0x5A)
    a.emit('ori', 't2', 't2', (PK2 + 0x1B0) & 0xFFFF)
    a.emit('j', 0x3424CC)
    a.emit('nop')
    return a

def build_tag():
    a = Asm(TAG)
    a.emit('lui', 't7', 0x5A)
    a.emit('lui', 't0', 0x5B)
    a.emit('lw', 't0', 0x7F00, 't0')
    a.emit('beq', 't0', 'zero', 'T1')
    a.emit('nop')
    a.emit('ori', 't7', 't7', PK2 & 0xFFFF)
    a.label('T1')
    a.emit('j', 0x342520)
    a.emit('nop')
    return a

def build_und():
    a = Asm(UND)
    a.emit('lui', 't9', 0xFFFF)
    a.emit('ori', 't9', 't9', (0xFFFF & ~(PK2 & 0xFFFF)))
    a.emit('and', 't7', 't7', 't9')
    a.emit('bne', 't7', 't8', 'OUT')
    a.emit('nop')
    a.emit('j', 0x342568)
    a.emit('nop')
    a.label('OUT')
    a.emit('j', 0x342574)
    a.emit('nop')
    return a

HOOKS2 = {
    0x3424B8: 0x08000000 | (SEL >> 2),
    0x34251C: 0x08000000 | (TAG >> 2),
    0x342560: 0x08000000 | (UND >> 2),
}

def star_packet_words(state='rt7'):
    data = open(r'%s\%s\eeMemory.bin' % (SP, state), 'rb').read()
    out = []
    for off in range(0, 0x2E0, 4):
        w = struct.unpack_from('<I', data, 0x5A0000 + off)[0]
        out.append((PK2 + off, w))
    d = dict(out)
    # colours: RGBAQ words of the two layers (dark outline, red fill), A = 0x80
    d[PK2 + 0x60] = 0x80000000
    d[PK2 + 0x1A0] = 0x802030F0
    # the first word of every vertex qword is written by DOT every frame (position); a patch line there would overwrite
    # it with the stale value (the dot packet's own patch lines skip them too)
    for i in range(18):
        d.pop(PK2 + 0x70 + 16 * i, None)
        d.pop(PK2 + 0x1B0 + 16 * i, None)
    return sorted(d.items())

def star_patches():
    out = []
    for ad, w in star_packet_words():
        if w:
            out.append((ad, w))
    o, f = star_tables()
    for i, w in enumerate(o):
        if w: out.append((TB2 + 4 * i, w))
    for i, w in enumerate(f):
        if w: out.append((TB2 + 0x80 + 4 * i, w))
    for a in (build_sel(), build_tag(), build_und()):
        for i, w in enumerate(a.assemble()):
            out.append((a.base + 4 * i, w))
    for ad, w in HOOKS2.items():
        out.append((ad, w))
    return out
if __name__ == '__main__':
    for ad, w in all_patches() + star_patches():
        print('%08X %08X' % (ad, w))
