import sys
import re
import lxml.html

import util

cruft_classes = re.compile(r"(combx|comment|disqus|foot|menu|rss|shoutbox|sidebar|sponsor|ad-break|agegate|promo|list|photo|social|singleAd|adx|relatedarea)", re.I)

indicative1 = re.compile(r'^(article|body|entry|hentry|page|post|text|blog|story)$', re.I)
indicative2 = re.compile(r'(entrytext|story_content|bodytext)',re.I)


def pluck(root):

    # remove undesirable elements
    [cruft.drop_tree() for cruft in root.cssselect('meta, img, script, style, input, textarea, ul.breadcrumb')]

    for div in root.cssselect('div'):
        if cruft_classes.search(div.get('class','')) or cruft_classes.search(div.get('id','')):
            div.drop_tree()

    # convert <div>s that should be <p>s
    for div in root.cssselect('div'):
        brs = len([child for child in div if child.tag=='br'])
        if brs>2:
            div.tag='p'


    # try to find common names for containing div
    parents = {}
    for div in root.cssselect('div'):
        id = div.get('id','')
        if indicative1.search(id):
            parents[div] = 50000
        elif indicative2.search(id):
            parents[div] = 75000

    for para in root.cssselect('p'):
        points = calculate_points(para)
        parent = para.getparent()
        if parent in parents:
            parents[parent] += points
        else:
            parents[parent] = points

    winner = max(parents, key=parents.get)
#    for i,score in parents.iteritems():
#        print i.get('id','-na-'), i.get('class','-na-'), score

#    print "winner: #%s .%s" % (winner.get('id',''),winner.get('class',''))

    txt = ''
    for n in winner.findall('.//p'):
        cls = n.get('class','')
        if re.compile(r'^(summary|caption|posted|comment)$', re.I).search(cls):
            continue
        for cruft in n.findall('.//div'):
            n.drop_tree()
        txt = txt + "<p>" + n.text_content() + "</p>\n"

    #print txt
    return txt

def calculate_points(para, starting_points=0):
    # reward for being a new paragraph
    points = starting_points + 20

    # look at the id and class of paragraph and parent
    classes_and_ids = ' '.join((
        para.get('class', ''),
        para.get('id', ''),
        para.getparent().get('class', ''),
        para.getparent().get('id', '')))

    # deduct severely and return if clearly not content
    if re.compile(r'(comment|meta|footer|footnote|posted)', re.I).search(classes_and_ids):
        points -= 5000
        return points

    # reward if probably content
    if re.compile(r'post|hentry|entry|article|story.*', re.I).search(classes_and_ids):
        points += 500

    # look at the actual text of the paragraph
    content = para.text_content().lower()

    # deduct if very short
    if len(content) < 20:
        points -= 50

    # reward if long
    if len(content) > 100:
        points += 50


    # deduct if no periods, question marks, or exclamation points
    if '.' not in content or '?' not in content or '!' not in content:
        points -= 100

    # reward for periods and commas
    points += content.count('.') * 10
    points += content.count(',') * 20
    points += content.count('<br') * 30

    return points


if __name__ == "__main__":
    pluck(sys.argv[1])

