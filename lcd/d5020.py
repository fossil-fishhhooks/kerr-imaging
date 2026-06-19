from pycromanager import Core
core = Core()


class d5020():
    def __init__(dev_name):
        self.dev_name = dev_name



if __name__ == "__main__":
    print(core) # debugging
    strv = core.get_loaded_devices()
    print(strv)
    for i in range(strv.size()):
        print(strv.get(i))
