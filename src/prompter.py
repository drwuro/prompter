import pygame
import pygame.midi
import bitmapfont
import time
import threading
import subprocess
import math
import os


SCALED = True
SCALE = 3
SCR_W, SCR_H = 480//SCALE, 320//SCALE
ROTATED_DISPLAY = True

FONT_W, FONT_H = 6, 8

LAST_LINE = SCR_H // FONT_H -1

COLORS = [(0, 0, 0),       # 000000
          (255, 255, 255), # FFFFFF
          (153, 51, 51),   # 993333
          (119, 221, 221), # 77DDDD
          (153, 68, 187),  # 9944BB
          (119, 187, 51),  # 77BB33
          (51, 34, 187),   # 3322BB
          (225, 225, 102), # FFFF66

          (170, 102, 34),  # AA6622
          (102, 68, 0),    # 664400
          (238, 136, 136), # EE8888
          (85, 85, 85),    # 555555
          (136, 136, 136), # 888888
          (136, 238, 136), # 88EE88
          (119, 119, 238), # 7777EE
          (187, 187, 187), # BBBBBB

          (255, 0, 255),   # invalid
          ]

COLNAMES = ['BLK',
            'WHT',
            'RED',
            'CYN',
            'PUR',
            'GRN',
            'BLU',
            'YEL',
            'ORG',
            'BRN',
            'LRD',
            'GR1',
            'GR2',
            'LGN',
            'LBL',
            'GR3',
            ]
            
MIN_X = 3936
MAX_X = 227
MIN_Y = 268
MAX_Y = 3880

pygame.midi.init()
pygame.display.init()

screen = pygame.display.set_mode((SCR_W, SCR_H), flags=pygame.SCALED if SCALED else 0)

font = bitmapfont.BitmapFont('gfx/moonfont.png', 
                             char_w=FONT_W,
                             char_h=FONT_H,
                             zoom=1,
                             scr_w=SCR_W, scr_h=SCR_H)

for color in COLORS:
    font.initColor(color)

pages = {}
current_page = 'DEFAULT'

error_message = None


def midiThread():
    global running
    
    try:
        midi_in = pygame.midi.Input(3)
    except:
        showError('no midi input device')
        return

    def convert(bytes):
        s = ''
        for b in bytes:
            if b == 0:
                s += ' '
            elif b < 10:
                s += str(b)
            elif b == 0xF7: # end of message
                break
            else:
                s += chr(b)
        return s

    while running:
        while not midi_in.poll():
            time.sleep(0.1)
        data = midi_in.read(256)
        if data:
            next = False
            for msg in data:
                cmd = msg[0]
                timestamp = msg[1]
                if cmd[0] == 0xF0:  # sysex
                    pagename = convert(cmd[1:])
                    next = True
                elif next:
                    pagename += convert(cmd)
                    if 0xF7 in cmd:
                        next = False
                        switchPage(pagename)


