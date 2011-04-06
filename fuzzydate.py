import re
import dateutil.tz


class fuzzydate:
    def __init__(self, year=None, month=None, day=None, hour=None, minute=None, second=None, microsecond=None, tzinfo=None):
        self.year=year
        self.month=month
        self.day=day
        self.hour=hour
        self.minute=minute
        self.second=second
        self.microsecond=microsecond
        self.tzinfo=tzinfo
    def empty_date(self):
        return self.year is None and self.month is None and self.day is None
    def empty_time(self):
        return self.hour is None and self.minute is None and self.second is None and self.microsecond is None and self.tzinfo is None
    def empty(self):
        return self.empty_date() and self.empty_time()
    def __repr__(self):
        return "%s-%s-%s %s:%s:%s %s" %(self.year,self.month,self.day, self.hour,self.minute, self.second, self.tzinfo)
    @classmethod
    def combine(cls, *args):
        fd = fuzzydate()
        for a in args:
            fd.year = fd.year if a.year is None else a.year
            fd.month = fd.month if a.month is None else a.month
            fd.day = fd.day if a.day is None else a.day
            fd.hour = fd.hour if a.hour is None else a.hour
            fd.minute = fd.minute if a.minute is None else a.minute
            fd.second = fd.second if a.second is None else a.second
            fd.microsecond = fd.microsecond if a.microsecond is None else a.microsecond
            fd.tzinfo = fd.tzinfo if a.tzinfo is None else a.tzinfo
        return fd
        

# order is important(ish) - want to match as much of the string as we can
date_crackers = [

    #"Tuesday 16 December 2008"
    #"Tue 29 Jan 08"
    #"Monday, 22 October 2007"
    #"Tuesday, 21st January, 2003"
    r'(?P<dayname>\w{3,})[,\s]+(?P<day>\d{1,2})(?:st|nd|rd|th)?\s+(?P<month>\w{3,})[,\s]+(?P<year>(\d{4})|(\d{2}))',

    # "Friday    August    11, 2006"
    # "Tuesday October 14 2008"
    # "Thursday August 21 2008"
    r'(?P<dayname>\w{3,})[,\s]+(?P<month>\w{3,})\s+(?P<day>\d{1,2})(?:st|nd|rd|th)?[,\s]+(?P<year>(\d{4})|(\d{2}))',

    # "9 Sep 2009", "09 Sep, 2009", "01 May 10"
    # "23rd November 2007", "22nd May 2008"
    r'(?P<day>\d{1,2})(?:st|nd|rd|th)?\s+(?P<month>\w{3,})[,\s]+(?P<year>(\d{4})|(\d{2}))',
    # "Mar 3, 2007", "Jul 21, 08", "May 25 2010", "May 25th 2010", "February 10 2008"
    r'(?P<month>\w{3,})\s+(?P<day>\d{1,2})(?:st|nd|rd|th)?[,\s]+(?P<year>(\d{4})|(\d{2}))',

    # "2010-04-02"
    r'(?P<year>\d{4})-(?P<month>\d{1,2})-(?P<day>\d{1,2})',
    # "2007/03/18"
    r'(?P<year>\d{4})/(?P<month>\d{1,2})/(?P<day>\d{1,2})',
    # "22/02/2008"
    r'(?P<day>\d{1,2})/(?P<month>\d{1,2})/(?P<year>\d{4})',
    # "22-02-2008"
    r'(?P<day>\d{1,2})-(?P<month>\d{1,2})-(?P<year>\d{4})',
    # "09-Apr-2007", "09-Apr-07"
    r'(?P<day>\d{1,2})-(?P<month>\w{3,})-(?P<year>(\d{4})|(\d{2}))',


    # TODO:
    # dd/mm/yy
    # mm/dd/yy
    # dd.mm.yy
    # etc...
    # YYYYMMDD

    # TODO:
    # year/month only

     # "May 2011"
    r'(?P<month>\w{3,})\s+(?P<year>\d{4})',
]
date_crackers = [re.compile(pat,re.UNICODE|re.IGNORECASE) for pat in date_crackers]

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


# "BST" ,"+02:00", "+02"
tz_pat = r'(?P<tz>Z|[A-Z]{2,10}|(([-+])(\d{2})((:?)(\d{2}))?))'
ampm_pat = r'(?:(?P<am>am)|(?P<pm>pm))'

time_crackers = [
    #4:48PM GMT
    r'(?P<hour>\d{1,2})[:.](?P<min>\d{2})(?:[:.](?P<sec>\d{2}))?\s*' + ampm_pat + r'\s*' + tz_pat,
    #3:34PM
    #10:42 am
    r'(?P<hour>\d{1,2})[:.](?P<min>\d{2})(?:[:.](?P<sec>\d{2}))?\s*' + ampm_pat,
    #13:21:36 GMT
    #15:29 GMT
    #12:35:44+00:00
    #00.01 BST
    r'(?P<hour>\d{1,2})[:.](?P<min>\d{2})(?:[:.](?P<sec>\d{2}))?\s*' + tz_pat,
    #12.33
    #14:21
    r'(?P<hour>\d{1,2})[:.](?P<min>\d{2})(?:[:.](?P<sec>\d{2}))?\s*',

    # TODO: add support for microseconds?
]
time_crackers = [re.compile(pat,re.UNICODE|re.IGNORECASE) for pat in time_crackers]


