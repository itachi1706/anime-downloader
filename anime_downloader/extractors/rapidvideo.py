import logging
import re
from bs4 import BeautifulSoup

from anime_downloader.extractors.base_extractor import BaseExtractor
from anime_downloader import session

session = session.get_session()


class RapidVideo(BaseExtractor):
    def _get_data(self):
        url = self.url + '&q=' + self.quality
        logging.debug('Calling Rapid url: {}'.format(url))
        headers = self.headers
        headers['referer'] = url
        try:
            r = session.get(url, headers=headers)
            # This is a fix for new rapidvideo logic
            # It will return OK for a get request
            # even if there is a click button
            # This will make sure a source link is present
            soup = BeautifulSoup(r.text, 'html.parser')
            get_source(soup, self.quality)
        except:
            r = session.post(url, {
                'confirm.x': 12,
                'confirm.y': 12,
                'block': 1,
            }, headers=headers)
        soup = BeautifulSoup(r.text, 'html.parser')

        # TODO: Make these a different function. Can be reused in other classes
        #       too
        title_re = re.compile(r'"og:title" content="(.*)"')
        image_re = re.compile(r'"og:image" content="(.*)"')

        try:
            stream_url = get_source(soup, self.quality)
        except IndexError:
            stream_url = None

        try:
            title = str(title_re.findall(r.text)[0])
            thumbnail = str(image_re.findall(r.text)[0])
        except Exception as e:
            title = ''
            thumbnail = ''
            logging.debug(e)
            pass

        return {
            'stream_url': stream_url,
            'meta': {
                'title': title,
                'thumbnail': thumbnail,
            },
        }


def get_source(soup, quality):
    src_re = re.compile(r'src: "(.*)"')
    try:
        # Try and get based on quality as well
        source_map = {}
        for s in soup.find_all('source'):
            source_map[int(s.get('data-res'))] = s.get('src')
        if source_map:
            return further_source_processing(source_map, quality)
        else:
            return soup.find_all('source')[0].get('src')
    except IndexError:
        return str(src_re.findall(str(soup))[0])


def further_source_processing(source_map, ideal_resolution):
    try:
        ideal_resolution = int(ideal_resolution.replace("p", "").replace("P", ""))
        logging.debug("[RapidVideo] Mapped Sources: {}".format(source_map))
        if ideal_resolution in source_map:
            logging.info("[RapidVideo] Found Video at {}p resolution".format(ideal_resolution))
            logging.debug("[RapidVideo] Returning URL {}".format(source_map[ideal_resolution]))
            return source_map[ideal_resolution]
        res_divide = {1080: 360, 720: 240, 480: 120}
        logging.info("[RapidVideo] Ideal Resolution ({}p) not found. Attempting downgrade".format(ideal_resolution))

        # Try and downgrade
        res = ideal_resolution
        while res in res_divide:
            res -= res_divide[res]
            logging.debug("[RapidVideo] Attempting to download video at {}p".format(res))
            if res in source_map:
                logging.info("[RapidVideo] Found Video at {}p resolution".format(ideal_resolution))
                logging.debug("[RapidVideo] Returning URL {}".format(source_map[ideal_resolution]))
                return source_map[res]
            logging.debug("[RapidVideo] Cannot find in {}p resolution".format(res))
        logging.info("[RapidVideo] Unable to find resolutions. Falling back to legacy implementation")
        return list(source_map.items())[0]  # Correct Implementation
    except ValueError:
        return list(source_map.items())[0]  # Former implementation
