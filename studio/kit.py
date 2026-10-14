"""Scene kit for pieces: everything a piece needs to look good in headless Blender, no GPU or display.

A piece (see pieces/*.py) imports this as `import kit` and only describes *what* is in the scene.
The runner (run.py) owns rendering, post, QA and export, so every piece gets them for free.

Units: motion pieces use 1 unit = 1 meter-ish, whatever reads well. Model pieces set META["unit"] = "mm"
and model in millimeters; exports convert (STL/OBJ stay mm, GLB becomes meters as the spec requires).
"""

import math
import warnings

import bpy  # first: registers bmesh and mathutils
import bmesh
from mathutils import Euler, Vector

warnings.filterwarnings("ignore", category=DeprecationWarning)  # Material.use_nodes etc.

# ------------------------------------------------------------------ color


def rgb(hex_color: str, alpha: float = 1.0) -> tuple:
    """'#F2D75B' -> linear RGBA, which is what Blender colors want."""
    h = hex_color.lstrip("#")
    srgb = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in srgb]
    return (*lin, alpha)


# ------------------------------------------------------------------ context


class Context:
    """Handed to a piece's build(ctx) and animate(ctx, t)."""

    def __init__(self, meta: dict, mode: str, size: tuple, frames: int, samples: int, device: str):
        self.meta = meta
        self.mode = mode
        self.size = size
        self.frames = frames          # frames in one loop; the loop point is frame N+1 == frame 1
        self.samples = samples
        self.device = device
        self.scene = bpy.context.scene
        self.camera = None
        self.pivot = None             # model pieces parent their objects here; the runner spins it for turntables
        self.model_objects = []       # what gets QA'd and exported
        self.palette = {k: rgb(v) for k, v in meta.get("palette", {}).items()}
        self.hex = dict(meta.get("palette", {}))


def reset() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)


def new_context(meta: dict, mode: str, size: tuple, frames: int, samples: int, device: str) -> Context:
    reset()
    ctx = Context(meta, mode, size, frames, samples, device)
    configure_render(ctx)
    ctx.pivot = bpy.data.objects.new("pivot", None)
    link(ctx.pivot)
    return ctx


def link(ob, collection=None):
    (collection or bpy.context.scene.collection).objects.link(ob)
    return ob


# ------------------------------------------------------------------ render setup


def configure_render(ctx: Context) -> None:
    sc = ctx.scene
    r = sc.render
    r.engine = "CYCLES"
    r.resolution_x, r.resolution_y = ctx.size
    r.resolution_percentage = 100
    r.fps = int(ctx.meta.get("fps", 24))
    sc.frame_start, sc.frame_end = 1, ctx.frames
    r.film_transparent = bool(ctx.meta.get("alpha"))
    r.image_settings.file_format = "PNG"
    r.image_settings.color_mode = "RGBA" if ctx.meta.get("alpha") else "RGB"
    r.image_settings.color_depth = "8"

    c = sc.cycles
    c.samples = ctx.samples
    c.use_adaptive_sampling = True
    c.adaptive_threshold = 0.02
    c.use_denoising = True
    try:
        c.denoiser = "OPENIMAGEDENOISE"
    except TypeError:
        pass
    c.max_bounces = 12
    c.glossy_bounces = 10       # chrome reflecting chrome needs depth
    c.diffuse_bounces = 3
    c.transmission_bounces = 8
    c.sample_clamp_indirect = 8.0   # kills fireflies from tiny hot reflections
    c.use_animated_seed = False     # same noise every frame, which also makes loop frames match exactly

    sc.view_settings.view_transform = ctx.meta.get("tonemap", "AgX")
    look = ctx.meta.get("look", "High Contrast")
    for candidate in (f"AgX - {look}", look, "None"):
        try:
            sc.view_settings.look = candidate
            break
        except TypeError:
            continue
    sc.view_settings.exposure = ctx.meta.get("exposure", 0.0)

    if ctx.device == "gpu":
        _enable_gpu(sc)
    else:
        c.device = "CPU"


