"""Clean widescreen HUD for the 2D DMA chain layer 0x9A (screen-fixed HUD only).

Every HUD packet is squeezed by 3/4 about the screen centre and then moved 80 px toward its corner:
compass (+80, top right), kill counter (+80, bottom right), gauge and dialogue box (-80, left).
The layer is walked twice per frame: pass 0 only detects a dialogue box (then the compass is hidden and
everything in the top band belongs to the dialogue), pass 1 moves the vertices.

Registers: only at, v1, a0-a3, t0-t9 (v0 = the caller's return value is kept; no k0/k1/gp/fp; no stack).
"""
import sys, struct, math
sys.path.insert(0, r'C:\Users\shade\AppData\Local\Temp\claude\C--Users-shade-AppData-Roaming-Claude-scratch-workspaces-d26a4a75-75f2-47d7-a5b0-73edfc757065-46ea55b4-1b40-4e1b-8e0f-1c92210c0291-scratch-2026-10-16-8e6b16\9242a4f5-61eb-4545-89bd-55b3ca05d106\scratchpad')
import mipsasm
from mipsasm import Asm

HUDX = 0x5B8300          # cave (about 0x300 words)
STK = 0x5BA800           # call-return stack, 8 words
SCR = 0x5BA840           # scratch, see S_* below
RLAYER = 0x99            # aerial reticle (three blades and four orange dots)
S_DN, S_DX0, S_DX1, S_DY0, S_DY1, S_CX, S_CY, S_FAR = range(0x50, 0x70, 4)
S_MAP, S_MX0, S_MX1, S_MY1, S_MSH = range(0x70, 0x84, 4)
S_PREV, S_VALID, S_ANG0, S_ANG1, S_EASE = range(0x84, 0x98, 4)
S_RIDEP, S_DMT, S_YOFF, S_TYAW, S_LASTA, S_RIDEON, S_KD, S_KLAST, S_SLAST = range(0x98, 0xBC, 4)
S_BX0, S_BX1, S_RX, S_RY = range(0xBC, 0xCC, 4)      # pass 3: packet x box, ring centre
RIDE_TURN_EXTRA = 1.0                    # ridden ground turn: extra share of the game's heading step (1.0 = twice as fast)
DISMOUNT_FRAMES = 60                     # frames after a dismount in which the camera offset is eased to 0
DISMOUNT_K = 0.08                        # share of the offset removed each frame
EASE_FRAMES = 40                         # camera ease-back after the pause: frames
EASE_K = 0.15                            # share of the remaining angle covered each frame
CAMRING = 0x5B4500                       # game's ring of camera records (0x40 each)
CAMRING_N = 108
CAMANG = 0x3ADC40                        # player camera angles (pitch, second angle)
HOOK = 0x127334          # jr ra at the end of FUN_001270E8 (the 2D chain builder)
LAYER = 0x9A
BUFSIZE = 0x240000
MAXTAGS = 3000
MODE_TASKS = [0x3B9770, 0x3B98B0, 0x3B93B8, 0x3B9640, 0x342E38]
PAUSE = 0x3ADC50                         # 1 while the in-level pause map / menu is open
S_RA, S_END, S_ITEMS, S_COUNT, S_GRA, S_NEXT, S_MINY, S_MAXY, S_PASS, S_DLG, S_SHIFT, S_KILL = range(0, 48, 4)

def X(px): return 0x6C00 + px * 16      # GS x of a screen pixel (HUD XYOFFSET)
def Y(px): return 0x7100 + px * 16
WIDE = 600 * 16                          # packets this wide or wider: untouched
SHIFT = 80 * 16

class Asm2(Asm):
    def enc(self, it, pc):
        R = mipsasm.R
        if it[0] == 'srlv':
            return (R[it[3]] << 21) | (R[it[2]] << 16) | (R[it[1]] << 11) | 6
        return super().enc(it, pc)

def li(a, reg, val):
    val &= 0xFFFFFFFF
    if val >> 16:
        a.emit('lui', reg, val >> 16)
        if val & 0xFFFF: a.emit('ori', reg, reg, val & 0xFFFF)
    else:
        a.emit('ori', reg, 'zero', val)

def scr(a, op, reg, off):
    adr = SCR + off
    hi = (adr + 0x8000) >> 16
    a.emit('lui', 'at', hi)
    a.emit(op, reg, adr - (hi << 16), 'at')

_n = [0]
def L(name):
    _n[0] += 1
    return '%s_%d' % (name, _n[0])

def blt_u(a, ra_, rb_, label, tmp='at'):
    """branch if ra_ < rb_ (unsigned)"""
    a.emit('sltu', tmp, ra_, rb_); a.emit('bne', tmp, 'zero', label); a.emit('nop')

def bge_u(a, ra_, rb_, label, tmp='at'):
    a.emit('sltu', tmp, ra_, rb_); a.emit('beq', tmp, 'zero', label); a.emit('nop')

def regid(a):
    """at = register id of item index t2 (regs t4 / t5)"""
    hw = L('hw'); got = L('got')
    a.emit('andi', 'at', 't2', 8)
    a.emit('bne', 'at', 'zero', hw); a.emit('nop')
    a.emit('andi', 'at', 't2', 7); a.emit('sll', 'at', 'at', 2)
    a.emit('srlv', 'at', 't4', 'at')
    a.emit('beq', 'zero', 'zero', got); a.emit('nop')
    a.label(hw)
    a.emit('andi', 'at', 't2', 7); a.emit('sll', 'at', 'at', 2)
    a.emit('srlv', 'at', 't5', 'at')
    a.label(got)
    a.emit('andi', 'at', 'at', 0xF)

def item_loop(a, size, packed, body):
    """for each xyz item: t0 = item address; body(a) emitted for it"""
    top = L('it'); done = L('dn'); isx = L('ix'); skip = L('sk'); nw = L('nw')
    scr(a, 'lw', 't0', S_ITEMS)
    scr(a, 'lw', 't1', S_COUNT)
    a.emit('or', 't2', 'zero', 'zero')
    a.label(top)
    a.emit('beq', 't1', 'zero', done); a.emit('nop')
    regid(a)
    a.emit('andi', 't7', 'at', 6)
    a.emit('xori', 't7', 't7', 4)
    a.emit('beq', 't7', 'zero', isx); a.emit('nop')            # XYZ2 / XYZF2 / XYZ3 / XYZF3
    if packed:
        a.emit('xori', 't7', 'at', 0xE)                         # A+D to XYZ2 / XYZF2
        a.emit('bne', 't7', 'zero', skip); a.emit('nop')
        a.emit('lbu', 't7', 8, 't0')
        a.emit('addiu', 't7', 't7', -4)
        a.emit('sltiu', 't7', 't7', 2)
        a.emit('beq', 't7', 'zero', skip); a.emit('nop')
    else:
        a.emit('beq', 'zero', 'zero', skip); a.emit('nop')
    a.label(isx)
    body(a)
    a.label(skip)
    a.emit('addiu', 't0', 't0', size)
    a.emit('addiu', 't1', 't1', -1)
    a.emit('addiu', 't2', 't2', 1)
    a.emit('bne', 't2', 't3', nw); a.emit('nop')
    a.emit('or', 't2', 'zero', 'zero')
    a.label(nw)
    a.emit('beq', 'zero', 'zero', top); a.emit('nop')
    a.label(done)

