# -*- coding: utf-8 -*-
# Module: apizonamobi
# License: GPL v.3 https://www.gnu.org/copyleft/gpl.html

import requests
import urllib
import os
import sqlite3
import time
try:
    import json
except ImportError:
    import simplejson as json

class ZonaMobiApiError(Exception):
    """Custom exception"""
    pass

class ZonaMobiCache:

    def __init__( self, cache_dir, cache_hours=48 ):
        self._version = 1

        self._time_delta = cache_hours * 3600 #time in seconds

        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
        db_path = os.path.join(cache_dir, 'cache.db')

        db_exist = os.path.exists(db_path)

        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = self._dict_factory

        if db_exist:
            self.check_for_update()
            self.remove_old_data()
        else:
            self.create_database()

    def _dict_factory(self, cursor, row):
        d = {}
        for idx, col in enumerate(cursor.description):
            d[col[0]] = row[idx]
        return d

    def check_for_update(self):

        c = self.conn.cursor()
        c.execute('SELECT idVersion FROM version LIMIT 1')

        result = c.fetchone()
        if result['idVersion'] < self._version:
            c.execute('DELETE FROM version')
            c.execute('INSERT INTO version (idVersion) VALUES (:version)', {'version': self._version} )

            self.conn.commit()


    def create_database(self):

        c = self.conn.cursor()
        c.execute('CREATE TABLE version (idVersion integer)')
        c.execute('CREATE TABLE details (name_id text, season integer, data text, time integer)')

        c.execute('CREATE UNIQUE INDEX details_idx ON details(name_id, season)')
        c.execute('INSERT INTO version (idVersion) VALUES (:version)', {'version': self._version} )

        self.conn.commit()

    def get_details(self, params):
        sql_params = {'name_id': params['name_id'],
                      'season': params.get('season', 0)}

        c = self.conn.cursor()
        c.execute('SELECT data FROM details WHERE name_id = :name_id AND season = :season LIMIT 1', sql_params)

        result = c.fetchone()
        if result is not None:
            return result['data']

    def set_details(self, params, data):

        sql_params = {'data': data,
                      'name_id': params['name_id'],
                      'season': params.get('season', 0),
                      'time': time.time()}

        c = self.conn.cursor()
        c.execute('INSERT OR REPLACE INTO details (name_id, season, data, time) VALUES (:name_id, :season, :data, :time)', sql_params)

        self.conn.commit()

    def set_details_list(self, items):

        if items:
            c = self.conn.cursor()
            c.executemany('INSERT OR REPLACE INTO details (name_id, season, data, time) VALUES (:name_id, :season, :data, :time)', items)

            self.conn.commit()

    def remove_old_data(self):

        sql_params = {'time': time.time() - self._time_delta}

        c = self.conn.cursor()
        c.execute('DELETE FROM details WHERE time < :time', sql_params)

        self.conn.commit()

