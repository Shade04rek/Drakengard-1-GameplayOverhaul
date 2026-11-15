# Drakengard Overhaul – Version 4

Game: Drakengard (NTSC-U)

File: SLUS-20732_9679D44C.pnach

Copy the .pnach file into PCSX2\cheats\ or PCSX2\patches\.


This is a gameplay, camera, UI, and rendering overhaul for Drakengard(PS2), packaged into a simple PCSX2 .pnach cheat file.


# Features

-Sprint and super sprint
-Auto-attack
-R3 lock-on
-Ground and aerial Angelus rework
-Air dash, double-jump, and slash-jump chains
-Block projectiles, block counter attack
-Faster animations
-Quick menu, 360 camera, widescreen HUD , FOV
-Farther render distance on aerial stages
-Enemy spawn radius
-Many other tweaks


# Controls/Mapping

................................
Ground Stage - Caim
................................

Cross: Jump, Double Jump (don't attempt to jump oob, for combat only)

Triangle: Weapon Select

Square: Dodge Left (hold any direction to dodge any direction. only neutral dodges left)

Circle: Dodge Right (hold any direction to dodge any direction. only neutral dodges right)

L1: summon Ally

L2: Block (can counterattack with R1 and R2 after blocking non-projectile attack)

L3: Sprint (over 5 seconds of sprinting, speed increases to max speed. Additional L3 presses during sprint activates temporary sprint-bursts)

R1: Spell, Dump vertical-chop, Double jump heavy vertical-chop, Buffer on ground for ground vertical-chop

R2: Attack (hold to automatically perform attack combo.), Jump slice chain

R3: Enemy targeting (Use situationally. slightly jank with large enemy groups)

Start: Pause

Select: Map/Status

D-Up: Summon Angelus

D-Left: Toggle Enemy HP Bar


................................
Ground Stage - Angelus
................................

..........FAST-MODE.............

Right-stick-down during Fast-flight Mode: Bombing camera

Cross: Lock-height while held

Triangle: Turn-Around

Square: Dodge Left 

Circle: Dodge Right

L1: N/A

L2: Boost

L3: Drift

R1: Spell

R2: Attack

R3: Toggle Flight Mode

Start: Pause

Select: Map/Status

D-Up: Unmount Angelus

D-Left: Toggle Enemy HP Bar

..........FREE-MODE.............

Left Stick: Move Forward/Back/Left/Right

Right Stick: Aim/Steer

Cross: Brake

Triangle: Turn-Around

Square: Dodge Left 

Circle: Dodge Right

L1: Lift

L2: Boost

L3: Dodge Left/Right

R1: Spell

R2: Attack

R3: Toggle Flight Mode

Start: Pause

Select: Map/Status

D-Up: Unmount Angelus

D-Left: Toggle Enemy HP Bar


................................
Aerial Stage - Angelus
................................

Cross: Auto-aim targeted enemy, but only while held during "Drift".

Triangle: Turn Around

Square: Dodge Left 

Circle: Dodge Right

L1: N/A

L2: Boost

L3: Drift

R1: Spell

R2: Attack

R3: Target Enemy

Start: Pause

Select: Map/Status

D-Left: Toggle Enemy HP Bar


### Notes

---These are default controls since some mappings cannot be tied to in-game mapping system, such as d-pad buttons, though some face buttons and R1,R2,L1,L2 may be safely remapped.

---If performance drops from too many surrounding enemies, toggling off enemy health bars may help reduce the fps hit.

---Can not be dismounted from Angelus if above 50% health. Below 50% gives a 25% chance to be dismounted by any projectile. Below 25% gives a 50% chance to be dismounted.

--- **Leave PCSX2's built-in "Widescreen 16:9" game patch OFF**: the pnach contains its own widescreen and widescreen HUD (inside *Display, HUD and menus*). Set the PCSX2 aspect ratio to **16:9**.

--- Start from a **full boot** (not a save state made before the pnach was applied) – the mod hooks code and memory that are set up at boot.


### Tested configuration

- CPU: Intel Core i7-13620H (10 cores / 16 threads), 32 GB RAM
- GPU: NVIDIA GeForce RTX 4060 Laptop GPU
- PCSX2: Vulkan renderer, 3x internal resolution, 16x anisotropic, mipmaps on, VSync on, FXAA on
- The mod's render distance and per-frame work are light; the settings above are not a minimum, they are what it was developed on.
