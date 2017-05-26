import xml.etree.ElementTree as xml

from api.util import chunkify


def return_update_order_resp(*args, **kwargs):
    class foo(object):
        def success(self):
            return True
    return foo()


def get_user_name(arg1):
    return 'klsmith@usgs.gov'


def update_order_status(ee_order_id, ee_unit_id, something):
    return True, True, True


def update_order_status_fail(ee_order_id, ee_unit_id, something):
    raise Exception('lta comms failed')


def order_scenes(product_list, contact_id):
    chunked_list = chunkify(product_list, 3)
    results = dict()
    results["available"] = [p for p in chunked_list[0]]
    results["ordered"] = [p for p in chunked_list[1]]
    results["invalid"] = [p for p in chunked_list[2]]
    results["lta_order_id"] = "tramorderid1"
    return results


def get_available_orders():
    """
    Needs to return:

    response[ordernumber, email, contactid] = [
            {'sceneid':orderingId, 'unit_num':unitNbr},
            {...}
        ]
    """
    ret = {}
    ret[(123, 'klsmith@usgs.gov', 418781)] = [{'sceneid': 'LE70900652008327EDC00',
                                               'unit_num': 789},
                                              {'sceneid': 'LE70900652008327EDC00',
                                               'unit_num': 780}]
    ret[(124, 'klsmith@usgs.gov', 418781)] = [{'sceneid': 'LE70900652008327EDC00',
                                               'unit_num': 780},
                                              {'sceneid': 'LE70900652008327EDC00',
                                               'unit_num': 799}]
    return ret


def get_available_orders_partial(partial=False):
    ret = {}
    if partial:
        ret[(125, 'klsmith@usgs.gov', 418781)] = [{'sceneid': 'LE70900652008327EDC00',
                                                   'unit_num': 789}]
    else:
        ret[(125, 'klsmith@usgs.gov', 418781)] = [{'sceneid': 'LE70900652008327EDC00',
                                                   'unit_num': 789},
                                                  {'sceneid': 'LT50900652008327EDC00',
                                                   'unit_num': 780}]

    return ret


def sample_tram_order_ids():
    return '0611512239617', '0611512239618', '0611512239619'


def sample_scene_names():
    return 'LC81370432014073LGN00', 'LC81390422014071LGN00', 'LC81370422014073LGN00'


def get_order_status(tramid):
    response = None
    if tramid == sample_tram_order_ids()[0]:
        response = {'units': [{'sceneid':sample_scene_names()[0], 'unit_status': 'R'}]}
    elif tramid == sample_tram_order_ids()[1]:
        response = {'units': [{'sceneid':sample_scene_names()[1], 'unit_status': 'C'}]}
    elif tramid == sample_tram_order_ids()[2]:
        response = {'units': [{'sceneid':sample_scene_names()[2], 'unit_status': 'R'}]}
    else:
        response = {'units': [{'sceneid': sample_scene_names()[0], 'unit_status': 'C'}]}
    return response


class MockLTAUnit(object):

    def __init__(self, order_number=100):
        self.processingParam = ('<email></email>'
                           '<contactid></contactid>')
        self.productCode = 'sr01'
        self.orderingId = 6000
        self.orderNbr = order_number
        self.unitNbr = 101
        self.orderStatus = 'C'
        self.unitStatus = 'C'


class MockLTAService(object):
    unit = None
    def __init__(self):
        self.unit = [MockLTAUnit() for _ in range(3)]

    def __len__(self):
        return len(self.unit)


class MockSudsClient(object):
    def __init__(self, *args, **kwargs):
        pass

    class service(object):
        def getAvailableOrders(self, requestor):
            self.units = MockLTAService()
            return self

        def getOrderStatus(self, order_number):
            self.order = MockLTAUnit(order_number)
            return self

        def setOrderStatus(self, orderNumber, systemId, newStatus, unitRangeBegin, unitRangeEnd):
            self.message = ''
            if orderNumber == 'failure':
                self.status = None
            else:
                self.status = 'Pass'
            return self

    service = service()