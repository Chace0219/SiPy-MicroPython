import time
import machine
from machine import Pin
from machine import ADC

from network import Sigfox
import socket

#
#val = BattVol()                    # read an analog value

'''
    You can type here.
    
'''
def GetBattVolt():

    adc = ADC(0)
    BattVol = adc.channel(pin='P15',  attn=3)   # create an analog pin on P16
 
    realVoltage = 0

    # Average Count
    ADCCnt = 75
    for  idx in range(ADCCnt):
        realVoltage += BattVol.value()
        print(BattVol())
        time.sleep_ms(50)

    realVoltage = realVoltage / ADCCnt
    realVoltage = (realVoltage * 200) / 100
    realVoltage = realVoltage * 4.25 # Linear scaling (was 3.35)
    realVoltage = realVoltage / 4096
    
    print("Real Voltage is " + str(realVoltage))
    
    Level = 0
    
    if(realVoltage >= 3.8):
        Level = 6
    elif(realVoltage >= 3.7 and realVoltage < 3.8):
        Level = 5
    elif(realVoltage >= 3.6 and realVoltage < 3.7):
        Level = 4
    elif(realVoltage >= 3.5 and realVoltage < 3.6):
        Level = 3
    elif(realVoltage >= 3.4 and realVoltage < 3.5):
        Level = 2
    elif(realVoltage >= 3.0 and realVoltage < 3.4):
        Level = 1
    
    return Level,  realVoltage

def SendLevelSigfox(level):
    '''
    data = b""  			#string
    data = Msg.encode()	#bytes
    #data = b"" 			#bytes
    print(Msg)
    print(len(data))
    '''
    
    # Battery Level  
    BatteryLV,  RealVolt = GetBattVolt()
    
    BatteryLV = BatteryLV << 4
    RealVolt = int(RealVolt * 100) # Multiply 100 
    
    RVLow = RealVolt & 0xFF
    RVHigh = (RealVolt >> 8) & 0xFF
     
     # init Sigfox for RCZ4  
    sigfox = Sigfox(mode=Sigfox.SIGFOX, rcz=Sigfox.RCZ4) 

    # create a Sigfox socket 
    s = socket.socket(socket.AF_SIGFOX, socket.SOCK_RAW)

    # make the socket blocking 
    s.setblocking(True) 

    # configure it as uplink only 
    s.setsockopt(socket.SOL_SIGFOX, socket.SO_RX, False) 
    lowbyte = level & 0xFF
    highbyte = (level >> 8) & 0xFF
    
    
    # send some bytes 
    s.send(bytes([BatteryLV, 0x00,  0x00,  highbyte, lowbyte,  RVHigh,  RVLow,  0x00,  0x00,  0x00,  0x00,  0x00])) # 12 bytes payload
    s.close()

# Trigger Pin class
TRGPIN = Pin('P9',mode=Pin.OUT)
TRGPIN.value(0)

# ECHO Pin Class
EchoPin = Pin('P10',mode=Pin.IN,pull=Pin.PULL_UP)

#  SensorPower
SensorPower = Pin('P11',mode=Pin.OUT)
SensorPower.value(1)

AverValue = 0.0

def GetAndAverageLevel():
    print("Sensing Proc is started!")
    
    # Count  Variable
    nCnt = 0
    global AverValue
    AverValue = 0.0
    ErrCount = 0
    
    #define count of averaging
    AverCnt = 20
    
    while True:
        #
        ## TRIG LOW for 4us
        TRGPIN.value(0)    
        time.sleep_us(4)
        
        # Trigger Pin High 10 us
        TRGPIN.value(1)
        time.sleep_us(10)
        
        # LOW  Signal in trig pin
        TRGPIN.value(0)
        
        # Get current micro sec
        last_ustime = time.ticks_us()
        
        # delay 450micro secs ( most of ultra sensor  needs 450us delay )
        time.sleep_us(450)
        
        ErrCount = 0
        
        # wait until Echopin is low 
        while EchoPin() == 1:
            # 38ms is maximum waiting time
            if(last_ustime + 38000 < time.ticks_us()):
                break
        duration = time.ticks_us() - last_ustime
        if(duration >= 38000):
            print("No Echo signal")
            ErrCount += 1 # Error proc
            if(ErrCount > 5):
                print("You have to check wiring or sensor!")
                return False
        else:
            distance = duration / 58.2 - 2.0
            print("Current Distance is " + str(distance) + ", count index = " + str(nCnt))
            nCnt += 1
            AverValue += distance
            if(nCnt >= AverCnt):
                AverValue /= AverCnt
                return True
            time.sleep_ms(400)
                

# sleep interval , you can change it as 15 minutes, now it is 8000ms
SLEEPTIME = 850000 #  ~ 15 minutes allow for process
# main loop
print("Starting main loop")
while True:
    msg =""
    
    SensorPower.value(1)
    time.sleep(1) # 
    if(GetAndAverageLevel() ==True):
        msg = "Current tank level is " + str(int(AverValue))
        msg += "cm."
    else:
        msg = "I have found no echo signal!, You have to check wiring or sensor!"
    print(msg)
    SensorPower.value(0)
 
    print("I will send information to server!")
    msg = hex(int(AverValue))
    
    SendLevelSigfox(int(AverValue))
    
    ##
    print("I will enter sleep status")
    
    
    # You can enable or disable sleep mode with this part.
    # this part is temporalily
    
    ''''' 
    sleepcnt = 0
    while sleepcnt < SLEEPTIME / 1000:
        sleepcnt += 1
        time.sleep_ms(500)
     '''
    
    # deep sleep 
    machine.deepsleep(SLEEPTIME)
    
print("Exited main loop")
