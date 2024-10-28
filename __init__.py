bl_info = {
    "name": "Karamove - Texture Drawing",
    "author": "Tommy Lahitte",
    "version": (1, 5),
    "blender": (2, 80, 0),
    "location": "3D View > Sidebar > Karamove Texture",
    "description": "This addon, developed for the 9th edition of Karamove, is part of an interactive installation where children and artists can draw directly on the UV texture of 3D objects and see their artwork come to life in real-time within Blender.",
    "category": "Object",
}

import bpy
import os
import json
import threading
import time
import platform
import subprocess
from datetime import datetime

# Global variables
addon_data = {}
timer_running = False

def get_project_json_file_path():
    # Get the path to the project directory
    project_directory = bpy.path.abspath("//")
    if not project_directory:
        # Project directory is empty, .blend file not saved yet
        return None
    # Construct the path to the JSON file
    json_file_path = os.path.join(project_directory, "karamove_texture_drawing_data.json")
    return json_file_path

def load_addon_data():
    """
    Load addon data from the JSON file and apply settings to the scene and objects.
    """
    global addon_data
    json_file_path = get_project_json_file_path()
    addon_data = {}
    if json_file_path and os.path.exists(json_file_path):
        try:
            with open(json_file_path, 'r') as f:
                addon_data.update(json.load(f))
        except Exception as e:
            print(f"Failed to load addon data: {e}")

    # Ensure all required keys are present
    addon_data.setdefault("objects", [])
    addon_data.setdefault("selected_object", None)
    addon_data.setdefault("auto_refresh", False)
    addon_data.setdefault("refresh_interval", 5)
    addon_data.setdefault("review_pending", False)
    addon_data.setdefault("review_image_path", "")
    addon_data.setdefault("object_states", {})
    addon_data.setdefault("object_settings", {})

    # Apply settings to scene
    try:
        scene = bpy.context.scene
        scene.karamove_texture_auto_refresh = addon_data.get("auto_refresh", False)
        scene.karamove_texture_refresh_interval = addon_data.get("refresh_interval", 5)
    except Exception as e:
        print(f"Context not available: {e}")

    # Load object settings
    for obj_name, settings in addon_data.get("object_settings", {}).items():
        obj = bpy.data.objects.get(obj_name)
        if obj:
            obj.karamove_settings.default_texture = settings.get("default_texture", 'None')
            obj.karamove_settings.alpha_texture = settings.get("alpha_texture", 'None')
            # Update material to reflect loaded settings
            create_material_for_object(obj)

def save_addon_data():
    """
    Save addon data to the JSON file, including scene settings and object settings.
    """
    try:
        scene = bpy.context.scene
        addon_data["auto_refresh"] = scene.karamove_texture_auto_refresh
        addon_data["refresh_interval"] = scene.karamove_texture_refresh_interval

        # Save object settings
        object_settings = {}
        for obj_name in addon_data.get("objects", []):
            obj = bpy.data.objects.get(obj_name)
            if obj:
                object_settings[obj_name] = {
                    "use_default_texture": addon_data.get("object_states", {}).get(obj_name, {}).get("use_default_texture", True),
                    "default_texture": obj.karamove_settings.default_texture,
                    "alpha_texture": obj.karamove_settings.alpha_texture,
                }
        addon_data["object_settings"] = object_settings

        json_file_path = get_project_json_file_path()
        if json_file_path:
            with open(json_file_path, 'w') as f:
                json.dump(addon_data, f)
    except Exception as e:
        print(f"Failed to save addon data: {e}")

def get_addon_preferences():
    # Get addon preferences
    return bpy.context.preferences.addons[__name__].preferences

def get_image_enum_items(self, context):
    # Get list of images for dropdown menus
    items = [('None', 'None', 'No texture')]
    for img in bpy.data.images:
        items.append((img.name, img.name, ""))
    return items

def update_object_material(self, context):
    # Update material when object settings change
    obj = self.id_data
    if obj is not None and obj.type == 'MESH':
        create_material_for_object(obj)

class KaramoveObjectSettings(bpy.types.PropertyGroup):
    # Property group to store object-specific settings
    default_texture: bpy.props.EnumProperty(
        name="Default Texture",
        description="Select default texture",
        items=get_image_enum_items,
        update=update_object_material
    )
    alpha_texture: bpy.props.EnumProperty(
        name="Alpha Texture",
        description="Select alpha texture",
        items=get_image_enum_items,
        update=update_object_material
    )

