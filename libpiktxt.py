# Library for parsing some Pikmin 2 Text files (often have the ending .txt)


class TextRoot(list):
    pass

class TextNode(list):
    pass


def parse_structure(f, depth=0):
    data = TextNode()

    for line in f:
        #line = line.strip()
        for i, character in enumerate(line):
            if character == "#":
                line = line[:i]
                break
        line = line.strip()

        if line == "{":
            nested_data = TextNode(parse_structure(f, depth+1))
            data.append(nested_data)
        elif line == "}":
            break
        elif line != "":
            values = line.split(" ")
            if len(values) == 1:
                data.append(values[0])
            else:
                data.append(values)

    return data

# General parser/writer for all txt files, but not very useful
class PikminTxt(object):
    def __init__(self):
        self._root = TextRoot()

    def from_file(self, f):
        self._root = TextRoot(parse_structure(f, depth=0))

    def write(self, f, node=None, depth=0, indent_char="\t"):
        if node is None:
            node = self._root

        for item in node:
            if isinstance(item, TextNode):
                f.write(depth*indent_char+"{\n")
                self.write(f, item, depth=depth+1, indent_char=indent_char)
                f.write(depth*indent_char+"}\n")
            else:
                f.write(depth*indent_char)
                if isinstance(item, list):
                    f.write(" ".join(str(x) for x in item))
                else:
                    f.write(str(item))
                f.write("\n")

# Parser/writer for waterbox.txt files.
# Every entry in WaterboxTxt.waterboxes is x1,y1,z1, x2,y2,z2 specifying
# the corners of the water box.
class WaterboxTxt(PikminTxt):
    def __index__(self):
        super().__init__()

        self.waterboxes = []

    def from_file(self, f):
        super().from_file(f)

        self.waterboxes = []
        assert self._root[0] == "0" # In the waterbox.txt files it's a "Type", but always seems to be 0

        waterbox_list = self._root[1]

        waterbox_count = int(waterbox_list[0])
        assert len(waterbox_list) - 1 == waterbox_count

        if waterbox_count > 0:
            for waterbox in waterbox_list[1:]:
                x1, y1, z1, x2, y2, z2 = waterbox

                self.add_waterbox(
                    float(x1), float(y1), float(z1),
                    float(x2), float(y2), float(z2)
                )

    def add_waterbox(self, *coords):
        x1, y1, z1, x2, y2, z2 = coords

        self.waterboxes.append([
            min(x1, x2), min(y1, y2), min(z1, z2),
            max(x1, x2), max(y1, y2), max(z1, z2)
        ])

    def write(self, f, *args, **kwargs):
        self._root = TextRoot()
        self._root.append([0])

        waterbox_count = len(self.waterboxes)

        waterbox_data = TextNode()
        waterbox_data.append([waterbox_count])
        if waterbox_count > 0:
            for waterbox in self.waterboxes:
                waterbox_data.append([float(x) for x in waterbox])
        self._root.append(waterbox_data)
        super().write(f, *args, **kwargs)




if __name__ == "__main__":
    import os
    import pprint

    pikmintext = WaterboxTxt()
    input_path = os.path.join("examples", "waterbox.txt")
    output_pat = input_path+"new.txt"
    with open(input_path, "r", encoding="shift-jis") as f:
        print("parsing", input_path)
        pikmintext.from_file(f)
    #pprint.pprint(pikmintext.root)
    #print(pikmintext.waterboxes)
    with open(output_pat, "w") as f:
        pikmintext.write(f)

