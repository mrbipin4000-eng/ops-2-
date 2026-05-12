import os

import bpy

from . import update
from ... import __package__ as base_package
from ... import module

name = module.name()
icons = {}


class path:

    def __new__(self):
        return os.path.abspath(os.path.join(__file__, '..', '..', '..'))

    def icons():
        return os.path.join(os.path.realpath(path()), 'icons')

    def default_kpack():
        return os.path.join(os.path.realpath(path()), 'Master')

    def thumbnail(insert_type):
        if insert_type == 'INSERT':
            return path.insert_thumbnail()
        elif insert_type == 'MATERIAL':
            return path.material_thumbnail()
        elif insert_type == 'GEO_NODES':
            return path.geo_nodes_thumbnail()
        elif insert_type == 'SHADER_NODES':
            return path.shader_nodes_thumbnail()
        elif insert_type == 'DECAL':
            return path.decal_thumbnail()
        return os.path.join(path.default_kpack(), 'render.blend')

    def insert_thumbnail():
        return os.path.join(path.default_kpack(), 'render.blend')
    
    def material_thumbnail():
        return os.path.join(path.default_kpack(), 'material.blend')

    def geo_nodes_thumbnail():
        return os.path.join(path.default_kpack(), 'geometry_nodes.blend')

    def shader_nodes_thumbnail():
        return os.path.join(path.default_kpack(), 'shader_nodes.blend')

    def decal_thumbnail():
        return os.path.join(path.default_kpack(), 'decaltemplates/BATCH_Decal.blend')

    def get_thumbnail_paths():
        return {
            'INSERT': path.insert_thumbnail(),
            'MATERIAL': path.material_thumbnail(),
            'GEO_NODES': path.geo_nodes_thumbnail(),
            'SHADER_NODES': path.shader_nodes_thumbnail(),
            'DECAL': path.decal_thumbnail()
        }

    def material():
        return os.path.join(path.default_kpack(), 'material.blend')

    def default_thumbnail():
        return os.path.join(path.default_kpack(), 'thumb.png')

    def hardpoint_location():
        return os.path.join(path.default_kpack(), 'hardpoint.blend')

    def decal_templates_folder():
        return os.path.join(os.path.realpath(path()), 'decaltemplates')

def preference():
    # for bpy_package in bpy.context.preferences.addons:
    #     print(bpy_package)
    try:
        preference = bpy.context.preferences.addons[base_package].preferences
    except KeyError:
        return None

    if not len(preference.sets):
        all_set = preference.sets.add()
        all_set.name = 'ALL'

    if not len(preference.folders):
        folder = preference.folders.add()
        folder.name = 'Default KPACKs'
        folder.location = path.default_kpack()
        set_id = folder.set_ids.add()
        set_id.name = 'ALL'


    return preference


def option():
    wm = bpy.context.window_manager
    if not hasattr(wm, 'kitops'):
        return False

    option = bpy.context.window_manager.kitops

    if not option.name:
        option.name = 'options'
        update.options()

    return option


def hops():
    wm = bpy.context.window_manager

    if hasattr(wm, 'Hard_Ops_folder_name'):
        return bpy.context.preferences.addons[wm.Hard_Ops_folder_name].preferences

    return False


def bc():
    wm = bpy.context.window_manager

    if hasattr(wm, 'bc'):
        return bpy.context.preferences.addons[wm.bc.addon].preferences

    return False
