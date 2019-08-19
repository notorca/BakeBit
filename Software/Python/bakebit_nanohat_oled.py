#!/usr/bin/env python2.7
#
# BakeBit example for the basic functions of BakeBit 128x64 OLED (http://wiki.friendlyarm.com/wiki/index.php/BakeBit_-_OLED_128x64)
#
# The BakeBit connects the NanoPi NEO and BakeBit sensors.
# You can learn more about BakeBit here:  http://wiki.friendlyarm.com/BakeBit
#
# Have a question about this example?  Ask on the forums here:  http://www.friendlyarm.com/Forum/
#
'''
## License

The MIT License (MIT)

BakeBit: an open source platform for connecting BakeBit Sensors to the NanoPi NEO.
Copyright (C) 2016 FriendlyARM

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
'''

import bakebit_128_64_oled as oled
from PIL import Image
from PIL import ImageFont
from PIL import ImageDraw
import time
import sys
import subprocess
import Queue
import signal
import os
import socket
import fcntl
import struct
import ctypes

width=oled.SeeedOLED_Width
height=oled.SeeedOLED_Height
screenUpdateTime = 1


image = Image.new('1', (width, height))
draw = ImageDraw.Draw(image)
fontb24 = ImageFont.truetype('DejaVuSansMono-Bold.ttf', 24)
font14 = ImageFont.truetype('DejaVuSansMono.ttf', 14)
font12 = ImageFont.truetype('DejaVuSansMono.ttf', 12)
smartFont = ImageFont.truetype('DejaVuSansMono-Bold.ttf', 10)
font10 = ImageFont.truetype('DejaVuSansMono.ttf', 10)
fontb14 = ImageFont.truetype('DejaVuSansMono-Bold.ttf', 14)
font11 = ImageFont.truetype('DejaVuSansMono.ttf', 11)

libc = ctypes.CDLL('libc.so.6')
uptimeBuf = ctypes.create_string_buffer(4096) # generous buffer to hold struct sysinfo


class View:
    def render(self, draw):
        pass
    def processEvent(self, event):
        return self

class VnstatView(View):
    def render(self, draw):
        try:
            IPAddress = get_ip_address('eth0')
        except:
            IPAddress = get_ip()
        draw.text((2,2),"IP:" + str(IPAddress),font=font12, fill=255)
        #This months usage
        cmd = "vnstat -m 2 -i eth0 | grep \"$(date +'%Y-%m')\" | awk '{print $8\" \"substr ($9, 1, 3)}'"
        #cmd = "vnstat -m 2 -i eth0 | grep \"2019-09\" | awk '{print $8\" \"substr ($9, 1, 3)}'" #Usage for this month
        strCurrentUsage = subprocess.check_output(cmd, shell = True )
        draw.text((2,30),"Usage: " + strCurrentUsage, font=font12, fill=255)
        #Last months usage
        cmd = "vnstat -m 2 -i eth0 | grep \"$(date --date=\"$(date +%Y-%m-15) -1 month\" +'%Y-%m')\" | awk '{print $8\" \"substr ($9, 1, 3)}'"
        #cmd = "vnstat -m 2 -i eth0 | grep \"2019-08\" | awk '{print $8\" \"substr ($9, 1, 3)}'" #Usage for this month
        strCurrentUsage = subprocess.check_output(cmd, shell = True )
        draw.text((2,45),"Last: " + strCurrentUsage, font=font12, fill=255)

    def processEvent(self, event):
        return {
            'K1': lambda: self,
            'K2': StatsView,
            'K3': RebootView,
        }[event]()         

class StatsView(View):
    def render(self, draw):
        # Draw some shapes.
        # First define some constants to allow easy resizing of shapes.
        padding = 2
        top = padding
        # Move left to right keeping track of the current x position for drawing shapes.
        x = 0
        #Get CPU Load Averages
        #cmd = "uptime | cut -d : -f 4" #This option fails after a while
        #cmd = "uptime | awk '{print $9, $10, $11}'"
        #cmd = "top -bn1 | grep load | awk '{printf \"CPU Load: %.2f\", $(NF-2)}'"
        cmd = "uptime | awk '{if ($4 == \"min,\") print $9, $10, $11; else print $8, $9, $10;}'"
        CPU = subprocess.check_output(cmd, shell = True )
        #Get system uptime
        cmd = "uptime -p | cut -c3-" #1 hour, x minutes
        UpTime = subprocess.check_output(cmd, shell = True )
        cmd = "free -m | awk 'NR==2{printf \"Mem: %s/%sMB %.2f%%\", $3,$2,$3*100/$2 }'"
        MemUsage = subprocess.check_output(cmd, shell = True )
        cmd = "df -h | awk '$NF==\"/\"{printf \"Disk: %d/%dGB %s\", $3,$2,$5}'"
        Disk = subprocess.check_output(cmd, shell = True )
        tempI = int(open('/sys/class/thermal/thermal_zone0/temp').read())
        if tempI>1000:
            tempI = tempI/1000
        tempStr = "Temperature: %sC" % str(tempI)

        draw.text((x, top+1),    "CPU:" + str(CPU), font=font10, fill=255)
        #draw.text((x, top+5+12),    str(CPU), font=smartFont, fill=255)
        draw.text((x, top+5+8),         "Up: " + str(UpTime), font=font10, fill=255)
        draw.text((x, top+5+20),    str(MemUsage),  font=font10, fill=255)
        draw.text((x, top+5+32),    str(Disk),  font=font10, fill=255)
        draw.text((x, top+5+44),    tempStr,  font=font10, fill=255)

    def processEvent(self, event):
        return {
            'K1': VnstatView,
            'K2': lambda: self,
            'K3': RebootView,
        }[event]()    

