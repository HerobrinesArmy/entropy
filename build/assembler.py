import re
import optparse

class assembler:
    #TOOLS
    
    def readfile(self, file):
        try:
            with open(file, 'r') as f:
                return f.readlines()
        except IOError:
            return None

    def writefile(self, file, lines, end = '\n'):
        try:
            with open(file, 'w') as f:
                for line in lines:
                    f.write(line + end)
            return True
        except IOError:
            return False

    def readbin(self, file, le = True):
        try:
            with open(file, 'rb') as f:
                b = list(f.read())
        except IOError:
            return None
        r = []
        for i in range(len(b) // 2):
            r.append((b[2 * i], b[2 * i + 1]))
        if le:
            return [a * 256 + b for a, b in r]
        else:
            return [a * 256 + b for b, a in r]

    def writebin(self, file, binary, le = True):
        r = []
        if le:
            for i in binary:
                r.append(i >> 8 & 255)
                r.append(i & 255)
        else:
            for i in binary:
                r.append(i & 255)
                r.append(i >> 8 & 255)
        try:
            with open(file, 'wb') as f:
                f.write(bytes(r))
            return True
        except IOError:
            return False

    def stripcomments(self, s):
        scl = re.sub(self.stringre,
                     lambda x: len(x.group(0)) * '-', s).find(';')
        return s.strip() if scl == -1 else s[:scl].strip()

    def adderr(self, error):
        self.errors.append((error, self.file, self.lineno))

    def addwarn(self, warning):
        self.warnings.append((warning, self.file, self.lineno))

    def adddefine(self, key, expression):
        key = key.lower()
        if key in self.defines or key in self.labels or key in self.macros:
            self.adderr('Duplicate key: ' + key)
            return False
        self.defines[key] = expression.lower()
        self.definelocs[key] = (self.file, self.lineno)
        return True
        
    def addlabel(self, key):
        key = key.lower()
        if key[0] == '.':
            key = self.namespace + key
        else:
            self.namespace = key
        if key in self.labels or key in self.defines or key in self.macros:
            self.adderr('Duplicate key: ' + key)
            return False
        self.labels[key] = self.wordno
        self.labellocs[key] = (self.file, self.lineno)
        return True

    def addmacro(self, key, args, lines):
        key = key.lower()
        if key in self.defines or key in self.labels or key in self.macros:
            self.adderr('Duplicate key: ' + key)
            return False
        self.macros[key] = (args, lines)
        self.macrolocs[key] = (self.file, self.lineno)
        return True

    def datlines(self):
        i = 0
        r = []
        while i < len(self.words):
            t = 'dat '
            t += ', '.join([self.tohex(x) for x in self.words[i:i + 8]])
            r.append(t)
            i += 8
        return r

    def listing(self):
        lines = []
        i = -1
        while i < len(self.words) - 1:
            i += 1
            for l, n in list(self.labels.items()):
                if n == i:
                    lines.append(self.tohex(i) + '   label: :' + l)
            line = self.tohex(i) + '  source: '
            line += self.stripcomments(self.getline(self.wordinfo[i]))
            line = line.replace('\t', ' ')
            if self.wordinfo[i - 1:i] != self.wordinfo[i:i + 1]:
                if len(line) < 48:
                    line += ' ' * (48 - len(line)) + 'data: '
                    line += self.tohex(self.words[i])
                    lines.append(line)
                else:
                    lines.append(line)
                    lines.append(self.tohex(i) + '    data: ' + \
                                 self.tohex(self.words[i]))
            elif len(lines[-1]) < 72:
                lines[-1] += ', ' + self.tohex(self.words[i])
            else:
                lines.append(self.tohex(i) + '    data: ' + \
                             self.tohex(self.words[i]))
        return lines

    def tohex(self, h, i = 4):
        return '0x' + '0' * (i - len(hex(h)) + 2) + hex(h)[2:]

    def checkassembly(self):
        def tolen(s, i):
            return s + ' ' * (i - len(s))

        last = 0
        lastf = self.wordinfo[0][0]
        i = -1
        while i < len(self.words) - 1:
            i += 1
            if lastf != self.wordinfo[i][0]:
                last = 0
                lastf = self.wordinfo[i][0]
            for l, n in list(self.labels.items()):
                if n == i:
                    print(self.tohex(i) + ': :' + l)
            if self.wordinfo[i][1] == last:
                continue
            r = self.tohex(i) + ': '
            tmp = self.disassemble(self.words[i:i + 3])[0]
            r += tolen(tmp[0], 24)
            while last < self.wordinfo[i][1] - 1:
                last += 1
                t = ' ' * 24 + self.getline(self.wordinfo[i][0], last).strip()
                if t.strip():
                    print(t)
            r += self.getline(self.wordinfo[i]).strip()
            last += 1
            nul = input(r)

    def compareassembly(self, file, t = 0):
        def tolen(s, i):
            return s + ' ' * (i - len(s))
        
        bina = self.words
        binb = self.readbin(file, self.BE)
        i = -1
        j = -1
        o = 0
        while i < min(len(bina), len(binb)):
            i += 1
            j = i + o
            r = self.tohex(i) + ': '
            ta = self.disassemble(bina[i:i + 3])[0]
            tb = self.disassemble(binb[j:j + 3])[0]
            l = ta[2]
            r += tolen(''.join([self.tohex(x)[2:] for x in bina[i:i + l]]), 14)
            r += tolen(ta[0], 22)
            r += tolen(''.join([self.tohex(x)[2:] for x in binb[j:j + l]]), 14)
            r += tolen(tb[0], 22)
            if r[8:44] == r[44:] or i < t:
                print(r)
                inp = ''
            else:
                inp = input(r)
            if inp == '+':
                o += 1
            elif inp == '-':
                o -= 1
            i += l - 1
            
            
    def getline(self, file, line = None):
        if line == None:
            line = file[1]
            file = file[0]
        line -= 1
        if file in self.filelines:
            if line < len(self.filelines[file]):
                return self.filelines[file][line]
            else:
                return ''
        else:
            tmp = self.readfile(file)
            if tmp == None:
                return ''
            else:
                self.filelines[file] = tmp
                if line < len(tmp):
                    return tmp[line]
                else:
                    return ''

    def checkcode(self):
        i = -1
        l = len(self.words)
        msgs = []
        while i < l - 1:
            i += 1
            w = self.words[i]
            op = w & 31
            b = (w >> 5) & 31
            a = (w >> 10) & 63
            if 'nw' in self.values[a]:
                i += 1
                a2 = self.words[i]
            else: a2 = None
            if op and 'nw' in self.values[b]:
                i += 1
                b2 = self.words[i]
            else: b2 = None
            if op == 0:
                #special opcode
                op = b
                if op in [16]:
                    if a > 30:
                        msgs.append(('Trying to assign to a literal', i))
                if op in [12]:
                    if a == 31:
                        msgs.append(('Shortform can be used here', i))
            else:
                #normal opcode
                if op < 16 or op > 23:
                    if b > 30:
                        msgs.append(('Trying to assign to a literal', i))
                if op == 1:
                    if a == b and a2 == b2:
                        msgs.append(('Assigning value to itself', i))
        for i in msgs:
            print(self.wordinfo[i[1]][0],
                  str(self.wordinfo[i[1]][1]) + ': ' + i[0])
                

    def disassemble(self, source, start = 0):
        r = []
        i = start - 1
        while i < len(source) - 1:
            i += 1
            o = i
            op = source[i] & 31
            b = (source[i] >> 5) & 31
            a = (source[i] >> 10) & 63
            sop = self.opcodes[op]
            if sop == 'spc':
                sop = self.spcops[b]
                if sop == 'nul':
                    r.append(('dat ' + self.tohex(source[i]), o, i - o + 1))
                    continue
                sa = self.values[a]
                if 'nw' in sa:
                    i += 1
                    if i == len(source):
                        return r
                    sa = sa.replace('nw', str(self.tohex(source[i], 1)))
                r.append((sop + ' ' + sa, o, i - o + 1))
            elif sop == 'nul':
                r.append(('dat ' + self.tohex(source[i]), o, i - o + 1))
            else:
                sa = self.values[a]
                sb = self.values[b]
                if sa == 'poppush':
                    sa = 'pop'
                if sb == 'poppush':
                    sb = 'push'
                if 'nw' in sa:
                    i += 1
                    if i == len(source):
                        return r
                    sa = sa.replace('nw', str(self.tohex(source[i], 1)))
                if 'nw' in sb:
                    i += 1
                    if i == len(source):
                        return r
                    sb = sb.replace('nw', str(self.tohex(source[i], 1)))
                r.append((sop + ' ' + sb + ', ' + sa, o, i - o + 1))
        return r

    def stringtodat(self, string):
        # "" two chars per word
        # '' one char per word
        # l'' p'' length-prefixed
        # ''0 ''n ''z ''c null-terminated
        # returns a string with a list of numbers
        # TODO: Add escape characters
        lenpf = False
        nterm = False
        o = string
        if string in ['""', "''"]:
            self.addwarn('Empty string did not produce any result')
            return ''
        if string[0] in 'lp':
            lenpf = True
            string = string[1:]
        if string[-1] in '0nzc':
            nterm = True
            string = string[:-1]
        if string[0] not in '"\'' or string[0] != string[-1]:
            self.adderr('String format unknown: ' + o)
            return ''
        r = [ord(i) for i in string[1:-1]]
        l = len(r)
        if nterm:
            r.append(0)
        if string[0] == '"':
            #two chars per word
            s = []
            if len(r) % 2 == 1:
                r.append(0)
            for i in range(len(r) // 2):
                s.append((r[2 * i] << 8) + r[2 * i + 1])
            if lenpf:
                s = [l] + s
            return s
        else:
            #one char per word
            if lenpf:
                r = [l] + r
            return r
    
    def printreport(self):
        if not self.errors and not self.warnings:
            print('Assembly successful!')
        elif not self.errors:
            for w in self.warnings:
                print(w[1] + ' line ' + str(w[2]) + ': ' + w[0])
            print('\nAssembly successful, but there were ' +
                  str(len(self.warnings)) + ' warnings.')
        else:
            for e in self.errors:
                print(e[1] + ' line ' + str(e[2]) + ': ' + e[0])
            print('\nAssembly failed, there were ' + str(len(self.errors)) +
                  ' errors.')

    def printlines(self):
        b = [print(i[0]) for i in self.lines]

    regpm = re.compile(r'(.*\+)?\s*([abcxyzij])\s*([+-].*)?\Z')
    def argval(self, arg, a = False):
        if arg[0] == '[' and arg[-1] == ']':
            #[ arg ]
            arg = arg[1:-1].strip()
            if arg in self.vals2:
                return (self.vals2[arg],)
            m = self.regpm.match(arg)
            if m:
                g = [m.group(1), m.group(2), m.group(3)]
                if g[0] == None and g[2] == None:
                    return 0
                tmp1 = 0 if g[0] == None else self.parse(g[0].strip()[:-1])
                tmp2 = 0 if g[2] == None else self.parse(g[2].strip()[1:])
                if tmp1 == None or tmp2 == None: return 1
                g[2] = '+' if g[2] == None else g[2].strip()
                r = 'abcxyzij'.index(g[1])
                if g[2][0] == '+':
                    return (r + 16, (tmp1 + tmp2) % 65536)
                else:
                    return (r + 16, (tmp1 - tmp2) % 65536)
            if a: m = re.match(r'sp\s*\+\+\Z', arg)
            else: m = re.match(r'--\s*sp\Z', arg)
            if m: return (24,)
            m = re.match(r'\s*sp\s*([+-])(.*)', arg)
            if m:
                tmp = self.parse(m.group(2))
                if tmp == None: return 1
                else:
                    if m.group(1) == '+':
                        return (26, tmp % 65536)
                    else:
                        return (26, (65536 - tmp) % 65536)
            tmp = self.parse(arg)
            if tmp == None: return 1
            return (30, tmp)
        else:
            #arg
            if (arg == 'pop' and not a) or (arg == 'push' and a):
                return 0
            if arg in self.vals1:
                return (self.vals1[arg],)
            m = re.match(r'pick\s+(.*)', arg)
            if m:
                tmp = self.parse(m.group(1))
                if tmp == None: return 1
                else: return (26, tmp % 65536)
            tmp = self.parse(arg)
            m = self.keyre.search(' ' + arg)
            if tmp == None: return 1
            else:
                tmp = tmp % 65536
                if a and (tmp <= 30 or tmp == 65535) \
                   and not m and not self.longform:
                    return ((tmp + 33) % 65536,)
                else:
                    return (31, tmp)
            return 0
    
    def arglen(self, arg, a = False):
        #arg is assumed to be .strip().lower()ed
        r = 0
        l = self.keyre.findall(' ' + arg)
        for i in l:
            if i not in self.reserved:
                return 1
        #when a define key is found, the length will be set to one, even if
        #that key would have evaluated between -1 and 30, as it should be.

        #We know there is no label or define now.
        if re.search(r'(?:0x[0-9a-fA-F]+)|(?:-?[0-9]+)', arg):
            if a and self.numm.match(arg) and not self.longform:
                n = int(arg, 0)
                while n < 0:
                    n += 65536
                if n <= 30 or n == 65535:
                    return 0
        else:
            return 0
        return 1

    def codelen(self, code, errs = False):
        if code == 'sti':
            return (1, 'sti a, a')
        if code == 'std':
            return (1, 'std a, a')
        if code == 'rfi':
            return (1, 'rfi a')
        op = code[:3]
        if len(code) < 4:
            if op in self.opcodes:
                if errs: self.adderr('Expected two arguments: ' + code)
                return None
            if op in self.spcops:
                if errs: self.adderr('Expected one argument: ' + code)
                return None
            if op == 'dat':
                if errs: self.addwarn('Empty dat statement.')
                return None
            if errs: self.adderr('Could not understand: ' + code)
            return None
        if code[3] not in ' \t':
            if errs: self.adderr('Could not understand: ' + code)
            return None
        if op == 'dat':
            return (code.count(',') + 1, 'dat ' +
                    ', '.join([s.strip() for s in code[4:].split(',')]))
        if op == 'nul':
            if errs: self.adderr('Could not understand: ' + code)
            return None
        if op in self.opcodes:
            #basic opcode
            if code.count(',') > 1:
                if errs: self.adderr('Expected two arguments: ' + code)
                return None
            comma = code.find(',')
            if comma == -1:
                if errs: self.adderr('Expected two arguments: ' + code)
                return None
            argb = code[4:comma].strip()
            arga = code[comma + 1:].strip()
            if argb == '' or arga == '':
                if errs: self.adderr('Expected two arguments: ' + code)
                return None
            return (1 + self.arglen(argb) + self.arglen(arga, True),
                    op + ' ' + argb + ', ' + arga)
        if op in self.spcops:
            #advanced opcode
            if code.count(',') > 0:
                if errs: self.adderr('Expected one argument: ' + code)
                return None
            arga = code[4:].strip()
            if arga == '':
                if errs: self.adderr('Expected one argument: ' + code)
                return None
            return (1 + self.arglen(arga, True), op + ' ' + arga)
        if errs: self.adderr('Could not understand: ' + code)
        return None

    def reset(self):
        self.namespace = ''
        self.errors = []        #(error, file, lineno)
        self.warnings = []      #(warn, file, lineno)
        self.lines = []         #(line, file, lineno)
        self.defines = {}       #expr or val
        self.labels = {}        #wordno
        self.definelocs = {}    #(file, lineno)
        self.labellocs = {}     #(file, lineno)
        self.macrolocs = {}     #(file, lineno)
        self.file = ''
        self.lineno = 0
        self.basefile = ''
        self.words = []
        self.wordinfo = []      #(file, lineno)
        self.filelines = {}     #dictionary of filelines
        self.macros = {}        #((args), (lines))
        self.success = False
        self.longform = False
        self.makefooter = False
        self.footerlist = []    #wordno's of words in need of relocation

    #CONSTANTS
    opcodes = ['spc', 'set', 'add', 'sub', 'mul', 'mli', 'div', 'dvi',
               'mod', 'mdi', 'and', 'bor', 'xor', 'shr', 'asr', 'shl',
               'ifb', 'ifc', 'ife', 'ifn', 'ifg', 'ifa', 'ifl', 'ifu',
               'nul', 'nul', 'adx', 'sbx', 'nul', 'nul', 'sti', 'std']
    spcops = ['nul', 'jsr', 'nul', 'nul', 'nul', 'nul', 'nul', 'nul',
              'int', 'iag', 'ias', 'rfi', 'iaq', 'nul', 'nul', 'nul',
              'hwn', 'hwq', 'hwi', 'nul', 'nul', 'nul', 'nul', 'nul',
              'nul', 'nul', 'nul', 'nul', 'nul', 'nul', 'nul', 'nul']
    values = ['a', 'b', 'c', 'x', 'y', 'z', 'i', 'j',
              '[a]', '[b]', '[c]', '[x]', '[y]', '[z]', '[i]', '[j]',
              '[a+nw]', '[b+nw]', '[c+nw]', '[x+nw]',
              '[y+nw]', '[z+nw]', '[i+nw]', '[j+nw]',
              'poppush', 'peek', '[sp+nw]', 'sp', 'pc', 'ex', '[nw]', 'nw'] + \
              [str(i) for i in range(-1, 31)]
    reserved = ['a', 'b', 'c', 'x', 'y', 'z', 'i', 'j', 'pc', 'sp', 'ex',
                'peek', 'pick', 'push', 'pop']
    vals1 = {'a': 0, 'b': 1, 'c': 2, 'x': 3, 'y': 4, 'z': 5, 'i': 6, 'j': 7,
             'pop': 24, 'push': 24, 'peek': 25, 'sp': 27, 'pc': 28,
             'ex': 29}
    vals2 = {'a': 8, 'b': 9, 'c': 10, 'x': 11, 'y': 12, 'z': 13,
             'i': 14, 'j': 15, 'sp': 25}
    LE = True
    BE = False

    #REGULAR EXPRESSIONS
    numm = re.compile(r'(?:(?:0x[0-9a-f]+)|(?:-?[0-9]+))\Z')
    stringre = re.compile(r'(?:"(?:[^"\\]|(?:\\.))*")|' +
                          r"(?:'(?:[^'\\]|(?:\\.))*')")
    stringm = re.compile(r'(?:"(?:[^"\\]|(?:\\.))*")|' +
                         r"(?:'(?:[^'\\]|(?:\\.))*')\Z")
    strpre = re.compile(r'(?:[lp]?"(?:[^"\\]|(?:\\.))*"[0nzc]?)|' +
                          r"(?:[lp]?'(?:[^'\\]|(?:\\.))*'[0nzc]?)")
    strpm = re.compile(r'(?:[lp]?"(?:[^"\\]|(?:\\.))*"[0nzc]?)|' +
                         r"(?:[lp]?'(?:[^'\\]|(?:\\.))*'[0nzc]?)\Z")
    localre = re.compile(r'(?<=[^A-Za-z0-9_.])\.[A-Za-z_.][A-Za-z0-9_.]*' +
                         r'(?=[^A-Za-z0-9_.]|\Z)')
    keyre = re.compile(r'(?<=[^A-Za-z0-9_.])[A-Za-z_.][A-Za-z0-9_.]*' +
                       r'(?=[^A-Za-z0-9_.]|\Z)')
    keym = re.compile(r'[A-Za-z_.][A-Za-z0-9_.]*\Z')
    labelm = re.compile(r'(?:(:[A-Za-z_.][A-Za-z0-9_.]*)(?:(?:[\s]+(.*))|\Z))')
    label2m = re.compile(r'(?:([A-Za-z_.][A-Za-z0-9_.]*:)(?:(?:[\s]+(.*))|\Z))')
    wsre = re.compile(r'[\s]+')
    notwsre = re.compile(r'[^\s]+')
    datm = re.compile(r'(?:((?::[a-z_.][a-z0-9_.]*)|' +
                      r'(?:[a-z_.][a-z0-9_.]*:))\s+)?\.?dat\s', re.IGNORECASE)
    definem = re.compile(r'[.#]define\s', re.IGNORECASE)
    reservem = re.compile(r'[.#]reserve\s', re.IGNORECASE)
    includem = re.compile(r'[.#]include\s', re.IGNORECASE)
    macrom = re.compile(r'[.#]macro\s', re.IGNORECASE)
    endmacrom = re.compile(r'[.#]endmacro', re.IGNORECASE)
    alignm = re.compile(r'[.#]align\s', re.IGNORECASE)
    longformm = re.compile(r'[.#]longform', re.IGNORECASE)
    shortformm = re.compile(r'[.#]shortform', re.IGNORECASE)
    binfooterm = re.compile(r'[.#]binfooter', re.IGNORECASE)
    endfooterm = re.compile(r'[.#]endfooter', re.IGNORECASE)
    
    def __init__(self, file = None, verbose = False):
        self.reset()
        self.verbose = verbose
        if file:
            if verbose:
                print('Chaotic Assembler is assembling: ' + file)
            self.basefile = file
            self.file = file
            self.lines = self.loadfile()
            if self.lines == 'empty':
                print('Assembly failed, the file is empty.')
            elif self.lines == None:
                print("Assembly failed, couldn't access the file.")
            else:
                self.checkmacros()
                self.checkdefines(False)
                self.getlabels()
                self.checkdefines()
                self.assemble()
                if not self.errors and not self.warnings:
                    self.success = True
                if verbose:
                    self.printreport()

    def loadfile(self):
        lines = self.readfile(self.file)
        if lines == None:
            return None
        if lines == []:
            return 'empty'
        r = []
        toskip = 0
        self.lineno = 0
        for line in lines:
            self.lineno += 1
            line = self.stripcomments(line)
            if toskip:
                toskip -= 1
                continue
            if not line:
                continue
            while line[-1] == '\\' and self.lineno + toskip < len(lines):
                line = line[:-1] + self.stripcomments(lines[self.lineno +
                                                            toskip])
                toskip += 1
            if self.includem.match(line):
                newfile = self.stringre.search(line, 9)
                if line[9:].strip() == '':
                    self.adderr('Missing argument: ' + line)
                    continue
                elif not newfile:
                    self.adderr('String expected: ' + line)
                    continue
                newfile = newfile.group(0)
                file = self.file
                lineno = self.lineno
                folder = max(file.rfind('/'), file.rfind('\\'))
                folder = file[:folder + 1] if folder >= 0 else ''
                self.file = folder + newfile[1:-1]
                newr = self.loadfile()
                self.lineno = lineno
                self.file = file
                if newr == None:
                    self.adderr('File could not be accessed: ' + newfile)
                    continue
                elif newr == 'empty':
                    self.addwarn('File is empty: ' + newfile)
                    continue
                else:
                    r.extend(newr)
                    continue
            elif self.definem.match(line):
                args = self.notwsre.findall(line, 8)
                if len(args) == 0:
                    self.adderr('Missing arguments: ' + line)
                elif (not self.keym.match(args[0])) or args[0] in self.reserved:
                    self.adderr('Invalid key: ' + args[0])
                elif len(args) == 1:
                    self.adderr('Value or expression expected: ' + line)
                else:
                    self.adddefine(args[0], ' '.join(args[1:]))
                continue
            m = self.datm.match(line)
            if m: #.dat
                e = m.group(1) + ' ' if m.group(1) else ''
                line = self.strpre.sub(
                    lambda x: str(self.stringtodat(x.group(0)))[1:-1], line)
                line = e + 'dat ' + line[len(m.group(0)):]
            r.append([line.lower(), self.file, self.lineno])
        return r

    def checkmacros(self):
        #find all macro definitions
        toskip = 0
        i = -1
        todel = []
        for line, self.file, self.lineno in self.lines:
            i += 1
            if toskip != 0:
                toskip -= 1
                continue
            if self.macrom.match(line):
                line = line[6:].strip()
                pl = line.find('(')
                if pl == -1:
                    name = line
                    args = []
                else:
                    name = line[:pl].strip()
                    args = [x.strip() for x in line[pl + 1:-1].split(',')]
                try:
                    while not self.endmacrom.match(self.lines[i + toskip][0]):
                        toskip += 1
                    if self.lines[i + toskip][0][9:].strip() != '':
                        self.addwarn('Did not evaluate after .endmacro' +
                                     self.lines[i + toskip][0][9:].strip())
                except IndexError:
                    self.adderr('Could not find .endmacro for: ' + line)
                    todel.append(i)
                    continue
                mlines = self.lines[i + 1:i + toskip]
                todel.extend(range(i, i + len(mlines) + 2))
                if not name:
                    self.adderr('Incorrect macro definition: ' + line)
                self.addmacro(name, args, mlines)
        todel.sort(reverse = True)
        for i in todel:
            del self.lines[i]
        #replace all macro calls
        for key in self.macros:
            argn = str(len(self.macros[key][0]) - 1)
            if argn == '-1':
                reg = re.compile(key + r'(?:\s*\(\s*\)\s*)?\Z')
            else:
                reg = re.compile(key + r'\s*\((' + r'(?:[^,],){' + argn + 
                                 r'}[^,]*)\)\Z')
            i = -1
            while True:
                i += 1
                if i == len(self.lines):
                    break
                m = reg.match(self.lines[i][0])
                if m:
                    if argn == '-1':
                        self.lines[i:i + 1] = self.macros[key][1]
                    else:
                        self.lines[i:i + 1] = self.parsemacro(key,
                                                              m.group(1).split(','))

    def parsemacro(self, key, args):
        argnames, lines = self.macros[key]
        for k in range(len(argnames)):
            reg = re.compile(r'(?<=[^A-Za-z0-9_.])' + argnames[k] +
                             r'(?=[^A-Za-z0-9_.]|\Z)')
            for i in range(len(lines)):
                lines[i][0] = reg.sub(args[k], ' ' + lines[i][0])[1:]
        return lines

    def checkdefines(self, unknownerrs = True):
        for key in self.defines:
            self.file, self.lineno = self.definelocs[key]
            tmp = self.parse(key, [], unknownerrs)
            if tmp != None and not unknownerrs:
                reg = re.compile(r'(?<=[^A-Za-z0-9_.])' + key +
                                 r'(?=[^A-Za-z0-9_.]|\Z)')
                rep = str(self.defines[key])
                for i in range(len(self.lines)):
                    self.lines[i][0] = reg.sub(rep, ' ' + self.lines[i][0])[1:]

    def getlabels(self):
        i = -1
        lines = []
        self.wordno = 0
        for line, self.file, self.lineno in self.lines:
            i += 1
            while True:
                line = line.strip()
                if not line:
                    break
                match = self.labelm.match(line)
                if not match:
                    match = self.label2m.match(line)
                if match:
                    if match.group(1)[0] == ':':
                        self.addlabel(match.group(1)[1:])
                    else:
                        self.addlabel(match.group(1)[:-1])
                    if match.group(2):
                        line = match.group(2)
                        continue
                    else:
                        line = ''
                        break
                if self.reservem.match(line):
                    tmp = self.parse(line[9:], [], False)
                    if tmp and tmp > 0:
                        line = 'dat 0' + ', 0' * (tmp - 1)
                        self.wordno += tmp
                        break
                    elif tmp and tmp == 0:
                        addwarn('Redundant statement: .reserve 0')
                        line = ''
                        break
                    elif tmp:
                        adderr("Can't reserve a negative amount: " + tmp)
                        line = ''
                        break
                    else:
                        adderr('Could not solve expression: ' + line[9:])
                        line = ''
                        break
                elif self.alignm.match(line):
                    tmp = self.parse(line[7:], [], False)
                    if tmp and tmp < self.wordno:
                        adderr("Can't align to a previous address: " + tmp)
                        line = ''
                        break
                    elif tmp and tmp == self.wordno:
                        addwarn('Redundant .align to current address')
                        line = ''
                        break
                    elif tmp:
                        line = 'dat 0' + ', 0' * (tmp - self.wordno - 1)
                        self.wordno = tmp
                        break
                    else:
                        adderr('Could not solve expression: ' + line[7:])
                        line = ''
                        break
                elif self.longformm.match(line):
                    if line[9:].strip() != '':
                        self.addwarn('Did not evaluate after .longform' +
                                     line[9:].strip())
                    if self.longform:
                        self.addwarn('Redundant .longform, already in ' +
                                     'longform mode.')
                        line = ''
                    else:
                        self.longform = True
                        line = '#longform'
                    break
                elif self.shortformm.match(line):
                    if line[10:].strip() != '':
                        self.addwarn('Did not evaluate after .shortform' +
                                     line[10:].strip())
                    if not self.longform:
                        self.addwarn('Redundant .shortform, already in ' +
                                     'shortform mode.')
                        line = ''
                    else:
                        self.longform = False
                        line = '#shortform'
                    break
                elif self.binfooterm.match(line):
                    if line[10:].strip() != '':
                        self.addwarn('Did not evaluate after .binfooter' +
                                     line[10:].strip())
                    if self.makefooter:
                        self.addwarn('Already generating binfooter.')
                    else:
                        self.makefooter = True
                    line = ''
                    break
                elif self.endfooterm.match(line):
                    if line[10:].strip() != '':
                        self.addwarn('Did not evaluate after .endfooter' +
                                     line[10:].strip())
                    if not self.makefooter:
                        self.addwarn("Wasn't generating binfooter.")
                    else:
                        self.footerlist.extend([32, 0,
                                                len(self.footerlist) + 3])
                        line = 'dat ' + ', '.join(str(x) for x in
                                                  self.footerlist)
                        self.wordno += self.footerlist[-1]
                        self.footerlist = []
                        self.makefooter = False
                    break
                #add namespace to lines
                line = self.localre.sub(lambda m: self.namespace + m.group(0),
                                        ' ' + line)[1:]
                if line[0:1] != '#':
                    tmp = self.codelen(line, True)
                    if tmp:
                        if self.makefooter:
                            args = line[4:].split(',')
                            wno = -1
                            for arg in args:
                                wno += 1
                                tmp2 = self.keyre.findall(' ' + arg)
                                if any(x not in self.reserved for x in tmp2):
                                    self.footerlist.append(self.wordno + wno)
                        self.wordno += tmp[0]
                        line = tmp[1]
                    else:
                        line = ''
                break
            if line:
                lines.append([line, self.file, self.lineno])
        self.lines = lines
    
    def parse(self, expr, tried = [], unknownerrs = True):
        keys = self.keyre.findall(' ' + expr)
        if not keys:
            try:
                r = eval(expr)
            except (TypeError, SyntaxError, NameError):
                self.adderr('Failed to parse: ' + expr)
                return None
            return int(r)
        for key in keys:
            if key in self.reserved:
                self.adderr('Invalid key: ' + key)
                return None
            if key in tried:
                self.adderr('Recursive defenition detected: ' + key)
                return None
            if key in self.labels:
                expr = re.sub(r'(?<=[^A-Za-z0-9_.])' + key +
                       r'(?=[^A-Za-z0-9_.])', str(self.labels[key]),
                       ' ' + expr + ' ')[1:-1]
                continue
            elif key in self.defines:
                if type(self.defines[key]) != type(3):
                    tried.append(key)
                    tmp = self.parse(self.defines[key], tried, unknownerrs)
                    if tmp == None:
                        return None
                    else:
                        self.defines[key] = tmp
                expr = re.sub(r'(?<=[^A-Za-z0-9_.])' + key +
                              r'(?=[^A-Za-z0-9_.])', str(self.defines[key]),
                              ' ' + expr + ' ')[1:-1]
                continue
            else:
                if unknownerrs:
                    self.adderr('Unknown label detected: ' + key)
                return None
        try:
            r = eval(expr)
        except (TypeError, SyntaxError, NameError):
            self.adderr('Failed to parse: ' + expr)
            return None
        return int(r)

    def assemble(self):
        #ASSUME:
        #opc argb, arga
        #dat arg, arg, arg, arg, ...
        def check(a, m):
            if a == 0 or a == 1:
                self.adderr('Failed to parse: ' + m)
                return [0] * (a + 1)
            return a
        for line, self.file, self.lineno in self.lines:
            if line == '#shortform':
                self.longform = False
                continue
            elif line == '#longform':
                self.longform = True
                continue
            op = line[:3]
            if op == 'dat':
                args = line[4:].split(', ')
                for arg in args:
                    tmp = self.parse(arg)
                    if tmp == None:
                        self.words.append(0)
                        self.wordinfo.append((self.file, self.lineno))
                    else:
                        self.words.append(tmp)
                        self.wordinfo.append((self.file, self.lineno))
                continue
            comma = line.find(', ')
            if comma == -1:
                arga = line[4:]
                argb = ''
            else:
                argb = line[4:comma]
                arga = line[comma + 2:]
            if op in self.opcodes:
                o = self.opcodes.index(op)
                b, a = self.argval(argb), self.argval(arga, True)
                a = check(a, arga)
                b = check(b, argb)
                self.words.append(o + 32 * b[0] + 1024 * a[0])
                self.wordinfo.append((self.file, self.lineno))
                if len(a) == 2:
                    self.words.append(a[1])
                    self.wordinfo.append((self.file, self.lineno))
                if len(b) == 2:
                    self.words.append(b[1])
                    self.wordinfo.append((self.file, self.lineno))
            if op in self.spcops:
                o = self.spcops.index(op)
                a = self.argval(arga, True)
                a = check(a, arga)
                self.words.append(32 * o + 1024 * a[0])
                self.wordinfo.append((self.file, self.lineno))
                if len(a) == 2:
                    self.words.append(a[1])
                    self.wordinfo.append((self.file, self.lineno))
        assert self.wordno == len(self.words)



if __name__ == '__main__':
    dowait = True
    parser = optparse.OptionParser()
    parser.add_option('-q', '--quiet', action='store_true',
        help="don't print errors, warnings or status messages")
    parser.add_option('-b', '--bigendian', action='store_true',
        help="use big endian instead of little endian for output")
    parser.add_option('-d', '--datfile', action='store_true',
        help="create a file with dat statements instead of a binary file")
    parser.add_option('-l', '--listing', metavar='PATH',
        help="write a listing file to PATH")
    options, args = parser.parse_args()

    if len(args) == 1:
        infile = args[0]
        tmp = args[0].rfind('.')
        outfile = (args[0][:tmp] if tmp != -1 else args[0]) + '.bin'
        dowait = False
    elif len(args) < 2:
        infile = input('Enter input file: ')
        outfile = input('Enter output file: ')
    else:
        infile = args[0]
        outfile = args[1]

    a = assembler(infile, not options.quiet)
    success = a.success
    if success:
        if options.datfile:
            if a.writefile(outfile, a.datlines()):
                print('Dat file stored in: ' + outfile)
            else:
                print('Unable to access: ' + outfile)
                success = False
        else:
            if a.writebin(outfile, a.words, not options.bigendian):
                print('Binary stored in: ' + outfile)
            else:
                print('Unable to access: ' + outfile)
                success = False
        if options.listing:
            if a.writefile(options.listing, a.listing()):
                print('Listing file stored in: ' + options.listing)
            else:
                print('Unable to access: ' + options.listing)
                success = False

    if dowait and success:
        input('Press enter to continue...')



