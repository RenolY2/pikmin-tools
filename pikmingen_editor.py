import traceback

import PyQt5.QtWidgets as QtWidgets
import PyQt5.QtCore as QtCore

from PyQt5.QtCore import QSize, QRect, QMetaObject, QCoreApplication, QPoint
from PyQt5.QtWidgets import (QWidget, QMainWindow, QFileDialog,
                             QSpacerItem, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QHBoxLayout,
                             QScrollArea, QGridLayout, QMenuBar, QMenu, QAction, QApplication, QStatusBar, QLineEdit)
from PyQt5.QtGui import QMouseEvent, QImage

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
        self.pikmin_gen_file = None
        self.setup_ui()

        try:
            self.configuration = read_config()
            print("config loaded")
        except FileNotFoundError as e:
            print(e)
            print("creating file...")
            self.configuration = make_default_config()
        #self.ground_wp_when_moving = self.configuration["ROUTES EDITOR"].getboolean("groundwaypointswhenmoving")

        self.pathsconfig = self.configuration["default paths"]
        self.editorconfig = self.configuration["routes editor"]
        #self.pikminroutes_screen.editorconfig = self.editorconfig

        self.current_coordinates = None
        self.editing_windows = {}
        self.add_object_window = None

    def reset(self):
        pass

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
                except Exception as error:
                    print("error", error)
                    traceback.print_exc()

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

        self.file_load_action = QAction("Load", self)
        self.file_load_action.triggered.connect(self.button_load_level)
        self.file_menu.addAction(self.file_load_action)
        self.file_menu.setTitle("File")

        # ------ Collision Menu
        self.collision_menu = QMenu(self.menubar)
        self.collision_load_action = QAction("Load .OBJ", self)
        self.collision_load_action.triggered.connect(self.button_load_collision)
        self.collision_menu.addAction(self.collision_load_action)
        self.collision_load_grid_action = QAction("Load GRID.BIN", self)
        #self.collision_load_grid_action.triggered.connect(self.button_load_collision_grid)
        self.collision_menu.addAction(self.collision_load_grid_action)
        self.collision_menu.setTitle("Geometry")

        self.menubar.addAction(self.file_menu.menuAction())
        self.menubar.addAction(self.collision_menu.menuAction())
        self.setMenuBar(self.menubar)

    def setup_ui_toolbar(self):
        self.toolbar = QtWidgets.QToolBar("Test", self)
        self.toolbar.addAction(QAction("TestToolbar", self))
        self.toolbar.addAction(QAction("TestToolbar2", self))
        self.toolbar.addAction(QAction("TestToolbar3", self))

        self.toolbar2 = QtWidgets.QToolBar("Second Toolbar", self)
        self.toolbar2.addAction(QAction("I like cake", self))

        self.addToolBar(self.toolbar)
        self.addToolBarBreak()
        self.addToolBar(self.toolbar2)

    def connect_actions(self):
        self.pikmin_gen_view.select_update.connect(self.action_update_info)
        self.pik_control.lineedit_coordinatex.editingFinished.connect(self.create_field_edit_action("coordinatex"))
        self.pik_control.lineedit_coordinatey.editingFinished.connect(self.create_field_edit_action("coordinatey"))
        self.pik_control.lineedit_coordinatez.editingFinished.connect(self.create_field_edit_action("coordinatez"))

        self.pik_control.lineedit_rotationx.editingFinished.connect(self.create_field_edit_action("rotationx"))
        self.pik_control.lineedit_rotationy.editingFinished.connect(self.create_field_edit_action("rotationy"))
        self.pik_control.lineedit_rotationz.editingFinished.connect(self.create_field_edit_action("rotationz"))

        self.pikmin_gen_view.position_update.connect(self.action_update_position)

        self.pikmin_gen_view.customContextMenuRequested.connect(self.mapview_showcontextmenu)
        self.pik_control.button_edit_object.pressed.connect(self.action_open_editwindow)

        self.pik_control.button_add_object.pressed.connect(self.button_open_add_item_window)

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

    def button_open_add_item_window(self):
        if self.add_object_window is None:
            self.add_object_window = pikwidgets.AddPikObjectWindow()
            self.add_object_window.show()

    def button_load_collision_grid(self):
        try:
            filepath, choosentype = QFileDialog.getOpenFileName(
                self, "Open File",
                self.pathsconfig["collision"],
                "Grid.bin (*.bin);;Archived grid.bin (texts.arc, texts.szs);;All files (*)")
            print(choosentype)

            if choosentype == "Archived grid.bin (texts.arc, texts.szs)" or filepath.endswith(".szs") or filepath.endswith(".arc"):
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
            self.pikminroutes_screen.level_image = framebuffer

            tmprenderwindow.destroy()

            self.pikminroutes_screen.set_collision(verts, faces)
            self.pathsconfig["routes"] = filepath
            save_cfg(self.configuration)

        except:
            traceback.print_exc()

    def create_field_edit_action(self, fieldname):
        attribute = "lineedit_"+fieldname

        @catch_exception
        def change_field():
            try:
                val = float(getattr(self.pik_control, attribute).text())
            except Exception as e:
                print(e)
            else:
                print("hi")
                if len(self.pikmin_gen_view.selected) == 1:
                    pikobject = self.pikmin_gen_view.selected[0]

                    coord = fieldname[-1]
                    if fieldname.startswith("coordinate"):
                        setattr(pikobject, coord, val)
                        setattr(pikobject, "position_"+coord, val)
                        setattr(pikobject, "offset_"+coord, 0)  # We reset offset to 0 for ease

                        self.pikmin_gen_view.update()
                    elif fieldname.startswith("rotation"):
                        if pikobject.object_type == "{item}":
                            if coord == "x": pikobject.set_rotation((val, None, None))
                            elif coord == "y": pikobject.set_rotation((None, val, None))
                            elif coord == "z": pikobject.set_rotation((None, None, val))
                            print("rotation set")
                        elif pikobject.object_type == "{teki}":
                            pikobject.set_rotation((None, val, None))

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
                            self.pik_control.set_info(currentobj.object_type,
                                                      (currentobj.x, currentobj.y, currentobj.z),
                                                      currentobj.get_rotation())
                            self.pikmin_gen_view.update()

                    self.editing_windows[currentobj].button_savetext.pressed.connect(action_editwindow_save_data)

                    self.editing_windows[currentobj].show()




    @catch_exception
    def action_update_info(self, event):
        if self.pikmin_gen_file is not None:
            selected = self.pikmin_gen_view.selected
            if len(self.pikmin_gen_view.selected) == 1:
                currentobj = selected[0]

                self.pik_control.set_info(currentobj.object_type,
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
        pass
        print("foobar", self.current_coordinates)

        QApplication.clipboard().setText(", ".join(str(x) for x in self.current_coordinates))

    def action_update_position(self, event, pos):
        self.current_coordinates = pos
        self.statusbar.showMessage(str(pos))

if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)


    pikmin_gui = GenEditor()

    pikmin_gui.show()
    err_code = app.exec()
    #traceback.print_exc()
    sys.exit(err_code)