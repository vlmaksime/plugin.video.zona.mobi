# -*- coding: utf-8 -*-
# Module: default
# License: GPL v.3 https://www.gnu.org/copyleft/gpl.html

import xbmc
import xbmcgui

from simpleplugin import Plugin

import resources.lib.apizonamobi as apizonamobi

# Create plugin instance
plugin = Plugin()
_ = plugin.initialize_gettext()

def init_api():
    settings_list = ['video_quality']

    settings = {}
    for id in settings_list:
        settings[id] = plugin.get_setting(id)

    return apizonamobi.zonamobi(settings)

def _get_rating_source():
    rating_source = plugin.movie_rating
    if rating_source == 0: source = 'zona'
    elif rating_source == 1: source = 'imdb'
    elif rating_source == 2: source = 'kinopoisk'
    return source

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
    return plugin.create_listing(_list_root(), content='files')

def _list_root():
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
        update_listing = (cur_page > 1)

    dir_params = {}
    dir_params.update(params)
    del dir_params['action']
    if cur_page > 1:
        del dir_params['_page']

    try:
        video_list = get_video_list(cur_cat, get_request_params(params))
        succeeded = True
    except apizonamobi.ZonaMobiApiError as err:
        show_api_error(err)
        succeeded = False

    category_title = []
    if cur_cat in ['movies', 'tvseries', 'search']:
        category_title.append('%s %d' % (_('Page'), cur_page))
    category_title.append(video_list.get('title'))
    if cur_cat == 'episodes':
        category_title.append('%s %s' % (_('Season').decode('utf-8'), video_list['season']))
    category = ' / '.join(category_title)

    if succeeded \
      and cur_cat == 'seasons' \
      and video_list['count'] == 1:
        dir_params['cat'] = 'episodes'
        url = plugin.get_url(action='list_videos', _season = 1, **dir_params)
        xbmc.executebuiltin('Container.Update("%s")' % url)
        return

    if succeeded:
        listing = make_video_list(video_list, params, dir_params)
    else:
        listing = []

    sort_methods = _get_sort_methods(cur_cat)

    return plugin.create_listing(listing, content=content, succeeded=succeeded, update_listing=update_listing, category=category, sort_methods=sort_methods)

def _get_sort_methods( cat ):
    major_version = xbmc.getInfoLabel('System.BuildVersion')[:2]
    if cat == 'episodes' \
      and major_version >= '16':
      if plugin.use_atl_names:
        sort_methods=[1]
      else:
        sort_methods=[24]
    elif cat == 'seasons':
        sort_methods=[1]
    else:
        sort_methods=[0]

def get_category_content( cat ):
    if cat  == 'tvseries':
        content = 'tvshows'
    elif cat == 'seasons':
        content = 'seasons'
    elif cat == 'episodes':
        content = 'episodes'
    elif cat in ['movies', 'search']:
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

def make_video_list( video_list, params={}, dir_params = {} ):
    cur_cat  = params.get('cat', '')
    keyword  = params.get('_keyword', '')
    cur_page = int(params.get('_page', '1'))

    count = video_list['count']
    total_pages = video_list.get('total_pages', 0)

    search = (cur_cat == 'search')
    usearch  = (params.get('usearch') == 'True')

    use_filters  = not search and (cur_cat in ['movies', 'tvseries'])
    use_pages    = not usearch and total_pages

    if use_filters:
        filters = get_filters()
        yield _make_filter_item('sort', params, dir_params, filters)
        if params.get('_sort') != 'updates':
            yield _make_filter_item('genre', params, dir_params, filters)
            yield _make_filter_item('year', params, dir_params, filters)
            yield _make_filter_item('country', params, dir_params, filters)
            yield _make_filter_item('rating', params, dir_params, filters)

    if video_list['count']:
        for video_item in video_list['list']:
            yield _make_item(video_item, search)

    elif not usearch:
        item_info = {'label': make_colour_label('red', '[%s]' % _('Empty')),
                     'is_folder':   False,
                     'is_playable': False,
                     'url':   ''}
        yield item_info

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

def _make_filter_item( filter, params, dir_params, filters ):
    cur_value = params.get('_%s' % filter,'')

    filter_title = _get_filter_title(filter)
    url = plugin.get_url(action='select_filer', filter = filter, **dir_params)
    label = make_category_label('yellowgreen', filter_title, get_filter_name(filters[filter], cur_value))
    list_item = {'label': label,
                 'is_folder':   False,
                 'is_playable': False,
                 'url':    url,
                 'icon':   plugin.icon,
                 'fanart': plugin.fanart}

    return list_item

def _get_filter_title( filter ):
    result = ''
    if filter == 'genre': result = _('Genre')
    elif filter =='year': result = _('Year')
    elif filter =='country': result = _('Country')
    elif filter =='rating': result = _('Rating')
    elif filter =='sort': result = _('Sort')

    return result

