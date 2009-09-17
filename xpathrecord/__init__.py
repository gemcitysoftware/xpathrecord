"""
XPathRecord - pulling read-only Python objects out of XML

An example simple RSS reader:

import xpathrecord

class RSSPost(xpathrecord.XPathRecord):
    title = xpathrecord.TextField('title/text()')
    link = xpathrecord.TextField('link/text()')
    pubdate = xpathrecord.DatetimeField('pubDate/text()',
                                        '%a, %d %b %Y %H:%M:%S +0000')

def main():
    import libxml2, urllib2, sys
    for feed_url in sys.argv[1:]:
        doc = urllib2.urlopen(feed_url).read()
        dom = libxml2.parseMemory(doc, len(doc))
        for post in RSSPost.records(dom, '//item'):
            print 'Post:'
            print '\ttitle: %s' % post.title()
            print '\tlink:  %s' % post.link()
            print '\tdate:  %s' % post.pubdate()

if '__main__' == __name__:
    main()
"""

VERSION = '0.3'

# Copyright 2009 Gem City Software
# Distributed under http://creativecommons.org/licenses/by/3.0/

import copy, datetime, re

try:
    strptime = datetime.datetime.strptime
except AttributeError:
    import time
    def strptime(s, fmt):
        return datetime.datetime(*(time.strptime(s, fmt)[:6]))

class Field(object):
    """
    A base class for all field types.  Child classes should
    implement a value() method that uses the DOM node
    passed as its only argument
    """
    pass

class Lazy(object):
    def __init__(self, dom, field):
        self.__cache = None
        self.__dom   = dom
        self.__field = field

    def __call__(self):
        if self.__cache is None:
            self.__cache = self.__field.value(self.__dom)
        return self.__cache

class XPathRecord(object):
    """
    The base class for XPathRecords.  Derive from this,
    set class fields as xpathrecord.Field-derived objects
    and you're good to go.

    Optional:

    Implement a static method record_filter(node).  Given
    your object's root DOM node, it can decide via a True
    or False return value whether or not that particular 
    node should be used to construct an object or not.
    """
    def __init__(self, dom):
        self.__cache = {}
        self.__fields = {}
        self.__dom = dom
        for name in dir(self):
            field = getattr(self, name)
            if isinstance(field, Field):
                setattr(self, name, Lazy(self.__dom, field))

    @classmethod
    def records(cls, dom, xpath = None):
        for node in dom.xpathEval(xpath):
            if cls.record_filter(node):
                yield cls(node)

    @staticmethod
    def record_filter(node):
        return True

class TextField(Field):
    """
    Extract text (either from text() segments or attributes)
    from a DOM tree.

    Constructor args:
    
    * xpath: A relative xpath string

    Constructor kwargs:
    
    None
    """
    def __init__(self, xpath):
        self.__xpath = xpath

    def value(self, dom):
        return ''.join(n.content.strip() for n in 
                       dom.xpathEval(self.__xpath)).strip()

class FloatField(TextField):
    """
    Extract a floating point value (from either text() segments
    or attributes) from a DOM tree.  Raises a ValueError if it can not
    properly convert its value to floating point using the builtin 
    float().

    Constructor args:
    
    * xpath: A relative xpath string

    Constructor kwargs:
    
    None
    """
    def value(self, dom):
        return float(TextField.value(self, dom))

class IntField(TextField):
    """
    Extract an integer value (from either text() segments or
    attributes) from a DOM tree.  Raises a ValueError if it 
    can not properly convert its value to an integer using the
    builtin int().

    Constructor args:
    
    * xpath: A relative xpath string

    Constructor kwargs:
    
    None
    """
    def value(self, dom):
        return int(TextField.value(self, dom))

