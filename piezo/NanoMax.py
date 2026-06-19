from pycromanager import Core


class MDT693B_NanoMax():
    def __init__(self, core, dev_name="ThorlabsMDT"):
        self.dev_name = dev_name
        self.core = core
        
        # Mapping the MDT693B physical channels to clear spatial axes
        self.axes = {
            'X': "VoltageX", 
            'Y': "VoltageY",
            'Z': "VoltageZ"
        }

    def get_voltage(self, axis):
        axis = axis.upper()
        if axis in self.axes:
            return float(self.core.get_property(self.dev_name, self.axes[axis]))
        print(f"Error: Invalid axis '{axis}'. Choose X, Y, or Z.")
        return -1.0

    def set_voltage_safe(self, axis, voltage_val):
        axis = axis.upper()
        if axis in self.axes:
            voltage_val = float(voltage_val) 
            self.core.set_property(self.dev_name, self.axes[axis], str(voltage_val))
            
            self.core.wait_for_device(self.dev_name)
            
            if abs(voltage_val - self.get_voltage(axis)) > 1e-3:
                return -1  # Voltage mismatc
            return 0  # Success

        return -2  # Invalid axis

    def set_voltage(self, axis, voltage_val):
        axis = axis.upper()
        if axis in self.axes:
            voltage_val = float(voltage_val) 
            self.core.set_property(self.dev_name, self.axes[axis], str(voltage_val))
            return 0  # Success

        return -2  # Invalid axis


if __name__ == "__main__":
    core = Core()
    piezo = MDT693B_NanoMax(core, "ThorlabsMDT")
    

    print(f"Current X Voltage: {piezo.get_voltage('X')} V")
    print(f"Current Y Voltage: {piezo.get_voltage('Y')} V")
    print(f"Current Z Voltage: {piezo.get_voltage('Z')} V")
    
    
    status = piezo.set_voltage('Z', 25.5)
    if status == 0:
        print(f"Successfully shifted Z axis to: {piezo.get_voltage('Z')} V")