def _make_item( video_item, search ):
        label_list = []

        video_type = video_item['video_info']['type']
        use_atl_names = plugin.use_atl_names

        if plugin.load_details \
          and video_type in ['movies', 'tvseries','seasons']:
            video_details = get_video_details(video_item['video_info'])
            item_info = video_details['item_info']
            video_info = video_details['video_info']
        else:
            item_info = video_item['item_info']
            video_info = video_item['video_info']

        if item_info.get('rating'):
            rating_source = _get_rating_source()
            for rating in item_info['rating']:
                if rating['type'] == rating_source:
                    rating['defaultt'] = True

        if video_type == 'movies':
            is_playable = True
            url = plugin.get_url(action='play', _type = video_type, _name_id = video_info['name_id'])

            if search:
                label_list.append('[%s] ' % _('Movies').decode('utf-8'))

            if use_atl_names:
                title = item_info['info']['video']['originaltitle']
            else:
                title = item_info['info']['video']['title']

            label_list.append(title)

            if use_atl_names \
              and item_info['info']['video']['year'] > 0:
                label_list.append(' (%d)' % item_info['info']['video']['year'])

            if use_atl_names or search:
                del item_info['info']['video']['title']

            if video_info.get('have_trailer'):
                trailer_url = plugin.get_url(action='trailer', _type = video_type, _name_id = video_info['name_id'])
                item_info['info']['video']['trailer'] = trailer_url

        elif video_type == 'tvseries':
            is_playable = False
            url = plugin.get_url(action='list_videos', cat = 'seasons', _name_id = video_info['name_id'])

            if video_info.get('have_trailer'):
                trailer_url = plugin.get_url(action='trailer', _type = video_type, _name_id = video_info['name_id'])
                item_info['info']['video']['trailer'] = trailer_url

            if search:
                label_list.append('[%s] ' % _('TV Series').decode('utf-8'))

            if use_atl_names:
                title = item_info['info']['video']['originaltitle']
            else:
                title = item_info['info']['video']['title']
            label_list.append(title)

            if use_atl_names \
              and item_info['info']['video']['year'] > 0:
                label_list.append(' (%d)' % item_info['info']['video']['year'])

        elif video_type == 'seasons':
            is_playable = False
            url = plugin.get_url(action='list_videos', cat = 'episodes', _name_id = video_info['name_id'], _season = video_info['season'])

            label_list.append('%s %d' % (_('Season').decode('utf-8'), video_info['season']))

        elif video_type == 'episodes':
            is_playable = True
            url = plugin.get_url(action='play', _type = 'episodes', _name_id = video_info['name_id'], _season = video_info['season'], _episode = video_info['episode'])

            if use_atl_names:
                label_list.append(video_info['originaltitle'])
                label_list.append('.s%02de%02d' % (video_info['season'], video_info['episode']))
                if item_info['info']['video']['title']:
                    label_list.append('.%s' % (item_info['info']['video']['title']))
            else:
                if not item_info['info']['video']['title']:
                    item_info['info']['video']['title'] = '%s %d' % (_('Episode').decode('utf-8'), video_info['episode'])
                label_list.append(item_info['info']['video']['title'])

            if use_atl_names:
                del item_info['info']['video']['title']

        item_info['label'] = ''.join(label_list)
        item_info['url'] = url
        item_info['is_playable'] = is_playable
        
        _backward_capatibility( item_info )

        return item_info

def _backward_capatibility( item_info ):
    major_version = xbmc.getInfoLabel('System.BuildVersion')[:2]
    if major_version < '18':
        for rating in item_info.get('rating'):
            if rating['defaultt']:
                if rating['rating']:
                    item_info['info']['video']['rating'] = rating['rating']
                if rating['votes']:
                    item_info['info']['video']['votes'] = rating['votes']
                break
        for fields in ['genre', 'writer', 'director', 'country', 'credits']:
            item_info['info']['video'][fields] = ' / '.join(item_info['info']['video'].get(fields,[]))

    if major_version < '17':
        cast = []
        castandrole = []
        for cast_ in item_info.get('cast',[]):
            cast.append(cast_['name'])
            castandrole.append((cast_['name'], cast_.get('role')))
        item_info['info']['video']['cast'] = cast
        item_info['info']['video']['castandrole'] = castandrole

    if major_version < '15':
        item_info['info']['video']['duration'] = (item_info['info']['video']['duration'] / 60)
        
def make_category_label( color, title, category ):
    label_parts = []
    label_parts.append('[COLOR=%s][B]' % color)
    label_parts.append(title)
    label_parts.append(':[/B] ')
    label_parts.append(category)
    label_parts.append('[/COLOR]')
    return ''.join(label_parts)

def make_colour_label( color, title ):
    label_parts = []
    label_parts.append('[COLOR=%s][B]' % color)
    label_parts.append(title)
    label_parts.append('[/B][/COLOR]')
    return ''.join(label_parts)

@plugin.cached(180)
def get_video_details( params ):
    if params['type'] == 'movies':
        return _api.get_movie_details(params)
    if params['type'] in ['seasons', 'tvseries']:
        return _api.get_tvseries_details(params)

@plugin.cached(180)
def get_filters():
    return _api.get_filters()

def get_filter_name( list, value ):
    for item in list:
        if item['value'] == value:
            return item['name'].encode('utf-8')
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
        params['action'] = 'list_videos'
        params['cat'] = 'search'
        params['_keyword'] = keyword
        return list_videos(params)

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
def select_filer( params ):
    filter = params['filter']
    filter_name = filter
    filter_title = _get_filter_title(filter)
    filter_key = '_%s' % filter

    list = get_filters()[filter]
    if filter != 'sort':
        list.insert(0, {'value': '', 'name': _('All')})

    titles = []
    for list_item in list:
        titles.append(list_item['name'])

    ret = xbmcgui.Dialog().select(filter_title, titles)
    if ret >= 0:
        filter_value = list[ret]['value']
        if not filter_value and params.get(filter_key):
            del params[filter_key]
        else:
            params[filter_key] = filter_value

        del params['action']
        del params['filter']

        remove_param(params, '_page')

        if filter_name == 'sort' and filter_value == 'updates':
            remove_param(params, '_genre')
            remove_param(params, '_year')
            remove_param(params, '_country')
            remove_param(params, '_rating')

        url = plugin.get_url(action='list_videos', update_listing=True, **params)
        xbmc.executebuiltin('Container.Update("%s")' % url)

def remove_param(params, name):
    if params.get(name):
        del params[name]

if __name__ == '__main__':
    _api = init_api()
    plugin.run()