class ZonaMobi:

    def __init__( self, params = {} ):

        #Settings
        self.video_quality = params.get('video_quality', 0)
        self.load_details = params.get('load_details', False)
        cache_dir = params.get('cache_dir')

        if cache_dir is not None:
            self._cache = ZonaMobiCache(cache_dir)

        #URLs
        base_url = 'https://w1.zona.plus'

        self._actions = {'main': {'url': base_url},
                         'get_filters': {'url': base_url + '/ajax/widget/filter'},
                         'get_video_url': {'url': base_url + '/api/v1/video/#mobi_link_id'},
                         'search': {'url': base_url + '/search//#keyword'},
                         #content
                         'browse_content': {'url': base_url + '/#content/#filter'},
                         'browse_content_updates': {'url': base_url + '/updates/#content'},
                         'get_content_details': {'url': base_url + '/#content/#name_id'},
                         #tvseries
                         'browse_episodes': {'url': base_url + '/tvseries/#name_id/season-#season'}
                         }

        self._html_headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:54.0) Gecko/20100101 Firefox/54.0',
                              'Accept': 'application/json, text/javascript, */*; q=0.01',
                              'Accept-Encoding': 'gzip, deflate, br',
                              'Connection': 'keep-alive',
                              'X-Requested-With': 'XMLHttpRequest',
                              }


    def _http_request( self, action, params=None, data=None, url='', url_params=None ):
        params = params or {}
        data = data or {}
        url_params = url_params or {}
        
        action_settings = self._actions.get(action)

        if not url:
            url = action_settings.get('url', url)
            for key, val in url_params.iteritems():
                url = url.replace(key, str(val))

        try:
            r = requests.get(url, data=data, params=params, headers=self._html_headers)
            r.raise_for_status()
        except requests.ConnectionError as err:
            raise ZonaMobiApiError('Connection error')
        except requests.exceptions.HTTPError as err:
            raise ZonaMobiApiError(err)
        return r


    def _sort_by_episode(self, item):
        return item.get('episode_key', '')

    def _get_filter( self, params ):
        filter_keys = ['genre', 'year', 'country', 'rating', 'sort']
        filters = []
        for filter_key in filter_keys:
            filter_value = params.get(filter_key)
            if filter_value:
                filters.append('%s-%s' % (filter_key, filter_value))

        if len(filters):
            filters.insert(0, 'filter')
        return '/'.join(filters)

    def get_video_list( self, content_type, params={} ):
        if content_type in ['movies', 'tvseries']:
            video_list = self.browse_content(content_type, params)
        elif content_type == 'seasons':
            video_list = self.browse_seasons(params)
        elif content_type == 'episodes':
            video_list = self.browse_episodes(params)
        elif content_type == 'search':
            video_list = self.search(params)
        return video_list

    def browse_content( self, content_type, params ):

        u_params = {'page':    params.get('page', 1)}
        url_params = {'#content': content_type}

        if params.get('sort') == 'updates':
            action = 'browse_content_updates'
        else:
            action = 'browse_content'
            url_params['#filter'] = self._get_filter(params)

        r = self._http_request(action, u_params, url_params=url_params)

        data = r.json()
        items = data.get('items', [])

        result = {'count': len(items),
                  'title': data['title_h1'].strip(),
                  'total_pages': data.get('pagination', {}).get('total_pages', 0),
                  'list':  self._make_list(content_type, data, items)}
        return result

    def browse_episodes( self, params ):

        url_params = {'#name_id': params['name_id'],
                      '#season': str(params['season'])}

        r = self._http_request('browse_episodes', url_params=url_params)
        data = r.json()

        item = data['serial']
        items = self._make_eposode_list(data)

        result = {'count': len(items),
                  'title': item['name_rus'],
                  'season': params['season'],
                  'list':  self._make_list('episodes', data, items, item)}
        return result

    def _make_eposode_list( self, data ):
        episodes = []

        items = data['episodes']['items']
        if isinstance(items, dict):
            for key, val in items.iteritems():
                episodes.append(val)
        elif isinstance(items, list):
            episodes = items

        episodes.sort(key=self._sort_by_episode)

        return episodes

    def browse_seasons( self, params ):

        url_params = {'#content': 'tvseries',
                      '#name_id': params['name_id']}

        r = self._http_request('get_content_details', url_params=url_params)
        data = r.json()

        item = data['serial']

        result = {'count': int(data['seasons']['count']),
                  'title': item['name_rus'],
                  'list':  self._make_list('seasons', data, item=item)}

        return result

    def get_filters( self ):
        r = self._http_request('get_filters')
        data = r.json()

        genres = []
        for key, genre in data['genres'].iteritems():
            genres.append({'name': genre['name'],
                          'value': genre['translit']
                          })

        countries = []
        for country in data['countries']:
            countries.append({'name': country['name'],
                              'value': country['translit']
                              })

        ratings = []
        for rating in xrange(9, 0, -1):
            ratings.append({'name': u'от %d' % rating,
                            'value': str(rating)
                            })

        r = self._http_request('main')
        data = r.json()

        current_year = data['current_year']
        last_year = current_year // 10 * 10

        years = []
        for year in xrange(current_year, last_year - 1, -1):
            years.append({'name': str(year),
                          'value': str(year)
                          })
        for year in xrange(last_year - 10, 1930, -10):
            val = year if year >= 2000 else year % 100
            years.append({'name': u'%d-е' % (val),
                          'value': '%ds' % (val)
                          })
        years.append({'name': u'до 40-х',
                      'value': 'old'
                      })

        sorts = []
        sorts.append({'name': u'По популярности',
                      'value': ''
                      })
        sorts.append({'name': u'По рейтингу',
                      'value': 'rating'
                      })
        sorts.append({'name': u'По дате выхода',
                      'value': 'date'
                      })
        sorts.append({'name': u'Последние обновления',
                      'value': 'updates'
                      })

        result = {'genre': genres,
                  'country': countries,
                  'rating': ratings,
                  'year': years,
                  'sort': sorts
                  }

        return result

    def search( self, params ):

        url = self._actions['search'].get('url').replace('#keyword', urllib.quote(params['keyword']))

        u_params = {'page':    params.get('page', 1)}

        r = self._http_request('search', params = u_params, url = url)
        data = r.json()

        items = data.get('items', [])

        result = {'count': len(items),
                  'title': params['keyword'],
                  'is_second': data['is_second'],
                  'total_pages': data['pagination']['total_pages'],
                  'list':  self._make_list('search', data, items)
                  }
        return result

    def _get_content_data(self, params):
        url_params = {'#name_id': params['name_id']}

        content = params['type']

        if content == 'episodes':
            action = 'browse_episodes'
            url_params['#season'] = params['season']
        elif content in ['movies', 'tvseries']:
            action = 'get_content_details'
            url_params['#content'] = content
        else:
            action = None

        if self._cache is not None:
            cached_data = self._cache.get_details(params)

        if action is not None \
          and (self._cache is None \
               or cached_data is None):
            r = self._http_request(action, url_params=url_params)
            data = r.json()

        if self._cache is not None:
            if cached_data is None:
                self._cache.set_details(params, r.text)
            else:
                data = json.loads(cached_data)

        return data

    def get_content_url( self, params ):

        data = self._get_content_data(params)

        if params['type'] == 'movies':
            item = data['movie']
        else:
            item = data['serial']

        item_info = self._get_item_info(data, item, params=params)

        if params['type'] == 'movies':
            mobi_link_id = item['mobi_link_id']
        else:
            episode = self._get_episode(params['episode'], params['season'], data)
            mobi_link_id = episode.get('mobi_link_id','')

        path = self._get_video_url(mobi_link_id)

        item_info['path'] = path
        return item_info

    def get_trailer_url( self, params ):

        data = self._get_content_data(params)

        if params['type'] == 'movies':
            item = data['movie']
        else:
            item = data['serial']

        if item['trailer']['url']:
            path = item['trailer']['url']
        else:
            path = self._get_video_url(item['trailer']['id'])

        item_info = {'path': path}
        return item_info

    def _get_video_url( self, mobi_link_id ):
        video_quality = self.video_quality

        url_params = {'#mobi_link_id': str(mobi_link_id)}
        r = self._http_request('get_video_url', url_params=url_params)
        data = r.json()

        path = ''
        if not path or video_quality >= 0:
            path = data['lqUrl']
        if not path or video_quality >= 1:
            path = data['url']

        return path

    def _get_items_details(self, source, data):

        details = {}
        if not self.load_details:
            return details

        req_items = []
        for item in data:
            if source in ['movies', 'tvseries', 'search']:
                params = {'name_id': item['name_id'],
                          'season': 0,
                          'content': 'tvseries' if item['serial'] else 'movies'}
                req_items.append(params)
            elif source == 'seasons':
                item = data['serial']
                for season in xrange(1, data['seasons']['count'] + 1):
                    params = {'name_id': item['name_id'],
                              'season': season,
                              'content': 'tvseries' if item['serial'] else 'movies'}
                    req_items.append(params)



        if self._cache is not None:
            items_for_caching =[]

            for item in req_items:
                cached_data = self._cache.get_details(item)
                if cached_data is not None:
                    item_key = '%s_%d' % (item['name_id'], item['season'])
                    details[item_key] = json.loads(cached_data)

        for item in req_items:
            item_key = '%s_%d' % (item['name_id'], item['season'])
            if details.get(item_key) is None:
                url_params = {'#name_id': item['name_id']}

                if source == 'seasons':
                    action = 'browse_episodes'
                    url_params['#season'] = item['season']
                else:
                    action = 'get_content_details'
                    url_params['#content'] = item['content']

                r = self._http_request(action, url_params=url_params)

                details[item_key] = r.json()

                if self._cache is not None:
                    item_for_caching = {'name_id': item['name_id'],
                                        'season': item['season'],
                                        'time': time.time(),
                                        'data': r.text,
                                        }
                    items_for_caching.append(item_for_caching)

        if self._cache is not None:
            self._cache.set_details_list(items_for_caching)

        return details

    def _make_list( self, source, data, items=None, item=None, params=None ):
        items = items or []
        item = item or {}
        params = params or {} 

        if source in ['movies', 'tvseries', 'search']:

            details = self._get_items_details(source, items)

            for item in items:
                item_key = '%s_%d' % (item['name_id'], 0)

                full_details = True
                item_data = details.get(item_key)
                if item_data is not None:
                    item_type = 'serial' if item['serial'] else 'movie'
                    item_detail = item_data[item_type]
                else:
                    full_details = False
                    item_detail = item

                video_info = {'type': 'tvseries' if item_detail['serial'] else 'movies',
                              'name_id': item_detail['name_id'],
                              'have_trailer': True if item_detail.get('trailer_url') else False,
                              }

                item_info = self._get_item_info(item_data, item_detail, full_details )

                video_info = {'item_info':  item_info,
                              'video_info': video_info,
                              }

                yield video_info

        elif source == 'seasons':

            details = self._get_items_details(source, data)

            for season in xrange(1, data['seasons']['count'] + 1):
                item_key = '%s_%d' % (item['name_id'], season)

                full_details = True
                item_data = details.get(item_key)
                if item_data is not None:
                    item_type = 'serial' if item['serial'] else 'movie'
                    season_detail = item_data[item_type]
                    season_data = item_data
                else:
                    full_details = False
                    season_detail = item
                    season_data = data

                video_info = {'type':    source,
                              'name_id': item['name_id'],
                              'season':  season}

                item_info = self._get_item_info(season_data, season_detail, params=video_info )

                video_info = {'item_info':  item_info,
                              'video_info': video_info,
                              }

                yield video_info

        elif source == 'episodes':

            title = item['name_rus']
            title_orig = item.get('name_eng') if item.get('name_eng') else item['name_rus']
            if isinstance(title, int):
                title = str(title)
            if isinstance(title_orig, int):
                title_orig = str(title_orig)

            for episode in items:
                video_info = {'type': source,
                              'name_id': item['name_id'],
                              'season': episode['season'],
                              'episode': episode['episode'],
                              'originaltitle': item.get('name_original') if item.get('name_original') else item['name_rus'],
                              }

                item_info = self._get_item_info(data, item, params=video_info )

                video_info = {'item_info':  item_info,
                              'video_info': video_info,
                              }

                yield video_info

    def _get_episode( self, episode, season, data ):
        for _episode in self._make_eposode_list(data):
            if _episode['episode'] == int(episode) \
               and _episode['season'] == int(season):
                return _episode
        return {}

    def _get_rating( self, item ):

        r_kinopoisk = self._make_rating(item, 'kinopoisk')
        r_imdb = self._make_rating(item, 'imdb')
        r_zona = self._make_rating(item, 'zona')

        return [r_imdb, r_kinopoisk, r_zona]

    def _make_rating( self, item, rating_source ):

        keys = ['rating']
        if rating_source != 'zona':
            keys.append(rating_source)
        rating_field = '_'.join(keys)

        keys.append('count')
        votes_field = '_'.join(keys)

        rating = item.get(rating_field, '0')
        if rating is not None:
            rating = float(rating)
        else:
            rating = 0

        return {'type':	rating_source,
                'rating': rating,
                'votes': item.get(votes_field, 0),
                'defaultt': False,
                }

    def _get_premiere_date( self, item ):

        premiered = ''

        months = {u'января':   1,
                  u'февраля':  2,
                  u'марта':    3,
                  u'апреля':   4,
                  u'мая':      5,
                  u'июня':     6,
                  u'июля':     7,
                  u'августа':  8,
                  u'сентября': 9,
                  u'октября': 10,
                  u'ноября':  11,
                  u'декабря': 12,
                  }

        release_date_int = item.get('release_date_int', '')
        release_date_rus = item.get('release_date_rus', '')

        if release_date_int:
            release_date = release_date_int
        else:
            release_date = release_date_rus

        if release_date:
            parts = release_date.split(' ')
            premiered = '%s-%02d-%02d' % (parts[2], months[parts[1]], int(parts[0]))

        return premiered

    def _get_item_info( self, data, item, full_details=True, params={} ):

        #Default variables
        fanart = ''
        aired = ''
        date = ''
        premiered = ''
        title = ''
        originaltitle = ''
        tvshowtitle = ''
        plot = ''
        episode = None
        season = None
        mobi_link_id = ''

        ratings = []
        genres = []
        cast = []
        director = []
        writer = []
        country = []

        properties = {}
        mediatype = 'video'
        duration = 0

        #Defaults
        if full_details:
            poster = item['image']
            fanart = data['backdrops']['image_1280']
            plot = item.get('description')
            premiered = self._get_premiere_date(item)
        else:
            poster = item['cover']

        thumb = poster

        #Titles
        item_title = item['name_rus']
        if isinstance(item_title, int):
            item_title = str(item_title)

        if full_details:
            item_title_orig = item.get('name_original') if item.get('name_original') else item['name_rus']
        else:
            item_title_orig = item.get('name_eng') if item.get('name_eng') else item['name_rus']
        if isinstance(item_title_orig, int):
            item_title_orig = str(item_title_orig)

        if full_details:
            #Duration
            if item['runtime']:
                duration = item['runtime']['value'] * 60

            #Genres
            for genre in data['genres']:
                genres.append(genre['name'])

            persons = data.get('persons', {})

            #Cast
            for actor in persons.get('actors', []):
                cast.append({'name': actor['name'],
                             'thumbnail': actor['cover']})

            #Director
            for _director in persons.get('director', []):
                director.append(_director['name'])

            #Writer
            for scenarist in persons.get('scenarist', []):
                writer.append(scenarist['name'])

            #Country
            for _country in data.get('countries', []):
                country.append(_country['name'])

            #Date
            mobi_link_date = item.get('mobi_link_date', '')
            if mobi_link_date:
                date = ('%s.%s.%s') %(mobi_link_date[8:10], mobi_link_date[5:7], mobi_link_date[0:4])

        if item['serial']:
            tvshowtitle = item_title

            p_episode = params.get('episode')
            p_season = params.get('season')

            if data is not None:
                season = data['seasons']['count']
                episode = data['episodes']['count_all']

            if p_episode is not None:
                _episode = self._get_episode(p_episode, p_season, data)
                mobi_link_id = _episode.get('mobi_link_id','')

                mediatype = 'episode'
                thumb = data['images'].get(str(mobi_link_id))

                release_date = _episode.get('release_date')
                if release_date:
                    aired = release_date[0:10]

                title = _episode.get('title', '')
                if type(title) == int:
                    title = str(title)
                originaltitle = title

                episode = _episode['episode']
                season = _episode['season']


                if episode == 0:
                    episode = season
                    season = 0

            elif p_season is not None:
                mediatype = 'season'
                title = item_title
                originaltitle = item_title_orig
                episodes = self._make_eposode_list(data)
                for _episode in episodes:
                    if _episode['episode'] == 1:
                      if _episode['release_date']:
                        aired = _episode['release_date'][0:10]
                      break
                properties['TotalEpisodes'] = str(len(episodes))
                properties['WatchedEpisodes'] = '0'
            else:
                mediatype = 'tvshow'
                title = item_title
                originaltitle = item_title_orig
                ratings = self._get_rating(item)

                properties['TotalSeasons'] = str(season)
                properties['TotalEpisodes'] = str(episode)
                properties['WatchedEpisodes'] = '0'
        else:
            mediatype = 'movie'
            title = item_title
            originaltitle = item_title_orig
            ratings = self._get_rating(item)

        item_info = {# 'label':  label,
                     'cast':   cast,
                     'ratings': ratings,
                     'properties': properties,
                     'info': {'video': {'date': date,
                                        'genre': genres,
                                        'country': country,
                                        'year': item.get('year'),
                                        'sortepisode': episode,
                                        'sortseason': season,
                                        'director': director,
                                        'plot': plot,
                                        'title': title,
                                        'originaltitle': originaltitle,
                                        'sorttitle': title,
                                        'duration': duration,
                                        'writer': writer,
                                        'premiered': premiered,
                                        'aired': aired,
                                        'mediatype': mediatype,
                                        }
                              },
                     'art': {'poster': poster},
                     'fanart': fanart,
                     'thumb':  thumb,
                    }
        if item['serial']:
            item_info['info']['video'].update({'episode': episode,
                                               'season': season,
                                               'tvshowtitle': tvshowtitle,
                                               })

        return item_info