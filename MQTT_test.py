import paho.mqtt.client as paho
import os, urlparse
import time
import json
import os
import subprocess



# Define event callbacks
def on_connect(mosq, obj, rc):
    print("rc: " + str(rc))

def on_message(mosq, obj, msg):
    global start_time
    
    messageTime = time.time() - start_time
    start_time = time.time()       

    print(msg.topic + " " + str(msg.qos) + " " + str(msg.payload))
    

    #parsed_json['Red'] =  min(parsed_json['Red'],255) 
    #parsed_json['Blue'] =  min(parsed_json['Blue'],255)
    #parsed_json['Green'] = min(parsed_json['Green'],255)
    
    global ideal_r
    global ideal_g
    global ideal_b
    global totalEnergy
    global disco

    if "publish" in (msg.topic): 
        parsed_json = json.loads(msg.payload)
        
        
        if disco:
            parsed_json['Red'] = 300
            parsed_json['Green'] = 300
            parsed_json['Blue'] = 300 
        else:
            message = balanceColour(ideal_r,ideal_g,ideal_b,parsed_json['Red'], parsed_json['Green'],parsed_json['Blue']) 
            
        mqttc.publish("esys/VESKembedded/test", str(message),0)        
        print "pubish: succesful"
        

        #power calculation
        totalEnergy += messageTime*(800-parsed_json['Consumption'])/1000
        print ("current power: {}mW; \n total savings: {}J").format(str(parsed_json['Consumption']), totalEnergy)

 
    elif  'settings' in msg.topic:
        if 'warm' in str(msg.payload): 
            ideal_r = 160
            ideal_g = 115
            ideal_b = 84
        elif 'neutral' in str(msg.payload):
            global proc            
            proc.kill() 
            ideal_r = 190 #140
            ideal_g = 190 #140
            ideal_b =  190   #150
            disco = False
        elif 'cold' in str(msg.payload): 
            ideal_r = 118
            ideal_g = 132
            ideal_b = 160
        elif 'disco' in str(msg.payload):
            global proc
            proc = subprocess.Popen(['mplayer', 'Oliver_Cheatham_Get_Down_Saturday_Night.mp3'])
            ideal_r = 150
            ideal_g = 10
            ideal_b = 10
            disco = True
        print "settings: succesful"
    
    

  

def on_publish(mosq, obj, mid):
    print("mid: " + str(mid))

def on_subscribe(mosq, obj, mid, granted_qos):
    print("Subscribed: " + str(mid) + " " + str(granted_qos))

def on_log(mosq, obj, level, string):
    print(string)

def serverProcessing(mosq,obj,msg):
    #message = json.loads(msg.payload)
    print(str(msg.payload))

def balanceColour(ideal_r,ideal_g,ideal_b,r,g,b):
    #ideal_r = 120
    #ideal_g = 150
    #ideal_b = 180
    
    threshold = 3
    
    if (ideal_r-r) > threshold:
        balanceValue_r = max((ideal_r-r)/10, 1)
    elif abs(ideal_r-r) <= threshold:
        balanceValue_r = 0
    else:
        balanceValue_r = min((ideal_r-r)/10, -1)
    if (ideal_g-g) > threshold:
        balanceValue_g = max((ideal_g-g)/10, 1)
    elif abs(ideal_g-g) <= threshold:
        balanceValue_g = 0
    else:
        balanceValue_g = min((ideal_g-g)/10, -1)
    if (ideal_b-b) > threshold:
        balanceValue_b = max((ideal_b-b)/10, 1)
    elif abs(ideal_b-b) <= threshold:
        balanceValue_b = 0
    else:
        balanceValue_b = min((ideal_b-b)/10, -1)
      
    output_dic = json.dumps({ 'Red': balanceValue_r, 'Green': balanceValue_g, 'Blue': balanceValue_b })
    return output_dic

mqttc = paho.Client()
# Assign event callbacks
mqttc.on_message = on_message
mqttc.on_connect = on_connect
mqttc.on_publish = on_publish
mqttc.on_subscribe = on_subscribe



# Uncomment to enable debug messages
#mqttc.on_log = on_log

# Connect
mqttc.username_pw_set('dataPROC',password = 'unkownPASSWORD123')
#mqttc.connect('m20.cloudmqtt.com',18428,60)
mqttc.connect('192.168.0.119')

# Start subscribe, with QoS level 1
mqttc.subscribe("esys/VESKembedded/publish",1)
mqttc.subscribe("esys/VESKembedded/settings",1)
#mqttc.message_callback_add("esys/VESKembedded/publish",serverProcessing)

# Publish a message
#mqttc.loop_forever()

#mqttc.publish("esys/VESKembedded/test", "It's working!!!",0)

ideal_r = 140
ideal_g = 140
ideal_b = 150

totalEnergy = 0
disco = False

start_time = time.time()

mqttc.loop_forever()


#check = True
while True:
    #mqttc.loop_forever()
    mqttc.loop_read()   
#    mqttc.connect('192.168.0.10')
#    mqttc.subscribe("esys/VESKembedded/publish",1)
#    check
#    mqttc.publish("esys/VESKembedded/test", "It's working!!!",0)
#    mqttc.loop_start()
