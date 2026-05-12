import re

from copy import deepcopy as copy

import bpy

from math import radians
from mathutils import *
from pathlib import Path
import uuid

from bpy.types import Operator
from bpy.props import *
from bpy.utils import register_class, unregister_class
from bpy_extras.io_utils import ExportHelper, ImportHelper

from .. utility import addon, backup, bbox, dpi, insert, ray, remove, update, view3d, collections, smart, persistence, handler, id, hardpoints, regex

from .. t3dn_bip import ops

import os
import subprocess
import sys

authoring_enabled = True
try: from .. utility import matrixmath
except ImportError: authoring_enabled = False


class KO_OT_purchase(Operator):
    bl_idname = 'mesh.ko_purchase'
    bl_label = 'KIT OPS PRO'
    bl_description = 'Buy KIT OPS PRO'

    def execute(self, context):
        # Do nothing, this option should always be disabled in the ui
        return {'FINISHED'}


class KO_OT_store(Operator):
    bl_idname = 'mesh.ko_store'
    bl_label = 'Store'
    bl_description = 'Visit the KIT OPS Store'

    def execute(self, context):
        bpy.ops.wm.url_open('INVOKE_DEFAULT', url='http://cw1.me/kpacks')

        return {'FINISHED'}


class KO_OT_documentation(Operator):
    bl_idname = 'mesh.ko_documentation'
    bl_label = 'Documentation'
    bl_description = 'View the KIT OPS documentation'

    authoring: BoolProperty(default=False)

    def execute(self, context):
        bpy.ops.wm.url_open('INVOKE_DEFAULT', url='http://cw1.me/kops2docs')

        return {'FINISHED'}


class KO_OT_add_kpack_path(Operator):
    bl_idname = 'mesh.ko_add_kpack_path'
    bl_label = 'Add KIT OPS KPACK path'
    bl_description = 'Add a path to a KIT OPS KPACK'

    def execute(self, context):
        preference = addon.preference()

        folder = preference.folders.add()
        folder['location'] = 'Choose Path'
        folder.set_ids.add().name = 'ALL'

        return {'FINISHED'}


class KO_OT_remove_kpack_path(Operator):
    bl_idname = 'mesh.ko_remove_kpack_path'
    bl_label = 'Remove path'
    bl_description = 'Remove path'

    index: IntProperty()

    def execute(self, context):
        preference = addon.preference()

        preference.folders.remove(self.index)

        update.kpack(None, context)

        return {'FINISHED'}


class KO_OT_refresh_kpacks(Operator):
    bl_idname = 'mesh.ko_refresh_kpacks'
    bl_label = 'Refresh KIT OPS KPACKS'
    bl_description = 'Refresh KIT OPS KPACKS'

    record_previous : BoolProperty(default=False) # record the previous selection to keep the KPACK in the UI.

    def execute(self, context):
        if self.record_previous:
            option = addon.option()
            previous_set = str(option.kpack_set)
            previous_kpack = str(option.kpacks)
            category = option.kpack.categories[option.kpack.active_index]
            previous_thumbnail = str(category.thumbnail)

        update.kpack(None, context)

        if self.record_previous:
            option = addon.option()
            try:
                option.kpack_set = previous_set
                option.kpacks = previous_kpack
            except TypeError:
                pass
            if option.kpacks == previous_kpack:
                try:
                    category = option.kpack.categories[option.kpack.active_index]
                    category.thumbnail = previous_thumbnail
                except TypeError:
                    pass

        return {'FINISHED'}


class KO_OT_next_kpack(Operator):
    bl_idname = 'mesh.ko_next_kpack'
    bl_label = 'Next KPACK'
    bl_description = 'Change to the next INSERT\n  Ctrl - Change KPACK'
    bl_options = {'INTERNAL'}


    def invoke(self, context, event):
        option = addon.option()

        if event.ctrl:
            index = option.kpack.active_index + 1 if option.kpack.active_index + 1 < len(option.kpack.categories) else 0

            option.kpacks = option.kpack.categories[index].name

        else:
            category = option.kpack.categories[option.kpack.active_index]
            index = category.active_index + 1 if category.active_index + 1 < len(category.blends) else 0

            category.active_index = index
            category.thumbnail = category.blends[category.active_index].name

        return {'FINISHED'}


class KO_OT_previous_kpack(Operator):
    bl_idname = 'mesh.ko_previous_kpack'
    bl_label = 'Previous KPACK'
    bl_description = 'Change to the previous INSERT\n  Ctrl - Change KPACK'
    bl_options = {'INTERNAL'}


    def invoke(self, context, event):
        option = addon.option()

        if event.ctrl:
            index = option.kpack.active_index - 1 if option.kpack.active_index - 1 > -len(option.kpack.categories) else 0

            option.kpacks = option.kpack.categories[index].name

        else:
            category = option.kpack.categories[option.kpack.active_index]
            index = category.active_index - 1 if category.active_index - 1 > -len(category.blends) else 0

            category.active_index = index
            category.thumbnail = category.blends[category.active_index].name

        return {'FINISHED'}

def _add_material(obj, material):
        if len(obj.data.materials) and obj.active_material_index < len(obj.data.materials):
            obj.data.materials[obj.active_material_index] = material
        else:
            obj.data.materials.append(material)

