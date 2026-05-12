import bpy

from bpy.types import Panel, UIList
from bpy.utils import register_class, unregister_class

from ... import bl_info
from .. utility import addon, dpi, insert, update, modifier, previews, persistence, thumbnails

authoring_enabled = True
try: from .. utility import matrixmath
except ImportError: authoring_enabled = False

import os


def _is_standard_mode(context):
    '''determines whether the standard or authoring panel should be displayed'''
    option = addon.option()
    return not option.authoring_mode and not context.scene.kitops.thumbnail

class KO_PT_Main(Panel):
    bl_space_type = 'VIEW_3D'
    bl_label = 'KIT OPS'
    bl_region_type = 'UI'
    bl_category = '♥♥♥'
    bl_idname = "KITOPS_PT_Panel_Main"

    def draw_header_preset(self, context):
        layout = self.layout
        row = layout.row()

        version = bl_info['version']
        row.label(text=f"v{version[0]}.{version[1]}.{version[2]}")
        row.operator("mesh.ko_open_help_url", icon='QUESTION', text="").url = "http://cw1.me/kitops3"

        row.separator()

    def draw(self, context):
        pass



class KO_PT_KPACKS(Panel):
    bl_space_type = 'VIEW_3D'
    bl_label = 'KPACKS'
    bl_region_type = 'UI'
    bl_category = '♥♥♥'
    bl_parent_id = 'KITOPS_PT_Panel_Main'

    @classmethod
    def poll(cls, context):
        return _is_standard_mode(context)

    def draw_header_preset(self, context):
        layout = self.layout
        preference = addon.preference()
        if authoring_enabled:
            row = layout.row(align=True)
            if not preference.show_favorites:
                row.prop(preference, 'show_favorites', text="", icon="SOLO_OFF", emboss=False)
            if not preference.show_recents:
                row.prop(preference, 'show_recents', text="", icon="MOD_TIME", emboss=False)



    def draw(self, context):
        global authoring_enabled

        layout = self.layout
        preference = addon.preference()
        option = addon.option()
        scene = context.scene

        if len(option.kpack.categories):



            column = layout.column(align=True)
            if authoring_enabled:
                set_col = column.column()
                set_col.prop(option, 'kpack_set', text='')
                set_col.separator()


            #fvs and rts
            if authoring_enabled:
                matrixmath.draw_fvs_rcts(column)
                column = column.box().column(align=True)

                

            row = column.row(align=True)
            if authoring_enabled and option.kpack.active_index < len(option.kpack.categories):
                category = option.kpack.categories[option.kpack.active_index]
                is_favorite = option.kpack_set + '>' + category.name in preference.favorites
                props = row.operator('mesh.ko_add_favorite' if not is_favorite else 'mesh.ko_remove_favorite', text='', icon="SOLO_ON" if is_favorite else "SOLO_OFF", depress=is_favorite)
                props.kpack_set = option.kpack_set
                props.kpack_name = category.name

            row.prop(option, 'kpacks', text='')

            row.operator('mesh.ko_refresh_kpacks', text='', icon='FILE_REFRESH').record_previous = True


            if option.kpack.active_index < len(option.kpack.categories):
                category = option.kpack.categories[option.kpack.active_index]

                row = column.row(align=True)

                sub = row.row(align=True)
                sub.scale_y = 6
                sub.operator('mesh.ko_previous_kpack', text='', icon='TRIA_LEFT')

                row.template_icon_view(category, 'thumbnail', show_labels=preference.thumbnail_labels)

                sub = row.row(align=True)
                sub.scale_y = 6
                sub.operator('mesh.ko_next_kpack', text='', icon='TRIA_RIGHT')


                insert_blend = category.blends[category.active_index]

                if insert_blend.is_legacy:
                    row = column.row(align=True)
                    row.scale_y = 1.5
                    op = row.operator('mesh.ko_add_insert')
                    op.location = insert_blend.location
                    op.material = False
                    op.rotation_amount = 0

                    row.scale_y = 1.5
                    op = row.operator('mesh.ko_add_insert_material')
                    op.location = insert_blend.location
                    op.material = True
                else:
                    insert_type = insert_blend.insert_type
                    row = column.row(align=True)
                    row.scale_y = 1.5
                    if insert_type in {'INSERT', 'DECAL'}:
                        operator_name = 'Add INSERT' if insert_type == 'INSERT' else 'Add DECAL'
                        op = row.operator('mesh.ko_add_insert', text=operator_name)
                        op.location = insert_blend.location
                        op.material = False
                        op.rotation_amount = 0
                    elif insert_type == 'GEO_NODES':
                        op = row.operator('mesh.ko_add_insert_gn', text='Add Geo Node INSERT')
                        op.location = insert_blend.location
                    elif insert_type == 'SHADER_NODES':
                        op = row.operator('mesh.ko_add_insert_shader_nodes', text='Add Shader Node INSERT')
                        op.location = insert_blend.location
                    elif insert_type in {'MATERIAL'}:
                        operator_name = 'Add Material INSERT'
                        op = row.operator('mesh.ko_add_insert_material', text=operator_name)
                        op.location = insert_blend.location
                        op.material = True



                row = column.row()
                row.operator('mesh.ko_select_insert')
                    
                column.separator()

                if authoring_enabled:
                    
                    row = column.row()
                    row.operator('mesh.ko_select_inserts')

                    column.separator()

                row = column.row()
                row.operator('mesh.ko_duplicate_insert')

                column.separator()
                
                row = column.row()
                row.operator('mesh.ko_delete_insert')

                if authoring_enabled:

                    column.separator()

                    row = column.row()
                    row.operator('mesh.ko_move_insert')

                    column.separator()

                    row = column.row()
                    row.operator('mesh.ko_edit_insert')

                    column.separator()

                    row = column.row(align=True)
                    op = row.operator('mesh.ko_remove_insert_properties')
                    op.remove = False
                    op.uuid = ''

                    sub = row.row(align=True)
                    sub.enabled = context.active_object.kitops.insert if context.active_object else False
                    op = sub.operator('mesh.ko_remove_insert_properties_x', text='', icon='X')
                    op.remove = True
                    op.uuid = ''

                    column.separator()

                    row = column.row()
                    row.operator('mesh.ko_replace_insert', text='Replace INSERT(s)')

                column.separator()

                row = column.row()
                row.operator('mesh.ko_load_search_window', text="Search INSERTs")


            active = context.active_object

            
            if active and hasattr(active, 'kitops') and active.kitops.insert:

                    col =layout.column()
                    col.label(text='Target Object:')
                    row = col.row(align=True)

                    row.prop(context.active_object.kitops, 'insert_target', text='')


