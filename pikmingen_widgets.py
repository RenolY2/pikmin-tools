import traceback
import os
from time import sleep
from timeit import default_timer
from io import StringIO
from math import sin, cos, atan2, radians, degrees

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
import pikmingen

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
            return func(*args, **kwargs)
        except Exception as e:
            traceback.print_exc()
            open_error_dialog(str(e), None)
    return handle


class GenMapViewer(QWidget):
    mouse_clicked = pyqtSignal(QMouseEvent)
    entity_clicked = pyqtSignal(QMouseEvent, str)
    mouse_dragged = pyqtSignal(QMouseEvent)
    mouse_released = pyqtSignal(QMouseEvent)
    mouse_wheel = pyqtSignal(QWheelEvent)
    position_update = pyqtSignal(QMouseEvent, tuple)
    select_update = pyqtSignal(QMouseEvent)
    move_points = pyqtSignal(float, float)
    connect_update = pyqtSignal(int, int)
    create_waypoint = pyqtSignal(float, float)
    ENTITY_SIZE = ENTITY_SIZE

    rotate_current = pyqtSignal(pikmingen.PikminObject, float)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._zoom_factor = 10

        self.SIZEX = 1024#768#1024
        self.SIZEY = 1024#768#1024

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

        self.mousemode = MOUSE_MODE_NONE

        self.overlapping_wp_index = 0
        self.editorconfig = None

        self.setContextMenuPolicy(Qt.CustomContextMenu)

        self.spawnpoint = None

        self.shift_is_pressed = False
        self.rotation_is_pressed = False
        self.last_drag_update = 0

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
        self.SPEEDUP = 0

        self._wasdscrolling_speed = 1
        self._wasdscrolling_speedupfactor = 3

    @catch_exception
    def set_editorconfig(self, config):
        self.editorconfig = config
        self._wasdscrolling_speed = config.getfloat("wasdscrolling_speed")
        self._wasdscrolling_speedupfactor = config.getfloat("wasdscrolling_speedupfactor")

    @catch_exception
    def render_loop(self):
        now = default_timer()

        diff = now-self._lastrendertime
        timedelta = now-self._lasttime
        self.handle_arrowkey_scroll(timedelta)
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

        if self.MOVE_UP == 1 and self.MOVE_DOWN == 1:
            diff_y = 0
        elif self.MOVE_UP == 1:
            diff_y = 1*speedup*self._wasdscrolling_speed*timedelta
        elif self.MOVE_DOWN == 1:
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

    def set_collision(self, verts, faces):
        self.collision = Collision(verts, faces)

    def set_mouse_mode(self, mode):
        assert mode in (MOUSE_MODE_NONE, MOUSE_MODE_ADDWP, MOUSE_MODE_CONNECTWP, MOUSE_MODE_MOVEWP)

        self.mousemode = mode

        if self.mousemode == MOUSE_MODE_NONE:
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

    #@catch_exception_with_dialog
    def paintEvent(self, event):
        #start = default_timer()

        p = self.p
        p.begin(self)
        h = self.height()
        w = self.width()
        drawLine = p.drawLine
        setBrush = p.setBrush
        setPen = p.setPen
        p_pen = p.pen
        save, translate, restore, rotate = p.save, p.translate, p.restore, p.rotate
        drawImage = p.drawImage
        drawRect = p.drawRect
        drawEllipse = p.drawEllipse

        zf = self.zoom_factor
        last_color = None
        draw_bound = event.rect().adjusted(-ENTITY_SIZE//2, -ENTITY_SIZE//2, ENTITY_SIZE//2, ENTITY_SIZE//2)


        startx, starty = draw_bound.topLeft().x(), draw_bound.topLeft().y()
        endx, endy = startx+draw_bound.width(), starty+draw_bound.height()
        setBrush(QColor("white"))
        drawRect(0, 0, w-1, h-1)

        pen = p_pen()
        defaultwidth = pen.width()
        pen.setWidth(1)
        setPen(pen)
        offsetx, offsetz = (-self.origin_x-self.origin_x-self.offset_x,
                            -self.origin_z-self.origin_z-self.offset_z) # (self.origin_x)+self.offset_x, self.origin_z+self.offset_z
        #print(startx,starty, endx,endy, zf, offsetx, offsetz)

        drawstartx = 0+offsetx - (zf-1.0)*(w//2)
        drawstartz = 0+offsetz - (zf-1.0)*(h//2)

        drawendx = drawstartx + w + (zf-1.0)*(w//2)
        drawendz = drawstartz + h + (zf-1.0)*(h//2)

        drawendxView = drawstartx + w + (zf - 1.0) * (w)
        drawendzView = drawstartz + h + (zf - 1.0) * (h)

        viewportwidth = drawendx-drawstartx
        viewportheight = drawendz-drawstartz

        midx = (drawendx+drawstartx)/2.0
        midz = (drawendz+drawstartz)/2.0

        scalex = (w/viewportwidth)#/2.0
        scalez = (h/viewportheight)#/2.0

        if self.level_image is not None:
            #print("drawing things")
            startx = (-6000 - midx) * scalex
            startz = (-6000 - midz) * scalez
            endx = (6000 - midx) * scalex
            endz = (6000 - midz) * scalez
            drawImage(QRect(startx, startz, endx-startx, endz-startz),
                        self.level_image)

        pen = p_pen()
        prevwidth = pen.width()
        pen.setWidth(5)
        setPen(pen)
        # DRAW COORDINATE FIELD
        x = (0-midx)*scalex
        #p.drawLine(QPoint(x,-5000), QPoint(x,+5000))
        drawLine(x, -5000, x, +5000)
        z = (0-midz)*scalez
        #p.drawLine(QPoint(-5000, z), QPoint(+5000, z))
        drawLine(-5000, z, +5000, z)

        pen.setWidth(prevwidth)
        setPen(pen)

        step = 500

        loop_startx = int(drawstartx-drawstartx%step)
        loop_endx = int((drawendxView+step) - (drawendxView+step) % step)
        for x in range(loop_startx, loop_endx + 4*500, 500):
            x = (x-midx)*scalex
            #p.drawLine(QPoint(x, -5000), QPoint(x, +5000))
            drawLine(x, -5000, x, +5000)

        loop_startz = int(drawstartz - drawstartz % step)
        loop_endz = int((drawendzView + step) - (drawendzView + step) % step)
        for z in range(loop_startz, loop_endz + 2*500, 500):
            z = (z-midz)*scalez
            #p.drawLine(QPoint(-5000, z), QPoint(+5000, z))
            drawLine(-5000, z, +5000, z)

        if self.pikmin_generators is not None:
            if self.editorconfig is not None:
                if self.editorconfig.getboolean("renderStartPos") is True:
                    # Draw startPos
                    x, z, rotation = self.pikmin_generators.startpos_x, self.pikmin_generators.startpos_z, self.pikmin_generators.startdir
                    x, z = (x - midx) * scalex, (z - midz) * scalez

                    pen.setColor(QColor("orange"))
                    pen.setWidth(10)
                    setPen(pen)

                    size = ENTITY_SIZE*scalex + 1
                    drawRect(x - size // 2, z - size // 2, size, size)

                    pen.setColor(QColor("black"))
                    pen.setWidth(prevwidth)
                    setPen(pen)

                    # draw startPos end

            selected = self.selected
            objects = self.pikmin_generators.objects
            #links = self.pikmin_routes.links
            #for waypoint, wp_info in self.waypoints.items():
            for pikminobject in objects:
                x, y, z = pikminobject.x, pikminobject.y, pikminobject.z
                x, z = (x - midx) * scalex, (z - midz) * scalez

                name = pikminobject.get_useful_object_name()

                if pikminobject.object_type == "{item}":
                    if name in BRIDGE_LENGTHS:
                        save()
                        length = BRIDGE_LENGTHS[name]*scalex
                        angle = pikminobject.get_horizontal_rotation()
                        translate(x, z)
                        rotate(-angle)
                        width = 130*scalex
                        #p.drawRect(x-width//2, z, width, length)
                        drawImage(QRect(0 - width // 2, 0 - (42)*scalex, width, 38*scalex + length),
                                    BRIDGE_GRAPHICS[name])
                        #p.drawRect(0 - width // 2, 0, width, length)

                        restore()
                    elif name in GATE_GRAPHICS:
                        save()
                        angle = pikminobject.get_horizontal_rotation()
                        translate(x, z)
                        rotate(-angle)

                        length = 267*scalex

                        if name == pikmingen.GATE_ELECTRIC:
                            width = 35*scalez
                            drawImage(QRect(0 - length // 2, 0 - width//2-10*scalex, length, width),
                                        GATE_GRAPHICS[name])
                        else:
                            width = 70*scalez
                            drawImage(QRect(0 - length // 2, 0 - width // 2, length, width),
                                        GATE_GRAPHICS[name])
                        restore()

                    else:
                        itemdata = pikminobject._object_data[0]
                        if itemdata[0] == "{dwfl}":
                            downfloortype = itemdata[4]
                            image = None
                            save()
                            angle = pikminobject.get_horizontal_rotation()
                            translate(x, z)
                            rotate(-angle)

                            if downfloortype == "0":
                                # draw small block
                                length = 100*scalex
                                width = 100*scalez
                                image = DOWNFLOOR_GRAPHICS[downfloortype]
                            elif downfloortype == "1":
                                # draw normal block
                                length = 150*scalex
                                width = 120*scalez
                                image = DOWNFLOOR_GRAPHICS[downfloortype]
                            elif downfloortype == "2":
                                #draw paperbag
                                length = 256*scalex
                                width = 197*scalez
                                image = DOWNFLOOR_GRAPHICS[downfloortype]

                            if image is not None:
                                drawImage(QRect(0 - length // 2, 0 - width // 2, length, width),
                                          image)
                            restore()

            for pikminobject in objects:
                x,y,z = pikminobject.x, pikminobject.y, pikminobject.z

                color = DEFAULT_ENTITY

                drawcircle = False
                isselected = False
                if pikminobject.object_type == "{item}":

                    name = pikminobject.get_useful_object_name()
                    if name in ONION_COLORTABLE:
                        color = ONION_COLORTABLE[name]
                        drawcircle = True

                    if name in OBJECT_SIZES:
                        size = OBJECT_SIZES[name] * scalex
                    else:
                        size = ENTITY_SIZE * scalex
                else:
                    size = ENTITY_SIZE * scalex

                if pikminobject in selected:
                    # print("vhanged")
                    color = DEFAULT_SELECTED
                    isselected = True

                # x, z = offsetx + x*zf, offsetz + z*zf
                x, z = (x-midx)*scalex, (z-midz)*scalez

                if last_color != color:
                    setBrush(color)
                    setPen(color)
                    #p.setPen(QColor(color))
                    last_color = color

                if drawcircle:
                    if not isselected:
                        setBrush(DEFAULT_ENTITY)
                        setPen(DEFAULT_ENTITY)
                    else:
                        setBrush(color)
                        setPen(color)

                    drawEllipse(x-(size//2)-2, z-(size//2)-2, size+4, size+4)

                    setBrush(color)
                    setPen(color)

                    drawEllipse(x - size // 2, z - size // 2, size, size)
                else:
                    #p.drawRect(x-size//2, z-size//2, size, size)
                    drawEllipse(x - size // 2, z - size // 2, size, size)

                if isselected:
                    setPen(QColor("blue"))
                    angle = pikminobject.get_horizontal_rotation()
                    if angle is not None:
                        pointx = x
                        pointz = z + 25*scalez
                        relx, relz = rotate_rel(pointx, pointz, x, z, angle)
                        drawLine(x, z, x-relx, z+relz)
                    setPen(color)

            arrows = []
            pen = p_pen()
            prevwidth = pen.width()
            pen.setWidth(5)
            pen.setColor(DEFAULT_ENTITY)
            setPen(pen)

        pen.setColor(QColor("red"))
        pen.setWidth(2)
        setPen(pen)

        if self.selectionbox_start is not None and self.selectionbox_end is not None:
            startx, startz = ((self.selectionbox_start[0] - midx)*scalex,
                              (self.selectionbox_start[1] - midz)*scalez)

            endx, endz = (  (self.selectionbox_end[0] - midx)*scalex,
                            (self.selectionbox_end[1] - midz)*scalez)

            startpoint, endpoint = QPoint(startx, startz), QPoint(endx, endz)

            corner_horizontal = QPoint(endx, startz)
            corner_vertical = QPoint(startx, endz)
            selectionbox_polygon = QPolygon([startpoint, corner_horizontal, endpoint, corner_vertical,
                                            startpoint])
            p.drawPolyline(selectionbox_polygon)

        """if self.highlighttriangle is not None:
            p1, p2, p3 = self.highlighttriangle
            p1x = (p1[0] - midx)*scalex
            p2x = (p2[0] - midx)*scalex
            p3x = (p3[0] - midx)*scalex
            p1z = (p1[2] - midz)*scalez
            p2z = (p2[2] - midz)*scalez
            p3z = (p3[2] - midz)*scalez

            selectionbox_polygon = QPolygon([QPoint(p1x, p1z), QPoint(p2x, p2z), QPoint(p3x, p3z),
                                             QPoint(p1x, p1z)])
            p.drawPolyline(selectionbox_polygon)"""

        p.end()
        #end = default_timer()

        #print("time taken:", end-start, "sec")
        """""#self.last_render = end
        frame = 60.0
        if end-start < 1/frame:
            print("sleeping for", 1/frame - (end-start))
            sleep(1/frame - (end-start))"""

    @catch_exception
    def mousePressEvent(self, event):
        # Set up values for checking if the mouse hit a node
        offsetx, offsetz = (-self.origin_x-self.origin_x-self.offset_x,
                            -self.origin_z-self.origin_z-self.offset_z)
        h, w, zf = self.height(), self.width(), self.zoom_factor
        drawstartx = 0+offsetx - (zf-1.0)*(w//2)
        drawstartz = 0+offsetz - (zf-1.0)*(h//2)

        drawendx = drawstartx + w + (zf-1.0)*(w//2)
        drawendz = drawstartz + h + (zf-1.0)*(h//2)

        viewportwidth = drawendx-drawstartx
        viewportheight = drawendz-drawstartz

        midx = (drawendx+drawstartx)/2.0
        midz = (drawendz+drawstartz)/2.0

        scalex = (w/viewportwidth)#/2.0
        scalez = (h/viewportheight)#/2.0
        # Set up end
        # -------------
        if (event.buttons() & Qt.LeftButton and not self.left_button_down):
            mouse_x, mouse_z = (event.x(), event.y())
            selectstartx = mouse_x/scalex + midx
            selectstartz = mouse_z/scalez + midz

            if True: #(self.mousemode == MOUSE_MODE_MOVEWP or self.mousemode == MOUSE_MODE_NONE):
                self.left_button_down = True
                self.selectionbox_start = (selectstartx, selectstartz)

            if self.pikmin_generators is not None:
                hit = False
                all_hit_waypoints = []
                for pikminobject in self.pikmin_generators.objects:
                    objx, objz = (pikminobject.x - midx)*scalex, (pikminobject.z - midz)*scalez
                    x, z = selectstartx, selectstartz
                    #print("checking", abs(x-mouse_x), abs(z-mouse_z), radius)
                    #if abs(x-mouse_x) < radius and abs(z-mouse_z) < radius:
                    #if ((x-way_x)**2 + (z-way_z)**2)**0.5 < radius_actual:
                    #    all_hit_waypoints.append(wp_index)
                    # print(abs(x-objx), abs(z-objz))
                    name = pikminobject.get_useful_object_name()

                    if name in OBJECT_SIZES:
                        size = OBJECT_SIZES[name]
                    else:
                        size = ENTITY_SIZE

                    #if abs(mouse_x-objx) <= size and abs(mouse_z - objz) <= size:
                    if abs(selectstartx-pikminobject.x) <= size//2 and abs(selectstartz-pikminobject.z) <= size//2:
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
                    self.select_update.emit(event)

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
                    self.select_update.emit(event)
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
                movetox = mouse_x/scalex + midx
                movetoz = mouse_z/scalez + midz

                if self.rotation_is_pressed and len(self.selected) == 1:
                    obj = self.selected[0]
                    relx = obj.x - movetox
                    relz = obj.z - movetoz

                    self.rotate_current.emit(obj, degrees(atan2(-relx, -relz)))

                elif not self.rotation_is_pressed:
                    if len(self.selected) > 0:
                        sumx, sumz = 0, 0
                        wpcount = len(self.selected)
                        for obj in self.selected:
                            sumx += obj.x
                            sumz += obj.z

                        x = sumx/float(wpcount)
                        z = sumz/float(wpcount)

                        self.move_points.emit(movetox-x, movetoz-z)

            elif self.mousemode == MOUSE_MODE_ADDWP:
                mouse_x, mouse_z = (event.x(), event.y())
                destx = mouse_x/scalex + midx
                destz = mouse_z/scalez + midz

                self.create_waypoint.emit(destx, destz)

    @catch_exception
    def mouseMoveEvent(self, event):
        offsetx, offsetz = (-self.origin_x-self.origin_x-self.offset_x,
                            -self.origin_z-self.origin_z-self.offset_z)
        h, w, zf = self.height(), self.width(), self.zoom_factor
        drawstartx = 0+offsetx - (zf-1.0)*(w//2)
        drawstartz = 0+offsetz - (zf-1.0)*(h//2)

        drawendx = drawstartx + w + (zf-1.0)*(w//2)
        drawendz = drawstartz + h + (zf-1.0)*(h//2)

        viewportwidth = drawendx-drawstartx
        viewportheight = drawendz-drawstartz

        midx = (drawendx+drawstartx)/2.0
        midz = (drawendz+drawstartz)/2.0

        scalex = (w/viewportwidth)#/2.0
        scalez = (h/viewportheight)#/2.0

        if self.mid_button_down:
            x, y = event.x(), event.y()
            d_x, d_y  = x - self.drag_last_pos[0], y - self.drag_last_pos[1]
            """delta_length = (d_x**2+d_y**2)**0.5
            LEN = 3
            steps = int(delta_length // LEN)
            rest = delta_length % LEN
            print(d_x, d_y, (d_x**2+d_y**2)**0.5)
            d_x = d_x / delta_length
            d_y = d_y / delta_length

            for i in range(steps+1):
                if i == steps:
                    steplen = rest
                else:
                    steplen = LEN

                if self.zoom_factor > 1.0:
                    self.offset_x += d_x*(1.0 + (self.zoom_factor-1.0)/2.0)*steplen
                    self.offset_z += d_y*(1.0 + (self.zoom_factor-1.0)/2.0)*steplen
                else:
                    self.offset_x += d_x*steplen
                    self.offset_z += d_y*steplen

                self.update()"""
            if self.zoom_factor > 1.0:
                self.offset_x += d_x * (1.0 + (self.zoom_factor - 1.0) / 2.0)
                self.offset_z += d_y * (1.0 + (self.zoom_factor - 1.0) / 2.0)
            else:
                self.offset_x += d_x
                self.offset_z += d_y
            self.drag_last_pos = (event.x(), event.y())
            # self.update()
            self.do_redraw()

        if self.left_button_down:
            # -----------------------
            # Set up values for checking if the mouse hit a node
            offsetx, offsetz = (-self.origin_x-self.origin_x-self.offset_x,
                                -self.origin_z-self.origin_z-self.offset_z)
            h, w, zf = self.height(), self.width(), self.zoom_factor
            drawstartx = 0+offsetx - (zf-1.0)*(w//2)
            drawstartz = 0+offsetz - (zf-1.0)*(h//2)

            drawendx = drawstartx + w + (zf-1.0)*(w//2)
            drawendz = drawstartz + h + (zf-1.0)*(h//2)

            viewportwidth = drawendx-drawstartx
            viewportheight = drawendz-drawstartz

            midx = (drawendx+drawstartx)/2.0
            midz = (drawendz+drawstartz)/2.0

            scalex = (w/viewportwidth)#/2.0
            scalez = (h/viewportheight)#/2.0
            # Set up end
            # -------------

            mouse_x, mouse_z = event.x(), event.y()

            selectendx = mouse_x/scalex + midx
            selectendz = mouse_z/scalez + midz

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
                    way_z = pikminobject.z

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
                    self.select_update.emit(event)
                elif any(x not in selected for x in self.selected) or any(x not in self.selected for x in selected):
                    self.selected = selected
                    self.select_update.emit(event)

            else:
                changed = False
                for val in selected:
                    if val not in self.selected:
                        changed = True
                        self.selected.append(val)

                if changed:
                    self.select_update.emit(event)

            self.do_redraw()

        if self.right_button_down:
            if self.mousemode == MOUSE_MODE_MOVEWP:
                mouse_x, mouse_z = (event.x(), event.y())
                movetox = mouse_x/scalex + midx
                movetoz = mouse_z/scalez + midz

                if self.rotation_is_pressed and len(self.selected) == 1:
                    obj = self.selected[0]
                    relx = obj.x - movetox
                    relz = obj.z - movetoz

                    self.rotate_current.emit(obj, degrees(atan2(-relx, -relz)))

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

                        self.move_points.emit(movetox-x, movetoz-z)


        if True:  # self.highlighttriangle is not None:
            mouse_x, mouse_z = (event.x(), event.y())
            mapx = mouse_x/scalex + midx
            mapz = mouse_z/scalez + midz

            if self.collision is not None:
                height = self.collision.collide_ray_downwards(mapx, mapz)

                if height is not None:
                    # self.highlighttriangle = res[1:]
                    # self.update()
                    self.position_update.emit(event, (round(mapx, 2), round(height, 2), round(mapz, 2)))
                else:
                    self.position_update.emit(event, (round(mapx, 2), None, round(mapz,2)))
            else:
                self.position_update.emit(event, (round(mapx, 2), None, round(mapz, 2)))
        # self.mouse_dragged.emit(event)

    @catch_exception
    def mouseReleaseEvent(self, event):
        """if self.left_button_down:
            self.left_button_down = False
            self.last_pos = None
        if self.left_button_down:
            self.left_button_down = False"""
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
