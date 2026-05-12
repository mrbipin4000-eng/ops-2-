import os

import bpy

from bpy.types import Operator
from bpy.props import *
from bpy.utils import register_class, unregister_class

from . import addon, bbox, id, insert, modifier, remove

import re

#XXX: type and reference error
#DEPRECATED TODO this method now does nothing - remove if it works out ok.
def toggles_depsgraph_update_post():
    return
    option = addon.option()

    solid_inserts = insert.collect(solids=True, all=True)
    count = 0
    for obj in solid_inserts:
        try:
            if obj.hide_viewport:
                option['show_solid_objects'] = False
                break
            elif obj.name in bpy.context.view_layer.objects and not obj.select_get():
                count += 1
        except RuntimeError: pass

    if count > 2 and count == len(solid_inserts):
        option['show_solid_objects'] = True

    boolean_inserts = insert.collect(cutters=True, all=True)
    count = 0
    for obj in boolean_inserts:
        try:
            if obj.hide_viewport:
                option['show_cutter_objects'] = False
                break
            elif not obj.select_get():
                count += 1
        except RuntimeError: pass

    if count > 2 and count == len(boolean_inserts):
        option['show_cutter_objects'] = True

    wire_inserts = insert.collect(wires=True, all=True)
    count = 0
    for obj in wire_inserts:
        try:
            if obj.hide_viewport:
                option['show_wire_objects'] = False
                break
            elif not obj.select_get():
                count += 1
        except RuntimeError: pass

    if count > 2 and count == len(wire_inserts):
        option['show_wire_objects'] = True

def is_direct_duplicate_of(original_name, possible_duplicate_name):
    # First, check if the names are exactly the same (i.e., the possible duplicate is the original)
    if original_name == possible_duplicate_name:
        return False

    # Next, try to extract the base name and the duplicate number from the possible duplicate name
    match = re.match(rf"(.*)(\.\d{{3}})$", possible_duplicate_name)

    # If the name doesn't match the expected format (base name + ".001", ".002", etc.), it's not a duplicate
    if match is None:
        return False

    # Extract the base name and duplicate number
    base_name, duplicate_number = match.groups()

    # If the base name is the same as the original name and the duplicate number is ".001", it's a direct duplicate
    if base_name == original_name and duplicate_number == ".001":
        return True

    # Otherwise, check if the original name is also a duplicate and if its duplicate number is one less than the possible duplicate's number
    original_match = re.match(rf"(.*)(\.\d{{3}})$", original_name)
    if original_match is not None:
        original_base_name, original_duplicate_number = original_match.groups()
        if original_base_name == base_name and int(duplicate_number[1:]) == int(original_duplicate_number[1:]) + 1:
            return True

    # If none of the above checks succeeded, the possible duplicate is not a direct duplicate of the original
    return False


def add_mirror(obj, axis='X'):
    obj.kitops.mirror = True
    mod = obj.modifiers.new(name='KIT OPS Mirror', type='MIRROR')

    if mod:
        mod.show_expanded = False
        mod.use_axis[0] = False

        index = {'X': 0, 'Y': 1, 'Z': 2} # patch inplace for api change
        axis_to_use = getattr(obj.kitops, F'mirror_{axis.lower()}')
        mod.use_axis[index[axis]] = axis_to_use


        mod.mirror_object = obj.kitops.insert_target
        obj.kitops.mirror_target = obj.kitops.insert_target

        sort_modifiers(obj)




def validate_mirror(inserts, axis='X'):
    for obj in inserts:
        if obj.kitops.mirror:

            available = False
            # assuming our mirror is most recent
            for modifier in reversed(obj.modifiers):

                if modifier.type == 'MIRROR' and modifier.mirror_object == obj.kitops.mirror_target:
                    available = True
                    index = {'X': 0, 'Y': 1, 'Z': 2} # patch inplace for api change
                    axis_to_use = getattr(obj.kitops, F'mirror_{axis.lower()}')
                    modifier.use_axis[index[axis]] = axis_to_use


                    if True not in modifier.use_axis[:]:
                        obj.kitops.mirror = False
                        obj.kitops.mirror_target = None
                        obj.modifiers.remove(modifier)

                    break

            if not available:
                add_mirror(obj, axis=axis)

        else:
            add_mirror(obj, axis=axis)


