#!/usr/bin/env python
import unittest
from mock import patch, MagicMock
import yaml
import copy
import itsdangerous

from api.interfaces.ordering.version1 import API as APIv1
from api.util import lowercase_all
from api.util.dbconnect import db_instance
import version0_testorders as testorders
from api.providers.validation.validictory import BaseValidationSchema
from api import ValidationException, InventoryException

import os
from api.domain.mocks.order import MockOrder
from api.domain.mocks.user import MockUser
from api.domain.order import Order
from api.domain.user import User
from api.providers.production.mocks.production_provider import MockProductionProvider
from api.providers.production.production_provider import ProductionProvider


api = APIv1()
production_provider = ProductionProvider()
mock_production_provider = MockProductionProvider()


class TestAPI(unittest.TestCase):
    def setUp(self):
        os.environ['espa_api_testing'] = 'True'
        # create a user
        self.mock_user = MockUser()
        self.mock_order = MockOrder()
        user_id = self.mock_user.add_testing_user()
        order_id = self.mock_order.generate_testing_order(user_id)
        self.order = Order.find(order_id)
        self.user = User.find(user_id)
        self.product_id = 'LT50150401987120XXX02'
        self.staff_product_id = 'LE70450302003206EDC01'

        staff_user_id = self.mock_user.add_testing_user()
        self.staff_user = User.find(staff_user_id)
        self.staff_user.update('is_staff', True)
        staff_order_id = self.mock_order.generate_testing_order(staff_user_id)
        staff_order = Order.find(staff_order_id)
        staff_scene = staff_order.scenes()[0]
        staff_scene.update('name', self.staff_product_id)
        user_scene = self.order.scenes()[0]
        user_scene.update('name', self.staff_product_id)

        with open('api/domain/restricted.yaml') as f:
            self.restricted = yaml.load(f.read())
            self.restricted['all']['role'].remove('restricted_prod')

    def tearDown(self):
        # clean up orders
        self.mock_order.tear_down_testing_orders()
        # clean up users
        self.mock_user.cleanup()
        os.environ['espa_api_testing'] = ''

    def test_api_versions_key_val(self):
        self.assertEqual(set(api.api_versions().keys()), set(['v0', 'v1']))

    def test_get_available_products_key_val(self):
        self.assertEqual(api.available_products(self.product_id, self.user.username).keys()[0], "tm5")

    def test_get_available_products_by_staff(self):
        # staff should see all available products
        self.user.update('is_staff', True)
        return_dict = api.available_products(self.staff_product_id, self.staff_user.username)
        for item in self.restricted['all']['role']:
            self.assertTrue(item in return_dict['etm7']['products'])

    def test_get_available_products_by_public(self):
        # public should not see products listed in api/domain.restricted.yaml
        self.user.update('is_staff', False)
        return_dict = api.available_products(self.staff_product_id, self.user.username)
        for item in self.restricted['all']['role']:
            self.assertFalse(item in return_dict['etm7']['products'])

    def test_fetch_user_orders_by_email_val(self):
        orders = api.fetch_user_orders(self.user.email)
        self.assertEqual(orders.keys()[0], "orders")

    def test_fetch_user_orders_by_username_val(self):
        orders = api.fetch_user_orders(self.user.username)
        self.assertEqual(orders.keys()[0], "orders")

    def test_fetch_order_by_orderid_val(self):
        order = api.fetch_order(self.order.orderid)
        self.assertEqual(order['orderid'], self.order.orderid)

    def test_fetch_order_status_valid(self):
        response = api.order_status(self.order.orderid)
        self.assertEqual(response.keys(), ['orderid', 'status'])

    def test_fetch_order_status_invalid(self):
        invalid_orderid = 'invalidorderid'
        response = api.order_status(invalid_orderid)
        self.assertEqual(response.keys(), ['msg'])

    def test_fetch_item_status_valid(self):
        response = api.item_status(self.order.orderid)
        self.assertEqual(response.keys(), ['orderid'])
        self.assertIsInstance(response['orderid'], dict)

    def test_fetch_item_status_invalid(self):
        invalid_orderid = 'invalidorderid'
        response = api.order_status(invalid_orderid)
        self.assertEqual(response.keys(), ['msg'])


