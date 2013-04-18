#! /usr/bin/env python3.3

import os, platform

l = ['genericclock', 'sped3', 'spc2000', 'm35fd', 'lem1802', 'generickeyboard']
if platform.system() != "Windows":
    c = 'mono ../tools/Lettuce.exe ../bin/bootloader.bin --connect '
else:
    c = '..\\tools\\Lettuce.exe ../bin/bootloader.bin --connect '
with open('../build/devicelist.txt') as f:
    t = f.readlines()
t = t[0:len(l)]
t = [int(x[0:x.find(' ')]) for x in t]
for i in range(len(l)):
    c += (l[i] + ',') * t[i]
os.system(c[:-1])
