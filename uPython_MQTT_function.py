#import pyb
import simple

mqttc = simple.MQTTClient('1',server = 'm20.cloudmqtt.com', port = 18428)

mqttc.user = "ccdmmpze"
mqttc.pswd = "4dE8WJGSbqja"
mqttc.keepalive = 60


#connect
mqttc.connect()

#publish with qos 1

mqttc.publish('hello/world','hi')

#disconnect
mqttc.disconnect


