#!/bin/python
# Python script for performing a latex document word count
# as required, for instance, by 'Earth and Planetary Science Letters'.

import argparse
import os
from tempfile import TemporaryFile
from libclean import remove_comments, evaluate_header, replace_commands, \
                     replace_inline_math_mode, replace_environment
parser = argparse.ArgumentParser()
parser.add_argument('-i', action='store', type=str)
#parser.add_argument('-o', action='store', type=str)
#parser.add_argument('-d', action='store', type=str)
parser.add_argument('--defines', action='store', type=str, default="")
parser.add_argument('--count-section-headings', action='store_true')
parser.add_argument('--count-appendix', action='store_true')
parser.add_argument('--count-figure-captions', action='store_true')
parser.add_argument('--count-table-captions', action='store_true')
args = parser.parse_args()

# Parsing the arguments:
FILE = args.i
OUTFILE = FILE + ".wordcount.tmp.tex"
DEFINES = ["\\"+d for d in args.defines.split(",")]
REMOVE_FIGURES = not args.count_figure_captions
REMOVE_TABLES = not args.count_table_captions
CL_REVISION_COMMANDS = True
COUNT_REFERENCES = True # If true, count one word for each reference.
COUNT_FOOTNOTES = False
COUNT_INLINE_MATHMODE = True # If true, count one word for each inline math mode
COUNT_SEPARATE_MATHMODE = True # If true, count extra mathmode (e.g. align)
COUNT_SECTIONS = args.count_section_headings # If true, count words in section headings.
REMOVE_APPENDIX = not args.count_appendix # If true, remove the appendix from word count.
KEEP_TMP_OUTFILE = False # If true, keep temporary output file


if KEEP_TMP_OUTFILE:
    raise NotImplementedError()

# Remove comments:
with TemporaryFile(mode='w+') as out:
    with open(FILE, 'r') as f:
        remove_comments(f, out)


    ############################################################################
    # 2. Define some commands which should not have an effect on word count,   #
    #    or for which the effect should be specified:                          #
    ############################################################################
    co_predef = ["\\color","\\textbf","\\texttt","\\textit","\\citep","\\citet",
                 "\\label", "\\ref", "\\includegraphics", "\\maketitle",
                 "\\citeauthor", "\\caption"]
    commands = {"\\color" : (1,""), "\\textbf" : (1,"#1"), "\\texttt" : (1,"#1"),
                "\\textit" : (1,""), "\\label" : (1,""), "\\ref": (1,"REF"),
                "\\includegraphics" : (2,""), "\\maketitle" : (0,""),
                "\\caption" : (1,"#1")}
    if COUNT_REFERENCES:
        commands |= {"\\citep" : (1,"(#1)"), "\\citet" : (1,"#1, (YEAR)"),
                     "\\citeauthor" : (1,"#1")}
    else:
        commands |= {"\\citep" : (1,""), "\\citet" : (1,""),
                     "\\citeauthor" : (1,"#1")}

    # - environments:
    co_predef.extend(["\\begin{center}", "\\end{center}","\\begin{itemize}",
                      "\\end{itemize}", "\\item", "\\begin{enumerate}",
                      "\\end{enumerate}"])
    commands |= {"\\begin{center}" : (0,""), "\\end{center}" : (0,""),
                 "\\begin{itemize}" : (0,""), "\\end{itemize}" : (0,""),
                 "\\item" : (0,""), "\\begin{enumerate}" : (0,""),
                 "\\end{enumerate}" : (0,"")}

    #  - footnotes:
    co_predef += ["\\footnote"]
    if COUNT_FOOTNOTES:
        commands |= {"\\footnote" : (1," #1 ")}
    else:
        commands |= {"\\footnote" : (1,"")}

    #  - Section headings:
    co_predef += ["\\chapter","\\section","\\section*","\\subsection","\\subsection*",
                  "\\subsubsection","\\subsubsection*"]
    if COUNT_SECTIONS:
        commands |= {x : (1,"#1") for x in ("\\chapter","\\section","\\section*","\\subsection",
                                            "\\subsection*","\\subsubsection","\\subsubsection*")}
    else:
        commands |= {x : (1,"") for x in ("\\chapter","\\section","\\section*","\\subsection",
                                          "\\subsection*","\\subsubsection","\\subsubsection*")}


    ############################################################
    # 3. Parse header, evaluate ifdefines and custom commands: #
    ############################################################
    out.seek(0)
    if CL_REVISION_COMMANDS:
        commands |= {"\\replaced" : (2,'#2'), "\\added" : (1, '#1'),
                     "\\deleted" : (1,''), "\\replacedincaption" : (2, '#2'),
                     "\\addedincaption" : (1, "#1"),
                     "\\deletedincaption" : (1, ""), "\\listofchanges" : (0, ""),
                     "\\replacedlabel" : (1,"\\label{#1}"),
                     "\\drafttrue" : (0,""), "\\countchange" : (0, "")}
    LINES, commands, command_order \
       = evaluate_header(out, defines=DEFINES, commands=commands)

command_order.extend(co_predef)

if CL_REVISION_COMMANDS:
    command_order += ["\\replaced", "\\added", "\\deleted",
                      "\\replacedincaption", "\\addedincaption",
                      "\\deletedincaption", "\\listofchanges","\\replacedlabel",
                      "\\drafttrue", "\\countchange"]
command_order = command_order[::-1]


# TODO this is a hotfix. Should be possible to specify optional argument numbers.
# Handle optional argument of \includegraphics:
document = "\n".join(LINES).replace('\includegraphics{','\includegraphics[scale=1]{')

# Replace the custom commands:
document, commands = replace_commands(document, command_order, commands)


################################
# 4. Reduce to document text:  #
################################
i = 0
document = document.split("\\begin{document}")[1].split("\end{document}")[0]


##################
# 5. Mathmode:   #
##################
if '$$' in document:
    raise NotImplementedError("Two-dollar math mode not implemented!")

if '$' in document:
    if COUNT_INLINE_MATHMODE:
        document = replace_inline_math_mode(document, "EQN")
    else:
        document = replace_inline_math_mode(document, "")

if COUNT_SEPARATE_MATHMODE:
    document = replace_environment(document, "align", "SEPARATEEQN")
else:
    document = replace_environment(document, "align", "")



##################################
# 6. Remove figures and tables:  #
##################################
nfig = document.count("\\begin{figure")
ntab = document.count("\\begin{table")
if REMOVE_FIGURES:
    document = replace_environment(document, "figure","")
    document = replace_environment(document, "figure*","")
else:
    document = replace_environment(document, "figure", lambda x : x)
    document = replace_environment(document, "figure*", lambda x : x)

if REMOVE_TABLES:
    document = replace_environment(document, "table","")
    document = replace_environment(document, "table*","")
else:
    document = replace_environment(document, "table", lambda x : x)
    document = replace_environment(document, "table*", lambda x : x)


########################
# 7. Remove appendix:  #
########################
if REMOVE_APPENDIX:
    document = document.split("\\appendix")[0]


################################################
# 8. Remove remaining braces and parantheses:  #
################################################
document = document.replace("{","").replace("}","").replace("(","")\
                   .replace(")","").replace("[","").replace("[","")\
                   .replace("]","").replace("\\","")
document = "\n".join(line for line in document.splitlines()
                     if len(line) > 0)



# Some splitting:
document = document.replace("\n"," ").replace(","," ").replace("?"," ")\
                   .replace("-"," ").strip()

##############################
# 9. Output the word count!  #
##############################
print("#words:  ",len(document.split()))
print("#figures:",nfig)
print("#tables: ",ntab)
