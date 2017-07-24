# -*- coding: utf-8 -*-
# Module: default
# License: GPL v.3 https://www.gnu.org/copyleft/gpl.html

import resources.lib.apizonamobi as apizonamobi
import xbmcgui
from simpleplugin import Plugin
import xbmc

# Create plugin instance
plugin = Plugin()
_ = plugin.initialize_gettext()

def init_api():
    settings_list = ['video_quality', 'rating_source']

    settings = {}
    for id in settings_list:
        if id == 'rating_source':
            rating_source = plugin.movie_rating
            if rating_source == 0: settings[id] = ''
            elif rating_source == 1: settings[id] = 'imdb'
            elif rating_source == 2: settings[id] = 'kinopoisk'
        else:
            settings[id] = plugin.get_setting(id)

    settings['episode_title'] = _('Episode').decode('utf-8')
    settings['season_title']  = _('Season').decode('utf-8')

    return apizonamobi.zonamobi(settings)

def show_api_error(err):
    text = ''
    if err.code == 1:
        text = _('Connection error')
    else:
        text = str(err)
    xbmcgui.Dialog().notification(plugin.addon.getAddonInfo('name'), text, xbmcgui.NOTIFICATION_ERROR)

def show_notification(text):
    xbmcgui.Dialog().notification(plugin.addon.getAddonInfo('name'), text)

def get_request_params( params ):
    result = {}
    for param in params:
        if param[0] == '_':
            result[param[1:]] = params[param]
    return result

@plugin.action()
def root( params ):
    listing = list_root()
    return plugin.create_listing(listing, content='files')

def list_root():
    items = [{'action': 'list_videos',    'label': _('Movies'),    'params': {'cat': 'movies'}},
             {'action': 'list_videos',    'label': _('TV Series'), 'params': {'cat': 'tvseries'}},
             {'action': 'search_history', 'label': _('Search')}]

    for item in items:
        params = item.get('params',{})
        url = plugin.get_url(action=item['action'], **params)

        list_item = {'label':  item['label'],
                     'url':    url,
                     'icon':   plugin.icon,
                     'fanart': plugin.fanart}
        yield list_item

@plugin.action()
def list_videos( params ):
    cur_cat  = params['cat']
    cur_page = int(params.get('_page', '1'))
    content  = get_category_content(cur_cat)

    update_listing = (params.get('update_listing')=='True')
    if update_listing:
        del params['update_listing']
    else:
        update_listing = (int(params.get('_page','1')) > 1)

    dir_params = {}
    dir_params.update(params)
    del dir_params['action']
    if cur_page > 1:
        del dir_params['_page']

    u_params = get_request_params(params)

    try:
        video_list = get_video_list(cur_cat, u_params)
        succeeded = True
    except apizonamobi.ZonaMobiApiError as err:
        show_api_error(err)
        succeeded = False

    if cur_cat in ['videos', 'movies', 'tvseries']:
        category = '%s %d' % (_('Page'), cur_page)
    else:
        category = video_list.get('title')

    if succeeded and cur_cat == 'seasons' and video_list['count'] == 1:
        listing = []
        dir_params['cat'] = 'episodes'
        url = plugin.get_url(action='list_videos', _season = 1, **dir_params)
        xbmc.executebuiltin('Container.Update("%s")' % url)
        return

    if succeeded:
        listing = make_video_list(video_list, params, dir_params)
    else:
        listing = []

    if cur_cat == 'episodes':
        sort_methods=[27]
    else:
        sort_methods=[0]
    return plugin.create_listing(listing, content=content, succeeded=succeeded, update_listing=update_listing, category=category, sort_methods=sort_methods)

def get_category_content( cat ):
    if cat == 'tvseries':
        content = 'tvshows'
    elif cat == 'seasons':
        content = 'tvshows'
    elif cat == 'episodes':
        content = 'episodes'
    elif cat in ['movies', 'movie_related']:
        content = 'movies'
    else:
        content = 'files'
        
    return content

def get_video_list(cat, u_params):
    if cat == 'movies':
        video_list = _api.browse_movies(u_params)
    elif cat == 'tvseries':
        video_list = _api.browse_tvseries(u_params)
    elif cat == 'seasons':
        video_list = _api.browse_seasons(u_params)
    elif cat == 'episodes':
        video_list = _api.browse_episodes(u_params)
    elif cat == 'search':
        video_list = _api.search(u_params)

    return video_list

