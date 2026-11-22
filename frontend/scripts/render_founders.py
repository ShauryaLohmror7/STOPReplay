"""Render the founder portraits and export their 3D meshes for Blender.

Run with Python and Pillow from any directory. Import art/founders.glb in
Blender to edit the three figures.
"""
import json
import math
import random
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FACES = (
    ((-1, 0, 0), ((0, 0, 0), (0, 0, 1), (0, 1, 1), (0, 1, 0))),
    ((1, 0, 0), ((1, 0, 0), (1, 1, 0), (1, 1, 1), (1, 0, 1))),
    ((0, -1, 0), ((0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1))),
    ((0, 1, 0), ((0, 1, 0), (0, 1, 1), (1, 1, 1), (1, 1, 0))),
    ((0, 0, -1), ((0, 0, 0), (0, 1, 0), (1, 1, 0), (1, 0, 0))),
    ((0, 0, 1), ((0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1))),
)
PROFILES = (
    dict(id='founder-jm', hair=(76, 47, 33), shine=(125, 81, 47), skin=(222, 165, 123),
         shirt=(236, 227, 212), pants=(67, 91, 104), eyes=(87, 113, 117), jaw=(96, 62, 43),
         fringe=[34, 34, 33, 34, 35, 35, 36, 36, 36, 35, 35, 34, 33, 32, 32, 33], yaw=22),
    dict(id='founder-tm', hair=(106, 72, 43), shine=(153, 113, 69), skin=(220, 162, 125),
         shirt=(40, 51, 77), pants=(74, 91, 111), eyes=(90, 83, 68), jaw=(164, 111, 82),
         fringe=[33, 33, 33, 34, 34, 34, 35, 35, 35, 34, 34, 34, 33, 33, 33, 33], yaw=-18),
    dict(id='founder-rs', hair=(171, 129, 76), shine=(223, 183, 118), skin=(236, 174, 135),
         shirt=(97, 88, 137), pants=(48, 78, 100), eyes=(86, 128, 164), jaw=None,
         fringe=[33, 33, 34, 33, 34, 33, 33, 34, 33, 33, 34, 34, 33, 34, 33, 33], yaw=17),
)


def shade(color, amount):
    return tuple(max(0, min(255, round(value * amount))) for value in color)


