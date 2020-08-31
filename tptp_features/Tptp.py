from pathlib import Path
from pprint import pprint
import re

from collections import namedtuple

TptpProblem = namedtuple("TptpProblem", "group name file meta tptp")
TptpAxiom   = namedtuple("TptpAxiom", "name file meta tptp")

class TptpMetaParseException(Exception):
    pass

class Tptp:
    """Representing TPTP problem set"""

    def __init__(self, tptpdir):
        self.tptpdir = Path(tptpdir)
        self.problems = self.tptpdir.glob("Problems/*/*.p")
        self.problems = [
            TptpProblem(
                group=p.parent.stem, name=p.stem, file=p,
                meta=self._parse_meta(p), tptp=self)
            for p in self.problems]
        self.problems = {p.name: p for p in self.problems}

        self.axioms = self.tptpdir.glob("Axioms/**/*.ax")
        self.axioms = [
            TptpAxiom(
                name='/'.join(a.parts[1:-1] + (a.stem,)),
                file=a, meta=self._parse_meta(a), tptp=self)
            for a in self.axioms]
        self.axioms = {a.name: a for a in self.axioms}

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

            # Flatten metadata (needed?)
            for k, v in metadata.items():
                if len(v) == 1:
                    metadata[k] = v[0]

            return metadata

    def get_problems(self, metamatch=None):
        if not metamatch:
            yield from self.problems.values()
            return

        metamatch = {k: re.compile(v) for k, v in metamatch.items()}
        for problem in self.problems.values():
            matched = True
            for key, rx in metamatch.items():
                if not key in problem.meta:
                    matched = False
                    break

                text = str(problem.meta[key])
                if rx.fullmatch(text) is None:
                    matched = False
                    break

            if matched: yield problem

if __name__ == "__main__":
    import cProfile
    cProfile.run('t  = Tptp("../../tptp-parser/")')
    # for p in t.get_problems({'SPC': 'FOF_.*'}):
    #    print(p.meta['SPC'])
    #print(t.axioms.keys())
