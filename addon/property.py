import sys
import traceback

import bpy

from bpy.types import PropertyGroup
from bpy.props import *
from bpy.utils import register_class, unregister_class

import os
from pathlib import Path


from . utility import addon, insert, update, previews, enums, smart, persistence

authoring_enabled = True
try: from . utility import matrixmath
except ImportError: authoring_enabled = False

def sort_items(e):
  return e[0].lower()

def prepare_items(items: list, sort: bool=True) -> list:
    '''For each item, replace icon_path with icon_id and cast list to tuple.'''

    for index, item in enumerate(items):
        if isinstance(item, list):
            try:
                item[3] = previews.get(item[3]).icon_id
            except FileNotFoundError:
                pass
            items[index] = tuple(item)


    if sort:
        items.sort(key = sort_items)

    return items


def thumbnails(prop, context):
    option = addon.option()
    return option.get_kitops_insert_enum(prop.folder)

kpack_sets_items = []
def kpack_sets(pt, context):
    global kpack_sets_items
    kpack_sets_items = []
    preference = addon.preference()
    
    for kpack_set in preference.sets:
        kpack_sets_items.append((kpack_set.name, kpack_set.name, ''))

    kpack_sets_items.sort(key=lambda t : tuple(t[0].lower()))   # case insensitive sort Added by Lyne Frappier

    return kpack_sets_items

def kpack_enum(pt, context):
    option = addon.option()
    return option.get_kitops_category_enum_filtered()


_insert_types = [('INSERT', 'Insert', 'This folder contains INSERTS'),
               ('MATERIAL', 'Material', 'This folder contains Materials'),
               ('GEO_NODES', 'Geo Node', 'This folder contains Geo Node INSERTS'),
               ('SHADER_NODES', 'Shader Node', 'This folder contains Shader Node INSERTS'),
               ('DECAL', 'Decal', 'This folder contains Decals INSERTS'),]
class file(PropertyGroup):
    location: StringProperty()
    icon_path : StringProperty()
    insert_type: EnumProperty(
        name = 'Folder type',
        description = 'Type of folder',
        items=_insert_types,
        default='INSERT')
    is_legacy: BoolProperty(
        name = 'Legacy',
        description = 'This file is a legacy type before insert types were introduced',
        default=False)

class folder(PropertyGroup):
    thumbnail: EnumProperty(update=update.thumbnails, items=thumbnails, name="Active INSERT thumbnail")
    active_index: IntProperty(name="Active index pointing to currently selected INSERT.")
    blends: CollectionProperty(type=file, name="List of blend files containing the INSERT.")
    folder: StringProperty(name="folder name")



class kpack(PropertyGroup):
    active_index: IntProperty(name="Active index pointing to a folder")
    categories: CollectionProperty(type=folder, name="sub folders containing INSERTS for a kpack")

class mat(PropertyGroup):
    id: StringProperty()
    material: BoolProperty()


class data(PropertyGroup):
    id: StringProperty()
    insert: BoolProperty()

class boolean_ref(PropertyGroup):
    pass


