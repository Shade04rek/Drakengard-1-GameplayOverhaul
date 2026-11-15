"""Allies get their own attack animation speed: Leonard (player object +0x920 = word 003ACF00 = 0x6A) 1.5x, Seere (0x6B) 1.0x
(unchanged), Arioch (0x6C) 1.25x; Caim (0) and everyone else use the real table.
FUN_0017E464 (a0 = row, returns the row pointer of the current animation parameter table; callers read the playback rate,
halfword 1 of the 16-byte row, from it). Its lw v0,-14184(gp) becomes j ARI. For Leonard / Arioch ARI copies the 86-row
table to SH (005BD000) with the rates of rows 1..32 (attack clips 0x69..0x88) raised and returns the copy."""
import sys
sys.path.insert(0, r'C:\Users\shade\OneDrive\Documents\PCSX2\roms\drakengard_mod\src\lib')
from mipsasm import Asm
ARI = 0x5BD600
SH = 0x5BD000
HOOK = 0x17E468
def scale(a, shift, tag):
    a.emit('lui', 't1', 0x5B); a.emit('ori', 't1', 't1', (SH + 16) & 0xFFFF); a.emit('addiu', 't3', 'zero', 32)
    a.label(tag)
    a.emit('lhu', 't4', 2, 't1'); a.emit('srl', 't2', 't4', shift); a.emit('addu', 't4', 't4', 't2'); a.emit('sh', 't4', 2, 't1')
    a.emit('addiu', 't3', 't3', -1)
    a.emit('bne', 't3', 'zero', tag); a.emit('addiu', 't1', 't1', 16)
def build():
    a = Asm(ARI)
    a.emit('lw', 'v0', -14184, 'gp')
    a.emit('lui', 't0', 0x3B); a.emit('lw', 't0', -0x3100, 't0')       # 003ACF00: 0 = Caim, 0x6A Leonard, 0x6B Seere, 0x6C Arioch
    a.emit('addiu', 't0', 't0', -0x6A)                                  # t0: 0 Leonard, 1 Seere, 2 Arioch
    a.emit('sltiu', 't5', 't0', 3); a.emit('beq', 't5', 'zero', 'OUT'); a.emit('nop')
    a.emit('addiu', 't5', 't0', -1); a.emit('beq', 't5', 'zero', 'OUT'); a.emit('nop')    # Seere: no change
    a.emit('lui', 't1', 0x5B); a.emit('ori', 't1', 't1', SH & 0xFFFF)
    a.emit('or', 't2', 'v0', 'zero'); a.emit('addiu', 't3', 'zero', 344)
    a.label('LOOP')
    a.emit('lw', 't4', 0, 't2'); a.emit('sw', 't4', 0, 't1')
    a.emit('addiu', 't2', 't2', 4); a.emit('addiu', 't3', 't3', -1)
    a.emit('bne', 't3', 'zero', 'LOOP'); a.emit('addiu', 't1', 't1', 4)
    a.emit('bne', 't0', 'zero', 'ARIO'); a.emit('nop')
    scale(a, 1, 'L1')                                                   # Leonard: +50%
    a.emit('beq', 'zero', 'zero', 'DONE'); a.emit('nop')
    a.label('ARIO')
    scale(a, 2, 'L2')                                                   # Arioch: +25%
    a.label('DONE')
    a.emit('lui', 'v0', 0x5B); a.emit('ori', 'v0', 'v0', SH & 0xFFFF)
    a.label('OUT')
    a.emit('sll', 'a0', 'a0', 4)
    a.emit('jr', 'ra'); a.emit('addu', 'v0', 'v0', 'a0')
    return a
def patches():
    return [(ARI + 4 * i, w) for i, w in enumerate(build().assemble())] + [(HOOK, 0x08000000 | (ARI >> 2))]
if __name__ == '__main__':
    for ad, w in patches(): print('patch=1,EE,%08X,word,%08X' % (ad, w))
