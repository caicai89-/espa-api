#!/usr/bin/env python
import datetime
import unittest

import os
from api.domain.mocks.order import MockOrder
from api.domain.mocks.user import MockUser
from api.domain.order import Order, OptionsConversion
from api.domain.scene import Scene
from api.domain.user import User
from api.external.mocks import lta, inventory, lpdaac, onlinecache, nlaps, hadoop
from api.interfaces.production.version1 import API
from api.notification import emails
from api.providers.production.mocks.production_provider import MockProductionProvider
from api.providers.production.production_provider import ProductionProvider
from api.system.mocks import errors
from mock import patch

api = API()
production_provider = ProductionProvider()
mock_production_provider = MockProductionProvider()


class TestProductionAPI(unittest.TestCase):
    def setUp(self):
        os.environ['espa_api_testing'] = 'True'
        # create a user
        self.mock_user = MockUser()
        self.mock_order = MockOrder()
        self.user_id = self.mock_user.add_testing_user()

    def tearDown(self):
        # clean up orders
        self.mock_order.tear_down_testing_orders()
        # clean up users
        self.mock_user.cleanup()
        os.environ['espa_api_testing'] = ''

    @patch('api.external.lpdaac.get_download_urls', lpdaac.get_download_urls)
    @patch('api.providers.production.production_provider.ProductionProvider.set_product_retry',
           mock_production_provider.set_product_retry)
    def test_fetch_production_products_modis(self):
        order_id = self.mock_order.generate_testing_order(self.user_id)
        # need scenes with statuses of 'processing'
        self.mock_order.update_scenes(order_id, 'modis', 'status', ['processing', 'oncache'])
        user = User.find(self.user_id)
        params = {'for_user': user.username, 'product_types': ['modis']}
        response = api.fetch_production_products(params)
        self.assertTrue('bilbo' in response[0]['orderid'])

    @patch('api.external.inventory.get_cached_session', inventory.get_cached_session)
    @patch('api.external.inventory.get_cached_download_urls', inventory.get_cached_download_urls)
    @patch('api.providers.production.production_provider.ProductionProvider.set_product_retry',
           mock_production_provider.set_product_retry)
    def test_fetch_production_products_landsat(self):
        order_id = self.mock_order.generate_testing_order(self.user_id)
        # need scenes with statuses of 'processing'
        self.mock_order.update_scenes(order_id, 'landsat', 'status', ['processing', 'oncache'])
        user = User.find(self.user_id)
        params = {'for_user': user.username, 'product_types': ['landsat']}
        response = api.fetch_production_products(params)
        self.assertTrue('bilbo' in response[0]['orderid'])

    def test_fetch_production_products_plot(self):
        order_id = self.mock_order.generate_testing_order(self.user_id)
        self.mock_order.update_scenes(order_id, ('landsat', 'modis'), 'status', ['complete'])
        order = Order.find(order_id)
        plot_scene = order.scenes({'name': 'plot'})[0]
        plot_scene.name = 'plot'
        plot_scene.sensor_type = 'plot'
        plot_scene.status = 'submitted'
        plot_scene.save()
        response = production_provider.handle_submitted_plot_products()
        pscene = order.scenes({'status': 'oncache', 'sensor_type': 'plot'})
        self.assertTrue(response is True)
        self.assertEqual(len(pscene), 1)

    def test_production_set_product_retry(self):
        order_id = self.mock_order.generate_testing_order(self.user_id)
        order = Order.find(order_id)
        scene = order.scenes()[3]
        scene.update('retry_count', 4)
        processing_loc = "get_products_to_process"
        error = 'not available after EE call '
        note = 'note this'
        retry_after = datetime.datetime.now() + datetime.timedelta(hours=1)
        retry_limit = 9
        response = production_provider.set_product_retry(scene.name, order.orderid, processing_loc,
                                                         error, note, retry_after, retry_limit)

        new = Scene.get('ordering_scene.status', scene.name, order.orderid)
        self.assertTrue('retry' == new)

    @patch('api.external.lta.update_order_status', mock_production_provider.respond_true)
    def test_production_set_product_error_unavailable(self):
        """
        Move a scene status from error to unavailable based on the error
        message
        """
        order = Order.find(self.mock_order.generate_testing_order(self.user_id))
        scene = order.scenes({'name !=': 'plot'})[0]
        production_provider.set_product_error(scene.name, order.orderid,
                                              'get_products_to_process',
                                              'include_dswe is an unavailable product option for OLITIRS')
        self.assertTrue('unavailable' == Scene.get('ordering_scene.status', scene.name, order.orderid))

    def test_production_set_product_error_submitted(self):
        """
        Move a scene status from error to submitted based on the error
        message
        """
        order = Order.find(self.mock_order.generate_testing_order(self.user_id))
        scene = order.scenes({'name !=': 'plot'})[0]
        production_provider.set_product_error(scene.name, order.orderid,
                                              'get_products_to_process',
                                              'BLOCK, COMING FROM LST AS WELL: No such file or directory')
        self.assertTrue('submitted' == Scene.get('ordering_scene.status', scene.name, order.orderid))

    def test_production_set_product_error_retry(self):
        """
        Move a scene status from error to retry based on the error
        message
        """
        order = Order.find(self.mock_order.generate_testing_order(self.user_id))
        scene = order.scenes()[2]
        production_provider.set_product_error(scene.name, order.orderid,
                                              'somewhere',
                                              'Verify the missing auxillary data products')
        self.assertTrue('retry' == Scene.get('ordering_scene.status', scene.name, order.orderid))

    @patch('api.external.lta.update_order_status', lta.update_order_status)
    @patch('api.providers.production.production_provider.ProductionProvider.set_product_retry', mock_production_provider.set_product_retry)
    def test_update_product_details_update_status(self):
        """
        Set a scene status to Queued
        """
        order = Order.find(self.mock_order.generate_testing_order(self.user_id))
        scene = order.scenes()[0]
        api.update_product_details('update_status',
                                   {'name': scene.name,
                                    'orderid': order.orderid,
                                    'processing_loc': 'L8SRLEXAMPLE',
                                    'status': 'Queued'})
        self.assertTrue(Scene.get('ordering_scene.status', scene.name, order.orderid) == 'Queued')

    @patch('api.external.lta.update_order_status', lta.update_order_status)
    @patch('api.providers.production.production_provider.ProductionProvider.set_product_retry', mock_production_provider.set_product_retry)
    @patch('api.external.onlinecache.capacity', onlinecache.capacity)
    def test_update_product_details_set_product_error(self):
        """
        Set a scene status to error
        :return:
        """
        order = Order.find(self.mock_order.generate_testing_order(self.user_id))
        scene = order.scenes()[0]
        production_provider.update_product('set_product_error',
                                           name=scene.name, orderid=order.orderid,
                                           processing_loc="L8SRLEXAMPLE",
                                           error='problems yo')
        self.assertTrue(Scene.find(scene.id).status == 'error')

    @patch('api.external.lta.update_order_status', lta.update_order_status)
    @patch('api.providers.production.production_provider.ProductionProvider.set_product_retry', mock_production_provider.set_product_retry)
    def test_update_product_details_set_product_unavailable(self):
        order = Order.find(self.mock_order.generate_testing_order(self.user_id))
        scene = order.scenes()[0]
        production_provider.update_product('set_product_unavailable',
                                           name=scene.name, orderid=order.orderid,
                                           processing_loc="L8SRLEXAMPLE",
                                           error='include_dswe is an unavailable product option for OLITIRS')
        self.assertTrue('unavailable' == Scene.get('ordering_scene.status', scene.name, order.orderid))

    @patch('api.external.lta.update_order_status', lta.update_order_status)
    @patch('api.providers.production.production_provider.ProductionProvider.set_product_retry', mock_production_provider.set_product_retry)
    @patch('os.path.getsize', lambda y: 999)
    def test_update_product_details_mark_product_complete(self):
        order = Order.find(self.mock_order.generate_testing_order(self.user_id))
        scene = order.scenes()[0]
        production_provider.update_product('mark_product_complete',
                                           name=scene.name,
                                           orderid=order.orderid,
                                           processing_loc='L8SRLEXAMPLE',
                                           completed_file_location='/some/loc',
                                           cksum_file_location='some checksum',
                                           log_file_contents='some log')

        self.assertTrue('complete' == Scene.get('ordering_scene.status', scene.name, order.orderid))

    def test_production_set_product_error_unavailable_night(self):
        """
        Move a scene status from error to unavailable based on the solar zenith
        error message
        """
        order = Order.find(self.mock_order.generate_testing_order(self.user_id))
        scene = order.scenes({'name !=': 'plot'})[0]
        production_provider.set_product_error(name=scene.name,
                                              orderid=order.orderid,
                                              processing_loc='L8SRLEXAMPLE',
                                              error='solar zenith angle out of range')
        scene = Scene.by_name_orderid(name=scene.name, order_id=order.id)
        self.assertTrue('unavailable' == scene.status)
        self.assertTrue('cannot be processed due to the extreme solar zenith angle' in scene.note)

    def test_production_set_product_error_unavailable_almost_night(self):
        """
        Move a scene status from error to unavailable based on the solar zenith
        error message
        """
        order = Order.find(self.mock_order.generate_testing_order(self.user_id))
        scene = order.scenes({'name !=': 'plot'})[0]
        production_provider.set_product_error(name=scene.name,
                                              orderid=order.orderid,
                                              processing_loc='L8SRLEXAMPLE',
                                              error='Solar zenith angle is too large')
        scene = Scene.by_name_orderid(name=scene.name, order_id=order.id)
        self.assertTrue('unavailable' == scene.status)
        self.assertTrue('cannot be processed to surface reflectance' in scene.note)

    @patch('api.external.lta.update_order_status', lta.update_order_status_fail)
    @patch('api.providers.production.production_provider.ProductionProvider.set_product_retry', mock_production_provider.set_product_retry)
    @patch('os.path.getsize', lambda y: 999)
    def test_update_product_details_fail_lta_mark_product_complete(self):
        order = Order.find(self.mock_order.generate_testing_order(self.user_id))
        scene = order.scenes()[1]
        order.update('order_source', 'ee')
        production_provider.update_product('mark_product_complete',
                                           name=scene.name,
                                           orderid=order.orderid,
                                           processing_loc='L8SRLEXAMPLE',
                                           completed_file_location='/some/loc',
                                           cksum_file_location='some checksum',
                                           log_file_contents='some log')

        s = Scene.where({'name': scene.name, 'order_id': scene.order_id})[0]
        self.assertTrue('C' == s.failed_lta_status_update)

    @patch('api.providers.production.production_provider.ProductionProvider.send_initial_emails',
           mock_production_provider.respond_true)
    @patch('api.providers.production.production_provider.ProductionProvider.handle_retry_products',
           mock_production_provider.respond_true)
    @patch('api.providers.production.production_provider.ProductionProvider.load_ee_orders',
           mock_production_provider.respond_true)
    @patch('api.providers.production.production_provider.ProductionProvider.finalize_orders',
           mock_production_provider.respond_true)
    @patch('api.providers.production.production_provider.ProductionProvider.purge_orders',
           mock_production_provider.respond_true)
    def test_handle_orders_success(self):
        self.assertTrue(api.handle_orders())

    @patch('api.external.onlinecache.delete', mock_production_provider.respond_true)
    @patch('api.notification.emails.send_purge_report', mock_production_provider.respond_true)
    @patch('api.external.onlinecache.capacity', onlinecache.capacity)
    def test_production_purge_orders(self):
        new_completion_date = datetime.datetime.now() - datetime.timedelta(days=12)
        order = Order.find(self.mock_order.generate_testing_order(self.user_id))
        order.update('status', 'complete')
        order.update('completion_date', new_completion_date)
        self.assertTrue(production_provider.purge_orders())

    # need to figure a test for emails.send_email
    @patch('api.notification.emails.Emails.send_email', mock_production_provider.respond_true)
    def test_production_send_initial_emails(self):
        order = Order.find(self.mock_order.generate_testing_order(self.user_id))
        order.update('status', 'ordered')
        self.assertTrue(emails.Emails().send_all_initial())

    def test_production_handle_retry_products(self):
        prev = datetime.datetime.now() - datetime.timedelta(hours=1)
        order_id = self.mock_order.generate_testing_order(self.user_id)
        self.mock_order.update_scenes(order_id, 'landsat', 'status', ['retry'])
        self.mock_order.update_scenes(order_id, 'landsat', 'retry_after', [prev])
        production_provider.handle_retry_products()
        for s in Scene.where({'order_id': order_id, 'sensor_type': 'landsat'}):
            self.assertTrue(s.status == 'submitted')

    #@patch('api.external.lta.get_available_orders', lta.get_available_orders)
    #@patch('api.external.lta.update_order_status', lta.update_order_status)
    #@patch('api.external.lta.get_user_name', lta.get_user_name)
    #def test_production_load_ee_orders(self):
    #    #production_provider.load_ee_orders()
    #    pass

    @patch('api.external.lta.get_available_orders', lta.get_available_orders_partial)
    @patch('api.external.lta.update_order_status', lta.update_order_status)
    @patch('api.external.lta.get_user_name', lta.get_user_name)
    def test_production_load_ee_orders_partial(self):
        order = Order.find(self.mock_order.generate_ee_testing_order(self.user_id, partial=True))
        self.assertTrue(order.product_opts == {'format': 'gtiff',
                                               'etm7': {'inputs': ['LE70900652008327EDC00'],
                                                        'products': ['sr']}})
        production_provider.load_ee_orders()
        reorder = Order.find(order.id)
        self.assertTrue(reorder.product_opts == {'format': 'gtiff',
                                               'etm7': {'inputs': ['LE70900652008327EDC00'],
                                                        'products': ['sr']},
                                               'tm5': {'inputs': ['LT50900652008327EDC00'],
                                                        'products': ['sr']}})

    @patch('api.external.lta.update_order_status', lta.update_order_status)
    def test_production_handle_failed_ee_updates(self):
        order = Order.find(self.mock_order.generate_testing_order(self.user_id))
        for scene in order.scenes():
            scene.update('failed_lta_status_update', 'C')

        production_provider.handle_failed_ee_updates()

        scenes = Scene.where({'failed_lta_status_update IS NOT': None})
        self.assertTrue(len(scenes) == 0)

    @patch('api.external.lta.update_order_status', lta.update_order_status)
    def test_production_set_products_unavailable(self):
        order = Order.find(self.mock_order.generate_testing_order(self.user_id))
        self.assertTrue(production_provider.set_products_unavailable(order.scenes(), "you want a reason?"))

    def test_production_handle_submitted_plot_products(self):
        order = Order.find(self.mock_order.generate_testing_order(self.user_id))
        order.status = 'ordered'
        order.order_type = 'lpcs'
        order.save()
        plot_id = None
        for idx, scene in enumerate(order.scenes()):
            # at the moment, mock_order.generate_testing_order
            # creates 21 products for the order. divvy those
            # up between 'complete' and 'unavailable', setting
            # one aside as the 'plot' product
            if idx % 2 == 0:
                if idx == 0:
                    # need to define a plot product
                    scene.update('status', 'submitted')
                    scene.update('sensor_type', 'plot')
                    plot_id = scene.id
                else:
                    scene.update('status', 'complete')
            else:
                scene.update('status', 'unavailable')

        self.assertTrue(production_provider.handle_submitted_plot_products())
        self.assertEqual(Scene.find(plot_id).status, "oncache")

    @patch('os.path.exists', lambda y: True)
    @patch('os.path.getsize', lambda y: 999)
    def test_production_calc_scene_download_sizes(self):
        order = Order.find(self.mock_order.generate_testing_order(self.user_id))
        scenes = order.scenes()
        Scene.bulk_update([s.id for s in scenes], {'status': 'complete', 'download_size': 0})
        self.assertTrue(production_provider.calc_scene_download_sizes())
        upscenes = Scene.where({'status': 'complete', 'download_size': 999})
        self.assertEqual(len(upscenes), len(scenes))

    @patch('api.providers.production.production_provider.ProductionProvider.update_order_if_complete',
           mock_production_provider.respond_true)
    def test_production_finalize_orders(self):
        order = Order.find(self.mock_order.generate_testing_order(self.user_id))
        order.update('status', 'ordered')
        self.assertTrue(production_provider.finalize_orders())

    @patch('api.providers.production.production_provider.ProductionProvider.send_completion_email',
           mock_production_provider.respond_true)
    def test_production_update_order_if_complete(self):
        order = Order.find(self.mock_order.generate_testing_order(self.user_id))
        Scene.bulk_update([s.id for s in order.scenes()], {'status': 'retry'})
        order.order_source = 'espa'
        order.completion_email_sent = None
        order.save()
        self.assertTrue(production_provider.update_order_if_complete(order))

    def test_production_queue_products_success(self):
        names_tuple = self.mock_order.names_tuple(3, self.user_id)
        processing_loc = "get_products_to_process"
        job_name = 'jobname49'
        params = (names_tuple, processing_loc, job_name)
        response = api.queue_products(*params)
        self.assertTrue(response)

    def test_production_get_key(self):
        key = 'system_message_title'
        response = api.get_production_key(key)
        val = response[key]
        self.assertIsInstance(val, str)

    def test_get_production_key_invalid(self):
        bad_key = 'foobar'
        response = api.get_production_key(bad_key)
        self.assertEqual(response.keys(), ['msg'])

    @patch('api.external.hadoop.HadoopHandler.job_names_ids',
           hadoop.jobs_names_ids)
    def test_catch_orphaned_scenes(self):
        order_id = self.mock_order.generate_testing_order(self.user_id)
        # need scenes with statuses of 'queued'
        self.mock_order.update_scenes(order_id, ('landsat', 'modis', 'plot'), 'status', ['queued'])
        response = production_provider.catch_orphaned_scenes()
        self.assertTrue(response)

        old_time = datetime.datetime.now() - datetime.timedelta(minutes=15)

        for s in Scene.where({'order_id': order_id}):
            self.assertTrue(s.reported_orphan is not None)
            s.reported_orphan = old_time
            s.save()

        response = production_provider.catch_orphaned_scenes()
        self.assertTrue(response)
        for s in Scene.where({'order_id': order_id}):
            self.assertTrue(s.orphaned)

    def test_convert_product_options(self):
        """
        Test the conversion procedure to make sure that the new format for orders converts
        to the old format
        """
        scenes = ['LE70480272012076EDC00', 'LC80500272013196LGN00',
                  'LT40480271983028PAC00', 'LT50490262009162PAC03']

        includes = ['include_sr', 'include_sr_toa',
                    'include_cfmask', 'include_sr_thermal']

        new_format = {u'etm7': {u'inputs': [u'LE70480272012076EDC00'],
                                u'products': [u'sr']},
                      u'olitirs8': {u'inputs': [u'LC80500272013196LGN00'],
                                    u'products': [u'toa']},
                      u'tm4': {u'inputs': [u'LT40480271983028PAC00'],
                               u'products': [u'cloud']},
                      u'tm5': {u'inputs': [u'LT50490262009162PAC03'],
                               u'products': [u'bt']},
                      u'format': u'gtiff',
                      u'image_extents': {u'east': -2265585.0,
                                         u'north': 3164805.0,
                                         u'south': 3014805.0,
                                         u'units': u'meters',
                                         u'west': -2415585.0},
                      u'note': u'CONUS_h1v1',

                      u'projection': {u'aea': {u'central_meridian': -96,
                                               u'datum': u'nad83',
                                               u'false_easting': 0,
                                               u'false_northing': 0,
                                               u'latitude_of_origin': 23,
                                               u'standard_parallel_1': 29.5,
                                               u'standard_parallel_2': 45.5}},
                      u'resampling_method': u'cc'}

        ruberic = {'central_meridian': -96,
                   'datum': u'nad83',
                   'false_easting': 0,
                   'false_northing': 0,
                   'image_extents': True,
                   'image_extents_units': u'meters',
                   'include_cfmask': False,
                   'include_customized_source_data': False,
                   'include_dswe': False,
                   'include_lst': False,
                   'include_solr_index': False,
                   'include_source_data': False,
                   'include_source_metadata': False,
                   'include_sr': False,
                   'include_sr_browse': False,
                   'include_sr_evi': False,
                   'include_sr_msavi': False,
                   'include_sr_nbr': False,
                   'include_sr_nbr2': False,
                   'include_sr_ndmi': False,
                   'include_sr_ndvi': False,
                   'include_sr_savi': False,
                   'include_sr_thermal': False,
                   'include_sr_toa': False,
                   'include_statistics': False,
                   'latitude_true_scale': None,
                   'longitude_pole': None,
                   'maxx': -2265585.0,
                   'maxy': 3164805.0,
                   'minx': -2415585.0,
                   'miny': 3014805.0,
                   'origin_lat': 23,
                   'output_format': u'gtiff',
                   'pixel_size': None,
                   'pixel_size_units': None,
                   'reproject': True,
                   'resample_method': 'cubic',
                   'resize': False,
                   'std_parallel_1': 29.5,
                   'std_parallel_2': 45.5,
                   'target_projection': u'aea',
                   'utm_north_south': None,
                   'utm_zone': None}

        for scene, include in zip(scenes, includes):
            ruberic[include] = True
            old_format = OptionsConversion.convert(new=new_format, scenes=[scene])

            self.assertDictEqual(ruberic, old_format)

            ruberic[include] = False

    def test_status_modified(self):
        order_id = self.mock_order.generate_testing_order(self.user_id)
        scene = Scene.where({'order_id': order_id}).pop()
        scene.status = 'oncache'
        scene.save()
        old_time = scene.status_modified
        scene.status = 'queued'
        scene.save()
        new_time = scene.status_modified
        self.assertGreater(new_time, old_time)

if __name__ == '__main__':
    unittest.main(verbosity=2)
