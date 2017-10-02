def read_vertex(v_data):
    split = v_data.split("/")
    if len(split) == 3:
        vnormal = int(split[2])
    else:
        vnormal = None
    v = int(split[0])
    return v, vnormal

def read_obj(objfile):

    vertices = []
    faces = []
    face_normals = []
    normals = []

    for line in objfile:
        line = line.strip()
        args = line.split(" ")

        if len(args) == 0 or line.startswith("#"):
            continue
        cmd = args[0]

        if cmd == "v":
            if "" in args:
                args.remove("")
            x,y,z = map(float, args[1:4])
            vertices.append((x,y,z))
        elif cmd == "f":
            # if it uses more than 3 vertices to describe a face then we panic!
            # no triangulation yet.
            if len(args) != 4:
                raise RuntimeError("Model needs to be triangulated! Only faces with 3 vertices are supported.")
            v1, v2, v3 = map(read_vertex, args[1:4])
            faces.append((v1,v2,v3))
        elif cmd == "vn":
            nx,ny,nz = map(float, args[1:4])
            normals.append((nx,ny,nz))


    #objects.append((current_object, vertices, faces))
    return vertices, faces, normals