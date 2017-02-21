from machine import I2C, Pin
import time
import network
import json
import machine, neopixel



import usocket as socket
import ustruct as struct
from ubinascii import hexlify

class MQTTException(Exception):                                 #MQTT client class, copied code
    pass

class MQTTClient:

    def __init__(self, client_id, server, port=0, user=None, password=None, keepalive=0,
                 ssl=False, ssl_params={}):
        if port == 0:
            port = 8883 if ssl else 1883
        self.client_id = client_id
        self.sock = None
        self.addr = socket.getaddrinfo(server, port)[0][-1]
        self.ssl = ssl
        self.ssl_params = ssl_params
        self.pid = 0
        self.cb = None
        self.user = user
        self.pswd = password
        self.keepalive = keepalive
        self.lw_topic = None
        self.lw_msg = None
        self.lw_qos = 0
        self.lw_retain = False

    def _send_str(self, s):
        self.sock.write(struct.pack("!H", len(s)))
        self.sock.write(s)

    def _recv_len(self):
        n = 0
        sh = 0
        while 1:
            b = self.sock.read(1)[0]
            n |= (b & 0x7f) << sh
            if not b & 0x80:
                return n
            sh += 7

    def set_callback(self, f):
        self.cb = f

    def set_last_will(self, topic, msg, retain=False, qos=0):
        assert 0 <= qos <= 2
        assert topic
        self.lw_topic = topic
        self.lw_msg = msg
        self.lw_qos = qos
        self.lw_retain = retain

    def connect(self, clean_session=True):
        self.sock = socket.socket()
        self.sock.connect(self.addr)
        if self.ssl:
            import ussl
            self.sock = ussl.wrap_socket(self.sock, **self.ssl_params)
        msg = bytearray(b"\x10\0\0\x04MQTT\x04\x02\0\0")
        msg[1] = 10 + 2 + len(self.client_id)
        msg[9] = clean_session << 1
        if self.user is not None:
            msg[1] += 2 + len(self.user) + 2 + len(self.pswd)
            msg[9] |= 0xC0
        if self.keepalive:
            assert self.keepalive < 65536
            msg[10] |= self.keepalive >> 8
            msg[11] |= self.keepalive & 0x00FF
        if self.lw_topic:
            msg[1] += 2 + len(self.lw_topic) + 2 + len(self.lw_msg)
            msg[9] |= 0x4 | (self.lw_qos & 0x1) << 3 | (self.lw_qos & 0x2) << 3
            msg[9] |= self.lw_retain << 5
        self.sock.write(msg)
        #print(hex(len(msg)), hexlify(msg, ":"))
        self._send_str(self.client_id)
        if self.lw_topic:
            self._send_str(self.lw_topic)
            self._send_str(self.lw_msg)
        if self.user is not None:
            self._send_str(self.user)
            self._send_str(self.pswd)
        resp = self.sock.read(4)
        assert resp[0] == 0x20 and resp[1] == 0x02
        if resp[3] != 0:
            raise MQTTException(resp[3])
        return resp[2] & 1

    def disconnect(self):
        self.sock.write(b"\xe0\0")
        self.sock.close()

    def ping(self):
        self.sock.write(b"\xc0\0")

    def publish(self, topic, msg, retain=False, qos=0):
        pkt = bytearray(b"\x30\0\0\0")
        pkt[0] |= qos << 1 | retain
        sz = 2 + len(topic) + len(msg)
        if qos > 0:
            sz += 2
        assert sz < 2097152
        i = 1
        while sz > 0x7f:
            pkt[i] = (sz & 0x7f) | 0x80
            sz >>= 7
            i += 1
        pkt[i] = sz
        #print(hex(len(pkt)), hexlify(pkt, ":"))
        self.sock.write(pkt, i + 1)
        self._send_str(topic)
        if qos > 0:
            self.pid += 1
            pid = self.pid
            struct.pack_into("!H", pkt, 0, pid)
            self.sock.write(pkt, 2)
        self.sock.write(msg)
        if qos == 1:
            while 1:
                op = self.wait_msg()
                if op == 0x40:
                    sz = self.sock.read(1)
                    assert sz == b"\x02"
                    rcv_pid = self.sock.read(2)
                    rcv_pid = rcv_pid[0] << 8 | rcv_pid[1]
                    if pid == rcv_pid:
                        return
        elif qos == 2:
            assert 0

    def subscribe(self, topic, qos=0):
        assert self.cb is not None, "Subscribe callback is not set"
        pkt = bytearray(b"\x82\0\0\0")
        self.pid += 1
        struct.pack_into("!BH", pkt, 1, 2 + 2 + len(topic) + 1, self.pid)
        self.sock.write(pkt)
        self._send_str(topic)
        self.sock.write(qos.to_bytes(1, "little"))
        while 1:
            op = self.wait_msg()
            if op == 0x90:
                resp = self.sock.read(4)
                #print(resp)
                assert resp[1] == pkt[2] and resp[2] == pkt[3]
                if resp[3] == 0x80:
                    raise MQTTException(resp[3])
                return

    def wait_msg(self):
        res = self.sock.read(1)
        self.sock.setblocking(True)
        if res is None:
            return None
        if res == b"":
            raise OSError(-1)
        if res == b"\xd0":  # PINGRESP
            sz = self.sock.read(1)[0]
            assert sz == 0
            return None
        op = res[0]
        if op & 0xf0 != 0x30:
            return op
        sz = self._recv_len()
        topic_len = self.sock.read(2)
        topic_len = (topic_len[0] << 8) | topic_len[1]
        topic = self.sock.read(topic_len)
        sz -= topic_len + 2
        if op & 6:
            pid = self.sock.read(2)
            pid = pid[0] << 8 | pid[1]
            sz -= 2
        msg = self.sock.read(sz)
        self.cb(topic, msg)
        if op & 6 == 2:
            pkt = bytearray(b"\x40\x02\0\0")
            struct.pack_into("!H", pkt, 2, pid)
            self.sock.write(pkt)
        elif op & 6 == 4:
            assert 0

    def check_msg(self):
        self.sock.setblocking(True)
        return self.wait_msg()