def sort_modifiers(obj):

    array_mod_index = obj.modifiers.find('KIT OPS Array')
    mirror_mod_index = obj.modifiers.find('KIT OPS Mirror')
    while (array_mod_index != -1 and mirror_mod_index != -1 and mirror_mod_index < array_mod_index):
        bpy.ops.object.modifier_move_down({'object': obj}, modifier='KIT OPS Mirror')
        array_mod_index = obj.modifiers.find('KIT OPS Array')
        mirror_mod_index = obj.modifiers.find('KIT OPS Mirror')


def update_array(obj, mod):
    if mod:
        mod.show_expanded = False
        mod.count = obj.kitops.array_count
        mod.use_relative_offset = False
        mod.use_constant_offset = True
        mod.constant_offset_displace = obj.kitops.array_offset

def add_array(obj):

    if obj.kitops.array_count > 1:
        mod = obj.modifiers.new(name='KIT OPS Array', type='ARRAY')
        update_array(obj, mod)

        sort_modifiers(obj)

def validate_array(inserts):


    for obj in inserts:
        # assuming our mirror is most recent
        available = False
        for modifier in reversed(obj.modifiers):            
            if modifier.type == 'ARRAY' and modifier.name.startswith('KIT OPS Array'):
                available = True

                # update the array modifier.
                if obj.kitops.array_count <= 1:
                    obj.modifiers.remove(modifier)
                else:
                    update_array(obj, modifier)
                break

        if not available:
            add_array(obj)


# XXX: align needs to check dimensions with current insert disabled
class KO_OT_align_horizontal(Operator):
    bl_idname = 'mesh.ko_align_horizontal'
    bl_label = 'Align horizontal'
    bl_description = 'Align selected INSERTS horizontally within target bounds'
    bl_options = {'REGISTER', 'UNDO'}

    y_axis: BoolProperty(
        name = 'Y Axis',
        description = 'Use the y axis of the INSERT TARGET for alignment',
        default = False)

    def execute(self, context):

        # get mains
        mains = insert.collect(context.selected_objects, mains=True)

        for main in mains:
            if main.kitops.insert_target:
                center = bbox.center(main.kitops.insert_target)
                setattr(main.location, 'y' if self.y_axis else 'x', getattr(center, 'y' if self.y_axis else 'x'))

        return {'FINISHED'}


class KO_OT_align_vertical(Operator):
    bl_idname = 'mesh.ko_align_vertical'
    bl_label = 'Align vertical'
    bl_description = 'Align selected INSERTS vertically within target bounds'
    bl_options = {'REGISTER', 'UNDO'}

    z_axis: BoolProperty(
        name = 'Z Axis',
        description = 'Use the Z axis of the INSERT TARGET for alignment',
        default = False)

    def execute(self, context):

        # get mains
        mains = insert.collect(context.selected_objects, mains=True)

        for main in mains:
            if main.kitops.insert_target:
                center = bbox.center(main.kitops.insert_target)
                setattr(main.location, 'z' if self.z_axis else 'y', getattr(center, 'z' if self.z_axis else 'y'))

        return {'FINISHED'}


class KO_OT_align_left(Operator):
    bl_idname = 'mesh.ko_align_left'
    bl_label = 'Align left'
    bl_description = 'Align selected INSERTS to the left of the target bounds'
    bl_options = {'REGISTER', 'UNDO'}

    y_axis: BoolProperty(
        name = 'Y Axis',
        description = 'Use the y axis of the INSERT TARGET for alignment',
        default = False)

    def execute(self, context):

        mains = insert.collect(context.selected_objects, mains=True)

        for main in mains:
            if main.kitops.insert_target:
                left = bbox.back(main.kitops.insert_target).y if self.y_axis else bbox.left(main.kitops.insert_target).x
                setattr(main.location, 'y' if self.y_axis else 'x', left)

        return {'FINISHED'}


