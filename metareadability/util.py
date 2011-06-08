""" miscellaneous utlitity functions for metareadability """

import re
import unicodedata
import urlparse

import fuzzydate

def tags( node, *tag_names):
    """iterator to go through all matching child tags"""
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


def uberstrip(s):
    # strip leading/trailing non-alphabetic chars
    pat = re.compile(r'^[^\w()]*(.*?)[^\w()]*$', re.IGNORECASE|re.UNICODE)
    return pat.sub(r'\1', s)


def render_text(el):
    """ like lxml.html text_content(), but with tactical use of whitespace for block elements """

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



def strip_date(s):
    """ remove all date/time bits from text """
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

