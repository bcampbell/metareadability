import re
import sys
import logging
import datetime
import urlparse

import lxml.html
import lxml.etree

import fuzzydate
import names
import util
import byline

from pprint import pprint


#from BeautifulSoup import BeautifulSoup, HTMLParseError, UnicodeDammit



headline_pats = { 'classes': re.compile('entry-title|headline|title',re.I),
        'metatags': re.compile('^headline|og:title|title|head$',re.I),
        }

pubdate_pats = { 'metatags': re.compile('date|time',re.I),
    'classes': re.compile('published|updated|date|time|fecha',re.I),
    'url_datefmts': (
        re.compile(r'/(?P<year>\d{4})/(?P<month>\d{1,2})/(?P<day>\d{1,2})/',re.I),
        re.compile(r'[^0-9](?P<year>\d{4})-(?P<month>\d{1,2})-(?P<day>\d{1,2})[^0-9]',re.I),
        ),
    'comment_classes': re.compile('comment|respond',re.I),
    'pubdate_indicator': re.compile('published|posted|updated',re.I),
    }

byline_pats = { 'metatags': re.compile('',re.I),
    'classes': re.compile('byline|author|writer|credits',re.I),
    'indicative': re.compile(r'^(by|written by|posted by|von)\b',re.I),
}


def extract(html, url, **kwargs):
    """ """
    logging.debug("*** extracting %s ***" % (url,))

    kw = { 'remove_comments': True }
    if 'encoding' in kwargs:
        kw['encoding'] = kwargs['encoding']
    parser = lxml.html.HTMLParser(**kw)
    doc = lxml.html.document_fromstring(html, parser, base_url=url)

    [i.drop_tree() for i in util.tags(doc,'script','style')]

#    html = UnicodeDammit(html, isHTML=True).markup
    headline_info = extract_headline(doc,url)
    headline_linenum = 0
    headline = None
    headline_node = None
    if headline_info is not None:
        headline_linenum = headline_info['sourceline']
        headline = headline_info['txt']
        headline_node = headline_info['node']

    pubdate, pubdate_node = extract_pubdate(doc,url,headline_linenum)

    authors = byline.extract(doc, url, headline_node, pubdate_node)

    return headline,authors,pubdate



def extract_headline(doc,url):

    logging.debug("extracting headline")

    candidates = {}

    for h in util.tags(doc,'h1','h2','h3','h4','h5','h6','div'):
        score = 1
        txt = unicode(h.text_content()).strip()
        txt = u' '.join(txt.split())
        if len(txt)==0:
            continue


        txt_norm = util.normalise_text(txt)

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
            score += 2

        # TEST: does it appear in <title> text?
        title = unicode(getattr(doc.find('.//title'), 'text', ''))
        if title is not None:
            if txt_norm in util.normalise_text(title):
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
                meta_content = util.normalise_text(unicode(meta.get('content','')))
                if meta_content != '':
                    if txt_norm==meta_content:
                        logging.debug("  match meta")
                        score += 3
                    elif txt_norm in meta_content:
                        logging.debug("  contained by meta")
                        score += 1

        # TEST: does it match slug part of url?
        slug = re.split('[-_]', util.get_slug(url).lower())
        parts = [util.normalise_text(part) for part in txt.split()]
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
            candidates[txt] = {'txt':txt, 'score':score, 'sourceline':h.sourceline, 'node':h}

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



def extract_pubdate(doc, url, headline_linenum):
    """ returns date,linenum """
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
            return d,None



    meta_dates = set()
    for meta in doc.findall('.//meta'):
        n = meta.get('name', meta.get('property', ''))
        if pubdate_pats['metatags'].search(n):
            logging.debug(" date: consider meta name='%s' content='%s'" % (n,meta.get('content','')))
            fuzzy = fuzzydate.parse_datetime(meta.get('content',''))
            if not fuzzy.empty_date():
                fuzzy = fuzzydate.fuzzydate.combine(fuzzy,fuzzydate.fuzzydate(day=1))
                meta_dates.add(fuzzy.date())

#    if len(meta_dates)==1:
#        # only one likely-looking <meta> entry - lets go with it
#        d = list(meta_dates)[0]
#        logging.debug("  using %s from <meta>" % (d,))
#        return d,None

    # start looking through whole page
    for e in util.tags(doc,'p','span','div','li','td','h4','h5','h6','font'):
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
            if dist >-10 and dist <25:
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

        # TEST: date appears in url? eg "http://blah.com/blahblah-20100801-blah.html"
        if re.compile("%d[-_/.]?0?%d[-_/.]?0?%d" % (dt.year,dt.month,dt.day)).search(url):
            logging.debug("  full date appears in url")
            score += 2
        elif re.compile("%d[-_/.]?0?%d" % (dt.year,dt.month)).search(url):
            logging.debug("  year and month appear in url")
            score += 1

        if dt.date() not in candidates or score>candidates[dt.date()]['score']:
            candidates[dt.date()] = {'datetime': dt, 'score': score, 'node': e}


    if not candidates:
        return None,None

    out = sorted(candidates.items(), key=lambda item: item[1]['score'], reverse=True)
#    print "========="
#    pprint( out[:5] )
#    print "========="
    best = out[0][1]
    return best['datetime'],best['node']



def parse_byline(el):
    parts = []
    parts.append(el.text)

    for child in el:
        parts.append(child.text_content);

