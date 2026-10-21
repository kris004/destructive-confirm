# SPDX-License-Identifier: GPL-3.0-or-later
"""Render the original fire-border artwork with Blender 5.0.

Run with Blender's --background --factory-startup --python, then pass:
    -- --output /tmp/fire-frames [--frames 4,36,90]

The scene is procedural and deterministic. No simulation cache, downloaded
textures, add-ons, user startup scene, or external assets are needed.
"""

import argparse
import math
from pathlib import Path
import random
import sys

import bpy
from mathutils import Vector

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fire_config import (
    FPS, INTRO, LOOP, WIDTH, HEIGHT, RADIUS, HALF_WIDTH, HALF_HEIGHT,
    FLAME_HEIGHT_MIN, FLAME_HEIGHT_MAX, SPARK_HOLD, SWEEP_TIME,
)

PERIMETER = 4 * (HALF_WIDTH + HALF_HEIGHT - 2 * RADIUS) + math.tau * RADIUS
RNG = random.Random(61208)
ROWS = 24


def perimeter_position(fraction):
    """Clockwise rounded rectangle, starting at the top-left tangent."""
    distance = (fraction % 1.0) * PERIMETER
    cx, cy = HALF_WIDTH - RADIUS, HALF_HEIGHT - RADIUS
    quarter = math.pi / 2 * RADIUS
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


def arc(x, y, angle):
    nx, ny = math.cos(angle), math.sin(angle)
    return x + RADIUS * nx, y + RADIUS * ny, nx, ny


def smooth(value):
    value = max(0.0, min(1.0, value))
    return value * value * (3 - 2 * value)


def emission_material(name, color, strength):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    emission = nodes.new("ShaderNodeEmission")
    emission.inputs["Color"].default_value = (*color, 1)
    emission.inputs["Strength"].default_value = strength
    material.node_tree.links.new(emission.outputs[0], output.inputs["Surface"])
    return material


def flame_material():
    material = bpy.data.materials.new("Turbulent translucent flame")
    material.use_nodes = True
    nodes = material.node_tree.nodes
    nodes.clear()
    links = material.node_tree.links

    def math_node(operation, a, b=None):
        node = nodes.new("ShaderNodeMath")
        node.operation = operation
        for index, value in enumerate((a, b)):
            if value is None:
                continue
            if isinstance(value, (int, float)):
                node.inputs[index].default_value = value
            else:
                links.new(value, node.inputs[index])
        return node.outputs[0]

    uv = nodes.new("ShaderNodeTexCoord")
    separate = nodes.new("ShaderNodeSeparateXYZ")
    links.new(uv.outputs["UV"], separate.inputs[0])
    mapping = nodes.new("ShaderNodeVectorMath")
    mapping.operation = "MULTIPLY_ADD"
    links.new(uv.outputs["UV"], mapping.inputs[0])
    mapping.inputs[1].default_value = (3.5, 5.5, 1)
    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 1
    noise.inputs["Detail"].default_value = 3
    noise.inputs["Roughness"].default_value = 0.7
    links.new(mapping.outputs[0], noise.inputs["Vector"])
    erosion = nodes.new("ShaderNodeValToRGB")
    erosion.color_ramp.elements[0].position = 0.16
    erosion.color_ramp.elements[1].position = 0.62
    links.new(noise.outputs["Fac"], erosion.inputs[0])

    # Soft edges and a taper dissolve the mesh silhouette into turbulent wisps.
    edge = math_node("SUBTRACT", 1, math_node(
        "ABSOLUTE", math_node("SUBTRACT",
                              math_node("MULTIPLY", separate.outputs["X"], 2), 1)))
    alpha = math_node("MULTIPLY", math_node("POWER", edge, 0.65),
                      math_node("POWER", math_node(
                          "SUBTRACT", 1, separate.outputs["Y"]), 0.4))
    alpha = math_node("MULTIPLY", alpha, erosion.outputs[0])

    color = nodes.new("ShaderNodeValToRGB")
    ramp = color.color_ramp
    ramp.elements[0].color = (1, 0.82, 0.24, 1)
    ramp.elements[1].color = (0.65, 0.018, 0.001, 1)
    ramp.elements.new(0.25).color = (1, 0.40, 0.025, 1)
    ramp.elements.new(0.65).color = (1, 0.09, 0.002, 1)
    links.new(separate.outputs["Y"], color.inputs[0])
    emission = nodes.new("ShaderNodeEmission")
    links.new(color.outputs[0], emission.inputs["Color"])
    emission.inputs["Strength"].default_value = 1.8
    transparent = nodes.new("ShaderNodeBsdfTransparent")
    mix = nodes.new("ShaderNodeMixShader")
    links.new(alpha, mix.inputs[0])
    links.new(transparent.outputs[0], mix.inputs[1])
    links.new(emission.outputs[0], mix.inputs[2])
    output = nodes.new("ShaderNodeOutputMaterial")
    links.new(mix.outputs[0], output.inputs["Surface"])
    return material, mapping.inputs[2]