def create_material_for_object(obj):
    """
    Create or update the material for the given object.

    The material uses two Principled BSDF shaders connected to a Mix Shader,
    allowing switching between the default texture and the imported texture.
    """
    mat_name = "Mat_" + obj.name
    mat = bpy.data.materials.get(mat_name)
    if not mat:
        # Create a new material
        mat = bpy.data.materials.new(name=mat_name)
        mat.use_nodes = True
        if obj.data.materials:
            obj.data.materials[0] = mat
        else:
            obj.data.materials.append(mat)

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    # Get object settings
    default_texture_name = obj.karamove_settings.default_texture
    alpha_texture_name = obj.karamove_settings.alpha_texture

    # Create nodes
    output_node = nodes.new(type='ShaderNodeOutputMaterial')
    output_node.location = (800, 0)

    mix_shader = nodes.new(type='ShaderNodeMixShader')
    mix_shader.location = (600, 0)

    # Principled BSDF for Default Texture
    default_principled = nodes.new(type='ShaderNodeBsdfPrincipled')
    default_principled.location = (400, 100)
    default_principled.inputs['Roughness'].default_value = 1.0
    default_principled.inputs['IOR'].default_value = 1.0

    if default_texture_name != 'None' and default_texture_name in bpy.data.images:
        default_image = bpy.data.images[default_texture_name]
        default_tex_node = nodes.new(type='ShaderNodeTexImage')
        default_tex_node.location = (200, 200)
        default_tex_node.image = default_image
        links.new(default_tex_node.outputs['Color'], default_principled.inputs['Base Color'])
    else:
        default_principled.inputs['Base Color'].default_value = (1, 1, 1, 1)  # White color

    # Principled BSDF for Imported Texture
    imported_principled = nodes.new(type='ShaderNodeBsdfPrincipled')
    imported_principled.location = (400, -100)
    imported_principled.inputs['Roughness'].default_value = 1.0
    imported_principled.inputs['IOR'].default_value = 1.0

    imported_tex_node = nodes.new(type='ShaderNodeTexImage')
    imported_tex_node.location = (200, -100)
    # Keep the image as is or create a new blank image
    image_name = "T_" + obj.name
    image = bpy.data.images.get(image_name)
    if not image:
        image = bpy.data.images.new(name=image_name, width=1024, height=1024, alpha=True)
    imported_tex_node.image = image

    # Link nodes
    links.new(imported_tex_node.outputs['Color'], imported_principled.inputs['Base Color'])
    links.new(default_principled.outputs['BSDF'], mix_shader.inputs[1])
    links.new(imported_principled.outputs['BSDF'], mix_shader.inputs[2])
    links.new(mix_shader.outputs['Shader'], output_node.inputs['Surface'])

    # Handle Alpha Texture
    if alpha_texture_name != 'None' and alpha_texture_name in bpy.data.images:
        alpha_image = bpy.data.images[alpha_texture_name]
        alpha_tex_node = nodes.new(type='ShaderNodeTexImage')
        alpha_tex_node.location = (200, 50)
        alpha_tex_node.image = alpha_image
        # Connect alpha texture to both shaders
        links.new(alpha_tex_node.outputs['Color'], default_principled.inputs['Alpha'])
        links.new(alpha_tex_node.outputs['Color'], imported_principled.inputs['Alpha'])
    else:
        # Set alpha to 1 if no alpha texture
        default_principled.inputs['Alpha'].default_value = 1.0
        imported_principled.inputs['Alpha'].default_value = 1.0

    # Set mix factor based on object state
    object_state = addon_data.get("object_states", {}).get(obj.name, {})
    use_default_texture = object_state.get("use_default_texture", True)
    mix_shader.inputs['Fac'].default_value = 0.0 if use_default_texture else 1.0