def make_video_list( video_list, params={}, dir_params = {}, search=False ):
    cur_cat  = params.get('cat', '')
    keyword  = params.get('_keyword', '')
    cur_page = int(params.get('_page', '1'))

    count = video_list['count']
    total_pages = video_list.get('total_pages', 0)

    use_pages    = not search and not keyword and total_pages
    use_search   = False #not search and (cur_cat in ['movies', 'tvseries', 'videos'])
    use_category = False #not search and (cur_cat in ['movies', 'videos'])
    use_genre    = False #not search and (cur_cat in ['movies'])
    use_lang     = False #not search and (cur_cat in ['movies'])

    if use_search:

        url = plugin.get_url(action='search_category', **dir_params)
        label = make_category_label('yellowgreen', _('Search'), keyword)
        list_item = {'label': label,
                     'is_folder':   False,
                     'is_playable': False,
                     'url':    url,
                     'icon':   plugin.icon,
                     'fanart': plugin.fanart}
        yield list_item

    if use_category:

        list = get_category(cur_cat)

        cur_category = params.get('_category','0')

        url = plugin.get_url(action='select_category', **dir_params)
        label = make_category_label('blue', _('Categories'), get_category_name(list, cur_category))
        list_item = {'label': label,
                     'is_folder':   False,
                     'is_playable': False,
                     'url':    url,
                     'icon':   plugin.icon,
                     'fanart': plugin.fanart}
        yield list_item

    if use_genre:

        list = get_genre(cur_cat)

        cur_genre = params.get('_genre','0')

        url = plugin.get_url(action='select_genre', **dir_params)
        label = make_category_label('blue', _('Genres'), get_category_name(list, cur_genre))
        list_item = {'label': label,
                     'is_folder':   False,
                     'is_playable': False,
                     'url':    url,
                     'icon':   plugin.icon,
                     'fanart': plugin.fanart}
        yield list_item

    if use_lang:

        list = get_lang()

        cur_lang = params.get('_lang')

        url = plugin.get_url(action='select_lang', **dir_params)
        label = make_category_label('blue', _('Language'), get_lang_name(list, cur_lang))
        list_item = {'label': label,
                     'is_folder':   False,
                     'is_playable': False,
                     'url':    url,
                     'icon':   plugin.icon,
                     'fanart': plugin.fanart}
        yield list_item
 
    for video_item in video_list['list']:
        yield make_item(video_item, search)

    if use_pages:
        if cur_page > 1:
            if cur_page == 2:
                del params['_page']
            else:
                params['_page'] = cur_page - 1
            url = plugin.get_url(**params)
            item_info = {'label': _('Previous page...'),
                         'url':   url}
            yield item_info

        if cur_page < total_pages:
            params['_page'] = cur_page + 1
            url = plugin.get_url(**params)
            item_info = {'label': _('Next page...'),
                         'url':   url}
            yield item_info