class add_insert():
    bl_options = {'REGISTER', 'UNDO'}

    location: StringProperty(
        name = 'Blend path',
        description = 'Path to blend file')

    material: BoolProperty(name='Material')
    material_link: BoolProperty(name='Link Materials')

    mouse = Vector()
    main = None
    duplicate = None

    data_to = None
    boolean_target = None

    inserts = list()

    init_active = None
    init_selected = list()
    cutter_objects = list()

    insert_scale = ('LARGE', 'MEDIUM', 'SMALL')

    import_material = None

    original_scale : FloatVectorProperty(default=[1,1,1])

    rotation_amount : FloatProperty(default=0)

    scene_hardpoints = []

    insert_collection_excluded = False

    @classmethod
    def poll(cls, context):
        return not context.space_data.region_quadviews


    def invoke(self, context, event):
        global authoring_enabled


        preference = addon.preference()

        preference.restrict_axis = 'NONE'

        insert.operator = self


        #select active object if not already.
        if context.active_object and context.active_object.mode == 'EDIT':
            context.active_object.select_set(True)

        # assign active object to internal variables.
        self.init_active = bpy.data.objects[context.active_object.name] if context.active_object and context.active_object.select_get() else None
        self.init_selected = [bpy.data.objects[obj.name] for obj in context.selected_objects]

        self.insert_collection_excluded = collections.init(context)

        if self.init_active:
            if self.init_active.kitops.insert and preference.place_on_insert:
                self.boolean_target = self.init_active
            elif self.init_active.kitops.insert and self.init_active.kitops.insert_target:
                self.boolean_target = self.init_active.kitops.insert_target
            elif preference.mode == 'REGULAR' and self.init_active.kitops.insert and self.init_active.kitops.reserved_target:
                self.boolean_target = self.init_active.kitops.reserved_target
            elif self.init_active.kitops.insert:
                self.boolean_target = None
            elif self.init_active.type == 'MESH':
                self.boolean_target = self.init_active
            else:
                self.boolean_target = None
        else:
            self.boolean_target = None

        for obj in context.selected_objects:
            obj.select_set(False)

        if self.init_active and self.init_active.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')

        if self.boolean_target:
            ray.make_duplicate(self)


        self.material_link = not event.ctrl

        if not self.main:
            insert.add(self, context)

        prev_name = ''
        if self.material and self.init_active and self.import_material:
            if hasattr(self.init_active, 'material_slots') and len(self.init_active.material_slots[:]) and self.init_active.material_slots[0].material:
                prev_name = self.init_active.material_slots[0].material.name

        
            _add_material(self.init_active, self.import_material)

            for obj in self.init_selected:
                if obj != self.init_active and obj.type == 'MESH':
                    _add_material(obj, self.import_material)


        if self.material:
            if not self.import_material:
                self.report({'WARNING'}, 'No materials found to import')

            elif not prev_name:
                self.report({'INFO'}, F'Imported material: {self.import_material.name}')

            else:
                self.report({'INFO'}, F'Material assigned: {self.import_material.name}')

            self.exit(context, clear=True)
            return {'FINISHED'}

        if self.main and self.main.kitops.animated:
            bpy.ops.screen.animation_play()

        # Record the original scale of the insert and apply a re-scale is needed.
        self.original_scale = self.main.scale.copy() if self.main else self.original_scale
        if not preference.auto_scale and self.main:
            option = addon.option()
            self.main.scale = self.main.scale * option.scale_amount


        scene_hardpoints = []

        if preference.snap_mode == 'HARDPOINT':
            # deal with hardpoint positioning.
            scene_hardpoints = [o for o in context.visible_objects if o.kitops.is_hardpoint and o.kitops.main_object !=  self.main]

            if preference.use_snap_mode_hardpoint_tag_match:

                insert_restrict_list = hardpoints.get_tags_from_str(preference.snap_mode_hardpoint_tag_match)
                scene_hardpoints = [hp for hp in scene_hardpoints if hardpoints.intersecting_tags(hardpoints.get_tags_from_str(hp.kitops.hardpoint_tags), insert_restrict_list)]

            if preference.snap_to_empty_hardpoints_only:
                scene_hardpoints = [hp for hp in scene_hardpoints if hp not in [o.kitops.hardpoint_object for o in context.visible_objects]]

        self.scene_hardpoints = scene_hardpoints

        self.is_hardpoint_mode = preference.snap_mode == 'HARDPOINT' and len(self.scene_hardpoints)
        self.is_duplicate_mode = hasattr(self, 'is_duplicate_mode') and self.is_duplicate_mode

        if (self.init_selected and self.boolean_target) or self.is_hardpoint_mode:
            self.mouse = Vector((event.mouse_x, event.mouse_y))
            self.mouse.x -= view3d.region().x - preference.insert_offset_x * dpi.factor()
            self.mouse.y -= view3d.region().y - preference.insert_offset_y * dpi.factor()

            insert.hide_handler(context, self)

            context.window_manager.modal_handler_add(self)

            return {'RUNNING_MODAL'}
        elif self.is_duplicate_mode:
            self.exit(context)
            bpy.ops.transform.translate('INVOKE_DEFAULT')
            return {'FINISHED'}
    
        else:
            if self.init_active and self.init_active.kitops.insert:
                self.report({'WARNING'}, 'An INSERT can not be added to an existing INSERT that has no target object.')
            if self.main:
                self.main.location = bpy.context.scene.cursor.location
            self.exit(context)
            if preference.remove_props_when_no_target:
                bpy.ops.mesh.ko_remove_insert_properties('INVOKE_DEFAULT', remove = False, uuid = '')
            return {'FINISHED'}


    def modal(self, context, event):
        global authoring_enabled

        preference = addon.preference()

        restrict_text = "[X/Y/Z] Restrict Axis    "
        if preference.restrict_axis != 'NONE':
            restrict_text = "Restricting movement to " + preference.restrict_axis + " axis    "

        snap_help_text = "Add KIT OPS INSERT:  " + restrict_text + "Mouse Scroll - resize INSERT    Alt + Mouse Scroll - rotate INSERT    [SHIFT + Click] Add multiple INSERTS    |    [F] Snap to FACE    [E] Snap to EDGE ([C] Toggle Snap to Edge Center)    [V] Snap to VERTEX    [N] Cancel SNAP MODE"

        if authoring_enabled:
            snap_help_text = snap_help_text + "    |    [P] Toggle Place on Selected Insert    [I] Flip Placement"


        context.workspace.status_text_set(text=snap_help_text)
        
        try:
            self.main, self.main.location
        except ReferenceError as e:
            return {'CANCELLED'}

        if not insert.operator:
            self.exit(context)
            return {'FINISHED'}

        if event.type in {'F', 'E', 'V', 'N', 'P', 'I'} and event.value == 'PRESS':
            if event.type == 'F':
                preference.snap_mode = 'FACE'
            if event.type == 'E':
                preference.snap_mode = 'EDGE'
            if event.type == 'V':
                preference.snap_mode = 'VERTEX'
            if event.type == 'H':
                preference.snap_mode = 'HARDPOINT'
            if event.type == 'N':
                preference.snap_mode = 'NONE'

            if authoring_enabled:    
                if event.type == 'P':
                    preference.place_on_insert = not preference.place_on_insert
                if event.type == 'I':
                    preference.flip_placement = not preference.flip_placement

            ray.refresh_duplicate(self)
            
            return {'RUNNING_MODAL'}
        
        # restrict movement by axis if needed
        if event.type in {'X', 'Y', 'Z'} and event.value == 'PRESS':
            if preference.restrict_axis == event.type:
                preference.restrict_axis = 'NONE'
            else:
                preference.restrict_axis = event.type
            return {'RUNNING_MODAL'}

    
        if preference.snap_mode == 'EDGE' and event.type == 'C' and event.value == 'PRESS':
            preference.snap_mode_edge = 'NEAREST' if preference.snap_mode_edge == 'CENTER' else 'CENTER'
            return {'RUNNING_MODAL'}

        if event.type == 'MOUSEMOVE':
            temp_scale = self.main.scale.copy()
            self.mouse = Vector((event.mouse_x, event.mouse_y))
            self.mouse.x -= view3d.region().x - preference.insert_offset_x * dpi.factor()
            self.mouse.y -= view3d.region().y - preference.insert_offset_y * dpi.factor()
            update.location(context, self)
            self.main.scale = temp_scale
            self.main.rotation_euler.rotate_axis("Z", radians(self.rotation_amount))

        insert.hide_handler(context, self)

        if event.type in {'ESC', 'RIGHTMOUSE'} and event.value == 'PRESS':

            self.exit(context, clear=True)
            return {'CANCELLED'}

        elif event.type in {'LEFTMOUSE', 'RET', 'NUMPAD_ENTER'} and event.value == 'PRESS':
            if ray.location:
                option = addon.option()
                option.scale_amount = (self.main.scale.magnitude / Vector(self.original_scale).magnitude)
                if event.shift and self.location:
                    self.exit(context)
                    bpy.ops.mesh.ko_add_insert('INVOKE_DEFAULT', 
                        location=self.location,
                        rotation_amount=self.rotation_amount)
                else:
                    self.exit(context)
                return{'FINISHED'}
            else:

                self.exit(context, clear=True)
                return {'CANCELLED'}

        elif event.type == 'WHEELDOWNMOUSE':      
            if event.alt:

                insert_hardpoints = None
                # if preference.use_insert_hardpoints:
                #     insert_hardpoints = hardpoints.get_hardpoints(self.main)

                #     if preference.use_insert_hardpoint_tag_match:
                #         insert_restrict_list = hardpoints.get_tags_from_str(preference.insert_hardpoint_tag_match)
                #         insert_hardpoints = [hp for hp in insert_hardpoints if hardpoints.intersecting_tags(hardpoints.get_tags_from_str(hp.kitops.hardpoint_tags), insert_restrict_list)]


                if not insert_hardpoints:
                    rotation_amount = 15 if not event.shift else 1
                    self.main.rotation_euler.rotate_axis("Z", radians(rotation_amount))
                    self.rotation_amount+=rotation_amount
                return {'RUNNING_MODAL'}

            if preference.auto_scale:
                if self.insert_scale.index(preference.insert_scale) + 1 < len(self.insert_scale):
                    preference.insert_scale = self.insert_scale[self.insert_scale.index(preference.insert_scale) + 1]
            else:
                step = 0.1 if not event.shift else 0.01
                self.main.scale -= self.main.scale * step
            return {'RUNNING_MODAL'}

        elif event.type == 'WHEELUPMOUSE':
            if event.alt:
                insert_hardpoints = None
                # if preference.use_insert_hardpoints:
                #     insert_hardpoints = hardpoints.get_hardpoints(self.main)

                #     if preference.use_insert_hardpoint_tag_match:
                #         insert_restrict_list = hardpoints.get_tags_from_str(preference.insert_hardpoint_tag_match)
                #         insert_hardpoints = [hp for hp in insert_hardpoints if hardpoints.intersecting_tags(hardpoints.get_tags_from_str(hp.kitops.hardpoint_tags), insert_restrict_list)]

                if not insert_hardpoints:
                    rotation_amount = 15 if not event.shift else 1
                    self.main.rotation_euler.rotate_axis("Z", radians(-rotation_amount))
                    self.rotation_amount-=rotation_amount
                return {'RUNNING_MODAL'}


            if preference.auto_scale:
                if self.insert_scale.index(preference.insert_scale) - 1 >= 0:
                    preference.insert_scale = self.insert_scale[self.insert_scale.index(preference.insert_scale) - 1]
            else:
                step = 0.1 if not event.shift else 0.01
                self.main.scale += self.main.scale * step
            return {'RUNNING_MODAL'}

        elif event.type in {'G', 'R', 'S'}:
            insert.operator = None

        return {'PASS_THROUGH'}

    def check_target_scale(self):
        ins_obj = self.main
        if ins_obj.kitops.insert_target:
            target_scale = ins_obj.kitops.insert_target.scale
            if len(target_scale) == 3 and target_scale != Vector((1,1,1)):
                self.report({'WARNING'}, "Target object is not at correct scale. (" \
                                    + "{:.2f}".format(target_scale[0]) + ", " \
                                        + "{:.2f}".format(target_scale[1]) + ", " \
                                            + "{:.2f}".format(target_scale[2]) + ")")



    def exit(self, context, clear=False):

        context.workspace.status_text_set(text=None)

        option = addon.option()

        if self.main and self.main.kitops.animated:
            bpy.ops.screen.animation_cancel(restore_frame=True)

        if not option.show_cutter_objects:
            for obj in self.cutter_objects:
                obj.hide_viewport = True

        for obj in self.inserts:
            # assert pin to last is set for the last Auto Smooth modifier.
            last_mod = obj.modifiers[-1] if obj.modifiers else None
            if last_mod and "Auto Smooth" in last_mod.name and hasattr(last_mod, 'use_pin_to_last'):
                last_mod.use_pin_to_last = True




        if clear:
            for obj in self.inserts:
                try:
                    insert.delete_hierarchy(obj, target_obj=self.boolean_target)
                    bpy.data.objects.remove(obj)
                except ReferenceError:
                    pass
                
            for obj in self.init_selected:
                obj.select_set(True)

            if self.init_active:
                context.view_layer.objects.active = self.init_active
                
        else:
            for obj in self.inserts:
                if obj.select_get() and obj.kitops.selection_ignore:
                    obj.select_set(False)
                else:
                    obj.select_set(True)

                if self.boolean_target and obj.parent is None:
                    # Add parent if we have a boolean target.
                    insert.parent_objects(obj, self.boolean_target)



            # set active object to main INSERT.
            if self.main:
                context.view_layer.objects.active = self.main

                self.main.kitops.rotation_amount = self.rotation_amount

                self.check_target_scale()

        #TODO: collection helper: collection.remove
        if 'INSERTS' in bpy.data.collections:
            for child in bpy.data.collections['INSERTS'].children:
                if not child.objects and not child.children:
                    bpy.data.collections.remove(child)

        # if we were in hardpoint mode, add a reference to the hardpoint on the object.
        if hasattr(self, 'is_hardpoint_mode') and self.is_hardpoint_mode and (update.last_hardpoint_obj_name and update.last_hardpoint_obj_name in bpy.data.objects):
            try:
                hardpoint_obj = bpy.data.objects[update.last_hardpoint_obj_name]
                self.main.kitops.hardpoint_object = hardpoint_obj
                update.last_hardpoint_obj_name = None
            except ReferenceError:
                pass

        ray.success = bool()
        ray.location = Vector()
        ray.normal = Vector()
        ray.face_index = int()
        ray.free(self)

        insert.operator = None

        if 'INSERTS' in bpy.data.collections and not bpy.data.collections['INSERTS'].objects and not bpy.data.collections['INSERTS'].children:
            bpy.data.collections.remove(bpy.data.collections['INSERTS'])

        for mesh in bpy.data.meshes:
            if mesh.users == 0:
                bpy.data.meshes.remove(mesh)

        # remove any created duplicates.
        for obj in [ob for ob in bpy.data.objects if ob.kitops.duplicate]:
            remove.object(obj, data=True, do_unlink=False)

        # remove INSERT collection if empty.
        for collection in bpy.data.collections:
            if collection.name == "INSERTS" and not collection.all_objects:
                bpy.data.collections.remove(collection)

        if self.insert_collection_excluded:
            collections.exclude_insert_collection(context)


