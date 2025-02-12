#########################
###
### BitmapFont
### by zeha@drwuro.com
###
### version 1.3 (2025)
###
#########################


import pygame

NUM_CHARS = 96
TEXT_CACHING = True


class BitmapFont:
    def __init__(self, filename, char_w=8, char_h=8, zoom=1, scr_w=320, scr_h=240):
        self.lastxpos, self.lastypos = 0, 0

        self.char_w = char_w
        self.char_h = char_h

        self.scr_w = scr_w
        self.scr_h = scr_h

        self.fonts = {}

        self.lastcolor = (255, 255, 255)

        self.font = pygame.image.load(filename)

        self.char_w *= zoom
        self.char_h *= zoom

        self.textCache = {}

    def initColor(self, c):
        f = pygame.transform.scale(self.font, (self.char_w * NUM_CHARS, self.char_h))
        f.fill(c, special_flags=pygame.BLEND_MULT)
        self.fonts[c] = f

    def drawText(self, output, text, x=None, y=None, fgcolor=None, bgcolor=None):
        if x is None:
            x = self.lastxpos
        if y is None:
            y = self.lastypos

        if fgcolor is None:
            fgcolor = self.lastcolor
        else:
            self.lastcolor = fgcolor

        if bgcolor is not None:
            output.fill(bgcolor, (x * self.char_w,
                                 (y * self.char_h),
                                 len(text) * self.char_w,
                                 (self.char_h))
                                 )

        if fgcolor not in self.fonts:
            self.initColor(fgcolor)

        if TEXT_CACHING:
            key = (text, fgcolor, bgcolor)

            if key not in self.textCache:
                cacheSurface = pygame.Surface((len(text) * self.char_w, self.char_h), flags=pygame.SRCALPHA)

                for i, c in enumerate(text):
                    grabx = (ord(c) - 32) * self.char_w
                    blitx = i * self.char_w
                    blity = (self.char_h - self.char_h + 1) / 2

                    cacheSurface.blit(self.fonts[fgcolor], (blitx, blity), (grabx, 0, self.char_w, self.char_h))
                    self.textCache[key] = cacheSurface
            else:
                cacheSurface = self.textCache[key]

            blitx = x * self.char_w
            blity = y * self.char_h + (self.char_h - self.char_h + 1) / 2
            output.blit(cacheSurface, (blitx, blity))
        else:
            for i, c in enumerate(text):
                grabx = (ord(c) - 32) * self.char_w
                blitx = (x + i) * self.char_w
                blity = y * self.char_h + (self.char_h - self.char_h + 1) / 2

                output.blit(self.fonts[fgcolor], (blitx, blity), (grabx, 0, self.char_w, self.char_h))

        self.lastxpos = x
        self.lastypos = y + 1

    def centerText(self, output, text, y=None, fgcolor=None, bgcolor=None, align=True):
        if align:
            x = ((self.scr_w // self.char_w) - len(text) +1) // 2
        else:
            x = ((self.scr_w // self.char_w) - len(text)) / 2

        self.drawText(output, text, x, y, fgcolor, bgcolor)

    def locate(self, x=None, y=None):
        if x is not None:
            self.lastxpos = x
        if y is not None:
            self.lastypos = y

    def locateRel(self, x=None, y=None):
        if x is not None:
            self.lastxpos += x
        if y is not None:
            self.lastypos += y