class TestValidation(unittest.TestCase):
    def setUp(self):
        os.environ['espa_api_testing'] = 'True'

        self.mock_user = MockUser()
        self.staffuser = User.find(self.mock_user.add_testing_user())
        self.staffuser.update('is_staff', True)

        self.base_order = lowercase_all(testorders.build_base_order())
        self.base_schema = BaseValidationSchema.request_schema

    def test_validation_get_order_schema(self):
        """
        Make sure the ordering schema is retrievable as a dict
        """
        self.assertIsInstance(api.validation.fetch_order_schema(), dict)

    def test_validation_get_valid_formats(self):
        """
        Make sure the file format options are retrievable as a dict
        """
        self.assertIsInstance(api.validation.fetch_formats(), dict)

    def test_validation_get_valid_resampling(self):
        """
        Make sure the resampling options are retrievable as a dict
        """
        self.assertIsInstance(api.validation.fetch_resampling(), dict)

    def test_validation_get_valid_projections(self):
        """
        Make sure the projection options are retrievable as a dict
        """
        self.assertIsInstance(api.validation.fetch_projections(), dict)

    def test_validate_good_order(self):
        """
        Test a series of known good orders
        """
        for proj in testorders.good_test_projections:
            valid_order = copy.deepcopy(self.base_order)
            valid_order['projection'] = {proj: testorders.good_test_projections[proj]}

            try:
                good = api.validation(valid_order, self.staffuser.username)
            except ValidationException as e:
                self.fail('Raised ValidationException: {}'.format(e.message))

    def test_modis_resize(self):
        """
        Most common issue of orders resizing MODIS to 30m pixels, without setting the extents
        """
        modis_order = {'mod09a1': {'inputs': 'mod09a1.a2016305.h11v04.006.2016314200836',
                                   'products': ['l1']},
                       'resampling_method': 'cc',
                       'resize': {'pixel_size': 30,
                                  'pixel_size_units': 'meters'},
                       'format': 'gtiff'}

        exc = 'pixel count value is greater than maximum size of'

        try:
            api.validation(modis_order, self.staffuser.username)
        except Exception as e:
            assert(exc in str(e))
        else:
            self.fail('Failed MODIS pixel resize test')

    def test_validate_bad_orders(self):
        """
        Build a series of invalid orders to try and catch any potential errors in a
        submitted order

        Check to make sure the invalid order raises ValidationException, then check
        the exception message for the expected error message

        The abbreviated flag for the InvalidOrders class changes the number of invalid
        orders that will get tested.

        abbreviated=True - test each constraint type once
        abbreviated=False - test each constraint on each value location in the nested structure
        """
        exc_type = ValidationException
        invalid_order = copy.deepcopy(self.base_order)
        c = 0  # For initial debugging

        for proj in testorders.good_test_projections:
            invalid_order['projection'] = {proj: testorders.good_test_projections[proj]}

            invalid_list = testorders.InvalidOrders(invalid_order, self.base_schema, abbreviated=True)

            for order, test, exc in invalid_list:
                # issues getting assertRaisesRegExp to work correctly
                with self.assertRaises(exc_type):
                    try:
                        c += 1
                        api.validation(order, self.staffuser.username)
                    except exc_type as e:
                        if str(exc) in str(e):
                            raise
                        else:
                            self.fail('\n\nExpected in exception message:\n{}'
                                      '\n\nException message raised:\n{}'
                                      '\n\nUsing test {}'.format(str(exc), str(e), test))
                    else:
                        self.fail('\n{} Exception was not raised\n'
                                  '\nExpected exception message:\n{}\n'
                                  '\nUsing test: {}'.format(exc_type, str(exc), test))
        #print c  # For initial debugging

    def test_validate_allow_human_readable(self):
        """
        Assert that adding response-readable to the JSON request is accepted
        """
        valid_order = copy.deepcopy(self.base_order)
        valid_order['response-readable'] = True
        try:
            good = api.validation.validate(valid_order, self.staffuser.username)
        except ValidationException as e:
            self.fail('Raised ValidationException: {}'.format(e.message))

    def test_validate_sr_restricted_human_readable(self):
        """
        Assert that a human readable response is returned for unavailable or date restricted products
        """
        exc_type = ValidationException
        invalid_list = {'olitirs8': {'inputs': ['lc80310272016056lgn00'],
                                     'products': ['sr'],
                                     'err_msg': 'Requested {} products are restricted by date. '
                                                'Remove <obj>.{} scenes: {}'},
                        'oli8': {'inputs': ['lo80141122015030lgn00'],
                                 'products': ['sr'],
                                 'err_msg': 'Requested {} products are not available. '
                                            'Remove <obj>.{} scenes: {}'}}

        for stype in invalid_list:
            invalid_order = copy.deepcopy(self.base_order)
            invalid_order[stype]['inputs'] = invalid_list[stype]['inputs']
            invalid_order[stype]['products'] = invalid_list[stype]['products']
            invalid_order['response-readable'] = True
            uppercase_products = map(str.upper, invalid_order[stype]['inputs'])
            for p in invalid_order[stype]['products']:
                err_message = invalid_list[stype]['err_msg'].format(p, stype, uppercase_products)
                with self.assertRaises(exc_type):
                    try:
                        api.validation.validate(invalid_order, self.staffuser.username)
                    except exc_type as e:
                        if str(err_message) in str(e):
                            raise
                        else:
                            self.fail('\n\nExpected in exception message:\n{}'
                                      '\n\nException message raised:\n{}'
                                      .format(str(err_message), str(e)))
                    else:
                        self.fail('\n{} Exception was not raised\n'
                                  '\nExpected exception message:\n{}\n'
                                  .format(exc_type, str(err_message)))

    @patch('api.providers.validation.validictory.api_cfg')
    def test_validate_order_source(self, mock_config):
        d = {'key': 'secret-key'}
        mock_config.return_value = MagicMock()
        mock_config.return_value.get = d.get
        valid_order = copy.deepcopy(self.base_order)
        secret_key = d['key']
        signer = itsdangerous.URLSafeTimedSerializer(secret_key)
        order_source = 'external'
        valid_order['order_source'] = signer.dumps(order_source).encode('hex')
        new_order = api.validation.validate(valid_order, self.staffuser.username)
        self.assertEqual(new_order.get('order_source'), order_source)

    @patch('api.providers.validation.validictory.api_cfg')
    def test_validate_order_source_fall_back(self, mock_config):
        d = {'key': 'secret-key'}
        mock_config.return_value = MagicMock()
        mock_config.return_value.get = d.get
        valid_order = copy.deepcopy(self.base_order)
        secret_key = 'this-should-be-a-secret'  # User trying to fake/guess this
        signer = itsdangerous.URLSafeTimedSerializer(secret_key)
        order_source = 'external'
        fall_back_source = 'espa'
        valid_order['order_source'] = signer.dumps(order_source).encode('hex')
        new_order = api.validation.validate(valid_order, self.staffuser.username)
        self.assertEqual(new_order.get('order_source'), fall_back_source)

    @patch('api.providers.validation.validictory.api_cfg')
    def test_validate_order_source_compromised(self, mock_config):
        d = {'key': 'secret-key'}
        mock_config.return_value = MagicMock()
        mock_config.return_value.get = d.get
        valid_order = copy.deepcopy(self.base_order)
        secret_key = d['key']  # User has guessed our secret key
        signer = itsdangerous.URLSafeTimedSerializer(secret_key)
        order_source = '1; DROP TABLE DB_NAME()'  # Some nonsense SQLi attempt
        fall_back_source = 'espa'
        valid_order['order_source'] = signer.dumps(order_source).encode('hex')
        new_order = api.validation.validate(valid_order, self.staffuser.username)
        self.assertEqual(new_order.get('order_source'), fall_back_source)