def _enable_gpu(sc) -> None:
    prefs = bpy.context.preferences.addons["cycles"].preferences
    for backend in ("OPTIX", "CUDA", "HIP", "METAL", "ONEAPI"):
        try:
            prefs.compute_device_type = backend
            prefs.get_devices()
        except TypeError:
            continue
        gpus = [d for d in prefs.devices if d.type != "CPU"]
        if gpus:
            for d in prefs.devices:
                d.use = d.type != "CPU"
            sc.cycles.device = "GPU"
            print(f"[kit] GPU rendering via {backend}: {', '.join(d.name for d in gpus)}")
            return
    print("[kit] no GPU found, rendering on CPU")
    sc.cycles.device = "CPU"


# ------------------------------------------------------------------ world, lights, camera


def world(color: str = "#0B0906", strength: float = 1.0) -> None:
    w = bpy.data.worlds.new("world")
    w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = rgb(color)
    bg.inputs["Strength"].default_value = strength
    bpy.context.scene.world = w


def softbox(name, location, size, color, power, target=(0, 0, 0), aspect=1.0, visible=False):
    """Rectangular area light. Hidden from the camera but present in reflections, which is how chrome gets its shapes."""
    light = bpy.data.lights.new(name, "AREA")
    light.shape = "RECTANGLE"
    light.size = size
    light.size_y = size * aspect
    light.energy = power
    light.color = rgb(color)[:3]
    ob = bpy.data.objects.new(name, light)
    ob.location = location
    ob.visible_camera = visible
    link(ob)
    aim(ob, target)
    return ob


def aim(ob, target) -> None:
    if not isinstance(target, bpy.types.Object):
        t = bpy.data.objects.new(ob.name + "_target", None)
        t.location = Vector(target)
        link(t)
        target = t
    con = ob.constraints.new("TRACK_TO")
    con.target = target
    con.track_axis = "TRACK_NEGATIVE_Z"
    con.up_axis = "UP_Y"


def camera(ctx: Context, location, target=(0, 0, 0), lens=50.0, fstop=None, focus=None, sensor=36.0) -> bpy.types.Object:
    """fstop=None keeps everything sharp; a low f-stop (1.4-4) gives the selective blur. focus = object or world point."""
    cam = bpy.data.cameras.new("cam")
    cam.lens = lens
    cam.sensor_width = cam.sensor_height = sensor
    # Fit the lens to the SHORT side, so a subject framed for a square also fits 9:16 and 16:9 (extra room goes top/bottom or left/right).
    cam.sensor_fit = "HORIZONTAL" if ctx.size[0] <= ctx.size[1] else "VERTICAL"
    cam.clip_start, cam.clip_end = 0.01, 100000
    ob = bpy.data.objects.new("cam", cam)
    ob.location = location
    link(ob)
    aim(ob, target)
    if fstop:
        cam.dof.use_dof = True
        cam.dof.aperture_fstop = fstop
        if isinstance(focus, bpy.types.Object):
            cam.dof.focus_object = focus
        else:
            point = Vector(focus if focus is not None else target)
            cam.dof.focus_distance = (point - Vector(location)).length
    ctx.scene.camera = ob
    ctx.camera = ob
    return ob


# ------------------------------------------------------------------ materials


