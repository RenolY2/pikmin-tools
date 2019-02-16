from OpenGL.GL import *
from .vectors import Vector3


class Model(object):
    def __init__(self):
        pass

    def render(self):
        pass

ALPHA = 0.8

class Waterbox(Model):
    def __init__(self, corner_bottomleft, corner_topright):
        self.corner_bottomleft = corner_bottomleft
        self.corner_topright = corner_topright

    def render(self):
        x1,y1,z1 = self.corner_bottomleft
        x2,y2,z2 = self.corner_topright
        glColor4f(0.1, 0.1875, 0.8125, ALPHA)
        glBegin(GL_TRIANGLE_FAN) # Bottom, z1
        glVertex3f(x2, y1, z1)
        glVertex3f(x2, y2, z1)
        glVertex3f(x1, y2, z1)
        glVertex3f(x1, y1, z1)
        glEnd()
        glBegin(GL_TRIANGLE_FAN) # Front, x1
        glVertex3f(x1, y1, z1)
        glVertex3f(x1, y1, z2)
        glVertex3f(x1, y2, z2)
        glVertex3f(x1, y2, z1)
        glEnd()

        glBegin(GL_TRIANGLE_FAN) # Side, y1
        glVertex3f(x1, y1, z1)
        glVertex3f(x1, y1, z2)
        glVertex3f(x2, y1, z2)
        glVertex3f(x2, y1, z1)
        glEnd()
        glBegin(GL_TRIANGLE_FAN) # Back, x2
        glVertex3f(x2, y1, z1)
        glVertex3f(x2, y1, z2)
        glVertex3f(x2, y2, z2)
        glVertex3f(x2, y2, z1)
        glEnd()
        glBegin(GL_TRIANGLE_FAN) # Side, y2
        glVertex3f(x1, y2, z1)
        glVertex3f(x1, y2, z2)
        glVertex3f(x2, y2, z2)
        glVertex3f(x2, y2, z1)
        glEnd()
        glBegin(GL_TRIANGLE_FAN) # Top, z2
        glVertex3f(x1, y1, z2)
        glVertex3f(x1, y2, z2)
        glVertex3f(x2, y2, z2)
        glVertex3f(x2, y1, z2)
        glEnd()


class TexturedPlane(object):
    def __init__(self, planewidth, planeheight, qimage):
        ID = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, ID)
        glPixelStorei(GL_UNPACK_ALIGNMENT, 1)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_BASE_LEVEL, 0)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAX_LEVEL, 0)

        imgdata = bytes(qimage.bits().asarray(qimage.width()*qimage.height()*4))
        glTexImage2D(GL_TEXTURE_2D, 0, 4, qimage.width(), qimage.height(), 0, GL_BGRA, GL_UNSIGNED_BYTE, imgdata)

        self.ID = ID
        self.planewidth = planewidth
        self.planeheight = planeheight

        self.offset_x = 0
        self.offset_z = 0
        self.color = (0.0, 0.0, 0.0)

    def set_offset(self, x, z):
        self.offset_x = x
        self.offset_z = z

    def set_color(self, color):
        self.color = color

    def apply_color(self):
        glColor4f(self.color[0], self.color[1], self.color[2], 1.0)

    def render(self):
        w, h = self.planewidth, self.planeheight
        offsetx, offsetz = self.offset_x, self.offset_z
        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, self.ID)
        glBegin(GL_TRIANGLE_FAN)
        glTexCoord2f(0.0, 0.0)
        glVertex3f(-0.5*w+offsetx, -0.5*h+offsetz, 0)
        glTexCoord2f(0.0, 1.0)
        glVertex3f(-0.5*w+offsetx, 0.5*h+offsetz, 0)
        glTexCoord2f(1.0, 1.0)
        glVertex3f(0.5*w+offsetx, 0.5*h+offsetz, 0)
        glTexCoord2f(1.0, 0.0)
        glVertex3f(0.5*w+offsetx, -0.5*h+offsetz, 0)
        glEnd()

    def render_coloredid(self, id):
        w, h = self.planewidth, self.planeheight
        offsetx, offsetz = self.offset_x, self.offset_z
        glDisable(GL_TEXTURE_2D)
        glColor3ub((id >> 16) & 0xFF, (id >> 8) & 0xFF, (id >> 0) & 0xFF)
        glBegin(GL_TRIANGLE_FAN)
        #glTexCoord2f(0.0, 0.0)
        glVertex3f(-0.5*w+offsetx, -0.5*h+offsetz, 0)
        #glTexCoord2f(0.0, 1.0)
        glVertex3f(-0.5*w+offsetx, 0.5*h+offsetz, 0)
        #glTexCoord2f(1.0, 1.0)
        glVertex3f(0.5*w+offsetx, 0.5*h+offsetz, 0)
        #glTexCoord2f(1.0, 0.0)
        glVertex3f(0.5*w+offsetx, -0.5*h+offsetz, 0)
        glEnd()

