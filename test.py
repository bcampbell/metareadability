#!/usr/bin/env python
from datetime import datetime
import metastuff
import urllib2
from optparse import OptionParser
import logging
import csv
import socket
import dateutil.parser

from urllib2helpers import CacheHandler


def tests_from_csv(filename):
    # url, headline, journo/byline, pubdate
    reader = csv.reader(open(filename, 'rb'))

    rows = [ row for row in reader ]
    n = 1
    try:
        for row in rows:
            row[1] = row[1].decode('utf-8')
            row[2] = row[2].decode('utf-8')
            if row[3].strip() == '':
                row[3] = None
            else:
                row[3] = dateutil.parser.parse(row[3])
            n+=1
    except:
        print "error in %s:%d"%(filename,n)
        raise
    return rows


def compare_result(got, expected, url):

    errs = []

    norm = metastuff.normalise_text
    #headline
    if got[0] is None or norm(got[0]) != norm(expected[0]):
        errs.append("title: got '%s', expected '%s'" % (got[0],expected[0]))
    #pubdate
    a = None if got[2] is None else got[2].date()
    b = None if expected[2] is None else expected[2].date()
    if a != b:
        errs.append(" date: got '%s', expected '%s'" % (got[2],expected[2]))

    if errs:
        logging.warning("failed %s" % (url,))
        [ logging.warning(" %s"%(err,)) for err in errs ]
        return False
    else:
        logging.debug("matched %s" % (url,))
        return True


def main():
    parser = OptionParser(usage="%prog: [options]")
    parser.add_option('-v', '--verbose', action='store_true')
    parser.add_option('-d', '--debug', action='store_true')
    parser.add_option('-u', '--url', help="only test urls containing URL")
    (options, args) = parser.parse_args()
 
    log_level = logging.ERROR
    if options.debug:
        log_level = logging.DEBUG
    elif options.verbose:
        log_level = logging.INFO

    logging.basicConfig(level=log_level, format='%(message)s')

    opener = urllib2.build_opener(CacheHandler('.cache'))
    urllib2.install_opener(opener)
    socket.setdefaulttimeout(5)

    test_data = tests_from_csv('./basic_tests.csv')


    good = 0
    bad = 0
    skipped = 0

    for row in test_data:
        url = row[0]
        expected = row[1:]

        if options.url and options.url not in url:
            continue

        if url.endswith(".pdf"):
            logging.info("SKIP pdf: %s" %(url,))
            skipped += 1
            continue
#        print "fetching", url
        try:
            html = urllib2.urlopen(url).read()
        except urllib2.URLError, e:
            logging.info("URLError (%s) on %s" %(e,url))
            skipped += 1
            continue

        got = metastuff.extract(html,url)
#        print "got '%s' (expected %s) [ %s ]" %(got[1],expected[1],url)
#        continue
        logging.debug(got)

        if compare_result(got, expected, url):
            good += 1
        else:
            bad += 1

    print "finished: %d good, %d bad, %d skipped" % (good, bad, skipped)


if __name__ == '__main__':
    main()

