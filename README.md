# Clean-Latex
Script for cleaning and preparing latex documents for journal submission.

This script was originally developed to prepare a latex document with custom
preamble for submission with an AGU journal. It parses commands in the preamble
and inserts them into the main text in a new clean document to comply with the
manuscript requirements. Figures in ```\includegraphics``` environments are
parsed and collectively copied into a folder together with the clean latex
document. The bibliography file is parsed and cited entries are copied into
a new compact bibliography file. Finally, comments are removed and a bit of
formatting is applied.

The script works with the [Revision](https://github.com/mjziebarth/Revise) package.

The script is not well tested. Be careful.

## Call Signature
```sh
python clean-latex.py -i INPUT.tex -o OUTPUT.tex -d OUTDIR --defines=\DEF1,\DEF2
```
Output files will be created within the ```OUTDIR```. Defines are optional.
