import json
from copy import deepcopy
from struct import pack
from itertools import chain
from io import StringIO

import libpiktxt



class TextRoot(list):
    pass


class TextNode(list):
    pass


ONYN_ROCKET = "Rocket"
ONYN_REDONION = "Red Onion"
ONYN_YELLOWONION = "Yellow Onion"
ONYN_BLUEONION = "Blue Onion"

BRIDGE_SHORT = "Short Bridge"
BRIDGE_SHORT_UP = "Short Bridge (Slanted)"
BRIDGE_LONG = "Long Bridge"
BRIDGES = {"0": BRIDGE_SHORT,
           "1": BRIDGE_SHORT_UP,
           "2": BRIDGE_LONG}

GATE_SAND = "Gate"
GATE_ELECTRIC = "Electric Gate"

with open("resources/entities.json", "r") as f:
    ENTITY_DICT = json.load(f)

TEKIS = ENTITY_DICT["teki"]
#BRIDGES = ENTITY_DICT["bridges"]
TREASURES = ENTITY_DICT["treasures"]
EXPKIT_TREASURES = ENTITY_DICT["expkit_treasures"]


def assert_notlist(val):
    assert not isinstance(val, list)


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
        self.preceeding_comment = []

        self._horizontal_rotation = None

        self._useful_name = "None"

    def from_text(self, text):
        node = libpiktxt.PikminTxt()
        node.from_text(text)

        if len(node._root) == 1:
            self.from_textnode(node._root[0])
        else:
            self.from_textnode(node._root)

        f = StringIO(text)

        comments = []
        for line in f:
            if line.startswith("#"):
                comments.append(line)
            elif line[0] != "#":
                break

        self.set_preceeding_comment(comments)
        if self.get_rotation() is not None:
            self._horizontal_rotation = float(self.get_rotation()[1])
        else:
            self._horizontal_rotation = None
        self.update_useful_name()

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
        if self.get_rotation() is not None:
            self._horizontal_rotation = float(self.get_rotation()[1])
        else:
            self._horizontal_rotation = None
        #print("Object", self.identifier, "with position", self.position_x, self.position_y, self.position_z)
        self.update_useful_name()

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
        self.set_preceeding_comment(other_pikminobj.preceeding_comment)

        if self.get_rotation() is not None:
            self._horizontal_rotation = float(self.get_rotation()[1])
        else:
            self._horizontal_rotation = None
        self.update_useful_name()

    def copy(self):
        #newobj = PikminObject()
        #newobj.from_pikmin_object(self)
        return deepcopy(self)#newobj

    def get_rotation(self):
        if self.object_type == "{item}":
            itemdata = self._object_data[0]

            return tuple(float(x) for x in itemdata[1])

        elif self.object_type == "{teki}":
            return 0.0, float(self._object_data[2]), 0.0
        elif self.object_type == "{pelt}":
            peltdata = self._object_data[0]

            return tuple(float(x) for x in peltdata[1])
        else:
            return None

    def update_useful_name(self):
        self._useful_name = self._get_useful_object_name()

    def get_useful_object_name(self):
        return self._useful_name

    def _get_useful_object_name(self):
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

            elif subtype == "{brdg}":
                bridgetype = itemdata[3]
                if bridgetype in BRIDGES:
                    return BRIDGES[bridgetype]
                else:
                    return "<unknown bridge type:{0}>".format(bridgetype)
            elif subtype == "{gate}":
                return GATE_SAND
            elif subtype == "{dgat}":
                return GATE_ELECTRIC
            elif subtype == "{dwfl}":
                blocktype = itemdata[4]
                is_seesaw = itemdata[5]
                suffix = ""

                if is_seesaw == "1":
                    suffix = " [Seesaw]"
                elif is_seesaw != "0":
                    suffix = " [Invalid]"

                if blocktype == "0":
                    return "Small Block"+suffix
                elif blocktype == "1":
                    return "Normal Block"+suffix
                elif blocktype == "2":
                    return "Paper Bag"+suffix
                else:
                    return "Invalid dwfl"
            elif subtype == "{plnt}":
                name = "Burg. Spiderwort"
                planttype = itemdata[3]
                if planttype == "0":
                    name += " (Red Berry)"
                elif planttype == "1":
                    name += " (Purple Berry)"
                elif planttype == "2":
                    name += " (Mixed)"
                else:
                    name += " (Invalid)"

                return name

            return self.object_type+subtype

        elif self.object_type == "{teki}":
            identifier = self.identifier_misc[1][1:]
            if identifier in TEKIS:
                return "Teki: "+TEKIS[identifier]
            else:
                return "Unknown Teki: {0}".format(identifier)

        elif self.object_type == "{pelt}":
            mgrid = self._object_data[0][0]

            if mgrid == "0":
                treasureid = self._object_data[0][3]
                if isinstance(treasureid, list):
                    pellet_type = treasureid[0]

                    if pellet_type == "0":
                        return "Blue Pellet"
                    elif pellet_type == "1":
                        return "Red Pellet"
                    elif pellet_type == "2":
                        return "Yellow Pellet"
                    else:
                        return "Unknown Pellet"
                else:
                    return "Invalid Pellet"

            if mgrid == "3":
                treasureid = self._object_data[0][3]
                if treasureid in TREASURES:
                    return "Treasure: "+TREASURES[treasureid]
                else:
                    return "Unknown treasure: {0}".format(treasureid)
            elif mgrid == "4":
                treasureid = self._object_data[0][3]
                if treasureid in EXPKIT_TREASURES:
                    return "ExpKit Treasure: "+EXPKIT_TREASURES[treasureid]
                else:
                    return "Unknown exploration kit treasure: {0}".format(treasureid)
            return self.object_type

        else:
            return self.object_type

    def get_horizontal_rotation(self):
        """if self.object_type == "{item}":
            return float(self._object_data[0][1][1])
        elif self.object_type == "{teki}":
            return float(self._object_data[2])
        elif self.object_type == "{pelt}":
            return float(self._object_data[0][1][1])
        else:
            return None"""
        return self._horizontal_rotation

    def set_rotation(self, rotation):
        if self.object_type == "{item}":
            itemdata = self._object_data[0]
            for i, val in enumerate(rotation):
                if val is not None:
                    itemdata[1][i] = val
                    if i == 1:
                        self._horizontal_rotation = float(val)

        elif self.object_type == "{teki}":
            self._object_data[2] = rotation[1]
            self._horizontal_rotation = float(rotation[1])
        elif self.object_type == "{pelt}":
            peltdata = self._object_data[0]
            for i, val in enumerate(rotation):
                if val is not None:
                    peltdata[1][i] = val
                    if i == 1:
                        self._horizontal_rotation = float(val)

    def set_preceeding_comment(self, comments):
        self.preceeding_comment = comments

    def get_identifier(self):
        try:
            name = pack(32 * "B", *self.arguments).split(b"\x00")[0]
            name = name.decode("shift_jis-2004", errors="backslashreplace")
        except:
            name = "<failed to decode identifier>"

        return name
    
    def add_remaining_data_if_exists(self, node, data, n):
        if len(data) > n:
            node.extend(data[n:])
    
    def to_textnode(self):
        textnode = TextNode()

        #for comment in self.preceeding_comment:
        #    assert comment.startswith("#")
        #    textnode.append([comment.strip()])
        current_progress = 0

        try:
            assert_notlist(self.version)
            assert_notlist(self.reserved)
            assert_notlist(self.days_till_resurrection)
        except:
            textnode.append(self.version)
            textnode.append(self.reserved)
            textnode.append(self.days_till_resurrection)
        else:
            textnode.append([self.version, "# Version"])
            textnode.append([self.reserved, "# Reserved"])
            textnode.append([self.days_till_resurrection, "# Days till resurrection"])

        #current_progress = len(textnode)

        name = self.get_identifier()
        argsversion = self.identifier_misc[0]
        textnode.append(list(chain(self.arguments, ["# {0}".format(name)])))

        textnode.append([self.position_x, self.position_y, self.position_z, "# Position"])
        textnode.append([self.offset_x, self.offset_y, self.offset_z, "# Offset"])
        current_progress = len(textnode)
        if isinstance(self.object_type, list):
            identifier = []
            identifier.extend(self.object_type)
        else:
            identifier = [self.object_type]
        identifier.extend(self.identifier_misc)
        textnode.append(identifier)
        current_progress = len(textnode)

        try:
            if self.object_type == "{teki}" and argsversion == "{0005}":
                for i in range(12):
                    assert_notlist(self._object_data[i])
                textnode.append([self._object_data[0], "# Teki Birth Type"])
                textnode.append([self._object_data[1], "# Teki Number"])
                textnode.append([self._object_data[2], "# Face Direction"])
                textnode.append([self._object_data[3], "# 0: Point, 1: Circle"])
                textnode.append([self._object_data[4], "# appear radius"])
                textnode.append([self._object_data[5], "# enemy size"])
                textnode.append([self._object_data[6], "# Treasure item code"])
                textnode.append([self._object_data[7], "# Pellet color"])
                textnode.append([self._object_data[8], "# Pellet size"])
                textnode.append([self._object_data[9], "# Pellet Min"])
                textnode.append([self._object_data[10], "# Pellet Max"])
                textnode.append([self._object_data[11], "# Pellet Min"])
                textnode.extend(self._object_data[12:])

            elif self.object_type == "{item}":
                itemdata = self._object_data[0]
                itemid = itemdata[0].strip()
                newitemdata = TextNode()
                newitemdata.append([itemid, "# Item ID"])
                newitemdata.append([itemdata[1][0],itemdata[1][1], itemdata[1][2],  "# rotation"])
                newitemdata.append([itemdata[2], "# item local version"])
                assert_notlist(itemdata[2])

                if itemid == "{dwfl}":
                    for i in range(3, 7): assert_notlist(itemdata[i])
                    newitemdata.append([itemdata[3], "# Required pikmin count for weighting down the downfloor (if behaviour=0)"])
                    newitemdata.append([itemdata[4], "# Type: 0=small block, 1=large block, 2=paper bag"])
                    newitemdata.append([itemdata[5], "# Behaviour: 0=normal, 1=seesaw"])
                    newitemdata.append([itemdata[6],
                                        "# ID of this downfloor. If set to seesaw, there needs to be another dwfl with same ID."])
                    
                    self.add_remaining_data_if_exists(newitemdata, itemdata, 7)
                    
                elif itemid == "{brdg}":
                    assert_notlist(itemdata[3])
                    newitemdata.append([itemdata[3], "# Bridge type: 0=short, 1=slanted, 2=long"])
                    
                    self.add_remaining_data_if_exists(newitemdata, itemdata, 4)
                    
                elif itemid == "{dgat}":
                    assert_notlist(itemdata[3])
                    newitemdata.append([itemdata[3], "# Gate Health"])
                    
                    self.add_remaining_data_if_exists(newitemdata, itemdata, 4)
                    
                elif itemid == "{gate}":
                    assert_notlist(itemdata[3])
                    assert_notlist(itemdata[4])
                    newitemdata.append([itemdata[3], "# Gate Health"])
                    newitemdata.append([itemdata[4], "# Color: 0=bright, 1=dark"])
                    
                    self.add_remaining_data_if_exists(newitemdata, itemdata, 5)
                elif itemid == "{onyn}":
                    assert_notlist(itemdata[3])
                    assert_notlist(itemdata[4])
                    newitemdata.append([itemdata[3], "# Onion type: 0=blue, 1=red, 2=yellow, 4=rocket"])
                    newitemdata.append([itemdata[4], "# after boot? true==1"])
                    
                    self.add_remaining_data_if_exists(newitemdata, itemdata, 5)
                    
                elif itemid == "{plnt}":
                    assert_notlist(itemdata[3])
                    newitemdata.append([itemdata[3], "# Berry type: 0=Red, 1=purple, 2=mixed"])
                    
                    self.add_remaining_data_if_exists(newitemdata, itemdata, 4)
                    
                else:
                    if len(itemdata) > 2:
                        newitemdata.extend(itemdata[3:])

                textnode.append(newitemdata)
                if len(self._object_data) > 1:
                    textnode.extend(self._object_data[1:])

            elif self.object_type == "{pelt}":
                pelt_data = self._object_data[0]
                new_pelt = TextNode()
                mgrid = pelt_data[0]
                assert_notlist(mgrid)
                assert_notlist(pelt_data[2])
                if mgrid == "0":
                    new_pelt.append([mgrid, "# Pellet"])
                else:
                    new_pelt.append([mgrid, "# Treasure category: 3=regular, 4=exploration kit"])
                new_pelt.append([pelt_data[1][0], pelt_data[1][1], pelt_data[1][2], "# Rotation"])
                new_pelt.append([pelt_data[2], "# Local version"])
                if mgrid == "0":
                    #tmp = []
                    #tmp.extend(pelt_data[3])
                    new_pelt.append([pelt_data[3][0], pelt_data[3][1], "# Pellet type (0,1,2 = B,R,Y respectively) and pellet size (1,5,10,20)"])
                else:
                    assert_notlist(pelt_data[3])
                    new_pelt.append([pelt_data[3], "# Identifier of treasure, see https://pikmintkb.com/wiki/Pikmin_2_identifiers	"])

                textnode.append(new_pelt)
                if len(self._object_data) > 1:
                    textnode.extend(self._object_data[1:])
            else:
                textnode.extend(self._object_data)
        except Exception as e:
            print(e)

            newtextnode = TextNode()
            newtextnode.extend(textnode[:current_progress])
            newtextnode.extend(self._object_data)

            textnode = newtextnode

        return textnode
