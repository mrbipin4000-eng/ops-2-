import bpy
from . import persistence
import os
import re


def get_edit_thumbnail_path(context, insert_type):
    """
    Returns the path to the thumbnail PNG file based on the current .blend file
    and the specified insert_type.
    """
    base_path = context.scene.kitops.last_edit if context.scene.kitops.last_edit else bpy.data.filepath
    base_png_path = re.sub(r'\.blend\d*$', '.png', base_path)

    type_map = {
        'INSERT': '-0.png',
        'MATERIAL': '-1.png',
        'GEO_NODES': '-2.png',
        'SHADER_NODES': '-3.png',
        'DECAL': '-4.png',
    }

    if insert_type in type_map:
        filename_no_ext = os.path.splitext(base_png_path)[0]
        candidate = f"{filename_no_ext}{type_map[insert_type]}"
        return candidate

    return base_png_path  # fallback


def get_thumbnail_path(context):
    """
    Returns a tuple: (path to thumbnail PNG file, insert_type)
    based on the last_edit path or current .blend file.
    Tries the base PNG first, then numbered variants (-0 to -5).
    """
    type_map = {
        '-0.png': 'INSERT',
        '-1.png': 'MATERIAL',
        '-2.png': 'GEO_NODES',
        '-3.png': 'SHADER_NODES',
        '-4.png': 'DECAL',
    }

    base_path = context.scene.kitops.last_edit if context.scene.kitops.last_edit else bpy.data.filepath
    base_png_path = re.sub(r'\.blend\d*$', '.png', base_path)

    if os.path.exists(base_png_path):
        return base_png_path, "NONE"  # No insert_type for base

    filename_no_ext = os.path.splitext(base_png_path)[0]

    for suffix, insert_type in type_map.items():
        candidate = f"{filename_no_ext}{suffix}"
        if os.path.exists(candidate):
            return candidate, insert_type

    return base_png_path, "NONE"  # fallback