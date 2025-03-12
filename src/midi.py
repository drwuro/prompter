import pygame.midi
import threading
import time

from wurolib import print


class MidiThread:
    def __init__(self, pageCallback=lambda:None):
        pygame.midi.init()
        
        try:
            self.midi_in = pygame.midi.Input(3) 
        except:
            self.midi_in = None

        try:
            self.midi_out = pygame.midi.Output(2)
        except:
            self.midi_out = None

        self.running = False
        self.thread = threading.Thread(target=self._run)

        self.pageCallback = pageCallback

    def start(self):
        self.running = True
        self.thread.start()
            
    def stop(self):
        self.running = False

    def _run(self):
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

        while self.running:
            if self.midi_in:
                while not self.midi_in.poll():
                    time.sleep(0.1)

                data = self.midi_in.read(256)

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
                                self.pageCallback(pagename)

            else:
                time.sleep(0.1)
    
    def sendMute(self, channel):
        if self.midi_out is None:
            return False
            
        self.midi_out.note_on(38 + (channel -1), 0x7F, 15)
        return True
    
    def sendUnmute(self, channel):
        if self.midi_out is None:
            return False
            
        self.midi_out.note_off(38 + (channel -1), 0x7F, 15)
        return True
        
    def sendNextSequence(self):
        if self.midi_out is None:
            return False
            
        self.midi_out.note_on(37, 0x7F, 15)
        return True
    
