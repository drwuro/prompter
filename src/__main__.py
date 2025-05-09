import pygame
import os
import time
import math
import threading

import wurolib
from wurolib import print

from midi import MidiThread
from audio import AudioThread


DEBUG = not True
ROTATED_DISPLAY = True

MIN_X = 3936
MAX_X = 227
MIN_Y = 268
MAX_Y = 3880

####

SCR_W = 160
SCR_H = 106

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


error_message = ''
def showError(msg):
    global error_message
    error_message = msg
    if msg:
        print('ERROR:', msg)

def getPath():
    path = '/mnt/usb'
    if not os.path.ismount(path):
        path = '.'

    return path    

def getMousePos(e):        
    xpos = (e.pos[1] - MIN_X) / (MAX_X - MIN_X) * SCR_W
    ypos = (e.pos[0] - MIN_Y) / (MAX_Y - MIN_Y) * SCR_H
    
    if ROTATED_DISPLAY:
        xpos = SCR_W - xpos
        ypos = SCR_H - ypos

    return xpos, ypos

def getMousePosRaw(e):
    xpos = e.pos[1]
    ypos = e.pos[0]

    return xpos, ypos

pages = {}
pageCmds = {}

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
            elif line.startswith('CMD:'):
                cmd_key, cmd_exec = line[4:].strip().split(' ', 1)
                if not page_id in pageCmds:
                    pageCmds[page_id] = {}
                pageCmds[page_id][cmd_key] = cmd_exec
            else:
                if page_id is not None:
                    pages[page_id].append(line)


# --


