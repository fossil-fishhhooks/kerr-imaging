from pycromanager import Core
core = Core()


class d5020():
    def __init__(dev_name):
        self.dev_name = dev_name



if __name__ == "__main__":
    print(core) # debugging
    loaded_devices = mmc.get_loaded_devices()

    # Print all device names to find your Meadowlark controller
    for device in loaded_devices:
        print(device)