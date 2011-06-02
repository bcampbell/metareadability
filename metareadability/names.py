import os
import re

_lastnames = None
_firstnames = None

def _read_names(filename):
    names = set()
    fp = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), filename), "r")
    for line in fp:
        name = line.decode('ascii').strip()
        names.add(name)
    return names

# won't handle accented chars, but hey.
_prettycase_pat = re.compile('^[A-Z][a-z]+$')

def rate_name(name):
    global _firstnames, _lastnames
    if _firstnames is None:
        _firstnames = _read_names('firstnames.txt')
    if _lastnames is None:
        _lastnames = _read_names('lastnames.txt')

    parts = name.split()
    if len(parts)==0:
        return 0.0
    score = 0.0
    if parts[0].lower() in _firstnames:
        score += 1.0

    if parts[-1].lower() in _lastnames:
        score += 1.0

    # cheesiness: consolation points for captialisation:
    if score <= 0.0 and _prettycase_pat.match(parts[0]) and _prettycase_pat.match(parts[-1]):
        score += 0.2

    return score / float(len(parts))


def main():
    import sys
    name = ' '.join(sys.argv[1:])
    print rate_name(name)

if __name__ == '__main__':
    main()


