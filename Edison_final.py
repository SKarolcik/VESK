from wiringx86 import GPIOEdison as GPIO
import paho.mqtt.client as paho
import time

gpio = GPIO(debug=False)
gpio1 =GPIO(debug=False)
# Set up an LED on pin 6
# Prepare pins and loop


# Define event callbacks
def process_input (numbers):
	lis_num = [x.strip() for x in numbers.split(',')]
	val1 = int((int(lis_num[1])/10000)*255)
	val2 = int((int(lis_num[2])/10000)*255)
	print (val1, val2)
	gpio.analogWrite(9,val2)
    gpio1.analogWrite(6,val1)


def on_connect(mosq, obj, rc):
    print("rc: " + str(rc))

def on_message(mosq, obj, msg):
    print(msg.topic + " " + str(msg.qos) + " " + str(msg.payload))
    process_input(str(msg.payload))

def on_publish(mosq, obj, mid):
    print("mid: " + str(mid))

def on_subscribe(mosq, obj, mid, granted_qos):
    print("Subscribed: " + str(mid) + " " + str(granted_qos))

def on_log(mosq, obj, level, string):
    print(string)

mqttc = paho.Client()
# Assign event callbacks
mqttc.on_message = on_message
mqttc.on_connect = on_connect
mqttc.on_publish = on_publish
mqttc.on_subscribe = on_subscribe

gpio.pinMode(9, gpio.PWM)
gpio1.pinMode(6, gpio1.PWM)
# Uncomment to enable debug messages
#mqttc.on_log = on_log

# Connect
mqttc.username_pw_set('ccdmmpze',password = '4dE8WJGSbqja')
mqttc.connect('m20.cloudmqtt.com',18428,2)
# Start subscribe, with QoS level 0

gpio.pinMode(9, gpio.PWM)
gpio1.pinMode(6, gpio1.PWM)

try:
    while(True):
        mqttc.loop_start()
        mqttc.subscribe("sensor/rgb", 1)
#time.sleep(120)

except KeyboardInterrupt:
    # Leave the led turned off.
    print '\nCleaning up...'
    mqttc.disconnect()
    mqttc.loop_stop()
    gpio.pinMode(9, gpio.OUTPUT)
    gpio1.pinMode(6, gpio1.OUTPUT)
    gpio.digitalWrite(9, gpio.LOW)
    gpio1.digitalWrite(6, gpio1.LOW)

    # Do a general cleanup. Calling this function is not mandatory.
    gpio.cleanup()
    gpio1.cleanup()

# Publish a message