class BooleanField(TextField):
    """
    Extract an integer value (from either text() segments or
    attributes) from a DOM tree.  Raises a ValueError if it 
    can not properly convert its value to floating point.

    Constructor args:
    
    * xpath: A relative xpath string

    Constructor kwargs:
    
    * true_values: An optional list of strings to be considered
                   the universe of acceptable (case-insensitive)
                   true values.
    * false_values: An optional list of strings to be considered
                    the universe of acceptable (case-insensitive)
                    false values.                   
    """
    DEFAULT_TRUE_VALUES = ('y', 'yes', 'true', 't', 'ok')
    DEFAULT_FALSE_VALUES = ('n', 'no', 'false', 'f', 'nil')

    def __init__(self, xpath, true_values = None, false_values = None):
        TextField.__init__(self, xpath)
        if true_values is None:
            self.__true_values = self.DEFAULT_TRUE_VALUES
        else:
            self.__true_values = tuple(x.lower() for x in true_values)
        if false_values is None:
            self.__false_values = self.DEFAULT_FALSE_VALUES
        else:
            self.__false_values = tuple(x.lower() for x in false_values)
            
    def value(self, dom):
        s = TextField.value(self, dom).strip().lower()
        if s in self.__true_values:
            return True
        elif s in self.__false_values:
            return False
        else:
            raise ValueError('The value (%s) is neither true nor false' % s)
    

class DatetimeField(TextField):
    """
    Extracts a datetime object from a DOM tree.  Raises a ValueError
    if it can not properly convert its value to a datetime

    Constructor args:
    
    * xpath: A relative xpath string

    Constructor kwargs:
    
    * format: a list of datetime.datetime.strptime-compatible date 
              formats.  It will use each format in this list, in order
              to try to parse the text for the date.  If none of them
              work, it will use the formats in DEFAULT_FORMATS (in 
              order).  If none of those work, a ValueError will be
              raised.
              
              For backwards compatibility reasons, format also 
              accepts a single string argument.  This will be 
              tried before any of the DEFAULT_FORMATS.
    """
    DEFAULT_FORMATS = ('%Y-%m-%d %H:%M:%S', 
                       '%Y-%m-%d %H:%M',
                       '%Y-%m-%d',
                       '%Y%m%d',
                       '%m/%d/%Y')
    __kluge_date_re = re.compile('\.\d+ -\d+$')
    def __kluge_date(self, s):
        return self.__kluge_date_re.sub('', s)

    def __init__(self, xpath, format = []):
        TextField.__init__(self, xpath)
        if isinstance(format, str):
            self.__format = (format,)
        else:
            self.__format = tuple(format)

    def value(self, dom):
        s = self.__kluge_date(TextField.value(self, dom))
        for fmt in self.__format + self.DEFAULT_FORMATS:
            try:
                return strptime(s, fmt)
            except:
                pass
        raise ValueError("Can not parse date: %s" % s)

class NodeExistsField(Field):
    """
    Extracts a boolean that says whether or not a node exists.

    Constructor args:
    
    * xpath: A relative xpath string

    Constructor kwargs:
    
    None
    """
    def __init__(self, xpath):
        self.__xpath = xpath

    def value(self, dom):
        return 0 < sum(1 for x in dom.xpathEval(self.__xpath))

class ChildrenField(Field):
    """
    Converts the results of an xpath expression into a sequence of
    XPathRecord objects.

    Constructor args:
    
    * xpath: A relative xpath string
    * cls:   A subclass of XPathRecord

    Constructor kwargs:
    
    None
    """
    def __init__(self, xpath, cls):
        self.__xpath = xpath
        self.__cls   = cls
        
    def value(self, dom):
        for n in dom.xpathEval(self.__xpath):
            for x in self.__cls.records(n, '.'):
                yield x

class FirstChildField(Field):
    """
    Return the first child of an xpath expression as an XPathRecord
    object.

    Constructor args:
    
    * xpath: A relative xpath string
    * cls:   A subclass of XPathRecord

    Constructor kwargs:
    
    None
    """
    def __init__(self, xpath, cls):
        self.__xpath = xpath
        self.__cls   = cls
        
    def value(self, dom):
        for n in dom.xpathEval(self.__xpath):
            for x in self.__cls.records(n, '.'):
                return x


    