class MainScreen(wurolib.Screen):
    def __init__(self, context):
        super().__init__(context)
        self.currentPage = 'DEFAULT'
        
        self.cmdQueue = []
        self.cmdQueuePage = None

        self.lastMousePos = (0, 0)
        self.lastMousePosRaw = (0, 0)
        self.lastClickPos = (0, 0)

        self.debounceRecording = False

    def render(self):
        self.context.fill(COLORS[6])

        self.drawPage()
        self.drawRecLabel()
        self.drawMeters()

        if error_message:
            self.context.center(error_message, y=LAST_LINE-1, fgcolor=COLORS[1], bgcolor=COLORS[2])

    def drawPage(self):
        self.context.locate(0, 0.5)
        for line in pages[self.currentPage]:
            bgcolor = None
            fgcolor = COLORS[1]

            if line.startswith('BLINK:'):
                if (time.time() * 1000) % 1000 > 500:
                    line = line[6:].strip()
                else:
                    line = ''

            elif line.startswith('BGCOLOR:'):
                color, line = line[8:].strip().split(' ', 1)
                bgcolor = COLORS[int(color)]
                
            elif line.startswith('FGCOLOR:'):
                color, line = line[8:].strip().split(' ', 1)
                fgcolor = COLORS[int(color)]
                
            elif line.startswith(':MOUSEPOS'):
                self.context.center('%i / %i' % self.lastMousePos, fgcolor=COLORS[1])
                self.context.center('%i / %i' % self.lastMousePosRaw, fgcolor=COLORS[1])
                self.context.center('%i / %i' % self.lastClickPos, fgcolor=COLORS[10])
                line = ''

            self.context.center(line, fgcolor=fgcolor, bgcolor=bgcolor)


    def drawRecLabel(self):
        if audioThread.isRecording():
            # show rec label
            if (time.time() * 1000) % 1000 > 500:
                self.context.print(' `REC ', x=0.5, y=LAST_LINE, fgcolor=COLORS[1], bgcolor=COLORS[2])
            else:
                self.context.print(' `REC ', x=0.5, y=LAST_LINE, fgcolor=COLORS[10], bgcolor=COLORS[2])
        else:
            self.context.print('  REC ', x=0.5, y=LAST_LINE, fgcolor=COLORS[15], bgcolor=COLORS[14])
            
    def drawMeters(self):
        scale = (SCR_W - 9*FONT_W) / 100
        
        MX = math.floor(SCR_W - 100 * scale -5)
        MY = LAST_LINE * FONT_H

        meter_left, meter_right, peak_left, peak_right = audioThread.getMeter()
        
        pygame.draw.rect(self.context.output, COLORS[0], (MX -1, MY -1, math.floor(100 * scale) +2, 9))
        pygame.draw.rect(self.context.output, COLORS[5], (MX,    MY,    meter_left * scale, 3))
        pygame.draw.rect(self.context.output, COLORS[5], (MX,    MY +4, meter_right * scale, 3))
            
        for clip, colorid in [(70, 7), (80, 2)]:
            if meter_left > clip:
                pygame.draw.rect(self.context.output, COLORS[colorid], (MX + math.floor(clip * scale), MY, math.floor((meter_left - clip) * scale + (1 if colorid == 2 else 0)), 3))
            if meter_right > clip:
                pygame.draw.rect(self.context.output, COLORS[colorid], (MX + math.floor(clip * scale), MY +4, math.floor((meter_right - clip) * scale + (1 if colorid == 2 else 0)), 3))
        
        if peak_left:
            pygame.draw.rect(self.context.output, COLORS[14 if peak_left < 99 else 10], (math.floor(MX + peak_left * scale), MY, 1, 3))
        if peak_right:
            pygame.draw.rect(self.context.output, COLORS[14 if peak_right < 99 else 10], (math.floor(MX + peak_right * scale), MY +4, 1, 3))

    def event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_SPACE, pygame.K_RIGHT):
                self.nextPage()
            elif event.key == pygame.K_LEFT:
                self.prevPage()

            elif event.key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4):

                cmd_id = {pygame.K_1: '1',
                          pygame.K_2: '2',
                          pygame.K_3: '3',
                          pygame.K_4: '4',
                          }[event.key]

                if not self.currentPage in pageCmds:
                    print('no page commands for page %s' % self.currentPage)
                    return
                
                if cmd_id in pageCmds[self.currentPage]:
                    self.runCommand(pageCmds[self.currentPage][cmd_id])
                else:
                    print('page command %s not defined' % cmd_id)

        elif event.type == pygame.MOUSEBUTTONUP:
            xpos, ypos = getMousePos(event)

            if xpos < FONT_W * 7 and ypos > SCR_H - FONT_H * 2:
                if not self.debounceRecording:
                    if not audioThread.isRecording():
                        audioThread.startRecording()
                    else:
                        audioThread.stopRecording()
                        
                    self.debounceRecording = True

                    self.lastClickPos = getMousePos(event)

            elif xpos < FONT_W * 7 and ypos < FONT_H * 2:
                switchToShutdown()

        elif event.type == pygame.MOUSEMOTION:
            self.lastMousePos = getMousePos(event)
            self.lastMousePosRaw = getMousePosRaw(event)

        elif event.type == pygame.MOUSEBUTTONDOWN:
            self.debounceRecording = False

    def selectPage(self, pagename):
        if pagename.strip() in pages:
            self.currentPage = pagename.strip()
            
            if DEBUG:
                print('selected page', self.currentPage)
                
            showError(None)

            if self.cmdQueue:
                if self.currentPage == self.cmdQueuePage:
                    self.sendCommands(self.cmdQueue)
                else:
                    if DEBUG:
                        print('different page!')

                self.cmdQueue.clear()
        else:
            showError('page %s not found' % pagename.strip())

    def nextPage(self):
        pagenames = list(pages.keys())
        index = pagenames.index(self.currentPage) +1

        try:
            pagename = pagenames[index]
            self.selectPage(pagename)
        except:
            showError('already on last page')

    def prevPage(self):
        pagenames = list(pages.keys())
        index = pagenames.index(self.currentPage) -1

        if index < 0:
            index = 0

        try:
            pagename = pagenames[index]
            self.selectPage(pagename)
        except:
            showError('already on first page')
            
    def runCommand(self, cmd):
        cmds = cmd.split()
        
        wait = False
        cmdQueue = []
        
        for cmd in cmds:
            if cmd.startswith('mute'):
                _cmd, channels = cmd.split('=')
                channels = channels.split(',')

                for channel in channels:
                    cmdQueue.append((midiThread.sendMute, int(channel)))
                
            elif cmd.startswith('unmute'):
                _cmd, channels = cmd.split('=')
                channels = channels.split(',')

                for channel in channels:
                    cmdQueue.append((midiThread.sendUnmute, int(channel)))
            
            elif cmd.startswith('only'):
                _cmd, channels = cmd.split('=')
                channels = channels.split(',')
                
                unmutes = [int(c) for c in channels]
                mutes = list(range(1,17))
                for c in unmutes:
                    mutes.remove(c)
                
                for c in unmutes:
                    cmdQueue.append((midiThread.sendUnmute, c))
                for c in mutes:
                    cmdQueue.append((midiThread.sendMute, c))
                        
            elif cmd.startswith('not'):
                _cmd, channels = cmd.split('=')
                channels = channels.split(',')
                
                mutes = [int(c) for c in channels]
                unmutes = list(range(1,17))
                for c in mutes:
                    unmutes.remove(c)
                
                for c in unmutes:
                    cmdQueue.append((midiThread.sendUnmute, c))
                for c in mutes:
                    cmdQueue.append((midiThread.sendMute, c))
                        
            elif cmd.startswith('next'):
                if not midiThread.sendNextSequence():
                    showError('%s failed' % cmd)

            elif cmd.startswith('prev'):
                if not midiThread.sendPrevSequence():
                    showError('%s failed' % cmd)
                    
            elif cmd.startswith('wait'):
                wait = True
                self.sendCommands(cmdQueue)
                cmdQueue = []

            elif cmd.startswith('console'):
                toggleConsole()
                
        
        if not wait:
            self.sendCommands(cmdQueue)
        else:
            self.cmdQueue = cmdQueue
            self.cmdQueuePage = self.currentPage
            
    def sendCommands(self, queue):
        if DEBUG:
            print('%s queued commands' % len(queue))
            
        for cmd, arg in set(queue):
            if not cmd(arg):
                showError('%s(%s) failed' % (cmd.__name__, arg))

    def sync(self):
        if DEBUG:
            print('received sync')

        self.sendCommands(self.cmdQueue)
        self.cmdQueue.clear()


