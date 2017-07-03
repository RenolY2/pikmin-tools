# Library for parsing some Pikmin 2 Text files (often have the ending .txt)

class TextRoot(list):
    pass

class TextItem(list):
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
            data.append(TextItem(line.split(" ")))

    return data

class PikminTxt(object):
    def __init__(self):
        self.root = TextRoot()

    def from_file(self, f):
        self.root = TextRoot(parse_structure(f, depth=0))

    def write(self, f, node=None, depth=0, indent_char="\t"):
        if node is None:
            node = self.root

        for item in node:
            if isinstance(item, TextItem):
                f.write(depth*indent_char)
                f.write(" ".join(item))
                f.write("\n")
            elif isinstance(item, TextNode):
                f.write(depth*indent_char+"{\n")
                self.write(f, item, depth=depth+1, indent_char=indent_char)
                f.write(depth*indent_char+"}\n")

if __name__ == "__main__":
    import os
    import pprint

    pikmintext = PikminTxt()
    input_path = os.path.join("examples", "caveinfo_toy.txt")
    output_pat = input_path+"new.txt"
    with open(input_path, "r", encoding="shift-jis") as f:
        print("parsing", input_path)
        pikmintext.from_file(f)
    pprint.pprint(pikmintext.root)

    with open(output_pat, "w") as f:
        pikmintext.write(f)