from datetime import date
from lxml import etree
import re

import constants as c


class XBRL:

    def __init__(self, XBRLInstanceLocation, opener=None):
        self.XBRLInstanceLocation = XBRLInstanceLocation
        self.fields = {}

        if opener:
            # Allow us to read directly from a ZIP archive without extracting
            # the whole thing.
            self.EntireInstanceDocument = opener(XBRLInstanceLocation, 'r').read()
        else:
            self.EntireInstanceDocument = open(XBRLInstanceLocation, 'r').read()

        self.oInstance = etree.fromstring(self.EntireInstanceDocument)
        self.ns = {}
        for k in self.oInstance.nsmap.keys():
            if k is not None:
                self.ns[k] = self.oInstance.nsmap[k]
        self.ns['xbrli'] = 'http://www.xbrl.org/2003/instance'
        self.ns['xlmns'] = 'http://www.xbrl.org/2003/instance'
        self.GetBaseInformation()
        # self.loadYear()

        self._context_start_dates = {}
        self._context_end_dates = {}

    # def loadYear(self):
        # self.currentEnd = self.getNode("//dei:DocumentPeriodEndDate").text

    def getNodeList(self, xpath, root=None):
        if root is None:
            root = self.oInstance
        oNodelist = root.xpath(xpath, namespaces=self.ns)
        return oNodelist

    def getNode(self, xpath, root=None):
        oNodelist = self.getNodeList(xpath, root)
        if len(oNodelist):
            return oNodelist[0]
        return None

    def iter_namespace(self, ns='us-gaap'):
        """
        Iterates over all namespace elements, yielding each one.
        """
        SeekConcept = '%s:*' % (ns,)
        node_list = self.getNodeList("//" + SeekConcept)
        for node in node_list:
            yield node

    def GetFactValue(self, SeekConcept, ConceptPeriodType):
        factValue = None
        if ConceptPeriodType == c.INSTANT:
            ContextReference = self.fields['ContextForInstants']
        elif ConceptPeriodType == c.DURATION:
            ContextReference = self.fields['ContextForDurations']
        else:
            # An error occured
            return "CONTEXT ERROR"

        if not ContextReference:
            return None

        oNode = self.getNode("//" + SeekConcept + "[@contextRef='" + ContextReference + "']")
        if oNode is not None:
            factValue = oNode.text
            if 'nil' in oNode.keys() and oNode.get('nil') == 'true':
                factValue = 0
            # set the value to ZERO if it is nil
            # if type(factValue)==str:
            try:
                factValue = float(factValue)
            except:
                # print 'couldnt convert %s=%s to string' % (SeekConcept,factValue)
                factValue = None
                pass

        return factValue

    def GetBaseInformation(self):
        for node in self.iter_namespace(ns='dei'):
            tag = re.search('[^{}]*$', node.tag).group()
            self.fields[tag] = node.text

        # This is super ugly
        # Instances context references are listed in <xbrli:context> blocks --> "//xbrli:context"
        # We want the child period that is instance type --> "[(xbrli:period[xbrli:instant"
        # With text value of DocumentPeriodEndDate --> '[text()="{0}"]])'.format(x.fields['DocumentPeriodEndDate']
        # But there are many contextRefs with this date.  We want the "root" one with no segments --> "and (xbrli:entity[not (xbrli:segment)])]"
        context = '//xbrli:context'
        period = '[(xbrli:period'
        instant = '[xbrli:instant'
        duration = '[xbrli:endDate'
        text = '[text()="{0}"]])'.format(self.fields['DocumentPeriodEndDate'])
        entity = ' and (xbrli:entity'
        segment = '[not (xbrli:segment)])]'
        instant_xpath = context + period + instant + text + entity + segment
        duration_xpath = context + period + duration + text + entity + segment
        self.fields['ContextForInstants'] = self.oInstance.xpath(instant_xpath,
                                                                 namespaces=self.ns)[0].get('id')
        self.fields['ContextForDurations'] = self.oInstance.xpath(duration_xpath,
                                                                  namespaces=self.ns)[0].get('id')

    def get_context_start_date(self, context_id):
        if context_id not in self._context_start_dates:
            node = self.getNode("//xbrli:context[@id='" + context_id + "']/xbrli:period/xbrli:startDate")
            if node is None:
                node = self.getNode("//xbrli:context[@id='" + context_id + "']/xbrli:period/xbrli:instant")
            dt = None
            if node is not None and node.text:
                dt = date(*map(int, node.text.split('-')))
            self._context_start_dates[context_id] = dt
        return self._context_start_dates[context_id]

    def get_context_end_date(self, context_id):
        if context_id not in self._context_end_dates:
            node = self.getNode("//xbrli:context[@id='" + context_id + "']/xbrli:period/xbrli:endDate")
            dt = None
            if node is not None and node.text:
                dt = date(*map(int, node.text.split('-')))
            self._context_end_dates[context_id] = dt
        return self._context_end_dates[context_id]