class object(PropertyGroup):
    id: StringProperty()
    collection: StringProperty()
    label: StringProperty()
    insert: BoolProperty()
    insert_name :  StringProperty()
    inserted: BoolProperty()
    main_object: PointerProperty(type=bpy.types.Object)
    reserved_target: PointerProperty(type=bpy.types.Object)
    applied: BoolProperty()
    duplicate: BoolProperty()
    mirror: BoolProperty()
    mirror_target: PointerProperty(type=bpy.types.Object)
    animated: BoolProperty()
    hide: BoolProperty()
    author: StringProperty()
    temp: BoolProperty()
    material_base: BoolProperty()
    bool_duplicate: BoolProperty()
    is_hardpoint : BoolProperty()
    hardpoint_object: PointerProperty(type=bpy.types.Object)

    hardpoint_tags : StringProperty(
        name="Hardpoint Tags",
        description="A Comma separated list of tags for the hardpoint"
        )

    mirror_x: BoolProperty(
        name = 'X',
        description = 'Mirror INSERT on X axis of the INSERT target',
        update = smart.update.mirror_x,
        default = False)

    mirror_y: BoolProperty(
        name = 'Y',
        description = 'Mirror INSERT on Y axis of the INSERT target',
        update = smart.update.mirror_y,
        default = False)

    mirror_z: BoolProperty(
        name = 'Z',
        description = 'Mirror INSERT on Z axis of the INSERT target',
        update = smart.update.mirror_z,
        default = False)

    array_count: IntProperty(
        name = 'Array Count',
        description = 'Number of array objects',
        update = smart.update.array_insert,
        min=1,
        default=1)

    array_offset: FloatVectorProperty(
        name = 'Array Offset',
        description = 'Array Constant Offset of INSERT on the INSERT target',
        update = smart.update.array_insert,
        default=[0.5, 0, 0])


    insert_target: PointerProperty(
        name = 'Insert target',
        description = 'Target obj for the INSERT',
        update = smart.update.insert_target,
        type = bpy.types.Object)

    main: BoolProperty(
        name = 'Main obj',
        description = 'This obj will become the main obj of all the other objs for this INSERT',
        update = smart.update.main,
        default = False)

    type: EnumProperty(
        name = 'Object type',
        description = 'Change KIT OPS obj type',
        items = [
            ('SOLID', 'Solid', 'This obj does NOT cut and is renderable'),
            ('WIRE', 'Wire', 'This obj does NOT cut and is NOT renderable'),
            ('CUTTER', 'Cutter', 'This obj does cut and is NOT renderable')],
        update = persistence.update.type,
        default = 'SOLID')

    boolean_type: EnumProperty(
        name = 'Boolean type',
        description = 'Boolean type to use for this obj',
        items = [
            ('DIFFERENCE', 'Difference', 'Combine two meshes in a subtractive way'),
            ('UNION', 'Union', 'Combine two meshes in an additive way'),
            ('INTERSECT', 'Intersect', 'Keep the part of the mesh that intersects with modifier object'),
            ('INSERT', 'Insert', 'The cutter is for the insert not the target')],
        default = 'DIFFERENCE')

    selection_ignore: BoolProperty(
        name = 'Selection ignore',
        description = 'Do not select this obj when using auto select',
        default = False)

    ground_box: BoolProperty(
        name = 'Ground box',
        description = 'Use to tell kitops that this is a ground box obj for thumbnail rendering',
        default = False)

    rotation_amount : FloatProperty(
        name = 'Rotation Amount',
        description = 'Amount of rotation that has been applied to the object.',
        default=0)

    is_factory_scene: BoolProperty(
        name = 'Is a factory Scene',
        description = 'Used to tell kitops that this is object is from a factory scene',
        default = False)


class world(PropertyGroup):

    is_factory_scene: BoolProperty(
        name = 'Is a factory Scene',
        description = 'Used to tell kitops that this is a world factory scene',
        default = False)

class image(PropertyGroup):

    is_factory_scene: BoolProperty(
        name = 'Is a factory Scene',
        description = 'Used to tell kitops that this is an image used in the factory scene',
        default = False)

_asset_library_options = []
_asset_library_catalogs = []
_asset_library_txt_file =  "blender_assets.cats.txt"
class scene(PropertyGroup):
    factory: BoolProperty()
    thumbnail: BoolProperty()
    original_scene: StringProperty()
    last_edit: StringProperty()
    original_file: StringProperty()

    auto_parent: BoolProperty(
        name = 'Auto parent',
        description = 'Automatically parent all objs to the main obj when saving\n  Note: Incorrect parenting can lead to an unusable INSERT',
        default = False)

    animated: BoolProperty(
        name = 'Animated',
        description = 'Begin the timeline when you add this insert',
        default = False)

    render_mode : EnumProperty(
        name = 'Render mode',
        description = 'Render mode to use for this scene',
        items=[('CYCLES', 'Cycles', 'Cycles render mode'),
               ('EEVEE', 'EEVEE', 'EEVEE render mode'),
               ('OPENGL', 'Viewport', 'A snapshot of the active viewport')],
        default='CYCLES'
    )

    preview_hardpoints: BoolProperty(default=False)

    previous_lock_camera: BoolProperty(
        name = 'Lock camera',
        description = 'Whether previous camera was locked or not',
        default = False)


