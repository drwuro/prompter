import threading
import subprocess
import time
import os

from wurolib import print


class AudioThread():
    def __init__(self, outPath):
        self.outPath = outPath

        self.running = False
        self.process = None
        self.playProcess = None

        self.thread = threading.Thread(target=self._run)

        self.meter_left = 0
        self.meter_right = 0
        self.peak_left = 0
        self.peak_right = 0
        
    def start(self):
        self.running = True
        self.thread.start()
            
    def stop(self):
        self.running = False

    def _run(self):
        import select
        while self.running:
            buf = b''
            while self.running:
                if self.process:
                    select.select([self.process.stderr], [], [])
                    if not self.process:
                        break
                        
                    data = self.process.stderr.read()
                    if data == b'':
                        break

                    buf = buf + data
                    while self.running:
                        line, sep, buf = buf.partition(b'\r')
                        if not sep:
                            buf = line
                            break
                        
                        try:
                            line = str(line)
                            p1, p2 = line.split('|')
                            
                            val1 = p1.count('#') * 100/35
                            val2 = p2.count('#') * 100/35
                            
                            center = line.find('|')
                            peak1 = line[center-4:center-1].strip()
                            peak2 = line[center+1:center+3].strip()
                            
                            if peak1 == 'MAX':
                                peak1 = 100
                            if peak2 == 'MAX':
                                peak2 = 100
                            
                            self.setMeter(val1, val2, int(peak1), int(peak2))
                        except Exception as e:
                            print(e)
                else:
                    time.sleep(0.1)
            
                continue
                
            else:
                time.sleep(0.1)
            
        self.stopRecording()
        self.stopPlaying()
        
    def startRecording(self):
        if self.isRecording():
            print('ALREADY RECORDING!')
            return
        
        date = time.gmtime()
        filename = 'rec-%04i-%02i-%02i_%02i-%02i-%02i.wav' % (date.tm_year,
                                                              date.tm_mon,
                                                              date.tm_mday,
                                                              date.tm_hour,
                                                              date.tm_min,
                                                              date.tm_sec,
                                                              )
        print('start recording:\n%s' % filename)
        
        self.process = subprocess.Popen(['arecord',
                                         '-D', 'hw:1,0',   # device
                                         '-f', 'cd',       # cd quality
                                         '-c', '2',        # 2 channels
                                         '-V', 'stereo',   # VU meter
                                         os.path.join(self.outPath, filename),
                                         ],
                                         stderr=subprocess.PIPE)

        import fcntl
        fd = self.process.stderr.fileno()
        fl = fcntl.fcntl(fd, fcntl.F_GETFL)
        fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)

    def stopRecording(self):
        print('stop recording')
        if self.process:
            self.process.kill()
            self.process = None
            
        self.setMeter(0, 0)
    
    def isRecording(self):
        if self.process:
            return True
        else:
            return False
        
    def setMeter(self, left, right, peakl=0, peakr=0):
        self.meter_left = left
        self.meter_right = right
        
        self.peak_left = peakl
        self.peak_right = peakr

    def getMeter(self):
        return self.meter_left, self.meter_right, self.peak_left, self.peak_right
    
    def startPlaying(self, filename):
        print('start playing', filename)
        if not filename:
            return
            
        if self.playProcess:
            self.playProcess.kill()
            
        self.playProcess = subprocess.Popen(['aplay', filename])
        
    def stopPlaying(self):
        print('stop playing')
        if self.playProcess:
            self.playProcess.kill()

