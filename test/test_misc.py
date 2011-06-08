#!/usr/bin/env python

import unittest
import site
import lxml.html
site.addsitedir("..")

from metareadability.util import render_text


class TestMiscFunctions(unittest.TestCase):

    def setUp(self):
        pass

    def test_render_text(self):
        """ test the render_text() fn """

        test_html = """<html>
<head></head>
<body>
<div id="test1">Here is some text.</div>
<div id="test2">a <div>div within</div> a div</div>
<span id="test3">leave off the</span>tail
<span id="test4">lots<br/>of<br/>breaks</span>
<span id="test5"><span>spans</span><span>join</span></span>
<span id="test6"><span>spans need</span> <span>explicit whitespace</span></span>
</body>
</html>"""

        tests = [
            ("#test2", u"\na \ndiv within\n a div\n"),
            ("#test1", u"\nHere is some text.\n"),
            ("#test3", u"leave off the"),
            ("#test4", u"lots\nof\nbreaks"),
            ("#test5", u"spansjoin"),
            ("#test6", u"spans need explicit whitespace"),
                ]
        doc = lxml.html.fromstring(test_html)
        for sel,expected in tests:
            el = doc.cssselect(sel)[0]
            self.assertEqual(render_text(el),expected)


if __name__ == '__main__':
    unittest.main()