def create_or_update_material(obj, image_path):
    """
    Update the imported texture in the material for the given object.

    Load the new texture and set it to the imported texture node.
    """
    mat_name = "Mat_" + obj.name
    mat = bpy.data.materials.get(mat_name)
    if not mat:
        create_material_for_object(obj)
        mat = bpy.data.materials.get(mat_name)

    nodes = mat.node_tree.nodes
    imported_tex_node = None
    mix_shader = None

    # Find nodes
    for node in nodes:
        if node.name == 'Mix Shader':
            mix_shader = node
        elif node.type == 'TEX_IMAGE' and node.location == (200, -100):
            imported_tex_node = node

    if not imported_tex_node or not mix_shader:
        return  # Material not properly set up

    # Load the image with a unique name
    unique_image_name = f"T_{obj.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    image = bpy.data.images.load(image_path, check_existing=False)
    image.name = unique_image_name
    imported_tex_node.image = image

    # Set mix factor to use the imported texture
    object_state = addon_data.get("object_states", {}).get(obj.name, {})
    use_default_texture = object_state.get("use_default_texture", True)
    mix_shader.inputs['Fac'].default_value = 0.0 if use_default_texture else 1.0

def process_watch_folder():
    """
    Check the watch folder for new textures.

    If a new texture is found, move it to the review folder and set it for review.
    """
    prefs = get_addon_preferences()
    watch_folder = bpy.path.abspath(prefs.watch_folder_path)
    if not watch_folder or not os.path.exists(watch_folder):
        return

    project_texture_folder = bpy.path.abspath("//textures/")
    if not os.path.exists(project_texture_folder):
        os.makedirs(project_texture_folder)

    files = os.listdir(watch_folder)
    for file_name in files:
        file_path = os.path.join(watch_folder, file_name)
        if os.path.isfile(file_path) and file_name.lower().endswith(('.png', '.jpg', '.jpeg', '.tga', '.bmp', '.tiff')):
            selected_object_name = addon_data.get("selected_object")
            if selected_object_name:
                ext = os.path.splitext(file_name)[1]
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                new_file_name = f"T_{selected_object_name}_{timestamp}{ext}"
                new_file_path = os.path.join(project_texture_folder, new_file_name)
                # Move the file to a temporary review path
                review_folder = bpy.path.abspath("//review/")
                if not os.path.exists(review_folder):
                    os.makedirs(review_folder)
                review_file_path = os.path.join(review_folder, new_file_name)
                os.replace(file_path, review_file_path)
                # Set review pending
                addon_data["review_pending"] = True
                addon_data["review_image_path"] = review_file_path
                save_addon_data()
                # Show image in Image Editor
                show_image_in_image_editor(review_file_path)
                break  # Only process one image at a time

def auto_refresh_timer():
    """
    Timer function for auto-refreshing textures.

    Checks the watch folder at specified intervals.
    """
    global timer_running
    prefs = get_addon_preferences()
    if addon_data.get("auto_refresh") and prefs.watch_folder_enabled:
        process_watch_folder()
        if not addon_data.get("review_pending"):
            for image in bpy.data.images:
                image.reload()
        interval = addon_data.get("refresh_interval", 5)
        timer_running = True
        return interval
    else:
        timer_running = False
        return None

def update_auto_refresh(self, context):
    """
    Update function for auto-refresh properties.

    Registers or unregisters the timer based on settings.
    """
    global timer_running
    addon_data["auto_refresh"] = context.scene.karamove_texture_auto_refresh
    addon_data["refresh_interval"] = context.scene.karamove_texture_refresh_interval
    save_addon_data()
    prefs = get_addon_preferences()
    if addon_data["auto_refresh"] and prefs.watch_folder_enabled:
        if not timer_running:
            bpy.app.timers.register(auto_refresh_timer)
    else:
        if timer_running:
            bpy.app.timers.unregister(auto_refresh_timer)
            timer_running = False

def update_watch_folder_enabled(self, context):
    """
    Update function for watch folder enabled property.

    Registers or unregisters the timer based on settings.
    """
    global timer_running
    prefs = get_addon_preferences()
    if not prefs.watch_folder_enabled and timer_running:
        bpy.app.timers.unregister(auto_refresh_timer)
        timer_running = False
    elif prefs.watch_folder_enabled and addon_data.get("auto_refresh"):
        if not timer_running:
            bpy.app.timers.register(auto_refresh_timer)

def show_image_in_image_editor(image_path):
    """
    Load and display the image in the Image Editor.

    If no Image Editor area exists, split the area to create one.
    """
    image = bpy.data.images.load(image_path, check_existing=True)
    for area in bpy.context.window.screen.areas:
        if area.type == 'IMAGE_EDITOR':
            area.spaces.active.image = image
            return
    # If no IMAGE_EDITOR area, split area and create one
    for area in bpy.context.window.screen.areas:
        if area.type == 'VIEW_3D':
            with bpy.context.temp_override(area=area):
                bpy.ops.screen.area_split(direction='HORIZONTAL', factor=0.5)
                new_area = bpy.context.window.screen.areas[-1]
                new_area.type = 'IMAGE_EDITOR'
                new_area.spaces.active.image = image
            return

