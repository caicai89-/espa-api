
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



class sceneMetadata(RequestsSpoof):
    def __init__(self, *args, **kwargs):
        super(sceneMetadata, self).__init__(*args, **kwargs)

    def json(self):
        return {
            "errorCode": None,
            "error": "",
            "data": [
                {
                    "acquisitionDate": "2014-04-10",
                    "startTime": "2014-04-10",
                    "endTime": "2014-04-10",
                    "lowerLeftCoordinate": {
                        "latitude": 43.95287,
                        "longitude": -73.38717
                    },
                    "upperLeftCoordinate": {
                        "latitude": 45.66895,
                        "longitude": -72.81323
                    },
                    "upperRightCoordinate": {
                        "latitude": 45.24376,
                        "longitude": -70.44335
                    },
                    "lowerRightCoordinate": {
                        "latitude": 43.53155,
                        "longitude": -71.0851
                    },
                    "sceneBounds": "-73.38717,43.53155,-70.44335,45.66895",
                    "browseUrl": "http:\/\/earthexplorer.usgs.gov\/browse\/landsat_8\/2014\/013\/029\/LC80130292014100LGN00.jpg",
                    "dataAccessUrl": "http:\/\/earthexplorer.usgs.gov\/order/process?dataset_name=LANDSAT_8&amp;ordered=LC80130292014100LGN00&amp;node=INVSVC",
                    "downloadUrl": "http:\/\/earthexplorer.usgs.gov\/download\/external\/options\/LANDSAT_8\/LC80130292014100LGN00\/INVSVC\/",
                    "entityId": "LC80130292014100LGN00",
                    "displayId": "LC80130292014100LGN00",
                    "metadataUrl": "http:\/\/earthexplorer.usgs.gov\/metadata\/xml\/4923\/LC80130292014100LGN00\/",
                    "fgdcMetadataUrl": "http:\/\/earthexplorer.usgs.gov\/fgdc\/4923\/LC80130292014100LGN00\/save_xml",
                    "modifiedDate": "2014-07-13",
                    "orderUrl": None,
                    "bulkOrdered": False,
                    "ordered": False,
                    "summary": "Entity ID: LC80130292014100LGN00, Acquisition Date: 10-APR-14, Path: 13, Row: 29",
                }
            ],
            "api_version": "1.0"
        }


class userContext(RequestsSpoof):
    def __init__(self, *args, **kwargs):
        super(userContext, self).__init__(*args, **kwargs)

    def json(self):
        return {
                "errorCode": None,
                "error": "",
                "data": True
            }


def clearUserContext ():
    return NotImplementedError()


class download(RequestsSpoof):
    def __init__(self, *args, **kwargs):
        super(download, self).__init__(*args, **kwargs)

    def json(self):
        return {
            "datasetName": "LANDSAT_8",
            "apiKey": "USERS API KEY",
            "node": "EE",
            "entityIds": ["LC80130292014100LGN00"],
            "products": ["STANDARD"]
        }
