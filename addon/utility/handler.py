import sys
import traceback

import bpy
from bpy.app.handlers import persistent, depsgraph_update_pre, depsgraph_update_post, load_pre, load_post, save_pre

from . import addon, insert, remove, update, smart

authoring_enabled = True
try: from . import matrixmath
except ImportError: authoring_enabled = False

# flag to determine whether we are saving or not.
is_saving = False
class pre:


    @persistent
    def depsgraph(none):
    
        global is_saving
        if is_saving:
            return


    @persistent
    def load(none):


        global is_saving
        if is_saving:
            return

    @persistent
    def save(none):

        global is_saving
        if is_saving:
            return

        option = addon.option()

        if authoring_enabled:
            matrixmath.authoring_save_pre()



class post:


    @persistent
    def depsgraph(none):

        global is_saving
        if is_saving:
            return

        preference = addon.preference()
        option = addon.option()

        if option.authoring_mode:
            option.authoring_mode = True
            if addon.preference().mode == 'SMART':
                addon.preference().mode = 'REGULAR'
            if authoring_enabled:
                matrixmath.authoring_depsgraph_update_post()

        scene = bpy.context.scene

        if not insert.operator and scene and hasattr(scene, 'kitops') and scene.kitops and not scene.kitops.thumbnail:
            for obj in [ob for ob in bpy.data.objects if ob.kitops.duplicate]:
                remove.object(obj, data=True, do_unlink=False)

        if not insert.operator:
            smart.toggles_depsgraph_update_post()


        # enable inserts if in local view mode
        if bpy.context.screen:
            for area in bpy.context.screen.areas:
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        inserts = [i for i in insert.collect(all=True) if i.kitops.insert_target == bpy.context.active_object]
                        for target_insert in inserts:
                            if space.local_view:
                                target_insert.local_view_set(space, True)


    @persistent
    def load(none):

        global is_saving
        if is_saving:
            return
            
        option = addon.option()

        option.authoring_mode = insert.authoring()

        if option.authoring_mode:
            if authoring_enabled:
                matrixmath.authoring_load_post()
            else:
                for obj in bpy.data.objects:
                    obj.kitops.applied = True
        
def register():
    depsgraph_update_pre.append(pre.depsgraph)
    depsgraph_update_post.append(post.depsgraph)
    load_pre.append(pre.load)
    load_post.append(post.load)
    save_pre.append(pre.save)


def unregister():
    depsgraph_update_pre.remove(pre.depsgraph)
    depsgraph_update_post.remove(post.depsgraph)
    load_pre.remove(pre.load)
    load_post.remove(post.load)
    save_pre.remove(pre.save)