def get_description():
    if authoring_enabled:
        return  ('Add INSERT to the scene \n'
                            ' \n'
                            ' Mouse Scroll - scale INSERT\n'
                            ' Alt + Mouse Scroll - rotate INSERT\n'
                            ' SHIFT + click - add the same INSERT multiple times\n'
                            ' \n'
                            ' V - Snap to Vertex\n'
                            ' E - Snap to Edge\n'
                            '  [C - Toggle Snap to Edge Center]\n'
                            ' F - Snap to Face\n'
                            ' N - Cancel Snap Mode\n'
                            ' \n'
                            ' P - Toggle Place on Selected INSERT\n'
                            ' I - Flip Placement')
    else:
        return  ('Add INSERT to the scene \n'
                    ' Alt + mouse scroll - rotate INSERT\n'
                    ' Snap to Face/Edge/Vertex: Purchase KIT OPS Pro')


def _toggle_boolean(obj, is_enabled):
    """Toggle whether the object's boolean operator is on or off"""
    inserts = insert.collect([obj])
    for obj in inserts:
        if obj.kitops.reserved_target:
            for mod in obj.kitops.reserved_target.modifiers:
                if mod.type == "BOOLEAN" and mod.object == obj:
                    mod.show_render = is_enabled
                    mod.show_viewport = is_enabled
            bpy.context.view_layer.update()


class move_insert(add_insert):
    bl_options = {'REGISTER', 'UNDO'}

    original_matrix_world = None

    original_scale_option = None

    old_active = None

    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object.kitops.insert and context.active_object.kitops.main_object

    def invoke(self, context, event):
        self.main = context.active_object.kitops.main_object        
        
        self.original_matrix_world = self.main.matrix_world.copy()
        option = addon.option()
        self.original_scale_option = option.scale_amount
        option.scale_amount = 1
        self.rotation_amount = self.main.kitops.rotation_amount
        self.old_active = context.view_layer.objects.active
        if self.main.kitops.reserved_target:
            context.view_layer.objects.active = self.main.kitops.reserved_target
            context.view_layer.objects.active.select_set(True)

        _toggle_boolean(self.main, False)
        result = super().invoke(context, event)
        _toggle_boolean(self.main, True)
        
        return result

    def exit(self, context, clear=False):
        context.workspace.status_text_set(text=None)
        option = addon.option()

        if self.main.kitops.animated:
            bpy.ops.screen.animation_cancel(restore_frame=True)

        if not option.show_cutter_objects:
            for obj in self.cutter_objects:
                obj.hide_viewport = True

        if clear:
            self.main.matrix_world = self.original_matrix_world

            option = addon.option()
            context.view_layer.objects.active.select_set(False)
            context.view_layer.objects.active = self.old_active

        else:
            self.main.select_set(True)
            context.view_layer.objects.active = self.main
            inserts = insert.collect([self.main])
            for ins in inserts:
                ins.select_set(True)
            self.main.kitops.rotation_amount = self.rotation_amount
            self.check_target_scale()


        option.scale_amount = self.original_scale_option

        ray.success = bool()
        ray.location = Vector()
        ray.normal = Vector()
        ray.face_index = int()
        ray.free(self)

        insert.operator = None

        context.view_layer.update()


class KO_OT_auto_create_insert(Operator):
    
    bl_idname = 'mesh.ko_auto_create_insert'
    bl_label = 'Create INSERT'
    bl_description = "Automatically create from the selected object"
    bl_options = {'UNDO', 'INTERNAL'}

    set_object_origin_to_bottom : BoolProperty(default=False)

    material : BoolProperty(default=False)

    directory : StringProperty(
        name= "Materials Output Folder",
        subtype= 'DIR_PATH',
        default= ''
    )

    create_type : EnumProperty(
        name = 'Create Type',
        items = persistence.create_type_items,
        default = 'INSERT'
    )

    @classmethod
    def poll(cls, context):
        return context.active_object # todo consider context.selected_objects

    def execute(self, context):
        insert.correct_ids()
        
        obj = context.active_object

        # remember old location and rotation as we will reset these.
        if not self.material:
            if self.set_object_origin_to_bottom:
                original_translation = obj.matrix_world.copy().translation
                insert.origin_to_bottom(obj)
                context.view_layer.update()
            old_loc = obj.location.copy()
            obj.location = Vector((0,0,0))
            old_euler = obj.rotation_euler.copy()
            obj.rotation_euler = [0,0,0]
            
            # because of sys.exit() protection, we have to set the objects into a temporary state.
            old_saving = handler.is_saving
            handler.is_saving = True
            id_present = obj.kitops.id != ''
            if id_present:
                old_id = obj.kitops.id
            old_main = obj.kitops.main

            old_main_map = {}
            for o in bpy.data.objects:
                old_main_map[o.name] = o.kitops.main
            old_bool_duplicate_map = {}
            for o in bpy.data.objects:
                old_bool_duplicate_map[o.name] = o.kitops.bool_duplicate
                o.kitops.bool_duplicate = False

        smart.smart_update = False
        try:


            # open a new factory mode, position the camera, save the insert, and render the thumbnail.
            if not self.material:
                obj.kitops.id = id.uuid()
                obj.kitops.main = True
                for other_obj in [o for o in bpy.data.objects if o != obj]:
                    other_obj.kitops.main = False

            if not bpy.data.use_autopack:
                bpy.ops.file.autopack_toggle()

            bpy.ops.object.mode_set(mode='OBJECT')

            obj.kitops.bool_duplicate = False
            
            persistence.new_factory_scene(context, self.create_type, link_selected=True, link_children=True, duplicate=not self.material, apply_all_materials=not self.material)
            

            if self.create_type not in {'MATERIAL', 'SHADER_NODES'}:
                bpy.ops.view3d.camera_to_view_selected()


            if self.material and self.create_type == 'MATERIAL':
                insert_name = obj.active_material.name
            else:
                insert_name = obj.name

            insert_path = persistence.insert_path(insert_name, context, self.directory)
            thumb_path = persistence.insert_thumb_path(insert_name, self.create_type, context, self.directory)


            persistence.save_insert(path=insert_path)
            persistence.create_snapshot(self, context, thumb_path)
            bpy.ops.mesh.ko_refresh_kpacks(record_previous=True)

            persistence.close_factory_scene(self, context, log=False)

            pass
        finally:
            if not self.material:
                obj.location = old_loc
                if self.set_object_origin_to_bottom:
                    context.view_layer.update()
                    insert.set_origin(obj, original_translation)
                obj.rotation_euler = old_euler
                handler.is_saving = old_saving
                if id_present:
                    obj.kitops.id = old_id
                if old_main:
                    obj.kitops.main = True
                else:
                    # temporarily set the active to false so we can set the main parameter to false. 
                    context.view_layer.objects.active =  None
                    obj.kitops.main = old_main
                    if obj.name in context.view_layer.objects:
                        context.view_layer.objects.active = obj

                for o in bpy.data.objects:
                    if o.name in old_main_map:
                        o.kitops.main = old_main_map[o.name]
                    if o.name in old_bool_duplicate_map:
                        o.kitops.bool_duplicate = old_bool_duplicate_map[o.name]

            smart.smart_update = True

        return {'FINISHED'}



