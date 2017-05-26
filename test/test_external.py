import os
import unittest
from mock import patch, MagicMock

from test.version0_testorders import build_base_order
from api.external.nlaps import products_are_nlaps
from api.external import onlinecache
from api.external.mocks import onlinecache as mockonlinecache
from api.external import lta
from api.external.mocks import lta as mocklta
from api.external.hadoop import HadoopHandler
from api.external.mocks import inventory as mockinventory

from api.external import lpdaac
from api.external import inventory
from api import ProductNotImplemented

class TestLPDAAC(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass



class TestLTA(unittest.TestCase):
    def setUp(self):
        os.environ['espa_api_testing'] = 'True'
        self.contact_id = 0
        self.lta_order_number = 0
        self.lta_unit_number = 0
        base_order = build_base_order()
        self.scene_ids = [base_order[b].get('inputs', [None]).pop() for b in base_order if type(base_order[b]) == dict]
        self.scene_ids = [s for s in self.scene_ids if s and (s.startswith('L'))]  # Landsat only

    def tearDown(self):
        os.environ['espa_api_testing'] = ''

    @patch('api.external.lta.requests.post', mocklta.get_verify_scenes_response)
    def test_verify_scenes(self):
        resp = lta.verify_scenes(self.scene_ids)
        for item in self.scene_ids:
            self.assertTrue(item in resp.keys())
            self.assertTrue(resp[item])

    @patch('api.external.lta.requests.post')
    def test_verify_scenes_fail(self, mock_requests):
        mock_requests.return_value = MagicMock(ok=False, reason='Testing Failure')
        with self.assertRaises(Exception):
            resp = lta.verify_scenes(self.scene_ids)

    @patch('api.external.lta.requests.post', mocklta.get_order_scenes_response_main)
    def test_order_scenes(self):
        resp = lta.order_scenes(self.scene_ids, self.contact_id)
        self.assertIn('ordered', resp)
        self.assertEqual(len(self.scene_ids), len(resp['ordered']))

    @patch('api.external.lta.requests.post')
    def test_order_scenes_fail(self, mock_requests):
        mock_requests.return_value = MagicMock(ok=False, reason='Testing Failure')
        with self.assertRaises(Exception):
            resp = lta.order_scenes(self.scene_ids, self.contact_id)

    @patch('api.external.lta.requests.post', mocklta.get_order_scenes_response_main)
    def test_get_download_urls(self):
        resp = lta.get_download_urls(self.scene_ids, self.contact_id)
        for item in self.scene_ids:
            self.assertIn(item, resp)
            self.assertEqual('available', resp[item]['status'])

    @patch('api.external.lta.requests.post')
    def test_get_download_urls_fail(self, mock_requests):
        mock_requests.return_value = MagicMock(ok=False, reason='Testing Failure')
        with self.assertRaises(Exception):
            resp = lta.get_download_urls(self.scene_ids, self.contact_id)

    #@patch('api.external.lta.OrderUpdateServiceClient.update_order', mocklta.return_update_order_resp)
    @patch('api.external.lta.SoapClient', mocklta.MockSudsClient)
    def test_get_available_orders(self):
        resp = lta.get_available_orders()
        self.assertEqual(len(resp[('100', '', '')]), 3)

    @patch('api.external.lta.SoapClient', mocklta.MockSudsClient)
    def test_get_order_status(self):
        resp = lta.get_order_status(self.lta_order_number)
        self.assertIn('order_status', resp)
        self.assertEqual(resp['order_num'], str(self.lta_order_number))

    @patch('api.external.lta.SoapClient', mocklta.MockSudsClient)
    def test_update_order_complete(self):
        resp = lta.update_order_status(self.lta_order_number, self.lta_unit_number, 'C')
        self.assertTrue(resp.success)

    @patch('api.external.lta.SoapClient', mocklta.MockSudsClient)
    def test_update_order_incomplete(self):
        resp = lta.update_order_status('failure', self.lta_unit_number, 'C')
        self.assertFalse(resp.success)


class TestInventory(unittest.TestCase):
    """
    Provide testing for the EarthExplorer JSON API (Machine-2-Machine)
    """
    def setUp(self):
        self.token = '2fd976601eef1ebd632b545a8fef11a3'
        self.collection_ids = ['LC08_L1TP_156063_20170207_20170216_01_T1',
                               'LE07_L1TP_028028_20130510_20160908_01_T1',
                               'LT05_L1TP_032028_20120425_20160830_01_T1']
        self.contact_id = 0

    def tearDown(self):
        pass

    @patch('api.external.inventory.requests.get', mockinventory.RequestsSpoof)
    @patch('api.external.inventory.requests.post', mockinventory.RequestsSpoof)
    def test_api_login(self):
        token = inventory.get_session()
        self.assertIsInstance(token, basestring)
        self.assertTrue(inventory.logout(token))

    @patch('api.external.inventory.requests.post', mockinventory.RequestsSpoof)
    def test_api_available(self):
        self.assertTrue(inventory.available())

    @patch('api.external.inventory.requests.get', mockinventory.RequestsSpoof)
    def test_api_id_lookup(self):
        entity_ids = inventory.convert(self.token, self.collection_ids)
        self.assertEqual(set(self.collection_ids), set(entity_ids))

    @patch('api.external.inventory.requests.get', mockinventory.RequestsSpoof)
    def test_api_validation(self):
        expected = {k: True for k in self.collection_ids}
        results = inventory.verify_scenes(self.token, self.collection_ids)
        self.assertItemsEqual(expected, results)

    @patch('api.external.inventory.requests.get', mockinventory.RequestsSpoof)
    def test_api_get_download_urls(self):
        results = inventory.get_download_urls(self.token, self.collection_ids)
        self.assertIsInstance(results, dict)
        ehost, ihost = 'invalid.com', '127.0.0.1'
        results = {k:v.replace(ehost, ihost) for k,v in results.items()}
        self.assertEqual(set(self.collection_ids), set(results))
        ip_address_host_regex = 'http://\d+\.\d+\.\d+\.\d+/.*\.tar\.gz'
        for pid in self.collection_ids:
            self.assertRegexpMatches(results.get(pid), ip_address_host_regex)

    @patch('api.external.inventory.requests.get', mockinventory.RequestsSpoof)
    def test_set_user_context(self):
        success = inventory.set_user_context(self.token, self.contact_id)
        self.assertTrue(success)

    @patch('api.external.inventory.requests.get', mockinventory.RequestsSpoof)
    def test_clear_user_context(self):
        success = inventory.clear_user_context(self.token)
        self.assertTrue(success)

    def test_id_sensor_limits(self):
        with self.assertRaisesRegexp(ProductNotImplemented, 'is not a supported sensor product'):
            _ = inventory.convert(self.token, ['bad_id_yo'])

    @patch('api.external.inventory.requests.get', mockinventory.RequestsSpoof)
    def test_bad_id_lookup(self):
        with self.assertRaisesRegexp(inventory.LTAError, 'ID Lookup failed'):
            _ = inventory.convert(self.token, ['LC08_L1TP_000000_19000101_00000000_00_T1'])

    @patch('api.external.inventory.requests.post', mockinventory.BadRequestSpoofError)
    def test_error_code_halt(self):
        expected = 'UNKNOWN: A fake server error occurred'
        with self.assertRaisesRegexp(inventory.LTAError, expected):
            _ = inventory.get_session()

    @patch('api.external.inventory.requests.get', mockinventory.BadRequestSpoofNegative)
    def test_false_data_response(self):
        expected = 'Set user context ESPA failed for user {}'.format(self.contact_id)
        with self.assertRaisesRegexp(inventory.LTAError, expected):
            _ = inventory.set_user_context(self.token, self.contact_id)


class TestNLAPS(unittest.TestCase):
    """
    Provide testing for sorting out NLAPS products
    """
    def setUp(self):
        self.nlaps = ['LT40150231982306AAA02',
                      'LT40360241982341AAA05',
                      'LT51392101985039AAA03',
                      'LT51790261985079AAA04',
                      'LT50460331985171AAA04']

        self.non_nlaps = ['LT50290302011300PAC01',
                          'LC80300302016065LGN00',
                          'LE70300302016057EDC00',
                          'LE70290302003126EDC00']

    def test_nlaps_prods(self):
        all = [_ for _ in self.nlaps]
        all.extend(self.non_nlaps)

        nlaps_prods = products_are_nlaps(all)

        for prod in nlaps_prods:
            self.assertTrue(prod in self.nlaps)
            self.assertTrue(prod not in self.non_nlaps)


class TestOnlineCache(unittest.TestCase):
    """
    Tests for dealing with the distribution cache
    """
    def setUp(self):
        self.cache = onlinecache.OnlineCache()

    def test_cache_listorders(self):
        results = self.cache.list()

        self.assertTrue(results)

    def test_cache_capcity(self):
        results = self.cache.capacity()

        self.assertTrue('capacity' in results)

    @patch('api.external.onlinecache.OnlineCache.delete', mockonlinecache.delete)
    def test_cache_deleteorder(self):
        results = self.cache.delete('bilbo')
        self.assertTrue(results)


class TestHadoopHandler(unittest.TestCase):
    """
    Tests for the hadoop interaction class
    """
    def setUp(self):
        self.hadoop = HadoopHandler()

    def test_list_jobs(self):
        resp = self.hadoop.list_jobs()
        self.assertTrue('stdout' in resp.keys())

    def test_job_names_ids(self):
        resp = self.hadoop.job_names_ids()
        self.assertTrue(isinstance(resp, dict))

    def test_slave_ips(self):
        resp = self.hadoop.slave_ips()
        self.assertTrue(isinstance(resp, list))
        self.assertTrue(len(resp) > 0)

    def test_master_ip(self):
        resp = self.hadoop.master_ip()
        self.assertTrue(isinstance(resp, str))
        self.assertTrue(len(resp.split('.')) == 4)