class KO_OT_align_right(Operator):
    bl_idname = 'mesh.ko_align_right'
    bl_label = 'Align right'
    bl_description = 'Align selected INSERTS to the right of the target bounds'
    bl_options = {'REGISTER', 'UNDO'}

    y_axis: BoolProperty(
        name = 'Y Axis',
        description = 'Use the y axis of the INSERT TARGET for alignment',
        default = False)

    def execute(self, context):

        mains = insert.collect(context.selected_objects, mains=True)

        for main in mains:
            if main.kitops.insert_target:
                right = bbox.front(main.kitops.insert_target).y if self.y_axis else bbox.right(main.kitops.insert_target).x
                setattr(main.location, 'y' if self.y_axis else 'x', right)

        return {'FINISHED'}


class KO_OT_align_top(Operator):
    bl_idname = 'mesh.ko_align_top'
    bl_label = 'Align top'
    bl_description = 'Align selected INSERTS to the top of the target bounds'
    bl_options = {'REGISTER', 'UNDO'}

    z_axis: BoolProperty(
        name = 'Z Axis',
        description = 'Use the Z axis of the INSERT TARGET for alignment',
        default = False)

    def execute(self, context):

        mains = insert.collect(context.selected_objects, mains=True)

        for main in mains:
            if main.kitops.insert_target:
                top = bbox.top(main.kitops.insert_target).z if self.z_axis else bbox.back(main.kitops.insert_target).y
                setattr(main.location, 'z' if self.z_axis else 'y', top)

        return {'FINISHED'}


class KO_OT_align_bottom(Operator):
    bl_idname = 'mesh.ko_align_bottom'
    bl_label = 'Align bottom'
    bl_description = 'Align selected INSERTS to the bottom of the target bounds'
    bl_options = {'REGISTER', 'UNDO'}

    z_axis: BoolProperty(
        name = 'Z Axis',
        description = 'Use the Z axis of the INSERT TARGET for alignment',
        default = False)

    def execute(self, context):

        mains = insert.collect(context.selected_objects, mains=True)

        for main in mains:
            if main.kitops.insert_target:
                bottom = bbox.bottom(main.kitops.insert_target).z if self.z_axis else bbox.front(main.kitops.insert_target).y
                setattr(main.location, 'z' if self.z_axis else 'y', bottom)

        return {'FINISHED'}


class KO_OT_stretch_wide(Operator):
    bl_idname = 'mesh.ko_stretch_wide'
    bl_label = 'Stretch wide'
    bl_description = 'Stretch selected INSERTS to the width of the target bounds'
    bl_options = {'REGISTER', 'UNDO'}

    y_axis: BoolProperty(
        name = 'X axis',
        description = 'Use the Y axis of the INSERT TARGET for stretching',
        default = False)

    halve: BoolProperty(
        name = 'Halve',
        description = 'Halve the stretch amount',
        default = False)

    def execute(self, context):

        mains = insert.collect(context.selected_objects, mains=True)

        for main in mains:
            if main.kitops.insert_target:
                dimension = main.kitops.insert_target.dimensions[1 if self.y_axis else 0]

                if self.halve:
                    dimension /= 2

                main.scale.x = dimension / main.dimensions[0] * main.scale.x

        return {'FINISHED'}


class KO_OT_stretch_tall(Operator):
    bl_idname = 'mesh.ko_stretch_tall'
    bl_label = 'Stretch tall'
    bl_description = 'Stretch selected INSERTS to the height of the target bounds'
    bl_options = {'REGISTER', 'UNDO'}

    z_axis: BoolProperty(
        name = 'Side',
        description = 'Use the Z axis of the INSERT TARGET for stretching',
        default = False)

    halve: BoolProperty(
        name = 'Halve',
        description = 'Halve the stretch amount',
        default = False)

    def execute(self, context):

        mains = insert.collect(context.selected_objects, mains=True)

        for main in mains:
            if main.kitops.insert_target:
                dimension = main.kitops.insert_target.dimensions[2 if self.z_axis else 1]

                if self.halve:
                    dimension /= 2

                main.scale.y = dimension / main.dimensions[1] * main.scale.y

        return {'FINISHED'}



