# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'bw_gui_prototype.ui'
#
# Created by: PyQt5 UI code generator 5.5.1
#
# WARNING! All changes made in this file will be lost!
from libpiktxt import RouteTxt
import traceback
import itertools
import gzip
from copy import copy, deepcopy
import os
from os import path
from timeit import default_timer
from math import atan2, degrees, radians, sin, cos

from PyQt5.QtCore import QSize, QRect, QMetaObject, QCoreApplication, QPoint
from PyQt5.QtWidgets import (QWidget, QMainWindow, QFileDialog,
                             QSpacerItem, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QHBoxLayout,
                             QScrollArea, QGridLayout, QMenuBar, QMenu, QAction, QApplication, QStatusBar, QLineEdit)
from PyQt5.QtGui import QMouseEvent, QImage
import PyQt5.QtWidgets as QtWidgets
import PyQt5.QtCore as QtCore


"""
from res_tools.bw_archive_base import BWArchiveBase

from lib.bw_read_xml import BattWarsLevel, BattWarsObject"""
import custom_widgets
from custom_widgets import (MenuDontClose, BWMapViewer,
                            catch_exception, CheckableButton,
                            SHOW_TERRAIN_LIGHT, SHOW_TERRAIN_NO_TERRAIN, SHOW_TERRAIN_REGULAR)

from opengltext import TempRenderWindow

from helper_functions import (calc_zoom_in_factor, calc_zoom_out_factor,
                                  get_default_path, set_default_path, update_mapscreen,
                                  bw_coords_to_image_coords, image_coords_to_bw_coords,
                                  entity_get_army, entity_get_icon_type, entity_get_model,
                                  object_set_position, object_get_position, get_position_attribute, get_type,
                                  parse_terrain_to_image, get_water_height)

from py_obj import read_obj

PIKMIN2PATHS = "Carrying path files (route.txt)"
#BW_COMPRESSED_LEVEL = "BW compressed level files (*_level.xml.gz)"

class EditorMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setupUi(self)
        self.retranslateUi(self)
        path = get_default_path()
        if path is None:
            self.default_path = ""
        else:
            self.default_path = path
        self.default_collision_path = ""
        self.pikmin_routes = None
        self.collision = None

        self.button_delete_waypoints.pressed.connect(self.action_button_delete_wp)
        self.button_ground_waypoints.pressed.connect(self.action_button_ground_wp)
        self.button_move_waypoints.pressed.connect(self.action_button_move_wp)
        self.button_add_waypoint.pressed.connect(self.action_button_add_wp)
        self.button_connect_waypoints.pressed.connect(self.action_button_connect_wp)

        """
        self.level = None
        path = get_default_path()
        if path is None:
            self.default_path = ""
        else:
            self.default_path = path

        self.dragging = False
        self.last_x = None
        self.last_y = None
        self.dragged_time = None
        self.deleting_item = False # Hack for preventing focusing on next item after deleting the previous one

        self.moving = False

        self.resetting = False

        self.entity_list_widget.currentItemChanged.connect(self.action_listwidget_change_selection)
        self.button_zoom_in.pressed.connect(self.zoom_in)
        self.button_zoom_out.pressed.connect(self.zoom_out)
        self.button_remove_entity.pressed.connect(self.remove_position)
        self.button_move_entity.pressed.connect(self.move_entity)
        self.button_clone_entity.pressed.connect(self.action_clone_entity)
        self.button_show_passengers.pressed.connect(self.action_passenger_window)
        self.button_edit_xml.pressed.connect(self.action_open_xml_editor)
        self.button_edit_base_xml.pressed.connect(self.action_open_basexml_editor)
        self.lineedit_angle.editingFinished.connect(self.action_lineedit_changeangle)


        self.bw_map_screen.mouse_clicked.connect(self.get_position)
        self.bw_map_screen.entity_clicked.connect(self.entity_position)
        self.bw_map_screen.mouse_dragged.connect(self.mouse_move)
        self.bw_map_screen.mouse_released.connect(self.mouse_release)
        self.bw_map_screen.mouse_wheel.connect(self.mouse_wheel_scroll_zoom)


        status = self.statusbar
        self.bw_map_screen.setMouseTracking(True)

        self.passenger_window = BWPassengerWindow()
        self.passenger_window.passengerlist.currentItemChanged.connect(self.passengerwindow_action_choose_entity)

        self.xmlobject_textbox = BWEntityXMLEditor()
        self.xmlobject_textbox.button_xml_savetext.pressed.connect(self.xmleditor_action_save_object_xml)
        self.xmlobject_textbox.triggered.connect(self.action_open_xml_editor_unlimited)


        self.basexmlobject_textbox = BWEntityXMLEditor(windowtype="XML Base Object")
        self.basexmlobject_textbox.button_xml_savetext.pressed.connect(self.xmleditor_action_save_base_object_xml)
        self.basexmlobject_textbox.triggered.connect(self.action_open_xml_editor_unlimited)

        self.types_visible = {}
        self.terrain_image = None

        status.showMessage("Ready")

        self.xml_windows = {}"""
        print("We are now ready!")

    def reset(self):
        self.resetting = True
        self.statusbar.clearMessage()
        self.dragged_time = None
        self.moving = False
        self.dragging = False
        self.last_x = None
        self.last_y = None
        self.dragged_time = None

        self.moving = False
        self.pikminroutes_screen.reset()


        self.resetting = False

        print("reset done")

    def destroy_xml_editor(self, id):
        pass

    @catch_exception
    def open_xml_editor(self, objectid, offsetx=0, offsety=0):
        selected = objectid
        if self.level is not None and selected in self.level.obj_map:
            delete = []
            for objid, window in self.xml_windows.items():
                if not window.isVisible() and objid != selected:
                    window.destroy()
                    delete.append(objid)
            for objid in delete:
                del self.xml_windows[objid]

            if selected == self.basexmlobject_textbox.entity or selected == self.xmlobject_textbox.entity:
                pass # No need to make a new window
            elif selected in self.xml_windows and self.xml_windows[selected].isVisible():
                self.xml_windows[selected].activateWindow()
                self.xml_windows[selected].update()

            else:
                xml_window = BWEntityXMLEditor()

                def xmleditor_save_object_unlimited():
                    self.statusbar.showMessage("Saving object changes...")
                    try:
                        xmlnode = xml_window.get_content()
                        #assert self.bw_map_screen.current_entity == self.basexmlobject_textbox.entity
                        assert xml_window.entity == xmlnode.get("id")  # Disallow changing the id of the base object

                        self.level.remove_object(xmlnode.get("id"))
                        self.level.add_object(xmlnode)

                        self.statusbar.showMessage("Saved base object {0} as {1}".format(
                            xml_window.entity, self.level.obj_map[xmlnode.get("id")].name))
                    except:
                        self.statusbar.showMessage("Saving object failed")
                        traceback.print_exc()

                xml_window.button_xml_savetext.pressed.connect(xmleditor_save_object_unlimited)
                xml_window.triggered.connect(self.action_open_xml_editor_unlimited)


                obj = self.level.obj_map[selected]
                xml_window.set_title(obj.name)

                xml_window.set_content(obj._xml_node)
                #xml_window.move(QPoint(xml_editor_owner.pos().x()+20, xml_editor_owner.pos().y()+20))
                xml_window.move(QPoint(offsetx, offsety))

                xml_window.show()
                xml_window.update()
                self.xml_windows[selected] = xml_window



    @catch_exception
    def action_open_xml_editor_unlimited(self, xml_editor_owner):
        selected = xml_editor_owner.textbox_xml.textCursor().selectedText()
        self.open_xml_editor(selected,
                             offsetx=xml_editor_owner.pos().x()+20,
                             offsety=xml_editor_owner.pos().y()+20)

    @catch_exception
    def action_open_basexml_editor(self):
        """
        if not self.basexmlobject_textbox.isVisible():
            self.basexmlobject_textbox.destroy()
            self.basexmlobject_textbox = BWEntityXMLEditor(windowtype="XML Base Object")
            self.basexmlobject_textbox.button_xml_savetext.pressed.connect(self.xmleditor_action_save_base_object_xml)
            self.basexmlobject_textbox.triggered.connect(self.action_open_xml_editor_unlimited)
            self.basexmlobject_textbox.show()

        self.basexmlobject_textbox.activateWindow()"""
        if self.level is not None and self.bw_map_screen.current_entity is not None:
            obj = self.level.obj_map[self.bw_map_screen.current_entity]
            if not obj.has_attr("mBase"):
                pass
            else:
                baseobj = self.level.obj_map[obj.get_attr_value("mBase")]
                #self.basexmlobject_textbox.set_title(baseobj.id)
                self.open_xml_editor(baseobj.id)

    def xmleditor_action_save_base_object_xml(self):
        self.statusbar.showMessage("Saving base object changes...")
        try:
            xmlnode = self.basexmlobject_textbox.get_content()
            #assert self.bw_map_screen.current_entity == self.basexmlobject_textbox.entity
            assert self.basexmlobject_textbox.entity == xmlnode.get("id")  # Disallow changing the id of the base object

            self.level.remove_object(xmlnode.get("id"))
            self.level.add_object(xmlnode)

            self.statusbar.showMessage("Saved base object {0} as {1}".format(
                self.basexmlobject_textbox.entity, self.level.obj_map[xmlnode.get("id")].name))
        except:
            self.statusbar.showMessage("Saving base object failed")
            traceback.print_exc()

    def button_load_level(self):
        try:
            print("ok", self.default_path)

            filepath, choosentype = QFileDialog.getOpenFileName(
                self, "Open File",
                self.default_path,
                PIKMIN2PATHS+";;All files (*)")
            print("doooone")
            if filepath:
                print("resetting")
                self.reset()
                print("done")
                print("chosen type:",choosentype)

                with open(filepath, "r") as f:
                    try:
                        self.pikmin_routes = RouteTxt()
                        self.pikmin_routes.from_file(f)
                        self.default_path = filepath
                        set_default_path(filepath)

                        """for wp_index, waypoint in enumerate(self.pikmin_routes.waypoints):
                            x,y,z, radius = waypoint
                            self.pikminroutes_screen.add_waypoint(x, z, wp_index, update=False, metadata=[y, radius])

                        for wp_index, waypoints in self.pikmin_routes.links.items():
                            for dest_waypoint in waypoints:
                                self.pikminroutes_screen.add_path(wp_index, dest_waypoint)"""

                        self.pikminroutes_screen.pikmin_routes = self.pikmin_routes
                        self.pikminroutes_screen.update()

                        #for obj_id, obj in sorted(self.level.obj_map.items(),
                        #                          key=lambda x: get_type(x[1].type)+x[1].type+x[1].id):
                        if False:
                            #print("doing", obj_id)
                            if get_position_attribute(obj) is None:
                                continue
                            #if not obj.has_attr("Mat"):
                            #    continue
                            x, y, angle = object_get_position(self.level, obj_id)
                            assert type(x) != str
                            x, y = bw_coords_to_image_coords(x, y)

                            item = BWEntityEntry(obj_id, "{0}[{1}]".format(obj_id, obj.type))
                            self.entity_list_widget.addItem(item)

                            self.bw_map_screen.add_entity(x, y, obj_id, obj.type, update=False)
                            #if obj.type == "cMapZone":
                            update_mapscreen(self.bw_map_screen, obj)

                        print("ok")
                        #self.bw_map_screen.update()
                        path_parts = path.split(filepath)
                        self.setWindowTitle("Routes Editor - {0}".format(filepath))

                    except Exception as error:
                        print("error", error)
                        traceback.print_exc()

        except Exception as er:
            print("errrorrr", er)
            traceback.print_exc()
        print("loaded")

    def button_save_level(self):
        if self.level is not None:
            filepath, choosentype = QFileDialog.getSaveFileName(
                self, "Save File",
                self.default_path,
                BW_LEVEL+";;"+BW_COMPRESSED_LEVEL+";;All files (*)")
            print(filepath, "saved")

            if filepath:
                # Simiar to load level
                if choosentype == BW_COMPRESSED_LEVEL or filepath.endswith(".gz"):
                    file_open = gzip.open
                else:
                    file_open = open
                try:
                    with file_open(filepath, "wb") as f:
                        self.level._tree.write(f)
                except Exception as error:
                    print("COULDN'T SAVE:", error)
                    traceback.print_exc()

                self.default_path = filepath
        else:
            pass # no level loaded, do nothing


    def button_load_collision(self):
        try:
            filepath, choosentype = QFileDialog.getOpenFileName(
                self, "Open File",
                self.default_collision_path,
                "Collision (*.obj);;All files (*)")
            with open(filepath, "r") as f:
                verts, faces, normals = read_obj(f)

            tmprenderwindow = TempRenderWindow(verts, faces)
            tmprenderwindow.show()

            framebuffer = tmprenderwindow.widget.grabFramebuffer()
            framebuffer.save("tmp_image.png", "PNG")
            self.pikminroutes_screen.level_image = framebuffer

            tmprenderwindow.destroy()

            self.pikminroutes_screen.set_collision(verts, faces)


        except:
            traceback.print_exc()

    @catch_exception
    def event_update_lineedit(self, event):
        if len(self.pikminroutes_screen.selected_waypoints) == 1:
            for waypoint in self.pikminroutes_screen.selected_waypoints:
                x, y, z, radius = self.pikmin_routes.waypoints[waypoint]

                self.lineedit_xcoordinate.setText(str(x))
                self.lineedit_ycoordinate.setText(str(y))
                self.lineedit_zcoordinate.setText(str(z))
                self.lineedit_radius.setText(str(radius))

    def set_entity_text_multiple(self, entities):
        self.label_object_id.setText("{0} objects selected".format(len(entities)))
        MAX = 15
        listentities = [self.level.obj_map[x].name for x in sorted(entities.keys())][0:MAX]
        listentities.sort()
        if len(entities) > MAX:
            listentities.append("... and {0} more".format(len(entities) - len(listentities)))
        self.label_position.setText("\n".join(listentities[:5]))
        self.label_model_name.setText("\n".join(listentities[5:10]))
        self.label_4.setText("\n".join(listentities[10:]))#15]))
        self.label_5.setText("")#("\n".join(listentities[12:16]))

    def set_entity_text(self, entityid):
        try:
            obj = self.level.obj_map[entityid]
            if obj.has_attr("mBase"):
                base = self.level.obj_map[obj.get_attr_value("mBase")]
                self.label_object_id.setText("{0}\n[{1}]\nBase: {2}\n[{3}]".format(
                    entityid, obj.type, base.id, base.type))
            else:
                self.label_object_id.setText("{0}\n[{1}]".format(entityid, obj.type))
            self.label_model_name.setText("Model: {0}".format(entity_get_model(self.level, entityid)))
            x, y, angle = object_get_position(self.level, entityid)
            self.label_position.setText("x: {0}\ny: {1}".format(x, y))
            self.lineedit_angle.setText(str(round(angle,2)))
            self.label_4.setText("Army: {0}".format(entity_get_army(self.level, entityid)))
            if not obj.has_attr("mPassenger"):
                self.label_5.setText("Icon Type: \n{0}".format(entity_get_icon_type(self.level, entityid)))
            else:

                passengers = 0
                for passenger in obj.get_attr_elements("mPassenger"):
                    if passenger != "0":
                        passengers += 1
                self.label_5.setText("Icon Type: \n{0}\n\nPassengers: {1}".format(
                    entity_get_icon_type(self.level, entityid), passengers))
        except:
            traceback.print_exc()

    def action_lineedit_changeangle(self):
        if not self.resetting and self.bw_map_screen.current_entity is not None:
            print("ok")
            current = self.bw_map_screen.current_entity
            currx, curry, angle = object_get_position(self.level, current)

            newangle = self.lineedit_angle.text().strip()
            print(newangle, newangle.isdecimal())
            try:
                angle = float(newangle)
                object_set_position(self.level, current, currx, curry, angle=angle)
                currentobj = self.level.obj_map[current]
                update_mapscreen(self.bw_map_screen, currentobj)
                self.bw_map_screen.update()
            except:
                traceback.print_exc()

    def event_update_position(self, event, position):
        x,y,z = position
        if y is None:
            y = "-"
        coordtext = "X: {}, Y: {}, Z: {}".format(x,y,z)
        self.statusbar.showMessage(coordtext)
        #print(coordtext)

    @catch_exception
    def action_button_delete_wp(self):
        if self.pikmin_routes is not None:
            for wp in self.pikminroutes_screen.selected_waypoints:
                self.pikmin_routes.remove_waypoint(wp)
            self.pikminroutes_screen.selected_waypoints = {}
            self.pikminroutes_screen.update()

    def action_button_ground_wp(self):
        if self.pikmin_routes is not None and self.pikminroutes_screen.collision is not None:
            for wp in self.pikminroutes_screen.selected_waypoints:
                x, y, z, radius = self.pikmin_routes.waypoints[wp]

                result = self.pikminroutes_screen.collision.collide_ray_downwards(x, z, y=y)

                if result is not None:
                    point, v1, v2, v3 = result
                    height = point[1]

                    self.pikmin_routes.waypoints[wp][1] = height

            self.pikminroutes_screen.update()

    def action_button_move_wp(self):
        if self.button_move_waypoints.ispushed:

            self.button_move_waypoints.setPushed(False)
            self.pikminroutes_screen.set_mouse_mode(custom_widgets.MOUSE_MODE_NONE)
            self.button_delete_waypoints.setDisabled(False)
        else:
            self.button_add_waypoint.setPushed(False)
            self.button_move_waypoints.setPushed(True)
            self.button_connect_waypoints.setPushed(False)
            self.pikminroutes_screen.set_mouse_mode(custom_widgets.MOUSE_MODE_MOVEWP)
            self.button_delete_waypoints.setDisabled(True)

    def action_button_add_wp(self):
        if self.button_add_waypoint.ispushed:

            self.button_add_waypoint.setPushed(False)
            self.pikminroutes_screen.set_mouse_mode(custom_widgets.MOUSE_MODE_NONE)
            self.button_delete_waypoints.setDisabled(False)
        else:
            self.button_add_waypoint.setPushed(True)
            self.button_move_waypoints.setPushed(False)
            self.button_connect_waypoints.setPushed(False)
            self.pikminroutes_screen.set_mouse_mode(custom_widgets.MOUSE_MODE_ADDWP)
            self.button_delete_waypoints.setDisabled(True)

    def action_button_connect_wp(self):
        if self.button_connect_waypoints.ispushed:

            self.button_connect_waypoints.setPushed(False)
            self.pikminroutes_screen.set_mouse_mode(custom_widgets.MOUSE_MODE_NONE)
            self.button_delete_waypoints.setDisabled(False)
        else:
            self.button_add_waypoint.setPushed(False)
            self.button_move_waypoints.setPushed(False)
            self.button_connect_waypoints.setPushed(True)
            self.pikminroutes_screen.set_mouse_mode(custom_widgets.MOUSE_MODE_CONNECTWP)
            self.button_delete_waypoints.setDisabled(True)

    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(930, 850)
        MainWindow.setMinimumSize(QSize(930, 850))
        MainWindow.setWindowTitle("Pikmin Routes Editor")
        #MainWindow.setWindowTitle("Nep-Nep")


        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        MainWindow.setCentralWidget(self.centralwidget)

        self.horizontalLayout = QHBoxLayout(self.centralwidget)
        self.horizontalLayout.setObjectName("horizontalLayout")


        #self.scrollArea = QScrollArea(self.centralwidget)
        #self.scrollArea.setWidgetResizable(True)

        self.pikminroutes_screen = BWMapViewer(self.centralwidget)
        self.pikminroutes_screen.position_update.connect(self.event_update_position)
        self.pikminroutes_screen.select_update.connect(self.event_update_lineedit)
        #self.scrollArea.setWidget(self.bw_map_screen)
        self.horizontalLayout.addWidget(self.pikminroutes_screen)

        spacerItem = QSpacerItem(10, 20, QSizePolicy.Minimum, QSizePolicy.Expanding)
        self.horizontalLayout.addItem(spacerItem)

        self.vertLayoutWidget = QWidget(self.centralwidget)
        self.vertLayoutWidget.setMaximumSize(QSize(250, 1200))
        self.verticalLayout = QVBoxLayout(self.vertLayoutWidget)
        self.verticalLayout.setObjectName("verticalLayout")

        self.button_add_waypoint = CheckableButton(self.centralwidget)
        self.button_delete_waypoints = QPushButton(self.centralwidget)
        self.button_ground_waypoints = QPushButton(self.centralwidget)
        self.button_move_waypoints = CheckableButton(self.centralwidget)
        self.button_connect_waypoints = CheckableButton(self.centralwidget)

        self.lineedit_xcoordinate = QLineEdit(self.centralwidget)
        self.lineedit_ycoordinate = QLineEdit(self.centralwidget)
        self.lineedit_zcoordinate = QLineEdit(self.centralwidget)
        self.lineedit_radius = QLineEdit(self.centralwidget)


        self.verticalLayout.addWidget(self.button_add_waypoint)
        self.verticalLayout.addWidget(self.button_delete_waypoints)
        self.verticalLayout.addWidget(self.button_ground_waypoints)
        self.verticalLayout.addWidget(self.button_move_waypoints)
        self.verticalLayout.addWidget(self.button_connect_waypoints)

        self.verticalLayout.addWidget(self.lineedit_xcoordinate)
        self.verticalLayout.addWidget(self.lineedit_ycoordinate)
        self.verticalLayout.addWidget(self.lineedit_zcoordinate)
        self.verticalLayout.addWidget(self.lineedit_radius)

        spacerItem1 = QSpacerItem(10, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.verticalLayout.addItem(spacerItem1)

        self.verticalLayout_2 = QVBoxLayout()
        self.verticalLayout_2.setObjectName("verticalLayout_2")


        self.label_waypoint_info = QLabel(self.centralwidget)
        self.label_waypoint_info.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)


        self.verticalLayout_2.addWidget(self.label_waypoint_info)


        self.verticalLayout.addLayout(self.verticalLayout_2)

        self.horizontalLayout.addWidget(self.vertLayoutWidget)

        self.menubar = QMenuBar(MainWindow)
        self.menubar.setGeometry(QRect(0, 0, 820, 29))
        self.menubar.setObjectName("menubar")
        self.file_menu = QMenu(self.menubar)
        self.file_menu.setObjectName("menuLoad")

        # ------
        # File menu buttons
        self.file_load_action = QAction("Load", self)
        self.file_load_action.triggered.connect(self.button_load_level)
        self.file_menu.addAction(self.file_load_action)
        self.file_save_action = QAction("Save", self)
        self.file_save_action.triggered.connect(self.button_save_level)
        self.file_menu.addAction(self.file_save_action)


        # ------ Collision Menu
        self.collision_menu = QMenu(self.menubar)
        self.collision_menu.setObjectName("menuCollision")
        self.collision_load_action = QAction("Load .OBJ", self)
        self.collision_load_action.triggered.connect(self.button_load_collision)
        self.collision_menu.addAction(self.collision_load_action)

        # ----- Set up menu bar and add the file menus
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)
        self.menubar.addAction(self.file_menu.menuAction())
        self.menubar.addAction(self.collision_menu.menuAction())
        self.retranslateUi(MainWindow)
        QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QCoreApplication.translate
        self.file_menu.setTitle(_translate("MainWindow", "File"))
        self.button_add_waypoint.setText("Add Waypoint")
        self.button_connect_waypoints.setText("Connect Waypoint")
        self.button_delete_waypoints.setText("Delete Waypoint(s)")
        self.button_move_waypoints.setText("Move Waypoint(s)")
        self.button_ground_waypoints.setText("Ground Waypoint(s)")
        self.collision_menu.setTitle("Collision")
        """self.button_clone_entity.setText(_translate("MainWindow", "Clone Entity"))
        self.button_remove_entity.setText(_translate("MainWindow", "Delete Entity"))
        self.button_move_entity.setText(_translate("MainWindow", "Move Entity"))
        self.button_zoom_in.setText(_translate("MainWindow", "Zoom In"))
        self.button_zoom_out.setText(_translate("MainWindow", "Zoom Out"))
        self.button_show_passengers.setText(_translate("MainWindow", "Show Passengers"))
        self.button_edit_xml.setText("Edit Object XML")
        self.button_edit_base_xml.setText("Edit Base Object XML")

        self.label_model_name.setText(_translate("MainWindow", "TextLabel1"))
        self.label_object_id.setText(_translate("MainWindow", "TextLabel2"))
        self.label_position.setText(_translate("MainWindow", "TextLabel3"))
        self.label_4.setText(_translate("MainWindow", "TextLabel4"))
        self.label_5.setText(_translate("MainWindow", "TextLabel5"))
        self.file_menu.setTitle(_translate("MainWindow", "File"))
        self.visibility_menu.setTitle(_translate("MainWindow", "Visibility"))
        self.terrain_menu.setTitle("Terrain")"""

if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)


    bw_gui = EditorMainWindow()

    bw_gui.show()
    err_code = app.exec()
    #traceback.print_exc()
    sys.exit(err_code)
