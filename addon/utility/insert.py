import os

import bpy

from . import addon, id, ray, remove, regex, update, modifier

import numpy as np
from mathutils import Matrix, Vector

operator = None

def authoring():
    if not bpy.context or not hasattr(bpy.context, 'scene'):
        return False

    preference = addon.preference()

    if bpy.context.scene.kitops.factory:
        return True

    insert_file = False
    for folder in preference.folders:
        path = os.path.commonprefix([os.path.realpath(bpy.data.filepath), os.path.realpath(folder.location)])
        if path == os.path.realpath(folder.location):
            if os.path.basename(bpy.data.filepath) != 'render.blend':
                insert_file = True
                break

    return insert_file if not bpy.context.scene.kitops.thumbnail else False

def hide_handler(context,op):
    option = addon.option()
    preference = addon.preference()
    hide = False

    if op.duplicate:
        if not op.is_hardpoint_mode:
            ray.cast(op)
            hide = not ray.success
        else:
            hide = False

        for obj in op.inserts:
            obj.hide_viewport = hide

        for obj in op.cutter_objects:
            for modifier in op.boolean_target.modifiers:
                if modifier.type == 'BOOLEAN' and modifier.object == obj:
                    modifier.show_viewport = not hide

def collect(objs=[], mains=False, solids=False, cutters=False, wires=False, all=False):

    correct_ids()

    if all:
        inserts = [obj for obj in bpy.data.objects if obj.kitops.insert]
    else:
        # gather up all related inserts to the main object.
        insert_map = {}
        for obj in bpy.data.objects:
            if not obj.kitops.id:
                continue
            if obj.kitops.id not in insert_map:
                insert_map[obj.kitops.id] = []
            insert_map[obj.kitops.id].append(obj)

        inserts = []
        for kitops_id in insert_map:
            inserts_entries = insert_map[kitops_id]
            for insert_obj in inserts_entries:
                if insert_obj in objs and insert_obj.kitops.insert:
                    inserts.extend(inserts_entries)
                    continue

    inserts = list(set(inserts))

    inserts = sorted(inserts, key=lambda o: o.name)

    if mains:
        return [obj for obj in inserts if obj.kitops.main]

    elif solids:
        return [obj for obj in inserts if obj.kitops.type == 'SOLID']

    elif cutters:
        return [obj for obj in inserts if obj.kitops.type == 'CUTTER']

    elif wires:
        return [obj for obj in inserts if obj.kitops.type == 'WIRE']

    return inserts

def parent_objects(child, parent):
    # Add parent if we have a boolean target. TODO investigate why matric only needed for original inserts and extra copy needed for SYNTH
    preference = addon.preference()
    if preference.parent_inserts or child.kitops.is_hardpoint:
        child.parent = parent
        child.matrix_parent_inverse = parent.matrix_world.inverted()