def verts(a, size, packed):
    vend = L('vend')
    # ---- bounding box: v1 = min x, t6 = max x, S_MINY / S_MAXY
    li(a, 'v1', 0xFFFF)
    a.emit('or', 't6', 'zero', 'zero')
    li(a, 't7', 0xFFFF); scr(a, 'sw', 't7', S_MINY)
    scr(a, 'sw', 'zero', S_MAXY)
    def bbox(a):
        mn = L('mn'); mx = L('mx'); my = L('my'); xy = L('xy')
        a.emit('lhu', 't7', 0, 't0')
        a.emit('sltu', 'at', 't7', 'v1'); a.emit('beq', 'at', 'zero', mn); a.emit('nop')
        a.emit('or', 'v1', 't7', 'zero')
        a.label(mn)
        a.emit('sltu', 'at', 't6', 't7'); a.emit('beq', 'at', 'zero', mx); a.emit('nop')
        a.emit('or', 't6', 't7', 'zero')
        a.label(mx)
        a.emit('lhu', 't7', 2, 't0')                              # y
        scr(a, 'lw', 'a3', S_MINY)                                 # a3 is the layer stop: parked below
        a.emit('sltu', 'at', 't7', 'a3'); a.emit('beq', 'at', 'zero', my); a.emit('nop')
        scr(a, 'sw', 't7', S_MINY)
        a.label(my)
        scr(a, 'lw', 'a3', S_MAXY)
        a.emit('sltu', 'at', 'a3', 't7'); a.emit('beq', 'at', 'zero', xy); a.emit('nop')
        scr(a, 'sw', 't7', S_MAXY)
        a.label(xy)
    scr(a, 'sw', 'a3', S_NEXT + 0x30)                              # park a3 (layer stop)
    item_loop(a, size, packed, bbox)
    scr(a, 'lw', 'a3', S_NEXT + 0x30)
    # ---- no vertices: untouched
    blt_u(a, 't6', 'v1', vend)
    # ---- reticle passes (layer 0x99): 2 = find the four orange dots, 3 = halve the reticle about their centre
    np2 = L('np2'); np3 = L('np3')
    scr(a, 'lw', 't0', S_PASS)
    a.emit('addiu', 't1', 'zero', 2); a.emit('bne', 't0', 't1', np2); a.emit('nop')
    if size == 8:                                  # dots: REGLIST sprites at most 10 x 10 px
        a.emit('subu', 't0', 't6', 'v1')
        a.emit('sltiu', 't0', 't0', 10 * 16 + 1); a.emit('beq', 't0', 'zero', vend); a.emit('nop')
        scr(a, 'lw', 't7', S_MINY); scr(a, 'lw', 't2', S_MAXY)
        a.emit('subu', 't0', 't2', 't7')
        a.emit('sltiu', 't0', 't0', 10 * 16 + 1); a.emit('beq', 't0', 'zero', vend); a.emit('nop')
        for slot, reg, keep_lt in ((S_DX0, 'v1', True), (S_DX1, 't6', False), (S_DY0, 't7', True), (S_DY1, 't2', False)):
            k = L('dk')
            scr(a, 'lw', 't0', slot)
            if keep_lt: a.emit('sltu', 't1', reg, 't0')
            else: a.emit('sltu', 't1', 't0', reg)
            a.emit('beq', 't1', 'zero', k); a.emit('nop')
            scr(a, 'sw', reg, slot)
            a.label(k)
        scr(a, 'lw', 't0', S_DN); a.emit('addiu', 't0', 't0', 1); scr(a, 'sw', 't0', S_DN)
    a.emit('beq', 'zero', 'zero', vend); a.emit('nop')
    a.label(np2)
    a.emit('addiu', 't1', 'zero', 3); a.emit('bne', 't0', 't1', np3); a.emit('nop')
    yoff = 2 if size == 8 else 4
    def near(a):
        # any vertex 64 px or more from the centre: the packet is not part of the reticle (enemy rings, markers)
        far = L('far'); ok = L('nr')
        for reg, off, slot in (('t7', 0, S_CX), ('t6', yoff, S_CY)):
            g = L('ab')
            a.emit('lhu', reg, off, 't0')
            scr(a, 'lw', 'v1', slot)
            a.emit('sltu', 'at', reg, 'v1')
            a.emit('beq', 'at', 'zero', g); a.emit('subu', 'at', reg, 'v1')
            a.emit('subu', 'at', 'v1', reg)
            a.label(g)
            a.emit('sltiu', 'at', 'at', 64 * 16); a.emit('beq', 'at', 'zero', far); a.emit('nop')
        a.emit('beq', 'zero', 'zero', ok); a.emit('nop')
        a.label(far)
        a.emit('ori', 'v1', 'zero', 1); scr(a, 'sw', 'v1', S_FAR)
        a.label(ok)
    def half(a):
        sk = L('hs')
        for reg, off, slot in (('t7', 0, S_CX), ('t6', yoff, S_CY)):
            g = L('ab')
            a.emit('lhu', reg, off, 't0')
            scr(a, 'lw', 'v1', slot)
            a.emit('sltu', 'at', reg, 'v1')
            a.emit('beq', 'at', 'zero', g); a.emit('subu', 'at', reg, 'v1')
            a.emit('subu', 'at', 'v1', reg)
            a.label(g)
            a.emit('sltiu', 'at', 'at', 64 * 16); a.emit('beq', 'at', 'zero', sk); a.emit('nop')
            a.emit('sll', 'at', reg, 2); a.emit('addu', reg, reg, 'at')          # 5/8 size: (5 v + 3 c) / 8
            a.emit('sll', 'at', 'v1', 1); a.emit('addu', 'at', 'at', 'v1')
            a.emit('addu', reg, reg, 'at'); a.emit('srl', reg, reg, 3)
        a.emit('sh', 't7', 0, 't0'); a.emit('sh', 't6', yoff, 't0')
        a.label(sk)
    def rhalf(a):
        for reg, off, slot in (('t7', 0, S_RX), ('t6', yoff, S_RY)):
            a.emit('lhu', reg, off, 't0')
            scr(a, 'lw', 'v1', slot)
            a.emit('addu', reg, reg, 'v1'); a.emit('srl', reg, reg, 1)
        a.emit('sh', 't7', 0, 't0'); a.emit('sh', 't6', yoff, 't0')
    scr(a, 'sw', 'v1', S_BX0); scr(a, 'sw', 't6', S_BX1)
    scr(a, 'sw', 'zero', S_FAR)
    item_loop(a, size, packed, near)
    scr(a, 'lw', 't0', S_FAR)
    ring = L('ring')
    a.emit('bne', 't0', 'zero', ring); a.emit('nop')
    item_loop(a, size, packed, half)
    a.emit('beq', 'zero', 'zero', vend); a.emit('nop')
    a.label(ring)
    if size == 8:
        # not the reticle: a marked-enemy ring (one square quad, 16 px or more) is halved about its own centre
        scr(a, 'lw', 'v1', S_BX0); scr(a, 'lw', 't6', S_BX1)
        scr(a, 'lw', 't7', S_MINY); scr(a, 'lw', 't2', S_MAXY)
        a.emit('subu', 't0', 't6', 'v1')
        a.emit('sltiu', 't1', 't0', 16 * 16); a.emit('bne', 't1', 'zero', vend); a.emit('nop')
        a.emit('subu', 't1', 't2', 't7')
        a.emit('subu', 't1', 't0', 't1'); a.emit('addiu', 't1', 't1', 8 * 16)
        a.emit('sltiu', 't1', 't1', 16 * 16 + 1); a.emit('beq', 't1', 'zero', vend); a.emit('nop')
        a.emit('addu', 't0', 'v1', 't6'); a.emit('srl', 't0', 't0', 1); scr(a, 'sw', 't0', S_RX)
        a.emit('addu', 't0', 't7', 't2'); a.emit('srl', 't0', 't0', 1); scr(a, 'sw', 't0', S_RY)
        item_loop(a, size, packed, rhalf)
    a.emit('beq', 'zero', 'zero', vend); a.emit('nop')
    a.label(np3)
    if size == 8:
        # the two faint script panels behind the vine (sprites 0..104 x 240..480 and 104..200 x 368..490): their
        # L-shaped edge shows, so they are drawn at FADE_NUM/2^FADE_SH of their alpha (first item = RGBAQ)
        nf = L('nf'); df = L('df')
        scr(a, 'lw', 't7', S_MINY); scr(a, 'lw', 't2', S_MAXY)
        for x0, x1, y0, y1 in ((0, 104, 240, 480), (104, 200, 368, 490)):
            nx = L('nx')
            li(a, 't0', X(x0)); a.emit('bne', 'v1', 't0', nx); a.emit('nop')
            li(a, 't0', X(x1)); a.emit('bne', 't6', 't0', nx); a.emit('nop')
            li(a, 't0', Y(y0)); a.emit('bne', 't7', 't0', nx); a.emit('nop')
            li(a, 't0', Y(y1)); a.emit('beq', 't2', 't0', df); a.emit('nop')
            a.label(nx)
        a.emit('beq', 'zero', 'zero', nf); a.emit('nop')
        a.label(df)
        a.emit('andi', 't0', 't4', 0xF); a.emit('addiu', 't1', 'zero', 1)
        a.emit('bne', 't0', 't1', nf); a.emit('nop')                 # first register must be RGBAQ
        scr(a, 'lw', 't0', S_ITEMS)
        a.emit('sb', 'zero', 3, 't0')                                # alpha 0: not drawn
        a.label(nf)
    # ---- 600 px wide or more: untouched
    a.emit('nop')
    a.emit('subu', 't7', 't6', 'v1')
    li(a, 'at', WIDE)
    a.emit('sltu', 't7', 't7', 'at'); a.emit('beq', 't7', 'zero', vend); a.emit('nop')
    # ---- classification. t7 = min y, t2 = max y (t2 free here)
    scr(a, 'lw', 't7', S_MINY)
    scr(a, 'lw', 't2', S_MAXY)
    # compass box: x 495..625, y 30..130  -> t1 = 1 if inside
    notbox = L('nb'); boxdone = L('bd')
    a.emit('or', 't1', 'zero', 'zero')
    li(a, 't0', X(480)); blt_u(a, 'v1', 't0', notbox)
    li(a, 't0', X(640)); blt_u(a, 't0', 't6', notbox)
    li(a, 't0', Y(20)); blt_u(a, 't7', 't0', notbox)
    li(a, 't0', Y(145)); blt_u(a, 't0', 't2', notbox)
    inb = L('inb')
    a.emit('subu', 't0', 't2', 't7')                      # height
    li(a, 'at', 17 * 16); blt_u(a, 't0', 'at', inb, 't0')
    a.emit('subu', 't0', 't2', 't7')
    li(a, 'at', 60 * 16); blt_u(a, 't0', 'at', notbox, 't0')
    a.label(inb)
    a.emit('ori', 't1', 'zero', 1)
    a.label(notbox)
    # pass 0: a dialogue box is a top-band packet (min y < 60) at least 250 px wide outside the compass box
    p1 = L('p1')
    scr(a, 'lw', 't0', S_PASS)
    a.emit('bne', 't0', 'zero', p1); a.emit('nop')
    a.emit('bne', 't1', 'zero', vend); a.emit('nop')
    li(a, 't0', Y(60)); bge_u(a, 't7', 't0', vend)
    a.emit('subu', 't0', 't6', 'v1')
    li(a, 'at', 250 * 16)
    a.emit('sltu', 't0', 't0', 'at'); a.emit('bne', 't0', 'zero', vend); a.emit('nop')
    a.emit('ori', 't0', 'zero', 1); scr(a, 'sw', 't0', S_DLG)
    a.emit('beq', 'zero', 'zero', vend); a.emit('nop')
    a.label(p1)
    # pass 1: shift
    right = L('rt'); left = L('lf'); none = L('no'); apply_ = L('ap'); kill = L('kl'); nk = L('nk'); nk2 = L('nk2')
    # dialogue backdrop: starts above y 10 and is 300 px wide or more (parchment) or starts left of x 10 and is 200 px tall or more (left strip)
    # dialogue parchment (starts above y 10, 300 px wide or more, reaches the right screen edge): its right edge
    # vertices keep their original x so the parchment still runs off the screen edge (no visible seam)
    scr(a, 'sw', 'zero', S_KILL)
    li(a, 't0', Y(10)); bge_u(a, 't7', 't0', nk)
    a.emit('subu', 't0', 't6', 'v1')
    li(a, 'at', 300 * 16); blt_u(a, 't0', 'at', nk, 't0')
    li(a, 't0', X(630)); blt_u(a, 't6', 't0', nk, 't0')
    scr(a, 'sw', 't6', S_KILL)
    a.label(nk)
    # mission briefing map: a parchment starting above y 10, 280 px tall or more, 200..480 px wide; it and every later
    # piece inside it get one shift that puts the map in the middle of the screen
    nomap = L('nomap'); inmap = L('inmap'); usem = L('usem')
    scr(a, 'lw', 't0', S_MAP)
    a.emit('bne', 't0', 'zero', inmap); a.emit('nop')
    li(a, 't0', Y(10)); bge_u(a, 't7', 't0', nomap)
    a.emit('subu', 't0', 't2', 't7'); li(a, 'at', 280 * 16); blt_u(a, 't0', 'at', nomap, 't0')
    a.emit('subu', 't0', 't6', 'v1'); li(a, 'at', 200 * 16); blt_u(a, 't0', 'at', nomap, 't0')
    a.emit('subu', 't0', 't6', 'v1'); li(a, 'at', 480 * 16); bge_u(a, 't0', 'at', nomap, 't0')
    a.emit('ori', 't0', 'zero', 1); scr(a, 'sw', 't0', S_MAP)
    scr(a, 'sw', 'v1', S_MX0); scr(a, 'sw', 't6', S_MX1); scr(a, 'sw', 't2', S_MY1)
    a.emit('addu', 't0', 'v1', 't6'); a.emit('srl', 't0', 't0', 1)
    li(a, 'at', 0x8000); a.emit('subu', 't0', 't0', 'at')
    a.emit('sll', 'at', 't0', 1); a.emit('addu', 't0', 't0', 'at'); a.emit('sra', 't0', 't0', 2)
    a.emit('subu', 't0', 'zero', 't0'); scr(a, 'sw', 't0', S_MSH)
    a.emit('beq', 'zero', 'zero', usem); a.emit('nop')
    a.label(inmap)
    scr(a, 'lw', 't0', S_MX0); blt_u(a, 'v1', 't0', nomap, 't0')
    scr(a, 'lw', 't0', S_MX1); blt_u(a, 't0', 't6', nomap, 't0')
    scr(a, 'lw', 't0', S_MY1); blt_u(a, 't0', 't2', nomap, 't0')
    a.label(usem)
    scr(a, 'lw', 't0', S_MSH)
    a.emit('beq', 'zero', 'zero', apply_); a.emit('nop')
    a.label(nomap)
    # kill counter and its effects (angel icon, rings): centre right of x 500 and below y 300
    nc = L('nc')
    a.emit('addu', 't0', 'v1', 't6')
    li(a, 'at', 2 * X(500)); blt_u(a, 't0', 'at', nc, 't0')
    a.emit('addu', 't0', 't7', 't2')
    li(a, 'at', 2 * Y(300)); blt_u(a, 't0', 'at', nc, 't0')
    a.emit('beq', 'zero', 'zero', right); a.emit('nop')
    a.label(nc)
    # a dialogue-box piece (outside the compass box, starting above y 60, 250 px wide or more) marks the rest of the frame
    nd = L('nd')
    a.emit('bne', 't1', 'zero', nd); a.emit('nop')
    li(a, 't0', Y(60)); bge_u(a, 't7', 't0', nd)
    a.emit('subu', 't0', 't6', 'v1')
    li(a, 'at', 250 * 16)
    a.emit('sltu', 't0', 't0', 'at'); a.emit('bne', 't0', 'zero', nd); a.emit('nop')
    a.emit('ori', 't0', 'zero', 1); scr(a, 'sw', 't0', S_DLG)
    a.label(nd)
    # compass and its blips: inside the compass box, as long as no dialogue piece came before in this frame
    ncp = L('ncp')
    a.emit('beq', 't1', 'zero', ncp); a.emit('nop')
    scr(a, 'lw', 't0', S_DLG)
    a.emit('beq', 't0', 'zero', right); a.emit('nop')
    a.label(ncp)
    # left: top band (min y < 230), gauge rows (min y >= 360), left ornament (max x <= 120)
    li(a, 't0', Y(230)); blt_u(a, 't7', 't0', left)
    li(a, 't0', Y(360)); bge_u(a, 't7', 't0', left)
    li(a, 't0', X(120)); bge_u(a, 't0', 't6', left)
    # chain counter label and gauge effects: centre left of x 260 and below y 300
    ncl = L('ncl')
    a.emit('addu', 't0', 'v1', 't6')
    li(a, 'at', 2 * X(260)); bge_u(a, 't0', 'at', ncl, 't0')
    a.emit('addu', 't0', 't7', 't2')
    li(a, 'at', 2 * Y(300)); bge_u(a, 't0', 'at', left, 't0')
    a.label(ncl)
    a.emit('beq', 'zero', 'zero', none); a.emit('nop')
    a.label(right); li(a, 't0', SHIFT); a.emit('beq', 'zero', 'zero', apply_); a.emit('nop')
    a.label(left); li(a, 't0', (-SHIFT) & 0xFFFFFFFF); a.emit('beq', 'zero', 'zero', apply_); a.emit('nop')
    a.label(none); a.emit('or', 't0', 'zero', 'zero')
    a.label(apply_)
    scr(a, 'sw', 't0', S_SHIFT)
    def move(a):
        kl = L('kx'); st = L('st')
        scr(a, 'lw', 'at', S_KILL)
        a.emit('lhu', 't7', 0, 't0')
        a.emit('beq', 'at', 'zero', kl); a.emit('nop')  # 0 = not the parchment
        a.emit('beq', 't7', 'at', st); a.emit('nop')   # parchment right edge: keep original x
        a.label(kl)
        li(a, 'at', 0x8000)
        a.emit('subu', 't7', 't7', 'at')
        a.emit('sll', 'at', 't7', 1)
        a.emit('addu', 't7', 't7', 'at')
        a.emit('sra', 't7', 't7', 2)
        li(a, 'at', 0x8000)
        a.emit('addu', 't7', 't7', 'at')
        scr(a, 'lw', 'at', S_SHIFT)
        a.emit('addu', 't7', 't7', 'at')
        a.label(st)
        a.emit('sh', 't7', 0, 't0')
    item_loop(a, size, packed, move)
    a.label(vend)
    scr(a, 'lw', 't7', S_END)

