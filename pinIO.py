from wiringx86 import GPIOEdison as GPIO
import random
import time

gpio = GPIO(debug=False)
gpio1 =GPIO(debug=False)
# Set up an LED on pin 6
# Prepare pins and loop

gpio.pinMode(9, gpio.PWM)
gpio1.pinMode(6, gpio1.PWM)

try:
    while(True):
        # Write a state to the pin. ON or OFF.
        val = random.randint(0,255)
        val1 = random.randint(0,255)
        print (val, val1)
        gpio.analogWrite(9,val)
        gpio1.analogWrite(6,val1)

        # Sleep for a while.
        time.sleep(1)

# When you get tired of seeing the led blinking kill the loop with Ctrl-C.
except KeyboardInterrupt:
    # Leave the led turned off.
    print '\nCleaning up...'
    gpio.pinMode(9, gpio.OUTPUT)
	gpio1.pinMode(6, gpio1.OUTPUT)
    gpio.digitalWrite(9, gpio.LOW)
    gpio1.digitalWrite(6, gpio1.LOW)

    # Do a general cleanup. Calling this function is not mandatory.
    gpio.cleanup()
    gpio1.cleanup()
