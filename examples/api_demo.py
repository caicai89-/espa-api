"""
# ESPA-API DEMO code

Since many of our services written in python also interact with the API, we have
this example as a quick run-through which should hopefully get anyone started
towards building their own simple python services capable of interacting
with ESPA.

## Official documentation:

* See the [ESPA API Source Code](https://github.com/USGS-EROS/espa-api/)
* Visit the [ESPA On-Demand Interface](https://espa.cr.usgs.gov)

### WARNING! _This example is only provided as is._
To build this page, simply run:

    pycco examples/api_demo.py


Alternatively, you can run this file directly, like so:

    python examples/api_demo.py

"""

# ## Dependencies
# We will use the [requests](http://docs.python-requests.org/en/master/)
# library, although similar operations are available through the
# [Standard Python Libraries](https://docs.python.org/2/library/internet.html)
import requests
import json
import getpass

# The current URL hosting the ESPA interfaces has reached a stable version 1.0
host = 'https://espa.cr.usgs.gov/api/v1/'

# ESPA uses the ERS credentials for identifying users
username = 'earth_explorer_username'
password = getpass.getpass()


# ## api_request: A Function
# First and foremost, define a simple function for interacting with the API
def api_request(endpoint, verb='get', json=None, uauth=None):
    """
    Here we can see how easy it is to handle calls to a REST API that uses JSON
    """
    auth_tup = uauth if uauth else (username, password)
    response = getattr(requests, verb)(host + endpoint, auth=auth_tup, json=json)
    return response.json()


# ## General Interactions
# Basic call to get the current user's information
print('GET /api/v1/user')
resp = api_request('user')
print(json.dumps(resp, indent=4))

# Call to demonstrate what is returned from available-products
print('GET /api/v1/available-products')
avail_list = {'inputs': ['LE07_L1TP_029030_20170221_20170319_01_T1',
                         'MOD09A1.A2017073.h10v04.006.2017082160945.hdf',
                         'bad_scene_id']}

resp = api_request('available-products', verb='post', json=avail_list)
print(json.dumps(resp, indent=4))

# Call to show projection parameters that are accepted
print('GET /api/v1/projections')
projs = api_request('projections')

print projs.keys()
print(json.dumps(projs['utm']['properties'], indent=4))

# ## Building An Order
# Step through one way to build and place an order into the system. Here, let's
# use two different Landsat sensors to build up an order
print('POST /api/v1/order')
l8_ls = ['LC08_L1TP_029030_20161109_20170219_01_T1',
         'LC08_L1TP_029030_20160821_20170222_01_T1',
         'LC08_L1TP_029030_20130712_20170309_01_T1']
l7_ls =['LE07_L1TP_029030_20170221_20170319_01_T1',
        'LE07_L1TP_029030_20161101_20161127_01_T1',
        'LE07_L1TP_029030_20130602_20160908_01_T1']

# Differing products across the sensors
l7_prods = ['toa', 'bt']
l8_prods = ['sr']

# Standard Albers CONUS
projection = {'aea': {'standard_parallel_1': 29.5,
                      'standard_parallel_2': 45.5,
                      'central_meridian': -96.0,
                      'latitude_of_origin': 23.0,
                      'false_easting': 0,
                      'false_northing': 0,
                      'datum': 'nad83'}}

# Let available-products place the acquisitions under their respective sensors
ls = l8_ls + l7_ls
order = api_request('available-products', verb='post', json=dict(inputs=ls))
print(json.dumps(order, indent=4))

# Replace the available products that was returned with what we want
for sensor in order.keys():
    if isinstance(order[sensor], dict) and order[sensor].get('inputs'):
        if set(l7_ls) & set(order[sensor]['inputs']):
            order[sensor]['products'] = l7_prods
        if set(l8_ls) & set(order[sensor]['inputs']):
            order[sensor]['products'] = l8_prods

# Add in the rest of the order information
order['projection'] = projection
order['format'] = 'gtiff'
order['resampling_method'] = 'cc'
order['note'] = 'API Demo Python!!'

# Notice how it has changed from the original call available-products
print(json.dumps(order, indent=4))

# Place the order
resp = api_request('order', verb='post', json=order)
print(json.dumps(resp, indent=4))
orderid = resp['orderid']

# ## Check the status of an order
# Check on an order and get the download url's for completed scenes
print('GET /api/v1/item-status/')
resp = api_request('item-status/{0}'.format(orderid))
print(json.dumps(resp, indent=4))

print(json.dumps(resp['orderid'][orderid]))

# Once the order is completed or partially completed, can get the download url's
for item in resp['orderid'][orderid]:
    print(item.get('product_dload_url'))
