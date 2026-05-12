# Utility methods for saving INSERT data.
import bpy
import os
import re
from . import addon, id, modifier, handler, remove


authoring_enabled = True
try: from . import matrixmath
except ImportError: authoring_enabled = False


create_type_items = [
        ('INSERT', 'INSERT', 'Create an Object INSERT'),
        ('MATERIAL', 'MATERIAL', 'Create a Material INSERT'),
        ('GEO_NODES', 'GEO_NODES', 'Create a Geometry Nodes INSERT'),
        ('SHADER_NODES', 'SHADER_NODES', 'Create a Shader Nodes INSERT')
    ]

def insert_path(insert_name, context, directory=None):
    file_name = '_'.join(insert_name.split(' ')) + '.blend'
    if not directory:
        directory = directory_from(context.window_manager.kitops.kpack)        
    return os.path.join(directory, file_name)

def insert_thumb_path(insert_name, insert_type, context, directory):

    insert_suffix = insert_thumb_suffix(insert_type)

    file_name = '_'.join(insert_name.split(' ')) + insert_suffix + '.png'
    if not directory:
        directory = directory_from(context.window_manager.kitops.kpack)
    return os.path.join(directory, file_name)


def insert_thumb_suffix(insert_type):
    insert_suffix = '-0'

    if insert_type == 'MATERIAL':
        insert_suffix = '-1'
    elif insert_type == 'GEO_NODES':
        insert_suffix = '-2'
    elif insert_type == 'SHADER_NODES':
        insert_suffix = '-3'
    elif insert_type == 'DECAL':
        insert_suffix = '-4'

    return insert_suffix

def link_object_to(bpy_type, obj, children=False):
    if children:
        for child in obj.children:
            link_object_to(bpy_type, child, children=True)

    if hasattr(bpy_type, 'collection') and obj.name not in bpy_type.collection.all_objects:
        bpy_type.collection.objects.link(obj)

        return

    if obj.name not in bpy_type.objects:
        bpy_type.objects.link(obj)

def directory_from(kpack):
    if not kpack.categories:
        bpy.ops.mesh.ko_refresh_kpacks()
    try:
        current = kpack.categories[kpack.active_index]
        return os.path.realpath(os.path.dirname(current.blends[current.active_index].location))
    except IndexError:
        return None


def bool_objects(obj):
    bools = []
    for mod in obj.modifiers:
        if mod.type != 'BOOLEAN' or not mod.object:
            continue
        bools.append(mod.object)
        for ob in bool_objects(mod.object):
            bools.append(ob)

    return list(set(bools))

def create_snapshot(self, context, path):
    original_path = context.scene.render.filepath

    if not path:
        self.report({'WARNING'}, 'Unable to save rendered thumbnail, no reference PATH (Save your file first?)')
        return {'FINISHED'}

    # Match and remove suffix like -0.png to -4.png
    match = re.match(r"^(.*)-([0-4])\.png$", os.path.basename(path))
    if match:
        base_filename = match.group(1)
        directory = os.path.dirname(path)

        # Delete all matching files from -0.png to -4.png
        for i in range(5):
            test_file = os.path.join(directory, f"{base_filename}-{i}.png")
            if os.path.exists(test_file):
                try:
                    os.remove(test_file)
                except Exception as e:
                    self.report({'WARNING'}, f'Could not delete {test_file}: {e}')

    # Ensure a camera is set
    if not context.scene.camera:
        for obj in context.scene.collection.all_objects:
            if getattr(obj, "kitops", None) and getattr(obj.kitops, "temp", False) and obj.type == 'CAMERA':
                context.scene.camera = obj
                break

    context.scene.render.filepath = path

    render_mode = context.scene.kitops.render_mode
    old_render_engine = context.scene.render.engine
    try:
        if render_mode == 'CYCLES':
            context.scene.render.engine = 'CYCLES'
            bpy.ops.render.render(write_still=True)
        elif render_mode == 'EEVEE':
            if bpy.app.version < (4, 2, 0) or bpy.app.version >= (5, 0, 0):
                context.scene.render.engine = 'BLENDER_EEVEE'
            else:
                context.scene.render.engine = 'BLENDER_EEVEE_NEXT'
            bpy.ops.render.render(write_still=True)
        elif render_mode == 'OPENGL':
            bpy.ops.render.opengl(write_still=True)
    finally:
        context.scene.render.engine = old_render_engine

    context.scene.render.filepath = original_path

    return {'FINISHED'}

