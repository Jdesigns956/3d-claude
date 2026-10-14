"""Chrome mandala loop. Butter & oxblood: warm liquid-silver petals in a ring of rings, each petal tip carrying its own
small rosette, layered in depth and pulled apart by a low f-stop. Loops seamlessly: every ring turns a whole number of
petal pitches per loop, so the last frame lands exactly on the first."""

import math

import kit

META = dict(
    kind="motion", size=(1080, 1080), fps=24, seconds=4, samples=96,
    palette={"ink": "#0D0806", "butter": "#F4D35E", "oxblood": "#6A0F1C", "bone": "#F3EBDC", "chrome": "#E4EAF0", "saffron": "#E3A817"},
    post=dict(bloom=0.5, bloom_threshold=0.68, aberration=1.2, vignette=0.32, grain=0.022),
    exposure=-0.3,
)

RINGS = []   # (empty, base_z, pitches_per_loop, petal_count)
ROSETTES = []
PEARL = []


def build(ctx):
    P = ctx.hex
    kit.world(P["ink"], 0.15)
    chrome = kit.chrome("chrome", P["chrome"])
    blood = kit.enamel("oxblood", P["oxblood"], roughness=0.16)
    butter = kit.enamel("butter", P["saffron"], roughness=0.2)
    # What chrome reflects: mostly dark, with a few crisp bright bands. Contrast inside the reflection is what reads as chrome.
    kit.dome([(0.00, P["ink"], 0.10), (0.30, P["ink"], 0.15), (0.36, P["oxblood"], 1.3), (0.43, P["ink"], 0.08),
              (0.52, P["bone"], 2.6), (0.57, P["ink"], 0.05), (0.68, P["ink"], 0.08), (0.74, P["bone"], 3.2),
              (0.79, P["ink"], 0.06), (0.85, P["oxblood"], 1.0), (0.90, P["bone"], 2.0), (1.00, P["ink"], 0.12)])
    kit.radial_backdrop([(0.0, P["ink"], 1.0), (0.3, P["ink"], 1.0), (0.55, P["oxblood"], 0.55), (0.82, P["oxblood"], 1.1), (0.93, P["butter"], 1.6), (1.0, P["butter"], 3.0)], z=-1.2, radius=14)

    # softboxes: these shapes are what the chrome reflects
    kit.softbox("key_bone", (-3.6, -2.2, 5.2), 3.4, P["bone"], 900)
    kit.softbox("strip_oxblood", (4.2, 0.8, 3.0), 1.1, "#C2271F", 500, aspect=3.4)
    kit.softbox("top_bone", (0.4, 1.6, 6.4), 1.4, P["bone"], 400)
    kit.softbox("kick_bone", (-2.8, 3.6, 1.6), 0.9, P["bone"], 300, aspect=2.2)

    kit.camera(ctx, (0.0, -3.6, 6.8), target=(0, 0, 0), lens=50, fstop=1.4, focus=(0, 0, 0.15))

    # --- ring 1: 8 big chrome petals
    big = kit.petal(length=1.25, width=0.43, flatten=0.6, sharp=1.1, belly=0.4, name="petal_big")
    ring1 = kit.empty("ring1")
    for i in range(8):
        a = 2 * math.pi * i / 8
        kit.spawn(big, chrome, ring1, (0.38 * math.cos(a), 0.38 * math.sin(a), 0.0), (0, 0, a - math.pi / 2))
        # recursion: a small rosette sits on each tip
        tip = 0.38 + 1.25 + 0.1
        rosette = kit.empty(f"rosette_{i}", ring1, (tip * math.cos(a), tip * math.sin(a), 0.08))
        mini = kit.petal(length=0.3, width=0.1, flatten=0.6, sharp=1.1, belly=0.4, name="petal_mini")
        for j in range(6):
            b = 2 * math.pi * j / 6
            kit.spawn(mini, chrome if j % 2 == 0 else butter, rosette, (0.04 * math.cos(b), 0.04 * math.sin(b), 0), (0, 0, b - math.pi / 2))
        ROSETTES.append(rosette)
    RINGS.append((ring1, 0.18, 1, 8))

    # --- ring 2: 16 oxblood enamel petals peeking between the tips, one layer down
    mid = kit.petal(length=1.0, width=0.27, flatten=0.6, sharp=1.1, belly=0.4, name="petal_mid")
    ring2 = kit.empty("ring2")
    for i in range(16):
        a = 2 * math.pi * i / 16 + math.pi / 16
        kit.spawn(mid, blood, ring2, (1.05 * math.cos(a), 1.05 * math.sin(a), 0), (0, 0, a - math.pi / 2))
    RINGS.append((ring2, -0.12, -2, 16))

    # --- ring 3: 24 slim butter petals, furthest back and softest
    slim = kit.petal(length=0.8, width=0.17, flatten=0.6, sharp=1.1, belly=0.4, name="petal_slim")
    ring3 = kit.empty("ring3")
    for i in range(24):
        a = 2 * math.pi * i / 24
        kit.spawn(slim, butter if i % 2 else chrome, ring3, (1.6 * math.cos(a), 1.6 * math.sin(a), 0), (0, 0, a - math.pi / 2))
    RINGS.append((ring3, -0.42, 2, 24))   # even pitch count: petals alternate material, odd would swap them at the seam

    # --- heart and halo
    pearl = kit.pearl(0.46, "heart")
    PEARL.append(kit.spawn(pearl, chrome, None, (0, 0, 0.42)))
    bead = kit.pearl(0.12, "bead")
    for i in range(8):
        a = 2 * math.pi * i / 8 + math.pi / 8
        kit.spawn(bead, blood, ring1, (0.62 * math.cos(a), 0.62 * math.sin(a), 0.2))
    kit.spawn(kit.torus(2.35, 0.05, "halo"), chrome, None, (0, 0, -0.6))
    kit.spawn(kit.torus(1.98, 0.025, "halo_inner"), butter, None, (0, 0, -0.5))


def animate(ctx, t):
    tau = 2 * math.pi
    for k, (ring, base_z, pitches, count) in enumerate(RINGS):
        ring.rotation_euler[2] = tau / count * pitches * t       # whole pitches per loop = seamless
        ring.location[2] = base_z + 0.07 * kit.loop_sin(t, 1, k / 3)
    # Rosettes ride on ring 1, so they inherit its 45 degrees. Their world turn has to be a multiple of 120 (6 petals,
    # alternating colors) to loop, so the local spin is the 240 we want minus what the ring already gives them.
    for r in ROSETTES:
        r.rotation_euler[2] = math.radians(240 - 360 / 8) * t
    s = 1 + 0.07 * kit.loop_sin(t, 2)
    PEARL[0].scale = (s, s, s)
    ctx.camera.location[0] = 0.35 * kit.loop_sin(t, 1)
