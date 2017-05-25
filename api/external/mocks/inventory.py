
RESOURCE_DEF = {
    'login': {
        "errorCode": None,
        "error": "",
        "data": "9ccf44a1c7e74d7f94769956b54cd889",
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