def remove_object(obj, log=True): # TODO dupe method in smart
    collection_lookup = {
        "ARMATURE": bpy.data.armatures,
        "CAMERA": bpy.data.cameras,
        "CURVE": bpy.data.curves,
        "FONT": bpy.data.curves,
        "GPENCIL": bpy.data.grease_pencils,
        "LATTICE": bpy.data.lattices,
        "LIGHT": bpy.data.lights,
        "LIGHT_PROBE": bpy.data.lightprobes,
        "MESH": bpy.data.meshes,
        "SPEAKER": bpy.data.speakers,
        "SURFACE": bpy.data.curves,
        "VOLUME": bpy.data.volumes}

    if obj.type in collection_lookup:
        if log:
            print(F'        KITOPS: Removing {obj.type.lower()} datablock: {obj.data.name}')
        try:
            collection_lookup[obj.type].remove(obj.data)
        except ReferenceError:
            pass

    if obj in bpy.data.objects[:]:
        if log:
            print(F'        KITOPS: Removing object datablock: {obj.name}')
        try:
            bpy.data.objects.remove(obj)
        except ReferenceError:
            pass




def remove_temp_objects(duplicates=False, log=True):
    if log:
        print('')
    # material_base = False
    for obj in bpy.data.objects:
        # if not material_base and obj.kitops.material_base:
        #     material_base = True
        if obj.data and hasattr(obj.data, 'materials'):
            for mat in obj.data.materials:
                if mat and 'KITOPS FACTORY' in mat.name:
                    if log:
                        print(F'        KITOPS: Removing material datablock: {mat.name}')
                    try:
                        bpy.data.materials.remove(mat)
                    except ReferenceError:
                        pass


        if obj.kitops.temp or (duplicates and (obj.kitops.duplicate or obj.kitops.bool_duplicate)) or 'KITOPS FACTORY' in obj.name or obj.kitops.material_base:
            if log:
                print(F'        KITOPS: Removing object datablock: {obj.name}')
            remove_object(obj, log=log)

            continue
    
    factory_worlds = [w for w in bpy.data.worlds if w.kitops.is_factory_scene]
    for world in factory_worlds:
        try:
            bpy.data.worlds.remove(world)
        except ReferenceError:
            pass
    factory_images = [img for img in bpy.data.images if img.kitops.is_factory_scene]
    for img in factory_images:
        try:
            bpy.data.images.remove(img)
        except ReferenceError:
            pass


    if bpy.app.version > (2, 83, 0):
        for lib in bpy.data.libraries:
            if lib.filepath in {addon.path.material()}:
                try:
                    bpy.data.libraries.remove(lib)
                except ReferenceError:
                    pass

