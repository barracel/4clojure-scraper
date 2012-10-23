import collections
import functools
import itertools
import os
import pickle
import re
import sys
import textwrap

from BeautifulSoup import BeautifulSoup
from gevent import local
from gevent import monkey
from gevent.pool import Pool
import requests

monkey.patch_all()

Problem = collections.namedtuple('Problem', ('id', 'title', 'text'))
Solution = collections.namedtuple('Solution', ('id', 'text'))

class Scraper(object):
    local = local.local()

    def __init__(self, user, password):
        self.user = user
        self.password = password

    def _rsession(self):
        if not getattr(self.local, 'rsession', None):
            self.local.rsession = requests.session()
            payload = dict(user=self.user, pwd=self.password)
            self.local.rsession.post('https://www.4clojure.com/login',
                                data=payload, verify=False)
        return self.local.rsession

    def scrap_solution(self, num_problem):
        print 's', num_problem
        rsession = self._rsession()
        res = rsession.get('https://www.4clojure.com/problem/solutions/%s' %
                           num_problem,
                           verify=False)
        if "You must solve this problem" in res.text:
            return Solution(num_problem, None)
        soup = BeautifulSoup(res.text,
                             convertEntities=BeautifulSoup.HTML_ENTITIES)
        return Solution(num_problem, soup.find('pre').text)

    def scrap_problem(self, num_problem):
        print 'p', num_problem
        rsession = self._rsession()
        res = rsession.get('https://www.4clojure.com/problem/%s' %
                           num_problem,
                           verify=False)
        soup = BeautifulSoup(res.text,
                             convertEntities=BeautifulSoup.HTML_ENTITIES)
        titlediv = str(soup.find('div', {'id': 'prob-title'}))
        title = re.match('<div id="prob-title">(.*?)</div>', titlediv).group(1)
        textdiv = str(soup.find('div', {'id': 'prob-desc'}))
        text = re.match('<div id="prob-desc">(.*?)<br', textdiv).group(1)
        return Problem(num_problem, title, text)

def cache(func):
    @functools.wraps(func)
    def decorator(*args, **kwargs):
        call_args = ''.join(str(x) for x in itertools.chain(args,
                                                            kwargs.values()))
        cache_file = './.cache_%s' % hash(call_args)
        if os.path.exists(cache_file):
            return load(cache_file)
        ret = func(*args, **kwargs)
        save(ret, cache_file)
        return ret
    return decorator

def save(data, filename):
    with open(filename, 'w') as f:
        pickle.dump(data, f)

def load(filename):
    with open(filename) as f:
        return pickle.load(f)

@cache
def do_scrap(num_problems, user, password):
    scraper = Scraper(user, password)
    p = Pool(20)
    problems = list(p.imap_unordered(scraper.scrap_problem,
                                     range(0, num_problems)))
    solutions = list(s for s in p.imap_unordered(scraper.scrap_solution,
                                                 range(0, num_problems))
                     if s and s.text)
    return problems, solutions

template_src = """
; {problem.id}. {problem.title}
; https://www.4clojure.com/problem/{problem.id}
; {problem_text}

{solution.text}

"""
def src_lines(problems, solutions):
    for solution in solutions:
        problem_text = '\n; '.join(textwrap.wrap(problems[solution.id].text))
        yield template_src.format(problem=problems[solution.id],
                                  problem_text=problem_text,
                                  solution=solution)

def main(user, password, output_file):
    problems, solutions = do_scrap(290, user, password)
    problems = dict((p.id, p) for p in problems)
    solutions = sorted(solutions, key=lambda x: x[0])
    with open(output_file, 'w') as f:
        f.write('\n'.join(src_lines(problems, solutions)))
    return problems, solutions

if __name__ == '__main__':
    if len(sys.argv) < 4:
        print ("Usage: python %s user password output_file"
               % os.path.basename(__file__))
        sys.exit(1)
    problems, solutions = main(*sys.argv[1:4])
