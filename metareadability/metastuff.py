import unicodedata
import re
import sys
import logging
import datetime
import urlparse

import lxml.html
import lxml.etree

import fuzzydate
import names

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


def render_text(el):
    """ like element.text_content(), but with tactical use of whitespace """

    inline_tags = ( 'a', 'abbr', 'acronym', 'b', 'basefont', 'bdo', 'big',
        'br',
        'cite', 'code', 'dfn', 'em', 'font', 'i', 'img', 'input',
        'kbd', 'label', 'q', 's', 'samp', 'select', 'small', 'span',
        'strike', 'strong', 'sub', 'sup', 'textarea', 'tt', 'u', 'var',
        'applet', 'button', 'del', 'iframe', 'ins', 'map', 'object',
        'script' )

    txt = u''

    tag = str(el.tag).lower()
    if tag not in inline_tags:
        txt += u"\n";

    if el.text is not None:
        txt += unicode(el.text)
    for child in el.iterchildren():
        txt += render_text(child)
        if child.tail is not None:
            txt += unicode(child.tail)

    if el.tag=='br' or tag not in inline_tags:
        txt += u"\n";
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
    'classes': re.compile('byline|author|writer|credits',re.I),
    'indicative': re.compile(r'^(by|written by|posted by)\b',re.I),
}


def extract(html,url):
    """ """
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

    pubdate, pubdate_linenum = extract_pubdate(doc,url,headline_linenum)

    byline = extract_byline(doc,url,headline_linenum, pubdate_linenum)

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
    for e in tags(doc,'p','span','div','li','td','h4','h5','h6','font'):
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
            candidates[dt.date()] = {'datetime': dt, 'score': score, 'sourceline': e.sourceline }


    if not candidates:
        return None,None

    out = sorted(candidates.items(), key=lambda item: item[1]['score'], reverse=True)
#    print "========="
#    pprint( out[:5] )
#    print "========="
    best = out[0][1]
    return best['datetime'],best['sourceline']


#<meta name="date" content="Tuesday, Mar. 29, 2011" />
#    length_cutoff = len("Wednesday September 23rd, 2010, 10:15:12 AM BST") + 5


 #       print pubdate



def strip_date_cruft(s):
    d,dspan = fuzzydate.parse_date(s)
    if dspan is not None:
        s = s[:dspan[0]] + s[dspan[1]:]

    t,tspan = fuzzydate.parse_time(s)
    if tspan is not None:
        s = s[:tspan[0]] + s[tspan[1]:]

    if tspan is not None or dspan is not None:
        # TODO: strip leftover "on" "at" etc...
        s = re.compile(r'\b(on|at|published|posted)\b[:]?',re.IGNORECASE).sub('',s)

    return s



def uberstrip(s):
    # strip leading/trailing non-alphabetic chars
    pat = re.compile(r'^[^\w()]*(.*?)[^\w()]*$', re.IGNORECASE|re.UNICODE)
    return pat.sub(r'\1', s)


# various things that split up parts of a byline
byline_split_pat = re.compile(r'\s*(?:[^\w\s]|\b(?:by|and|in|of|written|posted)\b)+\s*',re.DOTALL|re.IGNORECASE)


def rate_byline(byline):
    parts = byline_split_pat.split(byline)
    parts = [part.strip() for part in parts if part.strip()]
    if len(parts)<1 or len(parts)>3:
        return -2.0

    if re.compile(r'\b(about us|contact us)\b',re.IGNORECASE).search(byline):
        return -2.0

    # indicators of jobtitle
    jobtitle_pat = re.compile(r'\b(editor|associate|reporter|correspondent|corespondent|director|writer|commentator|nutritionist|presenter|journalist|cameraman|deputy|columnist)\b',re.IGNORECASE)

    for part in parts:
        if len(part.split())>5:
            return 0.0

    score = names.rate_name(parts[0])
    if len(parts)>1:
        for part in parts[1:]:
            if jobtitle_pat.search(part):
                score += 1.0
                break
            else:
                score -= 1.0

    return score



