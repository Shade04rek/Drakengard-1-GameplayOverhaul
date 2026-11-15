import sys
sys.path.insert(0, r'C:\Users\shade\AppData\Local\Temp\claude\C--Users-shade--claude-spares-spare-lRXJwn\fc7fa988-ea8f-4fa2-b5eb-1c7f92e06e80\scratchpad')
sys.path.insert(1, r'C:\Users\shade\AppData\Local\Temp\claude\C--Users-shade-AppData-Roaming-Claude-scratch-workspaces-d26a4a75-75f2-47d7-a5b0-73edfc757065-46ea55b4-1b40-4e1b-8e0f-1c92210c0291-scratch-2026-10-16-8e6b16\9242a4f5-61eb-4545-89bd-55b3ca05d106\scratchpad')
from mipsasm import Asm
GLIDE = 0x5B7500
def build_glide():
    a = Asm(GLIDE)
    a.emit('lui', 't4', 0x3B)
    a.emit('lw', 't5', -0x30C0, 't4')      # Angelus +0x20
    a.emit('addiu', 't6', 'zero', 5)
    a.emit('bne', 't5', 't6', 'OUT')
    a.emit('nop')
    a.emit('lw', 't5', -0x2D3C, 't4')      # Angelus +0x3A4
    a.emit('addiu', 't6', 'zero', 2)
    a.emit('bne', 't5', 't6', 'OUT')
    a.emit('nop')
    a.emit('lw', 't5', -0x336C, 't4')      # Caim +0x6B4
    a.emit('addiu', 't6', 'zero', 2)
    a.emit('bne', 't5', 't6', 'OUT')
    a.emit('nop')
    for off in (0x47AA, 0x47AE):
        a.emit('lhu', 't3', off, 't2')
        a.emit('ori', 't3', 't3', 2)
        a.emit('sh', 't3', off, 't2')
    a.label('OUT')
    a.emit('j', 0x321A7C)
    a.emit('nop')
    return a
HOOK = {0x5B6D28: 0x08000000 | (GLIDE >> 2)}
def patches():
    a = build_glide()
    out = [(a.base + 4 * i, w) for i, w in enumerate(a.assemble())]
    out += list(HOOK.items())
    return out
if __name__ == '__main__':
    for ad, w in patches(): print('%08X %08X' % (ad, w))

# ---------------------------------------------------------------- glide: hold velocity while the ground ride is gliding
GLM = 0x5B7600
VEL = 0x5B7780

def build_glm(test=False):
    a = Asm(GLM)
    def SQ(): a.emit('nop') if test else a.emit('sq', 't6', 0, 's3')
    def LQ(): a.emit('nop') if test else a.emit('lq', 't6', 0, 's3')
    a.emit('lui', 't0', 0x42)
    a.emit('addiu', 't0', 't0', -0x3F70)       # 0041C090 = Angelus pose block position
    a.emit('bne', 's3', 't0', 'PASS')
    a.emit('nop')
    a.emit('lui', 't1', 0x3B)
    a.emit('lw', 't2', -0x30C0, 't1')          # Angelus +0x20 = 5
    a.emit('addiu', 't3', 'zero', 5)
    a.emit('bne', 't2', 't3', 'PASS')
    a.emit('nop')
    a.emit('lw', 't2', -0x2D3C, 't1')          # Angelus +0x3A4 = 2 (ground ride)
    a.emit('addiu', 't3', 'zero', 2)
    a.emit('bne', 't2', 't3', 'PASS')
    a.emit('nop')
    a.emit('lw', 't2', -0x336C, 't1')          # Caim +0x6B4 = 2 (mounted)
    a.emit('addiu', 't3', 'zero', 2)
    a.emit('bne', 't2', 't3', 'PASS')
    a.emit('nop')
    a.emit('lwc1', 'f0', 0, 's3')              # old position
    a.emit('lwc1', 'f1', 4, 's3')
    a.emit('lwc1', 'f2', 8, 's3')
    SQ()                                       # store the new one (TERC does it again)
    a.emit('lwc1', 'f3', 0, 's3')
    a.emit('lwc1', 'f4', 4, 's3')
    a.emit('lwc1', 'f5', 8, 's3')
    a.emit('lui', 't2', 0x42)
    a.emit('lw', 't3', -0x3370, 't2')          # 0041CC90 = dragon motion id: 0x1C while the glide is on
    a.emit('addiu', 't4', 'zero', 0x1C)
    a.emit('bne', 't3', 't4', 'REC')
    a.emit('nop')
    a.emit('lui', 't5', 0x5B)
    a.emit('lwc1', 'f6', 0x7780, 't5')
    a.emit('lwc1', 'f7', 0x7784, 't5')
    a.emit('lwc1', 'f8', 0x7788, 't5')
    a.emit('add.s', 'f3', 'f0', 'f6')          # position = old + the velocity of the last flapping frame
    a.emit('add.s', 'f4', 'f1', 'f7')
    a.emit('add.s', 'f5', 'f2', 'f8')
    a.emit('lui', 't9', 0xC1A0)                # keep 20 units above the ground (y positive = down)
    a.emit('mtc1', 't9', 'f9')
    a.emit('c.olt.s', 'f9', 'f4')
    a.emit('bc1f', 'YOK')
    a.emit('nop')
    a.emit('mov.s', 'f4', 'f9')
    a.label('YOK')
    a.emit('swc1', 'f3', 0, 's3')
    a.emit('swc1', 'f4', 4, 's3')
    a.emit('swc1', 'f5', 8, 's3')
    LQ()
    a.emit('beq', 'zero', 'zero', 'TER')
    a.emit('nop')
    a.label('REC')
    a.emit('sub.s', 'f6', 'f3', 'f0')
    a.emit('sub.s', 'f7', 'f4', 'f1')
    a.emit('sub.s', 'f8', 'f5', 'f2')
    a.emit('lui', 't5', 0x5B)
    a.emit('swc1', 'f6', 0x7780, 't5')
    a.emit('swc1', 'f7', 0x7784, 't5')
    a.emit('swc1', 'f8', 0x7788, 't5')
    a.emit('beq', 'zero', 'zero', 'TER')
    a.emit('nop')
    a.label('PASS')
    a.emit('lui', 't0', 0x5B)
    a.emit('lw', 't1', 0x6400, 't0')
    a.emit('bne', 't1', 'zero', 'TERC')
    a.emit('nop')
    SQ()
    a.emit('j', 0x1B77C4)
    a.emit('nop')
    a.label('TER')
    a.emit('lui', 't0', 0x5B)
    a.emit('lw', 't1', 0x6400, 't0')
    a.emit('beq', 't1', 'zero', 'NOTERC')
    a.emit('nop')
    a.label('TERC')
    a.emit('j', 0x5B6400)
    a.emit('nop')
    a.label('NOTERC')
    a.emit('j', 0x1B77C4)
    a.emit('nop')
    return a

def glm_patches():
    a = build_glm()
    out = [(a.base + 4 * i, w) for i, w in enumerate(a.assemble())]
    out.append((0x1B77BC, 0x08000000 | (GLM >> 2)))
    return out
