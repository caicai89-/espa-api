'''
Purpose: lta services client module
Author: David V. Hill
'''

import requests
import collections
import xml.etree.ElementTree as xml
from cStringIO import StringIO

from suds.client import Client as SoapClient
from suds.cache import ObjectCache

from api.domain import sensor
from api.providers.configuration.configuration_provider import ConfigurationProvider
from api.system.logger import ilogger as logger
from api import util as utils

config = ConfigurationProvider()

if config.mode in ('dev', 'tst'):
    import logging
    logging.basicConfig(level=logging.INFO)
    logging.getLogger('suds.client').setLevel(logging.DEBUG)


def check_lta_available():
    """
    Simple wrapper to check if lta is up
    :return: bool
    """
    url = config.url_for('earthexplorer')
    return utils.connections.is_reachable(url, timeout=1)


class LTAService(object):
    ''' Abstract service client for all of LTA services '''

    service_name = None

    def __init__(self):
        self.xml_header = "<?xml version ='1.0' encoding='UTF-8' ?>"
        self.url = config.url_for(self.service_name)
        self.location = self.url.split('?')[0]

    def __repr__(self):
        return "LTAService:{0}".format(self.__dict__)


class LTASoapService(LTAService):
    ''' Abstract service class for SOAP based clients '''

    def __init__(self, *args, **kwargs):
        super(LTASoapService, self).__init__(*args, **kwargs)
        logger.info('Building SoapClient for:{0}'.format(self.url))
        self.client = SoapClient(self.url, location=self.location, cache=self.build_object_cache())

    def build_object_cache(self):
        cache = ObjectCache()
        cache.setduration(seconds=config.get('soap.client_timeout'))
        cache.setlocation(config.get('soap.cache_location'))
        return cache


class RegistrationServiceClient(LTASoapService):

    service_name = 'registration'

    def __init__(self, *args, **kwargs):
        super(RegistrationServiceClient, self).__init__(*args, **kwargs)

    def get_username(self, contactid):
        '''Retrieves the users EE username given their contactid

        Keyword args:
        contactid -- The EE contactid

        Return:
        The EE username
        '''

        return self.client.service.getUserName(contactid)


class OrderUpdateServiceClient(LTASoapService):

    service_name = 'orderupdate'

    def __init__(self, *args, **kwargs):
        super(OrderUpdateServiceClient, self).__init__(*args, **kwargs)

    #TODO - Migrate this call to the OrderWrapperService
    def get_order_status(self, order_number):
        ''' Returns the status of the supplied order number

        Keyword args:
        order_number The EE order number to check status on

        Returns:
        A list of dictionaries containing unit_num, unit_status & sceneid
        '''

        retval = dict()

        # resp = self.client.factory.create("getOrderStatusResponse")
        resp = self.client.service.getOrderStatus(order_number)

        if resp is None:
            return dict()

        retval['order_num'] = str(resp.order.orderNbr)
        retval['order_status'] = str(resp.order.orderStatus)
        retval['units'] = list()

        for u in resp.units.unit:
            unit = dict()
            unit['unit_num'] = int(u.unitNbr)
            unit['unit_status'] = str(u.unitStatus)
            unit['sceneid'] = str(u.orderingId)
            retval['units'].append(unit)

        return retval

    def update_order(self, order_number, unit_number, status):
        ''' Update the status of orders that ESPA is working on

        Keyword args:
        order_number The EE order number to update
        unit_number  The unit within the order to update
        status The EE defined status to set the unit to
               'F' for failed
               'C' for complete
               'R' for rejected

        Returns:
        On success, a tuple (True, None, None)
        On failure, a tuple (False, failure message, failure status)
        '''

        returnval = collections.namedtuple('UpdateOrderResponse',
                                           ['success', 'message', 'status'])

        # resp = self.client.factory.create('StatusOrderReturn')

        try:
            unit_number = int(unit_number)
            status = str(status)
            resp = self.client.service.setOrderStatus(
                orderNumber=str(order_number),
                systemId='EXTERNAL',
                newStatus=status,
                unitRangeBegin=unit_number,
                unitRangeEnd=unit_number)
        except Exception, e:
            raise e

        if resp.status == 'Pass':
            return returnval(success=True, message=None, status=None)
        else:
            return returnval(success=False,
                             message=resp.message,
                             status=resp.status)


