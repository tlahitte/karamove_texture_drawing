# Karamove - Texture Drawing Addon for Blender

**Version:** 1.7  
**Author:** Tommy Lahitte

## Description

*Karamove - Texture Drawing* is a Blender addon developed for the 9th edition of **Karamove**, an interactive art installation. This addon allows children and artists to draw directly on the UV texture of 3D objects and see their artwork come to life in real-time within Blender.

The addon facilitates an engaging and dynamic creative process by:

- Enabling the selection and management of objects whose textures can be interactively updated.
- Automatically watching a specified folder for new images and updating object textures accordingly.
- Providing tools to reset textures to a default white canvas.
- Offering auto-refresh functionality to continuously update textures without manual intervention.

## Features

- **Object Management**: Easily add or remove objects from the texture management list.
- **Real-Time Texture Updates**: Automatically apply new textures to selected objects when images are added to the watch folder.
- **Auto-Refresh**: Set an interval for automatic texture updates.
- **Reset Textures**: Reset individual or all object textures to a white canvas.
- **Project-Specific Data**: All addon data is stored within the Blender project directory, ensuring settings are specific to each project.

## Installation

1. **Download the Addon**:

   - Download the latest release zip file from the [Releases](#) section.
   - Extract it's content to a new folder

2. **Install the Addon in Blender**:

   - Open Blender: Blender > Blender-Karamove9th_CircusScene.blend
   - Go to **Edit > Preferences**.
   - Select the **Add-ons** tab.
   - Click on **Install...** at the top.
   - Navigate to the extracted zip file > Plugin_Blender, select the zip file, and click **Install Add-on**.
   - Enable the addon by checking the box next to **Karamove - Texture Drawing**.
   - Set your Watchfolder path to the Watchfolder directory that came with the project

## Usage Instructions

### Initial Setup

1. **Save Your Blender Project**:

   - Ensure your Blender project is saved. The addon stores data within the project directory in a JSON file
   - Default project provided with the addon should come with a JSON file to automatically load the correct set of texture

2. **Access the Addon Panel**:

   - In the 3D Viewport, press `N` to open the sidebar.
   - Navigate to the **Karamove Texture** tab.

### Adding Objects

1. **Select an Object**:

   - Click on the object in the viewport you wish to manage.

2. **Add the Object to the List**:

   - In the addon panel, click **Add Selected Object**.
   - The object now appears in the list with options to select or remove it.

### Managing Objects

- **Select an Object in the List**:

  - Click on the object's name in the list to select it.
  - Only one object can be selected at a time.

- **Remove an Object from the List**:

  - Click the **X** button next to the object's name to remove it.
  - Removing an object resets its material to display a white shader.

### Setting Up the Watch Folder

1. **Specify the Watch Folder**:

   - In the addon panel, set the path to the folder you want the addon to watch for new images.

2. **Confirm the Watch Folder**:

   - Click **Set Watch Folder** to save the path.

### Applying Textures

- **Add Images to the Watch Folder**:

  - Place your image files (e.g., PNG, JPG) into the specified watch folder.
  - The addon will detect new images, rename them appropriately, and apply them to the selected object.

### Refreshing Textures

- **Manual Refresh**:

  - Click **Refresh Textures** to manually update textures with any new images from the watch folder.

- **Auto-Refresh**:

  - Enable **Auto Refresh** in the addon panel.
  - Set the **Interval (s)** to determine how often the addon checks for new images.

### Resetting Textures

- **Reset Selected Texture**:

  - Click **Reset Selected Texture** to revert the selected object's texture to a white canvas.

- **Reset All Textures**:

  - Click **Reset All Textures** to reset all objects in the list to a white canvas.

## Notes

- **Texture Storage**:

  - The addon stores textures in a `textures` folder within your project directory.

- **Material Setup**:

  - The addon creates a custom material for each object, which blends between a white diffuse shader and the texture based on whether a texture is applied.

- **Data Persistence**:

  - All addon settings and data are saved within the project directory, ensuring a clean workflow when switching between projects.

## Troubleshooting

- **Addon Not Working**:

  - Ensure your project is saved so that the addon can properly access the project directory.

- **Permissions Issues**:

  - Verify that you have read/write permissions for the watch folder and the project directory.

- **Texture Not Updating**:

  - Check that the image files are correctly named and placed in the watch folder.
  - Ensure that the selected object is correctly set in the addon panel.

## License

This addon is distributed under the [MIT License](LICENSE).

## Contributing

Contributions are welcome! Please open an issue or submit a pull request on GitHub.

## Contact

For questions or support, please contact **Tommy Lahitte** at [tlahitte@gmail.com](mailto:tlahitte@gmail.com).

---

**Enjoy creating interactive textures with Karamove - Texture Drawing!**
