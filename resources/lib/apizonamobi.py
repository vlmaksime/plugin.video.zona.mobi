# -*- coding: utf-8 -*-
# Module: apizonamobi
# License: GPL v.3 https://www.gnu.org/copyleft/gpl.html

import requests
import urllib
import re

class ZonaMobiApiError(Exception):
    def __init__(self, value, code):
         self.value = value
         self.code = code

class zonamobi:

    def __init__( self, params = {} ):

        self.__items = []
        self.__episodes = []
        self.__json = {}
        self.__item = {}

        #Settings
        self.video_quality = params.get('video_quality', 0)

        #Инициализация
        base_url = 'https://zona.mobi'

        self.__actions = {'main':            {'type': 'get', 'url': base_url},
                          'get_filters':     {'type': 'get', 'url': base_url + '/ajax/widget/filter'},
                          'get_video_url':   {'type': 'get', 'url': 'http://android.mzona.net/api/v1/video/#id'},
                          'search':          {'type': 'get', 'url': base_url + '/search//#keyword'},
                          #movies
                          'browse_movies':     {'type': 'get', 'url': base_url + '/movies/#filter'},
                          'browse_movies_updates': {'type': 'get', 'url': base_url + '/updates/movies'},
                          'get_movie_details': {'type': 'get', 'url': base_url + '/movies/#name_id'},                       
                          #tvseries
                          'browse_tvseries_updates': {'type': 'get', 'url': base_url + '/updates/tvseries'},
                          'browse_tvseries': {'type': 'get', 'url': base_url + '/tvseries/#filter'},
                          'get_tvseries_details': {'type': 'get', 'url': base_url + '/tvseries/#name_id'},                       
                          'browse_episodes': {'type': 'get', 'url': base_url + '/tvseries/#name_id/season-#season'}
                          }

    def __http_request( self, action, params = {}, data={}, url='' ):
        action_settings = self.__actions.get(action)

        if not url:
            url = action_settings.get('url', url)
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

            if r.status_code != 404:
                r.raise_for_status()
        except requests.ConnectionError as err:
            raise ZonaMobiApiError('Connection error', 1)
        return r

    def __get_filter( self, params ):
        filter_keys = ['genre', 'year', 'country', 'rating', 'sort']
        filters = []
        for filter_key in filter_keys:
            filter_value = params.get(filter_key)
            if filter_value:
                filters.append('%s-%s' % (filter_key, filter_value))
        
        if len(filters):
            filters.insert(0, 'filter')
        return '/'.join(filters)
        
    def browse_movies( self, params ):

        u_params = {'page':    params.get('page', 1)
                    }

        if params.get('sort') == 'updates':
            r = self.__http_request('browse_movies_updates', u_params)
        else:
            filter = self.__get_filter(params)
            url = self.__actions['browse_movies'].get('url').replace('#filter', filter)

            r = self.__http_request('browse_movies', u_params, url = url)

        if r.status_code != 404:
            self.__json = r.json()
        else:
            self.__json = {}

        self.__items = self.__json.get('items', [])
            
        result = {'count': len(self.__items),
                  'title': self.__json['title_h1'].strip(),
                  'total_pages': self.__json.get('pagination', {}).get('total_pages', 0),
                  'list':  self.__make_list('movies')}
        return result

    def get_movie_details( self, params ):
        url = self.__actions['get_movie_details'].get('url').replace('#name_id', params['name_id'])

        r = self.__http_request('get_movie_details', url = url)
        self.__json = r.json()

        self.__item = self.__json['movie']
        details = self.__get_details()
        return details

    def browse_tvseries( self, params ):

        u_params = {'page':    params.get('page', 1)
                    }

        if params.get('sort') == 'updates':
            r = self.__http_request('browse_tvseries_updates', u_params)
        else:
            filter = self.__get_filter(params)
            url = self.__actions['browse_tvseries'].get('url').replace('#filter', filter)

            r = self.__http_request('browse_tvseries', u_params, url = url)

        if r.status_code != 404:
            self.__json = r.json()
        else:
            self.__json = {}


        self.__items = self.__json.get('items', [])

        result = {'count': len(self.__items),
                  'title': self.__json['title_h1'].strip(),
                  'total_pages': self.__json.get('pagination', {}).get('total_pages', 0),
                  'list':  self.__make_list('movies')}
        return result

    def get_tvseries_details( self, params ):

        if params.get('season'):
            url = self.__actions['browse_episodes'].get('url').replace('#name_id', params['name_id']).replace('#season', str(params['season']))
        else:
            url = self.__actions['get_tvseries_details'].get('url').replace('#name_id', params['name_id'])

        r = self.__http_request('get_tvseries_details', url = url)
        self.__json = r.json()

        self.__item = self.__json['serial']
        
        details = self.__get_details(params)
        return details

    def browse_episodes( self, params ):

        url = self.__actions['browse_episodes'].get('url').replace('#name_id', params['name_id']).replace('#season', params['season'])

        r = self.__http_request('browse_episodes', url = url)
        self.__json = r.json()

        self.__item = self.__json['serial']
        self.__items = self.__make_eposode_list()
        
        result = {'count': len(self.__items),
                  'title': self.__item['name_rus'],
                  'season': params['season'],
                  'list':  self.__make_list('episodes')}
        return result

    def __make_eposode_list( self ):
        episodes = []

        items = self.__json['episodes']['items']
        if type(items) == dict:
            for key, val in items.iteritems():
                episodes.append(val)
        elif type(items) == list:
            episodes = items
        
        return episodes
    
    def browse_seasons( self, params ):

        url = self.__actions['get_tvseries_details'].get('url').replace('#name_id', params['name_id'])

        r = self.__http_request('get_tvseries_details', url = url)
        self.__json = r.json()
        
        self.__item = self.__json['serial']
        
        result = {'count': int(self.__json['seasons']['count']),
                  'title': self.__item['name_rus'],
                  'list':  self.__make_list('seasons')}
        return result

    def get_filters( self ):
        r = self.__http_request('get_filters')
        self.__json = r.json()

        genres = []
        for key, genre in self.__json['genres'].iteritems():
            genres.append({'name': genre['name'],
                          'value': genre['translit']
                          })

        countries = []
        for country in self.__json['countries']:
            countries.append({'name': country['name'],
                              'value': country['translit']
                              })

        ratings = []
        for rating in xrange(9, 0, -1):
            ratings.append({'name': u'от %d' % rating,
                            'value': str(rating)
                            })

        r = self.__http_request('main')
        self.__json = r.json()

        current_year = self.__json['current_year']
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

        url = self.__actions['search'].get('url').replace('#keyword', urllib.quote(params['keyword']))

        u_params = {'page':    params.get('page', 1)
                    }
        
        r = self.__http_request('search', params = u_params, url = url)
        self.__json = r.json()

        self.__items = self.__json.get('items', [])

        result = {'count': len(self.__items),
                  'title': params['keyword'],
                  'total_pages': self.__json['pagination']['total_pages'],
                  'list':  self.__make_list('search')
                  }
        return result
    
    def get_movie_url( self, params ):

        movie_details = self.get_movie_details(params)
        
        video_info = movie_details['video_info']
        item_info  = movie_details['item_info']
        
        url = self.__actions['get_video_url'].get('url').replace('#id', str(video_info['mobi_link_id']))
        r = self.__http_request('get_video_url', url = url)
        self.__json = r.json()

        path = self.__get_video_url(video_info['mobi_link_id'])
       
        item_info['path'] = path
        return item_info

    def get_movie_trailer( self, params ):

        movie_details = self.get_movie_details(params)
        
        if self.__item['trailer']['url']:
            path = self.__item['trailer']['url']
        else:
            path = self.__get_video_url(self.__item['trailer']['id'])
       
        item_info = {'path': path}
        return item_info

    def get_episode_url( self, params ):

        movie_details = self.get_tvseries_details(params)
        
        video_info = movie_details['video_info']
        item_info  = movie_details['item_info']
        
        path = self.__get_video_url(video_info['mobi_link_id'])

       
        item_info['path'] = path

        return item_info

    def get_tvseries_trailer( self, params ):

        movie_details = self.get_tvseries_details(params)
        
        if self.__item['trailer']['url']:
            path = self.__item['trailer']['url']
        else:
            path = self.__get_video_url(self.__item['trailer']['id'])
        
        item_info = {'path': path}
        return item_info

    def __get_video_url( self, mobi_link_id ):
        video_quality = self.video_quality

        url = self.__actions['get_video_url'].get('url').replace('#id', str(mobi_link_id))
        r = self.__http_request('get_video_url', url = url)
        self.__json = r.json()

        path = ''
        if not path or video_quality >= 0:
            path = self.__json['lqUrl']
        if not path or video_quality >= 1:
            path = self.__json['url']
            
        return path

    def __make_list( self, source, params = {} ):

        if source in ('movies', 'tvseries', 'search'):
            for item in self.__items:
                video_info = {'type':    'tvseries' if item['serial'] else 'movies',
                              'name_id': item['name_id'],
                              }

                title = item['name_rus']
                title_orig = item.get('name_eng') if item.get('name_eng') else item['name_rus']

                item_info = {'label':  title,
                             'rating': self.__get_rating(item),
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

            item = self.__item
            
            title = item['name_rus']
            title_orig = item.get('name_eng') if item.get('name_eng') else item['name_rus']

            for episode in self.__items:
                video_info = {'type': source,
                              'name_id': item['name_id'],
                              'season': episode['season'],
                              'episode': episode['episode'],
                              'originaltitle': self.__item.get('name_eng') if self.__item.get('name_eng') else self.__item['name_rus'],
                              }
                yield self.__get_details( video_info )

        elif source == 'seasons':
            item = self.__item
            
            for season in xrange(1, self.__json['seasons']['count'] + 1):
                video_info = {'type':    source,
                              'name_id': item['name_id'],
                              'season':  season}

                yield self.__get_details( video_info )
    
    def __get_episode( self, episode, season ):
        for episode_ in self.__make_eposode_list():
            if episode_['episode'] == int(episode) \
               and episode_['season'] == int(season):
                return episode_
        return {}

    def __get_rating( self, item ):
    
        r_kinopoisk = self.__make_rating(item, 'kinopoisk')
        r_imdb = self.__make_rating(item, 'imdb')
        r_zona = self.__make_rating(item, 'zona')

        return [r_imdb, r_kinopoisk, r_zona]

    def __make_rating( self, item, type ):

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
        
    def __get_premiere_date( self ):
        item = self.__item
        
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
        
    def __get_details( self, params = {} ):

        item = self.__item

        video_info = {}
        video_info.update(params)
        
        #Defaults
        poster = item['image']
        thumb = item['image']
        fanart = self.__json['backdrops']['image_1280']
        plot = item.get('description')

        premiered = self.__get_premiere_date()
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
        for genre in self.__json['genres']:
            genres.append(genre['name'])
        
        
        persons = self.__json.get('persons', {})

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
        for country_ in self.__json.get('countries', []):
            country.append(country_['name'])

        #Date
        mobi_link_date = item['mobi_link_date']
        if mobi_link_date:
            date = ('%s.%s.%s') %(mobi_link_date[8:10], mobi_link_date[5:7], mobi_link_date[0:4])
        else:
            date = ''
        
        if item['serial']:
            tvshowtitle = item_title
            
            p_episode = params.get('episode')
            p_season = params.get('season')

            season = self.__json['seasons']['count']
            episode = self.__json['episodes']['count_all']
            
            if p_episode:
                episode_ = self.__get_episode(p_episode, p_season)
                mobi_link_id = episode_.get('mobi_link_id','')

                mediatype = 'episode'
                thumb = self.__json['images'].get(str(mobi_link_id))

                release_date = episode_.get('release_date')
                if release_date:
                    aired = release_date[0:10]
                    
                title = episode_.get('title', '')
                if type(title) == int:
                    title = str(title)
                originaltitle = title

                episode = episode_['episode']
                season = episode_['season']
                
                plot = ''
                
            elif p_season:
                mediatype = 'season'
                title = item_title
                originaltitle = item_title_orig
                duration = 0
                episodes = self.__make_eposode_list()
                if len(episodes):
                    release_date = episodes[0]['release_date']
                    if release_date:
                        aired = release_date[0:10]
            else:
                mediatype = 'tvshow'
                title = item_title
                originaltitle = item_title_orig
                rating = self.__get_rating(item)
        else:
            mediatype = 'movie'
            title = item_title
            originaltitle = item_title_orig
            rating = self.__get_rating(item)
            mobi_link_id = item.get('mobi_link_id','')
            
        item_info = {#'label':  label,
                     'cast':   cast,
                     'rating': rating,
                     'properties': properties,
                     'info': {'video': {'date': date, 
                                        'genre': genres,
                                        'country': country,
                                        'year': item.get('year'),
                                        'episode': episode,
                                        'season': season,
                                        'sortepisode': episode,
                                        'sortseason': season,
                                        'director': director,
                                        'plot': plot,
                                        'title': title,
                                        'originaltitle': originaltitle,
                                        'sorttitle': title,
                                        'duration': duration,
                                        'writer': writer,
                                        'tvshowtitle': tvshowtitle,
                                        'premiered': premiered,
                                        'aired': aired,
                                        'mediatype': mediatype,
                                        }
                              },
                     'art': {'poster': poster},
                     'fanart': fanart,
                     'thumb':  thumb,
                    }
            
        video_info.update({'have_trailer': True if item.get('trailer_url') else False,
                           'name_id':      item['name_id'],
                           'mobi_link_id': mobi_link_id})

        return {'item_info':  item_info,
                'video_info': video_info}
        