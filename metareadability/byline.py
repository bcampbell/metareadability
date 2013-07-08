import re
import logging
from pprint import pprint

import util
import fuzzydate
import names
import pats

#'indicative': re.compile(r'^(by|written by|posted by|von)\b',re.I),
# from

# various things that split up parts of a byline
#byline_split_pat = re.compile(r'\s*(?:[^\w\s]|\b(?:by|and|in|of|written|posted|updated)\b)+\s*',re.DOTALL|re.IGNORECASE)




#def rate_byline(byline):
#    byline_re = re.compile(r'^(?P<indicative>by|posted by|written by|von)?\s*(?P<name>(?:(?:\w+|\w[.]|\w+-\w+)\s*)+)\s*[-,|]\s*(?P<leftovers>\w.*)?$', re.UNICODE)
#    jobtitle_re = re.compile(r'\b(editor|associate|reporter|correspondent|corespondent|director|writer|commentator|nutritionist|presenter|journalist|cameraman|deputy|columnist)\b',re.IGNORECASE)




def contains(container, el):
    """ return true if el node is inside container (any depth) """
    
    while 1:
        parent = el.getparent()
        if parent is None:
            return False
        if parent == container:
            return True
        el = parent


def intervening(el_from, el_to, all):
    try:
        pos1 = all.index(el_from)
        pos2 = all.index(el_to)
        assert(pos1 is not None)
        assert(pos2 is not None)

        if pos2>pos1:
            return all[pos1+1:pos2]
    except:
        pass

    return None


def extract(doc, url, headline_node, pubdate_node):
    """ Returns byline text """

    logging.debug("EXTRACTING BYLINE")


    all = list(doc.iter())

    candidates = {}

    bylineContainer=doc

    # TODO: REMOVE UGLY UGLY HACKERY!
    if 'independent.co.uk/voices' in url:
        foo = doc.cssselect('.articleByline')
        if len(foo)==1:
            bylineContainer = foo[0]

    # TODO: early-out for special cases (eg hAtom author, rel="author")
    for el in util.tags(bylineContainer, 'a','p','span','div','li','h3','h4','h5','h6','td','strong'):

        authors, score = parse_byline(el, all, headline_node)

        if score>1.5:
            # could be a date in it still
            #txt = util.strip_date(txt).strip()

            # reconstiute
            txt = u" and ".join([a['name'] for a in authors])
            candidates[el] = {'element':el, 'score': score, 'raw_byline': txt}

    if candidates:
        results = sorted(candidates.values(), key=lambda item: item['score'], reverse=True)
        logging.debug( " byline rankings (top 10):")
        for r in results[:10]:
            logging.debug("  %.3f: '%s'" % (r['score'], r['raw_byline']))
        return unicode(results[0]['raw_byline']).strip()

    return None



def parse_byline(candidate,all,headline_node):
    authors = []
    score = 0.0
    txt = util.render_text(candidate)
    txt = u' '.join(txt.split()).strip()
    if len(txt) > 200:
        return (authors,score)

    logging.debug("byline: consider <%s> '%s'"%(candidate.tag,txt[:75]))

#    if candidate.tag == 'a':
#        score += eval_author_link(candidate)

    # split up using html structure
    parts = util.iter_text(candidate)

    # pass 1: check for and strip out parts with dates & times
    # TODO: this is a bit ruthless - could lose names if in same block
    parts2 = []
    for txt,el in parts:
        is_pubdate_frag = False
        if pats.pubdate['pubdate_indicator'].search(txt):
            is_pubdate_frag = True

        t,dspan = fuzzydate.parse_date(txt)
        if dspan is not None:
            logging.debug("  +0.1 contains date")
            score += 0.1
            is_pubdate_frag = True

        d,tspan = fuzzydate.parse_time(txt)
        if tspan is not None:
            logging.debug("  +0.1 contains time")
            score += 0.1
            is_pubdate_frag = True

        if not is_pubdate_frag:
            parts2.append((txt,el))

    # pass 2: split up text on likely separators - "and" "in" or any non alphabetic chars...
    # (capturing patterns are included in results)
    split_pat = re.compile(r'((?:\b(?:and|with|in)\b)|(?:[^-_.\w\s]+))',re.IGNORECASE|re.UNICODE)
    parts3 = []
    for txt,el in parts2:
        fragments = split_pat.split(txt)
        for frag in fragments:
            parts3.append((frag.strip(),el))

    # pass three - split out indicatives ("by", "posted by" etc)
    parts4 = []
    for txt,el in parts3:
        for frag in pats.byline['indicative'].split(txt):
            parts4.append((frag,el))

    # clean up
    parts4 = [(txt.strip(),el) for txt,el in parts4]
    parts4 = [(txt,el) for txt,el in parts4 if txt!=u'']

    # now run through classifying and collecting authors
    authors,score = parse_byline_parts(parts4)

    # TEST: likely-looking class or id
    if pats.byline['classes'].search(candidate.get('class','')):
        logging.debug("  +1 likely class")
        score += 1.0
    if pats.byline['classes'].search(candidate.get('id','')):
        logging.debug("  +1 likely id")
        score += 1.0

    # TEST: directly after headline?
    foo = intervening(headline_node,candidate,all)
    if foo is not None:
        if len(foo) == 0:
            logging.debug("  +0.5 directly after headline")
            score += 0.5

    logging.debug( "  total: %.3f" % (score,))

    return (authors, score)