class KO_OT_auto_create_insert_confirm(Operator):
    """Automatically create from the selected object"""
    bl_idname = 'mesh.ko_auto_create_insert_confirm'
    bl_label = "Overwrite existing file?"

    bl_options = {'INTERNAL','UNDO'}

    create_type : EnumProperty(
        name = 'Create Type',
        items = persistence.create_type_items,
        default = 'INSERT'
    )

    set_object_origin_to_bottom : BoolProperty(default=False)

    material : BoolProperty(default=False)

    directory : StringProperty()


    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

    @classmethod
    def poll(self, context):
        return context.active_object

    def execute(self, context):
        bpy.ops.mesh.ko_auto_create_insert('INVOKE_DEFAULT', set_object_origin_to_bottom=self.set_object_origin_to_bottom, material=self.material, directory=self.directory, create_type=self.create_type)
        return {'FINISHED'}





#TODO: Collections
class KO_OT_add_insert(Operator, add_insert):
    bl_idname = 'mesh.ko_add_insert'
    bl_label = 'Add INSERT'
    bl_description = get_description()

class KO_OT_add_hardpoint(Operator, add_insert):
    bl_idname = 'mesh.ko_add_hardpoint'
    bl_label = 'Add Hardpoint'
    bl_description = "Add a Hardpoint"

    location: StringProperty(
        name = 'Blend path',
        description = 'Path to blend file',
        default=addon.path.hardpoint_location(),
        options={"HIDDEN"})

    def invoke(self, context, event):
        global authoring_enabled

        preference = addon.preference()

        preference.snap_mode = 'NONE'

        return super().invoke(context, event)

class KO_OT_move_insert(Operator, move_insert):
    bl_idname = 'mesh.ko_move_insert'
    bl_label = 'Relocate INSERT'
    bl_description = "Move INSERT in the scene using KIT OPS controls"

    is_duplicate_mode = True


class KO_OT_add_insert_material(Operator, add_insert):
    bl_idname = 'mesh.ko_add_insert_material'
    bl_label = 'Add Material'
    bl_description = ('Add INSERT\'s materials to target \n'
                      '  Ctrl - Add unique material instance')

class KO_OT_add_insert_gn(Operator):
    bl_idname = 'mesh.ko_add_insert_gn'
    bl_label = 'Add Geo Nodes'
    bl_description = 'Add Geometry Nodes INSERT'
    bl_options = {'INTERNAL', 'UNDO'}

    location: StringProperty(
        name = 'Blend path',
        description = 'Path to blend file')

    def execute(self, context):
        # List of node groups in the external blend file
        node_groups_to_load = []

        # Open the .blend file and get all node groups
        duplicates = []
        with bpy.data.libraries.load(self.location, link=False) as (blend, imported):
            for name in blend.node_groups:
                if name in bpy.data.node_groups:
                    # If the node group already exists, skip it
                    duplicates.append(name)
                    continue
                node_groups_to_load.append(name)
            imported.node_groups = node_groups_to_load

        to_remove = []
        for node_group in node_groups_to_load:
            if node_group.type != 'GEOMETRY':
                to_remove.append(node_group)
            else:
                node_group.use_fake_user = True

        for node_group in to_remove:
            node_groups_to_load.remove(node_group)
            bpy.data.node_groups.remove(bpy.data.node_groups[node_group.name], do_unlink=True)

        # display information about the imported node groups
        if node_groups_to_load:
            names = [ng.name for ng in node_groups_to_load]
            self.report({'INFO'}, f'Imported Geometry Nodes: {", ".join(names)}')
        elif duplicates:
            self.report({'WARNING'}, f'Skipped existing Geometry Nodes: {", ".join(duplicates)}')
        else:
            self.report({'WARNING'}, 'No Geometry Nodes found in the blend file')

        
        # purge all
        bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)  

        return {'FINISHED'}

class KO_OT_add_insert_shader_nodes(Operator):
    bl_idname = 'mesh.ko_add_insert_shader_nodes'
    bl_label = 'Add Shader Nodes'
    bl_description = 'Add Shader Nodes INSERT'
    bl_options = {'INTERNAL', 'UNDO'}

    location: StringProperty(
        name='Blend path',
        description='Path to blend file'
    )

    def execute(self, context):
        shader_groups_to_load = []

        duplicates = []
        with bpy.data.libraries.load(self.location, link=False) as (blend, imported):
            # Filter only shader node groups
            for name in blend.node_groups:
                if name in bpy.data.node_groups:
                    # If the node group already exists, skip it
                    duplicates.append(name)
                    continue
                # Shader groups usually have "ShaderNodeTree" types, but we can't access type info until they're imported
                shader_groups_to_load.append(name)
            imported.node_groups = shader_groups_to_load

        to_remove = []
        for node_group in shader_groups_to_load:
            if node_group.type != 'SHADER':
                to_remove.append(node_group)
            else:
                node_group.use_fake_user = True

        for node_group in to_remove:
            shader_groups_to_load.remove(node_group)
            bpy.data.node_groups.remove(bpy.data.node_groups[node_group.name], do_unlink=True)


        # Report result
        if shader_groups_to_load:
            names = [ng.name for ng in shader_groups_to_load]
            self.report({'INFO'}, f'Imported Shader Nodes: {", ".join(names)}')
        elif duplicates:
            self.report({'WARNING'}, f'Skipped existing Shader Nodes: {", ".join(duplicates)}')
        else:
            self.report({'WARNING'}, 'No Shader Node Groups found in the blend file')

        # Purge all
        bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)  

        return {'FINISHED'}

class KO_OT_select_inserts(Operator):
    bl_idname = 'mesh.ko_select_inserts'
    bl_label = 'Select All INSERTS'
    bl_description = 'Select all INSERTS'
    bl_options = {'REGISTER', 'UNDO'}

    solids: BoolProperty(
        name = 'Solid inserts',
        description = 'Select solid INSERTS',
        default = True)

    cutters: BoolProperty(
        name = 'Cutter inserts',
        description = 'Select cutter INSERTS',
        default = True)

    wires: BoolProperty(
        name = 'Wire inserts',
        description = 'Select wire INSERTS',
        default = True)


    def draw(self, context):
        layout = self.layout

        preference = addon.preference()
        option = addon.option()

        column = layout.column()
        column.prop(self, 'solids')
        column.prop(self, 'cutters')
        column.prop(self, 'wires')


    def check(self, context):
        return True


    def execute(self, context):
        solids = insert.collect(solids=True, all=True)
        cutters = insert.collect(cutters=True, all=True)
        wires = insert.collect(wires=True, all=True)

        if self.solids:
            for obj in solids:
                try:
                    obj.select_set(True)
                except RuntimeError:
                    pass

        if self.cutters:
            for obj in cutters:
                try:
                    obj.select_set(True)
                except RuntimeError:
                    pass

        if self.wires:
            for obj in wires:
                try:
                    obj.select_set(True)
                except RuntimeError:
                    pass

        return {'FINISHED'}


class remove_insert_properties():
    bl_options = {'UNDO'}

    remove: BoolProperty()
    uuid: StringProperty()


    def execute(self, context):
        objects = context.selected_objects if not self.uuid else [obj for obj in bpy.data.objects if obj.kitops.id == self.uuid]
        for obj in objects:
            obj.kitops.insert = False
        if self.remove:
            old_active = context.view_layer.objects.active
            context.view_layer.objects.active = objects[0]
            old_selected = [o for o in context.selected_objects]
            for o in old_selected:
                o.select_set(False)
            for o in objects:
                o.select_set(True)
            bpy.ops.object.delete(confirm=False)
            for o in old_selected:
                try:
                    o.select_set(True)
                except ReferenceError:
                    pass
            try:
                context.view_layer.objects.active = old_active
            except ReferenceError:
                pass

        return {'FINISHED'}


class KO_OT_remove_insert_properties(Operator, remove_insert_properties):
    bl_idname = 'mesh.ko_remove_insert_properties'
    bl_label = 'Remove KIT OPS props'
    bl_description = 'Remove properties from the selected OBJECTS'


class KO_OT_remove_insert_properties_x(Operator, remove_insert_properties):
    bl_idname = 'mesh.ko_remove_insert_properties_x'
    bl_label = 'Remove INSERT'
    bl_description = 'Deletes selected INSERTS'


class KO_OT_export_settings(Operator, ExportHelper):
    bl_idname = 'mesh.ko_export_settings'
    bl_label = 'Export Settings'
    bl_options = {'REGISTER', 'INTERNAL'}
    bl_description = '.\n'.join((
        'Save KIT OPS preferences to a file',
        'Made possible by PowerBackup'))

    filter_glob: bpy.props.StringProperty(default='*.json', options={'HIDDEN'})
    filename_ext: bpy.props.StringProperty(default='.json', options={'HIDDEN'})


    def invoke(self, context, event):
        self.filepath = backup.filepath()
        return super().invoke(context, event)


    def execute(self, context):
        result = backup.backup(self.filepath)
        self.report(result[0], result[1])
        return result[2]


