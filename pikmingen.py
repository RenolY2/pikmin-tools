import libpiktxt
from struct import pack
from itertools import chain


class TextRoot(list):
    pass


class TextNode(list):
    pass

ONYN_ROCKET = "Rocket"
ONYN_REDONION = "Red Onion"
ONYN_YELLOWONION = "Yellow Onion"
ONYN_BLUEONION = "Blue Onion"

class PikminObject(object):
    def __init__(self):
        self.version = "{v0.3}"
        self.reserved = 0
        self.days_till_resurrection = 0
        self.arguments = [0 for i in range(32)]

        self.position_x = self.position_y = self.position_z = 0.0
        self.offset_x = self.offset_y = self.offset_z = 0.0
        self.x = self.y = self.z = 0.0

        self.object_type = None
        self.identifier = None
        self.identifier_misc = None
        self._object_data = TextNode()

    def from_text(self, text):
        node = libpiktxt.PikminTxt()
        node.from_text(text)
        self.from_textnode(node._root)

    def from_textnode(self, textnode):
        self.version = textnode[0]  # Always v0.3?
        self.reserved = int(textnode[1])  # Unknown
        self.days_till_resurrection = int(textnode[2])  # Probably how many days till an object reappears.
        self.arguments = [int(x) for x in textnode[3]]  # 32 byte shift-jis encoded identifier string
        self.position_x, self.position_y, self.position_z = map(float, textnode[4])  # XYZ Position
        self.offset_x, self.offset_y, self.offset_z = map(float, textnode[5])  # XYZ offset

        self.x = self.position_x + self.offset_x
        self.y = self.position_y + self.offset_y
        self.z = self.position_z + self.offset_z

        # Sometimes the identifier information has 2 or 3 arguments so we handle it like this
        self.object_type = textnode[6][0]  # Commonly a 4 character string
        self.identifier_misc = textnode[6][1:]  # Sometimes just a 4 digit number with preceeding

        self._object_data = textnode[7:]  # All the remaining data, differs per object type

        #print("Object", self.identifier, "with position", self.position_x, self.position_y, self.position_z)

    def from_pikmin_object(self, other_pikminobj):
        self.version = other_pikminobj.version
        self.reserved = other_pikminobj.reserved
        self.days_till_resurrection = other_pikminobj.days_till_resurrection
        self.arguments = other_pikminobj.arguments

        self.position_x = other_pikminobj.position_x
        self.position_y = other_pikminobj.position_y
        self.position_z = other_pikminobj.position_z

        self.offset_x = other_pikminobj.offset_x
        self.offset_y = other_pikminobj.offset_y
        self.offset_z = other_pikminobj.offset_z

        self.x = self.position_x + self.offset_x
        self.y = self.position_y + self.offset_y
        self.z = self.position_z + self.offset_z

        self.object_type = other_pikminobj.object_type
        self.identifier_misc = other_pikminobj.identifier_misc

        self._object_data = other_pikminobj._object_data

    def copy(self):
        newobj = PikminObject()
        newobj.from_pikmin_object(self)
        return newobj

    def get_rotation(self):
        if self.object_type == "{item}":
            itemdata = self._object_data[0]

            return tuple(float(x) for x in itemdata[1])

        elif self.object_type == "{teki}":
            return 0.0, float(self._object_data[2]), 0.0
        else:
            return None

    def get_useful_object_name(self):
        if self.object_type == "{item}":
            itemdata = self._object_data[0]
            subtype = itemdata[0]

            if subtype == "{onyn}":
                oniontype = itemdata[3]
                if oniontype == "4":
                    return ONYN_ROCKET
                elif oniontype == "2":
                    return ONYN_YELLOWONION
                elif oniontype == "1":
                    return ONYN_REDONION
                elif oniontype == "0":
                    return ONYN_BLUEONION

            return self.object_type+subtype
        else:
            return self.object_type

    def get_horizontal_rotation(self):
        if self.object_type == "{item}":
            return float(self._object_data[0][1][1])
        elif self.object_type == "{teki}":
            return float(self._object_data[2])
        else:
            return None

    def set_rotation(self, rotation):
        if self.object_type == "{item}":
            itemdata = self._object_data[0]
            for i, val in enumerate(rotation):
                if val is not None:
                    itemdata[1][i] = val

        elif self.object_type == "{teki}":
            self._object_data[2] = rotation[1]

    def to_textnode(self):
        textnode = TextNode()

        textnode.append([self.version, "# Version"])
        textnode.append([self.reserved, "# Reserved"])
        textnode.append([self.days_till_resurrection, "# Days till resurrection"])

        name = pack(32*"B", *self.arguments).strip(b"\x00")

        try:
            name = name.decode("shift-jis")
        except:
            name = "<failed to decode identifier>"

        textnode.append(list(chain(self.arguments, ["# {0}".format(name)])))

        textnode.append([self.position_x, self.position_y, self.position_z, "# Position"])
        textnode.append([self.offset_x, self.offset_y, self.offset_z, "# Offset"])

        identifier = [self.object_type]
        identifier.extend(self.identifier_misc)
        textnode.append(identifier)

        textnode.extend(self._object_data)

        return textnode