# --


class PlayScreen(wurolib.Screen):
    def __init__(self, context):
        super().__init__(context)

        self.selectedFile = None
        self.playingFile = None

        self.fileList = self.getFiles()

    def render(self):
        self.context.fill(COLORS[6])

        self.drawFiles()
        self.drawPlayButton()

    def event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_DOWN:
                if self.selectedFile is None:
                    self.selectedFile = -1
                
                self.selectedFile += 1
                self.selectedFile %= len(self.fileList)

            elif event.key == pygame.K_UP:
                if self.selectedFile is None:
                    self.selectedFile = len(self.fileList)
                
                self.selectedFile -= 1
                self.selectedFile %= len(self.fileList)

            elif event.key == pygame.K_RETURN:
                audioThread.startPlaying(self.fileList[self.selectedFile])

    def getFiles(self):
        path = getPath()
        
        filenames = os.listdir(path)

        files = []
        for fn in filenames:
            if fn.endswith('.wav'):
                files.append(fn)
        
        return files

    def drawFiles(self):
        self.context.locate(0, 0)

        for i, filename in enumerate(self.fileList):
            self.context.print(filename, x=0, fgcolor=COLORS[5 if i != self.selectedFile else 1], bgcolor=COLORS[0])
            
            if i == self.selectedFile:
                self.playingFile = os.path.join(getPath(), filename)

    def drawPlayButton(self):
        self.context.print(' PLAY ', x=SCR_W//FONT_W - 7, y=LAST_LINE, fgcolor=COLORS[1], bgcolor=COLORS[14])


# --


class ShutdownScreen(wurolib.Screen):
    def __init__(self, context):
        super().__init__(context)

    def render(self):
        self.context.fill(COLORS[6])

        self.context.center('REALLY SHUTDOWN?', y=3, fgcolor=COLORS[1], bgcolor=COLORS[2])
        self.context.print(' YES ', x=5, y=6, fgcolor=COLORS[1], bgcolor=COLORS[11])
        self.context.print(' NO  ', x=SCR_W//FONT_W - 10, y=6, fgcolor=COLORS[1], bgcolor=COLORS[11])

    def event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                mainApp.quit()

        elif event.type == pygame.MOUSEBUTTONUP:
            xpos, ypos = getMousePos(event)

            if ypos > FONT_H * 6 and ypos < FONT_H * (6 + 1):
                if xpos > FONT_W * 5 and xpos < FONT_W * 10:
                    mainApp.quit()

                elif xpos > SCR_W - FONT_W * 10 and xpos < SCR_W - FONT_W * 5:
                    switchToMain()


# --


def consoleCommands(cmd):
    cmd = cmd.strip()

    if ' ' in cmd:
        cmd, args = cmd.split(' ', 1)
        args = args.split()
    else:
        args = []

    if not cmd:
        return

    if cmd == 'help':
        print('pages')
        print('show [PAGE]')
        print('rec')
        print('play')
        print('stop')
        print('size [N]')
        print('debug')
        print('exit/quit/bye')

    elif cmd == 'pages':
        for pagename in list(pages.keys()):
            print('- %s' % pagename)
            
    elif cmd == 'show':
        if args:
            mainScreen.selectPage(args[0])
        else:
            mainScreen.selectPage('DEFAULT')

    elif cmd in ('exit', 'quit', 'bye'):
        print('good bye.')
        mainApp.quit()

    elif cmd == 'rec':
        audioThread.startRecording()

    elif cmd == 'play':
        if playScreen.fileList:
            if playScreen.selectedFile is not None:
                audioThread.startPlaying(playScreen.fileList[playScreen.selectedFile])
            else:
                print('no file selected, playing first one')
                audioThread.startPlaying(playScreen.fileList[0])
        else:
            print('no files available')

    elif cmd == 'stop':
        audioThread.stopRecording()
        audioThread.stopPlaying()

    elif cmd == 'size':
        if args:
            size = int(args[0])
            if size < 1:
                size = 1
        else:
            size = 1

        global SCR_W, SCR_H
        SCR_W = 160 * size
        SCR_H = 106 * size
        fontzoom = 1
        
        if size == 2:       # special case for rpi3 display
            SCR_W = 480
            SCR_H = 320
            fontzoom = 2
        
        initScreens(fontzoom)

        print('new resolution: %sx%s' % (SCR_W, SCR_H))
        print('console dimensions: %sx%s' % (consoleScreen.charsPerLine, consoleScreen.maxLines))

        mainApp.setScreen(consoleScreen)

    elif cmd == 'debug':
        global DEBUG
        DEBUG = not DEBUG
        print('debug mode is', ['OFF','ON'][DEBUG])

    else:
        print('unknown command')


# -- wurolib stuff / screens etc

mainScreen = None
playScreen = None
shutdownScreen = None
consoleScreen = None

def initScreens(fontzoom=1):
    global mainScreen, playScreen, shutdownScreen, consoleScreen
    global currentScreen
        
    font = wurolib.BitmapFont(filename='gfx/moonfont.png',
                              char_w=FONT_W, char_h=FONT_H,
                              zoom=fontzoom,
                              )
    
    for color in COLORS:
        font.initColor(color)

    context = wurolib.initContext(SCR_W, SCR_H, title='prompter', font=font)

    mainScreen = MainScreen(context)
    playScreen = PlayScreen(context)
    shutdownScreen = ShutdownScreen(context)
    consoleScreen = wurolib.Console(context, wrap=True, interactive=True, callback=consoleCommands, bgcolor=(0, 0, 0, 128))

    currentScreen = mainScreen

    global LAST_LINE
    LAST_LINE = SCR_H // FONT_H -1


initScreens()

showConsole = False
def toggleConsole():
    global showConsole
    global currentScreen

    showConsole = not showConsole

    if showConsole:
        currentScreen = mainApp.getScreen()
        mainApp.setScreen(consoleScreen)
    else:
        mainApp.setScreen(currentScreen)

def switchToMain():
    global mainScreen, currentScreen
    mainApp.setScreen(mainScreen)
    currentScreen = mainScreen

def switchToPlay():
    global playScreen, currentScreen
    mainApp.setScreen(playScreen)
    currentScreen = mainScreen

def switchToShutdown():
    global shutdownScreen, currentScreen
    mainApp.setScreen(shutdownScreen)
    currentScreen = mainScreen
    
def pageCallback(pagename):
    mainScreen.selectPage(pagename)

def syncCallback():
    mainScreen.sync()


# -- initialization of threads and pages

loadData()

midiThread = MidiThread(pageCallback=pageCallback, syncCallback=syncCallback)
midiThread.start()

audioThread = AudioThread(outPath=getPath())
audioThread.start()

if not midiThread.midi_in:
    showError('no midi input device')


# -- main app

mainApp = wurolib.MainApp()

mainApp.setScreen(currentScreen)

mainApp.registerGlobalEvent(pygame.KEYDOWN, pygame.K_F11, pygame.display.toggle_fullscreen)
mainApp.registerGlobalEvent(pygame.KEYDOWN, pygame.K_F12, toggleConsole)

mainApp.registerGlobalEvent(pygame.KEYDOWN, pygame.K_F1, switchToMain)
mainApp.registerGlobalEvent(pygame.KEYDOWN, pygame.K_F2, switchToPlay)
mainApp.registerGlobalEvent(pygame.KEYDOWN, pygame.K_ESCAPE, switchToShutdown)

if DEBUG:
    toggleConsole()

try:
    mainApp.run()
finally:
    import traceback

    with open('prompter.log', 'w') as f:
        f.writelines(['%s\n' % line for line in wurolib.printLog])
        f.write(traceback.format_exc())

    midiThread.stop()
    audioThread.stop()

