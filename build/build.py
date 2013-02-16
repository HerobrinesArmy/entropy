#! /usr/bin/env python3.3

from assembler import assembler
import random

def stripdir(path):
    path = path[max(path.rfind('/'), path.rfind('\\')) + 1:]
    return path [:path.rfind('.')]

class diskfile:
    def __init__(self, diskname, contents):
        dl = diskname.rfind('.')
        self.name = (diskname[:dl] + '\0' * 8)[:8]
        self.ext = (diskname[dl + 1:] + '\0' * 3)[:3]
        self.contents = contents
        self.len = len(contents)
        self.slen = ((self.len - 1) >> 9) + 1
        self.fs = 1 if self.len > 0 else 65535

    def getdte(self):
        dte = []
        dte.extend(entropy.stringtodat('"' + self.name + '"')) #filename
        dte.extend(entropy.stringtodat('"' + self.ext + '"')) #ext and flags
        dte.extend([0, 0, 0, 0, 0, 0]) #times
        dte.extend([0, self.len]) #size in words
        dte.append(self.fs) #first sector
        dte.append(0) #unused
        return dte

    def getcontents(self, parentdte):
        return self.contents + [0] * (self.slen * 512 - self.len)

    def setoffset(self, amount):
        self.fs = amount if self.len > 0 else 65535

    def getfslist(self):
        return [(self.fs, self.name.strip('\0') + '.' + self.ext.strip('\0'))]

class diskdir:
    def __init__(self, diskname):
        self.name = (diskname + '\0' * 8)[:8]
        self.contents = []
        self.len = 16
        self.slen = 1
        self.fs = 0
        self.diskitems = []
        self.changed = True

    def getfslist(self):
        r = [(self.fs, self.name.strip('\0') + '.dir')]
        for di in self.diskitems:
            r.extend(di.getfslist())
        return r

    def getdte(self):
        dte = []
        dte.extend(entropy.stringtodat('"' + self.name + '"')) #filename
        dte.extend(entropy.stringtodat('"dir"')) #ext
        dte[-1] = dte[-1] | 16 #flags
        dte.extend([0, 0, 0, 0, 0, 0]) #times
        dte.extend([0, len(self.diskitems) * 16 + 16]) #size in words
        dte.append(self.fs) #first sector
        dte.append(0) #unused
        return dte

    def additem(self, diskitem, path = ''):
        if path:
            path = path.replace('\\', '/')
            sl = path.find('/')
            if sl >= 0:
                ndir = (path + '\0' * 8)[:min(sl, 8)]
                npath = path[sl + 1]
            else:
                ndir = (path + '\0' * 8)[:8]
                npath = ''
            for di in self.diskitems:
                if type(di) == diskdir and di.name == ndir:
                    di.additem(diskitem, npath)
                    break
            else:
                print('Warning: Invalid ondisk path: ' + ndir)
        else:
            self.diskitems.append(diskitem)
            self.len = (len(self.diskitems) + 1) * 16
            self.slen = ((len(self.diskitems)) >> 5) + 1 #-1+1
        self.changed = True

    def setoffset(self, amount):
        self.fs = amount
        for i in range(len(self.diskitems)):
            self.diskitems[i].setoffset(amount + self.fsecs[i])

    def getfsecs(self):
        self.changed = False
        self.slens = []
        self.fsecs = []
        for di in self.diskitems:
            self.fsecs.append(sum(self.slens) + self.slen)
            if type(di) == diskfile:
                self.slens.append(di.slen)
            elif type(di) == diskdir:
                self.slens.append(di.getfsecs())
            di.setoffset(self.fsecs[-1])
        return sum(self.slens) + self.slen

    def getfsecs2(self):
        if self.changed:
            return self.getfsecs()
        else:
            return sum(self.slens) + self.slen

    def getfat(self):
        self.getfsecs2()
        fat = []
        if self.diskitems:
            fat.extend(range(self.fs + 1, self.fs + self.slen))
            fat.append(65535)
        for di in self.diskitems:
            if type(di) == diskfile:
                if di.slen > 0:
                    fat.extend(range(di.fs + 1, di.fs + di.slen))
                    fat.append(65535)
            elif type(di) == diskdir:
                if di.slen > 0:
                    fat.extend(di.getfat())
        return fat

    def getcontents(self, parentdte):
        self.getfsecs2()
        r = parentdte
        #DTE table
        for di in self.diskitems:
            r.extend(di.getdte())
        r.extend([0] * (self.slen * 512 - len(r)))

        #contents
        for di in self.diskitems:
            r.extend(di.getcontents(self.getdte()))
        return r

    def getcontents2(self):
        self.getfsecs2()
        #FAT table
        r = self.getfat()
        r.extend([0] * (1536 - len(r)))
        #DTE table
        #data
        r.extend(self.getcontents(self.getdte()))
        return r
                

