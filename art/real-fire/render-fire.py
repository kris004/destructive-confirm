# SPDX-License-Identifier: GPL-3.0-or-later
"""Render rising fluid fire with Blender 5.0, not animated ribbon geometry.

blender --background --factory-startup --disable-autoexec --threads 4 \
  --python-exit-code 1 --python art/real-fire/render-fire.py -- \
  --output /tmp/fire/frames --cache /tmp/fire/fluid [--frames 4,36,90]
"""

import argparse
import math
import os
from pathlib import Path
import random
import sys

import bpy

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fire_config import (
    FPS, INTRO, LOOP, WIDTH, HEIGHT, HALF_WIDTH, HALF_HEIGHT, RADIUS,
    SPARK_HOLD, SWEEP_TIME, PIXELS_PER_UNIT,
)

PERIMETER = 4 * (HALF_WIDTH + HALF_HEIGHT - 2 * RADIUS) + math.tau * RADIUS


def perimeter_position(fraction):
    distance = (fraction % 1) * PERIMETER
    cx, cy = HALF_WIDTH - RADIUS, HALF_HEIGHT - RADIUS
    quarter = math.pi * RADIUS / 2

    def arc(x, y, angle):
        nx, ny = math.cos(angle), math.sin(angle)
        return x + RADIUS * nx, y + RADIUS * ny, nx, ny

    segments = [
        (2 * cx, lambda d: (-cx + d, HALF_HEIGHT, 0, 1)),
        (quarter, lambda d: arc(cx, cy, math.pi / 2 - d / RADIUS)),
        (2 * cy, lambda d: (HALF_WIDTH, cy - d, 1, 0)),
        (quarter, lambda d: arc(cx, -cy, -d / RADIUS)),
        (2 * cx, lambda d: (cx - d, -HALF_HEIGHT, 0, -1)),
        (quarter, lambda d: arc(-cx, -cy, -math.pi / 2 - d / RADIUS)),
        (2 * cy, lambda d: (-HALF_WIDTH, -cy + d, -1, 0)),
        (quarter, lambda d: arc(-cx, cy, math.pi - d / RADIUS)),
    ]
    for length, evaluate in segments:
        if distance <= length:
            return evaluate(distance)
        distance -= length
    return -cx, HALF_HEIGHT, 0, 1


def smooth(value):
    value = max(0, min(1, value))
    return value * value * (3 - 2 * value)


def emission_material(name, color, strength):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.node_tree.nodes.clear()
    emission = mat.node_tree.nodes.new("ShaderNodeEmission")
    emission.inputs["Color"].default_value = (*color, 1)
    emission.inputs["Strength"].default_value = strength
    output = mat.node_tree.nodes.new("ShaderNodeOutputMaterial")
    mat.node_tree.links.new(emission.outputs[0], output.inputs["Surface"])
    return mat


def flame_material():
    mat = bpy.data.materials.new("Fluid flame blackbody emission")
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    nodes.clear()
    field = nodes.new("ShaderNodeAttribute")
    field.attribute_name = "flame"

    def math_node(operation, a, b):
        node = nodes.new("ShaderNodeMath")
        node.operation = operation
        for i, value in enumerate((a, b)):
            if isinstance(value, (int, float)):
                node.inputs[i].default_value = value
            else:
                links.new(value, node.inputs[i])
        return node.outputs[0]

    strength = math_node("MULTIPLY", field.outputs["Fac"], 12)
    temperature = math_node("ADD", math_node(
        "MULTIPLY", field.outputs["Fac"], 1900), 1250)
    color = nodes.new("ShaderNodeBlackbody")
    links.new(temperature, color.inputs[0])
    volume = nodes.new("ShaderNodeVolumePrincipled")
    volume.inputs["Density Attribute"].default_value = ""
    links.new(math_node("MULTIPLY", field.outputs["Fac"], 2), volume.inputs["Density"])
    volume.inputs["Color"].default_value = (0, 0, 0, 1)
    volume.inputs["Blackbody Intensity"].default_value = 0
    links.new(strength, volume.inputs["Emission Strength"])
    links.new(color.outputs[0], volume.inputs["Emission Color"])
    output = nodes.new("ShaderNodeOutputMaterial")
    links.new(volume.outputs["Volume"], output.inputs["Volume"])
    return mat


