import re
from datetime import date

from lxml import etree

import constants as c


class XBRL:
    def __init__(self, xbrl_instance_location, opener=None):
        self.xbrlInstanceLocation = xbrl_instance_location
        self.fields = {}
        
        if opener:
            # Allow us to read directly from a ZIP archive without extracting
            # the whole thing.
            self.EntireInstanceDocument = opener(xbrl_instance_location, 'r').read()
        else:
            self.EntireInstanceDocument = open(xbrl_instance_location, 'r').read()
         
        self.oInstance = etree.fromstring(self.EntireInstanceDocument)
        self.ns = {}
        for k in self.oInstance.nsmap.keys():
            if k is not None:
                self.ns[k] = self.oInstance.nsmap[k]
        self.ns['xbrli'] = 'http://www.xbrl.org/2003/instance'
        self.ns['xlmns'] = 'http://www.xbrl.org/2003/instance'
        self.get_base_information()
        # self.loadYear()

        self._context_start_dates = {}
        self._context_end_dates = {}

    # def loadYear(self):
    #    self.currentEnd = self.get_node("//dei:DocumentPeriodEndDate").text
            
    def get_node_list(self, xpath, root=None):
        if root is None:
            root = self.oInstance
        node_list = root.xpath(xpath, namespaces=self.ns)
        return node_list
        
    def get_node(self, xpath, root=None):
        node_list = self.get_node_list(xpath, root)
        if len(node_list):
            return node_list[0]
        return None

    def iter_namespace(self, ns='us-gaap'):
        """
        Iterates over all namespace elements, yielding each one.
        """
        seek_concept = '%s:*' % (ns,)
        node_list = self.get_node_list("//" + seek_concept)
        for node in node_list:
            yield node

    def get_fact_value(self, seek_concept, concept_period_type):
                
        fact_value = None
            
        if concept_period_type == c.INSTANT:
            context_reference = self.fields['ContextForInstants']
        elif concept_period_type == c.DURATION:
            context_reference = self.fields['ContextForDurations']
        else:
            # An error occured
            return "CONTEXT ERROR"
        
        if not context_reference:
            return None

        node = self.get_node("//" + seek_concept + "[@contextRef='" + context_reference + "']")
        if node is not None:
            fact_value = node.text
            if 'nil' in node.keys() and node.get('nil') == 'true':
                fact_value = 0
            #     set the value to ZERO if it is nil
            # if type(factValue)==str:
            try:
                fact_value = float(fact_value)
            except:
                # print 'couldnt convert %s=%s to string' % (SeekConcept,factValue)
                fact_value = None
                pass
            
        return fact_value

    def get_base_information(self):
        for node in self.iter_namespace(ns='dei'):
            tag = re.search('[^{}]*$', node.tag).group()
            self.fields[tag] = node.text

        # This is super ugly
        # Instances context references are listed in <xbrli:context> blocks --> "//xbrli:context"
        # We want the child period that is instance type --> "[(xbrli:period[xbrli:instant"
        # With text value of DocumentPeriodEndDate --> '[text()="{0}"]])'.format(x.fields['DocumentPeriodEndDate']
        # But there are many contextRefs with this date.
        # We want the "root" one with no segments --> "and (xbrli:entity[not (xbrli:segment)])]"
        context = '//xbrli:context'
        period = '[(xbrli:period'
        instant = '[xbrli:instant'
        duration = '[xbrli:endDate'
        text = '[text()="{0}"]])'.format(self.fields['DocumentPeriodEndDate'])
        entity = ' and (xbrli:entity'
        segment = '[not (xbrli:segment)])]'
        instant_xpath = context + period + instant + text + entity + segment
        duration_xpath = context + period + duration + text + entity + segment
        self.fields['ContextForInstants'] = self.oInstance.xpath(instant_xpath, namespaces=self.ns)[0].get('id')
        self.fields['ContextForDurations'] = self.oInstance.xpath(duration_xpath, namespaces=self.ns)[0].get('id')

    def get_context_start_date(self, context_id):
        if context_id not in self._context_start_dates:
            node = self.get_node("//xbrli:context[@id='" + context_id + "']/xbrli:period/xbrli:startDate")
            if node is None:
                node = self.get_node("//xbrli:context[@id='" + context_id + "']/xbrli:period/xbrli:instant")
            dt = None
            if node is not None and node.text:
                dt = date(*map(int, node.text.split('-')))
            self._context_start_dates[context_id] = dt
        return self._context_start_dates[context_id]

    def get_context_end_date(self, context_id):
        if context_id not in self._context_end_dates:
            node = self.get_node("//xbrli:context[@id='" + context_id + "']/xbrli:period/xbrli:endDate")
            dt = None
            if node is not None and node.text:
                dt = date(*map(int, node.text.split('-')))
            self._context_end_dates[context_id] = dt
        return self._context_end_dates[context_id]
        
    def get_current_period_and_context_information(self, end_date):
        # Figures out the current period and contexts for the current period instance/duration contexts
        

        self.fields['BalanceSheetDate'] = "ERROR"
        self.fields['IncomeStatementPeriodYTD'] = "ERROR"
        
        self.fields['ContextForInstants'] = "ERROR"
        self.fields['ContextForDurations'] = "ERROR"

        # This finds the period end date for the database table, and instant date (for balance sheet):
        use_context = "ERROR"
        
        # Uses the concept ASSETS to find the correct instance context
        # This finds the Context ID for that end date (has correct <instant> date plus has no dimensions):
        node_list = self.get_node_list(("//us-gaap:Assets | "
                                        "//us-gaap:AssetsCurrent | "
                                        "//us-gaap:LiabilitiesAndStockholdersEquity"))
        context_for_instants = use_context
        self.fields['ContextForInstants'] = context_for_instants
        print(self.fields['ContextForInstants'])
        # This finds the duration context
        # This may work incorrectly for fiscal year ends because the dates cross calendar years
        # Get context ID of durations and the start date for the database table
        node_list = self.get_node_list(("//us-gaap:CashAndCashEquivalentsPeriodIncreaseDecrease | "
                                        "//us-gaap:CashPeriodIncreaseDecrease | "
                                        "//us-gaap:NetIncomeLoss | "
                                        "//dei:DocumentPeriodEndDate"))

        start_date = "ERROR"
        start_date_ytd = "2099-01-01"
        use_context = "ERROR"
        
        # Balance sheet date of current period
        self.fields['BalanceSheetDate'] = end_date
        
        # MsgBox "Instant context is: " + ContextForInstants
        if context_for_instants == "ERROR":
            # MsgBox "Looking for alternative instance context"
            
            context_for_instants = self.look_for_alternative_instance_context()
            self.fields['ContextForInstants'] = context_for_instants
        
        # Income statement date for current fiscal year, year to date
        self.fields['IncomeStatementPeriodYTD'] = start_date_ytd
        
        context_for_durations = use_context
        self.fields['ContextForDurations'] = context_for_durations

    def look_for_alternative_instance_context(self):
        # This deals with the situation where no instance context has no dimensions
        # See if there are any nodes with the document period focus date
        node_list = self.get_node_list("//xbrli:context[xbrli:period/xbrli:instant='" + self.fields['BalanceSheetDate'] + "']")

        # MsgBox "Node list length: " + oNodeList_Alt.length
        for node in node_list:
            # Found possible contexts
            # MsgBox node.selectSingleNode("@id").text
            something = self.get_node("//us-gaap:Assets[@contextRef='" + node.get("id") + "']")
            if something is not None:
                # MsgBox "Use this context: " + node.selectSingleNode("@id").text
                return node.get("id")
