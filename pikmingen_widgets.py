import traceback
import os
from time import sleep
from timeit import default_timer
from io import StringIO
from math import sin, cos, atan2, radians, degrees, pi, tan

from OpenGL.GL import *
from OpenGL.GLU import *

from PyQt5.QtGui import QMouseEvent, QWheelEvent, QPainter, QColor, QFont, QFontMetrics, QPolygon, QImage, QPixmap, QKeySequence
from PyQt5.QtWidgets import (QWidget, QListWidget, QListWidgetItem, QDialog, QMenu, QLineEdit,
                            QMdiSubWindow, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QTextEdit, QAction, QShortcut)
import PyQt5.QtWidgets as QtWidgets
import PyQt5.QtCore as QtCore
from PyQt5.QtCore import QSize, pyqtSignal, QPoint, QRect
from PyQt5.QtCore import Qt
import PyQt5.QtGui as QtGui

from helper_functions import calc_zoom_in_factor, calc_zoom_out_factor

from custom_widgets import (MapViewer, rotate_rel,
                            catch_exception, CheckableButton, Collision)
from pikmingen import PikminObject
from libpiktxt import PikminTxt
from opengltext import draw_collision
from lib.vectors import Matrix4x4, Vector3, Line, Plane, Triangle
import pikmingen
from lib.model_rendering import TexturedPlane

ENTITY_SIZE = 14

DEFAULT_ENTITY = QColor("black")
DEFAULT_MAPZONE = QColor("grey")
DEFAULT_SELECTED = QColor("red")
DEFAULT_ANGLE_MARKER = QColor("blue")

SHOW_TERRAIN_NO_TERRAIN = 0
SHOW_TERRAIN_REGULAR = 1
SHOW_TERRAIN_LIGHT = 2

MOUSE_MODE_NONE = 0
MOUSE_MODE_MOVEWP = 1
MOUSE_MODE_ADDWP = 2
MOUSE_MODE_CONNECTWP = 3

BRIDGE_LENGTHS = {pikmingen.BRIDGE_LONG: 360,
                   pikmingen.BRIDGE_SHORT_UP: 120,
                   pikmingen.BRIDGE_SHORT: 180}

BRIDGE_GRAPHICS = {pikmingen.BRIDGE_SHORT: QtGui.QImage("resources/sbridge.png", "png"),
                   pikmingen.BRIDGE_SHORT_UP: QtGui.QImage("resources/ubridge.png", "png"),
                   pikmingen.BRIDGE_LONG: QtGui.QImage("resources/lbridge.png", "png")}

GATE_GRAPHICS = {pikmingen.GATE_SAND: QtGui.QImage("resources/gate.png", "png"),
                 pikmingen.GATE_ELECTRIC: QtGui.QImage("resources/dgat.png", "png")}

DOWNFLOOR_GRAPHICS = {"0": QtGui.QImage("resources/downfloor1.png"),
                      "1": QtGui.QImage("resources/downfloor2.png"),
                      "2": QtGui.QImage("resources/paperbag.png")}

ONION_COLORTABLE = {pikmingen.ONYN_ROCKET: QColor("grey"),
                    pikmingen.ONYN_BLUEONION: QColor("blue"),
                    pikmingen.ONYN_REDONION: QColor(255, 55, 55),
                    pikmingen.ONYN_YELLOWONION: QColor(255, 212, 0)}

OBJECT_SIZES = {
    pikmingen.ONYN_BLUEONION: 47,
    pikmingen.ONYN_REDONION: 47,
    pikmingen.ONYN_YELLOWONION: 47,
    pikmingen.ONYN_ROCKET: 55,
}


def catch_exception_with_dialog(func):
    def handle(*args, **kwargs):
        try:
            print(args, kwargs)
            return func(*args, **kwargs)
        except Exception as e:
            traceback.print_exc()
            open_error_dialog(str(e), None)
    return handle

def catch_exception_with_dialog_nokw(func):
    def handle(*args, **kwargs):
        try:
            print(args, kwargs)
            return func(*args, **kwargs)
        except Exception as e:
            traceback.print_exc()
            open_error_dialog(str(e), None)
    return handle


MODE_TOPDOWN = 0
MODE_3D = 1

