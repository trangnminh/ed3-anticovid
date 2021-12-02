#!/usr/bin/env python3

# libarry for grove sensor
import threading                                                            # threading library
import time
from datetime import datetime
from seeed_dht import DHT                                                   # Temperature and humidity sensor library
from grove.display.jhd1802 import JHD1802
from mraa import getGpioLookup
from grove.grove_mini_pir_motion_sensor import GroveMiniPIRMotionSensor     # Motion sensor library
from grove.grove_moisture_sensor import GroveMoistureSensor                 # Moisture sensor library
from grove.gpio import GPIO
import sys
from grove.button import Button
from grove.grove_ryb_led_button import GroveLedButton                       # LED button library
from grove.grove_relay import GroveRelay                                    # Relay library
from grove.grove_ultrasonic_ranger import GroveUltrasonicRanger             # Ultrasonic sensor library
# Opencv QR import libarry
import cv2                                                                  # OpenCV
import numpy as np
from pyzbar.pyzbar import decode                                            # QR scan
from gtts import gTTS
import os
#import libaary for local host
import requests
import socketio
import base64

# Socket io 
sio = socketio.Client()
@sio.event
def connect():
    print("I'm connected!")
@sio.event
def connect_error():
    print("The connection failed!")
@sio.event
def disconnect():
    print('disconnected from server')
sio.connect('http://192.168.50.46:4000/')                                   # Connect through Pi IP port 4000


# Funtion for PWM of relay used for buzzer
class GroveRelay(GPIO):
    def __init__(self, pin):
        super(GroveRelay, self).__init__(pin, GPIO.OUT)
 
    def on(self):
        self.write(1)
 
    def off(self):
        self.write(0)

# Grove - Temperature&Humidity Sensor connected to port D5
motionSensor = GroveMiniPIRMotionSensor(5) 
# Grove - Moisture Sensor connected to port A0
moisture_sensor = GroveMoistureSensor(0)
# Grove - 16x2 LCD(White on Blue) connected to I2C port
lcd = JHD1802()
# Grove - Temperature&Humidity Sensor connected to port D22
temp_sensor = DHT('11', 22)
# Grove - LED Button connected to port D16
button = GroveLedButton(16)
# Grove - Buzzer connect to PWM port 12
buzzer = GroveRelay(12)
# Grove - Ultrasonic Ranger connected to port D18
distance = GroveUltrasonicRanger(18)

# initialize value
pTime = 0                                                                   # varialbe for fps display
entering = 0                                                                # variable for counting enter the room
exiting = 0                                                                 # variable for counting exit the room
total = 0                                                                   # variable for total people in room
count_QR = 0                                                                # variable for counting time to scan QR
humi = 0                                                                    # variable for room condition
temp = 0
mois = 0
fps = 0
distant_count = 0
system_state = 0
current_state = 0
button.led.light(False)
myData = None

# Constant variable
TIME_QR = 200                                                              # Limit time for scaning QR
DISTANCE = 50                                                              # limit distance for ultrasonic measure
TIME_MOTION = 20                                                           # Limit time for motion

language ="en"  
dataFile_path = r"/home/pi/Documents/Hardware/grove.py/myDataFile.txt"     # storing data check in
with open(dataFile_path, "r") as f:                                        # Open and read file
    myDataList = f.read().splitlines()                                     # Create the info array

# Function for checking people in list:
def check_in_list(name):
    file_path = r"/home/pi/Documents/Hardware/grove.py/check_in_list.txt"  # people are allowed
    with open(file_path, "a") as f:                                        # Open and read file
        f.write(name+"\n")

# Funtion for buzzer, buzzing 2 times
def buzzer_on():
    buzzer.on()
    time.sleep(0.3)
    buzzer.off()
    time.sleep(0.5)
    buzzer.on()
    time.sleep(0.3)
    buzzer.off()

# Function for buzzer room full reject QR, buzzer 3 times
def buzzer_reject():
    buzzer.on()
    time.sleep(0.3)
    buzzer.off()
    time.sleep(0.2)
    buzzer.on()
    time.sleep(0.3)
    buzzer.off()
    time.sleep(0.2)
    buzzer.on()
    time.sleep(0.3)
    buzzer.off()

# Funtion for buzzer indicating timeout, buzzer 1 time
def buzzer_timeout():
    buzzer.on()
    time.sleep(1)
    buzzer.off()
    