class OrderDeliveryServiceClient(LTASoapService):
    '''EE SOAP Service client to find orders for ESPA which originated in EE'''

    service_name = 'orderdelivery'

    def __init__(self, *args, **kwargs):
        super(OrderDeliveryServiceClient, self).__init__(*args, **kwargs)

    def get_available_orders(self):
        ''' Returns all the orders that were submitted for ESPA through EE

        Returns:
        A dictionary of lists that contain dictionaries

        response[ordernumber, email, contactid] = [
            {'sceneid':orderingId, 'unit_num':unitNbr},
            {...}
        ]
        '''
        rtn = dict()
        # resp = self.client.factory.create("getAvailableOrdersResponse")

        try:
            resp = self.client.service.getAvailableOrders("ESPA")
        except Exception, e:
            raise e

        #if there were none jusgetAvailt return
        if len(resp.units) == 0:
            return rtn

        #return these to the caller.
        for u in resp.units.unit:

            #ignore anything that is not for us
            if str(u.productCode).lower() not in ('sr01', 'sr02', 'sr03', 'sr04', 'sr05'):

                logger.warn('{0} is not an ESPA product. Order[{1}] Unit[{2}]'
                            'Product code[{3}]... ignoring'
                             .format(u.orderingId, u.orderNbr,
                                     u.unitNbr, u.productCode))
                # continue

            # get the processing parameters
            pp = u.processingParam

            try:
                email = pp[pp.index("<email>") + 7:pp.index("</email>")]
            except:
                logger.warn('Could not find an email address for '
                            'unit {0} in order {1] : rejecting'
                            .format(u.unitNbr,u.orderNbr))

                # we didn't get an email... fail the order
                resp = OrderUpdateServiceClient().update_order(u.orderNbr,
                                                               u.unitNbr,
                                                               "R")
                # we didn't get a response from the service
                if not resp.success:
                    raise Exception('Could not update order[{0}] unit[{1}] '
                                    'to status:F. Error message:{2} '
                                    'Error status code:{3}'
                                    .format(u.orderNbr,
                                            u.unitNbr,
                                            resp.message,
                                            resp.status))
                else:
                    continue

            try:
                # get the contact id
                cid = pp[pp.index("<contactid>") + 11:pp.index("</contactid>")]
            except:
                logger.warn('Could not find a contactid for unit {0} in '
                            'order {1}... rejecting'
                            .format(u.unitNbr, u.orderNbr))

                # didn't get an email... fail the order
                resp = OrderUpdateServiceClient().update_order(u.orderNbr,
                                                               u.unitNbr,
                                                               "R")
                # didn't get a response from the service
                if not resp.success:
                    raise Exception('Could not update unit {0} in order {1} '
                                    'to status:F. Error message:{2} '
                                    'Error status code:{3}'
                                    .format(u.orderNbr,
                                            u.unitNbr,
                                            resp.message,
                                            resp.status))
                else:
                    continue

            # This is a dictionary that contains a list of dictionaries
            key = (str(u.orderNbr), str(email), str(cid))

            if not key in rtn:
                rtn[key] = list()

            rtn[key].append({'sceneid': str(u.orderingId),
                             'unit_num': int(u.unitNbr)}
                            )

        return rtn


''' This is the public interface that calling code should use to interact
    with this module'''


def get_user_name(contactid):
    return RegistrationServiceClient().get_username(contactid)


def get_available_orders():
    return OrderDeliveryServiceClient().get_available_orders()


def get_order_status(lta_order_number):
    return OrderUpdateServiceClient().get_order_status(lta_order_number)


def update_order_status(lta_order_number, unit_number, new_status):
    return OrderUpdateServiceClient().update_order(lta_order_number,
                                                   unit_number,
                                                   new_status)