class TestInventory(unittest.TestCase):
    def setUp(self):
        os.environ['espa_api_testing'] = 'True'
        self.lta_prod_good = u'LT50300372011275PAC01'
        self.lta_prod_bad = u'LE70290302001200EDC01'
        self.lpdaac_prod_good = u'MOD09A1.A2016305.h11v04.006.2016314200836'
        self.lpdaac_prod_bad = u'MOD09A1.A2016305.h11v04.006.9999999999999'

        self.lta_order_good = {'olitirs8': {'inputs': [self.lta_prod_good]}}
        self.lta_order_bad = {'olitirs8': {'inputs': [self.lta_prod_bad]}}

        self.lpdaac_order_good = {'mod09a1': {'inputs': [self.lpdaac_prod_good]}}
        self.lpdaac_order_bad = {'mod09a1': {'inputs': [self.lpdaac_prod_bad]}}



    def test_lta_good(self):
        """
        Check LTA support from the inventory provider
        """
        self.assertIsNone(api.inventory.check(self.lta_order_good))

    def test_lta_bad(self):
        """
        Check LTA support from the inventory provider
        """
        with self.assertRaises(InventoryException):
            api.inventory.check(self.lta_order_bad)

    def test_lpdaac_good(self):
        """
        Check LPDAAC support from the inventory provider
        """
        self.assertIsNone(api.inventory.check(self.lpdaac_order_good))

    def test_lpdaac_bad(self):
        """
        Check LPDAAC support from the inventory provider
        """
        with self.assertRaises(InventoryException):
            api.inventory.check(self.lpdaac_order_bad)

if __name__ == '__main__':
    unittest.main(verbosity=2)
