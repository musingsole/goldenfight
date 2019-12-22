from time import sleep
import RPi.GPIO as GPIO


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
                 clock_pin=11,
                 data_pin=12):
        self.gain = gain
        self.data_cycles = data_cycles
        self.clock_pin = clock_pin
        self.data_pin = data_pin

        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(clock_pin, GPIO.OUT)
        GPIO.setup(data_pin, GPIO.IN)
        GPIO.output(clock_pin, GPIO.LOW)

    def read_data(self):
        return GPIO.input(self.data_pin)

    def clock(self):
        GPIO.output(self.clock_pin, GPIO.HIGH)
        GPIO.output(self.clock_pin, GPIO.LOW)

    def read(self):
        GPIO.output(self.clock_pin, GPIO.LOW)
        wait_iterations = 0
        while wait_iterations < 100 and self.read_data() != 0:
            wait_iterations += 1
            sleep(0.001)

        if wait_iterations >= 100:
            raise Exception("ADC Communication Failure")

        # Retrieve ADC Reading
        observation = []
        for i in range(self.data_cycles):
            self.clock()
            observation.append(self.read_data())

        # Set ADC Gain for next reading
        for i in range(self.gain):
            self.clock()

        ob_string = ''.join([str(i) for i in observation])
        ob_value = self.twosbinarystring_to_integer(ob_string, bits=self.data_cycles)

        return ob_value
