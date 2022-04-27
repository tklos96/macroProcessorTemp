#!i/usr/local/bin python3

import os, re
import argparse
try:
  from configparser import ConfigParser    #Python 3
except ImportError: pass

### Global Regular Expressions
string_char = "\""
comment_char = "!"
macro_keyword = 'M'
macro_regex = r'\s*@\s*' + re.escape(macro_keyword) + r'\s*\w*(?:\s*\(.*\))?'
invocation_regex = r'(?P<indent>\s*)@\s*' + re.escape(macro_keyword) + \
                   r'\s*(?P<key>\w*)(?:\s*\((?P<args>.*)\))?'


### General functions

# List files with a given suffix from a directory.
def filesWithSuffix(dirName,suffix):
    fileList = []
    if(os.path.isdir(dirName)):
        for f in os.listdir(dirName):
            fpath = os.path.join(dirName,f)
            if os.path.isfile(fpath) and fpath.endswith(suffix) :
                fileList.append(fpath)
    return fileList

# Strips given suffix
def removeSuffix(input_string, suffix):
    if suffix and input_string.endswith(suffix):
        return input_string[:-len(suffix)]
    return input_string

####################################################################

# An instance of macroProcessor stores several dictionaries, indexed
# by the list of strings in self.keylist.
class macroProcessor:
  def __init__(self):
    self.keylist = []
    self.mdict = {}
    self.argdict = {}
    self.typedict = {}
    self.indentdict = {}
    self.sourcedict = {}

  ######### LOADING DEFS ###########
  # Read a file and add contained macro definitions
  # to the macro dictionary.
  def loadDefs(self,filename):
    parser = ConfigParser(comment_prefixes=('#!','#!!'))
    parser.optionxform = lambda option: option # read keys case sensitively
    if filename is not None:
      dirName = os.path.dirname(os.path.abspath(filename))
      parser.read(filename)
      for section in parser.sections():
        if(section not in self.keylist):
            self.keylist.append(section)
            self.sourcedict[section] = dirName
        else:
            previousPath = self.sourcedict[section]

            # FLASHX SPECIFIC CODE
            if not (previousPath.startswith(dirName) or dirName.startswith(previousPath)):
                if not ('source/Simulation' in dirName or '/bin' in previousPath):
                    raise SyntaxError('{} defined in parellel directories, can\'t inherit properly'.format(section))
            # END FLASHXX CODE

            self.sourcedict[section] = dirName #overwrite keyword with def from new location

        self.mdict[section] = parser.get(section,'definition').strip()

        try:
            args = parser.get(section,'args')
            self.argdict[section] = [item.strip() for item in args.strip().split(',')]
        except:
            self.argdict[section] = []

        try:
            self.typedict[section] = parser.get(section,'type')
        except:
            self.typedict[section] = ''
        try:
            indents = parser.get(section,'line_indents').strip().split(',')
            self.indentdict[section] = [int(i) for i in indents]
        except:
            self.indentdict[section] = [0]

  # Load a whole list of files.
  def loadDefsList(self,filenames):
    for filename in filenames:
      self.loadDefs(filename)

  ####### EXPAND INVOCATIONS OF MACROS #############

  def getMacroDef(self,key,args=[],indent=''):
    # get definition and replace args
    definition =  self.mdict[key]
    arglist = self.argdict[key]
    for i,arg in enumerate(args):
      if(i<len(arglist) ):
        arg_re = r'\b'+arglist[i]+r'\b' #don't substitute substrings
        definition = re.sub( arg_re, arg, definition)

    # add appropriate indent to all lines
    def_lines = definition.split('\n')
    if (len(def_lines[0].strip()) > 0):
      if (def_lines[0].strip()[0] == '#'):
        #ensure preprocessor directives are not inserted inline
        def_lines[0] = '\n' + def_lines[0]
    j = 0 # track place in per-line indent list
    n = len(self.indentdict[key])
    for i in range(len(def_lines)):
      lineStripped = def_lines[i].strip()
      lead = indent + ' '*self.indentdict[key][j]
      if (len(lineStripped) > 0):
        if (lineStripped[0] == '#'):
          lead = ''
      def_lines[i] = lead + def_lines[i]
      if(j<n-1): j = j+1
    definition = '\n'.join(def_lines)

    return definition

  def expandMacro(self, invocation, macroStack):
    expansion = invocation
    keymatch = False

    # use regex to get parts of invocation
    invocation_parts = re.match(invocation_regex, invocation)
    macroName = invocation_parts.group('key')
    indent = invocation_parts.group('indent')

    # check to make sure recursive calls don't cause infinite loops
    if macroName in macroStack:
      mlist = ', '.join(macroStack)
      msg = "Error: macro(s): (%s) causing a loop via macro recursion."%mlist
      raise SyntaxError(msg)

    for key in self.keylist:
      if (macroName == key):
        args=[]
        if len(self.argdict[key])>0:
          argtext = invocation_parts.group('args')
          if argtext is None:
            msg = "Error: argument list expected for macro %s"%macroName
            raise SyntaxError(msg)

          #split on any comma not preceded by escape char %
          args_raw = re.split(r'(?<!%),',argtext)
          #get rid of escape characters
          args = [ re.sub(r'(?<!%)%','',arg) for arg in args_raw ]

        expansion = self.getMacroDef(macroName,args,indent)
        keymatch = True
        break

    # if expansion has a recursive macro, process lines again
    recursion = len(re.findall(macro_regex,expansion)) >0;
    if (recursion and keymatch):
      macroStack.append(macroName)
      expansionLines = expansion.split('\n')
      for i,line in enumerate(expansionLines):
        expansionLines[i] = self.processLine(line,macroStack)
      expansion = '\n'.join(expansionLines)

    return expansion


  ######### PROCESSING FILES  #################

  # Process a single line
  def processLine(self,lineIn,macroStack=None):
    if macroStack is None:
      macroStack = []

    lineOut = lineIn

    #scan line for comments and strip them
    lineStripped = lineIn
    inString = False
    for i,ch in enumerate(lineIn):
        if ch==string_char:
            inString = not inString
        if (ch==comment_char and not inString):
            lineStripped = lineIn[0:i]
            break

    if len(lineStripped.split())>=1:
      # find matches for macro invocation regex
      invocation_list = re.findall(macro_regex,lineStripped)

      # expand each invocation and replace
      for invocation in invocation_list:
        expansion = self.expandMacro(invocation,macroStack)
        lineOut = lineOut.replace(invocation, expansion, 1)

    return lineOut

  # Process a whole file
  def convertFile(self,filename,output):
    with open(output,'w') as f:
      lines = open(filename).readlines()
      for line in lines:
        f.write(self.processLine(line))