class KO_OT_import_settings(Operator, ImportHelper):
    bl_idname = 'mesh.ko_import_settings'
    bl_label = 'Import Settings'
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}
    bl_description = '.\n'.join((
        'Load KIT OPS preferences from a file',
        'Made possible by PowerBackup'))

    filter_glob: bpy.props.StringProperty(default='*.json', options={'HIDDEN'})
    filename_ext: bpy.props.StringProperty(default='.json', options={'HIDDEN'})


    def invoke(self, context, event):
        self.filepath = backup.filepath()
        return super().invoke(context, event)


    def execute(self, context):
        result = backup.restore(self.filepath)
        self.report(result[0], result[1])
        return result[2]


class KO_OT_convert_to_mesh(Operator):
    bl_idname = 'mesh.ko_convert_to_mesh'
    bl_label = 'Convert to mesh'
    bl_description = 'Apply modifiers and remove kitops properties of selected objects'
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.selected_objects


    def execute(self, context):
        inserts = [obj for obj in bpy.data.objects if obj.kitops.insert]

        # set applied flag.
        for obj in inserts:
            obj.kitops.applied = True

        old_active = context.view_layer.objects.active

        for obj in context.selected_objects:
            context.view_layer.objects.active = obj
            obj.kitops.insert = False
            obj.kitops.main = False
            for mod in obj.modifiers:
                if mod.show_viewport:
                    if mod.type == 'BOOLEAN' and mod.object:
                        mod.object.kitops.insert_target = None

                    bpy.ops.object.modifier_apply(modifier=mod.name, single_user=True)

        context.view_layer.objects.active = old_active

        bpy.ops.object.convert(target='MESH')

        for obj in context.selected_objects:
            obj.kitops.insert = False
            obj.kitops.main = False

        return {'FINISHED'}




class KO_OT_remove_wire_inserts(Operator):
    bl_idname = 'mesh.ko_remove_wire_inserts'
    bl_label = 'Remove Unused Wire INSERTS'
    bl_description = 'Remove unused wire objects from the INSERTS collection, keeping transforms on child objects'
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return 'INSERTS' in bpy.data.collections


    def execute(self, context):
        collection = bpy.data.collections['INSERTS']
        wires = {obj for obj in collection.all_objects if obj.display_type in {'WIRE', 'BOUNDS'}}

        # prune any wires used by boolean modifiers
        for obj in bpy.data.objects:
            if obj.type != 'MESH':
                continue            
            for mod in obj.modifiers:
                if mod.type == 'BOOLEAN' and mod.object in wires:

                    wires.remove(mod.object)

        for obj in collection.all_objects:
            if obj in wires:
                # before we remove the wire, remove any transformations to the children.
                def getChildren(myObject): 
                    children = [] 
                    for ob in bpy.data.objects: 
                        if ob.parent == myObject: 
                            children.append(ob) 
                    return children 

                wire_children = getChildren(obj)

                for wire_child in wire_children:
                    matrixcopy = wire_child.matrix_world.copy()
                    wire_child.parent = None
                    wire_child.matrix_world = matrixcopy

        for obj in collection.all_objects:
            # if the parent object is a wire, reset its local matrix.
            if obj.parent in wires:
                obj.matrix_local = obj.matrix_world
                obj.parent = None



        for obj in wires:
            bpy.data.objects.remove(obj)

        return {'FINISHED'}


class KO_OT_move_folder(Operator):
    bl_idname = 'mesh.ko_move_folder'
    bl_label = 'Move Folder'
    bl_description = 'Move the chosen folder up or down in the list'
    bl_options = {'REGISTER', 'INTERNAL'}

    index: IntProperty()
    direction: IntProperty()


    def execute(self, context):
        preference = addon.preference()
        neighbor = max(0, self.index + self.direction)
        preference.folders.move(neighbor, self.index)
        return {'FINISHED'}

class KO_OT_install_pillow(Operator, ops.InstallPillow):
    bl_idname = 'mesh.ko_install_pillow'
    bl_label = 'Install Pillow'
    bl_description = 'Install Pillow for thumbnail caching'
    bl_options = {'INTERNAL'}


    def execute(self: Operator, context: bpy.types.Context) -> set:
        # Install Pillow first.
        super().execute(context)
        update.kpack(None, context)
        return {'FINISHED'}

class KO_OT_OpenHelpURL(Operator):
    bl_idname = "mesh.ko_open_help_url" 
    bl_label = "KIT OPS Help"
    bl_description = 'Open KIT OPS documentation'
    bl_options = {'INTERNAL', 'UNDO'}
    
    url : StringProperty()

    def execute(self, context):
        bpy.ops.wm.url_open(url = self.url)
        return {'FINISHED'}

import blf
from bpy_extras import view3d_utils

def draw_callback_3d(self, context):

    try:

        if not (KO_OT_PreviewHardpointTags.running_preview_tags.get(self._region) is self): return

        font_id = 0  # XXX, need to find out how best to get this.

        preference = addon.preference()


        hardpoints = [hp for hp in context.visible_objects if hp.kitops.is_hardpoint]    
        
        for hp in hardpoints:

            view2d_co = view3d_utils.location_3d_to_region_2d(context.region, context.space_data.region_3d, hp.matrix_world.to_translation()   )

            if not view2d_co:
                continue

            # draw some text
            blf.position(font_id, view2d_co.x, view2d_co.y, 0)
            blf.size(font_id, 20, 72)
            color = preference.hardpoint_preview_color
            if hp.kitops.hardpoint_tags:
                blf.color(font_id, color[0], color[1], color[2], color[3])
                blf.draw(font_id, "%s" % ('[' + hp.kitops.hardpoint_tags + ']'))
            else:
                blf.color(font_id, color[0]*.01, color[1]*.01, color[2]*.01, color[3])
                blf.draw(font_id, "%s" % ('[NONE]'))
    except ReferenceError:
        pass


class KO_OT_PreviewHardpointTags(Operator):
    """Tooltip"""
    bl_idname = "mesh.ko_preview_hardpoint_tags"
    bl_label = "Preview Hardpoint Tags"
    bl_options = {'INTERNAL'}


    _handle_3d = None
    running_preview_tags = {}


    def validate_region(self):
        if not (KO_OT_PreviewHardpointTags.running_preview_tags.get(self._region) is self): return False
        return self.region_exists(self._region)

    def region_exists(self, r):
        wm = bpy.context.window_manager
        for window in wm.windows:
            for area in window.screen.areas:
                for region in area.regions:
                    if region == r: return True
        return False

    def update_view(self, context):
        bpy.context.area.tag_redraw()
        context.region.tag_redraw()
        layer = context.view_layer
        layer.update()

    def modal(self, context, event):
        """Modal execution method for the addon."""
        
        try:
            if not self.validate_region() or \
                not context.scene.kitops.preview_hardpoints:
                self.cancel(context)
                return {'CANCELLED'}
            
            return {'PASS_THROUGH'}
        except Exception as e:
            self.cancel(context)
            self.report({'ERROR'}, "An error occured: " + str(e))
            return {'CANCELLED'}

    def cancel(self, context):
        """Reset the screen by removing custom draw handlers."""
        try:
            context.scene.kitops.preview_hardpoints = False
            bpy.types.SpaceView3D.draw_handler_remove(self._handle_3d, 'WINDOW')
            self.update_view(context)
            if KO_OT_PreviewHardpointTags.running_preview_tags.get(self._region) is self:
                del KO_OT_PreviewHardpointTags.running_preview_tags[self._region]
        except Exception as e:
            pass


    def invoke(self, context, event):
        """Initialise the operator."""

        if context.area.type == 'VIEW_3D':

            self._region = context.region

            KO_OT_PreviewHardpointTags.running_preview_tags[self._region] = self

            self._handle_3d = bpy.types.SpaceView3D.draw_handler_add(draw_callback_3d, (self, context), 'WINDOW', 'POST_PIXEL')
            self.update_view(context)

            # set up modal handler.
            context.window_manager.modal_handler_add(self)
            context.scene.kitops.preview_hardpoints = True
            
            # ...and away we go...
            return {'RUNNING_MODAL'}
        else:
            return {'CANCELLED'}

        return {'FINISHED'}


class KO_OT_copy_hardpoint_tags(Operator):
    bl_idname = 'mesh.ko_copy_hardpoint_tags'
    bl_label = 'Copy tags'
    bl_description = 'Copy tags to others'
    bl_options = {'INTERNAL', 'UNDO'}

    tags: StringProperty()

    def execute(self, context):
        hardpoint_objs = [o for o in context.selected_objects if o.kitops.is_hardpoint]

        for hp in hardpoint_objs:
            hp.kitops.hardpoint_tags = self.tags

        context.area.tag_redraw()

        return {'FINISHED'}

