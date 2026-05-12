# Copyright (C) 2018-2020 chippwalters, masterxeon1001 All Rights Reserved
bl_info = {
    'name': 'KIT OPS',
    'author': 'Chipp Walters, Mark Kingsnorth',
    'version': (3, 1, 5),
    'blender': (3, 0, 0),
    'location': 'View3D > Toolshelf (T)',
    'description': 'Streamlined kit bash library with additional productivity tools',
    'wiki_url': 'http://cw1.me/kitops3',
    "doc_url": "http://cw1.me/kitops3",
    'category': '3D View'}

from . addon.utility import handler, previews
from . addon.interface import operator, panel
from . addon import preference, property

def register():

    previews.register()
    preference.register()
    property.register()
    operator.register()
    panel.register()
    handler.register()


def unregister():

    handler.unregister()

    panel.unregister()
    operator.unregister()

    property.unregister()
    preference.unregister()

    previews.unregister()
 