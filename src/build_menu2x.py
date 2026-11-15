import sys
sys.path.insert(0, r'C:\Users\shade\AppData\Local\Temp\claude\C--Users-shade--claude-spares-spare-lRXJwn\fc7fa988-ea8f-4fa2-b5eb-1c7f92e06e80\scratchpad')
sys.path.insert(1, r'C:\Users\shade\AppData\Local\Temp\claude\C--Users-shade-AppData-Roaming-Claude-scratch-workspaces-d26a4a75-75f2-47d7-a5b0-73edfc757065-46ea55b4-1b40-4e1b-8e0f-1c92210c0291-scratch-2026-10-16-8e6b16\9242a4f5-61eb-4545-89bd-55b3ca05d106\scratchpad')
from mipsasm import Asm

class Asm2(Asm):
    def enc(self, it, pc):
        if it[0] == 'word': return it[1]
        return super().enc(it, pc)

DBL = 0x5B7600
EXTRA = 3                     # extra Execute calls per frame in menus: 3 = 4x speed
JALR_V0 = 0x0040F809          # jalr ra,v0
# tasks whose Execute runs twice while a menu mode is active
WHITELIST = {
    0x53A798: 'CGameCoreTask', 0x546AB0: 'CFadeMan',
}
# a menu mode is active when one of these mode tasks has state word 0 (all are 1 during gameplay)
MODE_TASKS = [(0x3C, -0x6890, 'CTitleTask 003B9770'), (0x3C, -0x6750, 'CGWorldMapModeTask 003B98B0'),
              (0x3C, -0x6C48, 'CGResultModeTask 003B93B8'), (0x3C, -0x69C0, 'CGTitleCallTask 003B9640'),
              (0x34, 0x2E38, 'CGArmsModeTask 00342E38')]

def build_dbl():
    a = Asm2(DBL)
    a.emit('addiu', 'sp', 'sp', -0x30)
    a.emit('sw', 'ra', 0x20, 'sp')
    a.emit('sw', 'a0', 0x10, 'sp')
    a.emit('sw', 'a1', 0x14, 'sp')
    a.emit('sw', 'v0', 0x18, 'sp')
    a.emit('word', JALR_V0)                    # first, normal call of task->Execute(arg)
    a.emit('nop')
    a.emit('beq', 'v0', 'zero', 'DONE')        # the task finished: never call it again
    a.emit('nop')
    for hi, off, _ in MODE_TASKS:
        a.emit('lui', 't1', hi)
        a.emit('lw', 't2', off, 't1')
        a.emit('beq', 't2', 'zero', 'MENU')
        a.emit('nop')
    a.emit('beq', 'zero', 'zero', 'DONE')
    a.emit('nop')
    a.label('MENU')
    a.emit('lw', 't0', 0x120, 's0')            # vtable of this task (s0 = task node in the scheduler)
    for vt in WHITELIST:
        a.emit('lui', 't3', vt >> 16)
        a.emit('ori', 't3', 't3', vt & 0xFFFF)
        a.emit('beq', 't0', 't3', 'AGAIN')
        a.emit('nop')
    a.emit('beq', 'zero', 'zero', 'DONE')
    a.emit('nop')
    a.label('AGAIN')
    a.emit('addiu', 't4', 'zero', EXTRA)
    a.emit('sw', 't4', 0x1C, 'sp')             # extra calls left (callee may clobber t4)
    a.label('LOOP')
    a.emit('lw', 'a0', 0x10, 'sp')
    a.emit('lw', 'a1', 0x14, 'sp')
    a.emit('lw', 'v0', 0x18, 'sp')
    a.emit('word', JALR_V0)                    # extra call in the same frame
    a.emit('nop')
    a.emit('beq', 'v0', 'zero', 'DONE')        # the task finished: stop
    a.emit('nop')
    a.emit('lw', 't4', 0x1C, 'sp')
    a.emit('addiu', 't4', 't4', -1)
    a.emit('sw', 't4', 0x1C, 'sp')
    a.emit('bne', 't4', 'zero', 'LOOP')
    a.emit('nop')
    a.label('DONE')
    a.emit('lw', 'ra', 0x20, 'sp')
    a.emit('addiu', 'sp', 'sp', 0x30)
    a.emit('jr', 'ra')
    a.emit('nop')
    return a

def patches():
    a = build_dbl()
    out = [(a.base + 4 * i, w) for i, w in enumerate(a.assemble())]
    out.append((0x27E380, 0x0C000000 | (DBL >> 2)))   # jalr ra,v0 -> jal DBL (delay slot addu a0,s0,a0 still runs)
    return out

if __name__ == '__main__':
    for ad, w in patches(): print('%08X %08X' % (ad, w))
