import traceback

import PyQt5.QtWidgets as QtWidgets
import PyQt5.QtCore as QtCore

from PyQt5.QtCore import QSize, QRect, QMetaObject, QCoreApplication, QPoint
from PyQt5.QtCore import Qt

from PyQt5.QtWidgets import (QWidget, QMainWindow, QFileDialog,
                             QSpacerItem, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QHBoxLayout,
                             QScrollArea, QGridLayout, QMenuBar, QMenu, QAction, QApplication, QStatusBar, QLineEdit)
from PyQt5.QtGui import QMouseEvent, QImage
import PyQt5.QtGui as QtGui

import opengltext
import py_obj
from libpiktxt import PikminGenFile
from custom_widgets import catch_exception
from pikmingen import PikminObject
from configuration import read_config, make_default_config, save_cfg

import pikmingen_widgets as pikwidgets
from pikmingen_widgets import GenMapViewer, PikminSideWidget, PikObjectEditor
from lib.rarc import Archive

PIKMIN2GEN = "Generator files (defaultgen.txt;initgen.txt;plantsgen.txt;*.txt)"


class GenEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.pikmin_gen_file = PikminGenFile()

        self.setup_ui()

        try:
            self.configuration = read_config()
            print("config loaded")
        except FileNotFoundError as e:
            print(e)
            print("creating file...")
            self.configuration = make_default_config()

        self.pikmin_gen_view.pikmin_generators = self.pikmin_gen_file
        self.pikmin_gen_view.editorconfig = self.configuration["gen editor"]

        self.pathsconfig = self.configuration["default paths"]
        self.editorconfig = self.configuration["gen editor"]
        self.current_gen_path = None

        self.current_coordinates = None
        self.editing_windows = {}
        self.add_object_window = None
        self.object_to_be_added = None

        self.history = EditorHistory(20)
        self.edit_spawn_window = None

    @catch_exception
    def reset(self):
        self.history.reset()
        self.object_to_be_added = None
        self.pikmin_gen_view.reset(keep_collision=True)

        self.current_coordinates = None
        for key, val in self.editing_windows.items():
            val.destroy()

        self.editing_windows = {}

        if self.add_object_window is not None:
            self.add_object_window.destroy()
            self.add_object_window = None

        if self.edit_spawn_window is not None:
            self.edit_spawn_window.destroy()
            self.edit_spawn_window = None

        self.current_gen_path = None
        self.pik_control.reset_info()
        self.pik_control.button_add_object.setChecked(False)
        self.pik_control.button_move_object.setChecked(False)

    def setup_ui(self):
        self.resize(1000, 800)
        #self.setMinimumSize(QSize(930, 850))
        self.setWindowTitle("Pikmin 2 Gen Editor")

        self.setup_ui_menubar()
        self.setup_ui_toolbar()

        self.centralwidget = QWidget(self)
        self.centralwidget.setObjectName("centralwidget")
        self.setCentralWidget(self.centralwidget)

        self.pikmin_gen_view = GenMapViewer(self.centralwidget)
        self.horizontalLayout = QHBoxLayout(self.centralwidget)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.horizontalLayout.addWidget(self.pikmin_gen_view)

        spacerItem = QSpacerItem(10, 20, QSizePolicy.Minimum, QSizePolicy.Expanding)
        self.horizontalLayout.addItem(spacerItem)

        self.pik_control = PikminSideWidget(self)
        self.horizontalLayout.addWidget(self.pik_control)

        self.statusbar = QStatusBar(self)
        self.statusbar.setObjectName("statusbar")
        self.setStatusBar(self.statusbar)

        self.connect_actions()

    def setup_ui_menubar(self):
        self.menubar = QMenuBar(self)
        self.file_menu = QMenu(self)
        self.file_menu.setTitle("File")

        save_file_shortcut = QtWidgets.QShortcut(Qt.CTRL + Qt.Key_S, self.file_menu)
        save_file_shortcut.activated.connect(self.button_save_level)

        self.file_load_action = QAction("Load", self)
        self.save_file_action = QAction("Save", self)
        self.save_file_as_action = QAction("Save As", self)
        self.save_file_action.setShortcut("Ctrl+S")

        self.file_load_action.triggered.connect(self.button_load_level)
        self.save_file_action.triggered.connect(self.button_save_level)
        self.save_file_as_action.triggered.connect(self.button_save_level_as)

        self.file_menu.addAction(self.file_load_action)
        self.file_menu.addAction(self.save_file_action)
        self.file_menu.addAction(self.save_file_as_action)


        # ------ Collision Menu
        self.collision_menu = QMenu(self.menubar)
        self.collision_menu.setTitle("Geometry")
        self.collision_load_action = QAction("Load .OBJ", self)
        self.collision_load_action.triggered.connect(self.button_load_collision)
        self.collision_menu.addAction(self.collision_load_action)
        self.collision_load_grid_action = QAction("Load GRID.BIN", self)
        self.collision_load_grid_action.triggered.connect(self.button_load_collision_grid)
        self.collision_menu.addAction(self.collision_load_grid_action)


        # Misc
        self.misc_menu = QMenu(self.menubar)
        self.misc_menu.setTitle("Misc")
        self.spawnpoint_action = QAction("Set startPos/Dir", self)
        self.spawnpoint_action.triggered.connect(self.action_open_rotationedit_window)
        self.misc_menu.addAction(self.spawnpoint_action)

        self.menubar.addAction(self.file_menu.menuAction())
        self.menubar.addAction(self.collision_menu.menuAction())
        self.menubar.addAction(self.misc_menu.menuAction())
        self.setMenuBar(self.menubar)

    def setup_ui_toolbar(self):
        # self.toolbar = QtWidgets.QToolBar("Test", self)
        # self.toolbar.addAction(QAction("TestToolbar", self))
        # self.toolbar.addAction(QAction("TestToolbar2", self))
        # self.toolbar.addAction(QAction("TestToolbar3", self))

        # self.toolbar2 = QtWidgets.QToolBar("Second Toolbar", self)
        # self.toolbar2.addAction(QAction("I like cake", self))

        # self.addToolBar(self.toolbar)
        # self.addToolBarBreak()
        # self.addToolBar(self.toolbar2)
        pass

    def connect_actions(self):
        self.pikmin_gen_view.select_update.connect(self.action_update_info)
        self.pik_control.lineedit_coordinatex.textChanged.connect(self.create_field_edit_action("coordinatex"))
        self.pik_control.lineedit_coordinatey.textChanged.connect(self.create_field_edit_action("coordinatey"))
        self.pik_control.lineedit_coordinatez.textChanged.connect(self.create_field_edit_action("coordinatez"))

        self.pik_control.lineedit_rotationx.textChanged.connect(self.create_field_edit_action("rotationx"))
        self.pik_control.lineedit_rotationy.textChanged.connect(self.create_field_edit_action("rotationy"))
        self.pik_control.lineedit_rotationz.textChanged.connect(self.create_field_edit_action("rotationz"))

        self.pikmin_gen_view.position_update.connect(self.action_update_position)

        self.pikmin_gen_view.customContextMenuRequested.connect(self.mapview_showcontextmenu)
        self.pik_control.button_edit_object.pressed.connect(self.action_open_editwindow)

        self.pik_control.button_add_object.pressed.connect(self.button_open_add_item_window)
        self.pik_control.button_move_object.pressed.connect(self.button_move_objects)
        self.pikmin_gen_view.move_points.connect(self.action_move_objects)
        self.pikmin_gen_view.create_waypoint.connect(self.action_add_object)
        self.pik_control.button_ground_object.pressed.connect(self.action_ground_objects)
        self.pik_control.button_remove_object.pressed.connect(self.action_delete_objects)

        delete_shortcut = QtWidgets.QShortcut(QtGui.QKeySequence(Qt.Key_Delete), self)
        delete_shortcut.activated.connect(self.action_delete_objects)

        undo_shortcut = QtWidgets.QShortcut(QtGui.QKeySequence(Qt.CTRL + Qt.Key_Z), self)
        undo_shortcut.activated.connect(self.action_undo)

        redo_shortcut = QtWidgets.QShortcut(QtGui.QKeySequence(Qt.CTRL + Qt.Key_Y), self)
        redo_shortcut.activated.connect(self.action_redo)

    def action_open_rotationedit_window(self):
        print("wot")
        if self.edit_spawn_window is None:
            self.edit_spawn_window = pikwidgets.SpawnpointEditor()
            self.edit_spawn_window.position.setText("{0}, {1}, {2}".format(
                self.pikmin_gen_file.startpos_x, self.pikmin_gen_file.startpos_y, self.pikmin_gen_file.startpos_z
            ))
            self.edit_spawn_window.rotation.setText(str(self.pikmin_gen_file.startdir))
            self.edit_spawn_window.closing.connect(self.action_close_edit_startpos_window)
            self.edit_spawn_window.button_savetext.pressed.connect(self.action_save_startpos)
            self.edit_spawn_window.show()

    #@catch_exception
    def button_load_level(self):
        filepath, choosentype = QFileDialog.getOpenFileName(
            self, "Open File",
            self.pathsconfig["gen"],
            PIKMIN2GEN + ";;All files (*)")
        print("doooone")
        if filepath:
            print("resetting")
            self.reset()
            print("done")
            print("chosen type:", choosentype)

            with open(filepath, "r", encoding="shift-jis") as f:
                try:
                    self.pikmin_gen_file = PikminGenFile()
                    self.pikmin_gen_file.from_file(f)

                    self.pikmin_gen_view.pikmin_generators = self.pikmin_gen_file
                    self.pikmin_gen_view.update()

                    print("ok")
                    # self.bw_map_screen.update()
                    # path_parts = path.split(filepath)
                    self.setWindowTitle("Pikmin 2 Generators Editor - {0}".format(filepath))
                    self.pathsconfig["gen"] = filepath
                    save_cfg(self.configuration)
                    self.current_gen_path = filepath

                except Exception as error:
                    print("error", error)
                    traceback.print_exc()

    def button_save_level(self):
        if self.current_gen_path is not None:
            with open(self.current_gen_path, "w", encoding="shift-jis") as f:
                try:
                    self.pikmin_gen_file.write(f)
                except Exception as error:
                    print("error", error)
                    traceback.print_exc()
        else:
            self.button_save_level_as()

    def button_save_level_as(self):
        filepath, choosentype = QFileDialog.getSaveFileName(
            self, "Save File",
            self.pathsconfig["gen"],
            PIKMIN2GEN + ";;All files (*)")
        if filepath:
            with open(filepath, "w", encoding="shift-jis") as f:
                try:
                    self.pikmin_gen_file.write(f)
                    self.setWindowTitle("Pikmin 2 Generators Editor - {0}".format(filepath))
                    self.pathsconfig["gen"] = filepath
                    save_cfg(self.configuration)
                    self.current_gen_path = filepath

                except Exception as error:
                    print("error", error)
                    traceback.print_exc()

    def button_load_collision(self):
        try:
            filepath, choosentype = QFileDialog.getOpenFileName(
                self, "Open File",
                self.pathsconfig["collision"],
                "Collision (*.obj);;All files (*)")

            if not filepath:
                return

            with open(filepath, "r") as f:
                verts, faces, normals = py_obj.read_obj(f)

            tmprenderwindow = opengltext.TempRenderWindow(verts, faces)
            tmprenderwindow.show()

            framebuffer = tmprenderwindow.widget.grabFramebuffer()
            framebuffer.save("tmp_image.png", "PNG")
            self.pikmin_gen_view.level_image = framebuffer

            tmprenderwindow.destroy()

            self.pikmin_gen_view.set_collision(verts, faces)
            self.pathsconfig["collision"] = filepath
            save_cfg(self.configuration)

        except:
            traceback.print_exc()

    def action_close_edit_startpos_window(self):
        self.edit_spawn_window.destroy()
        self.edit_spawn_window = None

    @catch_exception
    def action_save_startpos(self):
        pos, direction = self.edit_spawn_window.get_pos_dir()
        self.pikmin_gen_file.startpos_x = pos[0]
        self.pikmin_gen_file.startpos_y = pos[1]
        self.pikmin_gen_file.startpos_z = pos[2]
        self.pikmin_gen_file.startdir = direction

        self.pikmin_gen_view.update()

    def button_open_add_item_window(self):
        if self.add_object_window is None:
            self.add_object_window = pikwidgets.AddPikObjectWindow()
            self.add_object_window.button_savetext.pressed.connect(self.button_add_item_window_save)
            self.add_object_window.closing.connect(self.button_add_item_window_close)
            self.add_object_window.show()
        elif self.pikmin_gen_view.mousemode == pikwidgets.MOUSE_MODE_ADDWP:
            self.pikmin_gen_view.set_mouse_mode(pikwidgets.MOUSE_MODE_NONE)
            self.pik_control.button_add_object.setChecked(False)

    @catch_exception
    def button_add_item_window_save(self):
        if self.add_object_window is not None:
            self.object_to_be_added = self.add_object_window.get_content()

            if self.object_to_be_added is not None:
                self.pik_control.button_add_object.setChecked(True)
                self.pik_control.button_move_object.setChecked(False)
                self.pikmin_gen_view.set_mouse_mode(pikwidgets.MOUSE_MODE_ADDWP)
                self.add_object_window.destroy()
                self.add_object_window = None
                self.pikmin_gen_view.setContextMenuPolicy(Qt.DefaultContextMenu)

    @catch_exception
    def button_add_item_window_close(self):
        # self.add_object_window.destroy()
        self.add_object_window = None
        self.pik_control.button_add_object.setChecked(False)
        self.pikmin_gen_view.set_mouse_mode(pikwidgets.MOUSE_MODE_NONE)
        print("okdone")

    @catch_exception
    def action_add_object(self, x, z):
        newobj = self.object_to_be_added.copy()

        newobj.position_x = newobj.x = x
        newobj.position_z = newobj.z = z
        newobj.offset_x = newobj.offset_z = 0.0

        self.pikmin_gen_file.objects.append(newobj)
        self.pikmin_gen_view.update()

        self.history.add_history_addobject(newobj)

    def button_move_objects(self):
        if self.pikmin_gen_view.mousemode == pikwidgets.MOUSE_MODE_MOVEWP:
            self.pikmin_gen_view.set_mouse_mode(pikwidgets.MOUSE_MODE_NONE)
        else:
            self.pikmin_gen_view.set_mouse_mode(pikwidgets.MOUSE_MODE_MOVEWP)

    @catch_exception
    def action_move_objects(self, deltax, deltaz):
        for obj in self.pikmin_gen_view.selected:
            obj.x += deltax
            obj.z += deltaz
            obj.position_x = obj.x
            obj.position_z = obj.z
            obj.offset_x = 0
            obj.offset_z = 0

            if self.editorconfig["GroundObjectsWhenMoving"] is True:
                if self.pikmin_gen_view.collision is not None:
                    y = self.pikmin_gen_view.collision.collide_ray_downwards(obj.x, obj.z)
                    obj.y = obj.position_y = y
                    obj.offset_y = 0

        if len(self.pikmin_gen_view.selected) == 1:
            obj = self.pikmin_gen_view.selected[0]
            self.pik_control.set_info(obj, (obj.x, obj.y, obj.z), obj.get_rotation())

        self.pikmin_gen_view.update()

    def action_ground_objects(self):
        for obj in self.pikmin_gen_view.selected:
            if self.pikmin_gen_view.collision is None:
                return None
            height = self.pikmin_gen_view.collision.collide_ray_downwards(obj.x, obj.z)

            if height is not None:
                obj.position_y = obj.y = height
                obj.offset_y = 0.0

        if len(self.pikmin_gen_view.selected) == 1:
            obj = self.pikmin_gen_view.selected[0]
            self.pik_control.set_info(obj, (obj.x, obj.y, obj.z), obj.get_rotation())

    def action_delete_objects(self):
        tobedeleted = []
        for obj in self.pikmin_gen_view.selected:
            self.pikmin_gen_file.objects.remove(obj)
            tobedeleted.append(obj)
        self.pikmin_gen_view.selected = []

        self.pik_control.reset_info()
        self.pikmin_gen_view.update()
        self.history.add_history_removeobjects(tobedeleted)

    @catch_exception
    def action_undo(self):
        res = self.history.history_undo()
        if res is None:
            return
        action, val = res

        if action == "AddObject":
            obj = val
            self.pikmin_gen_file.objects.remove(obj)
            if len(self.pikmin_gen_view.selected) == 1 and self.pikmin_gen_view.selected[0] is obj:
                self.pik_control.reset_info()
            if obj in self.pikmin_gen_view.selected:
                self.pikmin_gen_view.selected.remove(obj)

            self.pikmin_gen_view.update()

        if action == "RemoveObjects":
            for obj in val:
                self.pikmin_gen_file.objects.append(obj)

            self.pikmin_gen_view.update()

    @catch_exception
    def action_redo(self):
        res = self.history.history_redo()
        if res is None:
            return

        action, val = res

        if action == "AddObject":
            obj = val
            self.pikmin_gen_file.objects.append(obj)

            self.pikmin_gen_view.update()

        if action == "RemoveObjects":
            for obj in val:
                self.pikmin_gen_file.objects.remove(obj)
                if len(self.pikmin_gen_view.selected) == 1 and self.pikmin_gen_view.selected[0] is obj:
                    self.pik_control.reset_info()
                if obj in self.pikmin_gen_view.selected:
                    self.pikmin_gen_view.selected.remove(obj)

            self.pikmin_gen_view.update()

    def button_load_collision_grid(self):
        try:
            filepath, choosentype = QFileDialog.getOpenFileName(
                self, "Open File",
                self.pathsconfig["collision"],
                "Archived grid.bin (texts.arc, texts.szs);;Grid.bin (*.bin);;All files (*)")

            if (choosentype == "Archived grid.bin (texts.arc, texts.szs)"
                    or filepath.endswith(".szs")
                    or filepath.endswith(".arc")):
                load_from_arc = True
            else:
                load_from_arc = False

            with open(filepath, "rb") as f:
                if load_from_arc:
                    archive = Archive.from_file(f)
                    f = archive["text/grid.bin"]
                collision = py_obj.PikminCollision(f)

            verts = collision.vertices
            faces = [face[0] for face in collision.faces]

            tmprenderwindow = opengltext.TempRenderWindow(verts, faces)
            tmprenderwindow.show()

            framebuffer = tmprenderwindow.widget.grabFramebuffer()
            framebuffer.save("tmp_image.png", "PNG")
            self.pikmin_gen_view.level_image = framebuffer

            tmprenderwindow.destroy()

            self.pikmin_gen_view.set_collision(verts, faces)
            self.pathsconfig["collision"] = filepath
            save_cfg(self.configuration)

        except:
            traceback.print_exc()

    def create_field_edit_action(self, fieldname):
        attribute = "lineedit_"+fieldname

        @catch_exception
        def change_field(text):
            try:
                #val = float(getattr(self.pik_control, attribute).text())
                val = float(text)
            except Exception as e:
                print(e)
            else:
                if len(self.pikmin_gen_view.selected) == 1:
                    pikobject = self.pikmin_gen_view.selected[0]

                    coord = fieldname[-1]
                    if fieldname.startswith("coordinate"):
                        setattr(pikobject, coord, val)
                        setattr(pikobject, "position_"+coord, val)
                        setattr(pikobject, "offset_"+coord, 0)  # We reset offset to 0 for ease

                    elif fieldname.startswith("rotation"):
                        if pikobject.object_type == "{item}":
                            if coord == "x": pikobject.set_rotation((val, None, None))
                            elif coord == "y": pikobject.set_rotation((None, val, None))
                            elif coord == "z": pikobject.set_rotation((None, None, val))
                            print("rotation set")
                        elif pikobject.object_type == "{teki}":
                            pikobject.set_rotation((None, val, None))
                    self.pikmin_gen_view.update()

        return change_field

    @catch_exception
    def action_open_editwindow(self):
        if self.pikmin_gen_file is not None:
            selected = self.pikmin_gen_view.selected

            if len(self.pikmin_gen_view.selected) == 1:
                currentobj = selected[0]

                if currentobj not in self.editing_windows:
                    self.editing_windows[currentobj] = PikObjectEditor(
                        windowtype="Object {0}".format(currentobj.object_type)
                    )
                    self.editing_windows[currentobj].set_content(currentobj)

                    @catch_exception
                    def action_editwindow_save_data():
                        newobj = self.editing_windows[currentobj].get_content()
                        if newobj is not None:
                            currentobj.from_pikmin_object(newobj)
                            self.pik_control.set_info(currentobj,
                                                      (currentobj.x, currentobj.y, currentobj.z),
                                                      currentobj.get_rotation())
                            self.pikmin_gen_view.update()

                    def action_close_edit_window():
                        print("closing")
                        self.editing_windows[currentobj].destroy()
                        del self.editing_windows[currentobj]

                    self.editing_windows[currentobj].button_savetext.pressed.connect(action_editwindow_save_data)
                    self.editing_windows[currentobj].closing.connect(action_close_edit_window)
                    self.editing_windows[currentobj].show()

                else:
                    self.editing_windows[currentobj].activateWindow()
    @catch_exception
    def action_update_info(self, event):
        if self.pikmin_gen_file is not None:
            selected = self.pikmin_gen_view.selected
            if len(self.pikmin_gen_view.selected) == 1:
                currentobj = selected[0]

                self.pik_control.set_info(currentobj,
                                          (currentobj.x, currentobj.y, currentobj.z),
                                          currentobj.get_rotation())

                if currentobj.object_type == "{teki}":
                    self.pik_control.lineedit_rotationx.setDisabled(True)
                    self.pik_control.lineedit_rotationz.setDisabled(True)

            else:
                self.pik_control.reset_info("{0} objects selected".format(len(self.pikmin_gen_view.selected)))

    @catch_exception
    def mapview_showcontextmenu(self, position):
        context_menu = QMenu(self)
        action = QAction("Copy Coordinates", self)
        action.triggered.connect(self.action_copy_coords_to_clipboard)
        context_menu.addAction(action)
        context_menu.exec(self.mapToGlobal(position))
        context_menu.destroy()

    def action_copy_coords_to_clipboard(self):
        if self.current_coordinates is not None:
            QApplication.clipboard().setText(", ".join(str(x) for x in self.current_coordinates))

    def action_update_position(self, event, pos):
        self.current_coordinates = pos
        self.statusbar.showMessage(str(pos))


class EditorHistory(object):
    def __init__(self, historysize):
        self.history = []
        self.step = 0
        self.historysize = historysize

    def reset(self):
        del self.history
        self.history = []
        self.step = 0

    def _add_history(self, entry):
        if self.step == len(self.history):
            self.history.append(entry)
            self.step += 1
        else:
            for i in range(len(self.history) - self.step):
                self.history.pop()
            self.history.append(entry)
            self.step += 1
            assert len(self.history) == self.step

        if len(self.history) > self.historysize:
            for i in range(len(self.history) - self.historysize):
                self.history.pop(0)
                self.step -= 1

    def add_history_addobject(self, pikobject):
        self._add_history(("AddObject", pikobject))

    def add_history_removeobjects(self, objects):
        self._add_history(("RemoveObjects", objects))

    def history_undo(self):
        if self.step == 0:
            return None

        self.step -= 1
        return self.history[self.step]

    def history_redo(self):
        if self.step == len(self.history):
            return None

        item = self.history[self.step]
        self.step += 1
        return item




if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)


    pikmin_gui = GenEditor()

    pikmin_gui.show()
    err_code = app.exec()
    #traceback.print_exc()
    sys.exit(err_code)