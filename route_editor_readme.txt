Pikmin 2 Routes Editor by Yoshi2

In Pikmin 2 the carrying routes for Pikmin are pre-defined inside route files (route.txt).
When Pikmin carry an item back to an Onion or Rocket, the game calculates the path they will take 
using these routes.
Route files are found in the path user/Abe/map/<your level>/route.txt.


The Pikmin Routes Editor (short: route editor, with route referring to the file 
called "route.txt") is able to create and edit such route files. 
Waypoints are points which the Pikmin need to reach before they advance to the 
next part of their carrying path. The Pikmin will only follow the direction to 
which small green arrows point. Bi-directional connections between waypoints are 
possible and have green arrows on both ends.
Waypoints have a radius whose exact purpose is not well understood.
 
# Editor UI  

If "Connect Waypoint" isn't enabled, clicking the left mouse button selects a waypoint.
Holding left-click and dragging selects several waypoints.
Holding down mouse wheel while moving the mouse moves the level view.
Action of right-click on whether "Add Waypoint" or "Move Waypoint(s)" is enabled, see further below 
under "Side panel".

Tool bar: 
 * File->Load: loads an existing route file 
 Hotkey: Ctrl+O
 * File->Save: saves the current data to the path of the last loaded file (if no file was loaded, acts as "Save As")
 Hotkey: Ctrl+S
 * File->Save As: saves the current data to a path that the user chooses
 Hotkey: Ctrl+Alt+S
 * Collision->Load .OBJ: Loads a .obj file to be rendered as the background in the editor and to be used for height detection
 * Collision->Load GRID.BIN: Similar to above, but loads a grid.bin (Pikmin 2's level collision format). 
 Can load archived grid.bin files too (from texts.szs)
 
Side panel:
 * Add Waypoint: If enabled, you can add waypoints with a default radius (which can be configured, 
 see below under "Configuration file")
 Hotkey: Ctrl+A 
 
 * Remove Waypoint(s): Removes all selected waypoints with their connections.
 Hotkey: Del
 
 * Ground Waypoint(s): If the level terrain is loaded, sets the selected waypoints's height to the top-most ground level 
 at their position.
 Hotkey: G
 
 * Move Waypoint(s): When enabled, allows moving waypoints by pressing or holding the right mouse button.
 selected objects.
 Hotkey: M 
 
 * Connect Waypoint: When enabled, continuously connects waypoints in the order you select them with left-click.
 Going over the same waypoints in the same order removes the connection again.
 Hotkey: C
 
When one waypoint is selected, the 4 text boxes in the side panel are its X, Y, Z coordinate and its radius in this order.
 

 
# Configuration file
On the first run of the tool, if no piktool.ini exists, the file is created using default settings.

The ini keeps track of the default paths which the editor opens when you load files.
It also contains the following route editor settings:
 * defaultradius: Sets the default radius for waypoints that are added with "Add Waypoint"
 * invertzoom: If set to True, rolling the mouse wheel forward zooms out and rolling the wheel backward zooms in in top-down view.
 * groundwaypointswhenmoving : If set to True, puts waypoints automatically on the ground when moving them instead of 
 requiring the user to use ``Ground Waypoint(s)``.
 
Model render settings:
The width and height values specify the resolution of the pre-rendered image when you load a collision file. Higher values
give a cleaner appearance but take longer to render.