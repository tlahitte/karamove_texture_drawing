bl_info = {
    "name": "Karamove - Texture Drawing",
    "author": "Tommy Lahitte",
    "version": (1, 0),
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

# Global variables
addon_data = {}
timer_running = False

def get_project_json_file_path():
    project_directory = bpy.path.abspath("//")
    if not project_directory:
        # Project directory is empty, .blend file not saved yet
        return None
    json_file_path = os.path.join(project_directory, "karamove_texture_drawing_data.json")
    return json_file_path

def load_addon_data():
    global addon_data
    json_file_path = get_project_json_file_path()
    if json_file_path and os.path.exists(json_file_path):
        with open(json_file_path, 'r') as f:
            addon_data = json.load(f)
    else:
        addon_data = {
            "objects": [],
            "selected_object": None,
            "watch_folder": "",
            "auto_refresh": False,
            "refresh_interval": 5
        }
        if json_file_path:
            save_addon_data()
    scene = bpy.context.scene
    scene.karamove_texture_watch_folder = addon_data.get("watch_folder", "")
    scene.karamove_texture_auto_refresh = addon_data.get("auto_refresh", False)
    scene.karamove_texture_refresh_interval = addon_data.get("refresh_interval", 5)

def save_addon_data():
    scene = bpy.context.scene
    addon_data["watch_folder"] = scene.karamove_texture_watch_folder
    addon_data["auto_refresh"] = scene.karamove_texture_auto_refresh
    addon_data["refresh_interval"] = scene.karamove_texture_refresh_interval
    json_file_path = get_project_json_file_path()
    if json_file_path:
        with open(json_file_path, 'w') as f:
            json.dump(addon_data, f)

def create_material_for_object(obj):
    mat_name = "Mat_" + obj.name
    mat = bpy.data.materials.get(mat_name)
    if not mat:
        mat = bpy.data.materials.new(name=mat_name)
        mat.use_nodes = True
        if obj.data.materials:
            obj.data.materials[0] = mat
        else:
            obj.data.materials.append(mat)

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    # Create nodes
    output_node = nodes.new(type='ShaderNodeOutputMaterial')
    output_node.location = (400, 0)

    mix_shader = nodes.new(type='ShaderNodeMixShader')
    mix_shader.location = (200, 0)

    diffuse_node = nodes.new(type='ShaderNodeBsdfDiffuse')
    diffuse_node.location = (0, 100)
    diffuse_node.inputs['Color'].default_value = (1, 1, 1, 1)  # White color

    principled_node = nodes.new(type='ShaderNodeBsdfPrincipled')
    principled_node.location = (0, -100)

    texture_node = nodes.new(type='ShaderNodeTexImage')
    texture_node.location = (-400, -100)

    # Create an empty image with the name
    image_name = "T_" + obj.name
    image = bpy.data.images.get(image_name)
    if not image:
        image = bpy.data.images.new(name=image_name, width=1024, height=1024, alpha=True)
    texture_node.image = image

    # Link nodes
    links.new(texture_node.outputs['Color'], principled_node.inputs['Base Color'])
    links.new(diffuse_node.outputs['BSDF'], mix_shader.inputs[1])
    links.new(principled_node.outputs['BSDF'], mix_shader.inputs[2])
    links.new(mix_shader.outputs['Shader'], output_node.inputs['Surface'])

    # Set mix factor to 0 (show white diffuse)
    mix_shader.inputs['Fac'].default_value = 0.0

def create_or_update_material(obj, image_path):
    mat_name = "Mat_" + obj.name
    mat = bpy.data.materials.get(mat_name)
    if not mat:
        create_material_for_object(obj)
        mat = bpy.data.materials.get(mat_name)

    nodes = mat.node_tree.nodes
    texture_node = nodes.get('Image Texture')
    mix_shader = nodes.get('Mix Shader')

    if not texture_node or not mix_shader:
        return  # Material not properly set up

    # Load the image
    image = bpy.data.images.load(image_path, check_existing=True)
    texture_node.image = image

    # Set mix factor to 1 (show texture)
    mix_shader.inputs['Fac'].default_value = 1.0

def process_watch_folder():
    watch_folder = addon_data.get("watch_folder", "")
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
                new_file_name = "T_" + selected_object_name + ext
                new_file_path = os.path.join(project_texture_folder, new_file_name)
                # Use os.replace to overwrite if file exists
                os.replace(file_path, new_file_path)
                obj = bpy.data.objects.get(selected_object_name)
                if obj:
                    create_or_update_material(obj, new_file_path)

def auto_refresh_timer():
    global timer_running
    if addon_data.get("auto_refresh"):
        process_watch_folder()
        for image in bpy.data.images:
            image.reload()
        interval = addon_data.get("refresh_interval", 5)
        timer_running = True
        return interval
    else:
        timer_running = False
        return None

def update_auto_refresh(self, context):
    global timer_running
    addon_data["auto_refresh"] = context.scene.karamove_texture_auto_refresh
    addon_data["refresh_interval"] = context.scene.karamove_texture_refresh_interval
    save_addon_data()
    if addon_data["auto_refresh"]:
        if not timer_running:
            bpy.app.timers.register(auto_refresh_timer)
    else:
        if timer_running:
            bpy.app.timers.unregister(auto_refresh_timer)
            timer_running = False

class KaramoveTexturePanel(bpy.types.Panel):
    bl_label = "Karamove Texture"
    bl_idname = "OBJECT_PT_karamove_texture"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Karamove Texture'

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        # Add Selected Object
        row = layout.row()
        row.operator("object.karamove_add_object_to_list", text="Add Selected Object")

        # List of Objects
        box = layout.box()
        for obj_name in addon_data.get("objects", []):
            row = box.row()
            icon = 'RADIOBUT_ON' if obj_name == addon_data.get("selected_object") else 'RADIOBUT_OFF'
            op_select = row.operator("object.karamove_select_object_in_list", text=obj_name, icon=icon)
            op_select.object_name = obj_name
            op_remove = row.operator("object.karamove_remove_object_from_list", text="", icon='X')
            op_remove.object_name = obj_name

        # Reset Texture Buttons
        layout.label(text="Reset Textures:")
        row = layout.row()
        row.operator("object.karamove_reset_texture", text="Reset Selected Texture")
        row.operator("object.karamove_reset_all_textures", text="Reset All Textures")

        # Watch Folder
        layout.prop(scene, "karamove_texture_watch_folder", text="Watch Folder")
        layout.operator("object.karamove_set_watch_folder", text="Set Watch Folder")

        # Refresh and Auto-Refresh
        row = layout.row()
        row.operator("object.karamove_refresh_textures", text="Refresh Textures")
        row.prop(scene, "karamove_texture_auto_refresh", text="Auto Refresh")

        row = layout.row()
        row.prop(scene, "karamove_texture_refresh_interval", text="Interval (s)")

class KaramoveAddObjectToListOperator(bpy.types.Operator):
    bl_idname = "object.karamove_add_object_to_list"
    bl_label = "Add Selected Object to List"

    def execute(self, context):
        obj = context.active_object
        if obj and obj.name not in addon_data.get("objects", []):
            addon_data["objects"].append(obj.name)
            create_material_for_object(obj)
            save_addon_data()
        return {'FINISHED'}

class KaramoveRemoveObjectFromListOperator(bpy.types.Operator):
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
            save_addon_data()
        return {'FINISHED'}

class KaramoveSelectObjectInListOperator(bpy.types.Operator):
    bl_idname = "object.karamove_select_object_in_list"
    bl_label = "Select Object in List"

    object_name: bpy.props.StringProperty()

    def execute(self, context):
        addon_data["selected_object"] = self.object_name
        save_addon_data()
        return {'FINISHED'}

class KaramoveSetWatchFolderOperator(bpy.types.Operator):
    bl_idname = "object.karamove_set_watch_folder"
    bl_label = "Set Watch Folder"

    def execute(self, context):
        save_addon_data()
        return {'FINISHED'}

class KaramoveRefreshTexturesOperator(bpy.types.Operator):
    bl_idname = "object.karamove_refresh_textures"
    bl_label = "Refresh Textures"

    def execute(self, context):
        process_watch_folder()
        for image in bpy.data.images:
            image.reload()
        return {'FINISHED'}

class KaramoveResetTextureOperator(bpy.types.Operator):
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
                    texture_node = nodes.get('Image Texture')
                    mix_shader = nodes.get('Mix Shader')
                    if texture_node and mix_shader:
                        # Remove the image
                        image = texture_node.image
                        if image:
                            bpy.data.images.remove(image)
                        # Create a new blank image
                        image_name = "T_" + obj.name
                        image = bpy.data.images.new(name=image_name, width=1024, height=1024, alpha=True)
                        texture_node.image = image
                        # Set mix factor to 0 (show white diffuse)
                        mix_shader.inputs['Fac'].default_value = 0.0
        return {'FINISHED'}

class KaramoveResetAllTexturesOperator(bpy.types.Operator):
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
                    texture_node = nodes.get('Image Texture')
                    mix_shader = nodes.get('Mix Shader')
                    if texture_node and mix_shader:
                        # Remove the image
                        image = texture_node.image
                        if image:
                            bpy.data.images.remove(image)
                        # Create a new blank image
                        image_name = "T_" + obj.name
                        image = bpy.data.images.new(name=image_name, width=1024, height=1024, alpha=True)
                        texture_node.image = image
                        # Set mix factor to 0 (show white diffuse)
                        mix_shader.inputs['Fac'].default_value = 0.0
        return {'FINISHED'}

def register():
    bpy.utils.register_class(KaramoveTexturePanel)
    bpy.utils.register_class(KaramoveAddObjectToListOperator)
    bpy.utils.register_class(KaramoveRemoveObjectFromListOperator)
    bpy.utils.register_class(KaramoveSelectObjectInListOperator)
    bpy.utils.register_class(KaramoveRefreshTexturesOperator)
    bpy.utils.register_class(KaramoveSetWatchFolderOperator)
    bpy.utils.register_class(KaramoveResetTextureOperator)
    bpy.utils.register_class(KaramoveResetAllTexturesOperator)

    bpy.types.Scene.karamove_texture_watch_folder = bpy.props.StringProperty(
        subtype='DIR_PATH',
        update=update_auto_refresh
    )
    bpy.types.Scene.karamove_texture_auto_refresh = bpy.props.BoolProperty(
        update=update_auto_refresh
    )
    bpy.types.Scene.karamove_texture_refresh_interval = bpy.props.IntProperty(
        min=1,
        max=60,
        default=5,
        update=update_auto_refresh
    )

    load_addon_data()
    if addon_data.get("auto_refresh"):
        bpy.app.timers.register(auto_refresh_timer)

def unregister():
    bpy.utils.unregister_class(KaramoveTexturePanel)
    bpy.utils.unregister_class(KaramoveAddObjectToListOperator)
    bpy.utils.unregister_class(KaramoveRemoveObjectFromListOperator)
    bpy.utils.unregister_class(KaramoveSelectObjectInListOperator)
    bpy.utils.unregister_class(KaramoveRefreshTexturesOperator)
    bpy.utils.unregister_class(KaramoveSetWatchFolderOperator)
    bpy.utils.unregister_class(KaramoveResetTextureOperator)
    bpy.utils.unregister_class(KaramoveResetAllTexturesOperator)

    del bpy.types.Scene.karamove_texture_watch_folder
    del bpy.types.Scene.karamove_texture_auto_refresh
    del bpy.types.Scene.karamove_texture_refresh_interval

    try:
        bpy.app.timers.unregister(auto_refresh_timer)
    except:
        pass

if __name__ == "__main__":
    register()