class KO_PT_Modifiers(Panel):
    bl_space_type = 'VIEW_3D'
    bl_label = 'Modifiers'
    bl_region_type = 'UI'
    bl_category = '♥♥♥'
    bl_parent_id = 'KITOPS_PT_Panel_Main'
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        return _is_standard_mode(context)

    def draw(self, context):
        global authoring_enabled

        layout = self.layout
        preference = addon.preference()
        option = addon.option()
        scene = context.scene

        if len(option.kpack.categories):
            active = context.active_object

            if active and hasattr(active, 'kitops') and active.kitops.insert:

                    split = layout.split(factor=0.25, align=True)
                    split.label(text='Mirror:')
                    row = split.row(align=True)
                    row.prop(context.active_object.kitops, 'mirror_x', text='X', toggle=True)
                    row.prop(context.active_object.kitops, 'mirror_y', text='Y', toggle=True)
                    row.prop(context.active_object.kitops, 'mirror_z', text='Z', toggle=True)

                    split = layout.split(factor=0.25, align=True)
                    split.label(text='Array:')
                    array_row = split.column(align=True)

                    array_row_count = array_row.split(factor=0.4, align=True)
                    array_row_count.label(text='Count:')
                    array_row_count.prop(context.active_object.kitops, 'array_count', text='')

                    array_row_offset = array_row.split(factor=0.4, align=True)
                    array_row_offset.label(text="Offset:")
                    array_row_offset.column(align=True).prop(context.active_object.kitops, 'array_offset', text='')
            else:
                col = layout.column(align=True)
                col.label(text="No INSERT selected.")


