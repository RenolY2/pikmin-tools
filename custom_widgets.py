import traceback
import math
import xml.etree.ElementTree as etree
from time import sleep
from array import array
from timeit import default_timer
from copy import copy
from math import sin, cos, atan2, radians, degrees
from itertools import chain

from PyQt5.QtGui import QMouseEvent, QWheelEvent, QPainter, QColor, QFont, QFontMetrics, QPolygon, QImage, QPixmap, QKeySequence
from PyQt5.QtWidgets import (QWidget, QListWidget, QListWidgetItem, QDialog, QMenu,
                            QMdiSubWindow, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QTextEdit, QAction, QShortcut)
from PyQt5.QtCore import QSize, pyqtSignal, QPoint, QRect
from PyQt5.QtCore import Qt

from helper_functions import calc_zoom_in_factor, calc_zoom_out_factor

ENTITY_SIZE = 10

COLORS = {
    "cAirVehicle": QColor("yellow"),
    "cGroundVehicle": QColor(180, 50, 0),#QColor("brown"),
    "cTroop": QColor("blue"),
    "cMapZone": QColor("grey"),
    "cCamera": QColor("violet"),
    "cWaypoint": QColor("cyan"),
    "cSceneryCluster": QColor(90, 40, 40)
}

MAPZONECOLORS = {
    "ZONETYPE_MISSIONBOUNDARY": QColor("light green")
}
DEFAULT_ENTITY = QColor("black")
DEFAULT_MAPZONE = QColor("grey")
DEFAULT_SELECTED = QColor("red")
DEFAULT_ANGLE_MARKER = QColor("blue")

SHOW_TERRAIN_NO_TERRAIN = 0
SHOW_TERRAIN_REGULAR = 1
SHOW_TERRAIN_LIGHT = 2

#MOSUE_

