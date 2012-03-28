import logging

import lxml.html
import lxml.etree

from metastuff import extract_headline,extract_pubdate
from pluck import pluck
import byline
import util

class Article(object):
    def __init__(self, html, url, **kwargs):
        """ """

        logging.debug("*** extracting %s ***" % (url,))

        self.url = url
        self.headline_info = None
        self.pubdate_info = None
        self.author_info = None
        self.content_info = None

        kw = { 'remove_comments': True }
        if 'encoding' in kwargs:
            kw['encoding'] = kwargs['encoding']
            try:
                foo = html.decode(kw['encoding'])
            except UnicodeDecodeError:
                # make it legal
                logging.warning("Invalid %s - cleaning up" %(kw['encoding'],))
                foo = html.decode(kw['encoding'],'ignore')
                html = foo.encode(kw['encoding'])


        parser = lxml.html.HTMLParser(**kw)

        self.doc = lxml.html.document_fromstring(html, parser, base_url=url)

        [i.drop_tree() for i in util.tags(self.doc,'script','style')]

        # drop comment divs - they have a nasty habit of screwing things up
        [i.drop_tree() for i in self.doc.cssselect('#disqus_thread')]
        [i.drop_tree() for i in self.doc.cssselect('#comments, .comment')]

        # drop obvious structural cruft
        [i.drop_tree() for i in self.doc.cssselect('#header, #footer, #sidebar')]

        # nasty little hacks with no obvious general solutions:

        # Johnston Publishing sites - they have adverts embedded in the headline :-(
        [i.drop_tree() for i in self.doc.cssselect('.sponsorPanel')]
        
        # www.shropshirestar.com
        # www.expressandstar.com
        # Have annoyingly-well marked up author links to featured articles in masthead
        [i.drop_tree() for i in self.doc.cssselect('#masthead-quote')]


    @property
    def headline(self):
        if self.headline_info is None:
            self.headline_info = extract_headline(self.doc, self.url)
        return self.headline_info['txt']

    @property
    def pubdate(self):
        if self.headline_info is None:
            self.headline_info = extract_headline(self.doc, self.url)

        if self.pubdate_info is None:
            self.pubdate_info = extract_pubdate(self.doc,self.url,self.headline_info['sourceline'])
        pubdate, pubdate_node = self.pubdate_info
        return pubdate

    @property
    def authors(self):
        if self.headline_info is None:
            self.headline_info = extract_headline(self.doc, self.url)

        if self.pubdate_info is None:
            self.pubdate_info = extract_pubdate(self.doc,self.url,self.headline_info['sourceline'])

        if self.author_info is None:
            self.author_info = byline.extract(self.doc, self.url, self.headline_info['node'], self.pubdate_info[1])

        # TODO: None is a valid return from byline.extract()
        return self.author_info

    @property
    def content(self):
        if self.content_info is None:
            self.content_info = pluck(self.doc)
        # TODO: None is a valid return from pluck()
        return self.content_info