class KO_PT_Controls(Panel):
    bl_space_type = 'VIEW_3D'
    bl_label = 'Controls'
    bl_region_type = 'UI'
    bl_category = '♥♥♥'
    bl_parent_id = 'KITOPS_PT_Panel_Main'
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        return _is_standard_mode(context)

    def draw(self, context):


        global authoring_enabled

        layout = self.layout
        preference = addon.preference()
        option = addon.option()
        scene = context.scene

        if len(option.kpack.categories):

            column = layout.column(align=True)
            column.enabled = preference.auto_scale
            row = column.row(align=True)
            row.prop(preference, 'insert_scale', expand=True)
            column.prop(preference, '{}_scale'.format(preference.insert_scale.lower()), text='Scale')
            layout.separator()

            layout.prop(preference, 'auto_scale')
            layout.prop(preference, 'parent_inserts', text="Parent INSERTs")
            
            if authoring_enabled:
                
                layout.prop(preference, 'place_on_insert')
                layout.prop(preference, 'flip_placement')

            layout.separator()

            col_snap = layout.column(align=True)
            row_snap = col_snap.row(align=True)
            row_snap.label(text="Snap Mode:")


            row_snap.prop_enum(preference, 'snap_mode', 'NONE', text='' , icon='CANCEL')
            row_snap.prop_enum(preference, 'snap_mode', 'VERTEX', text='' , icon='SNAP_VERTEX')
            row_snap.prop_enum(preference, 'snap_mode', 'EDGE', text='' , icon='SNAP_EDGE')
            row_snap.prop_enum(preference, 'snap_mode', 'FACE', text='' , icon='SNAP_FACE')
            row_snap.prop_enum(preference, 'snap_mode', 'HARDPOINT', text='' , icon='EMPTY_ARROWS')

            if preference.snap_mode == 'EDGE':
                row_snap = layout.row(align=True)
                row_snap.alignment = 'RIGHT'
                row_snap.label(text="Snap to")
                row_snap.prop(preference, 'snap_mode_edge', expand=True)

            if preference.snap_mode == 'HARDPOINT':
                col_snap = layout.column(align=True)

                row_snap = col_snap.row(align=True)
                row_snap.separator()
                row_snap.prop(preference, 'snap_to_empty_hardpoints_only')

                row_snap = col_snap.row(align=True)
                row_snap.separator()
                row_snap.prop(preference, "use_snap_mode_hardpoint_tag_match", text="Only Use Tags Matching: ")
                row_tag_match = row_snap.row(align=True)
                row_tag_match.enabled = preference.use_snap_mode_hardpoint_tag_match
                row_tag_match.prop(preference, 'snap_mode_hardpoint_tag_match', text="")


            if context.active_object and context.active_object.kitops.insert_target:
                layout.label(text='Align')

                row = layout.row()
                row.scale_y = 1.5
                row.scale_x = 1.5

                row.operator('mesh.ko_align_top', text='', icon_value=previews.get(addon.icons['align-top']).icon_id)
                row.operator('mesh.ko_align_bottom', text='', icon_value=previews.get(addon.icons['align-bottom']).icon_id)
                row.operator('mesh.ko_align_left', text='', icon_value=previews.get(addon.icons['align-left']).icon_id)
                row.operator('mesh.ko_align_right', text='', icon_value=previews.get(addon.icons['align-right']).icon_id)

                row = layout.row()
                row.scale_y = 1.5
                row.scale_x = 1.5
                row.operator('mesh.ko_align_horizontal', text='', icon_value=previews.get(addon.icons['align-horiz']).icon_id)
                row.operator('mesh.ko_align_vertical', text='', icon_value=previews.get(addon.icons['align-vert']).icon_id)
                row.operator('mesh.ko_stretch_wide', text='', icon_value=previews.get(addon.icons['stretch-wide']).icon_id)
                row.operator('mesh.ko_stretch_tall', text='', icon_value=previews.get(addon.icons['stretch-tall']).icon_id)


