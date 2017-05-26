import copy

RESOURCE_DEF = {
    'login': {
        "errorCode": None,
        "error": "",
        "data": "2fd976601eef1ebd632b545a8fef11a3",
        "api_version": "1.2.1"
    },
    'logout': {
        "errorCode": None,
        "error": "",
        "data": True,
        "api_version": "1.2.1"
    },
    'idLookup': {
        "errorCode": None,
        "error": "",
        "data": {
            "LC08_L1TP_156063_20170207_20170216_01_T1": {
                "entityId": "LC81560632017038LGN00",
                "dispalyId": "LC08_L1TP_156063_20170207_20170216_01_T1",
                "orderingId": "LC81560632017038LGN00",
            },
            "LE07_L1TP_028028_20130510_20160908_01_T1": {
                "entityId": "LE70280282013130EDC00",
                "dispalyId": "LE07_L1TP_028028_20130510_20160908_01_T1",
                "orderingId": "LE70280282013130EDC00",
            },
            "LT05_L1TP_032028_20120425_20160830_01_T1" : {
                    "entityId": "LT50320282012116EDC00",
                    "dispalyId": "LT05_L1TP_032028_20120425_20160830_01_T1",
                    "orderingId": "LT50320282012116EDC00",
            },
            "INVALID_ID": None
        }
    },
    'download': {
        "errorCode": None,
        "error": "",
        "data": [
            "http://invalid.com/path/to/downloads/l1/2014/013/029/LC81560632017038LGN00.tar.gz?iid=LC81560632017038LGN00&amp;did=63173803&amp;ver="
            "http://invalid.com/path/to/downloads/l1/2014/013/029/LE70280282013130EDC00.tar.gz?iid=LE70280282013130EDC00&amp;did=63173803&amp;ver="
            "http://invalid.com/path/to/downloads/l1/2014/013/029/LT50320282012116EDC00.tar.gz?iid=LT50320282012116EDC00&amp;did=63173803&amp;ver="
        ],
        "api_version": "1.2.1"
    },
    'userContext': {
        "errorCode": None,
        "error": "",
        "data": True
    },
    'clearUserContext': {
        "errorCode": None,
        "error": "",
        "data": True
    }
}


class RequestsSpoof(object):
    def __init__(self, *args, **kwargs):
        self.url = args[0]
        self.resource = self.url.split('/')[-1]

        self.ok = True
        self.data = RESOURCE_DEF.get(self.resource)
        self.content = str(self.data)

    def __repr__(self):
        message = ('REQUEST SPOOF'
                   '\n\tURL: {}'
                   '\n\tRESOURCE: {}'
                   '\n\tDATA:{}').format(self.url, self.resource, self.data)
        return message

    def json(self):
        return self.data

    def raise_for_status(self):
        pass


class BadRequestSpoofError(RequestsSpoof):
    def __init__(self, *args, **kwargs):
        super(BadRequestSpoofError, self).__init__(*args, **kwargs)
        self.data = copy.deepcopy(self.data)

        if 'data' in self.data:
            self.data['data'] = None
        if 'errorCode' in self.data:
            self.data['errorCode'] = 'UNKNOWN'
        if 'error' in self.data:
            self.data['error'] = 'A fake server error occurred'


class BadRequestSpoofNegative(RequestsSpoof):
    def __init__(self, *args, **kwargs):
        super(BadRequestSpoofNegative, self).__init__(*args, **kwargs)
        self.data = copy.deepcopy(self.data)

        if 'data' in self.data and isinstance(self.data.get('data'), bool):
            self.data['data'] = not(self.data.get('data'))


class CachedRequestPreventionSpoof(object):
    def __init__(self, *args, **kwargs):
        raise RuntimeError('Should only require Cached values!')


# ----------------------------------------+
# Production API testing                  |
def get_cached_download_urls(product_list):
    response = {i: 'http://one_time_use.tar.gz' for i in product_list}
    return response
