# API DEMO code from 24 August 2016 talk at EROS
#
# Official documentation:
# ESPA - http://espa.cr.usgs.gov/
# ESPA API - https://github.com/USGS-EROS/espa-api/
# ESPA ODI - http://landsat.usgs.gov/documents/espa_odi_userguide.pdf
# Product Information - http://landsat.usgs.gov/CDR_ECV.php
#
# Provided as is

# Standard Python Libraries
import urllib
import urllib2
import json
import getpass
import base64

# Easier to read outputs
from pprint import pprint

# Setup some basic parameters
host = 'https://espa.cr.usgs.gov'
username = 'earth_explorer_username'
password = getpass.getpass()


# Create a simple method for interacting with the API
def api_request(endpoint, data=None):
    """
    Simple method to handle calls to a REST API that uses JSON

    args:
        endpoint - API endpoint URL
        data - Python dictionary to send as JSON to the API

    returns:
        Python dictionary representation of the API response
    """
    if data:
        data = json.dumps(data)

    request = urllib2.Request(host + endpoint, data=data)

    base64string = (base64
                    .encodestring('%s:%s' % (username, password))
                    .replace('\n', ''))
    request.add_header("Authorization", "Basic %s" % base64string)

    try:
        result = urllib2.urlopen(request)
    except urllib2.HTTPError as e:
        result = e

    return json.loads(result.read())


# #######################################
# Basic call to get the current user's information
# #######################################
print('GET /api/v1/user')
resp = api_request('/api/v1/user')
pprint(resp)

# #######################################
# Call to demonstrate what is returned from available-products
# #######################################
print('POST /api/v1/available-products')
avail_list = {'inputs': ['LE70290302003123EDC00',
                         'MOD09A1.A2000073.h12v11.005.2008238080250.hdf',
                         'bad_scene_id']}

resp = api_request('/api/v1/available-products', avail_list)

pprint(resp)

# #######################################
# Call to show projection parameters that are accepted
# #######################################
print('GET /api/v1/projections')
projs = api_request('/api/v1/projections')

print projs.keys()
pprint(projs['utm']['properties'])

# #######################################
# Step through one way to build and place an order into the system
# #######################################
print('POST /api/v1/order')
ls = ['LC80250362014152LGN00', 'LC80260352014143LGN00', 'LC80260362014143LGN00',
      'LE70260352014135EDC00', 'LE70260362014151EDC00', 'LE70250362014144EDC00',
      'LT50260352007140PAC01', 'LT50260362007140PAC01', 'LT50250362007149PAC01']

# Differing products across the sensors
l5_prods = ['sr', 'toa', 'cloud']
l7_prods = ['toa', 'bt']
l8_prods = ['toa']

# Standard Albers CONUS
projection = {'aea': {'standard_parallel_1': 29.5,
                      'standard_parallel_2': 45.5,
                      'central_meridian': -96.0,
                      'latitude_of_origin': 23.0,
                      'false_easting': 0,
                      'false_northing': 0,
                      'datum': 'nad83'}}

# Let available-products place the acquisitions under their respective sensors
order = api_request('/api/v1/available-products', {'inputs': ls})
pprint(order)

# Replace the available products that was returned with what we want
order['etm7']['products'] = l7_prods
order['tm5']['products'] = l5_prods
order['olitirs8']['products'] = l8_prods

# Add in the rest of the order information
order['projection'] = projection
order['format'] = 'gtiff'
order['resampling_method'] = 'cc'
order['note'] = 'API Demo Live!!'

# Notice how it has changed from the original call available-products
pprint(order)

# Place the order
resp = api_request('/api/v1/order', data=order)
pprint(resp)
orderid = resp['orderid']

# #######################################
# Check on an order and get the download url's for completed scenes
# #######################################
print('GET /api/v1/item-status/')
resp = api_request('/api/v1/item-status/{0}'.format(orderid)
resp

pprint(resp['orderid'][orderid])

# set orderid to a completed or partially completed order to get the download url's
for item in resp['orderid'][orderid]:
    pprint(item.get('product_dload_url'))
