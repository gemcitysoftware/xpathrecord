import unittest, libxml2, xpathrecord, datetime

SAMPLE_XML = """
<foo>
  <name date="Bogus Format">This is my name</name>
  <bar arg="1" date="20061028"/>
  <bar arg="2" date="2006-10-28"/>
  <bar arg="stuff" date="10/28/2006"/>
  <bar arg="3" date="2006-10-28 00:00:00"><stuff>I am inside bar</stuff></bar>
  <baz bool="y" average="1.234">Hello World</baz>
  <baz bool="whatever" average="badfloat">Goodbye World</baz>
</foo>
"""

class Stuff(xpathrecord.XPathRecord):
    text = xpathrecord.TextField('text()')

class Bar(xpathrecord.XPathRecord):
    arg       = xpathrecord.TextField('@arg')
    int_arg   = xpathrecord.IntField('@arg')
    has_stuff = xpathrecord.NodeExistsField('stuff/text()')
    stuff     = xpathrecord.TextField('stuff/text()')
    stuffs    = xpathrecord.ChildrenField('stuff', Stuff)
    date      = xpathrecord.DatetimeField('@date', format = "junk")
    textbool  = xpathrecord.BooleanField('stuff/text()', 
                                         true_values = ['i am inside bar'],
                                         false_values = [''])
    
    @staticmethod
    def record_filter(node):
        try:
            x = int(node.prop('arg'))
            return True
        except:
            return False

    def __str__(self):
        return 'Bar: %s, %s, %s' % (self.arg(), self.has_stuff(), self.stuff())
class Baz(xpathrecord.XPathRecord):
    content = xpathrecord.TextField('text()')
    average = xpathrecord.FloatField('@average')
    boolean = xpathrecord.BooleanField('@bool')

class Foo(xpathrecord.XPathRecord):
    name = xpathrecord.TextField('name/text()')
    bar = xpathrecord.ChildrenField('bar', Bar)
    baz = xpathrecord.FirstChildField('baz', Baz)
    date = xpathrecord.DatetimeField('name/@date')

class SimpleTest(unittest.TestCase):
    def setUp(self):
        self.dom = libxml2.parseMemory(SAMPLE_XML, len(SAMPLE_XML))
    
    def tearDown(self):
        del(self.dom)

    def testFoo(self):
        foos = list(Foo.records(self.dom, '/foo'))
        self.assertEquals(1, len(foos))
        foo = foos[0]

        try:
            when = foo.date()
            self.fail('Should have thrown an exception for a bad date')
        except ValueError:
            pass

        baz = foo.baz()
        self.assertEquals('Hello World', baz.content())
        self.assertAlmostEquals(1.234, baz.average())

        bars = list(foo.bar())
        self.assertEquals(3, len(bars))
        for bar in bars:
            if bar.has_stuff():
                self.assertEquals('I am inside bar', bar.stuff())
                self.assertEquals(1, sum(1 for stuff in bar.stuffs()))
            else:
                self.assertEquals(0, sum(1 for stuff in bar.stuffs()))
            self.assertEquals(True, bar.arg() in ("1", "2", "3"))

    def testBaz(self):
        bazs = list(Baz.records(self.dom, '//baz'))
        self.assertEquals(2, len(bazs))
        baz = bazs[0]
        self.assertEquals('Hello World', baz.content())
        self.assertAlmostEquals(1.234, baz.average())
        self.assertEquals(True, baz.boolean())

        baz = bazs[1]
        self.assertEquals('Goodbye World', baz.content())
        try:
            self.assertEquals(True, baz.boolean())
            self.fail("Should have thrown a ValueError")
        except ValueError:
            pass
        try:
            self.assertEquals(1.234, baz.average())
            self.fail("Should have thrown a ValueError")
        except ValueError:
            pass

    def testBars(self):
        bars = list(Bar.records(self.dom, '//bar'))
        self.assertEquals(3, len(bars))
        for bar in bars:
            self.assertEquals(datetime.datetime(2006, 10, 28),
                              bar.date())
            if bar.has_stuff():
                self.assertEquals('I am inside bar', bar.stuff())
                self.assertEquals(1, sum(1 for stuff in bar.stuffs()))
            else:
                self.assertEquals(0, sum(1 for stuff in bar.stuffs()))
            self.assertEquals(True, bar.arg() in ("1", "2", "3"))

            self.assertEquals(bar.int_arg(), int(bar.arg()))

            if "3" == bar.arg():
                self.assertEquals(True, bar.textbool())
            else:
                self.assertEquals(False, bar.textbool())
                    
            
            
if '__main__' == __name__:
    unittest.main()