# Define the property group
class searchresult(bpy.types.PropertyGroup):
    insert_name: bpy.props.StringProperty(name="Insert Name", description="Name of the insert")
    blend_file: bpy.props.StringProperty(name="Blend File", description="Name of the .blend file")
    master_folder: bpy.props.StringProperty(name="Master Folder", description="Name of the master folder")
    pack: bpy.props.StringProperty(name="Pack", description="Name of the pack (sub-folder)")



class options(PropertyGroup):
    addon: StringProperty(default=addon.name)
    kpack: PointerProperty(type=kpack)
    pro: BoolProperty(default=authoring_enabled)
    authoring_mode: BoolProperty(default=False)

    kpack_prefs_set : EnumProperty(
        items=kpack_sets, 
        name="Set", 
        description="Set of Master Folders")

    kpack_set: EnumProperty(
        name = 'Sets',
        description = 'Masterfolder Sets',
        items = kpack_sets,
        update = update.kpack_set)

    kpacks: EnumProperty(
        name = 'KPACKS',
        description = 'Available KPACKS',
        items = kpack_enum,
        update = update.kpacks)

    insert_name: StringProperty(
        name = 'INSERT Name',
        description = 'INSERT Name',
        default = 'Insert Name')

    author: StringProperty(
        name = 'Author Name',
        description = 'Kit author',
        update = persistence.update.author,
        default = 'Your Name')

    show_modifiers: BoolProperty(
        name = 'Modifiers',
        description = 'Toggle KIT OPS boolean modifier visibility',
        update = update.show_modifiers,
        default = True)

    show_solid_objects: BoolProperty(
        name = 'Solid objs',
        description = 'Show the KIT OPS solid objs',
        update = update.show_solid_objects,
        default = True)

    show_cutter_objects: BoolProperty(
        name = 'Cutter objs',
        description = 'Show the KIT OPS cutter objs',
        update = update.show_cutter_objects,
        default = True)

    show_wire_objects: BoolProperty(
        name = 'Wire objs',
        description = 'Show the KIT OPS wire objs',
        update = update.show_wire_objects,
        default = True)

    scale_amount : FloatProperty(
        name = 'Scale Amount',
        description = 'Current Scale multiplier to apply to the INSERT',
        default=1)

    def get_kitops_category_enum(self):
        '''Get Enum list for KIT OPS Categories'''
        return prepare_items(enums.kitops_category_enums, sort=False)

    def get_kitops_category_enum_filtered(self):
        '''Get Enum list for KIT OPS Categories'''

        option = addon.option()
        preference = addon.preference()

        kpack_set = option.kpack_set

        folders = preference.folders

        visible_folders = [f for f in folders if kpack_set in f.set_ids]
    
        enums.kitops_category_enums_filtered = []
        for visible_folder in visible_folders:
            if visible_folder.name in enums.kitops_category_enum_map:
                enums.kitops_category_enums_filtered.extend([e for e in prepare_items(enums.kitops_category_enum_map[visible_folder.name])]  )

        return prepare_items(enums.kitops_category_enums_filtered, sort=False)
    

    masterfolder_search_input : StringProperty(
        name = "Search Input",
        description = "Enter search keywords",
        default=""
    )
    

    kpacks_search_results : CollectionProperty(type=searchresult)


    def get_kitops_insert_enum(self, category):
        '''Get Enum List for KIT OPS Inserts related to a category'''
        if category in enums.kitops_insert_enum_map:
            return prepare_items(enums.kitops_insert_enum_map[category])
        return []

    new_set_name : StringProperty(
        name = "New Set Name",
        description = "Name for new set.",
        default=""
    )

    filter_sets :EnumProperty(
        name = 'Boolean type',
        description = 'Boolean type to use for this obj',
        items = [
            ('ALL', 'All', ''),
            ('VISIBLE', 'Visible', ''),
            ('INVISIBLE', 'Invisible', '')],
        default='ALL')
    
    def get_asset_libraries(self, context):
        global _asset_library_options
        _asset_library_options = []
        prefs = bpy.context.preferences
        filepaths = prefs.filepaths
        _asset_library_options = [(library.name, library.name, "") for library in filepaths.asset_libraries]
        return _asset_library_options


    def get_asset_library_catalogs(self, context):
        global _asset_library_catalogs
        global _asset_library_txt_file
        _asset_library_catalogs = [("ALL", "All", ""), ("NONE", "Unassigned", "")]
        
        prefs = bpy.context.preferences
        filepaths = prefs.filepaths

        if self.asset_libraries_options in filepaths.asset_libraries:
            library = filepaths.asset_libraries[self.asset_libraries_options]

            folder = Path(library.path)

            if os.path.exists(folder / _asset_library_txt_file):
                with (folder / _asset_library_txt_file).open() as f:

                    for line in f.readlines():
                        if line.startswith(("#", "VERSION", "\n")):
                            continue
                        # Each line contains : 'uuid:catalog_tree:catalog_name' + eol ('\n')
                        name = line.split(":")[2].split("\n")[0]
                        uuid = line.split(":")[0]

                        _asset_library_catalogs.append((uuid, name, ""))

        return _asset_library_catalogs

    asset_libraries_options : bpy.props.EnumProperty(
        name="Asset Libraries",
        description="Select which asset libraries to use",
        items=get_asset_libraries,
    )

    asset_libraries_catalogs : bpy.props.EnumProperty(
        name="Catalog",
        description="Select which catalog to use",
        items=get_asset_library_catalogs,
    )

    # String property to store the destination directory
    asset_destination_dir : bpy.props.StringProperty(
        name="Destination Directory",
        description="Directory where assets will be saved",
        subtype='DIR_PATH',  # makes the property display as a file browser for directories
    )

    asset_processing_is_running : BoolProperty(default=False)

    currently_processing_asset : StringProperty(default='')

    asset_processing_progress : bpy.props.FloatProperty(
        name="Progress", 
        min=0.0, 
        max=1.0, 
        default=0.0
    )

    save_insert_type : bpy.props.EnumProperty(
        name = 'Insert type',
        description = 'Type of insert to save',
        items = _insert_types,
        default='INSERT'
    )