consumption = 0


#Simple clamp function to clamp values to the desired range
def clamp(n, minn, maxn):               
    return max(min(maxn, n), minn)


#Adds parsed value from the server to the individual colour components
#Makes sure to not overflow any of the components, checks for addition to 255(max value)
#and substraction from 0 (min values)
#Also calculates the current consumption, based on the fact that each LED takes 18mA
#at full brightness of 255 and assuming linear current consumption decrease at lower values

def smooth_change(r,g,b):               
    new_red = np[0][0]
    new_green = np[0][1]
    new_blue = np[0][2]

    if not((np[0][0] == 0 and r == -1) or (np[0][0] == 255 and r == 1)):    
        new_red = clamp(np[0][0] + r,0,255)

    if not((np[0][1] == 0 and g == -1) or (np[0][1] == 255 and g == 1)):
        new_green = clamp(np[0][1] + g,0,255)

    if not((np[0][2] == 0 and b == -1) or (np[0][2] == 255 and b == 1)):
        new_blue = clamp(np[0][2] + b,0,255)


    global consumption 
    consumption = float(float(new_red+new_green+new_blue)/float(256*3) * 18 * 24 * 5) #Power consumption in mW
    for i in range(24):
        np[i] = (new_red,new_green,new_blue)
    print ("Current values: " + str(new_red) + " " + str(new_green) + " " + str(new_blue))
    np.write()


