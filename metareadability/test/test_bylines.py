import unittest
import site
import os
import sys
import lxml.html


here = os.path.dirname(os.path.abspath(__file__))
site.addsitedir(os.path.join(here,"../.."))
from metareadability import byline


# list of tuples: (html_snippet, expected_result)
test_data = [
    #
    ("""<li class="article-meta-author">by <a class='i-author' href='http://www.walesonline.co.uk/authors/martin-shipton/'>Martin Shipton</a>, Western Mail</li>""",
    [{"name":u"Martin Shipton"},]
    ),

    #
    ("""<a href="/standard-home/columnistarchive/Dick Murray, Transport Correspondent-columnist-3966-archive.do">Dick Murray, Transport Correspondent</a></strong>""",
    [{"name":u"Dick Murray"},]
    ),

    #
    ("""
    <h4 class="left padding7north" style="font-size: 12px;">
			By <span class="bold">Robert Gore-Langton</span>
		</h4>
    """,
    [{"name":u"Robert Gore-Langton"},]
    ),

    #
    ("""
    <p class="info">
            <author>By Jane Kirby and Hugh Macknight</author><br/>

            <em>Friday, 24 June 2011</em>
        </p>
    """,
    [{"name":u"Jane Kirby"},{"name":u"Hugh Macknight"}]
    ),

    #
    ("""<li class="byline">
					                        	        	        	            <a class='contributor'  rel='author' href='http://www.guardian.co.uk/profile/jackshenker'>
	            																		Jack Shenker</a> in Cairo
				</li>
    """,
    [{"name":u"Jack Shenker"},]
    ),

    #
    ("""<li class="byline">
					                        	        	        	            <a class='contributor'  rel='author' href='http://www.guardian.co.uk/profile/ianblack'>
	            																		Ian Black</a>, <a href="http://www.guardian.co.uk/world/middleeast" title="More from guardian.co.uk on Middle East">Middle East</a> editor
				</li>
    """,
    [{"name":u"Ian Black"},]
    ),
    #

    ("""<li class="byline">
					                        	        	        	        	            <a class='contributor'  rel='author' href='http://www.guardian.co.uk/profile/carolinedavies'>
	            																		Caroline Davies</a> and <a class='contributor'  rel='author' href='http://www.guardian.co.uk/profile/jamesrobinson'>
	            																		James Robinson</a>

				</li>
    """,
    [{"name":u"Caroline Davies"},{"name":u"James Robinson"}]
    ),

    #
    ("""<h4 class="left author" style="font-size: 12px;">By <span class="bold">Peter Dyke &amp; Katie Begley</span></h4>""",
    [{"name":u"Peter Dyke"},{"name":u"Katie Begley"}]
    ),

    #
    ("""<div class="asset-meta">


        Posted by <a href="http://feltham.hounslowchronicle.co.uk/jessica_thompson"/><a href="http://www.hounslowchronicle.co.uk">Jessica Thompson</a></a> on Aug 25, 11 11:24 AM

<a href="http://feltham.hounslowchronicle.co.uk/local-authority/"> in Local Authority</a>

</div>
""",
    [{"name":u"Jessica Thompson"},]
    ),


    # http://yourcardiff.walesonline.co.uk/2011/08/30/river-taff-makes-most-improved-rivers-list/
    (u"""<div class="post_meta">
By
<a rel="author" title="Posts by Brendan Hughes" href="http://yourcardiff.walesonline.co.uk/author/brendan-hughes/">Brendan Hughes</a>
<span class="dot">\xe2</span>
August 30, 2011
<span class="dot">\xe2</span>
<a href="#comments">Post a comment</a>
</div>""",
    [{"name":u"Brendan Hughes"},]
    ),

    ]


class TestBylines(unittest.TestCase):

    def setUp(self):
        pass


    def cmp(self,expected,got):

        expected_names = set([a['name'] for a in expected])
        got_names = set([a['name'] for a in got])

        if got_names == expected_names:
            return True
        else:
            print >>sys.stderr,"ERROR: expected '%s', got '%s'" % (list(expected_names), list(got_names))
            return False


    def runTest(self):
        """ check that the failsafe set of articles give the expected results """

        failcnt = 0
        for (html_fragment,expected) in test_data:
            doc = lxml.html.fromstring(html_fragment)
            parts = byline.tokenise_byline(doc)
            authors, score = byline.parse_byline_parts(parts)

            if not self.cmp(expected,authors):
                failcnt += 1

        self.assertEqual(failcnt, 0)



foo = TestBylines()
foo.runTest()


