import re
import logging
from pprint import pprint

import util
import names

#'indicative': re.compile(r'^(by|written by|posted by|von)\b',re.I),
# from

# various things that split up parts of a byline
#byline_split_pat = re.compile(r'\s*(?:[^\w\s]|\b(?:by|and|in|of|written|posted|updated)\b)+\s*',re.DOTALL|re.IGNORECASE)




#def rate_byline(byline):
#    byline_re = re.compile(r'^(?P<indicative>by|posted by|written by|von)?\s*(?P<name>(?:(?:\w+|\w[.]|\w+-\w+)\s*)+)\s*[-,|]\s*(?P<leftovers>\w.*)?$', re.UNICODE)
#    jobtitle_re = re.compile(r'\b(editor|associate|reporter|correspondent|corespondent|director|writer|commentator|nutritionist|presenter|journalist|cameraman|deputy|columnist)\b',re.IGNORECASE)


_pats = {
    'good_url': re.compile(r'[/](columnistarchive|profile|about|author[s]?|writer|i-author|authorinfo)[/]', re.I),
    'bad_url': re.compile(r'[/](category|tag[s]?|topic[s]?|thema)[/]', re.I),
    # TODO: support xfn rel-me?
    'good_rel': re.compile(r'\bauthor\b',re.I),
    'bad_rel': re.compile(r'\btag\b',re.I),
    'bad_title_attr': re.compile(r'^more on ',re.I),
    'classes': re.compile('byline|by-line|author|writer|credits',re.I),
    'structural_cruft': re.compile(r'^(sidebar|footer)$',re.I),
}


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
    """ returns list of elements between el_from and el_to, in document order """
    pos1=None
    pos2=None
    for i,x in enumerate(all):
        if x==el_from:
            pos1 = i
        if x==el_to:
            pos2 = i

    assert(pos1 is not None and pos2 is not None)

    if pos2>pos1:
        return all[pos1+1:pos2]
    else:
        return None



def extract(doc, url, headline_node, pubdate_node):

    logging.debug("EXTRACTING BYLINE")

    # check hatom author
    # TODO: more robust hCard support!
    authors = doc.cssselect('.hentry .author .fn')
    if len(authors)>0:
        byline = u','.join([unicode(author.text_content()) for author in authors])
        logging.debug("found hatom author(s): %s" %(byline))
        return byline   # yay! early out.

    # TODO: specialcase rel-author and rel-me? Are they used in the wild yet?

    all = doc.iter()

    candidates = {}
    for el in util.tags(doc, 'a','p','span','div','li','h3','h4','h5','h6','td','strong'):
        txt = util.render_text(el)
        txt = u' '.join(txt.split()).strip()
        if len(txt) > 200:
            continue


        logging.debug("byline: consider <%s> '%s'"%(el.tag,txt[:75]))
        parts = tokenise_byline(el)
        authors, score = parse_byline_parts(parts)
        logging.debug("   bylinescore=%.3f"%(score))

        if el.tag == 'a':
            logging.debug("LINK")
            score += eval_author_link(el)

        # TEST: likely-looking class or id
        if _pats['classes'].search(el.get('class','')):
            logging.debug("  +1 likely class")
            score += 1.0
        if _pats['classes'].search(el.get('id','')):
            logging.debug("  +1 likely id")
            score += 1.0
        logging.debug("   score=%.3f"%(score))

        if score>1.5:
            logging.debug("  score: %.3f"%(score,))
            # could be a date in it still
            txt = util.strip_date(txt).strip()
            candidates[el] = {'element':el, 'score': score, 'raw_byline': txt}

    if candidates:
        results = sorted(candidates.values(), key=lambda item: item['score'], reverse=True)
        logging.debug( " byline rankings (top 10):")
        for r in results[:10]:
            logging.debug("  %.3f: '%s'" % (r['score'], r['raw_byline']))
        return unicode(results[0]['raw_byline'])

    return None



indicative_pat = re.compile(r'^\s*(by|posted by|written by|exclusive by|reviewed by|published by|von)[:]?\s*',re.IGNORECASE)

def tokenise_byline(el):
    parts = []

    # split into parts based on html structure
    if el.text:
        parts.append((unicode(el.text),None))
    for child in el:
        parts.append((unicode(child.text_content()),child))
        if child.tail:
            parts.append((unicode(child.tail),None))

    # strip out any dates (often mashed in with byline)
    parts = [(util.strip_date(txt),e) for txt,e in parts]

    # now split up raw text parts by and/in/, etc...
    parts2 = []
    for part in parts:
        fragments = re.compile(r'((?:\band\b)|(?:\bin\b)|(?:\s+-\s+)|[,|&])',re.IGNORECASE).split(part[0])
        parts2.append((fragments[0],part[1]))
        for frag in fragments[1:]:
            parts2.append((frag,part[1]))

    parts3 = []
    for part in parts2:
        for frag in indicative_pat.split(part[0]):
            parts3.append((frag,part[1]))

    # clean up
    parts3 = [(s.strip(),e) for s,e in parts3]
    parts3 = [(s,e) for s,e in parts3 if s!=u'']

    return parts3


def parse_byline_parts(parts):
    authors = []

    expect_person = True
    byline_score = 0.0
    i=0
    while i < len(parts):
        txt,el = parts[i]

        if len(txt.split())>=5:
            logging.debug("  -2 excessive words")

            byline_score -= 2.0
            break

        i+=1

        if txt.lower() in ('-',',','|'):
            continue

        if i==1 and indicative_pat.match(txt):
            # starts with "by" or similar.  yay.
            logging.debug("  +1 Indicative")
            byline_score += 1.0
            continue
        if txt.lower() in ('and','&'):
            expect_person = True
            continue

        # TODO: check other indicatives: "at" "in" "for"

        # TODO: check for obvious cruft "About us" etc...

        author_score = rate_author(txt,el)
        if expect_person:
            expect_person = False
            author_score += 0.5

        is_title = is_job_title(txt)
        maybe_pub = could_be_publication(txt)
#        location_score = rate_publication(txt)

        # now decide if it's a person or not...
        person = False
        if len(authors) == 0:
            person = True

        author_threshold = 0.0
        if is_title or could_be_publication:
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


    for author in authors:
        byline_score += author['score']

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
    re.compile( r'\b(?:mail|sunday|press|bbc|mirror|telegraph|agencies|agences|express|reuters|afp|news|online|herald|guardian|times)\b', re.IGNORECASE ),
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
    if title:
        logging.debug(title)
    # TODO: TEST: email links almost certainly people?

    # TEST: likely url?
    if _pats['good_url'].search(url):
        score += 1.0
        logging.debug("  +1 likely-looking url '%s'" % (url,))
    # TEST: unlikely url?
    if _pats['bad_url'].search(url):
        score -= 1.0
        logging.debug("  -1 unlikely-looking url '%s'" % (url,))

    # TEST: recognised rel- pattern?
    if _pats['good_rel'].search(rel):
        score += 2.0
        logging.debug("  +2 likely-looking rel '%s'" % (rel,))

    # TEST: unwanted rel- pattern?
    if _pats['bad_rel'].search(rel):
        score -= 2.0
        logging.debug("  -2 unlikely-looking rel '%s'" % (rel,))

    # TEST: unlikely text in title attr?
    if _pats['bad_title_attr'].search(title):
        score -= 2.0
        logging.debug("  -2 unlikely-looking title attr '%s'" % (title,))

    return score

