import os

import bpy

from bpy.types import AddonPreferences, PropertyGroup
from bpy.props import *
from bpy.utils import register_class, unregister_class

from .. import __package__ as base_package

from . interface import operator

from . utility import addon, update, modifier

from . t3dn_bip.utils import support_pillow

import json

authoring_enabled = True
try:
    from . utility import matrixmath
except ImportError:
    authoring_enabled = False

import rna_keymap_ui


# The hierarchy for a KPACK reference is as follows

# -Set
# --MasterFolder
# ---KPACK
# ----INSERTS

# sets were introduced later, so to maintain backwards compatibility there is a set reference listing instead of a straight hierarchy.


class Set(PropertyGroup):
    pass  # implicitly has a set name associated with it.


class SetId(PropertyGroup):
    pass  # implicitly has a set name associated with it.


class folder(PropertyGroup):
    icon: StringProperty(default='FILE_FOLDER')

    name: StringProperty(
        name='Path Name',
        default='')

    visible: BoolProperty(
        name='Visible',
        description='Show KPACKS from this folder',
        default=True)

    location: StringProperty(
        name='Path',
        description='Path to KIT OPS library',
        update=update.libpath,
        subtype='DIR_PATH',
        default='')

    set_ids: CollectionProperty(type=SetId)


class favorite(PropertyGroup):
    pass


class recent(PropertyGroup):
    pass

def get_bool_options(self, context):
    if bpy.app.version >= (5, 0, 0):
        return [
            ('FLOAT', 'Float', 'Float solver for booleans'),
            ('EXACT', 'Exact', 'Exact solver for booleans'),
            ('MANIFOLD', 'Manifold', 'Manifold solver for booleans')]
    else:
        return [
            ('FAST', 'Fast', 'fast solver for booleans'),
            ('EXACT', 'Exact', 'exact solver for booleans')]