def reconstitute_byline(authors):
    names = [a['name'] for a in authors]
    raw_byline = u', '.join(names)
    if raw_byline != u'':
        raw_byline = u'by ' + raw_byline
    return raw_byline



def parse_byline_parts(parts):
    authors = []

    ANY=0
    PERSON=1
    PLACE_OR_CATEGORY=2

    expecting = PERSON
    byline_score = 0.0
    i=0
    while i < len(parts):
        txt,el = parts[i]

        if len(txt.split())>=5:
            logging.debug("  -2 excessive words")

            byline_score -= 2.0
            break

        i+=1

        if len(txt.lower()) <= 1:       # in ('-',',','|'):
            continue

        if i==1 and pats.byline['indicative'].match(txt):
            # starts with "by" or similar.  yay.
            logging.debug("  +1 Indicative")
            byline_score += 1.0
            expecting = PERSON
            continue
        if txt.lower() in ('and','&'):
            expecting = PERSON
            continue

        if txt.lower() in ('in',):
            expecting = PLACE_OR_CATEGORY
            continue

        # TODO: check for obvious cruft "About us" etc...

        author_score = rate_author(txt,el)
        if expecting==PERSON:
            expecting = ANY
            author_score += 0.5

        is_title = is_job_title(txt)
        maybe_pub = could_be_publication(txt)
#        location_score = rate_publication(txt)

        # TODO: check for "follow X on twitter", email addresses etc...


        # now decide if it's a person or not...
        person = False
        if len(authors) == 0:
            person = True

        author_threshold = 0.0
        if is_title or maybe_pub or expecting==PLACE_OR_CATEGORY:
            person = False
        else:
            if author_score > 0.0:
                person = True


        if len(authors) == 0:
            person = True

        if person:
            url = None
            if el is not None and el.tag=='a':
                url = el.get('href',None)
            authors.append({'name':txt, 'score':author_score, 'url':url, 'jobtitle':None, 'publication':None, 'cruft':[]})
            logging.debug("  person: '%s' (%.3f)"%(txt,author_score))
        else:
            if is_title:
                if authors[-1]['jobtitle'] is None:
                    logging.debug("   +1 job title '%s'"%(txt))
                    authors[-1]['jobtitle'] = txt
                    authors[-1]['score'] += 1.0
                else:
                    logging.debug("   -1 extra job title '%s'" % (txt))
                    authors[-1]['score'] -= 1.0
            elif maybe_pub:
                if authors[-1]['publication'] is None:
                    logging.debug("   +.5 publication '%s'"%(txt))
                    authors[-1]['publication'] = txt
                    authors[-1]['score'] += 0.5
                else:
                    logging.debug("   -.5 extra publication '%s'" % (txt))
                    authors[-1]['score'] -= 0.5
            else:
                authors[-1]['cruft'].append(txt)
                logging.debug("   -.2 cruft '%s'" % (txt))
                authors[-1]['score'] -= 0.2

        expecting = ANY

    if len(authors)>0:
        byline_score += sum([author['score'] for author in authors]) / len(authors)

    return authors,byline_score


def rate_author(txt,el):
    author_score = names.rate_name(txt)
    if el is not None and el.tag=='a':
        author_score += eval_author_link(el)
    return author_score


