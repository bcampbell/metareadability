import re

# patterns pulled out so they can be shared between modules
# eg a publication date is often an indication of a nearby byline (and
# vice versa)


pubdate = {
    'metatags': re.compile('date|time',re.I),
    'classes': re.compile('published|updated|date|time|fecha',re.I),
    'url_datefmts': (
        re.compile(r'/(?P<year>\d{4})/(?P<month>\d{1,2})/(?P<day>\d{1,2})/',re.I),
        re.compile(r'[^0-9](?P<year>\d{4})-(?P<month>\d{1,2})-(?P<day>\d{1,2})[^0-9]',re.I),
        ),
    'comment_classes': re.compile('comment|respond',re.I),
    'pubdate_indicator': re.compile('published|posted|updated',re.I),
}


byline = {
    'good_url': re.compile(r'[/](columnistarchive|profile|about|author[s]?|writer|i-author|authorinfo)[/]', re.I),
    'bad_url': re.compile(r'([/](category|tag[s]?|topic[s]?|thema)[/])|(#comment[s]?$)', re.I),
    # TODO: support xfn rel-me?
    'good_rel': re.compile(r'\bauthor\b',re.I),
    'bad_rel': re.compile(r'\btag\b',re.I),
    'bad_title_attr': re.compile(r'^more on ',re.I),
    'classes': re.compile('byline|by-line|by_line|author|writer|credits|firma',re.I),
    'structural_cruft': re.compile(r'^(sidebar|footer)$',re.I),
    'indicative': re.compile(r'\s*\b(by|text by|posted by|written by|exclusive by|reviewed by|published by|photographs by|von)\b[:]?\s*',re.I)
}

headline = {
    'classes': re.compile('entry-title|headline|title',re.I),
    'metatags': re.compile('^headline|og:title|title|head$',re.I),
}