usedd = False
usebe = False

print('Press enter to load default configuration.')
print('Type characters for other configurations.')
print('d = use disk_data.dasm, b = use big endian.')
config = input('usr>')
if 'd' in config: usedd = True
if 'b' in config: usebe = True

if True:
    try:
        entropy = assembler('../src/Kernel/main.dasm', True)
        if not entropy.success:
            print('Entropy main file missing!')
            print('\n====== BUILD FAILED ======\n')
            nul = input('Press enter to continue...')
            exit()
        diskdata = assembler('../src/Kernel/disk_data.dasm', True)
        if not diskdata.success:
            print('disk_data.dasm missing, diskdata option unavailable')
            usedd = False
        disklist = entropy.readfile('disklist.txt')
        filedata = []
        if not disklist:
            print('disklist.txt not found, no files were added.')

        rs = ((len(entropy.words) - 1) >> 9) + 1
        out = []
        out.append(0xc382)      #bootflag
        out.append(0x164a)      #filesystem descriptor
        out.extend(entropy.stringtodat('"EntropyLive\0"')) #disk name
        out.append(rs)          #reserved sectors
        out.append(1)           #number of FAT tables
        out.append(512)         #words per sector
        out.append(1440)        #number of sectors on disk
        out.append(random.randint(0, 65535))
        out.append(random.randint(0, 65535))
        out.append(random.randint(0, 65535))
        out.append(random.randint(0, 65535)) #random disk ID
        out.extend(entropy.words[16:]) #entropy code
        out.extend([0] * (512 * rs - len(out))) #filler
        if usedd:
            out.extend(diskdata.words)
        elif disklist:
            root = diskdir('')
            for i in disklist:
                if '"' in i or "'" in i:
                    args = entropy.stringre.findall(i)
                    args = [x[1:-1] for x in args]
                else:
                    args = entropy.notwsre.findall(i)
                com = args[0] if len(args) > 0 else ''
                file = args[1] if len(args) > 1 else ''
                path = args[2] if len(args) > 2 else ''
                if com == 'bin':
                    file = '../bin/' + file
                    tmp = entropy.readbin(file)
                    if tmp:
                        root.additem(diskfile(stripdir(file), tmp.words), path)
                    else:
                        print('Failed to access file: ' + i)
                elif com == 'file':
                    file = '../src/' + file
                    tmp = assembler(file, True)
                    if tmp.success:
                        root.additem(diskfile(stripdir(file), tmp.words), path)
                elif com == 'dir':
                    root.additem(diskdir(file), path)
                else:
                    print('Could not interpret disklist entry: ', i)
            out.extend(root.getcontents2())
            if True:
                sl = []
                sl.append((0, 'Entropy'))
                sl.append((rs, 'FAT'))
                sl += [(a + rs + 3, b) for a, b in root.getfslist()]
                sl.append((len(out) // 512, 'empty'))
                for i in range(len(sl) - 1):
                    for j in range(sl[i][0], sl[i + 1][0]):
                        print('Sector' + format(j, '4') + ' contains: ' + sl[i][1])
                        
        if not entropy.writebin('../bin/entropy.img', out, not usebe):
            print('Could not access output file: ../bin/entropy.img')
            print('\n====== BUILD FAILED ======\n')
            nul = input('Press enter to continue...')
        else:
            print('\n====== BUILD SUCCESS ======\n')
    except:
        print('\n====== BUILD FAILED ======\n')
        nul = input('Press enter to continue...')
        raise
    nul = input('Press enter to continue...')