def add(op, context):
    correct_ids()

    preference = addon.preference()
    option = addon.option()

    strip_num = lambda string: string.rstrip('0123456789.') if len(string.split('.')) == 2 else string

    basename = os.path.basename(op.location)
    material_ids = [mat.kitops.id for mat in bpy.data.materials if mat.kitops.id]
    kitops_materials = [regex.clean_name(strip_num(mat.name), use_re=preference.clean_datablock_names) for mat in bpy.data.materials if mat.kitops.material]


    dupe_mat_index_to_original = {}
    dupe_img_index_to_original = {}
    with bpy.data.libraries.load(op.location) as (blend, imported):
        imported.objects = blend.objects
        imported.materials = blend.materials
        imported.images = blend.images
        imported.node_groups = blend.node_groups
        if op.material_link:
            i = 0
            for mat in blend.materials:
                if mat in bpy.data.materials:
                    dupe_mat_index_to_original[i] = mat
                i+=1
            i = 0
            for img in blend.images:
                if img in bpy.data.images:
                    dupe_img_index_to_original[i] = img
                i+=1


    # if we have detected duplicates, assign them to a proper mapping of duplicate -> original material.
    dupe_mat_to_original_mat = {}
    for key_index in dupe_mat_index_to_original:
        original_mat_name = dupe_mat_index_to_original[key_index]
        duplicate_mat_name = imported.materials[key_index].name
        dupe_mat_to_original_mat[duplicate_mat_name] = bpy.data.materials[original_mat_name]


    dupe_img_to_original_img = {}
    for key_index in dupe_img_index_to_original:
        original_img_name = dupe_img_index_to_original[key_index]
        duplicate_img_name = imported.images[key_index].name
        dupe_img_to_original_img[duplicate_img_name] = bpy.data.images[original_img_name]



    # Attempt to handle any duplicate materials here ahead of handing them by id.
    if op.material_link:
        for obj in imported.objects:
            try:
                if obj is None or not hasattr(obj, 'data') or not hasattr(obj.data, 'materials'):
                    continue
                mats_to_remove = []
                # Handle any duplicate materials by merging them with the scene.
                for obj_mat in obj.data.materials:
                    if obj_mat is None:
                        continue

                    if obj_mat.name in dupe_mat_to_original_mat:
                        # This object contains a duplicate material.
                        orig_scene_material = dupe_mat_to_original_mat[obj_mat.name]
                        for slot in obj.material_slots:
                            if slot.material == obj_mat:
                                slot.material = orig_scene_material
                                mats_to_remove.append(obj_mat)

                for mat_to_remove in mats_to_remove:
                    if mat_to_remove.users == 0:
                        bpy.data.materials.remove(mat_to_remove)

                        node_map = {}

                        #preform clean up when a material has been removed.
                        def remove_node_groups():
                            for i in range(0, len(imported.node_groups)):
                                try:
                                    node_group = imported.node_groups[i]
                                    if node_group.users == 0:
                                        bpy.data.node_groups.remove(node_group)
                                        remove_node_groups()
                                except ReferenceError:
                                    pass
                        remove_node_groups()

                        for img in imported.images:
                            if img.users == 0:
                                bpy.data.images.remove(img)

            except (AttributeError, ReferenceError):
                pass





    op.inserts = []

    for obj in sorted(imported.objects, key=lambda obj: obj.name):
        if not obj.kitops.hide:
            op.inserts.append(obj)

    op.cutter_objects = sorted([obj for obj in op.inserts if obj.kitops.type == 'CUTTER'], key=lambda obj: not obj.kitops.main)

    new_id = id.uuid()

    for obj in op.inserts:
        obj.name = regex.clean_name(F'{basename[:-6].title()}_{obj.name.title()}', use_re=preference.clean_datablock_names)
        obj.kitops.inserted = True
        obj.kitops.id = new_id
        obj.kitops.label = regex.clean_name(basename, use_re=preference.clean_names)
        obj.kitops.collection = regex.clean_name(os.path.basename(str(op.location)[:-len(os.path.basename(op.location)) - 1]), use_re=preference.clean_datablock_names)

        if op.boolean_target:
            obj.kitops.insert_target = op.boolean_target
            obj.kitops.reserved_target = op.boolean_target

        for slot in obj.material_slots:
            if slot.material:
                slot.material.kitops.material = False

            # needs id check for standard assign
            if slot.material and regex.clean_name(slot.material.name, use_re=preference.clean_datablock_names) in kitops_materials and not op.material:
                old_material = bpy.data.materials[slot.material.name]
                slot.material = bpy.data.materials[regex.clean_name(slot.material.name, use_re=preference.clean_datablock_names)]

                if old_material.users == 0:
                    bpy.data.materials.remove(old_material, do_unlink=True, do_id_user=True, do_ui_user=True)

            elif slot.material and not op.material:
                slot.material.name = regex.clean_name(slot.material.name, use_re=preference.clean_datablock_names)
                bpy.data.materials[slot.material.name].kitops.material = True

            elif slot.material and op.material_link:
                if slot.material.kitops.id:
                    if slot.material.kitops.id in material_ids:
                        op.import_material = [mat for mat in bpy.data.materials if mat.kitops.id and mat.kitops.id == slot.material.kitops.id][0]
                        op.import_material.kitops.material = True
                        break

                    else:
                        op.import_material = slot.material
                        op.import_material.kitops.material = True
                        break

                elif regex.clean_name(strip_num(slot.material.name), use_re=preference.clean_datablock_names) in kitops_materials:
                    if strip_num(slot.material.name) in bpy.data.materials:
                        mats = [m for m in sorted(bpy.data.materials[:], key=lambda m: m.name) if m.kitops.material and regex.clean_name(strip_num(slot.material.name), use_re=preference.clean_datablock_names) == regex.clean_name(strip_num(m.name), use_re=preference.clean_datablock_names) and m != slot.material]

                        if mats:
                            op.import_material = mats[0]
                            break

                        op.import_material = slot.material

                    else:
                        op.import_material = slot.material
                    op.import_material.kitops.material = True
                    break

                else:
                    op.import_material = slot.material
                    op.import_material.kitops.material = True
                    break

            elif slot.material and op.material:
                slot.material.name = regex.clean_name(slot.material.name, use_re=preference.clean_datablock_names)
                op.import_material = slot.material
                bpy.data.materials[slot.material.name].kitops.material = True
                break

    insert_name = regex.clean_name(basename[:-6].title(), use_re=preference.clean_datablock_names)

    for obj in op.inserts:
        if insert_name not in bpy.data.collections:
            bpy.data.collections['INSERTS'].children.link(bpy.data.collections.new(name=insert_name))

        bpy.data.collections[insert_name].objects.link(obj)
        obj.kitops.applied = False

        if obj.kitops.main:
            bpy.context.view_layer.objects.active = obj

    added_mods = []
    if op.boolean_target:
        for obj in op.cutter_objects:
            obj.display_type = 'BOUNDS'
            # if obj.kitops.boolean_type != 'INSERT':
            mod = add_boolean(obj)
            if mod:
                mod.show_viewport = False
                mod.show_render = False
                added_mods.append(mod)


    op.main = context.active_object
    for obj in op.inserts:
        obj.kitops.main_object = op.main

    if op.init_selected and op.boolean_target:
        update.insert_scale(None, context)

    for scene in imported.scenes:
        bpy.data.scenes.remove(scene, do_unlink=True)

    for material in imported.materials:
        try:
            if not material.kitops.material and material.users == 0:
                bpy.data.materials.remove(material, do_unlink=True, do_id_user=True, do_ui_user=True)
        except: continue

    for obj in op.inserts:
        obj.kitops.insert = True
        obj.kitops.insert_name = insert_name
        if obj.data:
            obj.data.kitops.insert = True

    update.insert_scale(None, context)

    for mod in added_mods:
        mod.show_viewport = True
        mod.show_render = True

    return new_id