def new_factory_scene(context, insert_type, link_selected=False, link_children=False, duplicate=False, apply_all_materials=True):
    # global original_materials
    preference = addon.preference()
    path = addon.path.thumbnail(insert_type)

    strip_num = lambda string: string.rstrip('0123456789.') if len(string.split('.')) == 2 else string

    context.window_manager.kitops.author = preference.author

    original = bpy.data.scenes[context.scene.name]
    active_name = context.active_object.name

    # record whether this was a wire object as we will automatically make this a cutter later
    was_wire = context.active_object.display_type == 'WIRE'

    material = context.active_object.active_material
    materials = [slot.material for slot in context.active_object.material_slots if slot.material] if apply_all_materials else [material]

    insert = []
    bools = []

    if insert_type in {'INSERT', 'GEO_NODES'}:
        for obj in context.selected_objects[:]:
            insert.append(obj)
            insert.extend(bool_objects(obj))
            bools.extend(bool_objects(obj))

            # if hasattr(obj, 'material_slots'):
            #     original_materials[obj.name] = [slot.material.name for slot in obj.material_slots if slot.material]

        for obj in insert:
            insert.extend([o for o in bpy.data.objects if o.parent == obj])

        # for obj in bpy.data.objects:
        #     if obj.parent in context.visible_objects[:]:
        #         insert.append(obj)

    insert = sorted(list(set(insert)), key=lambda o: o.name)
    bools = sorted(bools, key=lambda o: o.name)

    with bpy.data.libraries.load(path) as (blend, imported):
        imported.scenes = blend.scenes
        imported.objects = blend.objects
        imported.images = blend.images
        imported.worlds = blend.worlds

    if 'KITOPS FACTORY Box' in bpy.data.objects:
        if insert_type in {'INSERT', 'GEO_NODES'}:
            remove_object(bpy.data.objects['KITOPS FACTORY Box'])

    objects = imported.objects[:]
    images = imported.images[:]
    worlds = imported.worlds[:]
    scene = imported.scenes[0]

    preference = addon.preference()
    scene.kitops.render_mode = preference.default_render_mode

    scene.name = 'KITOPS FACTORY'
    scene.kitops.factory = True
    scene.kitops.thumbnail = True
    context.window.scene = scene

    context.scene.kitops.last_edit = ''

    for obj in objects:
        try:
            obj.kitops.is_factory_scene = True
            obj.kitops.id = ''
            obj.kitops.insert = False
            obj.kitops.main = False
            obj.kitops.temp = True
            obj.select_set(False)

            is_material = False
            if  insert_type in {'MATERIAL', 'SHADER_NODES'}:
                if obj.kitops.material_base or obj.name in {'Base'}:
                    is_material = True

            if is_material:

                obj.name = obj.name.replace('KITOPS FACTORY ', '')

                obj.kitops.temp = False
                link_object_to(scene, obj)
                if obj.kitops.material_base:
                    context.view_layer.objects.active = obj
                    context.window_manager.kitops.insert_name = material.name

                    # remove the material called 'replace_me' and replace it with the active material
                    target_name = "KITOPS FACTORY replace_me"
                    mat = bpy.data.materials.get(target_name)                    

                    slots_to_remove = [i for i, slot in enumerate(obj.material_slots) if slot.material and slot.material.name == target_name]
                    for i in reversed(slots_to_remove):  # Reverse to avoid index shifting
                        obj.active_material_index = i
                        bpy.ops.object.material_slot_remove()
            
                    # If the material exists and is unused elsewhere, remove it from the .blend file
                    if mat and not mat.users:
                        bpy.data.materials.remove(mat)

                    for mat in materials:
                        mat.kitops.id = id.uuid()
                        mat.kitops.material = True
                        obj.data.materials.append(mat)
        except ReferenceError:
            pass

    for image in images:
        image.kitops.is_factory_scene = True

    for world in worlds:
        world.kitops.is_factory_scene = True

    if link_selected:
        for obj in insert:
            link_object_to(scene, obj)
            obj.hide_set(False)
            obj.kitops.duplicate = duplicate

            if obj in bools:
                obj.kitops.duplicate = duplicate
                if not duplicate:
                    if authoring_enabled:
                        obj.kitops.type = 'CUTTER'
                        obj.kitops.boolean_type = 'INSERT'
                else:
                    obj.kitops.bool_duplicate = True

            for ob in bpy.data.objects:
                if not hasattr(ob, 'modifiers'):
                    continue

                for mod in ob.modifiers:
                    if mod.type != 'BOOLEAN' or mod.object != obj or mod.object not in insert or mod.object in bools:
                        continue
                    
                    if authoring_enabled:
                        mod.object.kitops.type = 'CUTTER'

            if obj.name == active_name:
                context.view_layer.objects.active = obj
                obj.kitops.main = True

    for obj in context.visible_objects:
        if not obj.kitops.temp or obj.kitops.material_base:
            obj.select_set(True)

    if duplicate:
        # we need to stop the handler from firing when we are duplicating so that object visibility is not affected.
        old_is_saving = handler.is_saving
        handler.is_saving = True
        bpy.ops.object.duplicate()
        handler.is_saving = old_is_saving

        for obj in insert:
            obj.kitops.duplicate = False

        for obj in bools:
            obj.kitops.duplicate
            obj.kitops.bool_duplicate = False

        # objs_to_delete = list(set(insert + bools))
        # for o_to_delete in objs_to_delete:
        #     remove.object(o_to_delete)
        #     bpy.objects.data.remove(o_to_delete)
        old_selected = context.selected_objects
        for old_selected_obj in old_selected:
            old_selected_obj.select_set(False)
        objs_to_delete = list(set(insert + bools))
        for obj_to_delete in objs_to_delete:
            obj_to_delete.select_set(True)
        bpy.ops.object.delete()
        for old_selected_obj in old_selected:
            try:
                old_selected_obj.select_set(True)
            except ReferenceError:
                pass

        duplicates = [obj for obj in scene.collection.all_objects if not obj.kitops.temp]
        bases = [obj for obj in duplicates if not obj.kitops.bool_duplicate]

        for obj in duplicates:
            obj.kitops.duplicate = False
            if obj.parent in insert:
                for ob in bases:
                    for mod in ob.modifiers:
                        if mod.type != 'BOOLEAN' or not mod.object or mod.object != obj:
                            continue

                        obj['parent'] = ob

            if obj.kitops.bool_duplicate:
                if authoring_enabled:
                    obj.kitops.type = 'CUTTER'
                    obj.kitops.boolean_type = 'INSERT'
            elif obj.kitops.type != 'CUTTER':
                obj.kitops.type = 'SOLID'
            else:
                if authoring_enabled:
                    obj.kitops.type = 'CUTTER'

            if hasattr(obj, 'data') and obj.data:
                old_data = obj.data
                obj.data = obj.data.copy()
                if old_data.users == 0:
                    if old_data.name in bpy.data.meshes:
                        bpy.data.meshes.remove(old_data)
                    elif old_data.name in bpy.data.curves:
                        bpy.data.curves.remove(old_data)

            if strip_num(obj.name) == active_name:
                context.view_layer.objects.active = obj

            obj.kitops.bool_duplicate = False

        del insert
        del bools
        del duplicates
        del bases

    for obj in context.visible_objects:
        if not obj.kitops.temp or obj.kitops.material_base:
            obj.select_set(True)

    for obj in context.scene.collection.all_objects:
        if obj.kitops.temp and obj.type == 'CAMERA':
            context.scene.camera = obj

    # if this was a cutter then adjust scene accordingly.
    if was_wire:
        if context.active_object and authoring_enabled and not context.active_object.kitops.is_hardpoint:
            matrixmath.calc_cutter(context.active_object)
        if active_name in bpy.data.objects:
            bpy.data.objects[active_name].display_type = 'WIRE'

    scene.kitops.original_scene = original.name
    return original, scene