def setup_compositor(scene):
    tree = bpy.data.node_groups.new("Transparent fluid fire glow", "CompositorNodeTree")
    tree.interface.new_socket(name="Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    scene.compositing_node_group = tree
    nodes, links = tree.nodes, tree.links
    source = nodes.new("CompositorNodeRLayers")
    glare = nodes.new("CompositorNodeGlare")
    glare.inputs["Type"].default_value = "Fog Glow"
    glare.inputs["Quality"].default_value = "High"
    glare.inputs["Threshold"].default_value = 1.0
    glare.inputs["Size"].default_value = 0.12
    glare.inputs["Strength"].default_value = 0.3
    links.new(source.outputs["Image"], glare.inputs["Image"])
    luminance = nodes.new("CompositorNodeRGBToBW")
    links.new(glare.outputs["Image"], luminance.inputs[0])
    separate = nodes.new("CompositorNodeSeparateColor")
    links.new(source.outputs["Image"], separate.inputs[0])
    alpha = nodes.new("ShaderNodeMath")
    alpha.operation = "MAXIMUM"
    alpha.use_clamp = True
    links.new(separate.outputs["Alpha"], alpha.inputs[0])
    links.new(luminance.outputs[0], alpha.inputs[1])
    combine = nodes.new("CompositorNodeSetAlpha")
    combine.inputs["Type"].default_value = "Replace Alpha"
    links.new(glare.outputs["Image"], combine.inputs["Image"])
    links.new(alpha.outputs[0], combine.inputs["Alpha"])
    output = nodes.new("NodeGroupOutput")
    links.new(combine.outputs[0], output.inputs["Image"])


def setup_scene(args, end):
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    scene = bpy.context.scene
    scene.frame_start, scene.frame_end = 1, end
    scene.render.fps = FPS
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = args.samples
    scene.cycles.use_denoising = True
    scene.cycles.volume_step_rate = 0.5
    scene.render.threads_mode = "FIXED"
    scene.render.threads = 4
    scene.render.resolution_x, scene.render.resolution_y = WIDTH, HEIGHT
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "8"
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.exposure = -1.2
    scene.world.color = (0, 0, 0)
    camera_data = bpy.data.cameras.new("Fire artwork camera")
    camera = bpy.data.objects.new("Camera", camera_data)
    bpy.context.collection.objects.link(camera)
    camera.location = (0, -4, 0)
    camera.rotation_euler = (math.pi / 2, 0, 0)
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = WIDTH / PIXELS_PER_UNIT
    scene.camera = camera
    setup_compositor(scene)

    # The domain is shallow, but the buoyant fire is a real 3D gas simulation.
    bpy.ops.mesh.primitive_cube_add(size=1)
    domain = bpy.context.object
    domain.name = "Buoyant turbulent fire"
    domain.dimensions = (3.2, 0.3, 1.6)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    modifier = domain.modifiers.new("Fire domain", "FLUID")
    modifier.fluid_type = "DOMAIN"
    settings = modifier.domain_settings
    settings.domain_type = "GAS"
    settings.resolution_max = args.resolution
    settings.use_adaptive_domain = False
    settings.use_noise = True
    settings.noise_scale = 2
    settings.noise_strength = 1.0
    settings.vorticity = 0.15
    settings.flame_vorticity = 0.5
    settings.burning_rate = 1.5
    settings.flame_smoke = 0
    settings.cache_type = "ALL"
    settings.cache_frame_start, settings.cache_frame_end = 1, end
    settings.cache_directory = str(args.cache)
    domain.data.materials.append(flame_material())

    # Independent emitters stay lit after the ignition front passes them.
    # No sinusoidal "tongue" meshes are used to make the burning flames.
    count = 64
    for index in range(count):
        fraction = index / count
        x, z, _, _ = perimeter_position(fraction)
        bpy.ops.mesh.primitive_ico_sphere_add(
            subdivisions=1, radius=0.027,
            location=(x / PIXELS_PER_UNIT, 0, z / PIXELS_PER_UNIT))
        emitter = bpy.context.object
        emitter.name = f"Fuel {index:02d}"
        emitter.visible_camera = False
        emitter.visible_shadow = False
        flow_modifier = emitter.modifiers.new("Fuel inflow", "FLUID")
        flow_modifier.fluid_type = "FLOW"
        flow = flow_modifier.flow_settings
        flow.flow_type = "FIRE"
        flow.flow_behavior = "INFLOW"
        flow.fuel_amount = 1.2 + 0.18 * math.sin(index * 2.39996)
        flow.surface_distance = 1.5
        # Invert the smooth sweep to match the visible ignition spark.
        low, high = 0.0, 1.0
        for _ in range(24):
            middle = (low + high) / 2
            if smooth(middle) < fraction:
                low = middle
            else:
                high = middle
        start = 1 + round((SPARK_HOLD + SWEEP_TIME * (low + high) / 2) * FPS)
        flow.use_inflow = False
        flow.keyframe_insert(data_path="use_inflow", frame=1)
        flow.keyframe_insert(data_path="use_inflow", frame=start - 1)
        flow.use_inflow = True
        flow.keyframe_insert(data_path="use_inflow", frame=start)

    # Hold out the face; fire belongs outside the native button and its label.
    points = [perimeter_position(i / 128) for i in range(128)]
    mesh = bpy.data.meshes.new("Native face alpha hole")
    mesh.from_pydata([(x / PIXELS_PER_UNIT, -0.19, z / PIXELS_PER_UNIT)
                      for x, z, _, _ in points], [], [tuple(range(128))])
    face = bpy.data.objects.new("Transparent native button face", mesh)
    bpy.context.collection.objects.link(face)
    mat = bpy.data.materials.new("Native face holdout")
    mat.use_nodes = True
    mat.node_tree.nodes.clear()
    holdout = mat.node_tree.nodes.new("ShaderNodeHoldout")
    output = mat.node_tree.nodes.new("ShaderNodeOutputMaterial")
    mat.node_tree.links.new(holdout.outputs[0], output.inputs["Surface"])
    face.data.materials.append(mat)

    hot = emission_material("White-hot ignition", (1, 0.82, 0.45), 10)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8, radius=1)
    head = bpy.context.object
    head.name = "Ignition spark"
    head.data.materials.append(hot)
    sparks = []
    rng = random.Random(7441)
    for index in range(12):
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=1)
        obj = bpy.context.object
        obj.name = f"Ignition ember {index:02d}"
        obj.data.materials.append(hot)
        sparks.append((obj, rng.uniform(0, math.tau), rng.uniform(8, 26)))
    scene.frame_set(1)
    return scene, domain, head, sparks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--frames", help="Optional comma-separated preview indices")
    parser.add_argument("--resolution", type=int, default=128)
    parser.add_argument("--samples", type=int, default=32)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    args.cache = args.cache.resolve()
    args.output = args.output.resolve()
    # A real checkout has either a gitdir file or a .git directory with HEAD.
    if any((p / ".git").is_file() or (p / ".git/HEAD").is_file()
           for p in (args.cache, *args.cache.parents)):
        parser.error("Put disposable fluid caches outside Git worktrees")
    if args.cache.exists() and any(args.cache.iterdir()):
        parser.error("Use a fresh cache directory for each bake")
    frames = (list(range(INTRO + LOOP)) if not args.frames else
              [int(value) for value in args.frames.split(",")])
    if any(frame < 0 or frame >= INTRO + LOOP for frame in frames):
        parser.error(f"Frame indices must be between 0 and {INTRO + LOOP - 1}")
    args.cache.mkdir(parents=True, exist_ok=True)
    args.output.mkdir(parents=True, exist_ok=True)
    # Mantaflow also writes a reusable wavelet-noise tile in the working dir.
    os.chdir(args.cache)
    scene, domain, head, sparks = setup_scene(args, max(frames) + 1)
    bpy.context.view_layer.objects.active = domain
    domain.select_set(True)
    bpy.ops.wm.save_as_mainfile(filepath=str(args.cache / "render.blend"))
    print("FIRE_BAKE_START", flush=True)
    bpy.ops.fluid.bake_all()
    print("FIRE_BAKE_DONE", flush=True)
    for frame in frames:
        scene.frame_set(frame + 1)
        time = frame / FPS
        progress = smooth((time - SPARK_HOLD) / SWEEP_TIME)
        x, z, nx, nz = perimeter_position(progress)
        fade = 1 - smooth((time - SPARK_HOLD - SWEEP_TIME) / 0.3)
        pulse = 1 + 0.2 * math.sin(time * 20) * math.exp(-time * 2)
        head.location = ((x + nx * 8) / PIXELS_PER_UNIT, -0.2,
                         (z + nz * 8) / PIXELS_PER_UNIT)
        size = 7 * fade * pulse / PIXELS_PER_UNIT
        head.scale = (size, size, size)
        head.hide_render = fade < 0.01
        for index, (obj, angle, speed) in enumerate(sparks):
            distance = ((time + index / 12) % 1) * speed * 1.7
            obj.location = ((x + math.cos(angle) * distance) / PIXELS_PER_UNIT,
                            -0.2, (z + 8 + math.sin(angle) * distance) / PIXELS_PER_UNIT)
            size = fade * (1.2 + 0.5 * math.sin(index)) / PIXELS_PER_UNIT
            obj.scale = (size, size, size * 2.5)
            obj.hide_render = size < 0.0001
        scene.render.filepath = str(args.output / f"{frame:03d}.png")
        bpy.ops.render.render(write_still=True)
        print(f"FIRE_FRAME {frame:03d}", flush=True)


if __name__ == "__main__":
    main()
