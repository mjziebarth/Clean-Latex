# Utility code used in multiple scripts.

def remove_comments(infile, outfile):
    """
    Parse a LaTeX file `infile`, remove comments, and
    write to `outfile`.
    """
    can_have_empty = False
    for line in infile:
        if '\\%' in line:
            split = line.strip().split('\%')
            recombine = []
            for s in split:
                if '%' in s:
                    recombine += [s.split('%')[0] + "%"]
                    break
                else:
                    recombine += [s]
            line = '\\%'.join(recombine)
        else:
            if "%" in line:
                line = line.strip().split('%')[0] + "%"
            else:
                line = line.strip()
        if len(line) > 0:
            can_have_empty = True
            outfile.write(line + '\n')
        elif can_have_empty:
            outfile.write('\n')
            can_have_empty = False

def getscope(string, i0, begin='{',end='}'):
    """
    Get the string and number within the scope starting at i0.
    """
    # Skip spaces:
    i1 = i0
    while i0 < len(string) and string[i0] in ('\n',' ','\t','%'):
        i0 += 1
    if i0 == len(string) or string[i0] != begin:
        print("STRING:",string)
        print("i0:",i0,"-->",string[i0] if i0 < len(string) else "<ERROR>")
        print("i1:",i1)
        print("len(string):",len(string))
        raise RuntimeError()
    level = 1
    i1 = i0+1
    N = len(string)
    escape = False
    while level > 0 and i1 < N:
        if escape:
            escape = False
        else:
            c = string[i1]
            if c == begin:
                level += 1
            elif c == end:
                level -= 1
            elif c == '\\':
                escape = True
        i1 += 1
    return string[i0+1:i1-1], i1

def evaluate_header(src, dest=None, defines=[], commands={}):
    r"""
    Read the header, collecting define-guards and command defines.
    Performs the following tasks:
      (1) Evaluate \ifdefined guards in the header, choosing alternatives
          according to the list of defines given in `defines` parameter.
      (2) Parse \newcommand and create a hierachic list of parameter evaluation.
          This allows to replace all customly defined parameters by their
          definition.
      (3) Parse \newenvironment. Same as above.

    Arguments:
       src:  File handle of a .tex file to read.

    Keyword arguments:
       dest:     File handle to write the processed .tex document to. Can be None
                 to not write the results to a file.
                 Default: None
       defines:  List of defines to evaluate the header \ifdefined structure.
                 Default: []
       commands: Dictionary of predefined commands.
                 Default: {}

    Returns:
       lines, commands, commands_order
    """
    lines = []
    command_order = []
    iftrue = [True]
    iflevel = 0
    prefix = ''

    # Check whether the \fi command is in the string:
    breaking_chars = ['\\', ' '] + [str(i)[0] for i in range(10)]
    def check_fi(string):
        if '\\fi' not in string:
            return False
        print("\\fi in string \"" + string + "\"")
        substr = string.split("\\fi")[1]
        if len(substr) == 0:
            return True
        return substr[0] in breaking_chars

    for line in src:
        line = line.replace("\n","")
        if '\\ifdefined' in line:
            if line.split('\\ifdefined')[1] in defines:
                iftrue.append(iftrue[iflevel])
            else:
                iftrue.append(False)
            iflevel += 1
            continue
        elif '\\else' in line:
            iftrue[iflevel] = not iftrue[iflevel]
            continue
        elif check_fi(line):
            iftrue.pop()
            iflevel -= 1
            continue
        if not iftrue[iflevel]:
            continue
        if '\\newcommand' in line:
            assert line[:11] == '\\newcommand'
            # Get the command name:
            s0,i0 = getscope(line,11)
            # Get optional argument number:
            if line[i0] == '[':
                sargs, i0 = getscope(line, i0, begin='[', end=']')
                nargs = int(sargs)
            else:
                nargs = 0
            # Get the command definition:
            s1 = getscope(line, i0)[0]

            commands[s0] = (nargs, s1)
            command_order += [s0]
        elif '\\newenvironment' in line:
            assert line[:15] == '\\newenvironment'
            # Get the environment name:
            s0,i0 = getscope(line,15)
            # Get optional argument number:
            if line[i0] == '[':
                sargs, i0 = getscope(line, i0, begin='[', end=']')
                nargs = int(sargs)
            else:
                nargs = 0
            # Get the command definitions:
            s1,i0 = getscope(line, i0)
            s2 = getscope(line, i0)[0]
            # Create commands:
            cmd_begin = "\\begin{" + s0 + "}"
            cmd_end = "\\end{" + s0 + "}"
            commands[cmd_begin] = (nargs, s1)
            command_order.append(cmd_begin)
            commands[cmd_end] = (0, s2)
            command_order.append(cmd_end)
        else:
            if iftrue[iflevel] and line != '%':
                lines.append(prefix + line)

    if dest is not None:
        with open(dest, 'w') as f:
            f.writelines(lines)

    return lines, commands, command_order


def replace_single_command(string, cmd, commands):
    """
    Replaces all instances of one single command in a
    document given as a string.
    """
    split = string.split(cmd)
    dnew = [split[0]]
    nargs = commands[cmd][0]
    for s in split[1:]:
        # First find the arguments:
        i0 = 0
        insert = commands[cmd][1]
        for i in range(nargs):
            if s[i0] == '[':
                arg, i0 = getscope(s, i0, begin='[', end=']')
            else:
                arg, i0 = getscope(s, i0)
            insert = insert.replace("#" + str(i+1), arg)
        dnew += [insert, s[i0:]]
    return "".join(dnew)


def replace_commands(document, command_order, commands,
                     command_dict_inplace=True):
    """
    Iteratively evaluates commands within a document.
    """
    if not command_dict_inplace:
        commands = {**commands}
    for i,cmd in enumerate(command_order):
        # Replace in document:
        document = replace_single_command(document, cmd, commands)
        # Replace in all following commands:
        for c2 in command_order[i+1:]:
            commands[c2] = (commands[c2][0],
                            replace_single_command(commands[c2][1], cmd,
                                                   commands))

    return document, commands


def replace_inline_math_mode(document, replace_by):
    """
    Replaces all instances of inline math mode in the document
    by the content given by `replace_by`, which might be either
    a string or a callable taking the content of the math mode.
    """
    split = document.split('$')
    N = len(split)
    docnew = []
    for i in range(0,N,2):
        # First the text:
        docnew.append(split[i])

        # Second the inline equation:
        if i+1 < N:
            if isinstance(replace_by, str):
                docnew.append(replace_by)
            else:
                docnew.append(replace_by(split[i+1]))
    return "".join(docnew)


def replace_environment(document, environment, replace_by):
    """
    Replaces all instances of an environment in the document
    by the content given by `replace_by`, which might be either
    a string or a callable taking the content of the environment.
    """
    # Shortcut:
    begin = "\\begin{" + environment + "}"
    end = "\\end{" + environment + "}"
    if begin not in document:
        return document

    split = document.split(begin)
    docnew = [split[0]]
    for s in split[1:]:
        if end not in s:
            raise RuntimeError("Document malformed with environment "
                               + environment + ".")
        if isinstance(replace_by,str):
            docnew.append(replace_by)
            docnew.append(s.split(end)[1])
        else:
            s2 = s.split(end)
            docnew.append(replace_by(s2[0]))
            docnew.append(s2[1])
    return "".join(docnew)
