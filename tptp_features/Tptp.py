from pathlib import Path
from pprint import pprint

from collections import namedtuple

TptpProblem = namedtuple("TptpProblem", "name file meta")

class TptpMetaParseException(Exception):
    pass

class Tptp:
    """Representing TPTP problem set"""

    def __init__(self, tptpdir):
        self.tptpdir = Path(tptpdir)
        self.problems = self.tptpdir.glob("Problems/*/*.p")
        self.problems = [TptpProblem(name=p.stem, file=p, meta=self._parse_meta(p)) for p in self.problems]
        self.problems = {p.name: p for p in self.problems}

    def _parse_meta(self, problem):
        problem = Path(problem)
        with problem.open() as f:
            l = f.readline()
            if not l.startswith('%-'):
                raise TptpMetaParseException('File does not begin with comment block')
            
            metadata = {}
            lastkey = None
            while not (l := f.readline().strip()).startswith('%-'):
                if not l:
                    continue

                if not (l.startswith('%')):
                    raise TptpMetaParseException('Comment block is malformed: {}, {}'.format(problem, l))

                l = l.lstrip('%')
                if l and l[0] == ' ':
                    l = l[1:]

                if l and not l.startswith(' '):
                    try:
                        lastkey, val = [i.strip() for i in l.split(':', maxsplit=1)]
                    except ValueError:
                        print(problem, l)
                        raise

                    metadata.setdefault(lastkey, []).append(val)
                else:
                    l = l.strip()
                    if l and l[0] == ':':
                        l = l[1:].strip()

                    metadata[lastkey].append(l.strip())

            # for k, v in metadata.items():
            #     if len(v) == 1:
            #         metadata[k] = v[0]

            return metadata


if __name__ == "__main__":
    t  = Tptp("../../tptp-parser/")
    pprint(t.problems['SET001-1'])