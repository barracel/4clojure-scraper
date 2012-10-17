import itertools
import pickle
import re
import sys

from BeautifulSoup import BeautifulSoup
from gevent import local
from gevent import monkey
from gevent.pool import Pool
import requests
import os

monkey.patch_all()

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
            return (num_problem, None)
        soup = BeautifulSoup(res.text)
        return (num_problem, soup.find('pre').text)

    def scrap_problem(self, num_problem):
        print 'p', num_problem
        rsession = self._rsession()
        res = rsession.get('https://www.4clojure.com/problem/%s' %
                           num_problem,
                           verify=False)
        fulltext = str(BeautifulSoup(res.text).find('div',
                                                    {'id': 'prob-desc'}))
        text = re.match('<div id="prob-desc">(.*)<br', fulltext).group(1)
        return (num_problem, text)

def do_scrap(num_problems, user, password):
    scraper = Scraper(user, password)
    p = Pool(20)
    problems = list(p.imap_unordered(scraper.scrap_problem,
                                     range(0, num_problems)))
    solutions = list(p.imap_unordered(scraper.scrap_solution,
                                      range(0, num_problems)))
    solutions = [s for s in solutions if s[1]]
    save(problems, solutions)
    return problems, solutions

def save(*args):
    with open('./data.pickle', 'w') as f:
        pickle.dump(args, f)

def load():
    with open('./data.pickle') as f:
        return pickle.load(f)

def main(user, password):
    problems, solutions = do_scrap(200, user, password)
    #problems, solutions = load()
    problems = dict(problems)
    solutions = sorted(solutions, key=lambda x: x[0])
    return problems, solutions

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print "Usage: python %s user password" % os.path.basename(__file__)
        sys.exit(1)
    problems, solutions = main(*sys.argv[1:3])