def make_item( video_item, search ):
        item_info = video_item['item_info']

        video_info = video_item['video_info']
        video_type = video_info['type']

        use_atl_names = plugin.use_atl_names
        movie_details = plugin.load_details
        
        if video_type == 'movies':
            is_playable = True
            url = plugin.get_url(action='play', _type = video_type, _name_id = video_info['name_id'])

            label_list = []
            if search:
                label_list.append('[%s] ' % _('Movies').decode('utf-8'))
            
            if use_atl_names:
                title = item_info['info']['video']['originaltitle']
            else:
                title = item_info['info']['video']['title']
            if type(title) == int:
                title = str(title)
            label_list.append(title)
            # if item_info['info']['video']['year'] > 0:
                # label_list.append(' (%d)' % item_info['info']['video']['year'])

            if movie_details:
                movie_details = get_movie_details(video_info)
                item_info = movie_details['item_info']
                if movie_details['video_info'].get('have_trailer'):
                    trailer_url = plugin.get_url(action='trailer', _type = video_type, _name_id = video_info['name_id'])
                    item_info['info']['video']['trailer'] = trailer_url

            item_info['label'] = ''.join(label_list)

            del item_info['info']['video']['title']

        elif video_type == 'tvseries':
            is_playable = False
            url = plugin.get_url(action='list_videos', cat = 'seasons', _name_id = video_info['name_id'])

            if movie_details:
                tvseries_details = get_tvseries_details(video_info)
                item_info = tvseries_details['item_info']
                if tvseries_details['video_info'].get('have_trailer'):
                    trailer_url = plugin.get_url(action='trailer', _type = video_type, _name_id = video_info['name_id'])
                    item_info['info']['video']['trailer'] = trailer_url

            if search:
                label_list = []
                label_list.append('[%s] ' % _('TV Series').decode('utf-8'))
                label_list.append(item_info['info']['video']['title'])
                item_info['label'] = ''.join(label_list)

                del item_info['info']['video']['title']

        elif video_type == 'seasons':
            is_playable = False
            url = plugin.get_url(action='list_videos', cat = 'episodes', _name_id = video_info['name_id'], _season = video_info['season'])

        elif video_type == 'episodes':
            is_playable = True
            url = plugin.get_url(action='play', _type = 'episodes', _name_id = video_info['name_id'], _season = video_info['season'], _episode = video_info['episode'])

            if use_atl_names:
                label_list = []
                label_list.append(item_info['info']['video']['tvshowtitle'])
                label_list.append('.s%02de%02d' % (item_info['info']['video']['season'], item_info['info']['video']['episode']))
                item_info['label'] = ''.join(label_list)

                del item_info['info']['video']['title']
            
        item_info['url'] = url
        item_info['is_playable'] = is_playable

        return item_info

def make_category_label( color, title, category ):
    label_parts = []
    label_parts.append('[COLOR=%s][B]' % color)
    label_parts.append(title)
    label_parts.append(':[/B] ')
    label_parts.append(category)
    label_parts.append('[/COLOR]')
    return ''.join(label_parts)

@plugin.cached(180)
def get_movie_details( params ):
    return _api.get_movie_details(params)

@plugin.cached(180)
def get_tvseries_details( params ):
    return _api.get_tvseries_details(params)

@plugin.cached(180)
def get_category( cat ):
    list = []
    # if cat == 'movies':
        # list = _api.category_movie()
    # elif cat == 'videos':
        # list = _api.category_video()
    return list

@plugin.cached(180)
def get_genre( cat ):
    list = []
    # if cat == 'movies':
        # list = _api.category_genre()
    return list

@plugin.cached(180)
def get_lang():
    list = []
    list.append({'id': 'az', 'title': _('Azərbaycanca')})
    list.append({'id': 'ru', 'title': _('Русский')})
    list.append({'id': 'en', 'title': _('English')})
    list.append({'id': 'tr', 'title': _('Türkçe')})

    return list

def get_category_name( list, id ):
    for item in list:
        if item['id'] == id:
            return item['title'].encode('utf-8')
    return _('All')

def get_lang_name( list, id ):
    for item in list:
        if item['id'] == id:
            return item['title']
    return _('All')

@plugin.action()
def search( params ):

    keyword  = params.get('keyword', '')
    usearch  = (params.get('usearch') == 'True')

    new_search = (keyword == '')
    succeeded = False

    if not keyword:
        kbd = xbmc.Keyboard()
        kbd.setDefault('')
        kbd.setHeading(_('Search'))
        kbd.doModal()
        if kbd.isConfirmed():
            keyword = kbd.getText()

    if keyword and new_search and not usearch:
        with plugin.get_storage('__history__.pcl') as storage:
            history = storage.get('history', [])
            history.insert(0, {'keyword': keyword.decode('utf-8')})
            if len(history) > plugin.history_length:
                history.pop(-1)
            storage['history'] = history

        params['keyword'] = keyword
        url = plugin.get_url(**params)
        xbmc.executebuiltin('Container.Update("%s")' % url)
        return

    if keyword:
        succeeded = True
        u_params = {'keyword': keyword}

        try:
            search_list = get_video_list('search', u_params)
        except apizonamobi.ZonaMobiApiError as err:
            show_api_error(err)
            succeeded = False


        if succeeded and search_list['count'] == 0:
            succeeded = False
            if not usearch:
                show_notification(_('Nothing found!'))

    if succeeded:
        listing = make_video_list(search_list, search=True)
    else:
        listing = []

    return plugin.create_listing(listing, succeeded = succeeded, content='movies', category=keyword, sort_methods=[27])