def add_boolean(obj, insert_target = None):
    if obj.kitops.boolean_type == 'INSERT':
        return

    if not insert_target:
        insert_target = obj.kitops.insert_target

    mod = insert_target.modifiers.new(name='{}: {}'.format(obj.kitops.boolean_type.title(), obj.name), type='BOOLEAN')
    mod.show_expanded = False
    mod.operation = obj.kitops.boolean_type
    mod.object = obj

    if hasattr(mod, 'solver'):
        mod.solver = addon.preference().boolean_solver

    obj.show_all_edges = False

    ignore_weight = addon.preference().sort_bevel_ignore_weight
    ignore_vgroup = addon.preference().sort_bevel_ignore_vgroup
    ignore_verts = addon.preference().sort_bevel_ignore_only_verts
    props = {'use_only_vertices': True} if bpy.app.version[:2] < (2, 90) else {'affect': 'VERTICES'}
    bevels = modifier.bevels(insert_target, weight=ignore_weight, vertex_group=ignore_vgroup, props=props if ignore_verts else {})
    modifier.sort(insert_target, option=addon.preference(), ignore=bevels, stop_flag=addon.preference().sort_stop_char, ignore_flag=addon.preference().sort_ignore_char)

    return mod

def select():
    correct_ids()

    global operator

    inserts = collect([o for o in bpy.data.objects if o.select_get()])

    main_objects = collect(inserts, mains=True)

    for obj in inserts:
        if not operator:
            if obj.kitops.selection_ignore and obj.select_get():

                for deselect in inserts:
                    if deselect != obj:
                        deselect.select_set(False)

                break

            elif not obj.kitops.selection_ignore:
                obj.select_set(True)
        else:
            obj.select_set(True)

        if not operator:
            obj.hide_viewport = False

    active_spotted = None
    if bpy.context.active_object and bpy.context.active_object.kitops.insert:
        for main in main_objects:

            if main.kitops.id == bpy.context.active_object.kitops.id:
                active_spotted = main

    if active_spotted:
        bpy.context.view_layer.objects.active = active_spotted

        if not operator and active_spotted:
            bpy.context.active_object.hide_viewport = False


def find_ultimate_parent_insert(obj, insert_collection):
    """
    Recursively finds the ultimate parent of an object.
    If the object has no parent, it returns the object itself.
    """
    if obj.parent is None or insert_collection not in obj.parent.users_collection:
        return obj
    else:
        return find_ultimate_parent_insert(obj.parent, insert_collection)

