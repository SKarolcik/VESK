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
        
    
    #uncomment for debugging
    #print(msg.topic + " " + str(msg.qos) + " " + str(msg.payload))
    
    
    global ideal_r
    global ideal_g
    global ideal_b
    global totalEnergy
    global disco
    

    #when message was received from public topic do the following processing
    if "publish" in (msg.topic): 
        parsed_json = json.loads(msg.payload)
        message = balanceColour(ideal_r,ideal_g,ideal_b,parsed_json['Red'], parsed_json['Green'],parsed_json['Blue'])        
        mqttc.publish("esys/VESKembedded/test", str(message),0)        
        print "pubish: succesful"
        
        #power calculation

        #get round trip time 
        global start_time
        messageTime = time.time() - start_time
        start_time = time.time()           
        
        #For each time step, the energy saved is calculated by multiplying the difference between baseline power and actual power with the  round trip time
        totalEnergy += messageTime*(800-parsed_json['Consumption'])/1000
        print ("current power: {}mW; \n total savings: {}J").format(str(parsed_json['Consumption']), totalEnergy)   



    #if message was received in settings topic
    
    elif  'settings' in msg.topic:
        #set colour mode to warm
        if 'warm' in str(msg.payload): 
            ideal_r = 190
            ideal_g = 136
            ideal_b = 100
        
        #set colour mode to neutral/white    
        elif 'neutral' in str(msg.payload):            
            ideal_r = 180 
            ideal_g = 180 
            ideal_b =  190 
            #if disco is enabled disable it            
            if disco:
                global proc            
                proc.kill()            
                disco = False
        
        #set  colour mode to cold
        elif 'cold' in str(msg.payload): 
            ideal_r = 140
            ideal_g = 156
            ideal_b = 190
        
        #start disco mode
        elif 'disco' in str(msg.payload):
            #play the music 
            #global proc
            proc = subprocess.Popen(['mplayer', 'Oliver_Cheatham_Get_Down_Saturday_Night.mp3'])
            disco = True
        print "settings: succesful"
    
    

def balanceColour(ideal_r,ideal_g,ideal_b,r,g,b):
    
    global disco
    global disco_red
    global disco_blue
    
    #if disco is enabled it will set the balanceValue so it can blink
    if disco:
        
        #change lights by multiplying by one
        disco_red *= -1
        disco_blue *= -1
        
        #map the lights to balanced values 
        if disco_red == 1:
            balanceValue_r = 250
        else:
            balanceValue_r = -250

        if disco_blue == 1:
            balanceValue_b = 30
        else:
            balanceValue_b = -30
        
        #synchronise with the beat
        time.sleep(0.35)
    
    else:
        
        #threshold value for settling the colour balancing
        threshold = 3
         
        #RED           
        #check with threshol if it is neccesary to balance the colour
        if (ideal_r-r) > threshold:
            #balance the colour faster if the transition is bigger
            balanceValue_r = max((ideal_r-r)/10, 1)
        elif abs(ideal_r-r) <= threshold:
            #if within threshold don balance the colour anymore
            balanceValue_r = 0
        else:
            #balance the colour for negative values
            balanceValue_r = min((ideal_r-r)/10, -1)
        
        #GREEN    
        if (ideal_g-g) > threshold:
            balanceValue_g = max((ideal_g-g)/10, 1)
        elif abs(ideal_g-g) <= threshold:
            balanceValue_g = 0
        else:
            balanceValue_g = min((ideal_g-g)/10, -1)
        
        #BLUE
        if (ideal_b-b) > threshold:
            balanceValue_b = max((ideal_b-b)/10, 1)
        elif abs(ideal_b-b) <= threshold:
            balanceValue_b = 0
        else:
            balanceValue_b = min((ideal_b-b)/10, -1)
    


    
    #output the balance values  
    output_dic = json.dumps({ 'Red': balanceValue_r, 'Green': balanceValue_g, 'Blue': balanceValue_b })
    return output_dic

#callback function for debugging
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


# Uncomment to enable debug messages
#mqttc.on_log = on_log

# Connect
#the userdaname and password are assigned in the server configuration
mqttc.username_pw_set('dataPROC',password = 'unkownPASSWORD123')
#this is the IP address of our own broker, this needs to be changed according to IP address obtained
mqttc.connect('192.168.0.129')

# Start subscribe, with QoS level 1
mqttc.subscribe("esys/VESKembedded/publish",1) #this topic is for recieving the publish from the sensor
mqttc.subscribe("esys/VESKembedded/settings",1) #this topic is to set the mode: neutral, cold, warm, disco

#initial ligting conditions
ideal_r = 180
ideal_g = 180
ideal_b = 190

#initializing the energy calculation
totalEnergy = 0

#initial parameters for disco mode
disco = False
disco_red = 1
disco_green = 0
disco_blue = -1
constant = 10

start_time = time.time()

#loop forever to get messages
mqttc.loop_forever()


