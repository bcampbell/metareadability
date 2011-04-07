import unicodedata
import re
import sys
import logging
import datetime
import urlparse

import lxml.html
import lxml.etree
import dateutil.parser

import fuzzydate

#import parsedatetime.parsedatetime as pdt

#from BeautifulSoup import BeautifulSoup, HTMLParseError, UnicodeDammit
#from BeautifulSoup import UnicodeDammit

from pprint import pprint

def tags( node, *tag_names):
    for tag_name in tag_names:
        for e in node.findall('.//%s' %tag_name):
            yield e


def normalise_text(txt):
    """ return stripped-down, ascii, alphanumeric-only version for comparisons """
    # replace various accented latin chars with rough ascii equivalents
    txt = unicodedata.normalize('NFKD',txt).encode('ascii','ignore')
    txt = re.sub(u'[^a-zA-Z0-9 ]',u'',txt)
    txt = u' '.join(txt.split())    # compress spaces
    txt = txt.lower().strip()
    return txt


def get_slug(url):
    """ return slug portion of url, or empty string '' """
    o = urlparse.urlparse(url)

    m = re.compile('((?:[a-zA-Z0-9]+[-_])+[a-zA-Z0-9]+)').findall(url)[-1:]
    if not m:
        return ''
    return m[0]




headline_pats = { 'classes': re.compile('entry-title|headline|title',re.I),
        'metatags': re.compile('^headline|og:title|title|head$',re.I),
        }

pubdate_pats = { 'metatags': re.compile('date|time',re.I),
    'classes': re.compile('published|updated|date|time',re.I),
    'url_datefmts': (
        re.compile(r'/(?P<year>\d{4})/(?P<month>\d{1,2})/(?P<day>\d{1,2})/',re.I),
        re.compile(r'[^0-9](?P<year>\d{4})-(?P<month>\d{1,2})-(?P<day>\d{1,2})[^0-9]',re.I),
        ),
    'comment_classes': re.compile('comment|respond',re.I),
    'pubdate_indicator': re.compile('published|posted|updated',re.I),
    }

byline_pats = { 'metatags': re.compile('',re.I),
    'classes': re.compile('byline|author|writer',re.I),
    'indicative': re.compile(r'^(by|written by)\b',re.I),
}


def extract(html,url):
    logging.debug("*** extracting %s ***" % (url,))
    doc = lxml.html.fromstring(html)

    [i.drop_tree() for i in tags(doc,'script','style')]

#    html = UnicodeDammit(html, isHTML=True).markup
    headline_info = extract_headline(doc,url)
    headline_linenum = 0
    headline = None
    if headline_info is not None:
        headline_linenum = headline_info['sourceline']
        headline = headline_info['txt']

    byline = extract_byline(doc,url,headline_linenum)
    pubdate = extract_pubdate(doc,url,headline_linenum)

    return headline,byline,pubdate



def extract_headline(doc,url):

    logging.debug("extracting headline")

    candidates = {}

    for h in tags(doc,'h1','h2','h3','h4','h5','h6','div'):
        score = 1
        txt = unicode(h.text_content()).strip()
        txt = u' '.join(txt.split())
        if len(txt)==0:
            continue


        txt_norm = normalise_text(txt)

        if len(txt)>=500:
            continue

        logging.debug(" headline: consider %s '%s'" % (h.tag,txt,))

        # TODO: should run all these tests over a real corpus of articles
        # and work out proper probability-based scoring!

        # TEST: length of headline
        # TODO - get a proper headline-length frequency curve from
        # journalisted and score according to probability
        if len(txt)>=20 and len(txt)<60:
            logging.debug("  len in [20,60)")
            score +=1
        elif len(txt)>=25 and len(txt)<40:
            logging.debug("  len in [25,40)")
            score += 2

        if h.tag in ('h1','h2','h3','h4'):
            logging.debug("  significant heading (%s)" % (h.tag,))
            score +=1

        # TEST: does it appear in <title> text?
        title = unicode(getattr(doc.find('.//title'), 'text', ''))
        if title is not None:
            if txt_norm in normalise_text(title):
                logging.debug("  appears in <title>")
                score += 3

        # TEST: likely-looking class or id
        if headline_pats['classes'].search(h.get('class','')):
            logging.debug("  likely class")
            score += 2
        if headline_pats['classes'].search(h.get('id','')):
            logging.debug("  likely id")
            score += 2


        # TEST: does it appear in likely looking <meta> tags?
        # eg:
        # <meta property="og:title" content="Dementia checks at age 75 urged"/>
        # <meta name="Headline" content="Dementia checks at age 75 urged"/>
        for meta in doc.findall('.//meta'):
            n = meta.get('name', meta.get('property', ''))
            if headline_pats['metatags'].search(n):
                meta_content = normalise_text(unicode(meta.get('content','')))
                if meta_content != '':
                    if txt_norm==meta_content:
                        logging.debug("  match meta")
                        score += 3
                    elif txt_norm in meta_content:
                        logging.debug("  contained by meta")
                        score += 1

        # TEST: does it match slug part of url?
        slug = re.split('[-_]', get_slug(url).lower())
        parts = [normalise_text(part) for part in txt.split()]
        parts = [part for part in parts if part!='']
        if len(parts) > 1:
            matched = [part for part in parts if part in slug]

            value = (5.0*len(matched) / len(parts)) # max 5 points
            if value > 0:
                logging.debug("  match slug (%01f)" % (value,))
                score += value

        # TODO: other possible tests
        # TEST: is it near top of article container?
        # TEST: is it just above article container?
        # TEST: is it non-complex html (anything more complex than <a>)
        # TEST: is it outside likely sidebar elements?

        if txt not in candidates or score > candidates[txt]:
            candidates[txt] = {'txt':txt, 'score':score, 'sourceline':h.sourceline}

    if not candidates:
        return None

    # sort
    out = sorted(candidates.items(), key=lambda item: item[1]['score'], reverse=True)

    #pprint(out[:5])
    return out[0][1]


