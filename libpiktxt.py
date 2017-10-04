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
        x1, y1, z1, x2, y2, z2 = (float(x) for x in coords)

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


# class for route files which keep the paths used by pikmin to carry back treasures
class RouteTxt(PikminTxt):
    def __init__(self):
        super().__init__()

        self.waypoints = {}
        self.links = {}

    def add_link(self, waypoint_index, dest_waypoint_index):
        if waypoint_index != dest_waypoint_index:
            if waypoint_index not in self.links:
                self.links[waypoint_index] = [dest_waypoint_index]
            elif dest_waypoint_index not in self.links[waypoint_index]:
                self.links[waypoint_index].append(dest_waypoint_index)

    def remove_link(self, waypoint_index, dest_waypoint_index):
        if waypoint_index != dest_waypoint_index:
            assert waypoint_index in self.links
            assert dest_waypoint_index in self.links[waypoint_index]

            self.links[waypoint_index].remove(dest_waypoint_index)

            if len(self.links[waypoint_index]) == 0:
                del self.links[waypoint_index]


    def add_waypoint(self, x, y, z, radius):
        indices = sorted(self.waypoints.keys())

        newindex = None

        if len(indices) == 0:
            self.waypoints[0] = [x,y,z,radius]
            newindex = 0
        else:
            biggest = indices[-1]

            newindex = None
            for i in range(biggest+2):
                if i not in self.waypoints:
                    newindex = i
                    self.waypoints[i] = [x,y,z,radius]
                    break

        assert newindex is not None

        return newindex

    def remove_waypoint(self, index):
        del self.waypoints[index]

        if index in self.links:
            del self.links[index]

        # Remove all links pointing to the index
        for link, linksto in self.links.items():
            if index in linksto:
                linksto.remove(index)

    def from_file(self, f):
        super().from_file(f)

        self.waypoints = {}
        self.links = {}


        waypoint_count = int(self._root[0])
        assert waypoint_count == len(self._root) - 1

        # Prefill waypoints with placeholder value so we can add waypoints at specific indices
        #self.waypoints.extend(None for x in range(waypoint_count))



        if waypoint_count > 0:
            for waypoint in self._root[1:]:
                index = int(waypoint[0])
                link_count = int(waypoint[1])
                assert link_count == len(waypoint) - 3
                #assert index < len(self.waypoints)

                for link in waypoint[2:-1]:
                    #assert int(link) < len(self.waypoints)
                    self.add_link(index, int(link))

                position = [float(x) for x in waypoint[-1]]

                #self.waypoints.append(position)
                self.waypoints[index] = position

        assert None not in self.waypoints

    def write(self, f, *args, **kwargs):
        self._root = TextRoot()
        self._root.append([len(self.waypoints), "# waypoint count"])

        # This is for cleaning up gaps in the indices
        indices = sorted(self.waypoints.keys())
        map_indices_to_gapless_indices = {}
        for i, j in enumerate(indices):
            map_indices_to_gapless_indices[j] = i


        #for i, waypoint_pos in self.waypoints.items():
        for i in indices:
            waypoint_pos = self.waypoints[i]
            fixed_i = map_indices_to_gapless_indices[i]

            waypoint_node = TextNode()
            waypoint_node.append([fixed_i, "# index"])  # waypoint index
            if i in self.links:
                waypoint_node.append([len(self.links[i]), "# numLinks"])
                for j, link in enumerate(self.links[i]):
                    link = map_indices_to_gapless_indices[link]
                    waypoint_node.append([link, "# link {}".format(j)])
            else:
                waypoint_node.append(0)

            waypoint_node.append(waypoint_pos)
            self._root.append(waypoint_node)

        super().write(f, *args, **kwargs)


if __name__ == "__main__":
    import os
    import pprint

    pikmintext = RouteTxt()

    input_path = os.path.join("examples", "route.txt")
    output_pat = input_path+"new.txt"

    with open(input_path, "r", encoding="shift-jis") as f:
        print("parsing", input_path)
        pikmintext.from_file(f)

    print(pikmintext.waypoints)

    wp = pikmintext.add_waypoint(10, 20, 30, 1337)
    for i in range(15):
        pikmintext.add_link(wp, wp-i)
        pikmintext.add_link(wp-i, wp)
    with open(output_pat, "w") as f:
        pikmintext.write(f)
    pikmintext.remove_waypoint(wp)
    with open(output_pat+"2.txt", "w") as f:
        pikmintext.write(f)