#Callback function, called every time message on the subscribed topic is received
#Parses the json and calls smooth_change function to set the colour change
#Alternatively eneters polling loop where it momentarily disconnects from MQTT 
def printData(topic,msg):
    outp = str(msg)
    print (outp[2:-1])
    data = json.loads(outp[2:-1])
    if (data['Red'] == 0 and data['Green'] == 0 and data['Blue'] == 0):
        mqttc.disconnect()
        time.sleep(0.75)
        mqttc.connect()
        mqttc.set_callback(printData)
        mqttc.subscribe('esys/VESKembedded/test',1)
    else:
        smooth_change(data['Red'],data['Green'],data['Blue'])
    #print(topic + " " + msg)


#Define LED object as well as I2C comms channel

i2C = I2C(scl=Pin(5), sda=Pin(4))
np = neopixel.NeoPixel(machine.Pin(12), 24)

print('Connecting to TCS34725...')
i2C.writeto(41, b'\xb2') #Access ID register
deviceID = i2C.readfrom(41, 1) 
if deviceID == b'D':
    print ('Success!')
else:
    print('TCS34725 not responding')

i2C.writeto(41, b'\xa0') #Access enable register
i2C.writeto(41, b'\x03') #Write 0x03 to enter the ADC cycle

i2C.writeto(41, b'\xaf') #Access gain register
i2C.writeto(41, b'\x00') #Write 0x02 to set gain x1

i2C.writeto(41, b'\xa1') #Access RGBC timing register
i2C.writeto(41, b'\xd5') #Set integration time to 101 ms

#For reading 2-byte register values by applying a 1-byte offset to the more significant byte
def decode(inString):
    return (inString[0]) + 256*inString[1]

waitTime = 0.01	


#Create JSON formatted string to be sent via MQTT
def create_json(c,r,g,b,cons):

    json1 = json.dumps({'Clear': c, 'Red': r, 'Green': g, 'Blue': b, 'Consumption': cons}) #consumption is in mA
    return json1

#Connect to the WLAN network
ap_if = network.WLAN(network.AP_IF)
ap_if.active(False)
sta_if = network.WLAN(network.STA_IF)
sta_if.active(True)
sta_if.connect('EEERover','exhibition')
#sta_if.connect('pavii-HP-630-Notebook-PC','af820fa3bd')

#Wait until connected
while (sta_if.isconnected() == False):
    time.sleep(0.1)
print (sta_if.isconnected())

#We have set up our own MQTT broker that used name and password for added security
mqttc = MQTTClient('1',server = '192.168.0.129')
mqttc.user = "ESPrgb"
mqttc.pswd = "secretPASSWORD123"


mqttc.keepalive = 60

#connect and set subscription
mqttc.connect()
mqttc.set_callback(printData)
mqttc.subscribe('esys/VESKembedded/test',1)

while(True):
    
    

    i2C.writeto(41, b'\xb4') #Access clear channel register
    clear = decode(i2C.readfrom(41, 2)) #Read 2 bytes from clear channel register
    #time.sleep(waitTime)
    i2C.writeto(41, b'\xb6') #Access red channel register
    red = decode(i2C.readfrom(41, 2)) #Read 2 bytes from red channel register
    #time.sleep(waitTime)
    i2C.writeto(41, b'\xb8') #Access green channel register
    green = decode(i2C.readfrom(41, 2)) #Read 2 bytes from green channel register
    #time.sleep(waitTime)
    i2C.writeto(41, b'\xbA') #Access blue channel register
    blue = decode(i2C.readfrom(41, 2)) #Read 2 bytes from blue channel register
    #time.sleep(waitTime)
    #print (str(create_json(clear,red,green,blue)))
    
    #Publish sensor readings as JSON formatted string
    mqttc.publish('esys/VESKembedded/publish', str(create_json(clear,red,green,blue,consumption)), qos=1)

    mqttc.check_msg()

    
    #time.sleep(1.5)
    #print ("Clear, Red, Green, Blue:", clear, red, green, blue)
    #print (type(clear), type(clear[0]), type(clear[1]))