def close_image_editor():
    """
    Close the Image Editor area if it was opened by the addon.

    If only one area exists, clear the image.
    """
    for window in bpy.context.window_manager.windows:
        screen = window.screen
        for area in screen.areas:
            if area.type == 'IMAGE_EDITOR':
                # Check if area was created by addon (simple check)
                if len(screen.areas) > 1:
                    # Switch context to the area to be closed
                    with bpy.context.temp_override(window=window, area=area):
                        bpy.ops.screen.area_close()
                else:
                    area.spaces.active.image = None
                return

class KaramoveAddonPreferences(bpy.types.AddonPreferences):
    """
    Addon preferences for setting the watch folder path and enabling/disabling the watch folder.
    """
    bl_idname = __name__

    watch_folder_path: bpy.props.StringProperty(
        name="Watch Folder Path",
        description="Folder to watch for new textures",
        subtype='DIR_PATH',
    )

    watch_folder_enabled: bpy.props.BoolProperty(
        name="Watch Folder Enabled",
        default=False,
        update=update_watch_folder_enabled
    )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "watch_folder_path")
        layout.prop(self, "watch_folder_enabled")

class KaramoveTexturePanelObjectSelection(bpy.types.Panel):
    """
    Panel for object selection and settings.
    """
    bl_label = "Object Selection"
    bl_idname = "OBJECT_PT_karamove_texture_object_selection"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Karamove Texture'

    def draw(self, context):
        if not addon_data:
            load_addon_data()
            prefs = get_addon_preferences()
            if addon_data.get("auto_refresh") and prefs.watch_folder_enabled and not timer_running:
                bpy.app.timers.register(auto_refresh_timer)

        layout = self.layout

        # Add Selected Object
        row = layout.row()
        row.operator("object.karamove_add_object_to_list", text="Add Selected Object")

        # List of Objects
        for obj_name in addon_data.get("objects", []):
            obj = bpy.data.objects.get(obj_name)
            if obj:
                object_state = addon_data.get("object_states", {}).get(obj_name, {})
                use_default_texture = object_state.get("use_default_texture", True)

                box = layout.box()
                row = box.row()
                if obj_name == addon_data.get("selected_object"):
                    row.alert = True  # Highlight selected object
                toggle_op = row.operator("object.karamove_toggle_texture", text="", icon='TEXTURE' if use_default_texture else 'IMAGE_DATA')
                toggle_op.object_name = obj_name
                toggle_op.use_default_texture = not use_default_texture
                op_select = row.operator("object.karamove_select_object_in_list", text=obj_name)
                op_select.object_name = obj_name
                op_remove = row.operator("object.karamove_remove_object_from_list", text="", icon='X')
                op_remove.object_name = obj_name

                # Default Texture Dropdown
                row = box.row()
                row.prop(obj.karamove_settings, "default_texture")

                # Alpha Texture Dropdown
                row = box.row()
                row.prop(obj.karamove_settings, "alpha_texture")

class KaramoveTexturePanelTexture(bpy.types.Panel):
    """
    Panel for texture operations like resetting and opening the texture folder.
    """
    bl_label = "Texture"
    bl_idname = "OBJECT_PT_karamove_texture_texture"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Karamove Texture'

    def draw(self, context):
        layout = self.layout

        # Reset Texture Buttons
        row = layout.row()
        row.operator("object.karamove_reset_texture", text="Reset Selected Texture")
        row.operator("object.karamove_reset_all_textures", text="Reset All Textures")

        # Open Texture Folder
        row = layout.row()
        row.operator("object.karamove_open_texture_folder", text="Open Texture Folder")

class KaramoveTexturePanelRefresh(bpy.types.Panel):
    """
    Panel for refreshing textures and setting auto-refresh options.
    """
    bl_label = "Refresh"
    bl_idname = "OBJECT_PT_karamove_texture_refresh"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Karamove Texture'

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        # Refresh and Auto-Refresh
        row = layout.row()
        row.operator("object.karamove_refresh_textures", text="Refresh Textures")
        row.prop(scene, "karamove_texture_auto_refresh", text="Auto Refresh")

        row = layout.row()
        row.prop(scene, "karamove_texture_refresh_interval", text="Interval (s)")