def avatar(profile):
    blocks = {}
    randomizer = random.Random(22)
    skin, hair = profile['skin'], profile['hair']
    shirt, pants = profile['shirt'], profile['pants']

    def put(x, y, z, color, variance=.022):
        blocks[x, y, z] = shade(color, 1 + randomizer.uniform(-variance, variance))

    def box(x0, x1, y0, y1, z0, z1, color):
        for x in range(x0, x1):
            for y in range(y0, y1):
                for z in range(z0, z1):
                    put(x, y, z, color)

    for a, b in ((-5, -1), (1, 5)):
        box(a, b, -5, 4, 0, 1, (133, 141, 124))
        box(a, b, -5, 4, 1, 3, (48, 52, 51))
        box(a, b, -3, 3, 3, 11, pants)
        box(a, b, -3, -2, 4, 5, shade(pants, 1.16))

    box(-6, 6, -4, 4, 9, 20, shirt)
    box(-5, 5, -3, 3, 20, 21, shirt)
    box(-3, 3, -2, 2, 20, 24, skin)
    box(-9, -6, -3, 3, 16, 19, shirt)
    box(6, 9, -3, 3, 16, 19, shirt)
    for a, b in ((-9, -6), (6, 9)):
        short = profile['id'] == 'founder-jm'
        box(a, b, -3, 2, 10, 16, skin if short else shirt)
        box(a, b, -3, 2, 9, 12 if short else 11, skin)
        box(a, b, -3, 2, 15 if short else 11, 16 if short else 12, shade(shirt, .82))
        box(a, b, -3, 2, 9, 10, shade(skin, .95))

    for x in range(-5, 5):
        for z in range(11, 19):
            if (x - z) % 5 == 0 or profile['id'] == 'founder-rs' and x % 3 == 0:
                put(x, -4, z, shade(shirt, 1.075))
    if profile['id'] == 'founder-jm':
        for x in range(-3, 3):
            put(x, -4, 19, shade(shirt, .87))
        box(-2, 2, -4, -3, 20, 21, shade(shirt, .92))
    else:
        undershirt = (178, 200, 213) if profile['id'] == 'founder-tm' else (139, 129, 175)
        box(-1, 1, -4, -3, 15, 21, undershirt)
        box(-2, 2, -4, -3, 18, 20, undershirt)
        put(-3, -4, 20, shade(shirt, 1.3))
        put(2, -4, 20, shade(shirt, 1.3))
        put(0, -5, 15, (172, 171, 154))
        put(0, -5, 16, (124, 139, 146))

    chin = {-8: 25, -7: 24, -6: 23, 5: 23, 6: 24, 7: 25}
    for x in range(-8, 8):
        for y in range(-6, 7):
            if abs(x + .5) > 6.5 and y in (-6, 6):
                continue
            for z in range(chin.get(x, 23), 37 - (abs(x + .5) > 6)):
                paint = skin
                hairline = profile['fringe'][x + 8]
                if z >= hairline + (y <= -4) or (y >= 3 and z > 27) or (abs(x + .5) >= 6.5 and y >= -2 and z >= 29):
                    paint = profile['shine'] if (x + z + (y // 3) * 2) % 7 < 2 else hair
                put(x, y, z, paint, .05 if paint != skin else .012)
    for x in (-9, 8):
        box(x, x + 1, -2, 0, 27, 31, skin)
        put(x, -3, 28, shade(skin, .88))
        put(x, -3, 29, shade(skin, 1.05))

    # The swept outline and the blond fringe read at thumbnail scale.
    for x in range(-7, 7):
        if profile['id'] == 'founder-jm':
            cap = 39 - min(3, abs(x + 2) // 3)
        else:
            cap = 38 - (abs(x) > 5)
        for y in range(-4, 5):
            for z in range(36, cap - (abs(y) > 3)):
                put(x, y, z, profile['shine'] if (x + y + z * 2) % 9 < 3 else hair, .05)
        for z in range(profile['fringe'][x + 8], 36):
            if z > 34 or (x + z) % 4 != 0:
                put(x, -6, z, profile['shine'] if (x + z * 2) % 7 < 2 else hair, .05)

    jaw = profile['jaw']
    for x in range(-7, 7):
        if jaw:
            cheek = abs(x + .5)
            for z in range(chin.get(x, 23), 29):
                if cheek >= 5.5 or z <= (24 if profile['id'] == 'founder-jm' else 23):
                    put(x, -6, z, jaw, .12)
        if abs(x + .5) >= 4.5 and abs(x + .5) <= 6.5:
            put(x, -6, 27, shade((229, 145, 132), .98))
    for eye in (-4, 3):
        for x in (eye - 1, eye, eye + 1):
            put(x, -6, 32, shade(hair, .77))
            for z in range(29, 32):
                put(x, -6, z, (244, 226, 202))
        for z in range(29, 32):
            put(eye, -6, z, (28, 28, 25) if z != 29 else profile['eyes'])
        put(eye + 1, -6, 30, shade(profile['eyes'], .88))
        put(eye, -7, 31, (255, 249, 225))
    put(-1, -7, 28, shade(skin, 1.09))
    put(0, -7, 28, shade(skin, .94))
    put(-1, -7, 27, shade(skin, .91))
    for x in range(-3, 3):
        if profile['id'] == 'founder-jm':
            put(x, -6, 27, shade(jaw, 1.04))
        put(x, -6, 26, (113, 58, 51))
        if -2 <= x <= 1 and profile['id'] != 'founder-tm':
            put(x, -7, 26, (250, 239, 214))
    for x in range(-2, 2):
        put(x, -6, 25, shade(skin, .9))

    return blocks


def exposed_surfaces(blocks):
    for (x, y, z), color in blocks.items():
        for (nx, ny, nz), corners in FACES:
            if (x + nx, y + ny, z + nz) not in blocks:
                yield (nx, ny, nz), [(x + i, y + j, z + k) for i, j, k in corners], color


def render():
    from PIL import Image, ImageDraw, ImageFilter

    size = (852, 1074)
    out = ROOT / 'public' / 'founders'
    out.mkdir(parents=True, exist_ok=True)
    for profile in PROFILES:
        yaw, pitch = math.radians(profile['yaw']), math.radians(15)
        sy, cy, sp, cp = math.sin(yaw), math.cos(yaw), math.sin(pitch), math.cos(pitch)
        scale = 22

        def project(point):
            x, y, z = point
            toward = x * sy - y * cy
            return 426 + scale * (x * cy + y * sy), 987 + scale * (toward * sp - z * cp)

        image = Image.new('RGBA', size)
        shadow = Image.new('RGBA', size)
        ImageDraw.Draw(shadow).ellipse((158, 941, 694, 1023), fill=(0, 7, 2, 176))
        image.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(24)))
        artist = ImageDraw.Draw(image)
        quads = []
        for (nx, ny, nz), corners, color in exposed_surfaces(avatar(profile)):
            if nx * sy * cp - ny * cy * cp + nz * sp <= 0:
                continue
            depth = sum((x * sy - y * cy) * cp + z * sp for x, y, z in corners) / 4
            light = 1.17 if nz else .88 if nx else 1.02
            quads.append((depth, [project(point) for point in corners], shade(color, light)))
        for _, points, color in sorted(quads, key=lambda item: item[0]):
            artist.polygon(points, fill=(*color, 255))

        image.resize((426, 537), Image.Resampling.LANCZOS).save(
            out / (profile['id'] + '.webp'), method=6, lossless=True
        )


def save_gltf():
    # glTF packs the model's attributes and triangle indices into one buffer.
    data = bytearray()
    views, accessors, meshes, nodes = [], [], [], []

    def store(values, form, component, type_name, count, **bounds):
        offset = len(data)
        array = struct.pack(f'<{len(values)}{form}', *values)
        data.extend(array)
        views.append(dict(buffer=0, byteOffset=offset, byteLength=len(array)))
        accessors.append(dict(bufferView=len(views) - 1, componentType=component,
                              count=count, type=type_name, **bounds))
        return len(accessors) - 1

    for row, profile in enumerate(PROFILES):
        positions, normals, colors, indices = [], [], [], []
        for normal, corners, color in exposed_surfaces(avatar(profile)):
            first = len(positions)
            # Convert from the voxel editor's Z-up to glTF's Y-up.
            positions.extend((x * .1, z * .1, -y * .1) for x, y, z in corners)
            nx, ny, nz = normal
            normals.extend((nx, nz, -ny) * 4)
            linear_color = tuple((value / 255) ** 2.2 for value in color)
            colors.extend(linear_color * 4)
            indices.extend(first + i for i in (0, 1, 2, 0, 2, 3))
        axes = list(zip(*positions))
        attributes = {
            'POSITION': store([value for point in positions for value in point],
                              'f', 5126, 'VEC3', len(positions),
                              min=[min(axis) for axis in axes], max=[max(axis) for axis in axes]),
            'NORMAL': store(normals, 'f', 5126, 'VEC3', len(positions)),
            'COLOR_0': store(colors, 'f', 5126, 'VEC3', len(positions)),
        }
        triangles = store(indices, 'I', 5125, 'SCALAR', len(indices))
        meshes.append(dict(name=profile['id'], primitives=[
            dict(attributes=attributes, indices=triangles, material=0),
        ]))
        nodes.append(dict(name=profile['id'], mesh=row, translation=[(row - 1) * 2.6, 0, 0]))

    document = dict(
        asset=dict(version='2.0', generator='STOPReplay voxel portraits'),
        scene=0, scenes=[dict(nodes=list(range(len(nodes))))],
        nodes=nodes, meshes=meshes, accessors=accessors, bufferViews=views,
        buffers=[dict(byteLength=len(data))],
        materials=[dict(pbrMetallicRoughness=dict(metallicFactor=0, roughnessFactor=.87))],
    )
    metadata = json.dumps(document, separators=(',', ':')).encode()
    metadata += b' ' * (-len(metadata) % 4)
    total = 12 + 8 + len(metadata) + 8 + len(data)
    out = ROOT / 'art'
    out.mkdir(parents=True, exist_ok=True)
    with (out / 'founders.glb').open('wb') as file:
        file.write(struct.pack('<4sII', b'glTF', 2, total))
        file.write(struct.pack('<I4s', len(metadata), b'JSON'))
        file.write(metadata)
        file.write(struct.pack('<I4s', len(data), b'BIN\0'))
        file.write(data)


if __name__ == '__main__':
    render()
    save_gltf()