def walk(a, tagname, layer=LAYER):
    """one walk of layer LAYER; returns to the code after it"""
    T = lambda s: '%s_%s' % (tagname, s)
    a.emit('addiu', 'a2', 'a0', 16 * layer)
    a.emit('addiu', 'a3', 'a0', 16 * (layer + 1))
    li(a, 't8', MAXTAGS)
    li(a, 't9', STK)
    a.label(T('TAG'))
    a.emit('beq', 't8', 'zero', T('DONE')); a.emit('addiu', 't8', 't8', -1)
    blt_u(a, 'a2', 'a0', T('DONE'), 't0')
    bge_u(a, 'a2', 'a1', T('DONE'), 't0')
    a.emit('andi', 't0', 'a2', 0xF); a.emit('bne', 't0', 'zero', T('DONE')); a.emit('nop')
    a.emit('lw', 't1', 0, 'a2')
    a.emit('lw', 't2', 4, 'a2')
    a.emit('andi', 't3', 't1', 0xFFFF)
    a.emit('srl', 't4', 't1', 28); a.emit('andi', 't4', 't4', 7)
    a.emit('sll', 't5', 't3', 4)
    a.emit('addiu', 't6', 'a2', 16)
    a.emit('addu', 't7', 't6', 't5')
    for idv, lab in ((1, 'CNT'), (2, 'NXT'), (5, 'CAL'), (6, 'RET'), (3, 'REF')):
        a.emit('addiu', 't0', 'zero', idv); a.emit('beq', 't4', 't0', T(lab)); a.emit('nop')
    a.emit('beq', 'zero', 'zero', T('DONE')); a.emit('nop')
    a.label(T('CNT'))
    a.emit('jal', 'GIF'); a.emit('nop')
    a.emit('beq', 'zero', 'zero', T('NEXT')); a.emit('or', 'a2', 't7', 'zero')
    a.label(T('NXT'))
    a.emit('jal', 'GIF'); a.emit('nop')
    a.emit('beq', 'zero', 'zero', T('NEXT')); a.emit('or', 'a2', 't2', 'zero')
    a.label(T('CAL'))
    a.emit('jal', 'GIF'); a.emit('nop')
    blt_u(a, 't2', 'a0', T('SKIPCALL'), 't0')
    bge_u(a, 't2', 'a1', T('SKIPCALL'), 't0')
    li(a, 't0', STK + 4 * 8)
    a.emit('sltu', 't0', 't9', 't0'); a.emit('beq', 't0', 'zero', T('DONE')); a.emit('nop')
    a.emit('sw', 't7', 0, 't9'); a.emit('addiu', 't9', 't9', 4)
    a.emit('beq', 'zero', 'zero', T('NEXT')); a.emit('or', 'a2', 't2', 'zero')
    a.label(T('SKIPCALL'))
    a.emit('beq', 'zero', 'zero', T('NEXT')); a.emit('or', 'a2', 't7', 'zero')
    a.label(T('RET'))
    a.emit('jal', 'GIF'); a.emit('nop')
    li(a, 't0', STK)
    a.emit('beq', 't9', 't0', T('DONE')); a.emit('nop')
    a.emit('addiu', 't9', 't9', -4); a.emit('lw', 'a2', 0, 't9')
    a.emit('beq', 'zero', 'zero', T('NEXT')); a.emit('nop')
    a.label(T('REF'))
    blt_u(a, 't2', 'a0', T('REFDONE'), 't0')
    bge_u(a, 't2', 'a1', T('REFDONE'), 't0')
    a.emit('or', 't6', 't2', 'zero'); a.emit('addu', 't7', 't2', 't5')
    a.emit('jal', 'GIF'); a.emit('nop')
    a.label(T('REFDONE'))
    a.emit('addiu', 'a2', 'a2', 16)
    a.label(T('NEXT'))
    a.emit('bne', 'a2', 'a3', T('TAG')); a.emit('nop')
    a.label(T('DONE'))