class KaramoveTexturePanelReview(bpy.types.Panel):
    """
    Panel for reviewing new textures before applying them.
    """
    bl_label = "Review"
    bl_idname = "OBJECT_PT_karamove_texture_review"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Karamove Texture'

    def draw(self, context):
        layout = self.layout
        if addon_data.get("review_pending"):
            review_image_path = addon_data.get("review_image_path")
            if os.path.exists(review_image_path):
                # Inform user that image is displayed in Image Editor
                layout.label(text="Image displayed in Image Editor")
            row = layout.row()
            row.operator("object.karamove_accept_texture", text="Accept")
            row.operator("object.karamove_discard_texture", text="Discard")
        else:
            layout.label(text="No texture to review")

class KaramoveAddObjectToListOperator(bpy.types.Operator):
    """
    Operator to add the selected object to the list and initialize its settings.
    """
    bl_idname = "object.karamove_add_object_to_list"
    bl_label = "Add Selected Object to List"

    def execute(self, context):
        obj = context.active_object
        if obj and obj.name not in addon_data.get("objects", []):
            addon_data["objects"].append(obj.name)
            # Initialize object state
            if "object_states" not in addon_data:
                addon_data["object_states"] = {}
            addon_data["object_states"][obj.name] = {
                "use_default_texture": True
            }
            create_material_for_object(obj)
            save_addon_data()
        return {'FINISHED'}

class KaramoveRemoveObjectFromListOperator(bpy.types.Operator):
    """
    Operator to remove an object from the list and clean up its settings.
    """
    bl_idname = "object.karamove_remove_object_from_list"
    bl_label = "Remove Object from List"

    object_name: bpy.props.StringProperty()

    def execute(self, context):
        if self.object_name in addon_data.get("objects", []):
            addon_data["objects"].remove(self.object_name)
            if addon_data.get("selected_object") == self.object_name:
                addon_data["selected_object"] = None
            # Reset mix factor to 0
            obj = bpy.data.objects.get(self.object_name)
            if obj:
                mat_name = "Mat_" + obj.name
                mat = bpy.data.materials.get(mat_name)
                if mat:
                    mix_shader = mat.node_tree.nodes.get('Mix Shader')
                    if mix_shader:
                        mix_shader.inputs['Fac'].default_value = 0.0
            # Remove object state
            if "object_states" in addon_data and self.object_name in addon_data["object_states"]:
                del addon_data["object_states"][self.object_name]
            # Remove object settings
            if "object_settings" in addon_data and self.object_name in addon_data["object_settings"]:
                del addon_data["object_settings"][self.object_name]
            save_addon_data()
        return {'FINISHED'}

class KaramoveSelectObjectInListOperator(bpy.types.Operator):
    """
    Operator to select an object from the list.
    """
    bl_idname = "object.karamove_select_object_in_list"
    bl_label = "Select Object in List"

    object_name: bpy.props.StringProperty()

    def execute(self, context):
        addon_data["selected_object"] = self.object_name
        save_addon_data()
        return {'FINISHED'}

class KaramoveToggleTextureOperator(bpy.types.Operator):
    """
    Operator to toggle between the default texture and the imported texture for an object.
    """
    bl_idname = "object.karamove_toggle_texture"
    bl_label = "Toggle Texture"

    object_name: bpy.props.StringProperty()
    use_default_texture: bpy.props.BoolProperty()

    def execute(self, context):
        if "object_states" not in addon_data:
            addon_data["object_states"] = {}
        object_state = addon_data["object_states"].get(self.object_name, {})
        object_state["use_default_texture"] = self.use_default_texture
        addon_data["object_states"][self.object_name] = object_state

        # Update material
        obj = bpy.data.objects.get(self.object_name)
        if obj:
            mat_name = "Mat_" + obj.name
            mat = bpy.data.materials.get(mat_name)
            if mat:
                mix_shader = mat.node_tree.nodes.get('Mix Shader')
                if mix_shader:
                    mix_shader.inputs['Fac'].default_value = 0.0 if self.use_default_texture else 1.0
        save_addon_data()
        return {'FINISHED'}