classes = [
    boolean_ref,
    file,
    folder,
    kpack,
    mat,
    data,
    object,
    scene,
    world,
    image,
    searchresult,
    options]


def register():
    for cls in classes:
        register_class(cls)

    bpy.types.WindowManager.kitops = PointerProperty(name='KIT OPS', type=options)
    bpy.types.Scene.kitops = PointerProperty(name='KIT OPS', type=scene)
    bpy.types.Object.kitops = PointerProperty(name='KIT OPS', type=object)
    bpy.types.GreasePencil.kitops = PointerProperty(name='KIT OPS', type=data)
    bpy.types.Light.kitops = PointerProperty(name='KIT OPS', type=data)
    bpy.types.LightProbe.kitops = PointerProperty(name='KIT OPS', type=data)
    bpy.types.Camera.kitops = PointerProperty(name='KIT OPS', type=data)
    bpy.types.Speaker.kitops = PointerProperty(name='KIT OPS', type=data)
    bpy.types.Lattice.kitops = PointerProperty(name='KIT OPS', type=data)
    bpy.types.Armature.kitops = PointerProperty(name='KIT OPS', type=data)
    bpy.types.Curve.kitops = PointerProperty(name='KIT OPS', type=data)
    bpy.types.MetaBall.kitops = PointerProperty(name='KIT OPS', type=data)
    bpy.types.Mesh.kitops = PointerProperty(name='KIT OPS', type=data)
    bpy.types.Material.kitops = PointerProperty(name='KIT OPS', type=mat)
    bpy.types.World.kitops = PointerProperty(name='KIT OPS', type=world)
    bpy.types.Image.kitops =PointerProperty(name='KIT OPS', type=image)

    update.icons()
    update.kpack(None, bpy.context)

    preference = addon.preference()
    



def unregister():
    for cls in classes:
        unregister_class(cls)

    del bpy.types.WindowManager.kitops
    del bpy.types.Scene.kitops
    del bpy.types.Object.kitops
    del bpy.types.GreasePencil.kitops
    del bpy.types.Light.kitops
    del bpy.types.Camera.kitops
    del bpy.types.Speaker.kitops
    del bpy.types.Lattice.kitops
    del bpy.types.Armature.kitops
    del bpy.types.Curve.kitops
    del bpy.types.MetaBall.kitops
    del bpy.types.Mesh.kitops
    del bpy.types.Material.kitops

    addon.icons.clear()