class KO_PT_Management(Panel):
    bl_space_type = 'VIEW_3D'
    bl_label = 'Tools'
    bl_region_type = 'UI'
    bl_category = '♥♥♥'
    bl_parent_id = 'KITOPS_PT_Panel_Main'
    bl_idname = "KITOPS_PT_Panel_Tools"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        return _is_standard_mode(context)

    def draw(self, context):


        global authoring_enabled

        layout = self.layout
        preference = addon.preference()
        option = addon.option()
        scene = context.scene

        if len(option.kpack.categories):

            if context.window_manager.kitops.pro:
                if context.scene.kitops.thumbnail:
                    layout.separator()

                    row = layout.row()
                    row.scale_y = 1.5
                    op = row.operator('mesh.ko_render_thumbnail', text='Render thumbnail')
                    op.render = True
                    op.import_scene = False
            if context.window_manager.kitops.pro and not context.scene.kitops.thumbnail:

                row = layout.row()
                row.scale_y = 1.5
                row.operator('mesh.ko_clean_boolean_modifiers')

                master_col = layout.column()

                master_col.scale_y = 1.5

                # Row 1
                row = master_col.row()

                if context.active_object:
                    insert_path = persistence.insert_path(context.active_object.name, context)
                    if context.active_object and os.path.exists(insert_path):
                        op_ref = "mesh.ko_auto_create_insert_confirm"
                    else:
                        op_ref = "mesh.ko_auto_create_insert"

                    op = row.operator(op_ref, text="Create INSERT")
                    op.set_object_origin_to_bottom = False
                    op.material = False
                    op.directory = ''
                    op.create_type = 'INSERT'

                    op = row.operator(op_ref, text="Create GEO NODES")
                    op.set_object_origin_to_bottom = False
                    op.material = False
                    op.directory = ''
                    op.create_type = 'GEO_NODES'

                # Row 2
                row = master_col.row()

                if context.active_object and context.active_object.active_material:
                    material_path = persistence.insert_path(context.active_object.active_material.name, context)
                    if os.path.exists(material_path):
                        op_ref = "mesh.ko_auto_create_insert_confirm"
                    else:
                        op_ref = "mesh.ko_auto_create_insert"

                    op = row.operator(op_ref, text="Create MATERIAL")
                    op.set_object_origin_to_bottom = False
                    op.material = True
                    op.directory = ''
                    op.create_type = 'MATERIAL'

                    material_path = persistence.insert_path(context.active_object.name, context)
                    if os.path.exists(material_path):
                        op_ref = "mesh.ko_auto_create_insert_confirm"
                    else:
                        op_ref = "mesh.ko_auto_create_insert"

                    op = row.operator(op_ref, text="Create SHADER NODES")
                    op.set_object_origin_to_bottom = False
                    op.material = True
                    op.directory = ''
                    op.create_type = 'SHADER_NODES'

                # Row 3
                if context.active_object:
                    row = master_col.row()
                    row.operator('mesh.ko_create_decal', text='Create DECAL')

                    
            else:
                row = layout.row()
                row.scale_y = 1.5


            master_col.separator()
            if not context.scene.kitops.thumbnail:
                row.operator('mesh.ko_convert_to_mesh', text='Convert to mesh')

            row = layout.row()
            row.scale_y = 1.5
            row.operator('mesh.ko_select_similar_insert', text='Select Similar INSERTs')


            if context.window_manager.kitops.kpack:
                row = layout.row()
                row.scale_y = 1.5
                props = row.operator("mesh.ko_open_kpack_folder", text="Open KPACK Directory")
                props.directory_path = persistence.directory_from(context.window_manager.kitops.kpack)


        if not context.scene.kitops.thumbnail:

            row = layout.row()
            row.scale_y = 1.5
            row.operator('mesh.ko_remove_wire_inserts')           



class KO_PT_AssetManagement(Panel):
    bl_space_type = 'VIEW_3D'
    bl_label = 'Convert Assets'
    bl_region_type = 'UI'
    bl_category = '♥♥♥'
    bl_parent_id = 'KITOPS_PT_Panel_Tools'

    @classmethod
    def poll(cls, context):
        return _is_standard_mode(context)

    def draw(self, context):
        global authoring_enabled

        layout = self.layout
        preference = addon.preference()
        option = addon.option()
        
        kitops_scene = context.scene.kitops
        kitops_options = context.window_manager.kitops
        col = layout.column()
        col.prop(kitops_options, "asset_libraries_options", text="Library")
        col.prop(kitops_options, "asset_libraries_catalogs", text="Catalog")
        col.prop(kitops_options, "asset_destination_dir", text="Destination")
        progress_col = col.column()
        progress_col.enabled = not kitops_options.asset_processing_is_running
        if not kitops_options.asset_processing_is_running:
            progress_col.operator('mesh.ko_convert_assets_to_kitops')
        else:            
            progress_col.prop(kitops_options, "asset_processing_progress", slider=True, text="Processing... " + kitops_options.currently_processing_asset)