class KO_MT_KITOPS(bpy.types.Menu):
    bl_idname = 'KO_MT_KITOPS'
    bl_label = 'KIT OPS'

    def draw(self, context):
        col = self.layout.column()
        col.operator_context = 'INVOKE_DEFAULT'
        col.operator(KO_OT_select_insert.bl_idname)
        col.operator(KO_OT_move_insert.bl_idname)
        col.operator(KO_OT_duplicate_insert.bl_idname)
        col.operator(KO_OT_delete_insert.bl_idname)

        col.separator()

        insert_path = persistence.insert_path(context.active_object.name, context)

        if context.active_object and os.path.exists(insert_path):
            op_ref = KO_OT_auto_create_insert_confirm.bl_idname
        else:
            op_ref = KO_OT_auto_create_insert.bl_idname

        props = col.operator(op_ref, text="Create Object INSERT - Use Object Origin")
        props.set_object_origin_to_bottom = False
        props.material = False
        props.directory = ''
        props.create_type = 'INSERT'
        props = col.operator(op_ref, text="Create Object INSERT - Use Bottom of Object as Origin")
        props.set_object_origin_to_bottom = True
        props.material = False
        props.directory = ''
        props.create_type = 'INSERT'

        props = col.operator(op_ref, text="Create Geo Node INSERT")
        props.set_object_origin_to_bottom = False
        props.material = False
        props.directory = ''
        props.create_type = 'GEO_NODES'

        if context.active_object.active_material:

            material_path = persistence.insert_path(context.active_object.active_material.name, context)


            if context.active_object and os.path.exists(material_path):
                op_ref = KO_OT_auto_create_insert_confirm.bl_idname
            else:
                op_ref = KO_OT_auto_create_insert.bl_idname

            props = col.operator(op_ref, text="Create Shader Nodes INSERT")
            props.set_object_origin_to_bottom = False
            props.material = True
            props.directory = ''
            props.create_type = 'SHADER_NODES'

            props = col.operator(op_ref, text="Create Material INSERT")
            props.set_object_origin_to_bottom = False
            props.material = True
            props.directory = ''
            props.create_type = 'MATERIAL'


        global authoring_enabled
        if not authoring_enabled:
            col.separator()
            col.label(text='Note: Automatically Create Cutters in KIT OPS PRO')


        if authoring_enabled:
            col.operator('mesh.ko_create_decal', text='Create Decal INSERT')

        col.separator()
        col.operator(KO_OT_add_kitops_props.bl_idname, text="Add KIT OPS Props")

class KO_OT_toggle_mode(Operator):
    bl_idname = 'mesh.ko_toggle_mode'
    bl_label = 'Toggle Mode'
    bl_description = "Toggles between regular and smart modes"

    def invoke(self, context, event):
        global authoring_enabled

        preference = addon.preference()

        if preference.mode == 'SMART':
            preference.mode = 'REGULAR'
        elif preference.mode == 'REGULAR':
            preference.mode = 'SMART'

        return {'FINISHED'}

class KO_OT_add_set(Operator):
    bl_idname = 'mesh.ko_add_set'
    bl_label = 'Add Set'
    bl_description = "Create a new set"

    set_name : StringProperty(default="")

    @classmethod
    def poll(cls, context):
        option = addon.option()
        return option.new_set_name != ''

    def invoke(self, context, event):

        preference = addon.preference()

        new_set_name = self.set_name

        index = 0
        while new_set_name in preference.sets:
            index+=1
            new_set_name = self.set_name + '_' + str(index)

        new_set = preference.sets.add()
        new_set.name=new_set_name

        # go through folders and register this set.
        for folder in preference.folders:
            bpy.ops.mesh.ko_add_set_id('INVOKE_DEFAULT', folder_name=folder.name, set_name=new_set_name)

        option = addon.option()
        option.new_set_name = ''

        option.kpack_prefs_set = new_set_name

        return {'FINISHED'}

class KO_OT_remove_set(Operator):
    bl_idname = 'mesh.ko_remove_set'
    bl_label = 'Remove Set'
    bl_description = "Remove a set"

    set_name : StringProperty(default="")

    def invoke(self, context, event):

        preference = addon.preference()
        option = addon.option()

        found_set = preference.sets.find(self.set_name)

        previous_index = found_set - 1 

        if previous_index < 0:
            option.kpack_prefs_set = 'ALL'
        else:
            option.kpack_prefs_set = preference.sets[previous_index].name

        if self.set_name in preference.sets:
            preference.sets.remove(found_set)

        # go through folders and unregister this set.
        for folder in preference.folders:
            bpy.ops.mesh.ko_remove_set_id('INVOKE_DEFAULT', folder_name=folder.name, set_name=self.set_name)

        update.kpack(None, context)

        return {'FINISHED'}


class KO_OT_add_set_id(Operator):
    bl_idname = 'mesh.ko_add_set_id'
    bl_label = 'Add Set ID'
    bl_description = "Add Set ID"

    folder_name : StringProperty(default="")

    set_name : StringProperty(default="")

    def invoke(self, context, event):

        preference = addon.preference()

        option = addon.option()

        folder = preference.folders[self.folder_name]

        if self.set_name not in folder.set_ids:
            folder.set_ids.add().name = self.set_name
        return {'FINISHED'}

class KO_OT_add_folders_to_set(Operator):
    bl_idname = 'mesh.ko_add_folders_to_set'
    bl_label = 'Add all folders to current set'
    bl_description = "Add all folders to current set"

    def invoke(self, context, event):

        preference = addon.preference()

        option = addon.option()

        set_name = option.kpack_prefs_set

        if set_name == 'ALL':
            return {'CANCELLED'}

        for folder in preference.folders:
            if set_name not in folder.set_ids:
                folder.set_ids.add().name = set_name

        return {'FINISHED'}
    
class KO_OT_remove_folders_from_set(Operator):
    bl_idname = 'mesh.ko_remove_folders_from_set'
    bl_label = 'Remove all folders from current set'
    bl_description = "Remove all folders from current set"

    def invoke(self, context, event):

        preference = addon.preference()

        option = addon.option()

        set_name = option.kpack_prefs_set

        if set_name == 'ALL':
            return {'CANCELLED'}

        for folder in preference.folders:
            if set_name in folder.set_ids:
                folder.set_ids.remove(folder.set_ids.find(set_name))

        return {'FINISHED'}
    

class KO_OT_remove_set_id(Operator):
    bl_idname = 'mesh.ko_remove_set_id'
    bl_label = 'Remove Set ID'
    bl_description = "Remove Set ID"

    folder_name : StringProperty(default="")

    set_name : StringProperty(default="")

    def invoke(self, context, event):

        preference = addon.preference()

        option = addon.option()
        folder = preference.folders[self.folder_name]

        if self.set_name in folder.set_ids:
            folder.set_ids.remove(folder.set_ids.find(self.set_name))


        return {'FINISHED'}


class KO_OT_CreateDecal(Operator, ImportHelper):
    """Create a Decal from a .png file"""
    bl_idname = "mesh.ko_create_decal"
    bl_label = "Create Decal From File"

    filter_glob: StringProperty(
        default='*.png',
        options={'HIDDEN'}
    )

    @classmethod
    def poll(cls, context):
        return authoring_enabled

    def execute(self, context):
        matrixmath.generate_decal(self, context)
        return {'FINISHED'}

    
_empty_uuid = uuid.UUID('00000000-0000-0000-0000-000000000000')
def is_valid_asset(kitops_options, asset_data):
    global _empty_uuid
    if kitops_options.asset_libraries_catalogs != 'ALL':
        if kitops_options.asset_libraries_catalogs != 'NONE' and kitops_options.asset_libraries_catalogs != asset_data.catalog_id:
                return False
        if kitops_options.asset_libraries_catalogs == 'NONE' and asset_data.catalog_id != str(_empty_uuid):
                return False
    return True
    
def tag_redraw(context):
    '''Redraw every region in Blender.'''
    for window in context.window_manager.windows:
        for area in window.screen.areas:
            for region in area.regions:
                region.tag_redraw()