# Funtion for reading temperature and humidity
def roomCondition():
    global humi
    global temp
    global mois  
    humi, temp = temp_sensor.read()                                        # read temperture and humidity data from sensor
    mois = moisture_sensor.moisture
    return humi, temp, mois

# Funtion for blinking led in invalid scan
def led_blink():
    button.led.light(True)
    time.sleep(0.5)
    button.led.light(False)
    time.sleep(0.5)
    button.led.light(True)
    time.sleep(0.5)
    button.led.light(False)

# Funtion for getting room condition
def LCD_roomCondition():
    global system_state                                                    # In/Out checking state
    global humi
    global temp
    global mois
    global current_state
    global total
    global exiting
    global entering
    global fps
    print('roomcondition')
    if system_state == 0:                                                  # Room condition state
        lcd.clear()
        # write temp and humi to lcd
        lcd.setCursor(0, 0)                                   
        lcd.write('Tem:{}C'.format(temp))                                  # Write temperture to lcd
        lcd.setCursor(1, 0)
        lcd.write('Hum:{}%'.format(humi))                                  # Write humididy to lcd
        lcd.setCursor(0, 8)
        lcd.write('Moi:{}%'.format(mois))                                  # Write moisture to lcd      
        lcd.setCursor(1, 8)                                                # Write total people in room
        lcd.write('total:{}'.format(total))
    elif system_state == 1:                                                # QR valid scan state
        system_state = 0
        current_state = 1
        lcd.clear()
        lcd.setCursor(0, 0)                                   
        lcd.write('QR scan valid')
        lcd.setCursor(1, 0)                                   
        lcd.write('Enter the Room')
        time.sleep(5)
    elif system_state == 2:                                                # Room full state
        system_state = 0
        current_state = 2
        lcd.clear()
        lcd.setCursor(0, 0)                                   
        lcd.write('room is full')
        lcd.setCursor(1, 0)                                   
        lcd.write('Enter is rejected')
        time.sleep(5) 
    elif system_state == 3:                                                # QR invalid scan state
        system_state = 0
        current_state = 3
        lcd.clear()
        lcd.setCursor(0, 0)                                   
        lcd.write('QR scan invalid')
        lcd.setCursor(1, 0)                                   
        lcd.write('Enter is rejected')
        time.sleep(5)
    elif system_state == 4:                                                # Exit state
        system_state = 0
        current_state = 4
        lcd.clear()
        lcd.setCursor(0, 0)                                   
        lcd.write('Exiting the room')
        time.sleep(5)
    
    # Notify room full by turning on off LED
    if total == 5:                                                         # If room full, red LED on, else off
        button.led.light(True)
    if total < 5:
        button.led.light(False)
    
    # Sending data to UI through Socket IO
    sio.emit('sensor', {'temperature':temp, 'humidity':humi,'moisture':mois})  
    sio.emit('motion', {'total_people':total,  'people_in':entering, 'people_out':exiting})
    sio.emit('checkout',current_state)
    

# Funtion for socket io
def threadingforQR(img):
    res, frame = cv2.imencode('.jpg', img,[cv2.IMWRITE_JPEG_QUALITY,80])   # from image to binary buffer
    data = base64.b64encode(frame)                                         # convert to base64 format
    sio.emit('video', data)                                                # send to server

