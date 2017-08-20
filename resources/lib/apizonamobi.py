# -*- coding: utf-8 -*-
# Module: apizonamobi
# License: GPL v.3 https://www.gnu.org/copyleft/gpl.html

import requests
import urllib
import re

class ZonaMobiApiError(Exception):
    def _init_(self, value, code):
         self.value = value
         self.code = code

class zonamobi:

    def __init__( self, params = {} ):

        self._items = []
        self._json = {}
        self._item = {}

        #Settings
        self.video_quality = params.get('video_quality', 0)

        #Инициализация
        base_url = 'https://zona.mobi'

        self._actions = {'main':            {'type': 'get', 'url': base_url},
                          'get_filters':     {'type': 'get', 'url': base_url + '/ajax/widget/filter'},
                          'get_video_url':   {'type': 'get', 'url': 'http://android.mzona.net/api/v1/video/#mobi_link_id'},
                          'search':          {'type': 'get', 'url': base_url + '/search//#keyword'},
                          #content
                          'browse_content':     {'type': 'get', 'url': base_url + '/#content/#filter'},
                          'browse_content_updates': {'type': 'get', 'url': base_url + '/updates/#content'},
                          'get_content_details': {'type': 'get', 'url': base_url + '/#content/#name_id'},                       
                          #tvseries
                          'browse_episodes': {'type': 'get', 'url': base_url + '/tvseries/#name_id/season-#season'}
                          }

    def _http_request( self, action, params = {}, data={}, url='', url_params={} ):
        action_settings = self._actions.get(action)

        if not url:
            url = action_settings.get('url', url)
            for key, val in url_params.iteritems():
                url = url.replace(key, val)
            
        cookies = {}

        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:54.0) Gecko/20100101 Firefox/54.0',
                   'Accept': 'application/json, text/javascript, */*; q=0.01',
                   'Accept-Encoding': 'gzip, deflate, br',
                   'Connection': 'keep-alive',
                   'X-Requested-With': 'XMLHttpRequest',
                   }
	
        request_type = action_settings.get('type', 'post')
        try:
            if request_type == 'post':
                r = requests.post(url, data=data, params=params, headers=headers, cookies=cookies)
            elif request_type == 'get':
                r = requests.get(url, data=data, params=params, headers=headers, cookies=cookies)
            else:
                raise ZonaMobiApiError('Wrong request_type %s' % (request_type), 1)

            r.raise_for_status()
        except requests.ConnectionError as err:
            raise ZonaMobiApiError('Connection error', 1)
        return r

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

    def get_video_list( self, type, params ):
        if type in ['movies', 'tvseries']:
            video_list = self._browse_content(type, params)
        elif type == 'seasons':
            video_list = self.browse_seasons(params)
        elif type == 'episodes':
            video_list = self.browse_episodes(params)
        elif type == 'search':
            video_list = self.search(params)
        return video_list
        
    def _browse_content( self, type, params ):

        u_params = {'page':    params.get('page', 1)}
        url_params = {'#content': type}

        if params.get('sort') == 'updates':
            action = 'browse_content_updates'
        else:
            action = 'browse_content'
            url_params['#filter'] = self._get_filter(params)

        r = self._http_request(action, u_params, url_params=url_params)

        self._json = r.json()

        self._items = self._json.get('items', [])
            
        result = {'count': len(self._items),
                  'title': self._json['title_h1'].strip().encode('utf-8'),
                  'total_pages': self._json.get('pagination', {}).get('total_pages', 0),
                  'list':  self._make_list(type)}
        return result

    def get_content_details( self, params ):
        url_params = {'#name_id': params['name_id']}

        content = params['type']

        if params.get('season'):
            action = 'browse_episodes'
            url_params['#season'] = str(params['season'])
        elif content in ['movies', 'tvseries']:
            action = 'get_content_details'
            url_params['#content'] = content

        r = self._http_request(action, url_params=url_params)
        self._json = r.json()

        if params['type'] == 'movies':
            self._item = self._json['movie']
        else:
            self._item = self._json['serial']
        
        details = self._get_details(params)
        return details

    def browse_episodes( self, params ):

        url_params = {'#name_id': params['name_id'],
                      '#season': params['season']}

        r = self._http_request('browse_episodes', url_params=url_params)
        self._json = r.json()

        self._item = self._json['serial']
        self._items = self._make_eposode_list()
        
        result = {'count': len(self._items),
                  'title': self._item['name_rus'],
                  'season': params['season'],
                  'list':  self._make_list('episodes')}
        return result

    def _make_eposode_list( self ):
        episodes = []

        items = self._json['episodes']['items']
        if type(items) == dict:
            episodes = range(0, len(items))
            for key, val in items.iteritems():
                episodes[int(key) - 1] = val
        elif type(items) == list:
            episodes = items
        
        return episodes
    
    def browse_seasons( self, params ):

        url_params = {'#content': 'tvseries',
                      '#name_id': params['name_id']}
                      
        r = self._http_request('get_content_details', url_params=url_params)
        self._json = r.json()
        
        self._item = self._json['serial']
        
        result = {'count': int(self._json['seasons']['count']),
                  'title': self._item['name_rus'],
                  'list':  self._make_list('seasons')}

        return result

    def get_filters( self ):
        r = self._http_request('get_filters')
        self._json = r.json()

        genres = []
        for key, genre in self._json['genres'].iteritems():
            genres.append({'name': genre['name'],
                          'value': genre['translit']
                          })

        countries = []
        for country in self._json['countries']:
            countries.append({'name': country['name'],
                              'value': country['translit']
                              })

        ratings = []
        for rating in xrange(9, 0, -1):
            ratings.append({'name': u'от %d' % rating,
                            'value': str(rating)
                            })

        r = self._http_request('main')
        self._json = r.json()

        current_year = self._json['current_year']
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
                  'country':  countries,
                  'rating': ratings,
                  'year': years,
                  'sort': sorts
                  }
                  
        return result
    
    def search( self, params ):

        url = self._actions['search'].get('url').replace('#keyword', urllib.quote(params['keyword']))

        u_params = {'page':    params.get('page', 1)}
        
        r = self._http_request('search', params = u_params, url = url)
        self._json = r.json()

        self._items = self._json.get('items', [])

        result = {'count': len(self._items),
                  'title': params['keyword'],
                  'total_pages': self._json['pagination']['total_pages'],
                  'list':  self._make_list('search')
                  }
        return result
    
    def get_content_url( self, params ):

        video_details = self.get_content_details(params)
        
        video_info = video_details['video_info']
        item_info  = video_details['item_info']
        
        url_params = {'#mobi_link_id': str(video_info['mobi_link_id'])}
        r = self._http_request('get_video_url', url_params=url_params)
        self._json = r.json()

        path = self._get_video_url(video_info['mobi_link_id'])
       
        item_info['path'] = path
        return item_info

    def get_trailer_url( self, params ):

        video_details = self.get_content_details(params)
        
        if self._item['trailer']['url']:
            path = self._item['trailer']['url']
        else:
            path = self._get_video_url(self._item['trailer']['id'])
       
        item_info = {'path': path}
        return item_info

    def _get_video_url( self, mobi_link_id ):
        video_quality = self.video_quality

        url_params = {'#mobi_link_id': str(mobi_link_id)}
        r = self._http_request('get_video_url', url_params=url_params)
        self._json = r.json()

        path = ''
        if not path or video_quality >= 0:
            path = self._json['lqUrl']
        if not path or video_quality >= 1:
            path = self._json['url']
            
        return path

    def _make_list( self, source, params = {} ):

        if source in ('movies', 'tvseries', 'search'):
            for item in self._items:
                video_info = {'type':    'tvseries' if item['serial'] else 'movies',
                              'name_id': item['name_id'],
                              }

                title = item['name_rus']
                title_orig = item.get('name_eng') if item.get('name_eng') else item['name_rus']

                item_info = {'label':  title,
                             'ratings': self._get_rating(item),
                             'info': {'video': {'year': item.get('year'),
                                                'title': title,
                                                'originaltitle': title_orig,
                                                'sorttitle': title,
                                                'tvshowtitle': title if item['serial'] else '',
                                                'mediatype': 'tvshow' if item['serial'] else 'movie'
                                                }
                                      },
                             'art': {'poster': item['cover']},
                             'thumb': item['cover'],
                            }

                video_info = {'item_info':  item_info,
                              'video_info': video_info
                              }
                              
                yield video_info

        elif source == 'episodes':

            item = self._item
            
            title = item['name_rus']
            title_orig = item.get('name_eng') if item.get('name_eng') else item['name_rus']

            for episode in self._items:
                video_info = {'type': source,
                              'name_id': item['name_id'],
                              'season': episode['season'],
                              'episode': episode['episode'],
                              'originaltitle': item.get('name_original') if item.get('name_original') else item['name_rus'],
                              }
                yield self._get_details( video_info )

        elif source == 'seasons':
            item = self._item
            
            for season in xrange(1, self._json['seasons']['count'] + 1):
                video_info = {'type':    source,
                              'name_id': item['name_id'],
                              'season':  season}

                yield self._get_details( video_info )
    
    def _get_episode( self, episode, season ):
        for episode_ in self._make_eposode_list():
            if episode_['episode'] == int(episode) \
               and episode_['season'] == int(season):
                return episode_
        return {}

    def _get_rating( self, item ):
    
        r_kinopoisk = self._make_rating(item, 'kinopoisk')
        r_imdb = self._make_rating(item, 'imdb')
        r_zona = self._make_rating(item, 'zona')

        return [r_imdb, r_kinopoisk, r_zona]

    def _make_rating( self, item, type ):

        keys = ['rating']
        if type != 'zona':
            keys.append(type)
        rating_field = '_'.join(keys)
        
        keys.append('count')
        votes_field = '_'.join(keys)
        
        rating = item.get(rating_field, '0')
        if rating is not None:
            rating = float(rating)
        else:
            rating = 0
            
        return {'type':	type,
                'rating': rating,
                'votes': item.get(votes_field, 0),
                'defaultt': False,
                }
        
    def _get_premiere_date( self ):
        item = self._item
        
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
        
    def _get_details( self, params = {} ):

        item = self._item

        video_info = {}
        video_info.update(params)
        
        #Defaults
        poster = item['image']
        thumb = item['image']
        fanart = self._json['backdrops']['image_1280']
        plot = item.get('description')

        premiered = self._get_premiere_date()
        mediatype = 'video'

        aired = ''
        mobi_link_id = ''
        label = ''
        title = ''
        originaltitle = ''
        tvshowtitle = ''
        episode = None
        season = None
        rating = []
        properties = {}
        
        #Titles
        item_title = item['name_rus']
        item_title_orig = item.get('name_original') if item.get('name_original') else item['name_rus']
        if type(item_title) == int:
            item_title = str(item_title)
        if type(item_title_orig) == int:
            item_title_orig = str(item_title_orig)

        #Duration
        if item['runtime']:
            duration = item['runtime']['value'] * 60
        else:
            duration = 0

        #Genres
        genres = []
        for genre in self._json['genres']:
            genres.append(genre['name'])
        
        
        persons = self._json.get('persons', {})

        #Cast
        cast = []
        for actor in persons.get('actors', []):
            cast.append({'name': actor['name'],
                         'thumbnail': actor['cover']})

        #Director
        director = []
        for director_ in persons.get('director', []):
            director.append(director_['name'])

        #Writer
        writer = []
        for scenarist in persons.get('scenarist', []):
            writer.append(scenarist['name'])

        #Country
        country = []
        for country_ in self._json.get('countries', []):
            country.append(country_['name'])

        #Date
        mobi_link_date = item.get('mobi_link_date', '')
        if mobi_link_date:
            date = ('%s.%s.%s') %(mobi_link_date[8:10], mobi_link_date[5:7], mobi_link_date[0:4])
        else:
            date = ''
        
        if item['serial']:
            tvshowtitle = item_title
            
            p_episode = params.get('episode')
            p_season = params.get('season')

            season = self._json['seasons']['count']
            episode = self._json['episodes']['count_all']
            
            if p_episode is not None:
                episode_ = self._get_episode(p_episode, p_season)
                mobi_link_id = episode_.get('mobi_link_id','')

                mediatype = 'episode'
                thumb = self._json['images'].get(str(mobi_link_id))

                release_date = episode_.get('release_date')
                if release_date:
                    aired = release_date[0:10]
                    
                title = episode_.get('title', '')
                if type(title) == int:
                    title = str(title)
                originaltitle = title

                episode = episode_['episode']
                season = episode_['season']
                
                # plot = ''
                
            elif p_season is not None:
                mediatype = 'season'
                title = item_title
                originaltitle = item_title_orig
                duration = 0
                episodes = self._make_eposode_list()
                for episode_ in episodes:
                    if episode_['episode'] == 1:
                      if episode_['release_date']:
                        aired = episode_['release_date'][0:10]
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
            mobi_link_id = item.get('mobi_link_id','')
            
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
                                               
        video_info.update({'have_trailer': True if item.get('trailer_url') else False,
                           'name_id':      item['name_id'],
                           'mobi_link_id': mobi_link_id})

        return {'item_info':  item_info,
                'video_info': video_info}
        