class KO_OT_ConvertAssetsToKitOps(Operator):
    """Check for new updates of KIT OPS"""
    bl_idname = "mesh.ko_convert_assets_to_kitops"
    bl_label = "Convert Assets to KIT OPS"
    bl_options = {'INTERNAL', 'UNDO'}
    _timer = None
    step = 0
    max_step = 0

    assets_to_process = []

    new_scene = None

    old_scene = None

    tmp_obj = None

    old_active = None

    def modal(self, context, event):
        if event.type == 'TIMER':
            if self.step >= self.max_step:
                self.cancel(context)
                return {'FINISHED'}

            # Simulate a time-consuming process
            try:
                kitops_scene = context.scene.kitops
                kitops_options = context.window_manager.kitops
                context.window.scene = self.new_scene
                context.view_layer.update()

                asset_to_process = self.assets_to_process[self.step][0]
                asset_type = self.assets_to_process[self.step][1]

                if asset_type == 'OBJECT':
                    ob = asset_to_process

                    kitops_options.currently_processing_asset = ob.name
                    
                    self.new_scene.collection.objects.link(ob)
                    context.view_layer.objects.active = ob
                    ob.select_set(True)
                    bpy.ops.mesh.ko_auto_create_insert('INVOKE_DEFAULT', set_object_origin_to_bottom=False, material=False, directory=kitops_options.asset_destination_dir)
                    ob.select_set(False)
                    ob.use_fake_user = False
                elif asset_type == 'MATERIAL':
                    mat = asset_to_process
                    
                    kitops_options.currently_processing_asset = mat.name

                    context.view_layer.objects.active = self.tmp_obj
                    self.tmp_obj.select_set(True)
                    self.tmp_obj.data.materials.append(mat)
                    self.tmp_obj.active_material = mat
                    bpy.ops.mesh.ko_auto_create_insert('INVOKE_DEFAULT', set_object_origin_to_bottom=False, material=True, directory=kitops_options.asset_destination_dir)
                    self.tmp_obj.select_set(False)
                    mat.use_fake_user = False


                # Update the progress property that's displayed in the interface
                kitops_options.asset_processing_progress = (self.step + 1) / self.max_step
                context.window.cursor_set('WAIT')
                tag_redraw(context)
                self.step += 1
                
                context.window.scene = self.old_scene
                context.view_layer.objects.active = self.old_active
                context.view_layer.update()
                return {'PASS_THROUGH'}
            

            except Exception as e:
                self.cancel(context)
                self.report({'ERROR'}, f"Error whilst processing asset library: {e}")
                return {'CANCELLED'}
            
        return {'PASS_THROUGH'}
    
    

    def execute(self, context):
        prefs = bpy.context.preferences
        filepaths = prefs.filepaths
        asset_libraries = filepaths.asset_libraries
        kitops_scene = context.scene.kitops
        kitops_options = context.window_manager.kitops
        global _empty_uuid

        self.assets_to_process = []
        self.new_scene = None
        self.old_scene = None
        self.old_active = None
        self.tmp_obj = None
        self._timer = None
        self.step = 0
        self.max_step = 0

        # Check if asset_libraries_options is not set
        if not kitops_options.asset_libraries_options:
            self.report({'ERROR'}, "No asset library selected. Please select an asset library.")
            return {'CANCELLED'}
        

        for asset_library in asset_libraries:
            # Only process selected asset libraries
            if asset_library.name == kitops_options.asset_libraries_options:
                library_name = asset_library.name
                library_path = Path(asset_library.path)
                blend_files = [fp for fp in library_path.glob("**/*.blend") if fp.is_file()]
                print(f"Checking the content of library '{library_name}' :")
                if not blend_files:
                    self.report({'ERROR'}, "No assets files found in selected library.")
                    return {'CANCELLED'}
                
                self.old_active = context.view_layer.objects.active
                self.old_scene = context.scene
                self.new_scene = matrixmath.copy_scene()
                self.new_scene.name = "Export"

                context.window.scene = self.old_scene
                context.view_layer.update()

                for blend_file in blend_files:
                    
                    with bpy.data.libraries.load(str(blend_file), assets_only=True) as (data_from, data_to):
                        data_to.objects = data_from.objects
                        data_to.materials = data_from.materials



                    objs = data_to.objects
                    for ob in objs:
                        asset_data = ob.asset_data
                        if is_valid_asset(kitops_options, asset_data):
                            self.assets_to_process.append((ob, 'OBJECT'))
                        else:
                            ob.use_fake_user = False
                            

                    mats = data_to.materials
                    if mats:
                        for mat in mats:
                            asset_data = mat.asset_data
                            if is_valid_asset(kitops_options, asset_data):
                                self.assets_to_process.append((mat, 'MATERIAL'))
                            else:
                                mat.use_fake_user = False


                if len([m for m in self.assets_to_process if m[1] == 'MATERIAL']):
                    tmp_obj_data = bpy.data.meshes.new("KIT OPS tmp material data")
                    self.tmp_obj = bpy.data.objects.new("KIT OPS tmp material object", tmp_obj_data)
                    self.new_scene.collection.objects.link(self.tmp_obj)
                

                self.max_step = len(self.assets_to_process)
                kitops_options.asset_processing_is_running = True
                if self.assets_to_process:
                    kitops_options.currently_processing_asset = self.assets_to_process[0][0].name

                wm = context.window_manager
                self._timer = wm.event_timer_add(0.1, window=context.window)
                wm.modal_handler_add(self)
                context.window.cursor_set('WAIT')
                return {'RUNNING_MODAL'}
            
        return {'CANCELLED'} 

    def cancel(self, context):
        context.window.cursor_set('DEFAULT')
        kitops_scene = context.scene.kitops
        kitops_options = context.window_manager.kitops



        if self.tmp_obj:
            tmp_obj_data = self.tmp_obj.data
            bpy.data.objects.remove(self.tmp_obj)
            bpy.data.meshes.remove(tmp_obj_data)    

        # after exporting all objs delete the scene and perform a cleanup
        if self.new_scene:
            bpy.data.scenes.remove(self.new_scene)
        bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)  


        kitops_options.asset_processing_is_running = False
        kitops_options.asset_processing_progress = 0
        kitops_options.currently_processing_asset = ''

        context.view_layer.objects.active = self.old_active

        wm = context.window_manager
        wm.event_timer_remove(self._timer)
        tag_redraw(context)

class KO_OT_OpenKPACKFolder(Operator):
    """Open selected KPACK Directory"""      # Tooltip for menu items and buttons.
    bl_idname = "mesh.ko_open_kpack_folder"  # Unique identifier for buttons and menu items to reference.
    bl_label = "Open selected KPACK Directory"         # Display name in the interface.

    directory_path : StringProperty()
    
    def execute(self, context):        # execute() is called when running the operator.
        # The path of the folder you want to open
        directory_path = self.directory_path

        # Check if the folder exists
        if os.path.isdir(directory_path):
            try:
                # The command depends on your operating system
                if os.name == 'nt':  # For Windows
                    os.startfile(directory_path)
                elif os.name == 'posix':  # For MacOS and Linux
                    if sys.platform.startswith('darwin'):  # For MacOS
                        subprocess.Popen(['open', directory_path])
                    else:  # For Linux, BSDs, etc.
                        subprocess.Popen(['xdg-open', directory_path])
                else:
                    self.report({'ERROR'}, "Could not open folder: unsupported OS")
                    return {'CANCELLED'}
            except Exception as e:
                self.report({'ERROR'}, "Could not open folder: " + str(e))
                return {'CANCELLED'}
                
            return {'FINISHED'}  # Lets Blender know the operator finished successfully.

        else:
            self.report({'ERROR'}, "Directory does not exist")
            return {'CANCELLED'}
        

# Operator
class SEARCH_OT_kpacks(Operator):
    bl_idname = "search.kpacks"
    bl_label = "Search KPACKS"
    bl_description = "Search for KPACKS"

    def execute(self, context):
        # TODO: Insert your code for searching KPACKS here
        self.report({'INFO'}, "KPACKS search executed!")

        option = addon.option()
        # Clear previous search results
        option.kpacks_search_results.clear()

        # Get the search string from option.masterfolder_search_input
        search_string = option.masterfolder_search_input.lower()  # Convert to lowercase for case-insensitive search


        preference = addon.preference()
        folders_to_search = [f for f in preference.folders]

        # Convert search_string into a regex pattern
        # For instance, if the user enters "*", convert it to ".*" for regex
        regex_pattern = search_string.replace('*', '.*')

        for f in folders_to_search:
            # Traverse subfolders of the master folder
            for subdir, _, _ in os.walk(f.location):
                # Check if this is a subfolder and not the master folder itself
                if subdir != f.location:
                    subfolder_name = os.path.basename(subdir)
                    blend_files = [file for file in os.listdir(subdir) if file.endswith(".blend")]

                    for blend_file in blend_files:
                        # Now use this pattern to search within your strings
                        if re.search(regex_pattern, blend_file, re.IGNORECASE) or \
                            re.search(regex_pattern, subfolder_name, re.IGNORECASE) or \
                            re.search(regex_pattern, f.name, re.IGNORECASE):

                            result_item = option.kpacks_search_results.add()
                            result_item.blend_file = blend_file
                            result_item.master_folder = f.name
                            result_item.pack = subfolder_name
                            result_item.insert_name = regex.clean_name(blend_file, use_re=preference.clean_names)

        return {'FINISHED'}

class CLEAR_OT_kpack_search(Operator):
    bl_idname = "clear.kpack_search"
    bl_label = "Clear KPACK Search"
    bl_description = "Clear the KPACK search results"  # Optional description

    def execute(self, context):
        # TODO: Insert your code for clearing the KPACKS search results here
        option = addon.option()
        # Clear previous search results
        option.kpacks_search_results.clear()

        option.masterfolder_search_input = ""

        self.report({'INFO'}, "KPACKS search cleared!")
        return {'FINISHED'}
    


class KO_OT_select_kpack_insert(Operator):
    bl_idname = 'mesh.ko_select_kpack_insert'
    bl_label = 'Select'
    bl_options = {'INTERNAL'}

    kpack_set : StringProperty()

    kpack_name : StringProperty()

    insert_name : StringProperty()

    @classmethod
    def description(self, context, properties):
        if properties.kpack_name:
            return properties.kpack_name
        return ''

    def execute(self, context):
        if not self.kpack_set or not self.kpack_name:
            return {'CANCELLED'}
        
        kpack_name = self.kpack_name
        option = addon.option()
        
        option.kpack_set = self.kpack_set
        if kpack_name in option.kpack.categories:
            try:
                option.kpacks = kpack_name

                category = option.kpack.categories[kpack_name]

                category.thumbnail = self.insert_name

            except TypeError:
                pass
            return {'FINISHED'}
        return {'CANCELLED'}