def set_active_category_from_last_edit(context, previous_set=None):

    bpy.ops.mesh.ko_refresh_kpacks()
    option = context.window_manager.kitops
    if previous_set:
        kpack_set = previous_set
    else:
        kpack_set = context.window_manager.kitops.kpack_set
    kpack = context.window_manager.kitops.kpack
    for ic, category in enumerate(kpack.categories):
        for ib, blend in enumerate(category.blends):
            if os.path.realpath(blend.location) != context.scene.kitops.last_edit:
                continue
            option.kpack_set = kpack_set
            option.kpacks = category.name
            option.kpack.active_index = ic
            current = option.kpack.categories[category.name]
            current.active_index = ib
            current.thumbnail = blend.name

            break


def save_insert(path='', objects=[]):
    context = bpy.context

    path = insert_path(context.window_manager.kitops.insert_name, context) if not path else path

    path = os.path.realpath(path)

    scene = bpy.data.scenes.new(name='main')
    scene.kitops.animated = context.scene.kitops.animated

    objs = objects if objects else [obj for obj in context.scene.collection.all_objects if not obj.kitops.temp]

    was_duplicate = False

    for obj in objs:
        link_object_to(scene, obj)

        obj.kitops.id = ''
        obj.kitops.author = context.window_manager.kitops.author
        obj.kitops.insert = False
        obj.kitops.applied = False
        obj.kitops.animated = scene.kitops.animated

        # set rotation type to EULER if it is not already
        if hasattr(obj, 'rotation_mode'):
            obj.rotation_mode = 'XYZ'

        def safe_clear_property(bj, property_name):
            if property_name in obj.kitops and obj.kitops[property_name]:
                try:
                    obj.kitops[property_name].clear()
                except AttributeError:
                    try:
                        obj.kitops[property_name] = None
                    except Exception:
                        pass

        safe_clear_property(obj, 'insert_target')
        safe_clear_property(obj, 'mirror_target')
        safe_clear_property(obj, 'reserved_target')
        safe_clear_property(obj, 'main_object')
        


        if obj.kitops.duplicate:
            was_duplicate = True
            obj.kitops.duplicate = False

        if hasattr(obj, 'data') and obj.data:
            obj.data.kitops.id = id.uuid()
            obj.data.kitops.insert = False

        # if hasattr(obj, 'data') and obj.data and hasattr(obj.data, 'materials'):
            # for mat in obj.data.materials:
        if hasattr(obj, 'material_slots'):
            for slot in obj.material_slots:
                if slot.material and 'KITOPS FACTORY' in slot.material.name:
                    obj.active_material_index = 0
                    for _ in range(len(obj.material_slots)):
                        old_active = context.view_layer.objects.active
                        context.view_layer.objects.active = obj
                        bpy.ops.object.material_slot_remove()
                        context.view_layer.objects.active = old_active

                    break

        if obj.kitops.material_base:
            obj.kitops.material_base = False
            for slot in reversed(obj.material_slots[:]):
                if slot.material and slot.material.name.rstrip('0123456789.') == 'Material':
                    slot.material.name = context.window_manager.kitops.insert_name

    try:
        bpy.ops.file.pack_all()
    except Exception as e:
        pass

    # delete file if it exists
    if os.path.exists(path):
        os.remove(path)

    bpy.data.libraries.write(path, {scene}, compress=True)
    import subprocess
    subprocess.Popen([bpy.app.binary_path, '-b', path, '--python', os.path.join(addon.path(), 'addon', 'utility', 'save.py')])

    bpy.data.scenes.remove(scene)

    for obj in objs:
        obj.kitops.type = obj.kitops.type
        if was_duplicate:
            obj.kitops.duplicate = True

    context.scene.kitops.last_edit = path
    option = addon.option()
    previous_set = option.kpack_set
    bpy.ops.mesh.ko_refresh_kpacks()
    set_active_category_from_last_edit(context, previous_set=previous_set)
    




