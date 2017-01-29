from wiringx86 import GPIOEdison as GPIO
gpio = GPIO(debug=False)
gpio1 =GPIO(debug=False)
# Set up an LED on pin 6
gpio.pinMode(10, gpio.OUTPUT)
gpio.digitalWrite(10, gpio.HIGH)

gpio1.pinMode(11, gpio1.OUTPUT)
gpio1.digitalWrite(11, gpio1.HIGH)