from machine import Pin
from utime import sleep_ms


class Scale:
    """ A Class to represent SparkFun's HX711 Scale """

    @staticmethod
    def twosbinarystring_to_integer(value_string, bits):
        """ Given a binary string of a number in 2's complement, compute the integer value """
        value = int(value_string, 2)

        if value & (1 << (bits - 1)) != 0:
            value = value - (1 << bits)

        return value

    def __init__(self,
                 gain=1,
                 data_cycles=24,
                 clock_pin="G16",
                 data_pin="G15"):
        self.gain = gain
        self.data_cycles = data_cycles
        self.clock_pin = clock_pin
        self.data_pin = data_pin

        self.clk = Pin(self.clock_pin, mode=Pin.OUT)
        self.clk.mode(Pin.OUT)
        self.data = Pin(self.data_pin, mode=Pin.IN, pull=Pin.PULL_DOWN)
        self.data.mode(Pin.IN)

    def read(self):
        self.clk.value(0)

        wait_iterations = 0
        while wait_iterations < 100 and self.data.value() != 0:
            wait_iterations += 1
            sleep_ms(1)

        if wait_iterations >= 100:
            raise Exception("ADC Communication Failure")

        # Retrieve ADC Reading
        observation = []
        for i in range(self.data_cycles):
            self.clk.toggle()
            self.clk.toggle()

            observation.append(self.data.value())

        # Set ADC Gain for next reading
        for i in range(self.gain):
            self.clk.toggle()
            self.clk.toggle()

        ob_string = ''.join([str(i) for i in observation])
        ob_value = self.twosbinarystring_to_integer(ob_string, bits=self.data_cycles)

        return ob_value
