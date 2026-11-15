"""Air R2 chain: a press while the jump's takeoff is still running ([Caim+0x2EC] == 0, e.g. the 3rd slash pressed right after the 2nd
slash's re-takeoff) restarted the takeoff with the full arc (an unwanted triple jump). The chain entry 005B2540 (beq t5,zero,005B2564)
becomes j GUARD: with [Caim+0x2EC] == 0 the press is not used (the edge memory 0033F6FC is cleared so a still-held button triggers
again next frame, when the takeoff is over) and the normal path 342C4C continues; otherwise the replaced beq."""
import sys
sys.path.insert(0, r'C:\Users\shade\OneDrive\Documents\PCSX2\roms\drakengard_mod\src\lib')
from mipsasm import Asm
G = 0x5BDD40
def build():
    a = Asm(G)
    a.emit('lw', 't9', 0x2EC, 's1'); a.emit('bne', 't9', 'zero', 'GO'); a.emit('nop')
    a.emit('sw', 'zero', -2308, 't7')                      # 0033F6FC edge memory: the press stays pending
    a.emit('j', 0x342C4C); a.emit('nop')
    a.label('GO')
    a.emit('beq', 't5', 'zero', 'ZERO'); a.emit('nop')
    a.emit('j', 0x5B2548); a.emit('nop')
    a.label('ZERO')
    a.emit('j', 0x5B2564); a.emit('nop')
    return a
def patches():
    return [(G + 4 * i, w) for i, w in enumerate(build().assemble())] + [(0x5B2540, 0x08000000 | (G >> 2))]
if __name__ == '__main__':
    for ad, w in patches(): print('patch=1,EE,%08X,word,%08X' % (ad, w))
