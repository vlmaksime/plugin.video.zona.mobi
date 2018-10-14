# coding: utf-8
# Module: tests

import os
import sys
import unittest
import shutil

cwd = os.path.dirname(os.path.abspath(__file__))
cache_dir = os.path.join(cwd, 'cache')

plugin_name = 'plugin.video.zona.mobi'

# Import our module being tested
sys.path.append(os.path.join(cwd, plugin_name))
from resources.lib.zonamobi import ZonaMobi

def tearDownModule():
    shutil.rmtree(cache_dir, True)

class ZonaMobiTestCase(unittest.TestCase):
    """
    Test ZonaMobi class
    """

    def setUp(self):
        params = {'cache_dir': cache_dir,
                  'load_details': True,
                  'video_quality': 1,
                  }

        self.api = ZonaMobi(params)

    def test_browse_content_movies(self):
        print('\n#test_browse_content_movies')

        video_list = self.api.get_video_list('movies')

        has_video = False

        print('In list %d movies:' % (video_list['count']))
        for video in video_list['list']:
            video_info = video['video_info']
            print('name_id: %s' % (video_info['name_id']))
            has_video = True

        self.assertTrue(has_video)

    def test_browse_content_tvseries(self):
        print('\n#test_browse_content_tvseries')

        video_list = self.api.get_video_list('tvseries')

        has_video = False

        print('In list %d tvseries:' % (video_list['count']))
        for video in video_list['list']:
            video_info = video['video_info']
            print('name_id: %s' % (video_info['name_id']))
            has_video = True

        self.assertTrue(has_video)

    def test_browse_seasons(self):
        print('\n#test_browse_seasons')

        params = {'name_id': 'futurama'}

        video_list = self.api.get_video_list('seasons', params)

        has_video = False

        print('"%s" has %d seasons:' % (video_list['title'], video_list['count']))
        for video in video_list['list']:
            video_info = video['video_info']
            item_info = video['item_info']
            print('name_id: %s, season: %d' % (video_info['name_id'], video_info['season']))
            has_video = True

        self.assertTrue(has_video)

    def test_browse_episodes(self):
        print('\n#test_seasons_list')

        params = {'name_id': 'futurama',
                  'season': 1}

        video_list = self.api.get_video_list('episodes', params)

        has_video = False

        print('"%s" in season %d has %d episodes:' % (video_list['title'],video_list['season'] , video_list['count']))
        for video in video_list['list']:
            video_info = video['video_info']
            item_info = video['item_info']
            print('name_id: %s, episode: %d' % (video_info['name_id'], video_info['episode']))
            has_video = True

        self.assertTrue(has_video)

    def test_search(self):
        print('\n#test_search')

        params = {'keyword': 'Futurama'}

        video_list = self.api.get_video_list('search', params)

        has_video = False

        print('There are %d results for "%s":' % (video_list['count'], video_list['title']))
        for video in video_list['list']:
            video_info = video['video_info']
            item_info = video['item_info']
            print('name_id: %s, type: %s' % (video_info['name_id'], video_info['type']))
            has_video = True

        self.assertTrue(has_video)

    def test_get_content_url_movies(self):
        print('\n#test_get_content_url_movies')

        params = {'type': 'movies',
                  'name_id': 'futurama-zver-s-milliardom-spin'}

        item_info = self.api.get_content_url(params)
        print('For "%s" url is "%s":' % (item_info['info']['video']['title'], item_info['path']))
        self.assertNotEqual(item_info['path'], '')

    def test_get_content_url_tvseries(self):
        print('\n#test_get_content_url_tvseries')

        params = {'type': 'episodes',
                  'name_id': 'futurama',
                  'season': 1,
                  'episode': 1,
                  }

        item_info = self.api.get_content_url(params)
        print('For "%s" episode "%s" url is "%s":' % (item_info['info']['video']['tvshowtitle'], item_info['info']['video']['title'], item_info['path']))
        self.assertNotEqual(item_info['path'], '')

    def test_get_trailer_url_movies(self):
        print('\n#test_get_trailer_url_movies')

        params = {'type': 'movies',
                  'name_id': 'futurama-zver-s-milliardom-spin'}

        item_info = self.api.get_trailer_url(params)

        print(item_info['path'])

        self.assertNotEqual(item_info['path'], '')

    def test_get_trailer_url_tvseries(self):
        print('\n#test_get_trailer_url_tvseries')

        params = {'type': 'tvseries',
                  'name_id': 'interny',
                  }

        item_info = self.api.get_trailer_url(params)
        print(item_info['path'])
        self.assertNotEqual(item_info['path'], '')

    def test_get_filters(self):
        print('\n#get_filters')

        has_filters = False

        filters = self.api.get_filters()
        for filter, values in filters.iteritems():
            has_filters = True
            print('filter %s:' %(filter))
            for val in values:
                print('value: %s, name: %s' % (val['value'], val['name']))

        self.assertTrue(has_filters)

if __name__ == '__main__':
    unittest.main()