def _material(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    return m, m.node_tree.nodes["Principled BSDF"]


def _set(bsdf, name, value):
    if name in bsdf.inputs:
        bsdf.inputs[name].default_value = value


def chrome(name="chrome", tint="#E9E6E0", roughness=0.035):
    m, b = _material(name)
    _set(b, "Base Color", rgb(tint))
    _set(b, "Metallic", 1.0)
    _set(b, "Roughness", roughness)
    return m


def enamel(name, color, roughness=0.22, coat=1.0):
    """Glossy non-metal with a clear coat: the soft, candy counterpart to chrome."""
    m, b = _material(name)
    _set(b, "Base Color", rgb(color))
    _set(b, "Metallic", 0.0)
    _set(b, "Roughness", roughness)
    _set(b, "Coat Weight", coat)
    _set(b, "Coat Roughness", 0.03)
    return m


def glow(name, color, strength=4.0):
    m, b = _material(name)
    _set(b, "Base Color", rgb(color))
    _set(b, "Emission Color", rgb(color))
    _set(b, "Emission Strength", strength)
    return m


def radial_backdrop(stops, z=-2.0, radius=9.0, name="backdrop"):
    """Emissive disc facing +Z with a radial gradient. stops = [(position 0..1, '#hex', strength)], 0 = rim, 1 = center.
    Sits far behind the subject, so a low f-stop turns it into a soft glow."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    coord = nt.nodes.new("ShaderNodeTexCoord")
    grad = nt.nodes.new("ShaderNodeTexGradient")
    grad.gradient_type = "QUADRATIC_SPHERE"
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    emit = nt.nodes.new("ShaderNodeEmission")
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    elems = ramp.color_ramp.elements
    while len(elems) < len(stops):
        elems.new(0.5)
    for el, (pos, color, strength) in zip(elems, stops):
        el.position = pos
        el.color = tuple(c * strength for c in rgb(color)[:3]) + (1.0,)
    nt.links.new(coord.outputs["Object"], grad.inputs["Vector"])
    nt.links.new(grad.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], emit.inputs["Color"])
    nt.links.new(emit.outputs["Emission"], out.inputs["Surface"])
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=1.0)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    mesh.materials.append(m)
    ob = bpy.data.objects.new(name, mesh)
    ob.location = (0, 0, z)
    ob.scale = (radius, radius, 1)
    link(ob)
    return ob


def dome(stops, radius=40.0, name="dome"):
    """Invisible-to-camera emissive sphere whose vertical gradient is what chrome reflects (a studio sky).
    stops = [(height 0..1, '#hex', strength)], 0 = straight down, 1 = straight up. Close stops make hard bands."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    coord = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    to01 = nt.nodes.new("ShaderNodeMath")
    to01.operation = "MULTIPLY_ADD"
    to01.inputs[1].default_value = 0.5
    to01.inputs[2].default_value = 0.5
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    emit = nt.nodes.new("ShaderNodeEmission")
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    elems = ramp.color_ramp.elements
    while len(elems) < len(stops):
        elems.new(0.5)
    for el, (pos, color, strength) in zip(elems, sorted(stops)):
        el.position = pos
        el.color = tuple(c * strength for c in rgb(color)[:3]) + (1.0,)
    nt.links.new(coord.outputs["Object"], sep.inputs["Vector"])
    nt.links.new(sep.outputs["Z"], to01.inputs[0])
    nt.links.new(to01.outputs["Value"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], emit.inputs["Color"])
    nt.links.new(emit.outputs["Emission"], out.inputs["Surface"])
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=48, v_segments=24, radius=1.0)
    bmesh.ops.reverse_faces(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    mesh.materials.append(m)
    ob = bpy.data.objects.new(name, mesh)
    ob.scale = (radius, radius, radius)
    ob.visible_camera = False
    ob.visible_shadow = False
    link(ob)
    return ob


# ------------------------------------------------------------------ geometry


def _finish(mesh, smooth=True):
    mesh.update()
    if smooth:
        mesh.polygons.foreach_set("use_smooth", [True] * len(mesh.polygons))
        mesh.update()
    return mesh


def lathe(profile, segments=56, flatten=1.0, name="lathe"):
    """Revolve [(radius, y), ...] (tip to base, radius 0 at closed ends) around the Y axis. flatten scales Z (petals)."""
    bm = bmesh.new()
    rings = []
    for radius, y in profile:
        if radius < 1e-9:
            rings.append(bm.verts.new((0, y, 0)))
        else:
            rings.append([bm.verts.new((radius * math.cos(a), y, radius * math.sin(a) * flatten))
                          for a in (2 * math.pi * i / segments for i in range(segments))])
    for a, b in zip(rings, rings[1:]):
        for i in range(segments):
            j = (i + 1) % segments
            if isinstance(a, list) and isinstance(b, list):
                bm.faces.new((a[i], a[j], b[j], b[i]))
            elif isinstance(a, list):
                bm.faces.new((a[i], a[j], b))
            elif isinstance(b, list):
                bm.faces.new((a, b[j], b[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    return _finish(mesh)


def petal_profile(length=1.0, width=0.3, rings=48, sharp=1.7, belly=0.3):
    """Teardrop: round bulb at y=0, tapering to a point at y=length. Smooth at the belly, concave toward the tip."""
    pts = [(0.0, 0.0)]
    for i in range(1, rings):
        s = i / rings
        if s < belly:
            r = width * math.sqrt(max(0.0, 1 - ((belly - s) / belly) ** 2))
        else:
            x = (s - belly) / (1 - belly)
            r = width * (0.5 + 0.5 * math.cos(math.pi * x ** 0.85)) ** sharp
        pts.append((r, s * length))
    pts.append((0.0, length))
    return pts


def petal(length=1.0, width=0.3, flatten=0.45, sharp=1.7, belly=0.3, name="petal"):
    return lathe(petal_profile(length, width, sharp=sharp, belly=belly), flatten=flatten, name=name)


def pearl(radius=1.0, name="pearl"):
    return lathe([(0, -radius)] + [(radius * math.sin(a), -radius * math.cos(a))
                                   for a in (math.pi * i / 32 for i in range(1, 32))] + [(0, radius)], name=name)


def torus(major, minor, name="torus", major_segments=96, minor_segments=32):
    bm = bmesh.new()
    verts = [[bm.verts.new(((major + minor * math.cos(v)) * math.cos(u), (major + minor * math.cos(v)) * math.sin(u), minor * math.sin(v)))
              for v in (2 * math.pi * j / minor_segments for j in range(minor_segments))]
             for u in (2 * math.pi * i / major_segments for i in range(major_segments))]
    for i in range(major_segments):
        for j in range(minor_segments):
            i2, j2 = (i + 1) % major_segments, (j + 1) % minor_segments
            bm.faces.new((verts[i][j], verts[i2][j], verts[i2][j2], verts[i][j2]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    return _finish(mesh)


def spawn(mesh, material=None, parent=None, location=(0, 0, 0), rotation=(0, 0, 0), scale=1.0, name=None, collect=None):
    """Object sharing `mesh` data (cheap: Cycles instances it). Returns the object."""
    ob = bpy.data.objects.new(name or mesh.name, mesh)
    ob.location = location
    ob.rotation_euler = Euler(rotation)
    ob.scale = (scale, scale, scale) if isinstance(scale, (int, float)) else scale
    if material is not None and not mesh.materials:
        mesh.materials.append(material)
    elif material is not None:
        ob.material_slots[0].link = "OBJECT"
        ob.material_slots[0].material = material
    link(ob)
    if parent is not None:
        ob.parent = parent
    if collect is not None:
        collect.append(ob)
    return ob


def empty(name, parent=None, location=(0, 0, 0)):
    ob = bpy.data.objects.new(name, None)
    ob.location = location
    link(ob)
    if parent is not None:
        ob.parent = parent
    return ob


def ring_of(count, radius, make, phase=0.0, parent=None):
    """Radial symmetry: make(index, angle, position_xy) -> object, placed on a circle in the XY plane."""
    out = []
    for i in range(count):
        a = phase + 2 * math.pi * i / count
        ob = make(i, a, (radius * math.cos(a), radius * math.sin(a)))
        if parent is not None and ob.parent is None:
            ob.parent = parent
        out.append(ob)
    return out


def lerp(a, b, t):
    return a + (b - a) * t


def ease(t):
    """Smoothstep in, smoothstep out. Feed it 0..1."""
    return t * t * (3 - 2 * t)


def loop_sin(t, cycles=1, phase=0.0):
    """Periodic in t over one loop: sin goes round `cycles` whole times, so frame N+1 matches frame 1."""
    return math.sin(2 * math.pi * (cycles * t + phase))
