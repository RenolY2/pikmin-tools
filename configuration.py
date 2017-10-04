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
        "collision": ""
    }

    cfg["routes editor"] = {
        "DefaultRadius": "50",
        "InvertZoom": "False",
        "GroundWaypointsWhenMoving": "False"
    }

    with open("piktool.ini", "w") as f:
        cfg.write(f)

    return cfg

def save_cfg(cfg):
    with open("piktool.ini", "w") as f:
        cfg.write(f)