from time import sleep_ms
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
                 clock_pin=8,
                 data_pin=10):
        self.gain = gain
        self.data_cycles = data_cycles
        self.clock_pin = clock_pin
        self.data_pin = data_pin

        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(clock_pin, GPIO.OUT)
        GPIO.setup(data_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        GPIO.output(clock_pin, GPIO.LOW)

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
            GPIO.output(self.clock_pin, GPIO.HIGH)
            GPIO.output(self.clock_pin, GPIO.LOW)

            observation.append(GPIO.input(self.data_pin))

        # Set ADC Gain for next reading
        for i in range(self.gain):
            GPIO.output(self.clock_pin, GPIO.HIGH)
            GPIO.output(self.clock_pin, GPIO.LOW)

        ob_string = ''.join([str(i) for i in observation])
        ob_value = self.twosbinarystring_to_integer(ob_string, bits=self.data_cycles)

        return ob_value