def parse_date(s):
    for c in date_crackers:
        m = c.search(s)
        if not m:
            continue

        g = m.groupdict()

        year,month,day = (None,None,None)

        if 'year' in g:
            year = int(g['year'])
            if year < 100:
                year = year+2000

        if 'month' in g:
            month = month_lookup.get(g['month'].lower(),None)
            if month is None:
                continue    # not a valid month name (or number)

        if 'day' in g:
            day = int(g['day'])
            if day<1 or day>31:    # TODO: should take month into account
                continue

        if year is not None or month is not None or day is not None:
            return (fuzzydate(year,month,day),m.span())

    return (fuzzydate(),None)



def parse_time(s):
    for cracker in time_crackers:
        m = cracker.search(s)
        if not m:
            continue

        g = m.groupdict()

        hour,minute,second,microsecond,tzinfo = (None,None,None,None,None)

        if g.get('hour', None) is not None:
            hour = int(g['hour'])

            # convert to 24 hour time
            # if no am/pm, assume 24hr
            if g.get('pm',None) is not None and hour>=1 and hour <=11:
                hour = hour + 12
            if g.get('am',None) is not None and hour==12:
                hour = hour - 12

        if g.get('min', None) is not None:
            minute = int(g['min'])

        if g.get('sec', None) is not None:
            second = int(g['sec'])

        if g.get('tz', None) is not None:
            tzinfo = dateutil.tz.gettz(g['tz'])


        if hour is not None or min is not None or sec is not None:
            return (fuzzydate(hour=hour,minute=minute,second=second,microsecond=microsecond,tzinfo=tzinfo),m.span())

    return (fuzzydate(),None)


def parse_datetime(s):
    # TODO: include ',', 'T', 'at', 'on' between  date and time in the matched span...

    date,datespan = parse_date(s)
    time,timespan = parse_time(s)
    fd = fuzzydate.combine(date,time)
#    print "%s -> %s" % (s,fd)
    return fd



# examples from the wild:
tests = [
    "2010-04-02T12:35:44+00:00", #(iso8601, bbc blogs)
    "2008-03-10 13:21:36 GMT", #(technorati api)
    "9 Sep 2009 12.33", #(heraldscotland blogs)
    "May 25 2010 3:34PM", #(thetimes.co.uk)
    "Thursday August 21 2008 10:42 am", #(guardian blogs in their new cms)
    'Tuesday October 14 2008 00.01 BST', #(Guardian blogs in their new cms)
    'Tuesday 16 December 2008 16.23 GMT', #(Guardian blogs in their new cms)
    "3:19pm on Tue 29 Jan 08", #(herald blogs)
    "2007/03/18 10:59:02",
    "Mar 3, 2007 12:00 AM",
    "Jul 21, 08 10:00 AM", #(mirror blogs)
    "09-Apr-2007 00:00", #(times, sundaytimes)
    "4:48PM GMT 22/02/2008", #(telegraph html articles)
    "09-Apr-07 00:00", #(scotsman)
    "Friday    August    11, 2006", #(express, guardian/observer)
    "26 May 2007, 02:10:36 BST", #(newsoftheworld)
    "2:43pm BST 16/04/2007", #(telegraph, after munging)
    "20:12pm 23rd November 2007", #(dailymail)
    "2:42 PM on 22nd May 2008", #(dailymail)
    "February 10 2008 22:05", #(ft)
    "22 Oct 2007, #(weird non-ascii characters) at(weird non-ascii characters)11:23", #(telegraph blogs OLD!)
    'Feb 2, 2009 at 17:01:09', #(telegraph blogs)
    "18 Oct 07, 04:50 PM", #(BBC blogs)
    "02 August 2007  1:21 PM", #(Daily Mail blogs)
    'October 22, 2007  5:31 PM', #(old Guardian blogs, ft blogs)
    'October 15, 2007', #(Times blogs)
    'February 12 2008', #(Herald)
    'Monday, 22 October 2007', #(Independent blogs, Sun (page date))
    '22 October 2007', #(Sky News blogs)
    '11 Dec 2007', #(Sun (article date))
    '12 February 2008', #(scotsman)
    '03/09/2007', #(Sky News blogs, mirror)
    'Tuesday, 21 January, 2003, 15:29 GMT', #(historical bbcnews)
    '2003/01/21 15:29:49', #(historical bbcnews (meta tag))
    '2010-07-01',
    '2010/07/01',
    'Feb 20th, 2000',
    'May 2008',
    '3:15+10',
]

#for d in tests:
#    parse_datetime(d)