class kitops(AddonPreferences):
    bl_idname = base_package

    context: EnumProperty(
        name='Context',
        description='KIT OPS preference settings context',
        items=[
            ('GENERAL', 'General', ''),
            # ('THEME', 'Theme', ''),
            ('FILEPATHS', 'File Paths', ''),
            ('SEARCH', 'Search', '')],
        default='GENERAL')

    sets: CollectionProperty(type=Set)

    folders: CollectionProperty(type=folder)

    author: StringProperty(
        name='Author',
        description='Name that will be used when creating INSERTS',
        default='Your Name')

    insert_offset_x: IntProperty(
        name='INSERT offset X',
        description='Offset used when adding the INSERT from the mouse cursor',
        soft_min=-40,
        soft_max=40,
        subtype='PIXEL',
        default=0)

    insert_offset_y: IntProperty(
        name='INSERT offset Y',
        description='Offset used when adding the INSERT from the mouse cursor',
        soft_min=-40,
        soft_max=40,
        subtype='PIXEL',
        default=20)

    clean_names: BoolProperty(
        name='Clean names',
        description='Capatilize and clean up the names used in the UI from the KPACKS',
        update=update.kpack,
        default=False)

    clean_datablock_names: BoolProperty(
        name='Clean datablock names',
        description='Capatilize and clean up the names used for datablocks within INSERTS',
        default=False)

    thumbnail_labels: BoolProperty(
        name='Thumbnail labels',
        description='Displays names of INSERTS under the thumbnails in the preview popup',
        default=True)

    border_color: FloatVectorProperty(
        name='Border color',
        description='Color used for the border',
        min=0,
        max=1,
        size=4,
        precision=3,
        subtype='COLOR',
        default=(1.0, 0.030, 0.0, 0.9))

    border_size: IntProperty(
        name='Border size',
        description='Border size in pixels\n  Note: DPI factored',
        min=1,
        soft_max=6,
        subtype='PIXEL',
        default=1)

    border_offset: IntProperty(
        name='Border size',
        description='Border size in pixels\n  Note: DPI factored',
        min=1,
        soft_max=16,
        subtype='PIXEL',
        default=8)

    logo_color: FloatVectorProperty(
        name='Logo color',
        description='Color used for the KIT OPS logo',
        min=0,
        max=1,
        size=4,
        precision=3,
        subtype='COLOR',
        default=(1.0, 0.030, 0.0, 0.9))

    off_color: FloatVectorProperty(
        name='Off color',
        description='Color used for the KIT OPS logo when there is not an active insert with an insert target',
        min=0,
        max=1,
        size=4,
        precision=3,
        subtype='COLOR',
        default=(0.448, 0.448, 0.448, 0.1))

    logo_size: IntProperty(
        name='Logo size',
        description='Logo size in the 3d view\n  Note: DPI factored',
        min=1,
        soft_max=500,
        subtype='PIXEL',
        default=10)

    logo_padding_x: IntProperty(
        name='Logo padding x',
        description='Logo padding in the 3d view from the border corner\n  Note: DPI factored',
        subtype='PIXEL',
        default=18)

    logo_padding_y: IntProperty(
        name='Logo padding y',
        description='Logo padding in the 3d view from the border corner\n  Note: DPI factored',
        subtype='PIXEL',
        default=12)

    logo_auto_offset: BoolProperty(
        name='Logo auto offset',
        description='Offset the logo automatically for HardOps and BoxCutter',
        default=True)

    text_color: FloatVectorProperty(
        name='Text color',
        description='Color used for the KIT OPS help text',
        min=0,
        max=1,
        size=4,
        precision=3,
        subtype='COLOR',
        default=(1.0, 0.030, 0.0, 0.9))

    # displayed in panel
    mode: EnumProperty(
        name='Mode',
        description='Insert mode',
        items=[
            ('REGULAR', 'Regular', 'Stop creating modifiers for all INSERT objs except for new INSERTS\n  Note: Removes all insert targets'),
            ('SMART', 'Smart', 'Create modifiers as you work with an INSERT on the target obj')],
        update=update.mode,
        default='REGULAR')

    insert_scale: EnumProperty(
        name='Insert Scale',
        description='Insert scale mode based on the active obj when adding an INSERT',
        items=[
            ('LARGE', 'Large', ''),
            ('MEDIUM', 'Medium', ''),
            ('SMALL', 'Small', '')],
        update=update.insert_scale,
        default='LARGE')

    large_scale: IntProperty(
        name='Primary Scale',
        description='Percentage of obj size when adding an INSERT for primary',
        min=1,
        soft_max=200,
        subtype='PERCENTAGE',
        update=update.insert_scale,
        default=100)

    medium_scale: IntProperty(
        name='Secondary Scale',
        description='Percentage of obj size when adding an INSERT for secondary',
        min=1,
        soft_max=200,
        subtype='PERCENTAGE',
        update=update.insert_scale,
        default=50)

    small_scale: IntProperty(
        name='Tertiary Scale',
        description='Percentage of obj size when adding an INSERT for tertiary',
        min=1,
        soft_max=200,
        subtype='PERCENTAGE',
        update=update.insert_scale,
        default=25)

    auto_scale: BoolProperty(
        name='Auto scale INSERT',
        description='Scale INSERTS based on obj size',
        default=True)

    parent_inserts: BoolProperty(
        name='Parent INSERTs to the target object',
        description='Automatically Parent the INSERTS to the target object',
        default=False)

    boolean_solver: EnumProperty(
        name='Solver',
        description='',
        items=get_bool_options)

    place_on_insert: BoolProperty(
        name='Place on selected INSERT',
        description=('Place the object on the existing INSERT.  The new INSERT will still be associated with the target object. \n'
                     ' Keyboard shortcut: P'),
        default=False)

    snap_mode: EnumProperty(
        name='Snap Mode',
        description='',
        items=[
            ('NONE', 'None', 'No snapping \n Keyboard shortcut: N', 'CANCEL', 1),
            ('FACE', 'Face', 'Snap to face \n Keyboard shortcut: F', 'SNAP_FACE', 2),
            ('EDGE', 'Edge',
             'Snap to edge \n Keyboard shortcut: E [C - Toggle Snap to Edge Center]', 'SNAP_EDGE', 3),
            ('VERTEX', 'Vertex',
             'Snap to vertex \n Keyboard shortcut: V', 'SNAP_VERTEX', 4),
            ('HARDPOINT', 'Hardpoint', 'Snap to hardpoint \n Keyboard shortcut: H', 'EMPTY_ARROWS', 5)],
        default='NONE')
    
    restrict_axis: EnumProperty(
        name='Restrict Axis',
        description='',
        items=[
            ('NONE', 'None', 'No Restriction'),
            ('X', 'X', 'Restict to X axis'),
            ('Y', 'Y', 'Restict to Y axis'),
            ('Z', 'Z', 'Restict to Z axis'),],
        default='NONE')

    snap_mode_edge: EnumProperty(
        name='Snap Mode For Edges',
        description='',
        items=[
            ('NEAREST', 'Nearest',
             'Snap to nearest point on edge \n Keyboard shortcut: C'),
            ('CENTER', 'Center', 'Snap to edge center \n Keyboard shortcut: C')],
        default='NEAREST')

    snap_to_empty_hardpoints_only: BoolProperty(
        name="Only Snap to Empty Hardpoints",
        description="Only snap to hardpoints that have not already been snapped to.",
        default=True
    )

    use_snap_mode_hardpoint_tag_match: BoolProperty(
        name="Only Use Tags matching",
        description="Restrict which hardpoints are used"
    )

    snap_mode_hardpoint_tag_match: StringProperty(
        name="Tags to match on",
        description="Use these tags to restrict which hardpoints to use"
    )

    # TODO temporary disable until feature is elaborated.
    # use_insert_hardpoints : BoolProperty(
    #     name = "Use INSERT Hardpoints",
    #     description = "Use hardpoints from the INSERT when placing it",
    #     default=False
    # )

    use_insert_hardpoint_tag_match: BoolProperty(
        name="Only Use Tags matching",
        description="Restrict which hardpoints are used"
    )

    insert_hardpoint_tag_match: StringProperty(
        name="Tags to match on",
        description="Use these tags to restrict which of the INSERT\'s hardpoints to use"
    )

    flip_placement: BoolProperty(
        name="Flip Placement",
        description=("Flip the target object placement so the INSERT is added to the inside of the target object \n"
                     " Keyboard shortcut: I"),
        default=False

    )

    favorites: CollectionProperty(type=favorite)

    recently_used: CollectionProperty(type=recent)

    show_favorites: BoolProperty(
        name='Show Favorites',
        description='Show shortcuts to my favorite KPACKS',
        default=True)

    show_recents: BoolProperty(
        name='Show Recently Used',
        description='Show shortcuts to my most recently used KPACKS',
        default=True)

    sort_modifiers: BoolProperty(
        name='Sort Modifiers',
        description='\n Sort modifier order',
        update=update.sync_sort,
        default=True if bpy.app.version[:2] >= (4, 1) else False)

    sort_smooth: BoolProperty(
        name='Sort Smooth',
        description='\n Ensure smooth modifiers are placed after any boolean modifiers created',
        update=update.sync_sort,
        default=False)

    sort_bevel: BoolProperty(
        name='Sort Bevel',
        description='\n Ensure bevel modifiers are placed after any boolean modifiers created',
        update=update.sync_sort,
        default=False)

    sort_weighted_normal: BoolProperty(
        name='Sort Weighted Normal',
        description='\n Ensure weighted normal modifiers are placed after any boolean modifiers created',
        update=update.sync_sort,
        default=False)

    sort_array: BoolProperty(
        name='Sort Array',
        description='\n Ensure array modifiers are placed after any boolean modifiers created',
        update=update.sync_sort,
        default=False)

    sort_mirror: BoolProperty(
        name='Sort Mirror',
        description='\n Ensure mirror modifiers are placed after any boolean modifiers created',
        update=update.sync_sort,
        default=False)

    sort_solidify: BoolProperty(
        name='Sort Soldify',
        description='\n Ensure solidify modifiers are placed after any boolean modifiers created',
        update=update.sync_sort,
        default=False)

    sort_triangulate: BoolProperty(
        name='Sort Triangulate',
        description='\n Ensure triangulate modifiers are placed after any boolean modifiers created',
        update=update.sync_sort,
        default=False)

    sort_simple_deform: BoolProperty(
        name='Sort Simple Deform',
        description='\n Ensure simple deform modifiers are placed after any boolean modifiers created',
        update=update.sync_sort,
        default=False)

    sort_decimate: BoolProperty(
        name='Sort Decimate',
        description='\n Ensure decimate modifiers are placed after any boolean modifiers created',
        update=update.sync_sort,
        default=False)

    sort_remesh: BoolProperty(
        name='Sort Remesh',
        description='\n Ensure remesh modifiers are placed after any boolean modifiers created',
        update=update.sync_sort,
        default=False)

    sort_subsurf: BoolProperty(
        name='Sort Subsurf',
        description='\n Ensure subsurf modifiers are placed after any boolean modifiers created',
        update=update.sync_sort,
        default=False)

    sort_weld: BoolProperty(
        name='Sort Weld',
        description='\n Ensure weld modifiers are placed after any boolean modifiers created',
        update=update.sync_sort,
        default=False)

    sort_smooth_last: BoolProperty(
        name='Sort Smooth',
        description='\n Only effect the most recent smooth modifier when sorting',
        update=update.sync_sort,
        default=True)

    sort_uv_project: BoolProperty(
        name='Sort UV Project',
        description='\n Ensure uv project modifiers are placed after any boolean modifiers created',
        update=update.sync_sort,
        default=False)

    sort_auto_smooth: BoolProperty(
        name='Auto Smooth',
        description='\n Ensure auto smooth modifiers are placed after any boolean modifiers created',
        update=update.sync_sort,
        default=True)

    sort_smooth_by_angle: BoolProperty(
        name='Sort Smooth by Angle',
        description='\n Ensure smooth by angle modifiers are placed after any boolean modifiers created',
        update=update.sync_sort,
        default=True)

    sort_bevel_last: BoolProperty(
        name='Sort Bevel',
        description='\n Only effect the most recent bevel modifier when sorting',
        update=update.sync_sort,
        default=True)

    sort_weighted_normal_last: BoolProperty(
        name='Sort Weighted Normal Last',
        description='\n Only effect the most recent weighted normal modifier when sorting',
        update=update.sync_sort,
        default=True)

    sort_array_last: BoolProperty(
        name='Sort Array Last',
        description='\n Only effect the most recent array modifier when sorting',
        update=update.sync_sort,
        default=True)

    sort_mirror_last: BoolProperty(
        name='Sort Mirror Last',
        description='\n Only effect the most recent mirror modifier when sorting',
        update=update.sync_sort,
        default=True)

    sort_solidify_last: BoolProperty(
        name='Sort Soldify Last',
        description='\n Only effect the most recent solidify modifier when sorting',
        update=update.sync_sort,
        default=False)

    sort_triangulate_last: BoolProperty(
        name='Sort Triangulate Last',
        description='\n Only effect the most recent triangulate modifier when sorting',
        update=update.sync_sort,
        default=True)

    sort_simple_deform_last: BoolProperty(
        name='Sort Simple Deform Last',
        description='\n Only effect the most recent simple deform modifier when sorting',
        update=update.sync_sort,
        default=True)

    sort_decimate_last: BoolProperty(
        name='Sort Decimate Last',
        description='\n Only effect the most recent decimate modifier when sorting',
        update=update.sync_sort,
        default=False)

    sort_remesh_last: BoolProperty(
        name='Sort Remesh Last',
        description='\n Only effect the most recent remesh modifier when sorting',
        update=update.sync_sort,
        default=True)

    sort_subsurf_last: BoolProperty(
        name='Sort Subsurf Last',
        description='\n Only effect the most recent subsurface modifier when sorting',
        update=update.sync_sort,
        default=False)

    sort_weld_last: BoolProperty(
        name='Sort Weld Last',
        description='\n Only effect the most recent weld modifier when sorting',
        update=update.sync_sort,
        default=True)

    sort_uv_project_last: BoolProperty(
        name='Sort UV Project Last',
        description='\n Only effect the most recent uv project modifier when sorting',
        update=update.sync_sort,
        default=True)

    sort_auto_smooth_last: BoolProperty(
        name='Sort Auto Smooth Last',
        description='\n Only effect the most recent Auto Smooth modifier when sorting',
        update=update.sync_sort,
        default=True)

    sort_smooth_by_angle_last: BoolProperty(
        name='Sort Smooth by Angle Last',
        description='\n Only effect the most recent Smooth by Angle modifier when sorting',
        update=update.sync_sort,
        default=True)

    sort_bevel_ignore_weight: BoolProperty(
        name='Ignore Weight Bevels',
        description='\n Ignore bevel modifiers that are using the weight limit method while sorting',
        update=update.sync_sort,
        default=True)

    sort_bevel_ignore_vgroup: BoolProperty(
        name='Ignore VGroup Bevels',
        description='\n Ignore bevel modifiers that are using the vertex group limit method while sorting',
        update=update.sync_sort,
        default=True)

    sort_bevel_ignore_only_verts: BoolProperty(
        name='Ignore Only Vert Bevels',
        description='\n Ignore bevel modifiers that are using the only vertices option while sorting',
        update=update.sync_sort,
        default=True)

    sort_depth: IntProperty(
        name='Sort Depth',
        description='\n Number of sortable mods from the end (bottom) of the stack. 0 to sort whole stack',
        min=0,
        default=6)

    sort_ignore_char: StringProperty(
        name='Ignore Flag',
        description='\n Prefix the modifier name with this text character and it will be ignored\n  Default: Space',
        update=update.sort_ignore_char,
        maxlen=1,
        default=' ')

    sort_stop_char: StringProperty(
        name='Stop Flag',
        description='\n Prefix a modifier name with this text character and it will not sort modifiers previous to it',
        update=update.sort_stop_char,
        maxlen=1,
        default='_')

    hardpoint_preview_color: FloatVectorProperty(name="Hardpoint Preview Color",
                                                 subtype='COLOR',
                                                 size=4,
                                                 default=[0, 1, 0, 0.5])

    remove_props_when_no_target : BoolProperty(
        name="Remove KIT OPS props when no target",
        description="Remove the properties from the INSERT when there is no target object",
        default=True
    )

    default_render_mode: EnumProperty(
        name='Default Render Engine',
        description='Default render engine to use for KIT OPS',
        items=[
            ('EEVEE', 'Eevee', 'Use Blender Eevee as the default render engine'),
            ('CYCLES', 'Cycles', 'Use Blender Cycles as the default render engine')],
        default='CYCLES')

    def draw(self, context):
        layout = self.layout

        column = layout.column(align=True)

        row = column.row(align=True)
        row.prop(self, 'context', expand=True)

        box = column.box()
        box.separator()
        getattr(self, self.context.lower())(context, box)
        box.separator()

    def general(self, context, layout):
        row = layout.row()
        row.label(text='Author')
        row.prop(self, 'author', text='')

        layout.separator()

        row = layout.row()
        row.label(text='INSERT offset X')
        row.prop(self, 'insert_offset_x', text='')

        row = layout.row()
        row.label(text='INSERT offset Y')
        row.prop(self, 'insert_offset_y', text='')

        if bpy.app.version > (2, 90, 0):
            row = layout.row()
            row.label(text='Boolean Solver')
            row.prop(self, 'boolean_solver', expand=True)

        row = layout.row()
        row.label(text='Thumbnail labels')
        row.prop(self, 'thumbnail_labels', text='')

        row = layout.row()
        row.label(text='Remove KIT OPS properties when no target')
        row.prop(self, 'remove_props_when_no_target', text='')

        row = layout.row()
        row.label(text='Sort Modifiers')
        row.prop(self, 'sort_modifiers', text='')

        if self.sort_modifiers:
            row = layout.row(align=True)
            row.alignment = 'RIGHT'
            split = row.split(align=True, factor=0.85)

            row = split.row(align=True)
            for type in modifier.sort_types:
                icon = F'MOD_{type}'
                if icon == 'MOD_WEIGHTED_NORMAL':
                    icon = 'MOD_NORMALEDIT'
                elif icon == 'MOD_SIMPLE_DEFORM':
                    icon = 'MOD_SIMPLEDEFORM'
                elif icon == 'MOD_DECIMATE':
                    icon = 'MOD_DECIM'
                elif icon == 'MOD_WELD':
                    icon = 'AUTOMERGE_OFF'
                elif icon == 'MOD_UV_PROJECT':
                    icon = 'MOD_UVPROJECT'
                elif icon == 'MOD_AUTO_SMOOTH':
                    icon = 'GEOMETRY_NODES'
                elif icon == 'MOD_SMOOTH_BY_ANGLE':
                    icon = 'GEOMETRY_NODES'
                row.prop(self, F'sort_{type.lower()}', text='', icon=icon)

            row = split.row(align=True)
            row.scale_x = 1.5
            row.popover('KO_PT_sort_last', text='', icon='SORT_ASC')

        row = layout.row()
        row.operator('mesh.ko_export_settings')
        row.operator('mesh.ko_import_settings')

        # Pillow

        box = layout.box()
        supported = support_pillow()

        col = box.column()
        if supported:
            col.label(text="Thumbnail Caching: Enabled")
        else:
            col.label(text="Thumbnail Caching: Disabled")

        col.separator()
        col.label(
            text="While the thumbnail cache accelerator is not required, it provides a superior user experience. ")
        col.label(
            text="You must have a working INTERNET connection on order to install it, and it only needs to install once.")
        col.separator()

        if supported:
            col.operator('mesh.ko_install_pillow',
                         text="Thumbnail Caching Engine Installed Successfully")
        else:
            col.operator('mesh.ko_install_pillow',
                         text="Install Thumbnail Caching Engine")

        # Favorites
        if authoring_enabled:
            col = layout.column()
            col.label(text="Favorites")
            col.separator()
            col.operator("mesh.ko_clear_favorites_confirm",
                         text="Clear All Favorites")

            col = layout.column()
            col.label(text="Hardpoints")
            col.separator()
            col.prop(self, 'hardpoint_preview_color',
                     text="Hardpoint Preview Color")


        col = layout.column()
        col.label(text="Default Render Engine")
        col.row().prop(self, 'default_render_mode', expand=True)


    def theme(self, context, layout):
        row = layout.row()
        row.label(text='Border color')
        row.prop(self, 'border_color', text='')

        row = layout.row()
        row.label(text='Border size')
        row.prop(self, 'border_size', text='')

        row = layout.row()
        row.label(text='Border offset')
        row.prop(self, 'border_offset', text='')

        row = layout.row()
        row.label(text='Logo color')
        row.prop(self, 'logo_color', text='')

        row = layout.row()
        row.label(text='Off color')
        row.prop(self, 'off_color', text='')

        row = layout.row()
        row.label(text='Logo size')
        row.prop(self, 'logo_size', text='')

        row = layout.row()
        row.label(text='Logo padding x')
        row.prop(self, 'logo_padding_x', text='')

        row = layout.row()
        row.label(text='Logo padding y')
        row.prop(self, 'logo_padding_y', text='')

        row = layout.row()
        row.label(text='Logo auto offset')
        row.prop(self, 'logo_auto_offset', text='')

        row = layout.row()
        row.label(text='Text color')
        row.prop(self, 'text_color', text='')

    def filepaths(self, context, layout):

        option = addon.option()

        col = layout.column()

        folders_to_search = []

        if authoring_enabled:

            col_row = col.row()

            col_row.alignment = "LEFT"

            col_row.prop(option, 'kpack_prefs_set')

            if option.kpack_prefs_set != 'ALL':
                props = col_row.operator(
                    'mesh.ko_remove_set', text="", icon='CANCEL')
                props.set_name = option.kpack_prefs_set

            col_row.label(text="New Set: ")

            col_row.prop(option, 'new_set_name', text="")

            props = col_row.operator('mesh.ko_add_set', text="CREATE")
            props.set_name = option.new_set_name

            col_row.prop(option, 'filter_sets', text="Filter")

            if 'ALL' == option.filter_sets:
                folders_to_search.extend([f for f in self.folders])
            if 'VISIBLE' == option.filter_sets:
                folders_to_search.extend(
                    [f for f in self.folders if option.kpack_prefs_set in f.set_ids])
            if 'INVISIBLE' == option.filter_sets:
                folders_to_search.extend(
                    [f for f in self.folders if option.kpack_prefs_set not in f.set_ids])
                

            if option.kpack_prefs_set != 'ALL':
                col_row.label(text="Set all Folders: ")
                col_row_visibility  = col_row.row(align=True)
                col_row_visibility.operator('mesh.ko_add_folders_to_set', text="Visible")
                col_row_visibility.operator('mesh.ko_remove_folders_from_set', text="Invisible")

        else:
            folders_to_search.extend([f for f in self.folders])

        for index, folder in enumerate(folders_to_search):
            row1 = layout.row()
            split = row1.split(factor=0.3)

            row2 = split.row(align=True)
            row2.prop(folder, 'name', text='', emboss=False)

            if option.kpack_prefs_set != 'ALL':
                if option.kpack_prefs_set not in folder.set_ids:
                    props = row2.operator(
                        'mesh.ko_add_set_id', text="", icon='HIDE_ON', emboss=False)
                else:
                    props = row2.operator(
                        'mesh.ko_remove_set_id', text="", icon='HIDE_OFF', emboss=False)

                props.folder_name = folder.name
                props.set_name = option.kpack_prefs_set

            row3 = split.row(align=True)
            op = row3.operator('mesh.ko_move_folder', text='', icon='TRIA_UP')
            op.index, op.direction = index, -1
            op = row3.operator('mesh.ko_move_folder', text='', icon='TRIA_DOWN')
            op.index, op.direction = index, 1
            row3.prop(folder, 'location', text='')

            op = row1.operator('mesh.ko_remove_kpack_path', text='',
                               emboss=False, icon='PANEL_CLOSE')
            op.index = index

        row = layout.row()
        split = row.split(factor=0.3)

        split.separator()
        split.operator('mesh.ko_add_kpack_path', text='', icon='PLUS')

        sub = row.row()
        sub.operator('mesh.ko_refresh_kpacks', text='',
                     emboss=False, icon='FILE_REFRESH')



    def search(self, context, layout):

        option = addon.option()

        col = layout.column()

        search_input_row = col.row()
        search_input_row.alignment="CENTER"

        search_input_row.prop(option, "masterfolder_search_input", text="Search All Masterfolders" )

        search_input_row.operator('search.kpacks', text="Search")
        search_input_row.operator('clear.kpack_search', text="Clear")



        # If there are no results, display a message and return
        if len(option.kpacks_search_results) == 0:
            layout.label(text="No results found.")
            return
        
        column = layout.column(align=True)

        # Create a table-like UI using rows and columns
        box = column.box()

        # Header
        row = box.row()
        
        # Making the header bolder and embossed
        col = row.column()
        col.scale_y = 1.2  # Slightly larger text for header
        col.label(text=".blend File")
        
        col = row.column()
        col.scale_y = 1.2
        col.label(text="Master Folder")
        
        col = row.column()
        col.scale_y = 1.2
        col.label(text="KPACK")

        col = row.column()
        col.scale_y = 1.2
        col.label(text="")

        box = column.box()

        # Populate table with search results
        for result in option.kpacks_search_results:
            row = box.row()
            row.label(text=result.blend_file)
            row.label(text=result.master_folder)
            row.label(text=result.pack)
            props = row.operator("mesh.ko_select_kpack_insert", text="Load INSERT")
            props.kpack_set = 'ALL'
            props.kpack_name = result.pack
            props.insert_name = result.insert_name

def get_hotkey_entry_item(km, kmi_name, kmi_value, properties):
    for i, km_item in enumerate(km.keymap_items):
        if km.keymap_items.keys()[i] == kmi_name:
            if properties == 'name':
                if km.keymap_items[i].properties.name == kmi_value:
                    return km_item
            elif properties == 'tab':
                if km.keymap_items[i].properties.tab == kmi_value:
                    return km_item
            elif properties == 'none':
                return km_item
    return None

classes = [
    Set,
    SetId,
    favorite,
    recent,
    folder,
    kitops]


def register():
    for cls in classes:
        register_class(cls)

    addon.preference()


def unregister():
    for cls in classes:
        unregister_class(cls)
