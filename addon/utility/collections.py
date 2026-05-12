# Collection helper utilities.
import bpy

def init(context):
    """Initialize collections for inserts."""
    if 'INSERTS' not in bpy.data.collections:
        context.scene.collection.children.link(bpy.data.collections.new(name='INSERTS'))

    insert_collection_excluded = False
    for l in context.view_layer.layer_collection.children:
        if l.name == 'INSERTS':
            insert_collection_excluded = l.exclude
            l.exclude = False
            break

    for obj in bpy.data.objects:
        for modifier in obj.modifiers:
            if modifier.type == 'BOOLEAN' and not modifier.object:
                obj.modifiers.remove(modifier)

    return insert_collection_excluded


def exclude_insert_collection(context):
    """Exclude the INSERTs collection from the view layer"""
    for l in context.view_layer.layer_collection.children:
        if l.name == 'INSERTS':
            l.exclude = True
            break

def get_children_recursive(collection):
    '''recursively get children of a given collection'''
    all_children = []

    for child in collection.children:
        if child not in all_children:
            all_children.append(child)

    for child in collection.children:
        children = get_children_recursive(child)
        if len(children):
            all_children.extend(children)

    return all_children