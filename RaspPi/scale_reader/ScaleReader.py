from ScaleInterface import Scale
from time import sleep


class ScaleReader:
    def __init__(self):
        self.scale = Scale()
        self.tare_value = 0
        self.calibration_factor = 1

    def read_raw(self, samples=10):
        readings = []
        for i in range(samples):
            readings.append(self.scale.read())
            sleep(0.01)
        median = sorted(readings)[int(samples / 2)]
        return median
    
    def tare(self):
        self.tare_value = self.read_raw() 

    def calibrate(self, weight=5, samples=10):
        self.calibration_factor = (self.read_raw(samples) - self.tare_value) / weight

    def read(self, samples=10):
        return (self.read_raw(samples) - self.tare_value) / self.calibration_factor