icon_scale = 7
class KO_PT_Authoring(Panel):
    bl_space_type = 'VIEW_3D'
    bl_label = 'Authoring'
    bl_region_type = 'UI'
    bl_category = '♥♥♥'
    bl_parent_id = 'KITOPS_PT_Panel_Main'

    @classmethod
    def poll(cls, context):
        return not _is_standard_mode(context)

    def draw(self, context):
        global authoring_enabled

        layout = self.layout
        preference = addon.preference()
        option = addon.option()
        scene = context.scene

        column = layout.column(align=True)

        path, _ = thumbnails.get_thumbnail_path(context)


        if option.authoring_mode:
            if not authoring_enabled:
                layout.label(icon='ERROR', text='Purchase KIT OPS PRO')
                layout.label(icon='BLANK1', text='To use these features')

            if context.scene.kitops.factory:
                column.enabled = authoring_enabled

                column.label(text='INSERT name')
                column.prop(option, 'insert_name', text='')


            column.enabled = authoring_enabled
            column.label(text='Author')
            column.prop(option, 'author', text='')




            global icon_scale
            box = column.box()
            box_column = box.column(align=True)
            try:
                box_column.template_icon(icon_value=previews.get(path).icon_id, scale=icon_scale)
            except FileNotFoundError:
                box_column.template_icon(icon_value=previews.get(addon.path.default_thumbnail()).icon_id, scale=icon_scale)

        if option.authoring_mode or context.scene.kitops.thumbnail:

            row = column.row(align=True)
            row.scale_y = 1.5
            if not context.scene.kitops.thumbnail:




                col = row.column(align=True)
                col.label(text="Choose type of thumb")
                col.prop(option, 'save_insert_type', text='')


                op = col.operator('mesh.ko_render_thumbnail', text='Open Thumbnail Scene', icon='VIEW_CAMERA_UNSELECTED')
                op.render = False
                op.import_scene = True
                op.insert_type = option.save_insert_type

                control_box = layout.box()

                if context.active_object and (not context.active_object.kitops.temp or scene.kitops.factory):
                    if context.active_object.type not in {'LAMP', 'CAMERA', 'SPEAKER', 'EMPTY'}:
                        row = control_box.row()
                        row.enabled = authoring_enabled and not context.active_object.kitops.temp and not context.active_object.kitops.material_base
                        row.prop(context.active_object.kitops, 'main')

                    row = control_box.row()
                    row.enabled = authoring_enabled and not context.active_object.kitops.temp and not context.active_object.kitops.material_base
                    row.prop(context.active_object.kitops, 'type', expand=True)

                    if context.active_object.type == 'MESH' and context.active_object.kitops.type == 'CUTTER':
                        row = control_box.row()
                        row.enabled = authoring_enabled and not context.active_object.kitops.temp and not context.active_object.kitops.material_base
                        row.prop(context.active_object.kitops, 'boolean_type', text='Type')

                elif context.active_object and context.active_object.type == 'MESH' and scene.kitops.thumbnail:
                    row = control_box.row()
                    row.enabled = authoring_enabled
                    row.prop(context.active_object.kitops, 'ground_box')

                
                column_1 = control_box.column(align=True)
                if option.authoring_mode or context.scene.kitops.thumbnail:
                    # control_box.separator()

                    if context.active_object:
                        column = column_1.column(align=True)
                        column.enabled = authoring_enabled and not context.active_object.kitops.main and not context.active_object.kitops.temp
                        column.prop(context.active_object.kitops, 'selection_ignore')

                    # control_box.separator()

                    if not context.scene.kitops.thumbnail:
                        column = column_1.column(align=True)
                        column.enabled = authoring_enabled and bool(context.active_object) and not context.active_object.kitops.temp
                        column.prop(scene.kitops, 'animated')
                        column.prop(scene.kitops, 'auto_parent')

                        # control_box.separator()

                    if not context.scene.kitops.thumbnail or context.scene.kitops.factory:
                        row = control_box.row(align=True)
                        row.active = authoring_enabled
                        row.scale_y = 1.5
                        row.operator('mesh.ko_save_insert' if authoring_enabled else 'mesh.ko_purchase')



                row = layout.row()
                row.scale_y = 1.5
                row.operator('mesh.ko_remove_wire_inserts')

                layout.separator()

                # row = layout.row()
                # row.alignment = 'RIGHT'
                # row.scale_x = 1.5
                # row.scale_y = 1.5
                # op = row.operator('mesh.ko_documentation', text='', icon_value=previews.get(addon.icons['question-sign']).icon_id)
                # op.authoring = True


            
                if context.active_object and context.active_object.kitops.is_hardpoint:
                    col = control_box.column()
                    col.label(text="Hardpoint tags")
                    col.prop(context.active_object.kitops, 'hardpoint_tags', text='')


            if context.scene.kitops.factory:
                row.active = authoring_enabled
                row.operator('mesh.ko_close_factory_scene' if authoring_enabled else 'mesh.ko_purchase')

            elif context.scene.kitops.thumbnail:
                row.active = authoring_enabled
                if authoring_enabled:
                    row.operator('mesh.ko_close_thumbnail_scene', text='Close Thumbnail Scene', icon='VIEW_CAMERA')
                else:
                    row.operator('mesh.ko_purchase')


            if context.scene.kitops.factory or context.scene.kitops.thumbnail:


                control_box = layout.box()
                if context.scene.camera:
                    row = control_box.row(align=True)
                    row.scale_y = 1.5
                    row.operator('mesh.ko_camera_to_insert', text="Move Camera to INSERT")
                # row = layout.row()
                # row.alignment = 'CENTER'
                # row.active = authoring_enabled and not (context.scene.kitops.factory and not context.scene.kitops.last_edit)
                # row.scale_y = 1.5
                # column.separator()
                col = control_box.column(align=True)
                row = col.row(align=True)
                row.prop_enum(context.scene.kitops, 'render_mode', 'CYCLES')
                row.prop_enum(context.scene.kitops, 'render_mode', 'EEVEE')
                row.prop_enum(context.scene.kitops, 'render_mode', 'OPENGL')

                col.separator()
                row = col.row()
                row.active = authoring_enabled and not (context.scene.kitops.factory and not context.scene.kitops.last_edit)
                row.scale_y = 1.5
                props = row.operator('mesh.ko_create_snapshot' if authoring_enabled else 'mesh.ko_purchase', text='Render Thumbnail')
                props.insert_type = option.save_insert_type

        