class KaramoveRefreshTexturesOperator(bpy.types.Operator):
    """
    Operator to manually refresh all textures.
    """
    bl_idname = "object.karamove_refresh_textures"
    bl_label = "Refresh Textures"

    def execute(self, context):
        process_watch_folder()
        if not addon_data.get("review_pending"):
            for image in bpy.data.images:
                image.reload()
        return {'FINISHED'}

class KaramoveResetTextureOperator(bpy.types.Operator):
    """
    Operator to reset the texture of the selected object.
    """
    bl_idname = "object.karamove_reset_texture"
    bl_label = "Reset Texture of Selected Object"

    def execute(self, context):
        selected_object_name = addon_data.get("selected_object")
        if selected_object_name:
            obj = bpy.data.objects.get(selected_object_name)
            if obj:
                mat_name = "Mat_" + obj.name
                mat = bpy.data.materials.get(mat_name)
                if mat:
                    nodes = mat.node_tree.nodes
                    imported_tex_node = None
                    mix_shader = None

                    # Find nodes
                    for node in nodes:
                        if node.name == 'Mix Shader':
                            mix_shader = node
                        elif node.type == 'TEX_IMAGE' and node.location == (200, -100):
                            imported_tex_node = node

                    if imported_tex_node and mix_shader:
                        # Remove the image
                        image = imported_tex_node.image
                        if image:
                            bpy.data.images.remove(image)
                        # Unload the image texture
                        imported_tex_node.image = None
                        # Reset mix factor to show default texture
                        mix_shader.inputs['Fac'].default_value = 0.0
                        # Update object state
                        object_state = addon_data.get("object_states", {}).get(selected_object_name, {})
                        object_state["use_default_texture"] = True
                        addon_data["object_states"][selected_object_name] = object_state
                        save_addon_data()
        return {'FINISHED'}

class KaramoveResetAllTexturesOperator(bpy.types.Operator):
    """
    Operator to reset the textures of all objects.
    """
    bl_idname = "object.karamove_reset_all_textures"
    bl_label = "Reset All Textures"

    def execute(self, context):
        for obj_name in addon_data.get("objects", []):
            obj = bpy.data.objects.get(obj_name)
            if obj:
                mat_name = "Mat_" + obj.name
                mat = bpy.data.materials.get(mat_name)
                if mat:
                    nodes = mat.node_tree.nodes
                    imported_tex_node = None
                    mix_shader = None

                    # Find nodes
                    for node in nodes:
                        if node.name == 'Mix Shader':
                            mix_shader = node
                        elif node.type == 'TEX_IMAGE' and node.location == (200, -100):
                            imported_tex_node = node

                    if imported_tex_node and mix_shader:
                        # Remove the image
                        image = imported_tex_node.image
                        if image:
                            bpy.data.images.remove(image)
                        # Unload the image texture
                        imported_tex_node.image = None
                        # Reset mix factor to show default texture
                        mix_shader.inputs['Fac'].default_value = 0.0
                        # Update object state
                        object_state = addon_data.get("object_states", {}).get(obj_name, {})
                        object_state["use_default_texture"] = True
                        addon_data["object_states"][obj_name] = object_state
                        save_addon_data()
        return {'FINISHED'}

class KaramoveOpenTextureFolderOperator(bpy.types.Operator):
    """
    Operator to open the texture folder in the file explorer.
    """
    bl_idname = "object.karamove_open_texture_folder"
    bl_label = "Open Texture Folder"

    def execute(self, context):
        project_texture_folder = bpy.path.abspath("//textures/")
        if os.path.exists(project_texture_folder):
            if platform.system() == 'Windows':
                os.startfile(project_texture_folder)
            elif platform.system() == 'Darwin':
                subprocess.Popen(['open', project_texture_folder])
            else:
                subprocess.Popen(['xdg-open', project_texture_folder])
        return {'FINISHED'}

