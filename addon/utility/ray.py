import traceback

import bpy
import bmesh

from mathutils import *
from mathutils.bvhtree import BVHTree as BVH

from . import view3d, addon, remove

success = bool()
location = Vector()
normal = Vector()
face_index = int()
to_track_quat = None
bm = None
bvh = None
target_obj = None
init_active_obj = None


authoring_enabled = True
try: from . import matrixmath
except ImportError: authoring_enabled = False


def cast(op):
    global success
    global location
    global normal
    global face_index
    global to_track_quat
    

    preference = addon.preference()

    matrix = op.duplicate.matrix_world.copy()

    ray_origin = matrix.inverted() @ view3d.mouse_origin(op)
    ray_direction = matrix.inverted().to_3x3() @ view3d.mouse_vector(op)

    location, normal, face_index, distance = bvh.ray_cast(ray_origin, ray_direction)

    if location and preference.flip_placement:
        # project to back of object.
        location, normal, face_index, distance = bvh.ray_cast(location + (0.001 * ray_direction), ray_direction)

    success = location != None

    if success:
        # new_location = None
        if preference.snap_mode != 'NONE':
            location, to_track_quat, normal = calc_location(op, normal, bm, face_index, location)
        else:
            location = op.duplicate.matrix_world @ location
            to_track_quat = op.duplicate.matrix_world.to_quaternion() @ normal.to_track_quat('Z', 'Y')
            normal = op.duplicate.matrix_world.to_3x3() @ normal

def flip_placement():
    global bm
    if bm:
        for f in bm.faces:
            f.normal_flip()

def refresh_bm(op):
    global bm
    if bm:
        bm.free()
    bm = bmesh.new()
    bm.from_mesh(op.duplicate.data)


def refresh_bvh():
    global bm
    global bvh
    bvh = None
    if bm:
        bvh = BVH.FromBMesh(bm)


def _set_up_obj(obj, name):

    if obj.type == "MESH":
        data = bpy.data.meshes.new_from_object(obj.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    elif obj.data:
        data = obj.data.copy()
    else:
        data = bpy.data.meshes.new(obj.name + ' Data')

    new_obj = bpy.data.objects.new(name, data)
    new_obj.kitops.duplicate = True
    new_obj.display_type = 'BOUNDS'
    new_obj.matrix_world = obj.matrix_world

    bpy.data.collections['INSERTS'].objects.link(new_obj)

    return new_obj

def make_duplicate(op):
    global bm
    global bvh
    global target_obj
    global init_active_obj

    # set up caches of the object and the active object.
    target_obj = _set_up_obj(op.boolean_target, 'KIT OPS Duplicate')

    if op.init_active != op.boolean_target:
        init_active_obj = _set_up_obj(op.init_active, 'KIT OPS Duplicate Insert')
    else:
        init_active_obj = target_obj

    refresh_duplicate(op)

def refresh_duplicate(op):
    global target_obj
    global init_active_obj
    global bm

    preference = addon.preference()

    if authoring_enabled and preference.place_on_insert:
        # use the selected object as the snap target.
        op.duplicate = init_active_obj
    else:
        # use the object as the target.
        op.duplicate = target_obj

    refresh_bm(op)
    if preference.flip_placement:
        flip_placement()
    refresh_bvh()

    bpy.context.view_layer.objects.active = op.duplicate

def free(op):
    global bm
    global bvh
    global target_obj
    global init_active_obj

    if bm:
        bm.free()
    if bvh:
        bvh = None
    
    try:
        if target_obj != op.duplicate:
            bpy.data.objects.remove(target_obj)
        elif init_active_obj != op.duplicate:
            bpy.data.objects.remove(init_active_obj)
    except ReferenceError:
        pass
    if op.duplicate:
        remove.object(op.duplicate,  data=True, do_unlink=True)


def calc_location(op, normal, bm, face_index, orig_location):
    '''calculate snap position'''
    preference = addon.preference()

    matrix_world = op.duplicate.matrix_world
    to_track_quat = matrix_world.to_quaternion() @ normal.to_track_quat('Z', 'Y')
    normal = matrix_world.to_3x3() @ normal

    if preference.snap_mode == 'FACE':
        # return location based on face.
        bm.faces.ensure_lookup_table()
        face = bm.faces[face_index]
        location = matrix_world @ face.calc_center_median()
        return location, to_track_quat, normal
    elif preference.snap_mode == 'EDGE':
        if preference.snap_mode_edge == 'NEAREST':
            # find nearest edge in face based on projection.
            bm.faces.ensure_lookup_table()
            face = bm.faces[face_index]
            new_location = matrix_world @ orig_location
            def point_on_edge(e):
                edge_vector = (matrix_world @ e.verts[0].co - matrix_world @ e.verts[1].co)
                point, _ = geometry.intersect_point_line(new_location, matrix_world @ e.verts[0].co, matrix_world @ e.verts[1].co)
                return point

            point_map = {}
            for e in face.edges:
                point_map[e.index] = point_on_edge(e)

            def closest_distance(key):
                point = point_map[key]
                return (new_location - point).length

            closest_index = min(point_map.keys(), key=closest_distance)

            return point_map[closest_index], to_track_quat, normal
        else:
            # find the nearest edge center.
            bm.faces.ensure_lookup_table()
            face = bm.faces[face_index]
            new_location = matrix_world @ orig_location
            def edge_center(e):
                edge_center = (matrix_world @ e.verts[0].co + matrix_world @ e.verts[1].co) / 2
                return edge_center

            edge_map = {}
            for e in face.edges:
                edge_map[e.index] = edge_center(e)

            def closest_distance(key):
                point = edge_map[key]
                return (new_location - point).length

            closest_index = min(edge_map.keys(), key=closest_distance)

            return edge_map[closest_index], to_track_quat, normal

    elif preference.snap_mode == 'VERTEX':
        # find nearest vertex in face.
        bm.faces.ensure_lookup_table()
        face = bm.faces[face_index]
        new_location = matrix_world @ orig_location
        def dist_to_vert(v):
            return (new_location - matrix_world @ v.co).length
        vertex = min(face.verts, key=dist_to_vert)
        return matrix_world @ vertex.co, to_track_quat, normal

    # just return the original location if we got this far.
    return matrix_world @ orig_location, to_track_quat, normal