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
        self.__settings = {'episode_title': params.get('episode_title', 'Episode'),
                           'season_title':  params.get('season_title','Season'),
                           'video_quality': params.get('video_quality', 0),
                           'rating_source': params.get('rating_source', 'imdb')}

        #Инициализация
        base_url = 'https://zona.mobi'

        self.__actions = {'main':            {'type': 'get', 'url': base_url},
                          'get_filters':     {'type': 'get', 'url': base_url + '/ajax/widget/filter'},
                          'get_video_url':   {'type': 'get', 'url': 'http://android.mzona.net/api/v1/video/#id'},
                          'search':          {'type': 'get', 'url': 'https://zona.mobi/search//#keyword'},
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

    def __get_setting( self, id, default='' ):
        return self.__settings.get(id, default)

    def __set_setting( self, id, value ):
        self.__settings[id] = value

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
                  'total_pages': self.__json.get('pagination', {}).get('total_pages', 0),
                  'list':  self.__make_list('movies')}
        return result

    def get_movie_details( self, params):
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
                  'total_pages': self.__json.get('pagination', {}).get('total_pages', 0),
                  'list':  self.__make_list('movies')}
        return result

    def get_tvseries_details( self, params):

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
        video_quality = self.__get_setting('video_quality')

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
                             'info': {'video': {'year':          item.get('year'),
                                                'title':         title,
                                                'originaltitle': title_orig,
                                                'sorttitle':     title,
                                                'mediatype ':    'tvshow' if item['serial'] else 'movie'
                                                }
                                      },
                             'art': {'poster': item['cover']
                                     },
                            }

                video_info = {'item_info':  item_info,
                              'video_info': video_info
                              }
                              
                yield video_info

        elif source == 'episodes':
            season_title = self.__get_setting('season_title')
            episode_title = self.__get_setting('episode_title')

            item = self.__item
            
            title = item['name_rus']
            title_orig = item.get('name_eng') if item.get('name_eng') else item['name_rus']

            for episode in self.__items:
                video_info = {'type':    source,
                              'name_id': self.__item['name_id'],
                              'season':  episode['season'],
                              'episode': episode['episode'],
                              }

                if episode['title']:
                    title_full = '%02d. %s' % (int(episode['episode']), episode['title'])
                    title_orig_full = '%02d. %s' % (int(episode['episode']), episode['title'])
                else:
                    title_part = '%s %s %s %s' % (season_title, episode['season'], episode_title, episode['episode'])
                    title_full = '%s. %s' % (title, title_part)
                    title_orig_full = '%s. %s' % (title_orig, title_part)

                if type(self.__json['images']) == list:
                    thumb = ''
                else:
                    thumb = self.__json['images'].get(str(episode['mobi_link_id']),'')
                    
                item_info = {'label': title_full,
                             'info':  { 'video': {'title':         title_full,
                                                  'originaltitle': title_orig_full,
                                                  'tvshowtitle':   title_orig,
                                                  'sorttitle':     title_full,
                                                  'season':        int(episode['season']),
                                                  'episode':       int(episode['episode']),
                                                  'mediatype ':    'episode'} },
                             'art': {'poster': thumb,
                                     },
                             'fanart': self.__json['backdrops']['image_1280'],
                             'thumb':  thumb}

                video_info = {'item_info':  item_info,
                              'video_info': video_info}
                yield video_info

        elif source == 'seasons':
            season_title = self.__get_setting('season_title')
            item = self.__item
            
            title = item['name_rus']
            title_orig = item.get('name_eng') if item.get('name_eng') else item['name_rus']

            for season in xrange(1, self.__json['seasons']['count']+1):
                video_info = {'type':       source,
                              'id':      self.__item['id'],
                              'name_id': self.__item['name_id'],
                              'season':     str(season)}

                title_part = '%s %s' % (season_title, season)
                title_full = '%s. %s' % (title_part, title)
                title_orig_full = '%s. %s' % (title_part, title_orig)
                item_info = {'label':  title_full,
                             'info':  {'video': {'title':         title_full,
                                                 'originaltitle': title_orig_full,
                                                 'tvshowtitle':   title,
                                                 'sorttitle':     title,
                                                 'season':        int(season),
                                                 'plot':          item['description'],
                                                 'mediatype ':    'season'
                                                 }
                                       },
                              'art': {'poster': item['image']
                                      },
                             'fanart': self.__json['backdrops']['image_1280'],
                             'thumb':  self.__json['backdrops']['image_1280']
                             }

                video_info = {'item_info':  item_info,
                              'video_info': video_info}
                yield video_info
    
    def __get_episode( self, episode_num ):
        for episode in self.__make_eposode_list():
            if episode['episode'] == int(episode_num):
                return episode
                
    def __get_details( self, params = {} ):
        rating_source = self.__get_setting('rating_source')
        if rating_source:
            rating_field = 'rating_' + rating_source
        else:
            rating_field = 'rating'

        item = self.__item

        title = item['name_rus']
        title_orig = item.get('name_original') if item.get('name_original') else item['name_rus']
        if item['runtime']:
            duration = item['runtime']['value'] * 60
        else:
            duration = 0

        have_trailer = True if item.get('trailer_url') else False

        video_info = {'have_trailer': have_trailer,
                      'name_id':      item['name_id'],
                      'mobi_link_id': item.get('mobi_link_id','')}

        episode_num = params.get('episode')

        genres = []
        for genre in self.__json['genres']:
            genres.append(genre['name'])
        genre = ', '.join(genres)
                
        cast_names = []
        cast_full = []
        for actor in self.__json['persons'].get('actors', []):
            cast_names.append(actor['name'])
            cast_full.append({'name': actor['name'],
                         'thumbnail': actor['cover']})

        director = []
        for dir in self.__json['persons'].get('director', []):
            # director.append(dir['name'])
            director = dir['name']
            break

        writer = []
        for scenarist in self.__json['persons'].get('scenarist', []):
            writer.append(scenarist['name'])
        writer = ', '.join(writer)
        
        if episode_num:
            season_title = self.__get_setting('season_title')
            episode_title = self.__get_setting('episode_title')

            
            episode = self.__get_episode(episode_num)
            if episode['title']:
                title_full = '%02d. %s' % (int(episode['episode']), episode['title'])
                title_orig_full = '%02d. %s' % (int(episode['episode']), episode['title'])
            else:
                title_part = '%s %s %s %s' % (season_title, episode['season'], episode_title, episode['episode'])
                title_full = '%s. %s' % (title, title_part)
                title_orig_full = '%s. %s' % (title_orig, title_part)

            release_date = episode['release_date']
            if release_date:
                date = ('%s.%s.%s') %(release_date[8:10],release_date[5:7],release_date[0:4])
                premiered = release_date[0:10]
            else:
                date = ''
                premiered = ''
            
            thumb = self.__json['images'].get(str(episode['mobi_link_id']),'')
            item_info = {'label': title_full,
                         'date': date, 
                         'cast': cast_full,
                         'info':  { 'video': {'title':         title_full,
                                              'genre':         genre,
                                              'originaltitle': title_orig_full,
                                              'tvshowtitle':   title_orig,
                                              'sorttitle':     title,
                                              'director': director,
                                              'writer': writer,
                                              'cast': cast_names,
                                              'season':        int(episode['season']),
                                              'episode':       int(episode['episode']),
                                              'premiered':     premiered,
                                              'mediatype ':    'episode'} },
                         'art': {'poster': thumb,
                                 },
                         'fanart': self.__json['backdrops']['image_1280'],
                         'thumb':  thumb}
            video_info['mobi_link_id'] = episode['mobi_link_id']
        else:
            title = item['name_rus']
            title_orig = item.get('name_original') if item.get('name_original') else item['name_rus']

            if item[rating_field]:
                rating = float(item[rating_field])
            else:
                rating = 0

            if item['serial']:
                if item.get('episodes'):
                    duration = duration * item['episodes']['count_all'] 
                else:
                    duration = 0
            
            item_info = {'label':  title,
                         'cast':     cast_full,
                         'info': {'video': {'year':          item.get('year'),
                                            'title':         title,
                                            'originaltitle': title_orig,
                                            'sorttitle':     title,
                                            'rating':   rating,
                                            'genre':         genre,
                                            # 'cast':     cast_names,
                                            'director': director,
                                            'writer': writer,
                                            # 'genre':    movie['genres'], #.split(', ') if movie['genres'] else [],
                                            # 'cast':     movie['actors'].split(', ') if movie['actors'] else [],
                                            'country':  item['country'], #.split(', ') if movie['country'] else [],
                                            # 'director': movie['director'],
                                            # 'writer':   movie['script'],
                                            # 'tagline':  movie['slogan'],
                                            'duration': duration,
                                            'plot':     item['description'],
                                            # 'mpaa':     self.__get_mpaa(movie['age_restriction'])
                                            'mediatype ':    'tvshow' if item['serial'] else 'movie',
                                            }
                                  },
                         'art': {'poster': item['image']
                                 },
                        }

        video_info = {'item_info':  item_info,
                      'video_info': video_info}
        return video_info