def ribbon(name, material):
    mesh = bpy.data.meshes.new(name)
    vertices = [(0, 0, 0)] * ((ROWS + 1) * 2)
    faces = [(i * 2, i * 2 + 1, i * 2 + 3, i * 2 + 2) for i in range(ROWS)]
    mesh.from_pydata(vertices, [], faces)
    uv = mesh.uv_layers.new()
    for polygon in mesh.polygons:
        for index in polygon.loop_indices:
            vertex = mesh.loops[index].vertex_index
            uv.data[index].uv = (vertex % 2, (vertex // 2) / ROWS)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    return obj


def setup_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 24
    scene.cycles.use_denoising = False
    scene.cycles.transparent_max_bounces = 24
    scene.render.threads_mode = "FIXED"
    scene.render.threads = 4
    scene.render.resolution_x = WIDTH
    scene.render.resolution_y = HEIGHT
    scene.render.resolution_percentage = 100
    scene.render.fps = FPS
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.color_depth = "8"
    scene.render.image_settings.compression = 80
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.exposure = -0.8
    scene.world.color = (0, 0, 0)

    camera_data = bpy.data.cameras.new("Orthographic artwork camera")
    camera = bpy.data.objects.new("Camera", camera_data)
    bpy.context.collection.objects.link(camera)
    camera.location = (0, 0, 500)
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = WIDTH
    scene.camera = camera

    # Blender 5's compositor uses an explicit node group.
    tree = bpy.data.node_groups.new("Transparent fire glow", "CompositorNodeTree")
    tree.interface.new_socket(name="Image", in_out="OUTPUT",
                              socket_type="NodeSocketColor")
    scene.compositing_node_group = tree
    source = tree.nodes.new("CompositorNodeRLayers")
    glare = tree.nodes.new("CompositorNodeGlare")
    glare.inputs["Type"].default_value = "Fog Glow"
    glare.inputs["Quality"].default_value = "High"
    glare.inputs["Threshold"].default_value = 0.7
    glare.inputs["Size"].default_value = 0.2
    glare.inputs["Strength"].default_value = 0.65
    tree.links.new(source.outputs["Image"], glare.inputs["Image"])
    # Glow needs alpha of its own to survive composition over a native dialog.
    luminance = tree.nodes.new("CompositorNodeRGBToBW")
    tree.links.new(glare.outputs["Image"], luminance.inputs[0])
    separate = tree.nodes.new("CompositorNodeSeparateColor")
    tree.links.new(source.outputs["Image"], separate.inputs[0])
    alpha = tree.nodes.new("ShaderNodeMath")
    alpha.operation = "MAXIMUM"
    alpha.use_clamp = True
    tree.links.new(separate.outputs["Alpha"], alpha.inputs[0])
    tree.links.new(luminance.outputs[0], alpha.inputs[1])
    combine = tree.nodes.new("CompositorNodeSetAlpha")
    # Apply Mask would attenuate the existing film alpha a second time.
    combine.inputs["Type"].default_value = "Replace Alpha"
    tree.links.new(glare.outputs["Image"], combine.inputs["Image"])
    tree.links.new(alpha.outputs[0], combine.inputs["Alpha"])
    output = tree.nodes.new("NodeGroupOutput")
    tree.links.new(combine.outputs[0], output.inputs["Image"])
    return scene


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--frames", help=f"Frame indices, 0..{INTRO + LOOP - 1}")
    parser.add_argument("--scene", type=Path, help="Optional editable .blend output")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    args.output.mkdir(parents=True, exist_ok=True)
    frames = (range(INTRO + LOOP) if not args.frames else
              [int(value) for value in args.frames.split(",")])
    if any(frame < 0 or frame >= INTRO + LOOP for frame in frames):
        parser.error(f"Frame indices must be between 0 and {INTRO + LOOP - 1}")
    scene = setup_scene()
    material, noise_offset = flame_material()
    flames = []
    for index in range(92):
        flames.append((ribbon(f"Wisp {index:02d}", material), index / 92,
                       RNG.uniform(0, math.tau),
                       RNG.uniform(FLAME_HEIGHT_MIN, FLAME_HEIGHT_MAX),
                       RNG.uniform(6.0, 11.0)))

    curve = bpy.data.curves.new("Ignited perimeter", "CURVE")
    curve.dimensions = "3D"
    curve.bevel_depth = 1.3
    curve.bevel_resolution = 2
    spline = curve.splines.new("POLY")
    spline.points.add(255)
    spline.use_cyclic_u = True
    ring = bpy.data.objects.new("White-hot perimeter", curve)
    bpy.context.collection.objects.link(ring)
    ring.data.materials.append(emission_material("Hot gold", (1, 0.20, 0.01), 3))

    spark_material = emission_material("Ignition sparks", (1, 0.75, 0.3), 7)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=1)
    head = bpy.context.object
    head.name = "Visible white-hot ignition core"
    head.data.materials.append(emission_material("White-hot core", (1, 0.9, 0.7), 12))
    sparks = []
    for index in range(14):
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=1)
        obj = bpy.context.object
        obj.name = f"Spark {index:02d}"
        obj.data.materials.append(spark_material)
        sparks.append((obj, RNG.uniform(0, math.tau), RNG.uniform(5, 24)))

    for frame in frames:
        time = frame / FPS
        phase = math.tau * (time - INTRO / FPS) / (LOOP / FPS)
        progress = smooth((time - SPARK_HOLD) / SWEEP_TIME)
        noise_offset.default_value = (0.65 * math.sin(phase),
                                      0.85 * math.cos(phase), 0)
        for obj, position, seed, height, width in flames:
            age = (progress - position) * PERIMETER
            lit = smooth(age / 20) if progress < 1 else 1
            obj.hide_render = lit == 0
            x, y, nx, ny = perimeter_position(position)
            tangent = Vector((ny, -nx))
            normal = Vector((nx, ny))
            length = height * lit * (0.82 + 0.18 * math.sin(phase + seed))
            for row in range(ROWS + 1):
                v = row / ROWS
                bend = (math.sin(phase + seed + v * 4) * 18 * v ** 1.5)
                center = Vector((x, y)) + normal * (length * v)
                center += tangent * bend
                billow = 1 + 0.24 * math.sin(phase * 2 + seed + v * 9)
                half = width * (1 - v) ** 0.8 * lit * billow
                for side in range(2):
                    point = center + tangent * half * (side * 2 - 1)
                    obj.data.vertices[row * 2 + side].co = (*point, 1)
            obj.data.update()
        for index, point in enumerate(spline.points):
            fraction = index / 256
            x, y, _, _ = perimeter_position(fraction)
            point.co = (x, y, 1.3, 1)
            lit = smooth((progress - fraction) * PERIMETER / 8)
            point.radius = lit * (0.85 + 0.15 * math.sin(phase * 2 + index))
        x, y, nx, ny = perimeter_position(progress)
        fade = 1 - smooth((time - SPARK_HOLD - SWEEP_TIME) / 0.3)
        pulse = 1 + 0.28 * math.sin(time * 20) * math.exp(-time * 2)
        # Keep the core outside the native face, rather than hiding half of it.
        head.location = (x + nx * 8, y + ny * 8, 3)
        head.scale = (8 * pulse * fade, 8 * pulse * fade, 2 * fade)
        head.hide_render = fade < 0.01
        for index, (obj, angle, speed) in enumerate(sparks):
            burst = math.exp(-((time - 0.18) / 0.26) ** 2)
            size = fade * (burst + 0.6) * (1.2 + 0.7 * math.sin(index))
            distance = ((time * 0.9 + index / 14) % 1) * speed * 2.2
            obj.location = (x + math.cos(angle) * distance,
                            y + math.sin(angle) * distance + 8, 2)
            obj.scale = (size, size * 2.8, size)
            obj.hide_render = size < 0.02
        scene.render.filepath = str(args.output / f"{frame:03d}.png")
        bpy.ops.render.render(write_still=True)
        print(f"FIRE_FRAME {frame:03d}", flush=True)
    if args.scene:
        bpy.ops.wm.save_as_mainfile(filepath=str(args.scene))


if __name__ == "__main__":
    main()