@plugin.action()
def search_category( params ):

    category = params.get('cat')
    keyword = params.get('_keyword', '')

    kbd = xbmc.Keyboard()
    kbd.setDefault(keyword)
    kbd.setHeading(_('Search'))
    kbd.doModal()
    if kbd.isConfirmed():
        keyword = kbd.getText()

    params['_keyword'] = keyword
    del params['action']
    url = plugin.get_url(action='list_videos', update_listing=True, **params)
    xbmc.executebuiltin('Container.Update("%s")' % url)

@plugin.action()
def search_history():

    with plugin.get_storage('__history__.pcl') as storage:
        history = storage.get('history', [])

        if len(history) > plugin.history_length:
            history[plugin.history_length - len(history):] = []
            storage['history'] = history

    listing = []
    listing.append({'label': _('New Search...'),
                    'url': plugin.get_url(action='search')})

    for item in history:
        listing.append({'label': item['keyword'],
                        'url': plugin.get_url(action='search', keyword=item['keyword'].encode('utf-8'))})

    return plugin.create_listing(listing, content='movies')

@plugin.action()
def play( params ):

    u_params = get_request_params( params )
    try:
        if u_params['type'] == 'movies':
            item = _api.get_movie_url( u_params )
            succeeded = True
        elif u_params['type'] == 'episodes':
            item = _api.get_episode_url( u_params )
            succeeded = True
        else:
            succeeded = False
    except apizonamobi.ZonaMobiApiError as err:
        show_api_error(err)
        item = None
        succeeded = False

    return plugin.resolve_url(play_item=item, succeeded=succeeded)

@plugin.action()
def trailer( params ):

    u_params = get_request_params( params )
    try:
        if u_params['type'] == 'movies':
            item = _api.get_movie_trailer( u_params )
            succeeded = True
        elif u_params['type'] == 'tvseries':
            item = _api.get_tvseries_trailer( u_params )
            succeeded = True
        else:
            succeeded = False
    except apizonamobi.ZonaMobiApiError as err:
        show_api_error(err)
        item = None
        succeeded = False

    return plugin.resolve_url(play_item=item, succeeded=succeeded)

@plugin.action()
def select_category( params ):
    list = get_category( params['cat'])
    list.insert(0, {'id': '0', 'title': _('All')})
    titles = []
    for list_item in list:
        titles.append(list_item['title'])
    ret = xbmcgui.Dialog().select(_('Categories'), titles)
    if ret >= 0:
        category = list[ret]['id']
        if category == '0' and params.get('_category'):
            del params['_category']
        else:
            params['_category'] = category
        del params['action']
        url = plugin.get_url(action='list_videos', update_listing=True, **params)
        xbmc.executebuiltin('Container.Update("%s")' % url)

@plugin.action()
def select_genre( params ):
    list = get_genre( params['cat'])
    list.insert(0, {'id': '0', 'title': _('All')})
    titles = []
    for list_item in list:
        titles.append(list_item['title'])
    ret = xbmcgui.Dialog().select(_('Genres'), titles)
    if ret >= 0:
        genre = list[ret]['id']
        if genre == '0' and params.get('_genre'):
            del params['_genre']
        else:
            params['_genre'] = genre
        del params['action']
        url = plugin.get_url(action='list_videos', update_listing=True, **params)
        xbmc.executebuiltin('Container.Update("%s")' % url)

@plugin.action()
def select_lang( params ):
    list = get_lang()
    list.insert(0, {'id': '0', 'title': _('All')})
    titles = []
    for list_item in list:
        titles.append(list_item['title'])
    ret = xbmcgui.Dialog().select(_('Language'), titles)
    if ret >= 0:
        lang = list[ret]['id']
        if lang == '0' and params.get('_lang'):
            del params['_lang']
        else:
            params['_lang'] = lang
        del params['action']
        url = plugin.get_url(action='list_videos', update_listing=True, **params)
        xbmc.executebuiltin('Container.Update("%s")' % url)

if __name__ == '__main__':
    _api = init_api()
    plugin.run()