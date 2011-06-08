import re
import logging
from pprint import pprint

import util
import names

#'indicative': re.compile(r'^(by|written by|posted by|von)\b',re.I),
# from

# various things that split up parts of a byline
byline_split_pat = re.compile(r'\s*(?:[^\w\s]|\b(?:by|and|in|of|written|posted|updated)\b)+\s*',re.DOTALL|re.IGNORECASE)




#def rate_byline(byline):
#    byline_re = re.compile(r'^(?P<indicative>by|posted by|written by|von)?\s*(?P<name>(?:(?:\w+|\w[.]|\w+-\w+)\s*)+)\s*[-,|]\s*(?P<leftovers>\w.*)?$', re.UNICODE)
#    jobtitle_re = re.compile(r'\b(editor|associate|reporter|correspondent|corespondent|director|writer|commentator|nutritionist|presenter|journalist|cameraman|deputy|columnist)\b',re.IGNORECASE)


_pats = {
    'good_url': re.compile(r'[/](columnistarchive|profile|about|author[s]?|writer|i-author|authorinfo)[/]', re.I),
    'bad_url': re.compile(r'[/](category|tag[s]?|topic[s]?|thema)[/]', re.I),
    # TODO: support xfn rel-me?
    'good_rel': re.compile(r'\bauthor\b',re.I),
    'bad_rel': re.compile(r'\btag\b',re.I),
    'classes': re.compile('byline|author|writer|credits',re.I),
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


def extract(doc, url, headline_node, pubdate_node):
    candidates = {}

    logging.debug("EXTRACTING BYLINE")

    # check hatom author
    # TODO: more robust hCard support!
    authors = doc.cssselect('.hentry .author .fn')
    if len(authors)>0:
        byline = u','.join([unicode(author.text_content()) for author in authors])
        logging.debug("found hatom author(s): %s" %(byline))
        return byline   # yay! early out.

    # TODO: specialcase rel-author and rel-me? Are they used in the wild yet?

    # look for links only
    for a in util.tags(doc,'a'):
        score = 0.0
        name = unicode(a.text_content()).strip()
        url = a.get('href','')
        rel = a.get('rel','')

        # TEST: rate nameiness of name
        name_score = names.rate_name(name)
        if name_score < 0.0:
            continue;   # early out
        logging.debug(" byline: consider link '%s'" %(name,))
        score += name_score
        logging.debug("  name score: %.3f" % (name_score,))

        # TEST: likely url?
        if _pats['good_url'].search(url):
            score += 1.0
            logging.debug("  likely-looking url")
        # TEST: unlikely url?
        if _pats['bad_url'].search(url):
            score -= 1.0
            logging.debug("  -1 unlikely-looking url")

        # TEST: recognised rel- pattern?
        if _pats['good_rel'].search(rel):
            score += 2.0
            logging.debug("  likely-looking rel")

        # TEST: unwanted rel- pattern?
        if _pats['bad_rel'].search(rel):
            score += 2.0
            logging.debug("  -2 unlikely-looking rel")


        # TEST: likely-looking class or id
        if _pats['classes'].search(a.get('class','')):
            logging.debug("  likely class")
            score += 1.0
        if _pats['classes'].search(a.get('id','')):
            logging.debug("  likely id")
            score += 1.0
        # TEST: parent has likely-looking class or id
        parent = a.getparent()
        if _pats['classes'].search(parent.get('class','')):
            logging.debug("  parent has likely class")
            score += 1.0
        if _pats['classes'].search(parent.get('id','')):
            logging.debug("  parent has likely id")
            score += 1.0

        # TEST: proximity to headline
        if headline_node is not None:
            dist = a.sourceline - headline_node.sourceline
            if dist >-5 and dist <15:
                logging.debug("  near headline")
                score += 0.5

            container = headline_node.getparent()
            if(contains(container,a)):
                logging.debug("  inside same container as headline")
                score += 1.0



        # TEST: proximity to pubdate
        if pubdate_node is not None:
            dist = a.sourceline - pubdate_node.sourceline
            if dist >-5 and dist <10:
                logging.debug("  near pubdate")
                score += 0.5

        # TEST: in sidebar/footer?
        up = a.getparent()
        while(up is not None):
            if _pats['structural_cruft'].search(up.get('id','')):
                logging.debug("  -1 inside structural cruft (id: '%s')" % (up.get('id'),))
                score -= 1.0
                break
            if _pats['structural_cruft'].search(up.get('class','')):
                logging.debug("  -1 inside structural cruft (class: '%s')" %(up.get('class'),))
                score -= 1.0
                break
            up = up.getparent()


        # TODO TEST: preceeded by indicative text? ('By ....')

        # only consider significant ones...
        if score > 1.0:
            candidates[a] = {'element':a, 'score': score, 'name': name, 'url': url}

    if not candidates:
        return None

    results = sorted(candidates.values(), key=lambda item: item['score'], reverse=True)

    logging.debug( " byline rankings:")
    for r in results:
        logging.debug("  %.3f: %s (%s)" % (r['score'], r['name'], r['url']))

    return results[0]['name']

