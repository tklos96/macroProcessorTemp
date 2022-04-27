#!/usr/local/bin python3

import os
import argparse

from macroProcessorBase import *

# This is the file that can be run in shell to convert a whole directory
def processDirectory(inDir,outDir,defsList,varList):
    outList = []

    mp = macroProcessor()
    mp.loadDefsList( defsList )

    mcFiles = filesWithSuffix(inDir,'-mc')
    for f in mcFiles:
        outFile = removeSuffix(f,'-mc')
        mp.convertFile(f, outFile)
        outList.append(outFile)

    return outList


def main():
    parser=argparse.ArgumentParser(description='Macro Processor')
    parser.add_argument('processDir', nargs='*',default=[os.getcwd()],help='convert all files in this dir')
    parser.add_argument('--outdir','-o',type=str,help='output directory')
    parser.add_argument('--variant','-var',type=str,help='include defs from a variant (subdirectory)')
    parser.add_argument('-p',action='store_true',help='print output to stdout')
    args=parser.parse_args()

    for d in args.processDir:
        print('Processing macros in directory: {}'.format(d))
        if args.outdir is None:
            out = d
        else:
            out = args.outdir

        iniFiles = filesWithSuffix(d,'.ini')
        if(args.variant is not None):
            iniFiles += filesWithSuffix(os.path.join(d,args.variant),'.ini')

        outList = processDirectory(d,out,iniFiles,[])

        if(args.p):
            for f in outList:
                header = 'CONTENTS OF TRANSLATED FILE: {}'.format(os.path.abspath(f))
                line = ''.join(  ['-' for _ in range(len(header)) ]  )

                print(header)
                print(line)
                os.system('cat {}'.format(f))
                print()



if __name__ == '__main__':
    main()
