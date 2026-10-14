"""Mandala medallion: a 44 mm pendant, three layers of plump petals around a chrome pearl, with a hanging eyelet.
Pistachio & cherry: the soft-tech candy cousin of the chrome mandala loop. Modeled in millimeters; STL/OBJ export in mm,
GLB in meters. Every shell is closed, and the layers overlap on purpose (slicers union overlapping shells)."""

import math

import kit

META = dict(
    kind="model", unit="mm", printable=True, max_tris=400_000,
    size=(1080, 1080), fps=24, turntable_seconds=5, samples=96, hero_t=0.07,
    palette={"graphite": "#17181A", "pistachio": "#B9D98C", "cherry": "#C4101E", "bone": "#F4F1E8", "chrome": "#E6ECEF"},
    post=dict(bloom=0.3, bloom_threshold=0.78, vignette=0.28, grain=0.018, aberration=0.8),
    formats=["glb", "stl", "obj"],
    exposure=-0.2,
)


def build(ctx):
    P = ctx.hex
    kit.world(P["graphite"], 0.1)
    chrome = kit.chrome("chrome", P["chrome"], roughness=0.03)
    cherry = kit.enamel("cherry", P["cherry"], roughness=0.14)
    pivot, parts = ctx.pivot, ctx.model_objects

    # --- what the chrome reflects, and the floor it sits on (both scaled for a 100 mm-wide subject)
    kit.dome([(0.00, P["graphite"], 0.10), (0.32, P["graphite"], 0.20), (0.38, P["pistachio"], 1.3), (0.46, P["graphite"], 0.08),
              (0.54, P["bone"], 2.6), (0.59, P["graphite"], 0.05), (0.70, P["graphite"], 0.08), (0.76, P["bone"], 3.2),
              (0.81, P["graphite"], 0.06), (0.87, P["cherry"], 1.0), (0.92, P["bone"], 2.0), (1.00, P["graphite"], 0.12)], radius=900)
    kit.radial_backdrop([(0.0, P["graphite"], 1.0), (0.35, P["graphite"], 1.0), (0.6, P["pistachio"], 0.55), (0.85, P["pistachio"], 1.4), (1.0, P["pistachio"], 2.4)],
                        z=-3.0, radius=420)
    kit.softbox("key", (-90, -110, 150), 90, P["bone"], 230000)
    kit.softbox("strip", (120, 20, 80), 30, "#C2271F", 80000, aspect=3.2)
    kit.softbox("top", (10, 30, 190), 40, P["bone"], 60000)

    kit.camera(ctx, (0, -86, 112), target=(0, 0, 2), lens=85, fstop=6.0, focus=(0, 0, 3))

    # --- base: a domed disc with a rolled rim. Lathe axis is Y, so stand it up onto Z.
    disc = kit.lathe([(0, 1.6), (17, 1.6), (20.6, 1.1), (22, 0.0), (20.6, -1.1), (17, -1.6), (0, -1.6)], segments=96, name="base")
    kit.spawn(disc, chrome, pivot, rotation=(math.pi / 2, 0, 0), name="base", collect=parts)
    kit.spawn(kit.torus(21.2, 0.9, "rim", 128, 24), chrome, pivot, name="rim", collect=parts)
    kit.spawn(kit.torus(3.0, 1.25, "eyelet", 64, 24), chrome, pivot, location=(0, 23.6, 0), name="eyelet", collect=parts)

    # --- layer A: 12 chrome petals; layer B: 8 cherry enamel petals above them; chrome pearl heart
    for count, length, width, radius, z, phase, mat, tag in ((12, 15.5, 4.4, 5.0, 2.2, 0.0, chrome, "a"),
                                                              (8, 11.0, 3.8, 3.2, 3.8, math.pi / 8, cherry, "b")):
        for i in range(count):
            a = phase + 2 * math.pi * i / count
            m = kit.petal(length=length, width=width, flatten=0.42, sharp=1.1, belly=0.4, name=f"petal_{tag}{i}")
            kit.spawn(m, mat, pivot, (radius * math.cos(a), radius * math.sin(a), z), (0, 0, a - math.pi / 2), name=m.name, collect=parts)
    kit.spawn(kit.pearl(4.6, "heart"), chrome, pivot, (0, 0, 5.2), name="heart", collect=parts)
    for i in range(12):
        a = 2 * math.pi * (i + 0.5) / 12
        kit.spawn(kit.pearl(1.15, f"bead{i}"), cherry, pivot, (17.4 * math.cos(a), 17.4 * math.sin(a), 2.0), name=f"bead{i}", collect=parts)
