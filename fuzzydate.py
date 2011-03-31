import re
from datetime import datetime

# "Wednesday, October 21 2009, 17:46 BST"

# weekdayname, month, dayofmonth, year hour:min timezone

month_lookup = {
    '01': 1, '1':1, 'jan': 1, 'january': 1,
    '02': 2, '2':2, 'feb': 2, 'february': 2,
    '03': 3, '3':3, 'mar': 3, 'march': 3,
    '04': 4, '4':4, 'apr': 4, 'april': 4,
    '05': 5, '5':5, 'may': 5, 'may': 5,
    '06': 6, '6':6, 'jun': 6, 'june': 6,
    '07': 7, '7':7, 'jul': 7, 'july': 7,
    '08': 8, '8':8, 'aug': 8, 'august': 8,
    '09': 9, '9':9, 'sep': 9, 'september': 9,
    '10': 10, '10':10, 'oct': 10, 'october': 10,
    '11': 11, '11':11, 'nov': 11, 'november': 11,
    '12': 12, '12':12, 'dec': 12, 'december': 12 }


# various different datetime formats
datecrackers = [
    # "2010-04-02T12:35:44+00:00" (iso8601, bbc blogs)
    re.compile( r"(?P<year>\d{4})-(?P<month>\d\d)-(?P<day>\d\d)T(?P<hour>\d\d):(?P<min>\d\d):(?P<sec>\d\d)", re.UNICODE ),
    # "2008-03-10 13:21:36 GMT" (technorati api)
    re.compile( """(?P<year>\d{4})-(?P<month>\d\d)-(?P<day>\d\d)\s+(?P<hour>\d\d):(?P<min>\d\d):(?P<sec>\d\d)""", re.UNICODE ),
    # "9 Sep 2009 12.33" (heraldscotland blogs)
    re.compile( r"(?P<day>\d{1,2})\s+(?P<month>\w+)\s+(?P<year>\d{4})\s+(?P<hour>\d{1,2})[.:](?P<min>\d\d)", re.UNICODE ),
    # "May 25 2010 3:34PM" (thetimes.co.uk)
    # "Thursday August 21 2008 10:42 am" (guardian blogs in their new cms)
    re.compile( r'\w+\s+(?P<month>\w+)\s+(?P<day>\d{1,2})\s+(?P<year>\d{4})\s+(?P<hour>\d{1,2}):(?P<min>\d\d)\s*((?P<am>am)|(?P<pm>pm))', re.UNICODE|re.IGNORECASE ),
    # 'Tuesday October 14 2008 00.01 BST' (Guardian blogs in their new cms)
    re.compile( r'\w+\s+(?P<month>\w+)\s+(?P<day>\d{1,2})\s+(?P<year>\d{4})\s+(?P<hour>\d{1,2})[:.](?P<min>\d\d)\s+', re.UNICODE|re.IGNORECASE ),
    # 'Tuesday 16 December 2008 16.23 GMT' (Guardian blogs in their new cms)
    re.compile( r'\w+\s+(?P<day>\d{1,2})\s+(?P<month>\w+)\s+(?P<year>\d{4})\s+(?P<hour>\d{1,2})[:.](?P<min>\d\d)\s+', re.UNICODE|re.IGNORECASE ),
    
    # 3:19pm on Tue 29 Jan 08 (herald blogs)
    re.compile( """(?P<hour>\d+):(?P<min>\d\d)\s*((?P<am>am)|(?P<pm>pm))\s+(on\s+)?(\w+)\s+(?P<day>\d+)\s+(?P<month>\w+)\s+(?P<year>\d+)""", re.UNICODE|re.IGNORECASE ),
    # "2007/03/18 10:59:02"
    re.compile( """(?P<year>\d{4})/(?P<month>\d\d)/(?P<day>\d\d) (?P<hour>\d\d):(?P<min>\d\d):(?P<sec>\d\d)""", re.UNICODE ),

    # "Mar 3, 2007 12:00 AM"
    # "Jul 21, 08 10:00 AM" (mirror blogs)
    re.compile( """((?P<month>[A-Z]\w{2}) (?P<day>\d+), (?P<year>\d{2,4}) (?P<hour>\d\d):(?P<min>\d\d) ((?P<am>AM)|(?P<pm>PM)))""", re.UNICODE ),

    # "09-Apr-2007 00:00" (times, sundaytimes)
    re.compile( """(?P<day>\d\d)-(?P<month>\w+)-(?P<year>\d{4}) (?P<hour>\d\d):(?P<min>\d\d)""", re.UNICODE ),

    # "4:48PM GMT 22/02/2008" (telegraph html articles)
    re.compile( "(?P<hour>\d{1,2}):(?P<min>\d\d)\s*((?P<am>am)|(?P<pm>pm))\s+GMT\s+(?P<day>\d{1,2})/(?P<month>\d{1,2})/(?P<year>\d{2,4})", re.UNICODE|re.IGNORECASE ),

    # "09-Apr-07 00:00" (scotsman)
    re.compile( """(?P<day>\d\d)-(?P<month>\w+)-(?P<year>\d{2}) (?P<hour>\d\d):(?P<min>\d\d)""", re.UNICODE ),

    # "Friday    August    11, 2006" (express, guardian/observer)
    re.compile( """\w+\s+(?P<month>\w+)\s+(?P<day>\d+),?\s*(?P<year>\d{4})""", re.UNICODE ),

    # "26 May 2007, 02:10:36 BST" (newsoftheworld)
    re.compile( """(?P<day>\d\d) (?P<month>\w+) (?P<year>\d{4}), (?P<hour>\d\d):(?P<min>\d\d):(?P<sec>\d\d) BST""", re.UNICODE ),

    # "2:43pm BST 16/04/2007" (telegraph, after munging)
    re.compile( "(?P<hour>\d{1,2}):(?P<min>\d\d)\s*((?P<am>am)|(?P<pm>pm))\s+BST\s+(?P<day>\d{1,2})/(?P<month>\d{1,2})/(?P<year>\d{2,4})", re.UNICODE|re.IGNORECASE ),

    # "20:12pm 23rd November 2007" (dailymail)
    # "2:42 PM on 22nd May 2008" (dailymail)
    re.compile( r"(?P<hour>\d{1,2}):(?P<min>\d\d)\s*((?P<am>am)|(?P<pm>pm))\s+(?:on\s+)?(?P<day>\d{1,2})\w+\s+(?P<month>\w+)\s+(?P<year>\d{4})", re.UNICODE|re.IGNORECASE),
    # "February 10 2008 22:05" (ft)
    re.compile( """(?P<month>\w+)\s+(?P<day>\d+)\s+(?P<year>\d{4})\s+(?P<hour>\d{1,2}):(?P<min>\d\d)""", re.UNICODE ),


    # "22 Oct 2007 (weird non-ascii characters) at(weird non-ascii characters)11:23" (telegraph blogs OLD!)
#    re.compile( """(?P<day>\d{1,2}) (?P<month>\w+) (?P<year>\d{4}).*?at.*?(?P<hour>\d{1,2}):(?P<min>\d\d)""", re.UNICODE|re.DOTALL ),
    # 'Feb 2, 2009 at 17:01:09' (telegraph blogs)
    re.compile( r"(?P<month>\w+)\s+(?P<day>\d{1,2}), (?P<year>\d{4}).*?at.*?(?P<hour>\d\d):(?P<min>\d\d):(?P<sec>\d\d)", re.UNICODE|re.DOTALL ),
 
    # "18 Oct 07, 04:50 PM" (BBC blogs)
    # "02 August 2007  1:21 PM" (Daily Mail blogs)
    re.compile( """(?P<day>\d{1,2}) (?P<month>\w+) (?P<year>\d{2,4}),?\s+(?P<hour>\d{1,2}):(?P<min>\d\d) ((?P<am>AM)|(?P<pm>PM))?""", re.UNICODE ),

    # 'October 22, 2007  5:31 PM' (old Guardian blogs, ft blogs)
    re.compile( """((?P<month>\w+)\s+(?P<day>\d+),\s+(?P<year>\d{4})\s+(?P<hour>\d{1,2}):(?P<min>\d\d)\s*((?P<am>AM)|(?P<pm>PM)))""", re.UNICODE|re.IGNORECASE ),

    # 'October 15, 2007' (Times blogs)
    # 'February 12 2008' (Herald)
    re.compile( """(?P<month>\w+)\\s+(?P<day>\d+),?\\s+(?P<year>\d{4})""", re.UNICODE ),
    
    # 'Monday, 22 October 2007' (Independent blogs, Sun (page date))
    re.compile( """\w+,\s+(?P<day>\d+)\s+(?P<month>\w+)\s+(?P<year>\d{4})""", re.UNICODE ),
    
    # '22 October 2007' (Sky News blogs)
    # '11 Dec 2007' (Sun (article date))
    # '12 February 2008' (scotsman)
    re.compile( """(?P<day>\d+)\s+(?P<month>\w+)\s+(?P<year>\d{4})""", re.UNICODE ),
    # '03/09/2007' (Sky News blogs, mirror)
    re.compile( """(?P<day>\d{1,2})/(?P<month>\d{1,2})/(?P<year>\d{4})""", re.UNICODE ),

    #'Tuesday, 21 January, 2003, 15:29 GMT' (historical bbcnews)
    re.compile( r"(?P<day>\d{1,2})\s+(?P<month>\w+),?\s+(?P<year>\d{4}),?\s+(?P<hour>\d{1,2}):(?P<min>\d\d)", re.UNICODE ),
    # '2003/01/21 15:29:49' (historical bbcnews (meta tag))
    re.compile( r"(?P<year>\d{4})/(?P<month>\d{1,2})/(?P<day>\d{1,2})\s+(?P<hour>\d{1,2}):(?P<min>\d\d):(?P<sec>\d\d)", re.UNICODE ),
    # '2010-07-01'
    # '2010/07/01'
    re.compile( """(?P<year>\d{4})[-/](?P<month>\d{1,2})[-/](?P<day>\d{1,2})""", re.UNICODE ),

    ]