class KO_OT_load_search_window(Operator):
    """Open Blender Preferences window to use INSERT search feature"""
    bl_idname = "mesh.ko_load_search_window"
    bl_label = "mesh.ko_load_search_window"

    def execute(self, context):
        # Open the Preferences window
        bpy.ops.screen.userpref_show('INVOKE_DEFAULT')
        
        # Switch to the add-ons tab
        context.preferences.active_section = 'ADDONS'
        
        # Attempt to focus on a specific add-on (replace 'YourAddonName' with your add-on's module name)
        addon_name = 'kitops'
        module = next((mod for mod in context.preferences.addons if mod.module == addon_name), None)
        
        if module:
            context.window_manager.addon_search = 'KIT OPS'
            bpy.data.window_managers["WinMan"].addon_search = "KIT OPS"

            # TODO originally this method was to open the search INSERTs box but we do not have enough API access for now.
            preference = addon.preference()
            preference.context = 'SEARCH'
        else:
            # If the add-on isn't found, search for it
            context.window_manager.addon_search = 'KIT OPS'


        return {'FINISHED'}        
    

class KO_OT_clean_boolean_modifiers(Operator):
    """Remove all boolean modifiers that do not have a target"""
    bl_idname = "mesh.ko_clean_boolean_modifiers"
    bl_label = "Clean Boolean Modifiers"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):

        collected_objects = context.scene.collection.all_objects[:]
        visible_objects = [o for o in bpy.data.objects if o.visible_get()]

        if context.scene and not context.scene.kitops.thumbnail:
            for obj in visible_objects:
                for mod in obj.modifiers:
                    if mod.type != 'BOOLEAN':
                        continue

                    if not mod.object or (mod.object not in collected_objects):
                        obj.modifiers.remove(mod)

        return {'FINISHED'}
    


class KO_OT_delete_insert(Operator):
    """Remove all objects that are part of an INSERT"""
    bl_idname = "mesh.ko_delete_insert"
    bl_label = "Delete INSERT"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object.kitops.insert and context.active_object.kitops.main_object

    def execute(self, context):

        all_objs = []

        selected_objects = context.selected_objects[:]
        for obj in selected_objects:
            insert_objects = insert.find_insert_objects(obj)
            for ins in insert_objects:
                all_objs.append(ins)

        for ins in all_objs:
            if ins.kitops.type == 'CUTTER' and ins.kitops.boolean_type != 'INSERT' and ins.kitops.insert_target:
                modifiers_to_remove = []
                for mod in ins.kitops.insert_target.modifiers:
                    if mod.type == 'BOOLEAN' and mod.object == ins:
                        modifiers_to_remove.append(mod)

                for mod in modifiers_to_remove:
                    ins.kitops.insert_target.modifiers.remove(mod)
        for ins in all_objs:
            remove.object(ins, data=True, do_unlink=True)

        bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)  

        return {'FINISHED'}
    
class KO_OT_select_insert(Operator):
    """Select all objects that are part of an INSERT"""
    bl_idname = "mesh.ko_select_insert"
    bl_label = "Select INSERT"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        return context.active_object and context.active_object.kitops.insert and context.active_object.kitops.main_object
    
    def execute(self, context):

        selected_objects = context.selected_objects[:]
        for obj in selected_objects:
            insert_objects = insert.find_insert_objects(obj)
            for ins in insert_objects:
                ins.select_set(True)

        return {'FINISHED'}


class KO_OT_duplicate_insert(Operator, move_insert):
    """Copy an INSERT and then move it"""
    bl_idname = "mesh.ko_duplicate_insert"
    bl_label = "Duplicate INSERT"

    new_objs = []

    is_duplicate_mode = True
    
    @classmethod
    def poll(cls, context):
        return super().poll(context) and len(set([o.kitops.id for o in context.selected_objects])) == 1
    

    def invoke(self, context, event):

        # Go through all selected objefcts and grab associated INSERT objects.
        selected_objects = context.selected_objects[:]
        for obj in selected_objects:
            insert_objects = insert.find_insert_objects(obj)
            for ins in insert_objects:
                ins.select_set(True)

        # Duplicate the object(s) and keep a record of the new object(s).
        self.new_objs = []
        bpy.ops.object.duplicate()
        new_uuid = id.uuid()
        for obj in context.selected_objects:
            obj.kitops.id = new_uuid
            self.new_objs.append(obj)
        
        for ins in context.selected_objects:
                # Add new boolean modifiers if the new object warrants it.
                if ins.kitops.type == 'CUTTER' and ins.kitops.boolean_type != 'INSERT' and ins.kitops.insert_target:
                    insert.add_boolean(ins)

        return super().invoke(context, event)
    

    def exit(self, context, clear=False):
        super().exit(context, clear)
        if clear:
            for ins in self.new_objs:
                if ins.kitops.type == 'CUTTER' and ins.kitops.boolean_type != 'INSERT' and ins.kitops.insert_target:

                    modifiers_to_remove = []
                    for mod in ins.kitops.insert_target.modifiers:
                        if mod.type == 'BOOLEAN' and mod.object == ins:
                            modifiers_to_remove.append(mod)

                    for mod in modifiers_to_remove:
                        ins.kitops.insert_target.modifiers.remove(mod)

                # remove the object reference as well.
                obj_data = ins.data
                bpy.data.objects.remove(ins)
                if obj_data.users == 0:
                    bpy.data.meshes.remove(obj_data)

class KO_OT_add_kitops_props(Operator):
    """Add KIT OPS properties to an object"""
    bl_idname = "mesh.ko_add_kitops_props"
    bl_label = "Add KIT OPS Properties"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.active_object and not context.active_object.kitops.insert

    def execute(self, context):
        insert.add_kitops_props(context.active_object)
        context.view_layer.update() 
        return {'FINISHED'}

class KO_OT_select_similar_inserts(bpy.types.Operator):
    """Select all inserts with similar original INSERT name"""
    bl_idname = "mesh.ko_select_similar_insert"
    bl_label = "Select Similar INSERTs"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        selected_objs = [o for o in context.selected_objects if o.kitops.insert]
        if not selected_objs:
            self.report({'WARNING'}, "No selected objects")
            return {'CANCELLED'}

        # Deselect all first
        bpy.ops.object.select_all(action='DESELECT')

        # Select objects that have the same insert name as the selected objects
        for obj in selected_objs:
            insert_name = obj.kitops.insert_name
            for insert_obj in bpy.data.objects:
                if insert_obj.kitops.insert and insert_obj.kitops.insert_name == insert_name:
                    insert_obj.select_set(True)

        return {'FINISHED'}
            
    
operator_keymap_ids = [
    KO_OT_select_insert.bl_idname,
    KO_OT_delete_insert.bl_idname,
    KO_OT_clean_boolean_modifiers.bl_idname,
    KO_OT_duplicate_insert.bl_idname
]


classes = [
    KO_OT_purchase,
    KO_OT_store,
    KO_OT_documentation,
    KO_OT_add_kpack_path,
    KO_OT_remove_kpack_path,
    KO_OT_refresh_kpacks,
    KO_OT_next_kpack,
    KO_OT_previous_kpack,
    KO_OT_add_insert,
    KO_OT_move_insert,
    KO_OT_add_insert_material,
    KO_OT_add_insert_gn,
    KO_OT_add_insert_shader_nodes,
    KO_OT_select_inserts,
    KO_OT_remove_insert_properties,
    KO_OT_remove_insert_properties_x,
    KO_OT_export_settings,
    KO_OT_import_settings,
    KO_OT_convert_to_mesh,
    KO_OT_remove_wire_inserts,
    KO_OT_move_folder,
    KO_OT_install_pillow,
    KO_OT_OpenHelpURL,
    KO_OT_auto_create_insert,
    KO_OT_auto_create_insert_confirm,
    KO_MT_KITOPS,
    KO_OT_add_hardpoint,
    KO_OT_PreviewHardpointTags,
    KO_OT_copy_hardpoint_tags,
    KO_OT_toggle_mode,
    KO_OT_add_set,
    KO_OT_remove_set,
    KO_OT_add_set_id,
    KO_OT_remove_set_id,
    KO_OT_CreateDecal,
    KO_OT_ConvertAssetsToKitOps,
    KO_OT_OpenKPACKFolder,
    SEARCH_OT_kpacks,
    CLEAR_OT_kpack_search,
    KO_OT_select_kpack_insert,
    KO_OT_load_search_window,
    KO_OT_clean_boolean_modifiers,
    KO_OT_delete_insert,
    KO_OT_select_insert,
    KO_OT_duplicate_insert,
    KO_OT_add_folders_to_set,
    KO_OT_remove_folders_from_set,
    KO_OT_add_kitops_props,
    KO_OT_select_similar_inserts
]


def menu_func(self, context):
    self.layout.menu(KO_MT_KITOPS.bl_idname)
    col = self.layout.column()
    # col.operator_context = 'INVOKE_DEFAULT'
    # col.operator(KO_OT_move_insert.bl_idname)
    # col.operator(KO_OT_auto_create_insert.bl_idname)


def register():
    for cls in classes:
        register_class(cls)
    smart.register()
    try:
        from .. utility import matrixmath
        matrixmath.register()
    except: pass

    bpy.types.VIEW3D_MT_object_context_menu.append(menu_func)

def unregister():
    bpy.types.VIEW3D_MT_object_context_menu.remove(menu_func)

    for cls in classes:
        unregister_class(cls)

    smart.unregister()
    try:
        from .. utility import matrixmath
        matrixmath.unregister()
    except: pass