# Funtion for scaning QR
def QRcheck():
    # Set global variable
    global pTime                                                           # varialbe for fps display
    global entering                                                        # variable for counting enter the room
    global exiting                                                         # variable for counting exit the room
    global count_QR                                                        # variable for counting time to scan QR
    global total                                                           # variable for total people in rooom
    global entering                                                        # variable for counting enter the room
    global system_state
    global myData
    global current_state
    global fps
    
    stsQRcam = 1                                                           # QR cam status 1 = on, 0 = off
    cap = cv2.VideoCapture(0)                                              # Camera Streaming
    while stsQRcam and count_QR != TIME_QR:                                # Frequency 10Hz, 0.1s for 1 count  
        # Send img by socket
        success, img1 = cap.read()                                         # Capture real image from camera
        res, frame = cv2.imencode('.jpg', img1,[cv2.IMWRITE_JPEG_QUALITY,80]) # from image to binary buffer
        data = base64.b64encode(frame)                                     # convert to base64 format
        sio.emit('video', data)                                            # send to server
        img = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)                       # Convert the real imatge to the grayscale fo easy to scan

        # Frame rate
        cTime = time.time()
        fps = round(1 / (cTime - pTime))
        pTime = cTime

        for barcode in decode(img):                                        # Scan Barcode
            myData = barcode.data.decode('utf-8')
            currentTime = time.ctime()
            if myData in myDataList:                                       # Check on the list or not
                myOutput = 'Authorized'
                myColor = (0, 255, 0)                                      # Green
                # Voice the welcome message
                myData = myData[0:(len(myData)-9)]                         # Filter out the student ID for welcome message
                check_in_data = currentTime + '\tAuthorized\t\t' + myData
                check_in_list(check_in_data)
                stsQRcam = 0              
                if total < 5:                                              # Check people in room less than 5
                    entering = entering + 1
                    t1 = threading.Thread(target=buzzer_on)                # buzzer on
                    t1.start()                           
                    system_state = 1
                else:                                                      # If there are 5 people in room already
                    print('Room Full')
                    t1 = threading.Thread(target=buzzer_reject)            # buzzer on
                    t1.start()  
                    entering = entering
                    system_state = 2
                print(check_in_data)
                # Drawing bonding box for the scanned QR code
                pts = np.array([barcode.polygon], np.int32)
                pts = pts.reshape((-1, 1, 2))
                cv2.polylines(img, [pts], True, myColor, 5)
                pts2 = barcode.rect
            else:
                myOutput = 'Un-Authorized'
                myColor = (0, 0, 255)                                      # Red
                # Drawing bonding box for the scanned QR code
                pts = np.array([barcode.polygon], np.int32)
                pts = pts.reshape((-1, 1, 2))
                cv2.polylines(img, [pts], True, myColor, 5)
                pts2 = barcode.rect
                stsQRcam = 1
                check_in_data = currentTime + '\tUn-Authorized\t' + myData
                check_in_list(check_in_data)
                print(check_in_data)
                t2 = threading.Thread(target=led_blink)
                t2.start()
                system_state = 3
        count_QR += 1                                                       # counting for set time QR check 
        total = entering - exiting                                          # total people in room
        sio.emit('fps_qr', fps)                                             # Send fps to UI
        print('Number of people in room: ', total)
        print('People in: ', entering)
        print('People out: ', exiting)
        print('count: ', count_QR) 
    if myData == None:
        current_state = 5
    myData = None

    if count_QR == TIME_QR:                                                 # If QR scan times out, buzzer on for 1s 
        t3 = threading.Thread(target=buzzer_timeout)
        t3.start()

# Function for Distance dectect
def measure():
    distance_detect = distance.get_distance()
    print('{} cm'.format(distance_detect))
    return distance_detect
# Funtion for motion sensor dectected
def on_detect():
    global time_motion 
    time_motion = 0
    global flag                                                             # global variable
    global count_QR
    global exiting
    global total
    global entering
    global system_state
    global current_state
    global distant_count
    print('check', system_state)
    print('state_check', current_state)
    if current_state == 3:                                                  # Invalid
        system_state = 0
        current_state = 0
        print('Invalidout')
    elif current_state == 2:                                                # Room full
        system_state = 0
        current_state = 0
    elif current_state == 5:                                                # No scan
        system_state = 0
        current_state = 0
        print('No scan')    
    elif system_state == 0:
        flag = 1
        current_state = 0
        print('Motion detected')                                            # print out whenever motion detected
        # turn on Ultra sonic sensor
        while flag != 0:
            distance_detect = measure()
            time.sleep(0.4)
            if distance_detect < DISTANCE:                                  # if people in range -> run QR scan
                distant_count += 1
                if distant_count == 2:
                    distant_count = 0
                    QRcheck()
                    flag = 0
            else:                                                           # in case people exit the room
                time_motion += 1                                            # counting time for open ultra sonic
                print('time_motion', time_motion)
                if time_motion == TIME_MOTION:                              # Time limit for run ultra sonic
                    time_motion = 0
                    if total == 0:
                        exiting = exiting
                    else:
                        exiting += 1
                        system_state = 4  
                    flag = 0
                    print('exit', exiting)
                
        total = entering - exiting                                          # total people in room
        sio.emit('motion', {'total_people':total,  'people_in':entering, 'people_out':exiting})  # Send data inside room to UI
        count_QR = 0                                                        # Set time count back 0 for next loop

# main function
def main():    
    while True:
        roomCondition()
        t4 = threading.Thread(target=LCD_roomCondition)
        t4.start()
        motionSensor.on_detect = on_detect                                  # Motion detected
        time.sleep(0.1)
 
if __name__ == '__main__':
    main()