smart_update = True
class update:


    def main(prop, context):
        global smart_update
        if not smart_update:
            return
        smart_update = False
        try:
            for obj in bpy.data.objects:
                if obj != context.active_object:
                    obj.kitops.main = False
                else:
                    obj.kitops.main = True

        finally:
            smart_update = True

    def insert_target(prop, context):
        global smart_update
        if not smart_update:
            return
        smart_update = False
        try:
            insert_target_to_update = prop.insert_target
            inserts = insert.collect(context.selected_objects)

            for obj in inserts:
                if not context.active_object:
                    continue
                obj.kitops.applied = False

                reserved_target = obj.kitops.reserved_target
                if insert_target_to_update != reserved_target:
                    obj.kitops.reserved_target = insert_target_to_update

                    if reserved_target:
                        # Copy Boolean modifiers from reserved_target to insert_target if it is pointing to the active object.
                        for modifier in reserved_target.modifiers:
                            if modifier.type == 'BOOLEAN' and modifier.object == obj and insert_target_to_update:
                                new_modifier = insert_target_to_update.modifiers.new(name=modifier.name, type=modifier.type)

                                # Copy properties from the old modifier to the new one
                                for attr in dir(modifier):
                                    if not attr.startswith("__") and not callable(getattr(modifier, attr)):
                                        try:
                                            setattr(new_modifier, attr, getattr(modifier, attr))
                                        except AttributeError:
                                            pass  # Skip attributes that can't be copied

                        # Delete the old Boolean modifiers from reserved_target
                        for modifier in reserved_target.modifiers:
                            if modifier.type == 'BOOLEAN' and modifier.object == obj:
                                reserved_target.modifiers.remove(modifier)
                    
                    
                    if insert_target_to_update and obj.kitops.boolean_type != 'INSERT' and obj.kitops.type == 'CUTTER':
                        modifier_already_added = False
                        for modifier in insert_target_to_update.modifiers:
                            if modifier.type == 'BOOLEAN' and modifier.object == obj:
                                modifier_already_added = True
                                break
                        if not modifier_already_added:
                            insert.add_boolean(obj, insert_target_to_update)

                    obj.kitops.insert_target = insert_target_to_update
                    obj.kitops.reserved_target = insert_target_to_update

        finally:
            smart_update = True

    def mirror_x(prop, context):
        global smart_update
        if not smart_update:
            return
        smart_update = False
        try:
            inserts = insert.collect(context.selected_objects)

            for obj in inserts:
                obj.kitops.mirror_x = bpy.context.active_object.kitops.mirror_x

            validate_mirror(inserts, axis='X')
        finally:
            smart_update = True

    def mirror_y(prop, context):
        global smart_update
        if not smart_update:
            return
        smart_update = False
        try:
            inserts = insert.collect(context.selected_objects)

            for obj in inserts:
                obj.kitops.mirror_y = bpy.context.active_object.kitops.mirror_y

            validate_mirror(inserts, axis='Y')
        finally:
            smart_update = True

    def mirror_z(prop, context):
        global smart_update
        if not smart_update:
            return
        smart_update = False
        try:  
            inserts = insert.collect(context.selected_objects)

            for obj in inserts:
                obj.kitops.mirror_z = bpy.context.active_object.kitops.mirror_z

            validate_mirror(inserts, axis='Z')
        finally:
            smart_update = True

    def array_insert(prop, context):
        global smart_update
        if not smart_update:
            return
        smart_update = False
        try:
            inserts = insert.collect(context.selected_objects)

            for obj in inserts:
                obj.kitops.array_count = bpy.context.active_object.kitops.array_count
                obj.kitops.array_offset = bpy.context.active_object.kitops.array_offset

            validate_array(inserts)
        finally:
            smart_update = True


        return None

classes = [
    KO_OT_align_horizontal,
    KO_OT_align_vertical,
    KO_OT_align_left,
    KO_OT_align_right,
    KO_OT_align_top,
    KO_OT_align_bottom,
    KO_OT_stretch_wide,
    KO_OT_stretch_tall]


def register():
    for cls in classes:
        register_class(cls)


def unregister():
    for cls in classes:
        unregister_class(cls)