class KaramoveAcceptTextureOperator(bpy.types.Operator):
    """
    Operator to accept the reviewed texture and apply it to the selected object.
    """
    bl_idname = "object.karamove_accept_texture"
    bl_label = "Accept Texture"

    def execute(self, context):
        review_image_path = addon_data.get("review_image_path")
        selected_object_name = addon_data.get("selected_object")
        if review_image_path and selected_object_name:
            # Move the image to textures folder
            project_texture_folder = bpy.path.abspath("//textures/")
            if not os.path.exists(project_texture_folder):
                os.makedirs(project_texture_folder)
            ext = os.path.splitext(review_image_path)[1]
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            new_file_name = f"T_{selected_object_name}_{timestamp}{ext}"
            new_file_path = os.path.join(project_texture_folder, new_file_name)
            os.replace(review_image_path, new_file_path)
            # Update material
            obj = bpy.data.objects.get(selected_object_name)
            if obj:
                create_or_update_material(obj, new_file_path)
            # Clear review state
            addon_data["review_pending"] = False
            addon_data["review_image_path"] = ""
            save_addon_data()
            # Close Image Editor
            close_image_editor()
        return {'FINISHED'}

class KaramoveDiscardTextureOperator(bpy.types.Operator):
    """
    Operator to discard the reviewed texture.
    """
    bl_idname = "object.karamove_discard_texture"
    bl_label = "Discard Texture"

    def execute(self, context):
        review_image_path = addon_data.get("review_image_path")
        if review_image_path and os.path.exists(review_image_path):
            os.remove(review_image_path)
        # Clear review state
        addon_data["review_pending"] = False
        addon_data["review_image_path"] = ""
        save_addon_data()
        # Close Image Editor
        close_image_editor()
        return {'FINISHED'}

def register():
    # Register classes and properties
    bpy.utils.register_class(KaramoveObjectSettings)
    bpy.types.Object.karamove_settings = bpy.props.PointerProperty(type=KaramoveObjectSettings)

    bpy.utils.register_class(KaramoveAddonPreferences)
    bpy.utils.register_class(KaramoveTexturePanelObjectSelection)
    bpy.utils.register_class(KaramoveTexturePanelTexture)
    bpy.utils.register_class(KaramoveTexturePanelRefresh)
    bpy.utils.register_class(KaramoveTexturePanelReview)
    bpy.utils.register_class(KaramoveAddObjectToListOperator)
    bpy.utils.register_class(KaramoveRemoveObjectFromListOperator)
    bpy.utils.register_class(KaramoveSelectObjectInListOperator)
    bpy.utils.register_class(KaramoveToggleTextureOperator)
    bpy.utils.register_class(KaramoveRefreshTexturesOperator)
    bpy.utils.register_class(KaramoveResetTextureOperator)
    bpy.utils.register_class(KaramoveResetAllTexturesOperator)
    bpy.utils.register_class(KaramoveOpenTextureFolderOperator)
    bpy.utils.register_class(KaramoveAcceptTextureOperator)
    bpy.utils.register_class(KaramoveDiscardTextureOperator)

    bpy.types.Scene.karamove_texture_auto_refresh = bpy.props.BoolProperty(
        update=update_auto_refresh
    )
    bpy.types.Scene.karamove_texture_refresh_interval = bpy.props.IntProperty(
        min=1,
        max=60,
        default=5,
        update=update_auto_refresh
    )

def unregister():
    # Unregister classes and properties
    bpy.utils.unregister_class(KaramoveObjectSettings)
    del bpy.types.Object.karamove_settings

    bpy.utils.unregister_class(KaramoveAddonPreferences)
    bpy.utils.unregister_class(KaramoveTexturePanelObjectSelection)
    bpy.utils.unregister_class(KaramoveTexturePanelTexture)
    bpy.utils.unregister_class(KaramoveTexturePanelRefresh)
    bpy.utils.unregister_class(KaramoveTexturePanelReview)
    bpy.utils.unregister_class(KaramoveAddObjectToListOperator)
    bpy.utils.unregister_class(KaramoveRemoveObjectFromListOperator)
    bpy.utils.unregister_class(KaramoveSelectObjectInListOperator)
    bpy.utils.unregister_class(KaramoveToggleTextureOperator)
    bpy.utils.unregister_class(KaramoveRefreshTexturesOperator)
    bpy.utils.unregister_class(KaramoveResetTextureOperator)
    bpy.utils.unregister_class(KaramoveResetAllTexturesOperator)
    bpy.utils.unregister_class(KaramoveOpenTextureFolderOperator)
    bpy.utils.unregister_class(KaramoveAcceptTextureOperator)
    bpy.utils.unregister_class(KaramoveDiscardTextureOperator)

    del bpy.types.Scene.karamove_texture_auto_refresh
    del bpy.types.Scene.karamove_texture_refresh_interval

    try:
        bpy.app.timers.unregister(auto_refresh_timer)
    except:
        pass