#    regexpNS = "http://exslt.org/regular-expressions"
#    year_finder = lxml.etree.XPath(r"//*[(string-length(string())<50) and (re:test(., '\b\d\d\d\d\b', 'i'))]", namespaces={'re':regexpNS})
#    print "------"
#    for e in year_finder(doc):
#        print ">",e.text_content().strip()

#    print "------"



def extract_date(txt):

    # try the journalisted parser first
    fd = fuzzydate.parse_datetime(txt)
    if not fd.empty_date():
        if fd.day is None:
            fd.day = 1
        if fd.empty_time():
            return datetime.datetime(fd.year,fd.month,fd.day)
        else:
            if fd.second is None:
                fd.second = 0
            if fd.microsecond is None:
                fd.microsecond = 0
            return datetime.datetime(fd.year,fd.month,fd.day,fd.hour,fd.minute,fd.second,fd.microsecond,fd.tzinfo)
    return None

    # dateutil parser in fuzzy mode has an annoying habit of returning
    # current date when no date info can be extracted... probably
    # right for most cases, not here, since expect that a lot of what
    # we search _won't_ contain any date info.
    MAGIC_1 = datetime.datetime(1600,2,29) # a leap year :-)
    MAGIC_2 = datetime.datetime(1970,1,1)
    try:
        # parse it twice, so we can tell which fields have really changed... (ugh)
        dt1 = dateutil.parser.parse(txt, fuzzy=True, default=MAGIC_1)
        dt2 = dateutil.parser.parse(txt, fuzzy=True, default=MAGIC_2)
        # no year? no month? no deal.
        if dt1.year != dt2.year or dt1.month != dt2.month:
#            print "   BAIL '%s'" % (txt)
            return None
        # if it's only the day which is unset, then we'll accept it...
        if dt1.day != dt2.day:
            dt.day = 1

        return dt1
    except:
        pass
    return None




def extract_pubdate(doc, url, headline_linenum):
    candidates = {}

    logging.debug("extracting pubdate")

    # TODO: try some definitive meta tags first?
    # "DCSext.articleFirstPublished"
    # "DC.date.issued"
    # "last-modified"

    # check for date in slug
    for pat in pubdate_pats['url_datefmts']:
        m = pat.search(url)
        if m is not None:
            d = datetime.datetime( int(m.group('year')), int(m.group('month')), int(m.group('day')) )
            logging.debug("  using %s from url" % (d,))
            return d



    meta_dates = set()
    for meta in doc.findall('.//meta'):
        n = meta.get('name', meta.get('property', ''))
        if pubdate_pats['metatags'].search(n):
            try:
                meta_dates.add( dateutil.parser.parse(meta.get('content','')).date() )
            except ValueError:
                pass