def build():
    _n[0] = 0
    a = Asm2(HUDX)
    for t in MODE_TASKS:                         # levels only
        li(a, 't0', t)
        a.emit('lw', 't1', 0, 't0')
        a.emit('beq', 't1', 'zero', 'NOLEVEL')
        a.emit('nop')
    # camera angles: the pause map turns the camera straight down (003ADC40 = -pi/2) and leaves it there. Keep a copy
    # of both angles (003ADC40 / 003ADC44) on every gameplay frame and write it back when the pause flag 004EE29C clears.
    cpz = L('cpz'); csv = L('csv'); cdn = L('cdn')
    li(a, 't0', 0x4EE29C); a.emit('lw', 't1', 0, 't0')
    scr(a, 'lw', 't3', S_PREV)
    scr(a, 'sw', 't1', S_PREV)
    li(a, 't6', CAMANG)
    ease = L('ease')
    a.emit('bne', 't1', 'zero', cdn); a.emit('nop')          # paused or in a briefing: keep the copy
    a.emit('beq', 't3', 'zero', ease); a.emit('nop')         # was playing last frame too
    scr(a, 'lw', 't4', S_VALID)
    a.emit('beq', 't4', 'zero', csv); a.emit('nop')          # no copy from this level yet
    a.emit('ori', 't4', 'zero', EASE_FRAMES); scr(a, 'sw', 't4', S_EASE)   # pause just closed: start easing back
    a.label(ease)
    scr(a, 'lw', 't4', S_EASE)
    a.emit('beq', 't4', 'zero', csv); a.emit('nop')          # not easing: refresh the copy
    a.emit('addiu', 't4', 't4', -1); scr(a, 'sw', 't4', S_EASE)
    # each frame: angle += (copy - angle) * EASE_K   (FPU temporaries f4..f6 only)
    bits = struct.unpack('<I', struct.pack('<f', EASE_K))[0]
    li(a, 't4', bits); a.emit('mtc1', 't4', 'f6')
    for off, slot in ((0, S_ANG0), (4, S_ANG1)):
        scr(a, 'lw', 't4', slot); a.emit('mtc1', 't4', 'f5')
        a.emit('lwc1', 'f4', off, 't6')
        a.emit('sub.s', 'f5', 'f5', 'f4')
        a.emit('mul.s', 'f5', 'f5', 'f6')
        a.emit('add.s', 'f4', 'f4', 'f5')
        a.emit('swc1', 'f4', off, 't6')
    a.emit('beq', 'zero', 'zero', cdn); a.emit('nop')
    a.label(csv)
    a.emit('lw', 't4', 0, 't6'); scr(a, 'sw', 't4', S_ANG0)
    a.emit('lw', 't4', 4, 't6'); scr(a, 'sw', 't4', S_ANG1)
    a.emit('ori', 't4', 'zero', 1); scr(a, 'sw', 't4', S_VALID)
    a.label(cdn)
    # dismount: the on-foot camera keeps its own world angles (camera object +0x40 pitch / +0x44 yaw, 003ADB00 / 003ADB04),
    # frozen while Caim rides, and switches back to them when he gets off, so the view snapped to the direction he faced
    # when he mounted. While he rides (Caim 003AC5E0 +0x6B4 = 2) the live angles (003AD530 / 003AD534) are copied into
    # them every frame, so the on-foot camera carries on from the riding view.
    scr(a, 'lw', 't3', S_RIDEON); scr(a, 'sw', 'zero', S_RIDEON)
    nr = L('nr')
    li(a, 't0', 0x3AC5E0 + 0x6B4); a.emit('lw', 't1', 0, 't0')
    a.emit('addiu', 't4', 'zero', 2); a.emit('bne', 't1', 't4', nr); a.emit('nop')
    li(a, 't0', 0x3AD530)
    # faster ridden turn without extra lean: the doubled lean made the riding camera (built from her rolled body) roll
    # over. The lean stays vanilla; instead the heading (dragon 0041BFC0 +0xA0, wrapped -pi..pi) gets the game's own
    # change since last frame added RIDE_TURN_EXTRA times again, while steering (|target lean +0xB4| > 0.05) and only
    # for normal steps (under 0.2 rad; not the U-turn). t3 = 1 when last frame was a riding frame too.
    def wrap_h(a, r):
        x1 = L('x1'); x2 = L('x2')
        li(a, 't4', struct.unpack('<I', struct.pack('<f', math.pi))[0]); a.emit('mtc1', 't4', 'f6')
        li(a, 't4', struct.unpack('<I', struct.pack('<f', 2 * math.pi))[0]); a.emit('mtc1', 't4', 'f9')
        a.emit('c.olt.s', 'f6', r); a.emit('bc1f', x1); a.emit('nop')
        a.emit('sub.s', r, r, 'f9')
        a.label(x1)
        a.emit('neg.s', 'f6', 'f6')
        a.emit('c.olt.s', r, 'f6'); a.emit('bc1f', x2); a.emit('nop')
        a.emit('add.s', r, r, 'f9')
        a.label(x2)
    hs = L('hs')
    li(a, 't1', 0x41BFC0); a.emit('lwc1', 'f4', 0xA0, 't1')
    a.emit('beq', 't3', 'zero', hs); a.emit('nop')
    a.emit('lwc1', 'f8', 0xB4, 't1'); a.emit('abs.s', 'f8', 'f8')
    li(a, 't4', struct.unpack('<I', struct.pack('<f', 0.05))[0]); a.emit('mtc1', 't4', 'f7')
    a.emit('c.olt.s', 'f8', 'f7'); a.emit('bc1t', hs); a.emit('nop')
    scr(a, 'lw', 't4', S_LASTA); a.emit('mtc1', 't4', 'f5')
    a.emit('sub.s', 'f5', 'f4', 'f5'); wrap_h(a, 'f5')                # game's step this frame
    a.emit('abs.s', 'f8', 'f5')
    li(a, 't4', struct.unpack('<I', struct.pack('<f', 0.2))[0]); a.emit('mtc1', 't4', 'f7')
    a.emit('c.olt.s', 'f8', 'f7'); a.emit('bc1f', hs); a.emit('nop')
    li(a, 't4', struct.unpack('<I', struct.pack('<f', RIDE_TURN_EXTRA))[0]); a.emit('mtc1', 't4', 'f7')
    a.emit('mul.s', 'f5', 'f5', 'f7'); a.emit('add.s', 'f4', 'f4', 'f5'); wrap_h(a, 'f4')
    li(a, 't1', 0x41BFC0); a.emit('swc1', 'f4', 0xA0, 't1')
    a.label(hs)
    a.emit('mfc1', 't4', 'f4'); scr(a, 'sw', 't4', S_LASTA)
    a.emit('ori', 't4', 'zero', 1); scr(a, 'sw', 't4', S_RIDEON)
    a.emit('lw', 't4', 0, 't0'); a.emit('sw', 't4', 0x3ADB00 - 0x3AD530, 't0')
    a.emit('lw', 't4', 4, 't0'); a.emit('sw', 't4', 0x3ADB04 - 0x3AD530, 't0')
    # the game also restores the on-foot camera from its ring of 108 camera records (005B4500, 0x40 each, +0x28 = 3 and
    # +0x2C = 8; +0x04 / +0x18 yaw, +0x0C offset = yaw - Caim facing), frozen while riding: keep their yaw current too
    a.emit('lwc1', 'f4', 4, 't0')                                   # live yaw
    li(a, 't1', 0x3AC5E0); a.emit('lwc1', 'f5', 0x44, 't1')         # Caim facing
    a.emit('sub.s', 'f5', 'f4', 'f5')                               # offset, wrapped into -pi .. pi
    pi_bits = struct.unpack('<I', struct.pack('<f', math.pi))[0]
    tp_bits = struct.unpack('<I', struct.pack('<f', 2 * math.pi))[0]
    li(a, 't4', pi_bits); a.emit('mtc1', 't4', 'f6')
    li(a, 't4', tp_bits); a.emit('mtc1', 't4', 'f7')
    w1 = L('w1'); w2 = L('w2')
    a.emit('c.olt.s', 'f6', 'f5'); a.emit('bc1f', w1); a.emit('nop')
    a.emit('sub.s', 'f5', 'f5', 'f7')
    a.label(w1)
    a.emit('neg.s', 'f6', 'f6')
    a.emit('c.olt.s', 'f5', 'f6'); a.emit('bc1f', w2); a.emit('nop')
    a.emit('add.s', 'f5', 'f5', 'f7')
    a.label(w2)
    rl = L('rl'); rn = L('rn')
    li(a, 't1', CAMRING); a.emit('ori', 't3', 'zero', CAMRING_N)
    a.label(rl)
    a.emit('lw', 't4', 0x28, 't1'); a.emit('addiu', 't5', 'zero', 3)
    a.emit('bne', 't4', 't5', rn); a.emit('nop')
    a.emit('lw', 't4', 0x2C, 't1'); a.emit('addiu', 't5', 'zero', 8)
    a.emit('bne', 't4', 't5', rn); a.emit('nop')
    a.emit('swc1', 'f4', 0x04, 't1'); a.emit('swc1', 'f4', 0x18, 't1'); a.emit('swc1', 'f5', 0x0C, 't1')
    a.label(rn)
    a.emit('addiu', 't3', 't3', -1)
    a.emit('bne', 't3', 'zero', rl); a.emit('addiu', 't1', 't1', 0x40)
    li(a, 't0', 0x3AD534); a.emit('lw', 't4', 0, 't0'); scr(a, 'sw', 't4', S_TYAW)   # riding view yaw
    a.label(nr)
    # on foot the camera looks along Caim's facing (+0x44) + 003ADC44, and on the dismount the game fills 003ADC44
    # from a stale copy of the pre-mount view. For DISMOUNT_FRAMES after the dismount (Caim +0x6B4 2 -> 1) the cave
    # owns the yaw: T starts at the last riding yaw and eases toward Caim's facing; each frame the live yaw, the saved
    # yaw and the offset (T - facing) are all set from it, so the camera turns smoothly to look where he faces.
    nde = L('nde'); ndm = L('ndm')
    li(a, 't0', 0x3AC5E0 + 0x6B4); a.emit('lw', 't1', 0, 't0')
    scr(a, 'lw', 't3', S_RIDEP); scr(a, 'sw', 't1', S_RIDEP)
    a.emit('addiu', 't4', 'zero', 2); a.emit('bne', 't3', 't4', nde); a.emit('nop')
    a.emit('addiu', 't4', 'zero', 1); a.emit('bne', 't1', 't4', nde); a.emit('nop')
    a.emit('ori', 't4', 'zero', DISMOUNT_FRAMES); scr(a, 'sw', 't4', S_DMT)
    a.label(nde)
    scr(a, 'lw', 't4', S_DMT)
    a.emit('beq', 't4', 'zero', ndm); a.emit('nop')
    a.emit('addiu', 't4', 't4', -1); scr(a, 'sw', 't4', S_DMT)
    def wrap(a, r):
        """r into -pi .. pi (one turn each way); uses f6 / f7"""
        x1 = L('x1'); x2 = L('x2')
        li(a, 't4', pi_bits); a.emit('mtc1', 't4', 'f6')
        li(a, 't4', tp_bits); a.emit('mtc1', 't4', 'f7')
        a.emit('c.olt.s', 'f6', r); a.emit('bc1f', x1); a.emit('nop')
        a.emit('sub.s', r, r, 'f7')
        a.label(x1)
        a.emit('neg.s', 'f6', 'f6')
        a.emit('c.olt.s', r, 'f6'); a.emit('bc1f', x2); a.emit('nop')
        a.emit('add.s', r, r, 'f7')
        a.label(x2)
    scr(a, 'lw', 't4', S_TYAW); a.emit('mtc1', 't4', 'f4')          # T
    li(a, 't1', 0x3AC5E0); a.emit('lwc1', 'f8', 0x44, 't1')         # Caim facing
    a.emit('sub.s', 'f5', 'f8', 'f4'); wrap(a, 'f5')                # facing - T
    kb = struct.unpack('<I', struct.pack('<f', DISMOUNT_K))[0]
    li(a, 't4', kb); a.emit('mtc1', 't4', 'f6')
    a.emit('mul.s', 'f5', 'f5', 'f6'); a.emit('add.s', 'f4', 'f4', 'f5'); wrap(a, 'f4')
    a.emit('mfc1', 't4', 'f4'); scr(a, 'sw', 't4', S_TYAW)
    li(a, 't0', 0x3AD534); a.emit('swc1', 'f4', 0, 't0'); a.emit('swc1', 'f4', 0x3ADB04 - 0x3AD534, 't0')
    a.emit('sub.s', 'f5', 'f4', 'f8'); wrap(a, 'f5')                # offset = T - facing
    a.emit('swc1', 'f5', 4, 't6')
    a.label(ndm)
    # knockdown 50 % faster: while Caim is in the damage state (+0x2D0 = 5) after a knockdown clip (+0x120 = 0x48..0x4A,
    # marked until he leaves the state, so the get-up is included) the playback rate of the request (+0x174, read every
    # frame) is set to 1.5x the value the game wrote (the value written is kept, so it is not raised again)
    koff = L('koff'); kchk = L('kchk'); kend = L('kend')
    li(a, 't0', 0x3AC5E0); a.emit('lw', 't1', 0x2D0, 't0'); a.emit('addiu', 't2', 'zero', 5)
    a.emit('bne', 't1', 't2', koff); a.emit('nop')
    a.emit('lhu', 't1', 0x120, 't0'); a.emit('addiu', 't1', 't1', -0x48); a.emit('sltiu', 't1', 't1', 3)
    a.emit('beq', 't1', 'zero', kchk); a.emit('nop')
    a.emit('ori', 't3', 'zero', 1); scr(a, 'sw', 't3', S_KD)
    a.label(kchk)
    scr(a, 'lw', 't3', S_KD); a.emit('beq', 't3', 'zero', kend); a.emit('nop')
    a.emit('lhu', 't1', 0x174, 't0'); scr(a, 'lw', 't2', S_KLAST)
    a.emit('beq', 't1', 't2', kend); a.emit('nop')
    a.emit('srl', 't2', 't1', 1); a.emit('addu', 't1', 't1', 't2')
    a.emit('sh', 't1', 0x174, 't0'); scr(a, 'sw', 't1', S_KLAST)
    a.emit('beq', 'zero', 'zero', kend); a.emit('nop')
    a.label(koff)
    scr(a, 'sw', 'zero', S_KD); scr(a, 'sw', 'zero', S_KLAST)
    a.label(kend)
    # lock-on camera smoothing (section 'smooth lock-on camera', cave FILT 005AF000): DOT sets 005AF1F8 when it applied
    # a camera step this frame; if not (lock off, no target, riding) the smoothed turn speeds 005AF1F0 / F4 are reset
    lsk = L('lsk')
    a.emit('lui', 't0', 0x5B); a.emit('lw', 't1', -0x0E08, 't0')
    a.emit('bne', 't1', 'zero', lsk); a.emit('nop')
    a.emit('sw', 'zero', -0x0E10, 't0'); a.emit('sw', 'zero', -0x0E0C, 't0')
    a.label(lsk)
    a.emit('sw', 'zero', -0x0E08, 't0')
    li(a, 't0', PAUSE)                           # pause map open: leave the layer alone
    a.emit('lw', 't1', 0, 't0')
    a.emit('bne', 't1', 'zero', 'QUIT')
    a.emit('nop')
    scr(a, 'sw', 'ra', S_RA)
    li(a, 't0', 0x4F50D0)
    a.emit('lw', 'a0', 0, 't0')
    a.emit('beq', 'a0', 'zero', 'EXIT'); a.emit('nop')
    li(a, 't0', BUFSIZE)
    a.emit('addu', 'a1', 'a0', 't0')
    scr(a, 'sw', 'zero', S_DLG)
    scr(a, 'sw', 'zero', S_MAP)
    a.emit('ori', 't0', 'zero', 1); scr(a, 'sw', 't0', S_PASS)
    walk(a, 'W1')                                 # one walk: squeeze and move (dialogue pieces are marked as they come)
    # briefing map up: unlink the lock-on dot / star (tag at base + 0xA30) and the reticle layer 0x99
    nh = L('nh'); nd2 = L('nd2')
    scr(a, 'lw', 't0', S_MAP)
    a.emit('beq', 't0', 'zero', nh); a.emit('nop')
    a.emit('lw', 't1', 0xA34, 'a0')
    li(a, 't2', 0x5A0000); a.emit('beq', 't1', 't2', nd2); a.emit('nop')
    li(a, 't2', 0x5A0600); a.emit('bne', 't1', 't2', 'HIDE99'); a.emit('nop')
    a.label(nd2)
    li(a, 't2', 0x70000000); a.emit('sw', 't2', 0xA30, 'a0')   # END tag (the chain end, as DOT's own hide does)
    a.emit('sw', 'zero', 0xA34, 'a0')
    a.label('HIDE99')
    li(a, 't1', 0x20000000); a.emit('sw', 't1', 16 * RLAYER, 'a0')
    a.emit('addiu', 't2', 'a0', 16 * (RLAYER + 1)); a.emit('sw', 't2', 16 * RLAYER + 4, 'a0')
    a.emit('beq', 'zero', 'zero', 'EXIT'); a.emit('nop')
    a.label(nh)
    # aerial reticle at half size: find its four orange dots, then halve every vertex within 64 px of their centre
    scr(a, 'sw', 'zero', S_DN); scr(a, 'sw', 'zero', S_DX1); scr(a, 'sw', 'zero', S_DY1)
    li(a, 't0', 0xFFFF); scr(a, 'sw', 't0', S_DX0); scr(a, 'sw', 't0', S_DY0)
    a.emit('ori', 't0', 'zero', 2); scr(a, 'sw', 't0', S_PASS)
    walk(a, 'W2', RLAYER)
    scr(a, 'lw', 't0', S_DN)
    a.emit('addiu', 't1', 'zero', 4); a.emit('bne', 't0', 't1', 'NODOT'); a.emit('nop')
    for lo_, hi_, c in ((S_DX0, S_DX1, S_CX), (S_DY0, S_DY1, S_CY)):
        scr(a, 'lw', 't0', lo_); scr(a, 'lw', 't1', hi_)
        a.emit('subu', 't2', 't1', 't0')
        a.emit('sltiu', 't2', 't2', 90 * 16); a.emit('beq', 't2', 'zero', 'NODOT'); a.emit('nop')
        a.emit('addu', 't0', 't0', 't1'); a.emit('srl', 't0', 't0', 1); scr(a, 'sw', 't0', c)
    a.emit('beq', 'zero', 'zero', 'PASS3'); a.emit('nop')
    a.label('NODOT')                              # no reticle found: centre 0 = every packet is "far" (rings only)
    scr(a, 'sw', 'zero', S_CX); scr(a, 'sw', 'zero', S_CY)
    a.label('PASS3')
    a.emit('ori', 't0', 'zero', 3); scr(a, 'sw', 't0', S_PASS)
    walk(a, 'W3', RLAYER)
    a.label('EXIT')
    scr(a, 'lw', 'ra', S_RA)
    a.label('QUIT')
    a.emit('jr', 'ra')
    a.emit('nop')
    a.label('NOLEVEL')                            # outside levels: forget the camera copy (a new level starts fresh)
    scr(a, 'sw', 'zero', S_VALID)
    scr(a, 'sw', 'zero', S_PREV)
    scr(a, 'sw', 'zero', S_EASE)
    a.emit('jr', 'ra')
    a.emit('nop')

    # GIF block [t6, t7)
    a.label('GIF')
    scr(a, 'sw', 'ra', S_GRA)
    a.label('GTAG')
    a.emit('sltu', 't0', 't6', 't7'); a.emit('beq', 't0', 'zero', 'GEND'); a.emit('nop')
    a.emit('lw', 't1', 0, 't6')
    a.emit('lw', 't3', 4, 't6')
    a.emit('lw', 't4', 8, 't6')
    a.emit('lw', 't5', 12, 't6')
    a.emit('andi', 't1', 't1', 0x7FFF)
    a.emit('srl', 't0', 't3', 26); a.emit('andi', 't0', 't0', 3)
    a.emit('srl', 't3', 't3', 28)
    a.emit('bne', 't3', 'zero', 'NRG'); a.emit('nop')
    a.emit('addiu', 't3', 'zero', 16)
    a.label('NRG')
    a.emit('addiu', 't6', 't6', 16)
    a.emit('addiu', 't2', 'zero', 2); a.emit('beq', 't0', 't2', 'IMG'); a.emit('nop')
    a.emit('addiu', 't2', 'zero', 1); a.emit('beq', 't0', 't2', 'RGL'); a.emit('nop')
    a.emit('beq', 't0', 'zero', 'PKD'); a.emit('nop')
    a.emit('beq', 'zero', 'zero', 'GEND'); a.emit('nop')
    a.label('IMG')
    a.emit('sll', 't2', 't1', 4); a.emit('addu', 't6', 't6', 't2')
    a.emit('beq', 'zero', 'zero', 'GTAG'); a.emit('nop')
    for lab, size, packed in (('RGL', 8, False), ('PKD', 16, True)):
        a.label(lab)
        a.emit('mult', 't1', 't3'); a.emit('mflo', 't1')
        a.emit('sll', 't2', 't1', 3 if size == 8 else 4)
        a.emit('addu', 't2', 't6', 't2')
        if size == 8:
            ev = L('ev')
            a.emit('andi', 't0', 't1', 1); a.emit('beq', 't0', 'zero', ev); a.emit('nop')
            a.emit('addiu', 't2', 't2', 8)
            a.label(ev)
        a.emit('sltu', 't0', 't7', 't2'); a.emit('bne', 't0', 'zero', 'GEND'); a.emit('nop')
        scr(a, 'sw', 't7', S_END)
        scr(a, 'sw', 't6', S_ITEMS)
        scr(a, 'sw', 't1', S_COUNT)
        scr(a, 'sw', 't2', S_NEXT)
        verts(a, size, packed)
        scr(a, 'lw', 't6', S_NEXT)
        a.emit('beq', 'zero', 'zero', 'GTAG'); a.emit('nop')
    a.label('GEND')
    scr(a, 'lw', 'ra', S_GRA)
    a.emit('jr', 'ra')
    a.emit('nop')
    return a

def patches():
    a = build()
    return [(a.base + 4 * i, w) for i, w in enumerate(a.assemble())] + [(HOOK, 0x08000000 | (HUDX >> 2))]

if __name__ == '__main__':
    a = build()
    print('cave words', len(a.items), 'ends %X' % (HUDX + 4 * len(a.items)))
    for ad, w in patches(): print('%08X %08X' % (ad, w))