def is_author_link(a):
    """ return true if link looks like it could be an author """
    pat = re.compile(r'[/](profile|about|author|writer|authorinfo)[/]', re.I)
    href = a.get('href','')
    if pat.search(href):
        if names.rate_name(a.text_content()) > 0.1:
            return True
    return False



def extract_byline(doc, url, headline_linenum, pubdate_linenum):
    candidates = {}

    logging.debug("extracting byline")

    # check hatom author

    authors = doc.cssselect('.hentry .author .fn')
    if len(authors)>0:
        byline = u','.join([unicode(author.text_content()) for author in authors])
        logging.debug("found hatom author(s): %s" %(byline))
        return byline


    # TODO: check meta tags

    for e in tags(doc,'p','span','div','h3','h4','td','a','li','small'):
        txt = render_text(e).strip()

        # strip out date, compress spaces etc...
        txt = strip_date_cruft(txt)
        txt = u' '.join(txt.split())
        txt = uberstrip(txt)

        # discard anything too short or long
        if len(txt)<7 or len(txt) > 200:
            continue

        score = 0.0


        # TEST: contains names?
        byline_rating = rate_byline(txt)

        logging.debug(" byline: consider %s '%s' (base rating %f)" % (e.tag,txt,byline_rating))

#        logging.debug("  byline rating: %f" % (byline_rating,))
        score += 1.0*byline_rating

        # TEST: indicative text? ('By ....')
        if byline_pats['indicative'].search(txt):
            logging.debug("  text indicative of byline")
            score += 1.0

        # early out
        if score <= 0.0:
            continue


        # TEST: likely-looking class or id
        if byline_pats['classes'].search(e.get('class','')):
            logging.debug("  likely class")
            score += 1.0
        if byline_pats['classes'].search(e.get('id','')):
            logging.debug("  likely id")
            score += 1.0

        # TEST proximity to headline
        if headline_linenum>0 and e.sourceline>0:
            dist = headline_linenum - e.sourceline
            if dist >-5 and dist <10:
                logging.debug("  near headline")
                score += 1.0

        # TEST proximity to pubdate
        if pubdate_linenum is not None and e.sourceline>0:
            dist = pubdate_linenum - e.sourceline
            if dist >-5 and dist <5:
                logging.debug("  near pubdate")
                score += 1.0

        #TEST is link a tag/category/whatever
        if e.tag == 'a':
            rel = e.get('rel')
            if re.compile(r'\btag\b').search(e.get('rel','')):
                score -= 1.0
                logging.debug("  -1 rel-tag")
            else:
                blacklist = ('/category/', '/tag/', '/tags/')
                href = e.get('href','')
                for b in blacklist:
                    if b in href:
                        score -= 1.0
                        logging.debug("  -1 looks like tag")


        # TEST: is a link with a likely-looking href?
        if e.tag == 'a':
            if is_author_link(e):
                logging.debug("  is a likely-looking author link")
                score += 1.0

        # TEST: contains a link with a likely-looking href?
        for a in tags(e,'a'):
            if is_author_link(a):
                logging.debug("  contains likely-looking link")
                score += 1.0

        # TODO
        # TEST: looks like a byline?
        #   split into names, check length
        # TEST: names are links?
        #   and hrefs look like bio pages?
        # TEST: byline length
        #   statistical check against JL data
        # TEST: likely-looking title strings in links? title="posts by Fred Bloggs"
        #   extra points if link has likely author class (or hcard?)
        # TEST: not inside a suspected sidebar

        if score < 0.01:
            continue
        logging.debug("  score: %f" % (score))

        if txt not in candidates or score>candidates[txt]['score']:
            candidates[txt] = {'byline': txt, 'score': score}

    if not candidates:
        return None

    out = sorted(candidates.items(), key=lambda item: item[1]['score'], reverse=True)
#    print "========="
#    pprint( out[:5] )
#    print "========="
    return out[0][1]['byline']





