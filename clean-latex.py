#!/bin/python
# Python script for cleaning the latex file. Originally
# developed to make a latex document with some adjusted
# commands comply with AGU's document submission policy.
#
# This script does a couple of things:
#  - Remove comments and whitespaces
#  - Expand the commands of the Revision module.
#  - Collect and expand newcommands and newenvironments
#    in the document preamble, and expand them in the
#    document.
#  - Do some linting (indent environments with tabs,
#    remove large amounts of whitespaces)

import argparse
import os
from shutil import copyfile
from libclean import remove_comments, getscope, evaluate_header,\
                     replace_commands
parser = argparse.ArgumentParser()
parser.add_argument('-i', action='store', type=str)
parser.add_argument('-o', action='store', type=str)
parser.add_argument('-d', action='store', type=str)
parser.add_argument('--defines', action='store', type=str, default="")
args = parser.parse_args()

FILE = args.i   #'pbpsha_paper.tex'
OUTFILE = args.o   # 'jgr-submit-clean.tex'
OUTDIR = args.d
DEFINES = tuple(args.defines.split(",")) #('\\agudraft',)

if FILE is None:
    raise RuntimeError("No input file given.")
elif OUTFILE is None:
    raise RuntimeError("No output file given.")
elif OUTDIR is None:
    raise RuntimeError("No output directory given.")

# Step 1: Remove all the comments:
with open(OUTFILE, 'w') as dest:
    with open(FILE, 'r') as f:
        remove_comments(f, dest)


########################################################
#                                                      #
#   Step 2: Obtain all the commands and remove them:   #
#                                                      #
########################################################

commands = {"\\replaced" : (2,'#2'), "\\added" : (1, '#1'), "\\deleted" : (1,''),
            "\\replacedincaption" : (2, '#2'), "\\addedincaption" : (1, "#1"),
            "\\deletedincaption" : (1, ""), "\\listofchanges" : (0, ""), "\\replacedlabel" : (1,"\\label{#1}"),
            "\\drafttrue" : (0,""), "\\countchange" : (0, "")}


with open(OUTFILE, 'rw') as f:
    LINES, commands, command_order \
       = evaluate_header(f, defines=DEFINES, commands=commands)

# Append the revision commands and reverse order:
command_order += ["\\replaced", "\\added", "\\deleted", "\\replacedincaption", "\\addedincaption",
                  "\\deletedincaption", "\\listofchanges","\\replacedlabel","\\drafttrue",
                  "\\countchange"]
command_order = command_order[::-1]


##########################################
#                       
#   Step 3: Replace iteratively all commands:
#
################################################

document, commands = replace_commands("\n".join(LINES), command_order, commands)

with open(OUTFILE, "w") as f:
    f.write(document)




##########################
#                        #
#   Step 4: Formatting   #
#                        #
##########################
lines_in = document.split("\n")
lines_out = []
in_document = False
prefix = ""
previous_empty = True
previous_endbegin = False
in_empty_environment = 0
for line in lines_in:
    end_comment = len(line) > 0 and line[-1] == '%' and \
                  (len(line) == 1 or line[-2] != '\\')
    if end_comment:
        line = line[:-1]
    empty = len(line) == 0
    if empty:
        if end_comment:
            # Line consists solely of '%'. Skip.
            continue
        elif previous_empty:
            # Skip multiple empty lines and take only the first:
            continue
        elif previous_endbegin:
            # The previous is an \end{...} or \begin{...} command. Skip empty lines
            # afterwards:
            continue
        elif not in_document:
            # Within preamble, skip all empty lines:
            continue
        elif in_empty_environment > 0:
            # In some environments (e.g. Figures), remove empty lines.
            continue
    previous_empty = False
    previous_endbegin = False
    suffix = '%' if end_comment else ''
    if '\\begin{document}' in line:
        in_document = True
        lines_out += [(line + suffix, False)]
        prefix += "\t"
    elif '\\end{document}' in line:
        prefix = prefix[:-1]
        lines_out += [(line + suffix, False)]
        previous_end = True
    elif '\\begin' in line:
        # Check for some empty environmets:
        if "\\begin{figure" in line:
            in_empty_environment += 1
        # Remove previous empty lines:
        while lines_out[-1][1]:
            del lines_out[-1]
        lines_out += [(prefix + line + suffix, False)]
        prefix += "\t"
        previous_endbegin = True
    elif '\\end' in line:
        # Check for some empty environmets:
        if "\\end{figure" in line:
            in_empty_environment -= 1
        # Remove previous empty lines:
        while lines_out[-1][1]:
            del lines_out[-1]
        prefix = prefix[:-1]
        lines_out += [(prefix + line + suffix, False)]
        previous_endbegin = True
    else:
        lines_out += [(prefix + line + suffix, empty)]
    if empty:
        previous_empty = True


document = "\n".join(s[0] for s in lines_out)
with open(OUTFILE, "w") as f:
    f.write(document)



########################################
#
#   Step 5: Create the bibliography.
#
########################################
split = document.split("\\bibliography")
if len(split) == 2:
    bibfile, i1 = getscope(split[1], 0)
    split[1] = split[1][i1:]
    print("bibliography:",bibfile)
    
    # Read the bibliography:
    bibliography = dict()
    with open(bibfile, 'r') as f:
        entry = None
        entrylines = []
        for line in f:
            line = line.strip()
            if len(line) == 0 or line[0] == '%':
                continue
            if line[0] == '@':
                assert '{' in line
                assert line[-1] == ','
                if entry is not None:
                    bibliography[entry] = entrylines
                entry = line.split('{')[1].split(',')[0]
                entrylines = [line]
            elif line[0] == '%':
                continue
            else:
                entrylines += [line]

        if entry is not None:
            bibliography[entry] = entrylines
        print("entries:",sorted(list(bibliography.keys())))

    # Obtain cited entries:
    cited = {k: e for k,e in bibliography.items() if k in document}

    # Save the bibliography:
    newbib = OUTFILE.replace('.tex','.bib')
    with open(OUTDIR + "/" + newbib,'w') as f:
        for entry in sorted(list(cited.keys())):
            f.write("\n".join(cited[entry]))
            f.write("\n\n")

    # Use the new bibliography in the file:
    document = split[0] + "\\bibliography{" + newbib + "}" + split[1]
    with open(OUTFILE, "w") as f:
        f.write(document)





###############################################################
#                                                             #
#   Step 6: Create the output directory and copy all files.   #
#                                                             #
###############################################################
imagefiles = []
split = document.split("\\includegraphics")
extensions = ('','.pdf','.eps','.png','.jpg')
if len(split) > 1:
    for i,s in enumerate(split[1:]):
        # First obtain the path used in \includegraphics:
        if s[0] == '[':
            i0 = getscope(s,0,'[',']')[1]
        else:
            i0 = 0
        filename, i1 = getscope(s, i0, '{', '}')

        # Then test which file that points to:
        for ex in extensions:
            if os.path.isfile(filename + ex):
                break

        # Create the new filename:
        newfilename = filename.split('/')[-1]

        # Remember:
        imagefiles += [(filename, newfilename, ex)]

        # Insert the new filename:
        split[i+1] = "\\includegraphics" + s[:i0] + "{" + newfilename + "}" + s[i1:]

# Write the new document:
document = "".join(split)
os.makedirs(OUTDIR, exist_ok=True)
with open(OUTDIR + "/" + OUTFILE, "w") as f:
    f.write(document)

# Copy the files:
for f in imagefiles:
    src = f[0]+f[2]
    dst = OUTDIR + "/" + f[1] + f[2]
    copyfile(src, dst)