#    if len(meta_dates)==1:
#        # only one likely-looking <meta> entry - lets go with it
#        d = list(meta_dates)[0]
#        logging.debug("  using %s from <meta>" % (d,))
#        return d

    # if we got this far, start looking through whole page
    for e in tags(doc,'p','span','div','li','td','h4','h5','h6'):
        txt = unicode(e.text_content()).strip()
        txt = u' '.join(txt.split())

        # discard anything too short or long
        if len(txt)<6 or len(txt) > 150:
            continue


        score = 1
        dt = extract_date(txt)
        if dt is None:
            continue
        logging.debug(" date: considering %s '%s'" % (e.tag,txt))

        # TEST: proximity to headline in html
        if headline_linenum>0 and e.sourceline>0:
            dist = e.sourceline - headline_linenum
            if dist >-5 and dist <10:
                logging.debug("  near headline")
                score += 1

        # TEST: likely class or id?
        if pubdate_pats['classes'].search(e.get('class','')):
            logging.debug("  likely class")
            score += 1
        if pubdate_pats['classes'].search(e.get('id','')):
            logging.debug("  likely id")
            score += 1
        # in byline is also a good indicator
        if byline_pats['classes'].search(e.get('class','')):
            logging.debug("  likely class")
            score += 1
        if byline_pats['classes'].search(e.get('id','')):
            logging.debug("  likely id")
            score += 1


        # TEST: also appears in likely <meta> tags?
        if dt.date() in meta_dates:
            logging.debug("  appears in <meta>")
            score += 1


        # TEST: not within likely-looking comment container?
        in_comment = False
        foo = e.getparent()
        while foo is not None:
            if pubdate_pats['comment_classes'].search(foo.get('class','')):
                in_comment = True
                break
            foo = foo.getparent()
        if not in_comment:
            logging.debug("  not inside likely comment")
            score += 1

        # TEST: indicative text? ("posted on" , "last updated" etc...)
        if pubdate_pats['pubdate_indicator'].search(txt):
            logging.debug("  text indicative of pubdate")
            score += 1

        # other tests:
        # TEST: month and year in url,  eg "http://blah.com/2010/08/blah-blah.html"
        pat = re.compile("%d[-_/.]?0?%d" % (dt.year,dt.month))
        if pat.search(url):
            logging.debug("  year and month appear in url")
            score += 1

        if dt.date() not in candidates or score>candidates[dt.date()]['score']:
            candidates[dt.date()] = {'datetime': dt, 'score': score}


    if not candidates:
        return None

    out = sorted(candidates.items(), key=lambda item: item[1]['score'], reverse=True)
#    print "========="
#    pprint( out[:5] )
#    print "========="
    return out[0][1]['datetime']


#<meta name="date" content="Tuesday, Mar. 29, 2011" />
#    length_cutoff = len("Wednesday September 23rd, 2010, 10:15:12 AM BST") + 5


 #       print pubdate



def extract_byline(doc, url, headline_linenum):
    candidates = {}

    logging.debug("extracting byline")

    # TODO: check meta tags
    for e in tags(doc,'p','span','div','h3','h4','li','td'):
        txt = unicode(e.text_content()).strip()
        txt = u' '.join(txt.split())

        # discard anything too short or long
        if len(txt)<7 or len(txt) > 200:
            continue

        logging.debug(" byline: consider %s '%s'" % (e.tag,txt))

        score = 0

        # TEST: indicative text? ('By ....')
        if byline_pats['indicative'].search(txt):
            logging.debug("  text indicative of byline")
            score += 2

        # TEST: likely-looking class or id
        if byline_pats['classes'].search(e.get('class','')):
            logging.debug("  likely class")
            score += 2
        if byline_pats['classes'].search(e.get('id','')):
            logging.debug("  likely id")
            score += 2

        # TEST proximity to headline
        if headline_linenum>0 and e.sourceline>0:
            dist = headline_linenum - e.sourceline
            if dist >-5 and dist <10:
                logging.debug("  near headline")
                score += 1

        # TODO
        # TEST: looks like a byline?
        #   split into names, check length
        # TEST: names are links?
        #   and hrefs look like bio pages?
        # TEST: byline length
        #   statistical check against JL data

        if score == 0:
            continue

        if txt not in candidates or score>candidates[txt]['score']:
            candidates[txt] = {'byline': txt, 'score': score}

    if not candidates:
        return None

    out = sorted(candidates.items(), key=lambda item: item[1]['score'], reverse=True)
#    print "========="
#    pprint( out[:5] )
#    print "========="
    return out[0][1]['byline']




def main():
    import urllib2
    from optparse import OptionParser
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

    for url in args:
        html = urllib2.urlopen(url).read()
        headline,byline,pubdate = extract(html,url)
        print "%s,%s,%s,%s" % (url,headline,byline,pubdate)

if __name__ == '__main__':
    main()