class GenMapViewer(QtWidgets.QOpenGLWidget):
    mouse_clicked = pyqtSignal(QMouseEvent)
    entity_clicked = pyqtSignal(QMouseEvent, str)
    mouse_dragged = pyqtSignal(QMouseEvent)
    mouse_released = pyqtSignal(QMouseEvent)
    mouse_wheel = pyqtSignal(QWheelEvent)
    position_update = pyqtSignal(QMouseEvent, tuple)
    height_update = pyqtSignal(float)
    select_update = pyqtSignal()
    move_points = pyqtSignal(float, float)
    connect_update = pyqtSignal(int, int)
    create_waypoint = pyqtSignal(float, float)
    create_waypoint_3d = pyqtSignal(float, float, float)
    ENTITY_SIZE = ENTITY_SIZE

    rotate_current = pyqtSignal(pikmingen.PikminObject, float)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._zoom_factor = 10
        self.setFocusPolicy(Qt.ClickFocus)

        self.SIZEX = 1024#768#1024
        self.SIZEY = 1024#768#1024

        self.canvas_width, self.canvas_height = self.width(), self.height()

        #self.setMinimumSize(QSize(self.SIZEX, self.SIZEY))
        #self.setMaximumSize(QSize(self.SIZEX, self.SIZEY))
        self.setObjectName("bw_map_screen")

        self.origin_x = self.SIZEX//2
        self.origin_z = self.SIZEY//2

        self.offset_x = 0
        self.offset_z = 0

        self.point_x = 0
        self.point_y = 0
        self.polygon_cache = {}

        # This value is used for switching between several entities that overlap.
        self.next_selected_index = 0

        self.left_button_down = False
        self.mid_button_down = False
        self.right_button_down = False
        self.drag_last_pos = None

        self.current_waypoint = None
        self.selected = []

        self.terrain = None
        self.terrain_scaled = None
        self.terrain_buffer = QImage()

        self.p = QPainter()
        self.p2 = QPainter()
        # self.show_terrain_mode = SHOW_TERRAIN_REGULAR

        self.selectionbox_start = None
        self.selectionbox_end = None

        self.visualize_cursor = None

        self.click_mode = 0

        self.level_image = None

        self.collision = None

        self.highlighttriangle = None

        self.setMouseTracking(True)

        self.pikmin_generators = None
        self.waterboxes = []

        self.mousemode = MOUSE_MODE_NONE

        self.overlapping_wp_index = 0
        self.editorconfig = None

        #self.setContextMenuPolicy(Qt.CustomContextMenu)

        self.spawnpoint = None

        self.shift_is_pressed = False
        self.rotation_is_pressed = False
        self.last_drag_update = 0
        self.change_height_is_pressed = False
        self.last_mouse_move = None

        self.timer = QtCore.QTimer()
        self.timer.setInterval(2)
        self.timer.timeout.connect(self.render_loop)
        self.timer.start()
        self._lastrendertime = 0
        self._lasttime = 0

        self._frame_invalid = False

        self.MOVE_UP = 0
        self.MOVE_DOWN = 0
        self.MOVE_LEFT = 0
        self.MOVE_RIGHT = 0
        self.MOVE_FORWARD = 0
        self.MOVE_BACKWARD = 0
        self.SPEEDUP = 0

        self._wasdscrolling_speed = 1
        self._wasdscrolling_speedupfactor = 3

        self.main_model = None
        self.buffered_deltas = []

        # 3D Setup
        self.mode = MODE_TOPDOWN
        self.camera_horiz = pi*(1/2)
        self.camera_vertical = -pi*(1/4)
        self.camera_height = 1000
        self.last_move = None

        self.selection_queue = []

        self.selectionbox_projected_start = None
        self.selectionbox_projected_end = None

        self.selectionbox_projected_2d = None
        self.selectionbox_projected_origin = None
        self.selectionbox_projected_up = None
        self.selectionbox_projected_right = None
        self.selectionbox_projected_coords = None
        self.last_position_update = 0
        self.move_collision_plane = Plane(Vector3(0.0, 0.0, 0.0), Vector3(1.0, 0.0, 0.0), Vector3(0.0, 1.0, 0.0))

    @catch_exception_with_dialog
    def initializeGL(self):
        self.setup_grid()

        self.testimage = TexturedPlane(100, 100, BRIDGE_GRAPHICS[pikmingen.BRIDGE_SHORT])

        self.bridge_models = {pikmingen.BRIDGE_LONG: TexturedPlane(130, 360+80,
                                                                   QtGui.QImage("resources/lbridge.png", "png")),
                              pikmingen.BRIDGE_SHORT: TexturedPlane(130, 180+80,
                                                                       QtGui.QImage("resources/sbridge.png", "png")),
                              pikmingen.BRIDGE_SHORT_UP: TexturedPlane(130, 120+80,
                                                                       QtGui.QImage("resources/ubridge.png", "png"))}

        self.bridge_models[pikmingen.BRIDGE_SHORT].set_offset(0, (180+80)/2 - 42)
        self.bridge_models[pikmingen.BRIDGE_LONG].set_offset(0, (360+80)/2 - 42)
        self.bridge_models[pikmingen.BRIDGE_SHORT_UP].set_offset(0, (120+80)/2 - 42)

        self.gate_models = {pikmingen.GATE_ELECTRIC: TexturedPlane(267, 35,
                                                                   QtGui.QImage("resources/dgat.png", "png")),
                            pikmingen.GATE_SAND: TexturedPlane(267, 70,
                                                               QtGui.QImage("resources/gate.png", "png"))}
        self.gate_models[pikmingen.GATE_ELECTRIC].set_offset(0, -10)


        self.onion_models = {
            pikmingen.ONYN_BLUEONION: TexturedPlane(47*2, 47*2,
                                                    QtGui.QImage("resources/generic_circle.png", "png")),
            pikmingen.ONYN_REDONION: TexturedPlane(47*2, 47*2,
                                                    QtGui.QImage("resources/generic_circle.png", "png")),
            pikmingen.ONYN_YELLOWONION: TexturedPlane(47*2, 47*2,
                                                    QtGui.QImage("resources/generic_circle.png", "png")),
            pikmingen.ONYN_ROCKET: TexturedPlane(55*2, 55*2,
                                                    QtGui.QImage("resources/generic_circle.png", "png"))
        }

        self.onion_models[pikmingen.ONYN_BLUEONION].set_color((0.0, 0.0, 1.0))
        self.onion_models[pikmingen.ONYN_REDONION].set_color((255/255.0, 55/255.0, 55/255.0))
        self.onion_models[pikmingen.ONYN_YELLOWONION].set_color((255/255.0, 212/255.0, 0.0))
        self.onion_models[pikmingen.ONYN_ROCKET].set_color((0.5, 0.5, 0.5))

        self.downfloor_models = {
            "0": TexturedPlane(100, 100,
                               QtGui.QImage("resources/downfloor1.png", "png")),
            "1": TexturedPlane(150, 120,
                               QtGui.QImage("resources/downfloor2.png", "png")),
            "2": TexturedPlane(256,197,
                               QtGui.QImage("resources/paperbag.png", "png"))
        }

        self.generic_object = TexturedPlane(20*2, 20*2, QtGui.QImage("resources/generic_circle.png", "png"))

        self.rotation_visualizer = glGenLists(1)
        glNewList(self.rotation_visualizer, GL_COMPILE)
        glColor4f(0.0, 0.0, 1.0, 1.0)
        glLineWidth(2.0)
        glBegin(GL_LINES)
        glVertex3f(0.0, 0.0, 0.0)
        glVertex3f(0.0, 40.0, 0.0)
        glEnd()
        glEndList()

    def resizeGL(self, width, height):
        # Called upon window resizing: reinitialize the viewport.
        # update the window size
        self.canvas_width, self.canvas_height = width, height
        # paint within the whole window
        glEnable(GL_DEPTH_TEST)
        glViewport(0, 0, self.canvas_width, self.canvas_height)


        #glMatrixMode(GL_MODELVIEW)
        #glLoadIdentity()

    @catch_exception
    def set_editorconfig(self, config):
        self.editorconfig = config
        self._wasdscrolling_speed = config.getfloat("wasdscrolling_speed")
        self._wasdscrolling_speedupfactor = config.getfloat("wasdscrolling_speedupfactor")

    def change_from_topdown_to_3d(self):
        if self.mode == MODE_3D:
            return
        else:
            self.mode = MODE_3D

            if self.mousemode == MOUSE_MODE_NONE:
                self.setContextMenuPolicy(Qt.DefaultContextMenu)

            # This is necessary so that the position of the 3d camera equals the middle of the topdown view
            self.offset_x *= -1
            self.do_redraw()

    def change_from_3d_to_topdown(self):
        if self.mode == MODE_TOPDOWN:
            return
        else:
            self.mode = MODE_TOPDOWN
            if self.mousemode == MOUSE_MODE_NONE:
                self.setContextMenuPolicy(Qt.CustomContextMenu)

            self.offset_x *= -1
            self.do_redraw()

    @catch_exception
    def render_loop(self):
        now = default_timer()

        diff = now-self._lastrendertime
        timedelta = now-self._lasttime

        if self.mode == MODE_TOPDOWN:
            self.handle_arrowkey_scroll(timedelta)
        else:
            self.handle_arrowkey_scroll_3d(timedelta)

        """if len(self.buffered_deltas) > 0:
            deltax, deltay = self.buffered_deltas.pop(0)
            self.offset_x += deltax
            self.offset_z += deltay
            self._frame_invalid = True"""

        if diff > 1 / 60.0:
            if self._frame_invalid:
                self.update()
                self._lastrendertime = now
                self._frame_invalid = False
        self._lasttime = now

    def handle_arrowkey_scroll(self, timedelta):
        diff_x = diff_y = 0
        #print(self.MOVE_UP, self.MOVE_DOWN, self.MOVE_LEFT, self.MOVE_RIGHT)
        speedup = 1

        if self.shift_is_pressed:
            speedup = self._wasdscrolling_speedupfactor

        if self.MOVE_FORWARD == 1 and self.MOVE_BACKWARD == 1:
            diff_y = 0
        elif self.MOVE_FORWARD == 1:
            diff_y = 1*speedup*self._wasdscrolling_speed*timedelta
        elif self.MOVE_BACKWARD == 1:
            diff_y = -1*speedup*self._wasdscrolling_speed*timedelta

        if self.MOVE_LEFT == 1 and self.MOVE_RIGHT == 1:
            diff_x = 0
        elif self.MOVE_LEFT == 1:
            diff_x = 1*speedup*self._wasdscrolling_speed*timedelta
        elif self.MOVE_RIGHT == 1:
            diff_x = -1*speedup*self._wasdscrolling_speed*timedelta

        if diff_x != 0 or diff_y != 0:
            if self.zoom_factor > 1.0:
                self.offset_x += diff_x * (1.0 + (self.zoom_factor - 1.0) / 2.0)
                self.offset_z += diff_y * (1.0 + (self.zoom_factor - 1.0) / 2.0)
            else:
                self.offset_x += diff_x
                self.offset_z += diff_y
            # self.update()

            self.do_redraw()

    def handle_arrowkey_scroll_3d(self, timedelta):
        if self.selectionbox_projected_origin is not None:
            return

        diff_x = diff_y = diff_height = 0
        #print(self.MOVE_UP, self.MOVE_DOWN, self.MOVE_LEFT, self.MOVE_RIGHT)
        speedup = 1

        forward_vec = Vector3(cos(self.camera_horiz), sin(self.camera_horiz), 0)
        sideways_vec = Vector3(sin(self.camera_horiz), -cos(self.camera_horiz), 0)

        if self.shift_is_pressed:
            speedup = self._wasdscrolling_speedupfactor

        if self.MOVE_FORWARD == 1 and self.MOVE_BACKWARD == 1:
            forward_move = forward_vec*0
        elif self.MOVE_FORWARD == 1:
            forward_move = forward_vec*(1*speedup*self._wasdscrolling_speed*timedelta)
        elif self.MOVE_BACKWARD == 1:
            forward_move = forward_vec*(-1*speedup*self._wasdscrolling_speed*timedelta)
        else:
            forward_move = forward_vec*0

        if self.MOVE_LEFT == 1 and self.MOVE_RIGHT == 1:
            sideways_move = sideways_vec*0
        elif self.MOVE_LEFT == 1:
            sideways_move = sideways_vec*(-1*speedup*self._wasdscrolling_speed*timedelta)
        elif self.MOVE_RIGHT == 1:
            sideways_move = sideways_vec*(1*speedup*self._wasdscrolling_speed*timedelta)
        else:
            sideways_move = sideways_vec*0

        if self.MOVE_UP == 1 and self.MOVE_DOWN == 1:
            diff_height = 0
        elif self.MOVE_UP == 1:
            diff_height = 1*speedup*self._wasdscrolling_speed*timedelta
        elif self.MOVE_DOWN == 1:
            diff_height = -1 * speedup * self._wasdscrolling_speed * timedelta

        if not forward_move.is_zero() or not sideways_move.is_zero() or diff_height != 0:
            #if self.zoom_factor > 1.0:
            #    self.offset_x += diff_x * (1.0 + (self.zoom_factor - 1.0) / 2.0)
            #    self.offset_z += diff_y * (1.0 + (self.zoom_factor - 1.0) / 2.0)
            #else:
            self.offset_x += (forward_move.x + sideways_move.x)
            self.offset_z += (forward_move.y + sideways_move.y)
            self.camera_height += diff_height
            # self.update()

            self.do_redraw()

    def set_arrowkey_movement(self, up, down, left, right):
        self.MOVE_UP = up
        self.MOVE_DOWN = down
        self.MOVE_LEFT = left
        self.MOVE_RIGHT = right

    def do_redraw(self):
        self._frame_invalid = True

    def set_visibility(self, visibility):
        self.visibility_toggle = visibility

    def resize_map(self, newsizex, newsizey):
        self.SIZEX = newsizex
        self.SIZEY = newsizey
        self.origin_x = self.SIZEX // 2
        self.origin_z = self.SIZEY // 2

    def reset(self, keep_collision=False):
        self.overlapping_wp_index = 0
        self.shift_is_pressed = False
        self.SIZEX = 1024
        self.SIZEY = 1024
        self.origin_x = self.SIZEX//2
        self.origin_z = self.SIZEY//2
        self.last_drag_update = 0

        self.left_button_down = False
        self.mid_button_down = False
        self.right_button_down = False
        self.drag_last_pos = None

        self.selectionbox_start = None
        self.selectionbox_end = None

        self.selected = []

        if not keep_collision:
            # Potentially: Clear collision object too?
            self.level_image = None
            self.offset_x = 0
            self.offset_z = 0
            self._zoom_factor = 10
            #self.waterboxes = []

        self.pikmin_generators = None

        self.mousemode = MOUSE_MODE_NONE
        self.spawnpoint = None
        self.rotation_is_pressed = False

        self._frame_invalid = False

        self.MOVE_UP = 0
        self.MOVE_DOWN = 0
        self.MOVE_LEFT = 0
        self.MOVE_RIGHT = 0
        self.SPEEDUP = 0

    def setup_grid(self):
        offset = +0.2
        self.grid = glGenLists(1)
        glNewList(self.grid, GL_COMPILE)
        glColor3f(0.0, 0.0, 0.0)
        glLineWidth(4.0)
        glBegin(GL_LINES)
        glVertex3f(-6000, 0, offset)
        glVertex3f(6000, 0, offset)

        glVertex3f(0, -6000, offset)
        glVertex3f(0, 6000, offset)
        glEnd()
        glLineWidth(1.0)
        glBegin(GL_LINES)
        for ix in range(-6000, 6000+500, 500):
            glVertex3f(ix, -6000, offset)
            glVertex3f(ix, 6000, offset)

        for iy in range(-6000, 6000+500, 500):
            glVertex3f(-6000, iy, offset)
            glVertex3f(6000, iy, offset)

        glEnd()
        glEndList()

    def set_collision(self, verts, faces):
        self.collision = Collision(verts, faces)

        if self.main_model is None:
            self.main_model = glGenLists(1)

        glNewList(self.main_model, GL_COMPILE)
        #glBegin(GL_TRIANGLES)
        draw_collision(verts, faces)
        #glEnd()
        glEndList()

    def set_mouse_mode(self, mode):
        assert mode in (MOUSE_MODE_NONE, MOUSE_MODE_ADDWP, MOUSE_MODE_CONNECTWP, MOUSE_MODE_MOVEWP)

        self.mousemode = mode

        if self.mousemode == MOUSE_MODE_NONE and self.mode == MODE_TOPDOWN:
            self.setContextMenuPolicy(Qt.CustomContextMenu)
        else:
            self.setContextMenuPolicy(Qt.DefaultContextMenu)

    @property
    def zoom_factor(self):
        return self._zoom_factor/10.0

    def zoom(self, fac):
        if 0.1 < (self.zoom_factor + fac) <= 25:
            self._zoom_factor += int(fac*10)
            #self.update()
            self.do_redraw()

    def mouse_coord_to_world_coord(self, mouse_x, mouse_y):
        zf = self.zoom_factor
        width, height = self.canvas_width, self.canvas_height
        camera_width = width * zf
        camera_height = height * zf

        topleft_x = -camera_width / 2 - self.offset_x
        topleft_y = camera_height / 2 + self.offset_z

        relx = mouse_x / width
        rely = mouse_y / height
        res = (topleft_x + relx*camera_width, topleft_y - rely*camera_height)

        return res

    def mouse_coord_to_world_coord_transform(self, mouse_x, mouse_y):
        mat4x4 = Matrix4x4.from_opengl_matrix(*glGetFloatv(GL_PROJECTION_MATRIX))
        width, height = self.canvas_width, self.canvas_height
        result = mat4x4.multiply_vec4(mouse_x-width/2, mouse_y-height/2, 0, 1)

        return result



    #@catch_exception_with_dialog
    @catch_exception
    def paintGL(self):
        offset_x = self.offset_x
        offset_z = self.offset_z

        #start = default_timer()
        glClearColor(1.0, 1.0, 1.0, 0.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        width, height = self.canvas_width, self.canvas_height

        if self.mode == MODE_TOPDOWN:
            glMatrixMode(GL_PROJECTION)
            glLoadIdentity()
            zf = self.zoom_factor
            #glOrtho(-6000.0, 6000.0, -6000.0, 6000.0, -3000.0, 2000.0)
            camera_width = width*zf
            camera_height = height*zf

            glOrtho(-camera_width / 2 - offset_x, camera_width / 2 - offset_x,
                    -camera_height / 2 + offset_z, camera_height / 2 + offset_z, -3000.0, 2000.0)

            #glScalef(1.0 / zf, 1.0 / zf, 1.0 / zf)

            glMatrixMode(GL_MODELVIEW)
            glLoadIdentity()
        else:
            #glEnable(GL_CULL_FACE)
            # set yellow color for subsequent drawing rendering calls

            glMatrixMode(GL_PROJECTION)
            glLoadIdentity()
            gluPerspective(75, width / height, 1.0, 12800.0)

            glMatrixMode(GL_MODELVIEW)
            glLoadIdentity()

            look_direction = Vector3(cos(self.camera_horiz), sin(self.camera_horiz), sin(self.camera_vertical))
            # look_direction.unify()
            fac = 1.01 - abs(look_direction.z)
            # print(fac, look_direction.z, look_direction)

            gluLookAt(self.offset_x, self.offset_z, self.camera_height,
                      self.offset_x + look_direction.x * fac, self.offset_z + look_direction.y * fac,
                      self.camera_height + look_direction.z,
                      0, 0, 1)

            self.camera_direction = Vector3(look_direction.x * fac, look_direction.y * fac, look_direction.z)


        #glScalef(1.0 / zf, 1.0 / zf, 1.0 / zf)
        #glTranslatef(self.offset_x, -self.offset_z, 0)

        if len(self.selection_queue) > 0:
            click_x, click_y, clickwidth, clickheight, shiftpressed = self.selection_queue.pop(0)
            click_y = height - click_y
            print("Queued test:", click_x, click_y, clickwidth, clickheight)
            if self.pikmin_generators is not None:
                objects = self.pikmin_generators.objects
                for i, pikminobject in enumerate(objects):
                    x, y, z = pikminobject.x, pikminobject.y, pikminobject.z
                    name = pikminobject.get_useful_object_name()

                    glPushMatrix()
                    glTranslatef(x, -z, y + 2)

                    if name in self.onion_models:
                        self.onion_models[name].render_coloredid(i)
                    else:
                        self.generic_object.render_coloredid(i)

                    glPopMatrix()

                pixels = glReadPixels(click_x, click_y, clickwidth, clickheight, GL_RGB, GL_UNSIGNED_BYTE)

                selected ={}
                #for i in range(0, clickwidth*clickheight, 4):
                for x in range(0, clickwidth, 3):
                    for y in range(0, clickheight, 3):
                        i = (x + y*clickwidth)*3
                        index = (pixels[i+1] << 8) | pixels[i+2] # | (pixels[i*3+0] << 16)
                        if index != 0xFFFF:
                            pikminobject = objects[index]
                            selected[pikminobject] = True
                selected = list(selected.keys())
                print("result:", selected)
                if not shiftpressed:
                    self.selected = selected
                    self.select_update.emit()

                elif shiftpressed:
                    for obj in selected:
                        if obj not in self.selected:
                            self.selected.append(obj)
                    self.select_update.emit()


        glClearColor(1.0, 1.0, 1.0, 0.0)

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glEnable(GL_DEPTH_TEST)
        glDisable(GL_TEXTURE_2D)
        glColor4f(1.0, 1.0, 1.0, 1.0)
        if self.main_model is not None:
            #print(self.main_model, type(self.main_model))

            glCallList(self.main_model)


        if self.mode == MODE_TOPDOWN:
            glDisable(GL_DEPTH_TEST)
        glCallList(self.grid)

        if self.mode == MODE_TOPDOWN:
            glDisable(GL_ALPHA_TEST)
            glDisable(GL_TEXTURE_2D)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
            glEnable(GL_BLEND)
            glEnable(GL_DEPTH_TEST)
            for waterbox in self.waterboxes:
                waterbox.render()
            glDisable(GL_DEPTH_TEST)
            glDisable(GL_BLEND)

        glEnable(GL_ALPHA_TEST)

        glAlphaFunc(GL_GEQUAL, 0.5)
        #glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        #self.testimage.render()

        if self.pikmin_generators is not None:
            selected = self.selected
            objects = self.pikmin_generators.objects
            #links = self.pikmin_routes.links
            #for waypoint, wp_info in self.waypoints.items():
            for pikminobject in objects:
                x, y, z = pikminobject.x, pikminobject.y, pikminobject.z

                #glColor3f(1.0, 1.0, 1.0)
                name = pikminobject.get_useful_object_name()
                glPushMatrix()
                glColor4f(1.0, 1.0, 1.0, 1.0)
                if pikminobject.object_type == "{item}":
                    angle = pikminobject.get_horizontal_rotation()
                    glTranslatef(x, -z, y + 1)
                    glRotate(angle + 180, 0, 0, 1)

                    if name in self.bridge_models:
                        model = self.bridge_models[name]
                        model.render()
                    elif name in self.gate_models:
                        model = self.gate_models[name]
                        model.render()
                    else:
                        itemdata = pikminobject._object_data[0]
                        if itemdata[0] == "{dwfl}":
                            downfloortype = itemdata[4]
                            if downfloortype in self.downfloor_models:
                                model = self.downfloor_models[downfloortype]
                                model.render()

                if pikminobject in selected:
                    glColor4f(1.0, 0.0, 0.0, 1.0)
                elif name in self.onion_models:
                    self.onion_models[name].apply_color()
                else:
                    glColor4f(0.0, 0.0, 0.0, 1.0)

                glPopMatrix()
                glPushMatrix()
                glTranslatef(x, -z, y+2)

                angle = pikminobject.get_horizontal_rotation()
                if angle is not None:
                    glRotate(angle + 180, 0, 0, 1)
                if name in self.onion_models:
                    self.onion_models[name].render()
                else:
                    self.generic_object.render()

                if pikminobject in selected:
                    angle = pikminobject.get_horizontal_rotation()
                    if angle is not None:
                        #glRotate(angle + 180, 0, 0, 1)
                        glDisable(GL_ALPHA_TEST)
                        glCallList(self.rotation_visualizer)
                        glEnable(GL_ALPHA_TEST)
                glPopMatrix()

        glDisable(GL_TEXTURE_2D)

        if self.mode != MODE_TOPDOWN:
            glDisable(GL_ALPHA_TEST)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
            glEnable(GL_BLEND)
            glEnable(GL_DEPTH_TEST)
            for waterbox in self.waterboxes:
                waterbox.render()
            glDisable(GL_BLEND)

        glDisable(GL_DEPTH_TEST)
        if self.selectionbox_start is not None and self.selectionbox_end is not None:
            startx, startz = self.selectionbox_start
            endx, endz = self.selectionbox_end
            glColor4f(1.0, 0.0, 0.0, 1.0)
            glLineWidth(2.0)
            glBegin(GL_LINE_LOOP)
            glVertex3f(startx, startz, 0)
            glVertex3f(startx, endz, 0)
            glVertex3f(endx, endz, 0)
            glVertex3f(endx, startz, 0)

            glEnd()

        if self.selectionbox_projected_origin is not None and self.selectionbox_projected_coords:
            origin = self.selectionbox_projected_origin
            point2, point3, point4 = self.selectionbox_projected_coords
            glColor4f(1.0, 0.0, 0.0, 1.0)
            glLineWidth(2.0)

            point1 = origin

            glBegin(GL_LINE_LOOP)
            glVertex3f(point1.x, point1.y, point1.z)
            glVertex3f(point2.x, point2.y, point2.z)
            glVertex3f(point3.x, point3.y, point3.z)
            glVertex3f(point4.x, point4.y, point4.z)
            glEnd()

        glEnable(GL_DEPTH_TEST)
        glFinish()

    @catch_exception
    def mousePressEvent(self, event):
        if self.mode == MODE_TOPDOWN:
            if (event.buttons() & Qt.LeftButton and not self.left_button_down):
                mouse_x, mouse_z = (event.x(), event.y())

                selectstartx, selectstartz = self.mouse_coord_to_world_coord(mouse_x, mouse_z)

                if True: #(self.mousemode == MOUSE_MODE_MOVEWP or self.mousemode == MOUSE_MODE_NONE):
                    self.left_button_down = True
                    self.selectionbox_start = (selectstartx, selectstartz)

                if self.pikmin_generators is not None:
                    hit = False
                    all_hit_waypoints = []
                    for pikminobject in self.pikmin_generators.objects:
                        name = pikminobject.get_useful_object_name()

                        if name in OBJECT_SIZES:
                            size = OBJECT_SIZES[name]
                        else:
                            size = ENTITY_SIZE

                        #if abs(mouse_x-objx) <= size and abs(mouse_z - objz) <= size:
                        if abs(selectstartx-pikminobject.x) <= size//2 and abs(selectstartz+pikminobject.z) <= size//2:
                            # print("hit!")
                            all_hit_waypoints.append(pikminobject)

                    if len(all_hit_waypoints) > 0:
                        wp_index = all_hit_waypoints[self.overlapping_wp_index%len(all_hit_waypoints)]
                        if not self.shift_is_pressed:
                            self.selected = [wp_index]
                        else:
                            if wp_index not in self.selected:
                                self.selected.append(wp_index)
                            else:
                                self.selected.remove(wp_index)

                        # print("hit")
                        hit = True
                        self.select_update.emit()

                        #if self.connect_first_wp is not None and self.mousemode == MOUSE_MODE_CONNECTWP:
                        #    self.connect_update.emit(self.connect_first_wp, wp_index)
                        #self.connect_first_wp = wp_index
                        #self.move_startpos = [wp_index]
                        #self.update()
                        self.do_redraw()
                        self.overlapping_wp_index = (self.overlapping_wp_index+1)%len(all_hit_waypoints)

                    if not hit:
                        if not self.shift_is_pressed:
                            self.selected = []
                        self.select_update.emit()
                        self.connect_first_wp = None
                        self.move_startpos = []
                        #self.update()
                        self.do_redraw()

            if event.buttons() & Qt.MiddleButton and not self.mid_button_down:
                self.mid_button_down = True
                self.drag_last_pos = (event.x(), event.y())

            if event.buttons() & Qt.RightButton:
                self.right_button_down = True

                if self.mousemode == MOUSE_MODE_MOVEWP:
                    mouse_x, mouse_z = (event.x(), event.y())
                    movetox, movetoz = self.mouse_coord_to_world_coord(mouse_x, mouse_z)

                    if self.rotation_is_pressed and len(self.selected) == 1:
                        obj = self.selected[0]
                        relx = obj.x - movetox
                        relz = -obj.z - movetoz

                        self.rotate_current.emit(obj, degrees(atan2(-relx, relz)))

                    elif not self.rotation_is_pressed:
                        if len(self.selected) > 0:
                            sumx, sumz = 0, 0
                            wpcount = len(self.selected)
                            for obj in self.selected:
                                sumx += obj.x
                                sumz += obj.z

                            x = sumx/float(wpcount)
                            z = sumz/float(wpcount)

                            self.move_points.emit(movetox-x, -movetoz-z)

                elif self.mousemode == MOUSE_MODE_ADDWP:
                    mouse_x, mouse_z = (event.x(), event.y())
                    destx, destz = self.mouse_coord_to_world_coord(mouse_x, mouse_z)

                    self.create_waypoint.emit(destx, -destz)
        else:
            if event.buttons() & Qt.RightButton and not (event.buttons() & Qt.LeftButton & self.mousemode == MOUSE_MODE_NONE):
                self.last_move = (event.x(), event.y())
                self.right_button_down = True

            if (event.buttons() & Qt.LeftButton and not self.left_button_down):
                self.left_button_down = True

                # Do selection
                if self.mousemode == MOUSE_MODE_NONE and not self.right_button_down:
                    self.selection_queue.append((event.x(), event.y(), 1, 1,
                                                 self.shift_is_pressed))
                    self.do_redraw()

                    self.camera_direction.normalize()
                    self.selectionbox_projected_2d = (event.x(), event.y())
                    view = self.camera_direction.copy()

                    h = view.cross(Vector3(0, 0, 1))
                    v = h.cross(view)

                    h.normalize()
                    v.normalize()

                    rad = 75 * pi / 180.0
                    vLength = tan(rad / 2) * 1.0
                    hLength = vLength * (self.canvas_width / self.canvas_height)

                    v *= vLength
                    h *= hLength

                    mirror_y = self.canvas_height - event.y()

                    x = event.x() - self.canvas_width / 2
                    y = mirror_y - self.canvas_height / 2

                    x /= (self.canvas_width / 2)
                    y /= (self.canvas_height / 2)
                    camerapos = Vector3(self.offset_x, self.offset_z, self.camera_height)

                    pos = camerapos + view * 1.01 + h * x + v * y

                    self.selectionbox_projected_origin = pos

                elif self.mousemode == MOUSE_MODE_ADDWP:
                    print("shooting rays")
                    ray = self.create_ray_from_mouseclick(event.x(), event.y())
                    place_at = None

                    if self.collision is not None:
                        print("colliding with collision")
                        verts = self.collision.verts
                        faces = self.collision.faces

                        best_distance = None

                        for tri in self.collision.triangles:
                            collision = ray.collide(tri)

                            if collision is not False:
                                point, distance = collision

                                if best_distance is None or distance < best_distance:
                                    place_at = point
                                    best_distance = distance

                    if place_at is None:
                        print("colliding with plane")
                        front = Vector3(1.0, 0.0, 0.0)
                        left = Vector3(0.0, 1.0, 0.0)
                        plane = Plane(Vector3(0.0, 0.0, 0.0), front, left)

                        collision = ray.collide_plane(plane)
                        if collision is not False:
                            place_at, _ = collision

                    if place_at is not None:
                        print("collided")
                        self.create_waypoint_3d.emit(place_at.x, place_at.z, -place_at.y)
                    else:
                        print("nothing collided, aw")

                elif self.mousemode == MOUSE_MODE_MOVEWP and not self.change_height_is_pressed:
                    mouse_x, mouse_z = (event.x(), event.y())
                    ray = self.create_ray_from_mouseclick(event.x(), event.y())

                    if len(self.selected) > 0:
                        average_height = 0
                        for pikminobj in self.selected:
                            average_height += pikminobj.y+pikminobj.offset_y
                        average_height = average_height / len(self.selected)

                        self.move_collision_plane.origin.z = average_height
                        collision = ray.collide_plane(self.move_collision_plane)
                        if collision is not False:
                            point, d = collision
                            movetox, movetoz = point.x, point.y

                            if self.rotation_is_pressed and len(self.selected) == 1:
                                obj = self.selected[0]
                                relx = obj.x - movetox
                                relz = -obj.z - movetoz

                                self.rotate_current.emit(obj, degrees(atan2(-relx, relz)))

                            elif not self.rotation_is_pressed:
                                if len(self.selected) > 0:
                                    sumx, sumz = 0, 0
                                    wpcount = len(self.selected)
                                    for obj in self.selected:
                                        sumx += obj.x
                                        sumz += obj.z

                                    x = sumx/float(wpcount)
                                    z = sumz/float(wpcount)

                                    self.move_points.emit(movetox-x, -movetoz-z)
    @catch_exception
    def mouseMoveEvent(self, event):
        if self.mode == MODE_TOPDOWN:
            if self.mid_button_down:
                x, y = event.x(), event.y()
                d_x, d_y  = x - self.drag_last_pos[0], y - self.drag_last_pos[1]

                if self.zoom_factor > 1.0:
                    adjusted_dx = d_x * self.zoom_factor#(1.0 + (self.zoom_factor - 1.0))
                    adjusted_dz = d_y * self.zoom_factor#(1.0 + (self.zoom_factor - 1.0))
                else:
                    adjusted_dx = d_x
                    adjusted_dz = d_y

                self.offset_x += adjusted_dx
                self.offset_z += adjusted_dz
                self.do_redraw()
                self.drag_last_pos = (event.x(), event.y())

            if self.left_button_down:
                mouse_x, mouse_z = event.x(), event.y()
                selectendx, selectendz = self.mouse_coord_to_world_coord(mouse_x, mouse_z)

                selectstartx, selectstartz = self.selectionbox_start
                self.selectionbox_end = (selectendx, selectendz)
                #self.selectionbox_end = (selectendx, selectendz)

                if selectendx <= selectstartx:
                    tmp = selectendx
                    selectendx = selectstartx
                    selectstartx = tmp
                if selectendz <= selectstartz:
                    tmp = selectendz
                    selectendz = selectstartz
                    selectstartz = tmp

                selected = []
                #centerx, centerz = 0, 0
                if self.pikmin_generators is not None:
                    for pikminobject in self.pikmin_generators.objects:
                        #objx, objz = (pikminobject.x - midx)*scalex, (pikminobject.z - midz)*scalez
                        way_x = pikminobject.x
                        way_z = -pikminobject.z

                        if (
                                    (selectstartx <= way_x <= selectendx and selectstartz <= way_z <= selectendz)
                        ):

                            #centerx += way_x
                            #centerz += way_z
                            selected.append(pikminobject)

                """if len(selected) == 0:
                    self.move_startpos = []
                else:
                    count = float(len(selected))
                    self.move_startpos = selected"""

                if not self.shift_is_pressed:
                    if len(self.selected) != len(selected):
                        self.selected = selected
                        self.select_update.emit()
                    elif any(x not in selected for x in self.selected) or any(x not in self.selected for x in selected):
                        self.selected = selected
                        self.select_update.emit()

                else:
                    changed = False
                    for val in selected:
                        if val not in self.selected:
                            changed = True
                            self.selected.append(val)

                    if changed:
                        self.select_update.emit()

                self.do_redraw()

            if self.right_button_down:
                if self.mousemode == MOUSE_MODE_MOVEWP:
                    mouse_x, mouse_z = (event.x(), event.y())
                    movetox, movetoz = self.mouse_coord_to_world_coord(mouse_x, mouse_z)

                    if self.rotation_is_pressed and len(self.selected) == 1:
                        obj = self.selected[0]
                        relx = obj.x - movetox
                        relz = -obj.z - movetoz

                        self.rotate_current.emit(obj, degrees(atan2(-relx, relz)))

                    elif not self.rotation_is_pressed:
                        if len(self.selected) > 0:
                            sumx, sumz = 0, 0
                            objcount = len(self.selected)
                            objects = self.pikmin_generators.objects
                            for object in self.selected:
                                sumx += object.x
                                sumz += object.z

                            x = sumx/float(objcount)
                            z = sumz/float(objcount)

                            self.move_points.emit(movetox-x, (-movetoz-z))


            if default_timer() - self.last_position_update > 0.1: #True:  # self.highlighttriangle is not None:
                mouse_x, mouse_z = (event.x(), event.y())
                mapx, mapz = self.mouse_coord_to_world_coord(mouse_x, mouse_z)
                self.last_position_update = default_timer()
                if self.collision is not None:
                    height = self.collision.collide_ray_downwards(mapx, -mapz)

                    if height is not None:
                        # self.highlighttriangle = res[1:]
                        # self.update()
                        self.position_update.emit(event, (round(mapx, 2), round(height, 2), round(mapz, 2)))
                    else:
                        self.position_update.emit(event, (round(mapx, 2), None, round(mapz,2)))
                else:
                    self.position_update.emit(event, (round(mapx, 2), None, round(mapz, 2)))
        else:
            if self.right_button_down and self.last_move is not None:
                curr_x, curr_y = event.x(), event.y()
                last_x, last_y = self.last_move

                diff_x = curr_x - last_x
                diff_y = curr_y - last_y

                self.last_move = (curr_x, curr_y)

                self.camera_horiz = (self.camera_horiz - diff_x * (pi / 500)) % (2 * pi)
                self.camera_vertical = (self.camera_vertical - diff_y * (pi / 600))
                if self.camera_vertical > pi / 2.0:
                    self.camera_vertical = pi / 2.0
                elif self.camera_vertical < -pi / 2.0:
                    self.camera_vertical = -pi / 2.0

                # print(self.camera_vertical, "hello")
                self.do_redraw()

            if self.left_button_down:
                if self.mousemode == MOUSE_MODE_NONE and self.selectionbox_projected_2d is not None:
                    self.camera_direction.normalize()

                    view = self.camera_direction.copy()

                    h = view.cross(Vector3(0, 0, 1))
                    v = h.cross(view)

                    h.normalize()
                    v.normalize()

                    rad = 75 * pi / 180.0
                    vLength = tan(rad / 2) * 1.0
                    hLength = vLength * (self.canvas_width/self.canvas_height)

                    v *= vLength
                    h *= hLength

                    mirror_y = self.canvas_height - event.y()
                    halfwidth = self.canvas_width/2
                    halfheight = self.canvas_height / 2

                    x = event.x() - halfwidth
                    y = (self.canvas_height - event.y()) - halfheight
                    startx = (self.selectionbox_projected_2d[0] - halfwidth) / halfwidth
                    starty = (self.canvas_height - self.selectionbox_projected_2d[1] - halfheight)/halfheight

                    x /= halfwidth
                    y /= halfheight
                    camerapos = Vector3(self.offset_x, self.offset_z, self.camera_height)


                    self.selectionbox_projected_coords = (
                        camerapos + view * 1.01 + h * startx + v * y,
                        camerapos + view * 1.01 + h * x + v * y,
                        camerapos + view * 1.01 + h * x + v * starty
                    )

                    #print("ok", self.selectionbox_projected_right)
                    self.do_redraw()
                if self.mousemode == MOUSE_MODE_MOVEWP:
                    ray = self.create_ray_from_mouseclick(event.x(), event.y())

                    if len(self.selected) > 0:
                        average_origin = Vector3(0.0, 0.0, 0.0)

                        for pikminobj in self.selected:
                            average_origin += Vector3(pikminobj.x+pikminobj.offset_x,
                                                      pikminobj.y+pikminobj.offset_y,
                                                      pikminobj.z+pikminobj.offset_z)

                        average_origin = average_origin / len(self.selected)

                        if not self.change_height_is_pressed:
                            self.move_collision_plane.origin.z = average_origin.y
                            collision = ray.collide_plane(self.move_collision_plane)
                            if collision is not False:
                                point, d = collision
                                movetox, movetoz = point.x, point.y

                                if self.rotation_is_pressed and len(self.selected) == 1:
                                    obj = self.selected[0]
                                    relx = obj.x - movetox
                                    relz = -obj.z - movetoz

                                    self.rotate_current.emit(obj, degrees(atan2(-relx, relz)))

                                elif not self.rotation_is_pressed:
                                    if len(self.selected) > 0:
                                        sumx, sumz = 0, 0
                                        wpcount = len(self.selected)
                                        for obj in self.selected:
                                            sumx += obj.x
                                            sumz += obj.z

                                        x = sumx / float(wpcount)
                                        z = sumz / float(wpcount)

                                        self.move_points.emit(movetox - x, -movetoz - z)
                        else:
                            """
                            # Method of raising/lowering height:
                            # objects are moved to where the mouse goes
                            normal = self.camera_direction.copy()
                            normal.z = 0.0
                            normal.normalize()
                            tempz = average_origin.z
                            average_origin.z = average_origin.y
                            average_origin.y = -tempz

                            collision_plane = Plane.from_implicit(average_origin, normal)
                            collision = ray.collide_plane(collision_plane)
                            if collision is not False:

                                point, d = collision

                                delta_y = point.z - average_origin.z
                                print("hit", point, average_origin)
                                print(delta_y, normal)
                                if len(self.selected) > 0:
                                    self.height_update.emit(delta_y)"""

                            tempz = average_origin.z
                            average_origin.z = average_origin.y
                            average_origin.y = -tempz
                            campos = Vector3(self.offset_x, self.offset_z, self.camera_height)
                            dist = (campos - average_origin).norm()
                            fac = min(5.0, max(0.5, dist/200.0))
                            print(dist, fac)
                            delta_height = -1*(event.y() - self.last_mouse_move[1])
                            if len(self.selected) > 0:
                                self.height_update.emit(delta_height*fac)

        self.last_mouse_move = (event.x(), event.y()
                                )
    @catch_exception
    def mouseReleaseEvent(self, event):
        if self.mode == MODE_TOPDOWN:
            #print("hm")
            if not event.buttons() & Qt.MiddleButton and self.mid_button_down:
                #print("releasing")
                self.mid_button_down = False
                self.drag_last_pos = None
            if not event.buttons() & Qt.LeftButton and self.left_button_down:
                #print("releasing left")
                self.left_button_down = False
                self.selectionbox_start = self.selectionbox_end = None
                # self.update()
                self.do_redraw()
            if not event.buttons() & Qt.RightButton and self.right_button_down:
                #print("releasing right")
                self.right_button_down = False
                # self.update()
                self.do_redraw()
            #self.mouse_released.emit(event)
        else:
            if not event.buttons() & Qt.RightButton:
                self.last_move = None
                self.right_button_down = False
            if not event.buttons() & Qt.LeftButton and self.left_button_down:
                self.left_button_down = False
                if self.mousemode == MOUSE_MODE_NONE:
                    startx, starty = self.selectionbox_projected_2d

                    if startx > event.x():
                        minx = event.x()
                        maxx = startx
                    else:
                        minx = startx
                        maxx = event.x()

                    if starty > event.y():
                        miny = event.y()
                        maxy = starty
                    else:
                        miny = starty
                        maxy = event.y()
                    width = maxx - minx
                    height = maxy - miny

                    self.selection_queue.append((minx, maxy, width+1, height+1,
                                                 self.shift_is_pressed))

                    self.selectionbox_projected_2d = None
                    self.selectionbox_projected_origin = None
                    self.selectionbox_projected_right = None
                    self.selectionbox_projected_coords = None
                    self.do_redraw()

    def wheelEvent(self, event):
        wheel_delta = event.angleDelta().y()

        if self.editorconfig is not None:
            invert = self.editorconfig.getboolean("invertzoom")
            if invert:
                wheel_delta = -1*wheel_delta

        if wheel_delta < 0:
            self.zoom_out()

        elif wheel_delta > 0:
            self.zoom_in()

    def zoom_in(self):
        current = self.zoom_factor

        fac = calc_zoom_out_factor(current)

        self.zoom(fac)

    def zoom_out(self):
        current = self.zoom_factor
        fac = calc_zoom_in_factor(current)

        self.zoom(fac)

    def create_ray_from_mouseclick(self, mousex, mousey):
        self.camera_direction.normalize()
        height = self.canvas_height
        width = self.canvas_width

        view = self.camera_direction.copy()

        h = view.cross(Vector3(0, 0, 1))
        v = h.cross(view)

        h.normalize()
        v.normalize()

        rad = 75 * pi / 180.0
        vLength = tan(rad / 2) * 1.0
        hLength = vLength * (width / height)

        v *= vLength
        h *= hLength

        x = mousex - width / 2
        y = height - mousey- height / 2

        x /= (width / 2)
        y /= (height / 2)
        camerapos = Vector3(self.offset_x, self.offset_z, self.camera_height)

        pos = camerapos + view * 1.0 + h * x + v * y
        dir = pos - camerapos

        return Line(pos, dir)


class PikminSideWidget(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        parent = args[0]

        self.parent = parent
        self.setMaximumSize(QSize(250, 1500))
        self.verticalLayout = QVBoxLayout(self)
        self.verticalLayout.setAlignment(Qt.AlignBottom)

        font = QFont()
        font.setFamily("Consolas")
        font.setStyleHint(QFont.Monospace)
        font.setFixedPitch(True)
        font.setPointSize(9)

        self.verticalLayout.setObjectName("verticalLayout")

        self.button_add_object = QPushButton(parent)
        self.button_remove_object = QPushButton(parent)
        self.button_ground_object = QPushButton(parent)
        self.button_move_object = QPushButton(parent)
        self.button_edit_object = QPushButton(parent)

        self.button_add_object.setText("Add Object")
        self.button_remove_object.setText("Remove Object(s)")
        self.button_ground_object.setText("Ground Object(s)")
        self.button_move_object.setText("Move Object(s)")
        self.button_edit_object.setText("Edit Object")

        self.button_add_object.setToolTip("Hotkey: Ctrl+A")
        self.button_remove_object.setToolTip("Hotkey: Delete")
        self.button_ground_object.setToolTip("Hotkey: G")
        self.button_move_object.setToolTip("Hotkey: M\nWhen enabled, hold R to rotate when one object is selected.")
        self.button_edit_object.setToolTip("Hotkey: Ctrl+E")


        self.button_add_object.setCheckable(True)
        self.button_move_object.setCheckable(True)

        self.lineedit_coordinatex = QLineEdit(parent)
        self.lineedit_coordinatey = QLineEdit(parent)
        self.lineedit_coordinatez = QLineEdit(parent)
        self.verticalLayout.addStretch(10)
        self.lineedit_rotationx = QLineEdit(parent)
        self.lineedit_rotationy = QLineEdit(parent)
        self.lineedit_rotationz = QLineEdit(parent)
        self.verticalLayout.addWidget(self.button_add_object)
        self.verticalLayout.addWidget(self.button_remove_object)
        self.verticalLayout.addWidget(self.button_ground_object)
        self.verticalLayout.addWidget(self.button_move_object)
        self.verticalLayout.addWidget(self.button_edit_object)
        self.verticalLayout.addStretch(20)

        self.name_label = QLabel(parent)
        self.name_label.setFont(font)
        self.name_label.setWordWrap(True)
        self.name_label.setMinimumSize(self.name_label.width(), 30)
        #self.identifier_label = QLabel(parent)
        #self.identifier_label.setFont(font)
        #self.identifier_label.setMinimumSize(self.name_label.width(), 50)
        #self.identifier_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.verticalLayout.addWidget(self.name_label)
        #self.verticalLayout.addWidget(self.identifier_label)

        self.verticalLayout.addWidget(self.lineedit_coordinatex)
        self.verticalLayout.addWidget(self.lineedit_coordinatey)
        self.verticalLayout.addWidget(self.lineedit_coordinatez)

        self.verticalLayout.addLayout(self._make_labeled_lineedit(self.lineedit_coordinatex, "X:   "))
        self.verticalLayout.addLayout(self._make_labeled_lineedit(self.lineedit_coordinatey, "Y:   "))
        self.verticalLayout.addLayout(self._make_labeled_lineedit(self.lineedit_coordinatez, "Z:   "))
        self.verticalLayout.addStretch(10)
        self.verticalLayout.addLayout(self._make_labeled_lineedit(self.lineedit_rotationx, "RotX:"))
        self.verticalLayout.addLayout(self._make_labeled_lineedit(self.lineedit_rotationy, "RotY:"))
        self.verticalLayout.addLayout(self._make_labeled_lineedit(self.lineedit_rotationz, "RotZ:"))
        self.verticalLayout.addStretch(10)
        self.comment_label = QLabel(parent)
        self.comment_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.comment_label.setWordWrap(True)
        self.comment_label.setFont(font)
        self.verticalLayout.addWidget(self.comment_label)
        self.verticalLayout.addStretch(500)

        self.objectlist = []

        self.reset_info()

    def _make_labeled_lineedit(self, lineedit, label):
        font = QFont()
        font.setFamily("Consolas")
        font.setStyleHint(QFont.Monospace)
        font.setFixedPitch(True)
        font.setPointSize(10)

        layout = QHBoxLayout()
        label = QLabel(label, self)
        label.setFont(font)
        layout.addWidget(label)
        layout.addWidget(lineedit)
        return layout

    def reset_info(self, info="None selected"):
        self.name_label.setText(info)
        #self.identifier_label.setText("")
        self.comment_label.setText("")

        self.lineedit_coordinatex.setText("")
        self.lineedit_coordinatey.setText("")
        self.lineedit_coordinatez.setText("")

        self.lineedit_coordinatex.setDisabled(True)
        self.lineedit_coordinatey.setDisabled(True)
        self.lineedit_coordinatez.setDisabled(True)

        self.lineedit_rotationx.setText("")
        self.lineedit_rotationy.setText("")
        self.lineedit_rotationz.setText("")

        self.lineedit_rotationx.setDisabled(True)
        self.lineedit_rotationy.setDisabled(True)
        self.lineedit_rotationz.setDisabled(True)

        self.objectlist = []

    def set_info(self, obj, position, rotation=None):
        self.name_label.setText("Selected: {}".format(obj.get_useful_object_name()))
        #self.identifier_label.setText(obj.get_identifier())

        comment = "Object notes:\n"
        for part in obj.preceeding_comment:
            comment += part.strip() + "\n"
        self.comment_label.setText(comment)

        self.lineedit_coordinatex.setDisabled(False)
        self.lineedit_coordinatey.setDisabled(False)
        self.lineedit_coordinatez.setDisabled(False)
        self.lineedit_coordinatex.setText(str(position[0]))
        self.lineedit_coordinatey.setText(str(position[1]))
        self.lineedit_coordinatez.setText(str(position[2]))

        if rotation is None:
            self.lineedit_rotationx.setText("")
            self.lineedit_rotationy.setText("")
            self.lineedit_rotationz.setText("")
            self.lineedit_rotationx.setDisabled(True)
            self.lineedit_rotationy.setDisabled(True)
            self.lineedit_rotationz.setDisabled(True)
        else:
            self.lineedit_rotationx.setDisabled(False)
            self.lineedit_rotationy.setDisabled(False)
            self.lineedit_rotationz.setDisabled(False)
            self.lineedit_rotationx.setText(str(rotation[0]))
            self.lineedit_rotationy.setText(str(rotation[1]))
            self.lineedit_rotationz.setText(str(rotation[2]))

        self.objectlist = []

    def set_objectlist(self, objs):
        self.objectlist = []
        objectnames = []

        for obj in objs:
            if len(objectnames) < 25:
                objectnames.append(obj.get_useful_object_name())
            self.objectlist.append(obj)


        objectnames.sort()
        text = "Selected objects:\n" + (", ".join(objectnames))
        diff = len(objs) - len(objectnames)
        if diff == 1:
            text += "\nAnd {0} more object".format(diff)
        elif diff > 1:
            text += "\nAnd {0} more objects".format(diff)
        self.comment_label.setText(text)


class PikObjectEditor(QMdiSubWindow):
    triggered = pyqtSignal(object)
    closing = pyqtSignal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.window_name = "Edit Pikmin Object"
        self.resize(900, 500)
        self.setMinimumSize(QSize(300, 300))

        self.centralwidget = QWidget(self)
        self.setWidget(self.centralwidget)
        self.entity = None

        font = QFont()
        font.setFamily("Consolas")
        font.setStyleHint(QFont.Monospace)
        font.setFixedPitch(True)
        font.setPointSize(10)

        self.dummywidget = QWidget(self)
        self.dummywidget.setMaximumSize(0,0)

        self.verticalLayout = QVBoxLayout(self.centralwidget)
        self.verticalLayout.addWidget(self.dummywidget)


        # self.goto_id_action = ActionWithOwner("Go To ID", self, action_owner=self)

        #self.addAction(self.goto_id_action)

        #self.goto_shortcut = QKeySequence(Qt.CTRL+Qt.Key_G)


        #self.goto_id_action.setShortcut(self.goto_shortcut)
        #self.goto_id_action.setShortcutContext(Qt.WidgetShortcut)
        #self.goto_id_action.setAutoRepeat(False)

        #self.goto_id_action.triggered_owner.connect(self.open_new_window)

        self.textbox_xml = QTextEdit(self.centralwidget)
        self.button_savetext = QPushButton(self.centralwidget)
        self.button_savetext.setText("Save Object Data")
        self.button_savetext.setMaximumWidth(400)
        self.textbox_xml.setLineWrapMode(QTextEdit.NoWrap)
        self.textbox_xml.setContextMenuPolicy(Qt.CustomContextMenu)
        #self.textbox_xml.customContextMenuRequested.connect(self.my_context_menu)

        metrics = QFontMetrics(font)
        self.textbox_xml.setTabStopWidth(4 * metrics.width(' '))
        self.textbox_xml.setFont(font)

        self.verticalLayout.addWidget(self.textbox_xml)
        self.verticalLayout.addWidget(self.button_savetext)
        self.setWindowTitle(self.window_name)

        QtWidgets.QShortcut(Qt.CTRL + Qt.Key_S, self).activated.connect(self.emit_save_object)
        self.button_savetext.setToolTip("Hotkey: Ctrl+S")

    def keyPressEvent(self, event: QtGui.QKeyEvent):
        if event.key() == Qt.CTRL + Qt.Key_W:
            self.shortcut_closewindow()
        else:
            super().keyPressEvent(event)

    def emit_save_object(self):
        self.button_savetext.pressed.emit()

    @catch_exception
    def shortcut_closewindow(self):
        self.close()

    def closeEvent(self, event):
        self.closing.emit()

    def set_content(self, pikminobject):
        try:
            text = StringIO()
            for comment in pikminobject.preceeding_comment:
                assert comment.startswith("#")
                text.write(comment.strip())
                text.write("\n")
            node = pikminobject.to_textnode()
            piktxt = PikminTxt()
            piktxt.write(text, node=[node])
            self.textbox_xml.setText(text.getvalue())
            self.entity = pikminobject
            self.set_title(pikminobject.get_useful_object_name())
        except:
            traceback.print_exc()

    def open_new_window(self, owner):
        #print("It was pressed!", owner)
        #print("selected:", owner.textbox_xml.textCursor().selectedText())

        self.triggered.emit(self)

    def get_content(self):
        try:
            content = self.textbox_xml.toPlainText()
            obj = PikminObject()
            obj.from_text(content)
            obj.get_rotation()
            self.set_title(obj.get_useful_object_name())
            return obj
        except Exception as e:
            traceback.print_exc()
            open_error_dialog(str(e), self)
            return None

    def set_title(self, objectname):
        self.setWindowTitle("{0} - {1}".format(self.window_name, objectname))

    def reset(self):
        pass


class AddPikObjectWindow(PikObjectEditor):
    @catch_exception
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "windowtype" in kwargs:
            self.window_name = kwargs["windowtype"]
            del kwargs["windowtype"]
        else:
            self.window_name = "Add Pikmin Object"

        self.resize(900, 500)
        self.setMinimumSize(QSize(300, 300))

        self.centralwidget = QWidget(self)
        self.setWidget(self.centralwidget)
        self.entity = None

        font = QFont()
        font.setFamily("Consolas")
        font.setStyleHint(QFont.Monospace)
        font.setFixedPitch(True)
        font.setPointSize(10)

        self.dummywidget = QWidget(self)
        self.dummywidget.setMaximumSize(0,0)


        self.verticalLayout = QVBoxLayout(self.centralwidget)
        self.verticalLayout.addWidget(self.dummywidget)

        self.setup_dropdown_menu()
        self.verticalLayout.addWidget(self.template_menu)

        self.textbox_xml = QTextEdit(self.centralwidget)
        self.button_savetext = QPushButton(self.centralwidget)
        self.button_savetext.setText("Add Object")
        self.button_savetext.setToolTip("Hotkey: Ctrl+S")
        self.button_savetext.setMaximumWidth(400)
        self.textbox_xml.setLineWrapMode(QTextEdit.NoWrap)
        self.textbox_xml.setContextMenuPolicy(Qt.CustomContextMenu)
        #self.textbox_xml.customContextMenuRequested.connect(self.my_context_menu)

        metrics = QFontMetrics(font)
        self.textbox_xml.setTabStopWidth(4 * metrics.width(' '))
        self.textbox_xml.setFont(font)

        self.verticalLayout.addWidget(self.textbox_xml)
        self.verticalLayout.addWidget(self.button_savetext)
        self.setWindowTitle(self.window_name)

        #QtWidgets.QShortcut(Qt.CTRL + Qt.Key_S, self).activated.connect(self.emit_add_object)

    def keyPressEvent(self, event: QtGui.QKeyEvent):
        if event.key() == Qt.CTRL + Qt.Key_S:
            self.emit_add_object()
        else:
            super().keyPressEvent(event)

    def emit_add_object(self):
        self.button_savetext.pressed.emit()

    def get_content(self):
        try:
            content = self.textbox_xml.toPlainText()
            obj = PikminObject()
            obj.from_text(content)
            obj.get_rotation()
            return obj
        except Exception as e:
            traceback.print_exc()
            open_error_dialog(str(e), self)
            return None

    def setup_dropdown_menu(self):
        self.template_menu = QtWidgets.QComboBox(self)
        self.template_menu.addItem("-- select object template --")
        self.template_menu.addItem("[None]")

        for filename in os.listdir("./object_templates"):
            if filename.endswith(".txt"):
                self.template_menu.addItem(filename)

        self.template_menu.currentIndexChanged.connect(self.read_template_file_into_window)

    @catch_exception_with_dialog
    def read_template_file_into_window(self, index):
        if index == 1:
            self.textbox_xml.setText("")
        elif index > 1:
            filename = self.template_menu.currentText()

            with open(os.path.join("./object_templates", filename), "r", encoding="utf-8") as f:
                self.textbox_xml.setText(f.read())


class SpawnpointEditor(QMdiSubWindow):
    triggered = pyqtSignal(object)
    closing = pyqtSignal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.centralwidget = QWidget(self)
        self.setWidget(self.centralwidget)
        self.entity = None
        self.resize(400, 200)

        font = QFont()
        font.setFamily("Consolas")
        font.setStyleHint(QFont.Monospace)
        font.setFixedPitch(True)
        font.setPointSize(10)
        self.verticalLayout = QVBoxLayout(self.centralwidget)

        self.position = QLineEdit(self.centralwidget)
        self.rotation = QLineEdit(self.centralwidget)

        self.button_savetext = QPushButton(self.centralwidget)
        self.button_savetext.setText("Set Data")
        self.button_savetext.setMaximumWidth(400)

        self.verticalLayout.addWidget(QLabel("startPos"))
        self.verticalLayout.addWidget(self.position)
        self.verticalLayout.addWidget(QLabel("startDir"))
        self.verticalLayout.addWidget(self.rotation)
        self.verticalLayout.addWidget(self.button_savetext)
        self.setWindowTitle("Edit startPos/Dir")

    def closeEvent(self, event):
        self.closing.emit()

    def get_pos_dir(self):
        pos = self.position.text().strip()
        direction = float(self.rotation.text().strip())

        if "," in pos:
            pos = [float(x.strip()) for x in pos.split(",")]
        else:
            pos = [float(x.strip()) for x in pos.split(" ")]

        assert len(pos) == 3

        return pos, direction


def open_error_dialog(errormsg, self):
    errorbox = QtWidgets.QMessageBox()
    errorbox.critical(self, "Error", errormsg)
    errorbox.setFixedSize(500, 200)
