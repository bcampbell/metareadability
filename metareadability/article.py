import logging
import re

import lxml.html
import lxml.etree

from metastuff import extract_headline,extract_pubdate
import content
import byline
import util

logger = logging.getLogger('metareadability')


class Article(object):
    def __init__(self, html, url, **kwargs):
        """ """

        logger.debug("*** extracting %s ***" % (url,))

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
                logger.warning("Invalid %s - cleaning up" %(kw['encoding'],))
                foo = html.decode(kw['encoding'],'ignore')
                html = foo.encode(kw['encoding'])

        parser = lxml.html.HTMLParser(**kw)

        self.doc = lxml.html.document_fromstring(html, parser, base_url=url)
        self.doc.make_links_absolute(url)

        [i.drop_tree() for i in util.tags(self.doc,'script','style')]

        # drop comment divs - they have a nasty habit of screwing things up
        # TODO: reconcile with comment filtering in content extraction
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


        #[cruft.drop_tree() for cruft in doc.cssselect('meta, img, script, style, input, textarea, ul.breadcrumb')]
        [cruft.drop_tree() for cruft in self.doc.cssselect('img, script, style, input, textarea, ul.breadcrumb')]

        cruft_classes = re.compile(r"(combx|comment|disqus|foot|menu|rss|shoutbox|sidebar|sponsor|ad-break|agegate|promo|list|photo|social|singleAd|adx|relatedarea)", re.I)
        for div in self.doc.findall('.//div'):
            if cruft_classes.search(div.get('class','')) or cruft_classes.search(div.get('id','')):
                div.drop_tree()

        # hack from poligraft pluck code
        # convert <div>s that should be <p>s
        for div in self.doc.findall('.//div'):
            brs = len([child for child in div if child.tag=='br'])
            if brs>2:
                div.tag='p'

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
            self.content_info = content.extract(self)
        # TODO: None is a valid return from extract()
        return self.content_info