def find_all_children(parent, children_list):
    """
    Recursively finds all children of a given parent object.
    This function modifies the children_list in-place.
    """
    for child in parent.children:
        children_list.append(child)
        find_all_children(child, children_list)

def find_insert_objects(obj):
    """
    Finds the ultimate parent of the given object and all descendants.
    Returns a tuple containing the ultimate parent and a list of all children.
    """

    if obj.users_collection:
        # try and group these assuming the INSERT has a collection.#
        insert_collection = obj.users_collection[0]

        ultimate_parent = find_ultimate_parent_insert(obj, insert_collection)
        children_list = []
        find_all_children(ultimate_parent, children_list)
        return [ultimate_parent] + children_list
    else:
        inserts = collect([obj])
        return inserts




# DEPRECATED METHOD WILL DO NOTHING TODO remove if no issues are found.
def show_solid_objects():
    return

# DEPRECATED METHOD WILL DO NOTHING TODO remove if no issues are found.
def show_cutter_objects():
    return

# DEPRECATED METHOD WILL DO NOTHING TODO remove if no issues are found.
def show_wire_objects():
    return

def correct_ids():
    inserts = [obj for obj in bpy.data.objects if obj.kitops.insert]
    main_objects = [obj for obj in inserts if obj.kitops.main]
    
    ids = []
    correct = []
    for obj in main_objects:
        if obj.kitops.id not in ids:
            ids.append(obj.kitops.id)
        else:
            correct.append(obj)

    inserts = [obj for obj in bpy.data.objects if obj.kitops.insert]

    for main in correct:
        new_id = id.uuid()
        for obj in inserts:
            if obj.kitops.main_object == main:
                obj.kitops.id = new_id


def delete_hierarchy(obj_to_delete, target_obj=None):
    """Delete an object and it's hierarchy.""" #TODO move to helper class.

    correct_ids()

    if obj_to_delete is None or \
        (target_obj is not None and \
                obj_to_delete.kitops.reserved_target != target_obj):
        return

    objects_to_delete = [obj for obj in bpy.data.objects if obj is not None and obj.kitops.id == obj_to_delete.kitops.id]

    for obj in objects_to_delete:
        # find any boolean modifiers in all objects and remove the boolean.

        if target_obj is not None:
            for mod in target_obj.modifiers:
                if mod.type == 'BOOLEAN':
                    if mod.object == obj:
                        target_obj.modifiers.remove(mod)

        try:
            remove.object(obj, data=True)
        except: pass     #TODO better error handling needed.


def get_insert(id, parents_only=True):
    """Get an insert based on the id."""
    correct_ids()
    for obj in bpy.data.objects:
        if obj.kitops.id == id:
            if parents_only:
                if obj.parent is None:
                    return obj
            else:
                return obj
    return None


def origin_to_bottom(ob, use_verts=False):
    '''Set Origin of given object to the bottom of it'''
    me = ob.data
    mw = ob.matrix_world
    if use_verts:
        data = (v.co for v in me.vertices)
    else:
        data = (Vector(v) for v in ob.bound_box)

    coords = np.array([ob.matrix_world @ v for v in data])
    z = coords.T[2]
    mins = np.take(coords, np.where(z == z.min())[0], axis=0)

    o_world = Vector(np.mean(mins, axis=0))

    set_origin(ob, o_world)

def set_origin(ob, o_world):
    '''set origin of object to specified world point'''

    original_translation = ob.matrix_world.copy().translation

    o = ob.matrix_world.inverted() @ o_world

    me = ob.data
    mw = ob.matrix_world

    me.transform(Matrix.Translation(-o))

    mw.translation = mw @ o

    # recursively go through all direct children and offset their relative origins.
    for child in ob.children:
        # work out the change in offset in the child's local parent space and offset the local parent matrix accordingly.
        change_vec = child.matrix_parent_inverse @ original_translation - (child.matrix_parent_inverse @ o_world)
        child.matrix_local.translation += change_vec


def add_kitops_props(obj, main_obj=None, uuid=None):
    """Add kitops properties to an object and its children."""
    if main_obj is None:
        main_obj = obj
    if uuid is None:
        uuid = id.uuid()
    obj.kitops.id = uuid
    obj.kitops.insert = True
    obj.kitops.main_object = main_obj
    for child in obj.children:
        add_kitops_props(child, main_obj, uuid)