# TODO: split out into data file
jobtitle_pats = [
    re.compile( """associate editor""", re.IGNORECASE|re.UNICODE ),

    re.compile( """editor$""", re.IGNORECASE|re.UNICODE ),
    re.compile( """reporter$""", re.IGNORECASE|re.UNICODE ),
    re.compile( """correspondent$""", re.IGNORECASE|re.UNICODE ),
    re.compile( """corespondent$""", re.IGNORECASE|re.UNICODE ),
    re.compile( """director$""", re.IGNORECASE|re.UNICODE ),
    re.compile( """writer$""", re.IGNORECASE|re.UNICODE ),
    re.compile( """commentator$""", re.IGNORECASE|re.UNICODE ),
    re.compile( """nutritionist""", re.IGNORECASE|re.UNICODE ),

    re.compile( """presenter""", re.IGNORECASE|re.UNICODE ),
    re.compile( """online journalist""", re.IGNORECASE|re.UNICODE ),
    re.compile( """journalist""", re.IGNORECASE|re.UNICODE ),
    re.compile( """cameraman""", re.IGNORECASE|re.UNICODE ),
    re.compile( r'\bdeputy\b', re.IGNORECASE|re.UNICODE ),
    re.compile( r'\bhead\b', re.IGNORECASE|re.UNICODE ),
    re.compile( """columnist""", re.IGNORECASE|re.UNICODE ),
    ]

def is_job_title(txt):
    for pat in jobtitle_pats:
        if pat.search(txt):
            return True
    return False

# TODO: split out into data file
publication_pats = [
    re.compile( r'\b(?:mail|sunday|magazine|press|bbc|mirror|telegraph|agencies|agences|express|reuters|afp|news|online|herald|guardian|times|echo)\b', re.IGNORECASE ),
    re.compile( """the mail on sunday""", re.IGNORECASE|re.UNICODE ),
    re.compile( """the times""", re.IGNORECASE|re.UNICODE ),
    re.compile( """associated press""", re.IGNORECASE|re.UNICODE ),
    re.compile( """press association""", re.IGNORECASE|re.UNICODE ),
    re.compile( """\\bap\\b""", re.IGNORECASE|re.UNICODE ),
    re.compile( """\\bpa\\b""", re.IGNORECASE|re.UNICODE ),
    re.compile( """bbc news""", re.IGNORECASE|re.UNICODE ),
    re.compile( """bbc scotland""", re.IGNORECASE|re.UNICODE ),
    re.compile( """bbc wales""", re.IGNORECASE|re.UNICODE ),
    re.compile( """sunday telegraph""", re.IGNORECASE|re.UNICODE ),
    re.compile( """\\bmirror[.]co[.]uk\\b""", re.IGNORECASE|re.UNICODE ),
    re.compile( """\\bagencies\\b""", re.IGNORECASE|re.UNICODE ),
    re.compile( """\\bagences\\b""", re.IGNORECASE|re.UNICODE ),
    re.compile( """\\bexpress.co.uk\\b""", re.IGNORECASE|re.UNICODE ),
    
    re.compile( """\\breuters\\b""", re.IGNORECASE|re.UNICODE ),
    re.compile( """\\bafp\\b""", re.IGNORECASE|re.UNICODE ),
    re.compile( """sky news online""", re.IGNORECASE|re.UNICODE ),  # gtb
    re.compile( """sky news""", re.IGNORECASE|re.UNICODE ), # gtb
    re.compile( """sky""", re.IGNORECASE|re.UNICODE ),  # gtb
    re.compile( r"\bheraldscotland\b", re.IGNORECASE|re.UNICODE ),
    ]

def could_be_publication(txt):
    for pat in publication_pats:
        if pat.search(txt):
            return True
    return False

def rate_location(txt):
    return 0.0


def eval_author_link(a):
    score = 0.0
    url = a.get('href','')
    rel = a.get('rel','')
    title = a.get('title','')
#    logging.debug("  eval_author_link '%s'" % (a.text_content().strip(),))
    if title:
        logging.debug(title)
    # TODO: TEST: email links almost certainly people?

    # TEST: likely url?
    if pats.byline['good_url'].search(url):
        score += 1.0
        logging.debug("  +1 likely-looking url '%s'" % (url,))
    # TEST: unlikely url?
    if pats.byline['bad_url'].search(url):
        score -= 1.0
        logging.debug("  -1 unlikely-looking url '%s'" % (url,))

    # TEST: recognised rel- pattern?
    if pats.byline['good_rel'].search(rel):
        score += 2.0
        logging.debug("  +2 likely-looking rel '%s'" % (rel,))

    # TEST: unwanted rel- pattern?
    if pats.byline['bad_rel'].search(rel):
        score -= 2.0
        logging.debug("  -2 unlikely-looking rel '%s'" % (rel,))

    # TEST: unlikely text in title attr?
    if pats.byline['bad_title_attr'].search(title):
        score -= 2.0
        logging.debug("  -2 unlikely-looking title attr '%s'" % (title,))

    return score

