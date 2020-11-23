from pathlib import Path
from pprint import pprint
import re
import pickle
import logging
import os

from collections import namedtuple

TptpProblem = namedtuple("TptpProblem", "group name file tptp")
TptpAxiom   = namedtuple("TptpAxiom", "name file tptp")

TPTP_PY_CACHE_FILENAME = 'Tptp.py.cache.pickle'

class TptpException(Exception):
    pass

class TptpMetaParseException(Exception):
    pass

class Tptp:
    """Representing TPTP problem set"""

    def __init__(self, tptpdir=None):
        if (tptpdir is not None
                and Path(tptpdir).is_dir()
                and (Path(tptpdir) / 'Problems').is_dir()
                and (Path(tptpdir) / 'Axioms').is_dir()):
            self.tptpdir = Path(tptpdir)
        else:
            self.tptpdir = Path(os.environ['TPTP'])

        try:
            with (self.tptpdir / TPTP_PY_CACHE_FILENAME).open(mode='rb') as j:
                data = pickle.load(j)
                logging.debug(f"Loaded cache from {TPTP_PY_CACHE_FILENAME}")
                self.problems = data['problems']
                self.axioms = data['axioms']
        except EnvironmentError:
            self.problems = self.tptpdir.glob("Problems/*/*.p")
            self.problems = [
                TptpProblem(
                    group=p.parent.stem, name=p.stem, file=p,
                    tptp=tptpdir)
                for p in self.problems]
            self.problems = {p.name: p for p in self.problems}

            self.axioms = self.tptpdir.glob("Axioms/**/*.ax")
            self.axioms = [
                TptpAxiom(
                    #name='/'.join(a.parts[1:-1] + (a.stem,)),
                    name=a.stem, file=a, tptp=tptpdir)
                for a in self.axioms]
            self.axioms = {a.name: a for a in self.axioms}

            data = dict(problems=self.problems, axioms=self.axioms)
            with (self.tptpdir / TPTP_PY_CACHE_FILENAME).open(mode='wb') as j:
                pickle.dump(data, j, protocol=pickle.HIGHEST_PROTOCOL)
                logging.debug(f"Saved cache to {TPTP_PY_CACHE_FILENAME}")

    def parse_meta(self, problem):
        problem = Path(problem.file)
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
                metadata = self.parse_meta(problem)
                if not key in metadata:
                    matched = False
                    break

                text = str(metadata[key])
                if rx.fullmatch(text) is None:
                    matched = False
                    break

            if matched: yield problem

    def find_by_filename(self, problem_name):
        problem_name = Path(problem_name)
        problem_type = list(problem_name.parents)[-2].name
        try:
            if  problem_type == 'Axioms':
                return self.axioms[problem_name.stem]
            elif problem_type == 'Problems':
                return self.problems[problem_name.stem]
        except KeyError:
            pass # Exception will be raised below

        raise TptpException(f"Cannot find {problem_name}")

if __name__ == "__main__":
    import cProfile
    cProfile.run('t  = Tptp("../../tptp-parser/")')
    # for p in t.get_problems({'SPC': 'FOF_.*'}):
    #    print(p.meta['SPC'])
    #print(t.axioms.keys())