class RebootView(View):
    def __init__(self):
        self._selected = 1

    def render(self, draw):
        draw.text((2, 2),  'Exit',  font=fontb14, fill=255)

        draw.rectangle((2,20,width-4,20+16), outline=0, fill=(255 if self._selected == 1 else 0))
        draw.text((4, 22),  'Shutdown',  font=font11, fill=(0 if self._selected == 1 else 255))

        draw.rectangle((2,38,width-4,38+16), outline=0, fill=(255 if self._selected == 2 else 0))
        draw.text((4, 40),  'Reboot',  font=font11, fill=(0 if self._selected == 2 else 255))

    def processEvent(self, event):
        return {
            'K1': self._next,  # move
            'K2': lambda: ConfirmationView('Shutdown' if self._selected == 1 else 'Reboot'),  # confirm
            'K3': VnstatView,
        }[event]()  

    def _next(self):
        self._selected = 2 if self._selected == 1 else 1
        return self

class ConfirmationView(View):
    def __init__(self, title):
        self._title = title
        self._selected = 1

    def render(self, draw):
        draw.text((2, 2), self._title + '?', font=fontb14, fill=255)

        draw.rectangle((2,20,width-4,20+16), outline=0, fill=(255 if self._selected == 1 else 0))
        draw.text((4, 22),  'Yes',  font=font11, fill=(0 if self._selected == 1 else 255))

        draw.rectangle((2,38,width-4,38+16), outline=0, fill=(255 if self._selected == 2 else 0))
        draw.text((4, 40),  'No',  font=font11, fill=(0 if self._selected == 2 else 255))

    def processEvent(self, event):
        return {
            'K1': self._next,  # move
            'K2': VnstatView if self._selected == 2 else lambda: ByeView('poweroff' if self._title == 'Shutdown' else 'reboot'),  # confirm
            'K3': VnstatView,
        }[event]()

    def _next(self):
        self._selected = 2 if self._selected == 1 else 1
        return self

class ByeView(View):
    def __init__(self, action):
        self._action = action
        self._end = False
    
    def render(self, draw):
        if self._end:
            os.system('systemctl ' + self._action)
            raise KeyboardInterrupt
        
        self._end = True
        draw.text((2, 2),  'Performing ' + self._action,  font=fontb14, fill=255)
        draw.text((2, 20),  'Please wait',  font=font11, fill=255)

eventQueue = Queue.Queue()

def receive_signal(signum, stack):
    if signum == signal.SIGUSR1:
        key = 'K1'
    elif signum == signal.SIGUSR2:
        key = 'K2'
    elif signum == signal.SIGALRM:
        key = 'K3'
    print(key, 'pressed')
    eventQueue.put(key)

def main():
    oled.init()  #initialze SEEED OLED display
    oled.setNormalDisplay()      #Set display to normal mode (i.e non-inverse mode)
    oled.setHorizontalMode()

    oled.drawImage(Image.open('friendllyelec.png').convert('1'))
    time.sleep(1)

    signal.signal(signal.SIGUSR1, receive_signal)
    signal.signal(signal.SIGUSR2, receive_signal)
    signal.signal(signal.SIGALRM, receive_signal)

    currentView = VnstatView()

    while True:
        try:
            try:
                event = eventQueue.get(True, screenUpdateTime)
                currentView = currentView.processEvent(event)
            except Queue.Empty:
                pass

            # Draw a black filled box to clear the image
            draw.rectangle((0,0,width,height), outline=0, fill=0)
            currentView.render(draw)
            oled.drawImage(image)
        except KeyboardInterrupt:
            break
        except IOError as e:
            print ("Error:", e)

    # Cleanup before exit
    oled.clearDisplay()

def get_ip_address(ifname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    return socket.inet_ntoa(fcntl.ioctl(
        s.fileno(),
        0x8915,  # SIOCGIFADDR
        struct.pack('256s', ifname[:15])
    )[20:24])

def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't even have to be reachable
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

def uptime():
    if libc.sysinfo(uptimeBuf) != 0:
        print('failed')
        return -1

    uptime = struct.unpack_from('@l', uptimeBuf.raw)[0]
    return uptime

if __name__ == "__main__":
    main()
