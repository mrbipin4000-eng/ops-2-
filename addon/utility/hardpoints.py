
import bpy
from math import radians, degrees
from mathutils import Vector, Matrix, Euler, Quaternion
from bpy_extras import view3d_utils


def get_hardpoints(obj): 
    return [hp for hp in _get_children(obj) if hp.kitops.is_hardpoint]

def get_tags(obj):
    if obj:
        return get_tags_from_str(obj.kitops.hardpoint_tags)
    return []

def get_tags_from_str(s):
    return [x.strip().lower() for x in s.split(',') if not s == '']

def get_hardpoints_from_tags(tags):
    hps = []
    for obj in bpy.data.objects:
        if obj.kitops.is_hardpoint:
            hardpoint_tags = get_tags_from_str(obj.kitops.hardpoint_tags)
            for tag in tags:
                for hardpoint_tag in hardpoint_tags:
                    if tag == hardpoint_tag:
                        hps.append(obj)

    return hps

def intersecting_tags(tags1, tags2):
    return list(set(tags1) & set(tags2))

def offset_by_hardpoint(context, insert_obj, insert_hardpoint):



    # ok, let's offset the insert to this hardpoint.
    context.view_layer.update()
    
    # determine the difference in rotation.
    up_vec_insert = Vector((0,0,1))
    up_vec_insert.rotate(insert_obj.matrix_world.to_euler())

    up_vec_insert_hp = Vector((0,0,-1))
    up_vec_insert_hp.rotate(insert_hardpoint.matrix_world.to_euler())

    rotation_difference = up_vec_insert.rotation_difference(up_vec_insert_hp)
    # this would be the opposite of rotation, to get back to the original object.
    insert_obj.rotation_mode = 'QUATERNION'
    insert_obj.rotation_quaternion.rotate(rotation_difference.conjugated())

    context.view_layer.update()

    # work out distance offset for hardpoint
    distance_offset = (insert_obj.matrix_world.to_translation()) - \
                        (insert_hardpoint.matrix_world.to_translation())

    insert_obj.matrix_world.translation = insert_obj.matrix_world.to_translation() + distance_offset


def _get_children(obj): 
    children = [] 
    for ob in bpy.data.objects: 
        if ob.parent == obj: 
            children.append(ob) 
    return children 


def get_nearest_hardpoint(context, point, insert_hardpoints):
    hp_screen_points = []
    for hardpoint in insert_hardpoints:
        loc_3d = hardpoint.matrix_world.to_translation()
        view2d_co = view3d_utils.location_3d_to_region_2d(context.region, \
                            context.space_data.region_3d, \
                            loc_3d)
        hp_screen_points.append((hardpoint, view2d_co))

    def dist_to_hp(hp_tuple):
        if point and hp_tuple[1]:
            return (point - hp_tuple[1]).length
        return 0

    nearest_hardpoint_tuple = min(hp_screen_points, key=dist_to_hp)
    insert_hardpoint_obj = nearest_hardpoint_tuple[0]

    return insert_hardpoint_obj 