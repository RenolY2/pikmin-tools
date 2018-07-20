import configparser


def read_config():
    print("reading")
    cfg = configparser.ConfigParser()
    with open("piktool.ini", "r") as f:
        cfg.read_file(f)
    print("read")
    return cfg


def make_default_config():
    cfg = configparser.ConfigParser()

    cfg["default paths"] = {
        "routes": "",
        "collision": "",
        "gen": ""
    }

    cfg["routes editor"] = {
        "DefaultRadius": "50",
        "InvertZoom": "False",
        "GroundWaypointsWhenMoving": "False"
    }

    cfg["gen editor"] = {
        "InvertZoom": "False",
        "GroundObjectsWhenMoving": "False",
        "GroundObjectsWhenAdding": "True",
        "renderStartPos": "False",
        "wasdscrolling_speed": "200",
        "wasdscrolling_speedupfactor": "3"
    }
    cfg["model render"] = {
        "Width": "1000",
        "Height": "1000"
    }

    with open("piktool.ini", "w") as f:
        cfg.write(f)

    return cfg


def save_cfg(cfg):
    with open("piktool.ini", "w") as f:
        cfg.write(f)