def close_factory_scene(self, context, log=True):
    try: original_scene = bpy.data.scenes[context.scene.kitops.original_scene]
    except: original_scene = None

    if not original_scene:
        context.scene.name = 'Scene'
        context.scene.kitops.factory = False
        remove_temp_objects(log=False)
        return {'FINISHED'}

    remove_temp_objects(duplicates=True, log=False)

    if original_scene:
        to_remove = []
        for obj in bpy.data.scenes[context.scene.name].collection.all_objects:
            delete=True
            for scene in bpy.data.scenes:
                if scene.name != context.scene.name and obj.name in scene.collection.all_objects:
                    delete = False
                    break
            if delete:
                to_remove.append(obj)
        for obj in to_remove:
            remove_object(obj, log=log)
        bpy.data.scenes.remove(bpy.data.scenes[context.scene.name])
        context.window.scene = original_scene
    
    bpy.ops.outliner.orphans_purge()
    return {'FINISHED'}



class update:

    def author(prop, context):
        if not hasattr(context, 'active_object'):
            return

        for obj in bpy.data.objects:
            obj.kitops.author = context.active_object.kitops.author

    def type(prop, context):
        all_objects = [i for i in context.scene.collection.all_objects]
        
        try: ground_box = [obj for obj in all_objects if obj.kitops.ground_box][0]
        except: ground_box = None # ground box not detected

        for obj in all_objects:
            if obj.kitops.type == 'SOLID' or obj.type == 'GPENCIL':
                
                if not obj.kitops.is_hardpoint:
                    obj.display_type = 'SOLID' if obj.type != 'GPENCIL' else 'TEXTURED'


                if obj.type == 'MESH':
                    obj.hide_render = False



                    if hasattr(obj, 'cycles_visibility'):
                        obj.cycles_visibility.camera = True
                        obj.cycles_visibility.diffuse = True
                        obj.cycles_visibility.glossy = True
                        obj.cycles_visibility.transmission = True
                        obj.cycles_visibility.scatter = True
                        obj.cycles_visibility.shadow = True

                    if hasattr(obj, 'visible_camera'):
                        obj.visible_camera = True

                    if hasattr(obj, 'visible_diffuse'):
                        obj.visible_diffuse = True

                    if hasattr(obj, 'visible_glossy'):
                        obj.visible_glossy = True

                    if hasattr(obj, 'visible_transmission'):
                        obj.visible_transmission = True

                    if hasattr(obj, 'visible_volume_scatter'):
                        obj.visible_volume_scatter = True

                    if hasattr(obj, 'visible_shadow'):
                        obj.visible_shadow = True

            elif (obj.kitops.type == 'WIRE' or obj.kitops.type == 'CUTTER') and obj.type == 'MESH':
                obj.display_type = 'WIRE'

                visibility = obj.kitops.boolean_type == 'UNION'
                obj.hide_render = not visibility

                

                if hasattr(obj, 'cycles_visibility'):
                    obj.cycles_visibility.camera = visibility
                    obj.cycles_visibility.diffuse = visibility
                    obj.cycles_visibility.glossy = visibility
                    obj.cycles_visibility.transmission = visibility
                    obj.cycles_visibility.scatter = visibility
                    obj.cycles_visibility.shadow = visibility

                if hasattr(obj, 'visible_camera'):
                    obj.visible_camera = visibility

                if hasattr(obj, 'visible_diffuse'):
                    obj.visible_diffuse = visibility

                if hasattr(obj, 'visible_glossy'):
                    obj.visible_glossy = visibility

                if hasattr(obj, 'visible_transmission'):
                    obj.visible_transmission = visibility

                if hasattr(obj, 'visible_volume_scatter'):
                    obj.visible_volume_scatter = visibility

                if hasattr(obj, 'visible_shadow'):
                    obj.visible_shadow = visibility



        if ground_box and context.scene.kitops.factory:
            mats = [slot.material for slot in ground_box.material_slots if slot.material]
            for obj in sorted(all_objects, key=lambda o: o.name):
                if obj.kitops.temp or obj.type != 'MESH' or obj.kitops.material_base or obj.kitops.duplicate:
                    continue

                boolean = None
                for mod in ground_box.modifiers:
                    if mod.type == 'BOOLEAN' and mod.object == obj and obj.kitops.boolean_type != 'INSERT':
                        mod.show_viewport = obj.kitops.type == 'CUTTER' and obj.kitops.boolean_type != 'INSERT'
                        mod.show_render = mod.show_viewport
                        mod.operation = obj.kitops.boolean_type
                        boolean = mod

                if not boolean:
                    if obj.kitops.boolean_type != 'INSERT':

                        mod = ground_box.modifiers.new(name='KITOPS Boolean', type='BOOLEAN')
                        mod.object = obj
                        mod.operation = obj.kitops.boolean_type

                        if hasattr(mod, 'solver'):
                            mod.solver = addon.preference().boolean_solver

                        boolean = mod
                        modifier.sort(ground_box)

                if not obj.material_slots:
                    obj.data.materials.append(ground_box.material_slots[3].material)

                if not obj.material_slots or obj.material_slots[0].material in mats:
                    if obj.kitops.boolean_type == 'UNION':
                        boolean.operation = 'UNION'
                        obj.material_slots[0].material = ground_box.material_slots[1].material

                    elif obj.kitops.boolean_type == 'DIFFERENCE':
                        boolean.operation = 'DIFFERENCE'
                        obj.material_slots[0].material = ground_box.material_slots[2].material

                    else:
                        boolean.operation = 'INTERSECT'

                    if obj.kitops.type != 'CUTTER' or obj.kitops.boolean_type in {'INTERSECT', 'INSERT'}:
                        obj.material_slots[0].material = ground_box.material_slots[3].material