def parse( datestring, usa_format=False ):
    """Parse a date string in a variety of formats. Raises an exception if no dice"""

    def GetGroup(m,nm):
        """cheesy little helper for ParseDateTime()"""
        try:
            return m.group( nm )
        except IndexError:
            return None

    #DEBUG:
    #print "DATE: "
    #print datestring
    #print "\n"

    if usa_format:
        # swap day and month if both are numeric
        datestring = re.sub( r'(\d{1,2})([-/])(\d{1,2})([-/])(\d{2,4})', r'\3\2\1\4\5', datestring )


    for c in datecrackers:
        m = c.search( datestring )
        if not m:
            continue

        #DEBUG:
        #print "MONTH: "
        #print m.group( 'month' )
        #print "\n"

        day = int( m.group( 'day' ) )
        month = month_lookup.get(m.group('month'),None)
        if month is None:
            continue

        year = int( m.group( 'year' ) )
        if year < 100:
            year = year+2000

        hour = GetGroup(m,'hour')
        if not hour:
            return datetime( year,month,day )
        hour = int( hour )

        # convert to 24 hour time
        # if no am/pm, assume 24hr
        if GetGroup(m,'pm') and hour>=1 and hour <=11:
            hour = hour + 12
        if GetGroup(m,'am') and hour==12:
            hour = hour - 12

        # if hour present, min will be too
        min = int( m.group( 'min' ) )

        # sec might be missing
        sec = GetGroup( m,'sec' )
        if not sec:
            return datetime( year,month,day,hour,min )
        sec = int( sec )

        return datetime( year,month,day,hour,min,sec )

    return None


