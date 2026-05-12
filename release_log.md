# KIT OPS

## Release Log


### 3.0.0
- New Blender spawned when editing an INSERT.
- UI work: Moving general methods to Utils add-on, default collapse of panels.
- Introduced workflow changes to address performance issues.
- Bug fixes for slow downs on network drive access.
- Bug fixes for moving INSERT targets.
- Made the add-on also an extension for Blender 4.2
- Added ability to add KIT OPS props to any object and support for relocate and move.


### 2.26.0
    - Making Blender 4.0 changes.
    - Added Search KPACK feature.
    - Added buttons for Search results to open INSERT and rudimentary open Preferences button.

### 2.25.0

    - Added fix for asset library where assets were only processed if they were selected in the file.
    - Added ability to change insert target.
    - Fixed ordering bug for when the main object is a cutter and is not applied first.
    - Added fix for UNION inserts that were not displaying in render view.
    - Added bugfix seen in SYNTH when the insert locations are the same, KITOPS would think they are duplicates and try to add a boolean, causing a loop.
    - Added progress reporting for Asset processing.
    - Added "Open KPACK directory"
    - Changed layout of creatin buttons.
    - Added Catalog option on asset library conversion.
    - Switch Group Mode off automatically when editing an INSERT.
    - Move "Remove KIT OPS props" button to under "Edit Insert"
    - Remap "Create INSERT" and "Create Material" buttons so they match the right-click function
    - Purge recursive unused data blocks button (Tools section) under Remove Duplicate Materials
    - Moved snapping options to FREE

### 2.24.0+

- Added fixes for handling deleting objects in factory mode.
- Removed print checks in free mode.

### 2.24.0
- Added ability to add INSERTs in Local Mode (initial version before test)
- Made sure INSERT boolean modifiers on target object are duplicated only when the object is duplicated, still allowing user to delete the boolean modifier.
- Introduced Array option for INSERTs
- Added fix for Convert to Mesh on instanced objects.
- Added fix for Replace Inserts on instanced objects.
- Added changes to support KIT OPS BATCH material processing.
- Updated for 3.5 compatibility, changed handling of modifiers.
- Added Auto Remove Boolean modifier flag.
- Added "Check for Updates" button in preferences.

### 2.23.0
- Added Group Mode button instead of Smart mode
- Changed title to contain hearts

### 2.22.7
- Still fixing bug when object deleted but parent is none.

### 2.22.6
- Fixed bug when object deleted but parent is none.

### 2.22.5
- Fixed bug when insert is deleted but its parent remains.

### 2.22.4
- Disabled 'Use INSERT HARDPOINTS' feature.
- Restricted HARDPOINTS use to only be on Factory panel.

### 2.22.3
- Fixed bug when converting to Mesh in Smart mode.
- Reinstated 'Use INSERT HARDPOINTS' feature.

### 2.22.2
- Fixed bug when hardpoint is marked as main kitops object.
- Fixed bug when auto creating an object, only one main object is marked.
- Made Hardpoints panel open by default.
- Fixed bug when temporary duplicate is not removed when placing a hardpoint in factory mode.

### 2.22.1
- Bug Fix for deletion override (recursive collection not in Blender 3.0).

### 2.22.0
Initial version for Beta Test.

### 2.21.8 - 2.21.14
- Merge from Master

### 2.21.5
- Removed rotation of hardpoint in opposite direction.

### 2.21.4
- Fix on Convert to Mesh crash.

### 2.21.3
- Added further fixes for KIT OPS crash.

### 2.21.2
- Merge from Master branch for Hardpoints.

### 2.21.1
- Fixed placement bug when trying to offset by central cached object.

### 2.21.00
- Added initial implementation of HARDPOINTS

### 2.20.55
- Added fix for import error for linux users.7

### 2.20.54
- Added fix for select all runtime error.

### 2.20.53
- Added potential fix for boolean objects remaining as cutter even when deleted.

### 2.20.52
- Added cycles_visibility polyfiller fix for Blender 3.0.

### 2.20.51
- Added potential fix for erroneously deleting modifiers off of objects in the handler.

### 2.20.50
- Added initial implementation of Quick Create INSERT: Set object to bottom.

### 2.20.49
- Added Initial version of quick create INSERT code.

### 2.20.48
- Added initial capability for KIT OPS replacement of INSERTs.

### 2.20.47
- Bug fix for null check when auto scale is off.

### 2.20.46
- Added null checks to support BATCH.  This may need refactoring in the future (insert.add being used for multiple functions)


### 2.20.45
- Added potential fix for KIT OPS free crash bug.

### 2.20.44
- Added Smooth modifier to sort list.

### 2.20.43
- When adding a material, a material is now added to the active slot.

