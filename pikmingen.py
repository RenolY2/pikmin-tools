
class TextRoot(list):
    pass

class TextNode(list):
    pass

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

    def from_textnode(self, textnode):
        self.version = textnode[0] # Always v0.3?
        self.reserved = int(textnode[1]) # Unknown
        self.days_till_resurrection = int(textnode[2]) # Probably how many days till an object reappears.
        self.arguments = [int(x) for x in textnode[3]] # object data that differs per object type
        self.position_x, self.position_y, self.position_z = map(float, textnode[4]) # XYZ Position
        self.offset_x, self.offset_y, self.offset_z = map(float, textnode[5]) # XYZ offset

        self.x = self.position_x + self.offset_x
        self.y = self.position_y + self.offset_y
        self.z = self.position_z + self.offset_z

        # Sometimes the identifier information has 2 or 3 arguments so we handle it like this
        self.object_type = textnode[6][0] # Commonly a 4 character string
        self.identifier_misc = textnode[6][1:] # Sometimes just a 4 digit number with preceeding

        self._object_data = textnode[7:] # All the remaining data, differs per object type

        print("Object", self.identifier, "with position", self.position_x, self.position_y, self.position_z)

    def to_textnode(self):
        textnode = TextNode()

        textnode.append(self.version)
        textnode.append(self.reserved)
        textnode.append(self.days_till_resurrection)
        textnode.append(self.arguments)
        textnode.append([self.position_x, self.position_y, self.position_z])
        textnode.append([self.offset_x, self.offset_y, self.offset_z])

        identifier = [self.object_type]
        identifier.extend(self.identifier_misc)
        textnode.append(identifier)

        textnode.extend(self._object_data)

        return textnode