class KO_PT_Hardpoints(Panel):
    bl_space_type = 'VIEW_3D'
    bl_idname = "KITOPS_PT_Panel_HPs"
    bl_label = 'Hardpoints'
    bl_region_type = 'UI'
    bl_category = '♥♥♥'
    bl_parent_id = 'KITOPS_PT_Panel_Main'
    @classmethod
    def poll(cls, context):
        global authoring_enabled
        return not context.scene.kitops.thumbnail and authoring_enabled and not _is_standard_mode(context)

    def draw(self, context):
        layout = self.layout
        col = layout.column()

        op = col.operator('mesh.ko_add_hardpoint', text="Add Hardpoint")
        op.material = False
        op.rotation_amount = 0

class KO_PT_HardpointTags(Panel):
    bl_space_type = 'VIEW_3D'
    bl_label = 'Hardpoint Tags'
    bl_region_type = 'UI'
    bl_category = '♥♥♥'
    bl_parent_id = 'KITOPS_PT_Panel_HPs'

    # def draw_header_preset(self, context):
    #     col = self.layout.column()
    #     col.operator("mesh.ko_preview_hardpoint_tags", text="", depress=context.scene.kitops.preview_hardpoints, icon='HIDE_OFF' if not context.scene.kitops.preview_hardpoints else 'HIDE_ON', emboss=False)

    @classmethod
    def poll(cls, context):
        global authoring_enabled
        return not context.scene.kitops.thumbnail and authoring_enabled

    def draw(self, context):
        layout = self.layout
        col = layout.column()

        col.operator("mesh.ko_preview_hardpoint_tags", text="Preview Tags", depress=context.scene.kitops.preview_hardpoints,  )

        hardpoint_objs = [o for o in context.selected_objects if o.kitops.is_hardpoint]

        if hardpoint_objs:
            box = col.box()
            col_hp = box.column()
            col_hp.label(text='Selected Hardpoints: ')


            for hardpoint_index in range(0, len(hardpoint_objs)):
                hardpoint_obj = hardpoint_objs[hardpoint_index]
                row_hp = col_hp.row(align=True).split(factor=0.2)
                row_hp.label(text="Name: ")
                row_hp.prop(hardpoint_obj, 'name', text="")
                row_hp = col_hp.row(align=True).split(factor=0.2)
                row_hp.label(text="Tags: ")
                row_hp_sub = row_hp.row(align=True)
                row_hp_sub.prop(hardpoint_obj.kitops, 'hardpoint_tags', text="")
                props = row_hp_sub.operator('mesh.ko_copy_hardpoint_tags', text='', icon="PASTEDOWN")
                props.tags = hardpoint_obj.kitops.hardpoint_tags
                col_hp.separator()

        