def catch_exception(func):
    def handle(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except:
            traceback.print_exc()
            #raise
    return handle


def rotate(corner_x, corner_y, center_x, center_y, angle):
    temp_x = corner_x-center_x
    temp_y = corner_y-center_y
    angle = radians(angle)

    rotated_x = temp_x*cos(angle) - temp_y*sin(angle)
    rotated_y = temp_x*sin(angle) + temp_y*cos(angle)
    #print(sin(radians(angle)))

    return QPoint(int(rotated_x+center_x), int(rotated_y+center_y))

#def transform_coords(x,y, offsetx, offsety, scale):
#    pass

def transform_coords(x,z, startx, startz, scalex, scalez):
    relativex = x-startx
    relativez = z-startz

    return relativex*scalex, relativez*scalez

class BWMapViewer(QWidget):
    mouse_clicked = pyqtSignal(QMouseEvent)
    entity_clicked = pyqtSignal(QMouseEvent, str)
    mouse_dragged = pyqtSignal(QMouseEvent)
    mouse_released = pyqtSignal(QMouseEvent)
    mouse_wheel = pyqtSignal(QWheelEvent)
    position_update = pyqtSignal(QMouseEvent, tuple)
    select_update = pyqtSignal(QMouseEvent)
    ENTITY_SIZE = ENTITY_SIZE



    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._zoom_factor = 10

        self.SIZEX = 1024#768#1024
        self.SIZEY = 1366#768#1024


        self.setMinimumSize(QSize(self.SIZEX, self.SIZEY))
        self.setMaximumSize(QSize(self.SIZEX, self.SIZEY))
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

        #self.entities = [(0,0, "abc")]
        self.waypoints = {}#{"abc": (0, 0)}
        self.paths = []

        self.left_button_down = False
        self.mid_button_down = False
        self.right_button_down = False
        self.drag_last_pos = None

        self.current_waypoint = None
        self.selected_waypoints = {}

        self.terrain = None
        self.terrain_scaled = None
        self.terrain_buffer = QImage()

        self.p = QPainter()
        self.p2 = QPainter()
        self.show_terrain_mode = SHOW_TERRAIN_REGULAR

        self.selectionbox_start = None
        self.selectionbox_end = None

        self.visualize_cursor = None

        self.click_mode = 0

        self.level_image = None

        self.collision = None

        self.highlighttriangle = None

        self.setMouseTracking(True)

        self.pikmin_routes = None

    def set_visibility(self, visibility):
        self.visibility_toggle = visibility

    def reset(self):
        del self.waypoints
        del self.paths

        self.waypoints = {}
        self.paths = []

        self.SIZEX = 1024#768#1024
        self.SIZEY = 1366
        self.origin_x = self.SIZEX//2
        self.origin_z = self.SIZEY//2

        self.offset_x = 0
        self.offset_z = 0

        self._zoom_factor = 10

        self.left_button_down = False
        self.mid_button_down = False
        self.right_button_down = False
        self.drag_last_pos = None

        self.selectionbox_start = None
        self.selectionbox_end = None

        self.selected_waypoints = []

        self.setMinimumSize(QSize(self.SIZEX, self.SIZEY))
        self.setMaximumSize(QSize(self.SIZEX, self.SIZEY))

        self.level_image = None
        del self.collision
        self.collision = None

        self.highlighttriangle = None

        self.pikmin_routes = None

    def set_collision(self, verts, faces):
        self.collision = Collision(verts, faces)

    @property
    def zoom_factor(self):
        return self._zoom_factor/10.0

    def zoom(self, fac):
        if (self.zoom_factor + fac) > 0.1 and (self.zoom_factor + fac) <= 25:
            self._zoom_factor += int(fac*10)
            #self.zoom_factor = round(self.zoom_factor, 2)
            zf = self.zoom_factor
            #self.setMinimumSize(QSize(self.SIZEX*zf, self.SIZEY*zf))
            #self.setMaximumSize(QSize(self.SIZEX*zf, self.SIZEY*zf))

            #self.terrain_buffer = QImage()
            self.update()
            """if self.terrain is not None:
                if self.terrain_scaled is None:
                    self.terrain_scaled = self.terrain
                self.terrain_scaled = self.terrain_scaled.scaled(self.height(), self.width())"""

    @catch_exception
    def paintEvent(self, event):
        start = default_timer()
        #print("painting")

        p = self.p
        p.begin(self)
        h = self.height()
        w = self.width()
        p.setBrush(QColor("white"))
        p.drawRect(0, 0, h-1, w-1)

        zf = self.zoom_factor
        current_entity = self.current_waypoint
        last_color = None
        draw_bound = event.rect().adjusted(-ENTITY_SIZE//2, -ENTITY_SIZE//2, ENTITY_SIZE//2, ENTITY_SIZE//2)
        #contains = draw_bound.contains
        selected_entities = self.selected_waypoints

        startx, starty = draw_bound.topLeft().x(), draw_bound.topLeft().y()
        endx, endy = startx+draw_bound.width(), starty+draw_bound.height()


        pen = p.pen()
        defaultwidth = pen.width()
        pen.setWidth(1)
        p.setPen(pen)
        offsetx, offsetz = (-self.origin_x-self.origin_x-self.offset_x,
                            -self.origin_z-self.origin_z-self.offset_z) # (self.origin_x)+self.offset_x, self.origin_z+self.offset_z
        #print(startx,starty, endx,endy, zf, offsetx, offsetz)

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

        if self.level_image is not None:
            print("drawing things")
            startx = (-6000 - midx) * scalex
            startz = (-6000 - midz) * scalez
            endx = (6000 - midx) * scalex
            endz = (6000 - midz) * scalez
            p.drawImage(QRect(startx, startz, endx-startx, endz-startz),
                        self.level_image)

        pen = p.pen()
        prevwidth = pen.width()
        pen.setWidth(5)
        p.setPen(pen)
        # DRAW COORDINATE FIELD
        if True:#drawstartx <= 0 <= drawendx:
            x = (0-midx)*scalex
            #p.drawLine(QPoint(x-2,-5000), QPoint(x-2,+5000))
            #p.drawLine(QPoint(x-1,-5000), QPoint(x-1,+5000))
            p.drawLine(QPoint(x,-5000), QPoint(x,+5000))
            #p.drawLine(QPoint(x+1,-5000), QPoint(x+1,+5000))
            #p.drawLine(QPoint(x+2,-5000), QPoint(x+2,+5000))
        if True:#drawstartz <= 0 <= drawendz:
            z = (0-midz)*scalez
            #p.drawLine(QPoint(-5000, z-2), QPoint(+5000, z-2))
            #p.drawLine(QPoint(-5000, z-1), QPoint(+5000, z-1))
            p.drawLine(QPoint(-5000, z), QPoint(+5000, z))
            #p.drawLine(QPoint(-5000, z+1), QPoint(+5000, z+1))
            #p.drawLine(QPoint(-5000, z+2), QPoint(+5000, z+2))

        pen.setWidth(prevwidth)
        p.setPen(pen)

        for x in range(-6000, 6000+1, 400):
            x = (x-midx)*scalex
            if 0 <= x <= w:
                p.drawLine(QPoint(x,-5000), QPoint(x,+5000))

        for z in range(-6000, 6000+1, 400):

            z = (z-midz)*scalez
            if 0 <= z <= h:
                p.drawLine(QPoint(-5000, z), QPoint(+5000, z))



        if self.pikmin_routes is not None:
            selected = self.selected_waypoints
            waypoints = self.pikmin_routes.waypoints
            links = self.pikmin_routes.links
            #for waypoint, wp_info in self.waypoints.items():
            for wp_index, wp_data in waypoints.items():
                x,y,z,radius = wp_data
                color = DEFAULT_ENTITY
                if wp_index in selected:
                    print("vhanged")
                    color = QColor("red")

                radius = radius*scalex
                #x, z = offsetx + x*zf, offsetz + z*zf
                x, z = (x-midx)*scalex, (z-midz)*scalez


                if last_color != color:

                    p.setBrush(color)
                    p.setPen(color)
                    #p.setPen(QColor(color))
                    last_color = color
                size=8
                p.drawRect(x-size//2, z-size//2, size, size)

                if radius > 0:
                    pen = p.pen()
                    prevwidth = pen.width()
                    pen.setWidth(2)
                    p.setPen(pen)
                    p.drawArc(x-radius//2, z-radius//2, radius, radius, 0, 16*360)
                    pen.setWidth(prevwidth)
                    p.setPen(pen)

            arrows = []
            pen = p.pen()
            prevwidth = pen.width()
            pen.setWidth(5)
            p.setPen(pen)
            #for start_wp, end_wp in self.paths:
            for start_wp, linksto in links.items():
                startx, y, startz, radius = waypoints[start_wp]
                startx = (startx-midx)*scalex
                startz = (startz-midz)*scalez

                startpoint = QPoint(startx, startz)

                for end_wp in linksto:
                    endx, y, endz, radius = waypoints[end_wp]

                    endx = (endx-midx)*scalex
                    endz = (endz-midz)*scalez

                    p.drawLine(startpoint,
                               QPoint(endx, endz))

                    #angle = degrees(atan2(endx-startx, endz-startz))
                    angle = degrees(atan2(endz-startz, endx-startx))

                    centerx, centery = (endx)*0.8 + (startx)*0.2, \
                                       (endz)*0.8 + (startz)*0.2
                    p1 = rotate(centerx-15, centery, centerx, centery, angle+40)
                    p2 = rotate(centerx-15, centery, centerx, centery, angle-40)
                    #p.setPen(QColor("green"))
                    """pen = p.pen()
                    pen.setColor(QColor("blue"))
                    prevwidth = pen.width()
                    pen.setWidth(3)
                    p.setPen(pen)
                    p.drawLine(QPoint(centerx, centery),
                               p1)
                    p.drawLine(QPoint(centerx, centery),
                               p2)
                    pen.setColor(DEFAULT_ENTITY)
                    pen.setWidth(prevwidth)
                    p.setPen(pen)"""
                    arrows.append((QPoint(centerx, centery), p1, p2))
            pen = p.pen()
            pen.setColor(QColor("green"))
            pen.setWidth(4)
            p.setPen(pen)

            for arrow in arrows:
                p.drawLine(arrow[0], arrow[1])
                p.drawLine(arrow[0], arrow[2])

        if self.visualize_cursor is not None:
            a, b = self.visualize_cursor
            size = 5
            p.drawRect(a-size//2, b-size//2, size, size)

        pen.setColor(QColor("red"))
        pen.setWidth(2)
        p.setPen(pen)

        if self.selectionbox_start is not None and self.selectionbox_end is not None:
            print("selectionbox")
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
        if self.highlighttriangle is not None:
            p1, p2, p3 = self.highlighttriangle
            p1x = (p1[0] - midx)*scalex
            p2x = (p2[0] - midx)*scalex
            p3x = (p3[0] - midx)*scalex
            p1z = (p1[2] - midz)*scalez
            p2z = (p2[2] - midz)*scalez
            p3z = (p3[2] - midz)*scalez

            selectionbox_polygon = QPolygon([QPoint(p1x, p1z), QPoint(p2x, p2z), QPoint(p3x, p3z),
                                             QPoint(p1x, p1z)])
            p.drawPolyline(selectionbox_polygon)

        p.end()
        end = default_timer()

        print("time taken:", end-start, "sec")

        if end-start < 1/90.0:
            sleep(1/90.0 - (end-start))

    @catch_exception
    def mousePressEvent(self, event):
        #x,y = event.localPos()
        #if event.x() < self.height() and event.y() < self.width:

        """print(event.x(), event.y())
        event_x, event_y = event.x(), event.y()
        hit = False
        search_start = default_timer()

        if self.zoom_factor > 1:
            ENTITY_SIZE = int(self.ENTITY_SIZE * (1 + self.zoom_factor/10.0))
        else:
            ENTITY_SIZE = self.ENTITY_SIZE

        if event.buttons() == Qt.LeftButton:
            entities_hit = []
            toggle = self.visibility_toggle
            for entity, data in self.entities.items():
                x, y, entitytype, metadata = data
                x *= self.zoom_factor
                y *= self.zoom_factor
                if entitytype in toggle and toggle[entitytype] is False:
                    continue
                if ((x + ENTITY_SIZE//2) > event_x > (x - ENTITY_SIZE//2)
                    and (y + ENTITY_SIZE//2) > event_y > (y - ENTITY_SIZE//2)):
                    #hit = True
                    entities_hit.append(entity)

            print("we got it")
            if len(entities_hit) > 0:
                if self.next_selected_index > (len(entities_hit) - 1):
                    self.next_selected_index = 0
                entity = entities_hit[self.next_selected_index]

                search_end = default_timer()
                print("time for search:", search_end-search_start, "sec")
                self.next_selected_index = (self.next_selected_index+1) % len(entities_hit)
                self.entity_clicked.emit(event, entity)
            else:
                self.mouse_clicked.emit(event)
        else:
            self.mouse_clicked.emit(event)"""


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
        if event.buttons() & Qt.LeftButton and not self.left_button_down:
            self.left_button_down = True
            #self.last_pos = (event.x(), event.y())
            mouse_x, mouse_z = (event.x(), event.y()) #self.drag_last_pos
            #offsetx, offsetz = (self.origin_x)+self.offset_x, self.origin_z+self.offset_z
            zf = self.zoom_factor
            #scale = 4.0/zf


            selectstartx = mouse_x/scalex + midx
            selectstartz = mouse_z/scalez + midz

            self.selectionbox_start = (selectstartx, selectstartz)

            for wp_index, wp_data in self.pikmin_routes.waypoints.items():
                way_x, y, way_z, radius = wp_data
                radius = radius*scalex

                x, z = (way_x - midx)*scalex, (way_z - midz)*scalez
                #print("checking", abs(x-mouse_x), abs(z-mouse_z), radius)
                if abs(x-mouse_x) < radius/2.0 and abs(z-mouse_z) < radius/2.0:
                    self.selected_waypoints = [wp_index]
                    print("hit")
                    self.select_update.emit(event)
                    self.update()

        if event.buttons() & Qt.MiddleButton and not self.mid_button_down:
            self.mid_button_down = True
            self.drag_last_pos = (event.x(), event.y())

        if event.buttons() & Qt.RightButton and self.collision is not None:
            self.right_button_down = True
            mouse_x, mouse_z = (event.x(), event.y())
            mapx = mouse_x/scalex + midx
            mapz = mouse_z/scalez + midz

            res = self.collision.collide_ray_downwards(mapx, mapz)

            if res is not None:
                self.highlighttriangle = res[1:]
                self.update()

        #elif event.buttons() == Qt.LeftButton and self.left_button_down:
        #    # Drag the screen!
        #    """x, y = event.x(), event.y()
        #    d_x, d_y  = x - self.last_pos[0], y - self.last_pos[1]
        #    self.offset_x += d_x
        #    self.offset_z += d_y"""
        #else:
        #    self.left_button_down = False
        #    self.last_pos = None


        #self.mouse_clicked.emit(event)
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


            if self.zoom_factor > 1.0:
                self.offset_x += d_x*(1.0 + (self.zoom_factor-1.0)/2.0)
                self.offset_z += d_y*(1.0 + (self.zoom_factor-1.0)/2.0)
            else:
                self.offset_x += d_x
                self.offset_z += d_y


            self.drag_last_pos = (event.x(), event.y())
            self.update()

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

            for wp_index, wp_data in self.pikmin_routes.waypoints.items():
                way_x, y, way_z, meta = wp_data

                if selectstartx <= way_x <= selectendx and selectstartz <= way_z <= selectendz:
                    selected.append(wp_index)

            self.selected_waypoints = selected
            self.select_update.emit(event)
            self.update()

        if True:#self.highlighttriangle is not None:
            mouse_x, mouse_z = (event.x(), event.y())
            mapx = mouse_x/scalex + midx
            mapz = mouse_z/scalez + midz

            if self.collision is not None:
                res = self.collision.collide_ray_downwards(mapx, mapz)

                if res is not None:
                    #self.highlighttriangle = res[1:]
                    #self.update()
                    self.position_update.emit(event, tuple(round(v, 2) for v in res[0]))
                else:
                    self.position_update.emit(event, (round(mapx, 2), None, round(mapz,2)))
            else:
                self.position_update.emit(event, (round(mapx, 2), None, round(mapz, 2)))
        #self.mouse_dragged.emit(event)
    @catch_exception
    def mouseReleaseEvent(self, event):
        """if self.left_button_down:
            self.left_button_down = False
            self.last_pos = None
        if self.left_button_down:
            self.left_button_down = False"""
        print("hm")
        if not event.buttons() & Qt.MiddleButton and self.mid_button_down:
            print("releasing")
            self.mid_button_down = False
            self.drag_last_pos = None
        if not event.buttons() & Qt.LeftButton and self.left_button_down:
            print("releasing left")
            self.left_button_down = False
            self.selectionbox_start = self.selectionbox_end = None
            self.update()
        if not event.buttons() & Qt.RightButton and self.right_button_down:
            print("releasing right")
            self.right_button_down = False
            self.update()
        #self.mouse_released.emit(event)

    def wheelEvent(self, event):
        wheel_delta = event.angleDelta().y()
        if wheel_delta > 0:
            current = self.zoom_factor
            fac = calc_zoom_in_factor(current)

            self.zoom(fac)

        elif wheel_delta < 0:
            current = self.zoom_factor

            fac = calc_zoom_out_factor(current)

            self.zoom(fac)

        #self.mouse_wheel.emit(event)


class MenuDontClose(QMenu):
    def mouseReleaseEvent(self, e):
        try:
            action = self.activeAction()
            if action and action.isEnabled():
                action.trigger()
            else:
                QMenu.mouseReleaseEvent(self, e)
        except:
            traceback.print_exc()


class BWEntityEntry(QListWidgetItem):
    def __init__(self, xml_ref, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.xml_ref = xml_ref


class BWEntityListWidget(QListWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def select_item(self, pos):
        #item = self.item(pos)
        self.setCurrentRow(pos)


class BWPassengerWindow(QMdiSubWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setBaseSize(400, 400)

        self.centralwidget = QWidget(self)
        self.setWidget(self.centralwidget)

        layout = QHBoxLayout(self.centralwidget)
        self.passengerlist = QListWidget(self.centralwidget)
        layout.addWidget(self.passengerlist)
        self.setWindowTitle("Passengers")

    def reset(self):
        self.passengerlist.clearSelection()
        self.passengerlist.clear()

    def add_passenger(self, passenger_name, passenger_id):
        item = BWEntityEntry(passenger_id,
                             passenger_name)
        self.passengerlist.addItem(item)

    def set_title(self, entityname):
        self.setWindowTitle("Passengers - {0}".format(entityname))


class XMLTextEdit(QTextEdit):
    #mouse_clicked = pyqtSignal(QMouseEvent)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        """self.goto_id_action = QAction("Go To ID", self)
        self.goto_shortcut = QKeySequence(Qt.CTRL+Qt.Key_G)
        self.goto_id_action.setShortcut(self.goto_shortcut)
        self.goto_id_action.setShortcutContext(Qt.WidgetShortcut)"""

        #self.context_menu.exec(event.globalPos())
        #self.context_menu.destroy()


class ActionWithOwner(QAction):
    triggered_owner = pyqtSignal(object)

    def __init__(self, *args, **kwargs):
        self.action_owner = kwargs["action_owner"]
        del kwargs["action_owner"]

        super().__init__(*args, **kwargs)

        self.triggered.connect(self.triggered_with_owner)

    def triggered_with_owner(self):
        self.triggered_owner.emit(self.action_owner)





class BWEntityXMLEditor(QMdiSubWindow):
    triggered = pyqtSignal(object)
    closing = pyqtSignal(object)

    def __init__(self, *args, **kwargs):
        if "windowtype" in kwargs:
            self.windowname = kwargs["windowtype"]
            del kwargs["windowtype"]
        else:
            self.windowname = "XML Object"

        super().__init__(*args, **kwargs)

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


        self.goto_id_action = ActionWithOwner("Go To ID", self, action_owner=self)

        self.addAction(self.goto_id_action)

        self.goto_shortcut = QKeySequence(Qt.CTRL+Qt.Key_G)


        self.goto_id_action.setShortcut(self.goto_shortcut)
        #self.goto_id_action.setShortcutContext(Qt.WidgetShortcut)
        self.goto_id_action.setAutoRepeat(False)

        self.goto_id_action.triggered_owner.connect(self.open_new_window)

        self.textbox_xml = XMLTextEdit(self.centralwidget)
        self.button_xml_savetext = QPushButton(self.centralwidget)
        self.button_xml_savetext.setText("Save XML")
        self.button_xml_savetext.setMaximumWidth(400)
        self.textbox_xml.setLineWrapMode(QTextEdit.NoWrap)
        self.textbox_xml.setContextMenuPolicy(Qt.CustomContextMenu)
        self.textbox_xml.customContextMenuRequested.connect(self.my_context_menu)

        metrics = QFontMetrics(font)
        self.textbox_xml.setTabStopWidth(4 * metrics.width(' '))
        self.textbox_xml.setFont(font)

        self.verticalLayout.addWidget(self.textbox_xml)
        self.verticalLayout.addWidget(self.button_xml_savetext)
        self.setWindowTitle(self.windowname)

    def set_content(self, xmlnode):
        try:
            self.textbox_xml.setText(etree.tostring(xmlnode, encoding="unicode"))
            self.entity = xmlnode.get("id")
        except:
            traceback.print_exc()

    def open_new_window(self, owner):
        #print("It was pressed!", owner)
        #print("selected:", owner.textbox_xml.textCursor().selectedText())

        self.triggered.emit(self)

    def my_context_menu(self, position):
        try:
            #print("Triggered!")
            #print(event.x(), event.y())
            #print(args)
            context_menu = self.textbox_xml.createStandardContextMenu()
            context_menu.addAction(self.goto_id_action)
            context_menu.exec(self.mapToGlobal(position))
            context_menu.destroy()
            del context_menu
            #self.context_menu.exec(event.globalPos())
            #return super().contextMenuEvent(event)
        except:
            traceback.print_exc()

    def get_content(self):
        try:
            content = self.textbox_xml.toPlainText()
            xmlnode = etree.fromstring(content)

            return xmlnode
        except:
            traceback.print_exc()

    def set_title(self, objectname):
        self.setWindowTitle("{0} - {1}".format(self.windowname, objectname))

    def reset(self):
        pass

def collides(face_v1, face_v2, face_v3, box_mid_x, box_mid_z, box_size_x, box_size_z):
    min_x = min(face_v1[0], face_v2[0], face_v3[0]) - box_mid_x
    max_x = max(face_v1[0], face_v2[0], face_v3[0]) - box_mid_x

    min_z = min(face_v1[2], face_v2[2], face_v3[2]) - box_mid_z
    max_z = max(face_v1[2], face_v2[2], face_v3[2]) - box_mid_z

    half_x = box_size_x / 2.0
    half_z = box_size_z / 2.0

    if max_x < -half_x or min_x > +half_x:
        return False
    if max_z < -half_z or min_z > +half_z:
        return False

    return True

def subdivide_grid(minx, minz,
                   gridx_start, gridx_end, gridz_start, gridz_end,
                   cell_size, triangles, vertices, result):
    #print("Subdivision with", gridx_start, gridz_start, gridx_end, gridz_end, (gridx_start+gridx_end) // 2, (gridz_start+gridz_end) // 2)
    if gridx_start == gridx_end-1 and gridz_start == gridz_end-1:
        if gridx_start not in result:
            result[gridx_start] = {}
        result[gridx_start][gridz_start] = triangles

        return True

    assert gridx_end > gridx_start or gridz_end > gridz_start

    halfx = (gridx_start+gridx_end) // 2
    halfz = (gridz_start+gridz_end) // 2

    quadrants = (
        [], [], [], []
    )
    # x->
    # 2 3 ^
    # 0 1 z
    coordinates = (
        (0, gridx_start , halfx     , gridz_start   , halfz),   # Quadrant 0
        (1, halfx       , gridx_end , gridz_start   , halfz),     # Quadrant 1
        (2, gridx_start , halfx     , halfz         , gridz_end),     # Quadrant 2
        (3, halfx       , gridx_end , halfz         , gridz_end) # Quadrant 3
    )
    skip = []
    if gridx_start == halfx:
        skip.append(0)
        skip.append(2)
    if halfx == gridx_end:
        skip.append(1)
        skip.append(3)
    if gridz_start == halfz:
        skip.append(0)
        skip.append(1)
    if halfz == gridz_end:
        skip.append(2)
        skip.append(3)


    for i, face in triangles:
        v1_index, v2_index, v3_index = face

        v1 = vertices[v1_index[0]-1]
        v2 = vertices[v2_index[0]-1]
        v3 = vertices[v3_index[0]-1]


        for quadrant, startx, endx, startz, endz in coordinates:
            if quadrant not in skip:
                area_size_x = (endx - startx)*cell_size
                area_size_z = (endz - startz)*cell_size

                if collides(v1, v2, v3,
                            minx+startx*cell_size + area_size_x//2,
                            minz+startz*cell_size + area_size_z//2,
                            area_size_x,
                            area_size_z):
                    #print(i, "collided")
                    quadrants[quadrant].append((i, face))


    for quadrant, startx, endx, startz, endz in coordinates:
        #print("Doing subdivision, skipping:", skip)
        if quadrant not in skip:
            #print("doing subdivision with", coordinates[quadrant])
            subdivide_grid(minx, minz,
                           startx, endx, startz, endz,
                           cell_size, quadrants[quadrant], vertices, result)

def normalize_vector(v1):
    n = (v1[0]**2 + v1[1]**2 + v1[2]**2)**0.5
    return v1[0]/n, v1[1]/n, v1[2]/n

def create_vector(v1, v2):
    return v2[0]-v1[0],v2[1]-v1[1],v2[2]-v1[2]

def cross_product(v1, v2):
    cross_x = v1[1]*v2[2] - v1[2]*v2[1]
    cross_y = v1[2]*v2[0] - v1[0]*v2[2]
    cross_z = v1[0]*v2[1] - v1[1]*v2[0]
    return cross_x, cross_y, cross_z

class Collision(object):
    def __init__(self, verts, faces):
        self.verts = verts
        self.faces = faces

        cell_size = 100

        box_size_x = cell_size
        box_size_z = cell_size

        smallest_x =-6000#max(-6000.0, smallest_x)
        smallest_z = -6000#max(-6000.0, smallest_z)
        biggest_x = 6000#min(6000.0, biggest_x)
        biggest_z = 6000#min(6000.0, biggest_z)
        print("dimensions are changed to", smallest_x, smallest_z, biggest_x, biggest_z)
        start_x = math.floor(smallest_x / box_size_x) * box_size_x
        start_z = math.floor(smallest_z / box_size_z) * box_size_z
        end_x = math.ceil(biggest_x / box_size_x) * box_size_x
        end_z = math.ceil(biggest_z / box_size_z) * box_size_z
        diff_x = abs(end_x - start_x)
        diff_z = abs(end_z - start_z)
        grid_size_x = int(diff_x // box_size_x)
        grid_size_z = int(diff_z // box_size_z)

        self.grid = {}
        triangles = [(i, face) for i, face in enumerate(faces)]
        subdivide_grid(start_x, start_z, 0, grid_size_x, 0, grid_size_z, cell_size, triangles, self.verts, self.grid)
        print("finished generating triangles")
        print(grid_size_x, grid_size_z)

        self.collide_ray_downwards(1,2)

    def collide_ray_downwards(self, x, z, y=99999):
        grid_x = int((x+6000) // 100)
        grid_z = int((z+6000) // 100)

        triangles = self.grid[grid_x][grid_z]

        verts = self.verts

        y = y
        dir_x = 0
        dir_y = -1.0
        dir_z = 0

        hit = False

        for i, face in triangles:#face in self.faces:#
            v1index, v2index, v3index = face

            v1 = verts[v1index[0]-1]
            v2 = verts[v2index[0]-1]
            v3 = verts[v3index[0]-1]

            edge1 = create_vector(v1, v2)
            edge2 = create_vector(v1, v3)

            normal = cross_product(edge1, edge2)
            if normal[0] == normal[1] == normal[2] == 0.0:
                continue
            normal = normalize_vector(normal)

            D = -v1[0]*normal[0] + -v1[1]*normal[1] + -v1[2]*normal[2]

            if normal[1]*dir_y == 0.0:#abs(normal[1] * dir_y) < 10**(-6):
                continue # triangle parallel to ray

            t = -(normal[0] * x + normal[1] * y + normal[2] * z + D) / (normal[1]*dir_y)

            point = x, (y+dir_y*t), z
            #print(point)
            edg1 = create_vector(v1, v2)
            edg2 = create_vector(v2, v3)
            edg3 = create_vector(v3, v1)

            vectest1 = cross_product(edg1, create_vector(v1, point))
            vectest2 = cross_product(edg2, create_vector(v2, point))
            vectest3 = cross_product(edg3, create_vector(v3, point))

            if ((normal[0]*vectest1[0] + normal[1]*vectest1[1] + normal[2]*vectest1[2]) >= 0 and
                 (normal[0]*vectest2[0] + normal[1]*vectest2[1] + normal[2]*vectest2[2]) >= 0 and
                  (normal[0]*vectest3[0] + normal[1]*vectest3[1] + normal[2]*vectest3[2]) >= 0):

                hit = True
                break
        if hit:
            #print("HIT", point)
            return point, v1, v2, v3
        else:
            return None