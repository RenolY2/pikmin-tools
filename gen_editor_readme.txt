Pikmin 2 Generators Editor by Yoshi2

Pikmin 2 has generator files (initgen, plantsgen, defaultgen and others) 
which contain zero or more generators. 
These generators spawn an instance of the object they describe with
the parameters (position, rotation, etc.) written in their data.
Objects can be onions, plants, enemies and more.

The Generators Editor (short: gen editor) allows for those generators to be added, edited and removed.
For the purpose of this document and features in the editor, generators will be called objects.

What this editor can do:
 * Load and save generator files 
 * Render objects, collision and waterboxes in a 2D top-down view or a 3D view
 * Render bridges, walls and weighted floors using flat images (all other objects will be rendered as circles)
 * Add, select, move and remove objects and edit object data
 * Display the names of treasures and tekis 

What this editor cannot do:
 * Retain all comments written in a generator file. This is by design. For some object types comments are recreated.
 It is able to retain comments written above an object entry though (those are shown on the side bar as "Object notes")!
 * Protect you from all your mistakes. It is your responsibility to use values that the game considers valid.

Generator files can be found in user/Abe/map/<your level>/
Collision files and waterbox files can be found inside an archive in user/Kando/map/<your level>/texts.szs

# Editor UI  

Top-down View Controls:
Clicking the left mouse button selects objects and holding left mouse button while dragging selects multiple objects.
Holding down mouse wheel while moving the mouse moves the level view.
W, A, S and D can be used to scroll the level view upwards, to the left, downwards and to the right respectively.
Holding Shift while using WASD scrolls the view at a higher speed.

3D View Controls:
If neither Add Object nor Move Object is activated, clicking the left mouse button selects 
objects and holding left mouse button while dragging selects multiple objects.
W, A, S and D can be used to move the view forwards, to the left, backwards and to the right respectively. Q and E
move the view up and down respectively. Holding Shift moves the view at a higher speed.

Both views:
Ctrl+Z undoes adding or removing objects. Ctrl+Y redoes them. Up to 20 actions can be undone.
Holding shift while selecting objects adds objects to the current selection.
Pressing ESC cancels the Add Object/Move Object mode.


Tool bar: 
 * File->Load: loads an existing generator file 
 Hotkey: Ctrl+O
 * File->Save: saves the current data to the path of the last loaded file (if no file was loaded, acts as "Save As")
 Hotkey: Ctrl+S
 * File->Save As: saves the current data to a path that the user chooses
 Hotkey: Ctrl+Alt+S
 * Geometry->Load .OBJ: Loads a .obj file to be rendered as the background in the editor and to be used for height detection
 * Geometry->Load GRID.BIN: Similar to above, but loads a grid.bin (Pikmin 2's level collision format). 
 Can load archived grid.bin files too (from texts.szs)
 * Geometry->Load WATERBOX.TXT: Loads a waterbox file either directly or from a texts.szs file. Water boxes are 
 rendered in blue with slight transparency.
 * Misc->Topdown View: Change the view into an orthogonal top-down view.
 Hotkey: Ctrl+1
 * Misc->3D View: Change the view into an orthogonal top-down view.
 Hotkey: Ctrl+2
 
Side panel:
 * Add Object: Opens a window for adding an object with specific object data. The drop-down menu lists 
 object templates from the object_templates folder in the tool's folder and choosing one puts the template 
 in the text box below. Clicking the "Add Object" button in this window (or using Ctrl+S) closes the window and 
 allows you to add the object in the level by right-clicking (Top-down View) or left-clicking (3D View) on a spot on the level view.
 Hotkey: Ctrl+A 
 
 * Remove Objects(s): Removes all selected objects.
 Hotkey: Del
 
 * Ground Object(s): If the level terrain is loaded, sets the objects' height to the top-most ground level at their position.
 Hotkey: G
 
 * Move Object(s): When enabled, allows moving objects by pressing or holding the right mouse button (Top-down view) or left mouse button (3D view). 
 If you have one object selected, holding R in move mode and using the right mouse button (Top-down view) or left mouse button (3D view) 
 rotates the object in the direction you are clicking. In 3D view holding H while moving the mouse up or down raises or lowers the 
 selected objects.
 Hotkey: M 
 
 * Edit Object: Opens a window with the object's data that can be edited. Save Object Data (Or Ctrl+S) saves the object data, 
 Ctrl+W closes the edit object window. 
 Hotkey: Ctrl+E 
 
You might have noticed Ctrl+S is used as a hotkey multiple times. Its effect depends on which window is in focus.
(Example: When the main window is in focus, it acts as a shortcut for saving the level. When the Add Object window 
or Edit Object window is in focus, their respective action is triggered)
 

 
# Configuration file
On the first run of the tool, if no piktool.ini exists, the file is created using default settings.

The ini keeps track of the default paths which the editor opens when you load files.
It also contains the following gen editor settings:
 * invertzoom: If set to True, rolling the mouse wheel forward zooms out and rolling the wheel backward zooms in in top-down view.
 * groundobjectswhenmoving: If set to True, puts objects automatically on the ground when moving them instead of 
 requiring the user to use ``Ground Object(s)``. Might not be desired if the user wants to have an object floating
 in the air or slightly burried under the ground.
 * groundobjectswhenadding: If set to True, puts newly added objects on the ground. Only applies to top-down view.
 * wasdscrolling_speed: Speed at which the view moves in units per second.
 * wasdscrolling_speedupfactor: Holding shift while using WASD multiplies the speed by this factor. Example:
 a value of 3 makes it so holding shift while using WASD moves the level view 3 times as fast.
 
Model render settings:
Not used by the Gen Editor.