class KO_PT_sort_last(Panel):
    bl_label = 'Sort Last'
    bl_space_type = 'TOPBAR'
    bl_region_type = 'WINDOW'
    bl_options = {'DEFAULT_CLOSED'}


    def draw(self, context):
        preference = addon.preference()
        layout = self.layout

        row = layout.row(align=True)

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
            sub = row.row(align=True)
            sub.enabled = getattr(preference, F'sort_{type.lower()}')
            sub.prop(preference, F'sort_{type.lower()}_last', text='', icon=icon)

        if preference.sort_bevel:
            label_row(preference, 'sort_bevel_ignore_weight', layout.row(), label='Ignore Bevels using Weights')
            label_row(preference, 'sort_bevel_ignore_vgroup', layout.row(), label='Ignore Bevels with VGroups')
            label_row(preference, 'sort_bevel_ignore_only_verts', layout.row(), label='Ignore Bevels using Only Verts')

        layout.separator()

        label_row(preference, 'sort_depth', layout.row(), label='Sort Depth')
        label_row(preference, 'sort_ignore_char', layout.row(), label='Ignore Flag', scale_x_prop=0.35)
        label_row(preference, 'sort_stop_char', layout.row(), label='Stop Flag', scale_x_prop=0.35)



class KO_PT_GetKitOpsPro(Panel):
    bl_space_type = 'VIEW_3D'
    bl_label = 'Get KIT OPS PRO'
    bl_region_type = 'UI'
    bl_category = '♥♥♥'
    bl_parent_id = 'KITOPS_PT_Panel_Main'

    @classmethod
    def poll(cls, context):
        global authoring_enabled
        return not authoring_enabled

    def draw(self, context):
        global authoring_enabled

        layout = self.layout

        col = layout.column()

        col.label(text="- Enhanced INSERT placement")
        col.label(text="- Enhanced INSERT editing")
        col.label(text="- INSERT Snapping")
        col.label(text="- Save Favorite INSERTs")
        col.label(text="- Auto replace INSERTs")
        col.label(text="- INSERT FACTORY mode")


        col.operator('mesh.ko_store', text='Get KIT OPS PRO')


class KO_PT_ui():
    '''Facade class to for use with HOPS so that the panel will still be displayed'''

    def draw(self, context):
        if _is_standard_mode(context):
            KO_PT_KPACKS.draw_header_preset(self, context)
            KO_PT_KPACKS.draw(self, context)
            KO_PT_Modifiers.draw(self, context)
            KO_PT_Controls.draw(self, context)
            KO_PT_Management.draw(self, context)
        else:
            KO_PT_Authoring.draw(self, context)


def label_row(path, prop, row, label='', scale_x_prop=1.0):
    row.label(text=label)
    sub = row.row()
    sub.scale_x = scale_x_prop
    sub.prop(path, prop, text='')


classes = [
    KO_PT_Main,
    KO_PT_KPACKS,
    KO_PT_Modifiers,
    KO_PT_Controls,
    KO_PT_Management,
    KO_PT_Authoring,
    KO_PT_sort_last,
    KO_PT_Hardpoints,
    KO_PT_HardpointTags,
    KO_PT_GetKitOpsPro,
    KO_PT_AssetManagement]


def register():
    for cls in classes:
        register_class(cls)


def unregister():
    for cls in classes:
        unregister_class(cls)