### 2.20.42
- Added fix for hdri not being removed in factory modes.
- Added fix (potential) for cutters being removed when thumbnail is rendered.

### 2.20.41
- Added auto packing when saving an INSERT in factory mode.

### 2.20.40
- Added fix for bug when separate material with same image is imported.

### 2.20.39
- Added warning message when adding an INSERT to another that does not have a target.

### 2.20.38
- Added fix for handling duplicate images in scene

### 2.20.37
- Rolled back "Remove INSERT properties if there is no target" feature.

### 2.20.36
- Moved menu item.

### 2.20.35
- Adding fix for INSERT relocate crashing Blender.

### 2.20.34
- Introducing Relocate INSERT feature

### 2.20.33
- Added fix for INSERT not being active object when placed after snap mode enabled.

### 2.20.32
- Fixed "remove wire" panel bug.

### 2.20.31
- Snap Mode will now snap to a selected object if the target is not selected.

### 2.20.30
- When adding an INSERT with no target, INSERT props will be removed.

### 2.20.29
- Fixed duplicate material in image bug.

### 2.20.28
- Introduction of INSERT replace feature

### 2.20.27
- Added same icon logic to category thumbnails as for favorites/recents.

### 2.20.26
- Removed Auto Save Preferences as this was causing wider issues.

### 2.20.25
- Added further UI improvements to Favorites and Recently Used.

### 2.20.24
- Added improvements to recently used anf favorites layout.

### 2.20.23
- Added fix for User Preferences bug when favorites were not saving.

### 2.20.22
- Increased favorite rows.

### 2.20.21
- Introduced fix for Blender 3 crash on Creation of INSERT.

### 2.20.20
- Removed labels from favorites

### 2.20.19
- Added favorites and recently used functionality.

### 2.20.18
- Fixed save INSERT bug where insert_name.blend was being saved if button clicked twice.

### 2.20.17
- Disabled show_solid_objects, show_cutter_objects, and show_wire_objects

### 2.20.16
- Fix for when adding INSERTs and no target selected.

### 2.20.15
- When Creating and INSERT/Material, the lscene will be saved (with warning to save if not saved at al).
- Refresh button on panel should remember previous INSERT setting.
- Fixed Deselected Object/Edit Insertion Bug.

### 2.20.14
- Fixed a crash bug reported on a Mac when Close Factory Scene is pressed.

### 2.20.13
- Allowed scale to remembered when adding an Insert.


### 2.20.12
- Added minor fix for 'render' error on Close Factory Scene.

### 2.20.11
- Introduced snap modes for Face/Edge/Vertex

### 2.20.10
- Changed sorting to only be for inserts, not folders

### 2.20.9
- Changed aut scale and parent parameters to be associated with Blender preferences.
- Added a sort to all enums so that they should sort alphabetically.

### 2.20.8
- Added initial version of snap-to-face feature.
- Removed 'Apply INSERT' feature.
- Removed 'Delete INSERT' feature.

### 2.20.7
- Added messaging to Preferences folder for thumbnail cache and automatically refresh KPACKs on Pillow install.

### 2.20.5
- Added Known Issue note about object removal call getting exponentially longer.

### 2.20.5
- Added further improvements to thumbnail caching.

### 2.20.4
- Disabled Pillow install button if already installed.

### 2.20.3
- Introduced Image Caching.

### 2.20.2
- Changed wording for adding an INSERT to include mouse scroll info.

### 2.20.1
- Changed panel target object layout.

### 2.20.00
- Made Smart Mode part of standard Free release; separated authoring code.

### 2.19.18
- Moved Auto Parent option to main panel.

### 2.19.17
- Fixed bug when adding an INSERT in auto scale mode and booleans are added.

### 2.19.16
- Removed references to auto scale in code.

### 2.19.15
- Added fix for magnitude error on shift click.

### 2.19.14
- Removed auto_add checkbox and made Smart Mode the same as Auto Select.

### 2.19.13
- In SMART mode, scale and rotation are maintained when shift+adding inserts.

### 2.19.12
- Added rotation ability when pressing ctrl key.

### 2.19.11
- Added efficiency saving for auto select

### 2.19.10

- Bug fix for active object not being reset when collections are rest.


### 2.19.9

#### Features
- Initial version of aligning insert rotation with target object rotation

### 2.19.8

#### Features
- Materials are now de-duplicated by default when adding an INSERT to the scene.
- Added fix for Open Scene factory bug, when an INSERT was being removed when thumbnail mode was closed.
- Cache thumbnails button created: Speed up KIT OPS by creating thumbnails.
- Search feature removed as although the functionality worked its value was limited
- Exposed ability to programmatically disable and re-enable Smart mode
- Added ability to parent INSERTs (Experimental, off by default)


