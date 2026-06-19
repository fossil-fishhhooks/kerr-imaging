from pycromanager import Core
core = Core()


class d5020():
    def __init__(self, dev_name="verycooldefaultnametobereplacedlater"):
        self.dev_name = dev_name
        self.r0 = float(core.get_property(self.dev_name, "Retardance_0"))
        self.r1 = float(core.get_property(self.dev_name, "Retardance_1"))
    
    def get_retardance(self, port):
        if port==0:
            return float(core.get_property(self.dev_name, "Retardance_0")) #defensively convert mmc types
        if port==1:
            return float(core.get_property(self.dev_name, "Retardance_1"))

        return -3
    
    def set_retardance_safe(self, port, value):
        if port == 0:
            core.set_property(self.dev_name, "Retardance_0", value)
            core.wait_for_device(self.dev_name) 
            if abs(value - self.get_retardance(0)) > 1e-5:
                return -1
            else:
                return 0
        if port == 1:
            core.set_property(self.dev_name, "Retardance_1", value)
            core.wait_for_device(self.dev_name) 
            if abs(value - self.get_retardance(1)) > 1e-5:
                return -1
            else:
                return 0
        return -2

    def set_retardance(self, port, value):
        if port == 0:
            core.set_property(self.dev_name, "Retardance_0", value)
        if port == 1:
            core.set_property(self.dev_name, "Retardance_1", value)
        return




if __name__ == "__main__":
    print(core) # debugging
    strv = core.get_loaded_devices()
    print(strv)
    for i in range(strv.size()):
        print(strv.get(i))