class AudioThread():
    def __init__(self):
        self.running = False
        self.process = None
        self.playProcess = None
        
        self.thread = threading.Thread(target=self._run)
        
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
                            
                            setMeter(val1, val2, int(peak1), int(peak2))
                        except Exception as e:
                            print(e)
                else:
                    time.sleep(0.1)
            
                continue
                
                
                ###
            
            
                #print('still recording...')
                
                data = self.process.stderr.read(162)
                
                try:
                    start = data.find(ord('\r'))
                    end = data[start+1:].find(ord('\r'))
                    
                    line = str(data[start+1:start+1+end])
                    center = line.find('|')
                    val1 = int(line[center-4:center-1])
                    val2 = int(line[center+1:center+3])
                    
                    setMeter(val1, val2)
                except Exception as e:
                    #print(e)
                    pass
            else:
                time.sleep(0.1)
            
        self.stopRecording()
        
    def startRecording(self):
        if self.isRecording():
            print('ALREADY RECORDING!')
            return
            
        print('start recording')
        
        outpath = getPath()
        
        date = time.gmtime()
        filename = 'rec-%04i-%02i-%02i_%02i-%02i-%02i.wav' % (date.tm_year,
                                                              date.tm_mon,
                                                              date.tm_mday,
                                                              date.tm_hour,
                                                              date.tm_min,
                                                              date.tm_sec,
                                                              )
        
        self.process = subprocess.Popen(['arecord',
                                         '-D', 'hw:1,0',   # device
                                         '-f', 'cd',       # cd quality
                                         '-c', '2',        # 2 channels
                                         '-V', 'stereo',   # VU meter
                                         os.path.join(outpath, filename),
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
            
        setMeter(0, 0)
    
    def isRecording(self):
        if self.process:
            return True
        else:
            return False
    
    def startPlaying(self):
        print('start playing', current_file)
        if not current_file:
            return
            
        if self.playProcess:
            self.playProcess.kill()
            
        self.playProcess = subprocess.Popen(['aplay', current_file])
        
    def stopPlaying(self):
        print('stop playing')
        if self.playProcess:
            self.playProcess.kill()


def loadData():
    global pages
    
    path = getPath()
    
    with open(os.path.join(path, 'pages.txt'), 'r') as f:
        rawdata = f.readlines()
        page_id = None
        
        for i, line in enumerate(rawdata):
            if line.startswith('PAGE:'):
                page_id = line.split(':')[1].strip()
                print('found page:', page_id)
                
                pages[page_id] = []
                
            elif line.startswith('---'):
                continue
            else:
                if page_id is not None:
                    pages[page_id].append(line)


def showError(msg):
    global error_message
    error_message = msg
    if msg:
        print('ERROR:', msg)


def switchPage(pagename):
    global current_page
    
    if pagename.strip() in pages:
        current_page = pagename.strip()
        showError(None)
    else:
        showError('page %s not found' % pagename.strip())


def nextPage():
    global current_page
    index = list(pages.keys()).index(current_page) +1

    try:
        pagename = pages.keys()[index]
        switchPage(pagename)
    except:
        showError('already on last page')


def prevPage():
    global current_page
    index = list(pages.keys()).index(current_page) -1

    try:
        pagename = pages.keys()[index]
        switchPage(pagename)
    except:
        showError('already on first page')
        

def getMousePos(e):        
    xpos = (e.pos[1] - MIN_X) / (MAX_X - MIN_X) * SCR_W
    ypos = (e.pos[0] - MIN_Y) / (MAX_Y - MIN_Y) * SCR_H
    
    if ROTATED_DISPLAY:
        xpos = SCR_W - xpos
        ypos = SCR_H - ypos

    return xpos, ypos


meter_left = 0
meter_right = 0
peak_left = 0
peak_right = 0

def setMeter(left, right, peakl=0, peakr=0):
    global meter_left, meter_right, peak_left, peak_right
    meter_left = left
    meter_right = right
    
    peak_left = peakl
    peak_right = peakr
    
    #print(meter_left, meter_right)


selected_file = None
current_file = None

def selectFile(fileno):
    global selected_file
    selected_file = fileno


def drawPages():
    global bgcolor, fgcolor
    
    font.locate(0, 0.6)
    for line in pages[current_page]:
        if line.startswith('BLINK:'):
            if (time.time() * 1000) % 1000 > 500:
                line = line[6:].strip()
            else:
                line = ''
        elif line.startswith('BGCOLOR:'):
            color, line = line[8:].strip().split(' ', 1)
            bgcolor = COLORS[int(color)]
            #line = line.strip()
        elif line.startswith('FGCOLOR:'):
            color, line = line[8:].strip().split(' ', 1)
            fgcolor = COLORS[int(color)]
            #line = line.strip()
        
        font.centerText(screen, line, fgcolor=fgcolor, bgcolor=bgcolor)
        bgcolor = None
        fgcolor = COLORS[1]
    
def drawRecLabel():
    if audioThread.isRecording():
        # show rec label
        if (time.time() * 1000) % 1000 > 500:
            font.drawText(screen, ' `REC ', x=0.5, y=LAST_LINE, fgcolor=COLORS[1], bgcolor=COLORS[2])
        else:
            font.drawText(screen, ' `REC ', x=0.5, y=LAST_LINE, fgcolor=COLORS[10], bgcolor=COLORS[2])
    else:
        font.drawText(screen, '  REC ', x=0.5, y=LAST_LINE, fgcolor=COLORS[15], bgcolor=COLORS[14])
        
def drawMeters():
    scale = (SCR_W - 9*FONT_W) / 100
    
    MX = math.floor(SCR_W - 100 * scale -5)
    MY = LAST_LINE * FONT_H
    
    pygame.draw.rect(screen, COLORS[0], (MX -1, MY -1, math.floor(100 * scale) +2, 9))
    pygame.draw.rect(screen, COLORS[5], (MX,    MY,    meter_left * scale, 3))
    pygame.draw.rect(screen, COLORS[5], (MX,    MY +4, meter_right * scale, 3))
        
    for clip, colorid in [(70, 7), (80, 2)]:
        if meter_left > clip:
            pygame.draw.rect(screen, COLORS[colorid], (MX + math.floor(clip * scale), MY, math.floor((meter_left - clip) * scale + (1 if colorid == 2 else 0)), 3))
        if meter_right > clip:
            pygame.draw.rect(screen, COLORS[colorid], (MX + math.floor(clip * scale), MY +4, math.floor((meter_right - clip) * scale + (1 if colorid == 2 else 0)), 3))
    
    if peak_left:
        pygame.draw.rect(screen, COLORS[14 if peak_left < 99 else 10], (math.floor(MX + peak_left * scale), MY, 1, 3))
    if peak_right:
        pygame.draw.rect(screen, COLORS[14 if peak_right < 99 else 10], (math.floor(MX + peak_right * scale), MY +4, 1, 3))


def getPath():
    path = '/mnt/usb'
    if not os.path.ismount(path):
        path = '.'

    return path    

def getFiles():
    path = getPath()
    
    filenames = os.listdir(path)

    final = []
    for fn in filenames:
        if fn.endswith('.wav'):
            final.append(fn)
    
    return final    


the_path = getPath()
the_files = getFiles()

def drawFiles():
    global current_file, the_path, the_files

    font.locate(0, 0)

    for i, fn in enumerate(the_files):
        font.drawText(screen, fn, x=0, fgcolor=COLORS[5 if i != selected_file else 1], bgcolor=COLORS[0])
        
        if i == selected_file:
            current_file = os.path.join(the_path, fn)


def drawPlayButton():
    font.drawText(screen, ' PLAY ', x=SCR_W//FONT_W - 7, y=LAST_LINE, fgcolor=COLORS[1], bgcolor=COLORS[14])

def drawShutdown():
    font.centerText(screen, 'REALLY SHUTDOWN?', y=3, fgcolor=COLORS[1], bgcolor=COLORS[2])
    font.drawText(screen, ' YES ', x=5, y=6, fgcolor=COLORS[1], bgcolor=COLORS[11])
    font.drawText(screen, ' NO  ', x=SCR_W//FONT_W - 10, y=6, fgcolor=COLORS[1], bgcolor=COLORS[11])



try:
    midi_out = pygame.midi.Output(2)
except:
    showError('no midi output device')
    midi_out = None


def sendCommand(cmd):
    global midi_out
    
    if cmd == 'next':
        midi_out.note_on(36, 0x7F, 15)
        midi_out.note_on(37, 0x7F, 15)
    elif cmd == 'mute1':
        midi_out.note_on(38, 0x7F, 15)
        midi_out.note_on(39, 0x7F, 15)
        midi_out.note_on(40, 0x7F, 15)
        midi_out.note_on(41, 0x7F, 15)
    elif cmd == 'mute2':
        midi_out.note_off(38, 0x7F, 15)
        midi_out.note_off(39, 0x7F, 15)
        midi_out.note_off(40, 0x7F, 15)
        midi_out.note_off(41, 0x7F, 15)
    elif cmd == 'mute3':
        midi_out.note_on(38, 0x7F, 15)
        midi_out.note_off(39, 0x7F, 15)
        midi_out.note_off(40, 0x7F, 15)
        midi_out.note_off(41, 0x7F, 15)
    
#    midi_out.write([[0x9F, 36, 0x7F],
#                    [0x9F, 37, 0x7F],
#                   ])


loadData()
running = True
bgcolor = COLORS[5]
fgcolor = COLORS[1]

clock = pygame.time.Clock()

xpos = 0
ypos = 0

# threads
threading.Thread(target=midiThread).start()
audioThread = AudioThread()
audioThread.start()

# start application

mode = 'NORMAL'

try:
    while running:
        screen.fill(COLORS[6])
        
        if mode == 'NORMAL':
            drawPages()
            drawRecLabel()
            drawMeters()
        elif mode == 'PLAY':
            drawFiles()
            drawPlayButton()
        elif mode == 'SHUTDOWN':
            drawShutdown()

        # show error message
        if error_message:
            font.centerText(screen, error_message, y=LAST_LINE-1, fgcolor=COLORS[1], bgcolor=COLORS[2])
        
        pygame.display.flip()
        
        while True:
            e = pygame.event.poll()
            if not e:
                break
                
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    running = False
                if e.key in (pygame.K_SPACE, pygame.K_RIGHT):
                    nextPage()
                if e.key == pygame.K_LEFT:
                    prevPage()

                if e.key == pygame.K_F5:
                    sendCommand('next')
                if e.key == pygame.K_F6:
                    sendCommand('mute1')
                if e.key == pygame.K_F7:
                    sendCommand('mute2')
                if e.key == pygame.K_F8:
                    sendCommand('mute3')

                if e.key == pygame.K_F11:
                    pygame.display.toggle_fullscreen()

            elif e.type == pygame.MOUSEBUTTONUP:
                xpos, ypos = getMousePos(e)
                
                if xpos > SCR_W - FONT_W * 7 and ypos < FONT_H * 3:
                    if mode == 'NORMAL':
                        mode = 'PLAY'
                        the_files = getFiles()
                    else:
                        mode = 'NORMAL'
                    pygame.event.clear()
                    continue

                if mode == 'NORMAL':
                    if xpos < FONT_W * 7 and ypos > SCR_H - FONT_H * 2:
                        if not audioThread.isRecording():
                            audioThread.startRecording()
                        else:
                            audioThread.stopRecording()
                            
                        pygame.event.clear()
                        
                elif mode == 'SHUTDOWN':
                    if ypos > FONT_H * 6 and ypos < FONT_H * (6 + 1):
                        if xpos > FONT_W * 5 and xpos < FONT_W * 10:
                            running = False
                            break
                        elif xpos > SCR_W - FONT_W * 10 and xpos < SCR_W - FONT_W * 5:
                            mode = 'NORMAL'
                        
            elif e.type == pygame.MOUSEBUTTONDOWN:# or e.type == pygame.MOUSEMOTION:
                print(e)
                if mode == 'PLAY':
                    xpos, ypos = getMousePos(e)

                    if xpos > SCR_W - FONT_W * 7 and ypos > SCR_H - FONT_H * 2:
                        audioThread.startPlaying()
                        pygame.event.clear()
                    else:
                        selectFile(ypos // FONT_H -1)
                        pygame.event.clear()
                
                if xpos < FONT_W * 7 and ypos < FONT_H * 2:
                    mode = 'SHUTDOWN'

        time.sleep(0.05)
        clock.tick(20)
except KeyboardInterrupt:
    print('bye')
finally:
    audioThread.stop()
    
    screen.fill(COLORS[0])
    pygame.display.flip()
    
    pygame.quit()
    

#subprocess.Popen(['shutdown', '-P', 'now'])


