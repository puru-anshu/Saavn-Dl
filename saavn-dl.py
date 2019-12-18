#!/usr/bin/python
import requests, re, sys, os
import argparse
from bs4 import BeautifulSoup
from terminaltables import AsciiTable
from mutagen.mp4 import MP4
from mutagen.mp4 import MP4Cover
import urllib2 as urllib
from mutagen.mp3 import  EasyMP3
from mutagen.mp3 import  MP3
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3, APIC, error
from pyDes import *


class BadHTTPCodeError(Exception):
    def __init__(self, code):
        print(code)

class SaavnDownloader():


    def __init__(self):
        self.urls = {
            'search_songs_new' : 'http://www.saavn.com/api.php?__call=search.getResults&p=1&n=10&_format=json&_marker=0&q={query}',
            'search_albums_new' : 'http://www.saavn.com/api.php?__call=search.getAlbumResults&p=1&n=20&_format=json&_marker=0&q={query}',
            'search_playlist_new' : 'http://www.saavn.com/api.php?__call=search.getPlaylistResults&_marker=0&_format=json&q={query}',
            'album_details' : 'http://www.saavn.com/api.php?__call=content.getAlbumDetails&_marker=0&_format=json&albumid={album_id}',
            'playlist_details' : 'http://www.saavn.com/api.php?__call=playlist.getDetails&_marker=0&_format=json&listid={playlist_id}'
        }

    def _get_url_contents(self, url):
        url = url.replace(' ','%20')
        response = requests.get(url)
        if response.status_code == 200:
            return response
        else:
            raise BadHTTPCodeError(response.status_code)


    def _get_song_url(self, high_quality, encrypted_media_url):
        from base64 import b64decode as dec
        des_cipher = des(b"38346591", ECB, b"\0\0\0\0\0\0\0\0" , pad=None, padmode=PAD_PKCS5)
        song_url = des_cipher.decrypt(dec(encrypted_media_url))
        if high_quality=="true" :
            song_url=song_url.replace("_96.","_320.")
        else:
            song_url=song_url.replace("_96.","_160.")

#        print song_url
        return song_url

    def _html_decode(self,s):
        htmlCodes = (
            ("'", '&#39;'),
            ('"', '&quot;'),
            ('>', '&gt;'),
            ('<', '&lt;'),
            ('&', '&amp;')
        )
        for code in htmlCodes:
            s = s.replace(code[1], code[0])
        return s
    def _download_track(self, song_url, track_name, dir_name,metadata):
        track_name = self._html_decode(track_name)
        if '.mp4' in song_url:
            track_name = track_name + '.m4a'
        else:
            track_name = track_name + '.mp3'
        file_path = dir_name + '/' + track_name
        print 'Downloading to', file_path
	if os.path.isfile(file_path):
		return
        #print metadata
        #response = self._get_url_contents(song_url)
        #with open(file_path,'wb') as f:
        #    f.write(response.content)
	r = requests.get(song_url, stream=True)
	with open(file_path, 'wb') as f:
		for chunk in r.iter_content(chunk_size=1024):
			if chunk:
				f.write(chunk)
				f.flush()

        if '.m4a' in track_name:
            self._update_metadata_mp4(file_path,metadata)
        else :
            self._update_metadata_mp3(file_path,metadata)


    def _update_metadata_mp4(self,file_path,metadata):
         # print 'updating metadata'

         audio = MP4(file_path)
#         print metadata
         cover = metadata[5].decode('utf8')
         fd = urllib.urlopen(cover)

         covr = MP4Cover(fd.read(), getattr(
            MP4Cover,
            'FORMAT_PNG' if cover.endswith('png') else 'FORMAT_JPEG'
        ))
         fd.close() # always a good thing to do
         audio['covr'] = [covr] # make sure it's a list
         audio["\xa9nam" ] = metadata[0]# name
         audio["\xa9ART" ] = metadata[4]# artist
         audio["\xa9alb" ] = metadata[3]# album
         audio.save()





    def _update_metadata_mp3(self,file_path,metadata):
         # print 'Updating metadata of ' + file_path
         audio = MP3(file_path)

         try:
            audio.add_tags()
         except error :
            pass
         cover = metadata[5].decode('utf8')
         fd = urllib.urlopen(cover)
         audio.tags.add(
            APIC(
            encoding=3, # 3 is for utf-8
            mime='image/png' if cover.endswith('png') else 'image/jpeg', # image/jpeg or image/png
            type=3, # 3 is for the cover image
            desc=u'Cover',
            data=fd.read()
            )
            )


         fd.close() # always a good thing to do
         audio.save()
         audio = EasyMP3(file_path)
	 audio["title" ] = metadata[0]# name
         audio["artist" ] = metadata[4]# artist
         audio["album" ] = metadata[3]# album
         audio.save()




    def _get_file_name(self, _name):
        return _name.strip().replace(" ","_")


    def _check_path(self, _dir):
        import os
        if not os.path.exists(_dir):
            os.system('mkdir %s'%_dir)

    def _check_input(self, ids, len_of_tracks):
        ids = map(lambda x:x.strip(),ids.split(','))
        for i in ids:
            if not i.isdigit():
                return False
            if int(i) > len_of_tracks:
                return False
        return True

    def search_songs(self, query, _dir = 'misc'):
        from pprint import pprint
        self._check_path(_dir)
        url = self.urls['search_songs_new']
        url = url.format(query = query)
        response = self._get_url_contents(url)
        tracks = response.json()['results']
#        print tracks

        if tracks:
            tracks_x = filter(lambda k: ('encrypted_media_url' in k) ,tracks)
            tracks_list = map(lambda x:[x['song'],x['id'],x['albumid'],x['album'],x['singers'],x['image'],x['encrypted_media_url'],x['320kbps']], tracks_x)
            tabledata = [['S No.', 'Track Title', 'Track Artist', 'Album']]
            for idx, value in enumerate(tracks_list):
                tabledata.append([str(idx), value[0], value[4], value[3]])
            table = AsciiTable(tabledata)
            print table.table
            idx = raw_input('Which songs do you wish to download? Enter S No. :')
            while not self._check_input(idx, len(tracks_list)-1):
                print 'Oops!! You made some error in entering input'
                idx = raw_input('Which songs do you wish to download? Enter S No. :')
            idx = int(idx)
            song_url = self._get_song_url(tracks_list[idx][7], tracks_list[idx][6])
            self._download_track(song_url, self._get_file_name(tracks_list[idx][0]), _dir,tracks_list[idx])
        else:
            print 'Ooopsss!!! Sorry no track found matching your query'
            print 'Why not try another Song? :)'

    def search_albums(self, query, _dir = None):
        from pprint import pprint
        from json import dumps, loads, load
        url = self.urls['search_albums_new']
        url = url.format(query = query)
        response = self._get_url_contents(url)
        albums = response.json()['results']
        if albums:
            albums_list = map(lambda x:[x['albumid'],x['title'], x['language'], x['primary_artists'], x['year']], albums)
            tabledata = [['S No.', 'Album Title', 'Album Language', 'Year', 'Artists', 'Track Count']]
            for idx, value in enumerate(albums_list):
                tabledata.append([str(idx), value[1], value[2], value[4], value[3], value[0]])
            table = AsciiTable(tabledata)
            print table.table
            idx = int(raw_input('Which album do you wish to download? Enter S No. :'))
            album_details_url = self.urls['album_details']
            album_details_url = album_details_url.format(album_id = albums_list[idx][0])
#            print album_details_url
            #response = requests.get(album_details_url , headers = {'deviceType':'GaanaAndroidApp', 'appVersion':'V6'})
            response = requests.get(album_details_url , headers = {})
            tracks = response.json()['songs']
            tracks_list = map(lambda x:[x['song'],x['id'],x['albumid'],x['album'],x['singers'],x['image'],x['encrypted_media_url'],x['320kbps']], tracks)
            print 'List of tracks for ', albums_list[idx][1]
            tabledata = [['S No.', 'Track Title', 'Track Artist','Album art']]
            for idy, value in enumerate(tracks_list):
                tabledata.append([str(idy), value[0], value[4], value[5]])
            tabledata.append([str(idy+1), 'Enter this to download them all.',''])
            table = AsciiTable(tabledata)
            print table.table
            print 'Downloading tracks to %s folder'%albums_list[idx][1]
            ids = raw_input('Please enter csv of S no. to download:')
            while not self._check_input(ids, len(tracks_list)) or not ids:
                print 'Oops!! You made some error in entering input'
                ids = raw_input('Please enter csv of S no. to download:')
            if not _dir:
                _dir = "_".join(albums_list[idx][1].split())
            self._check_path(_dir)
            ids = map(int,map(lambda x:x.strip(),ids.split(',')))
            if len(ids) == 1 and ids[0] == idy + 1:
                for item in tracks_list:
                    song_url = self._get_song_url(item[7], item[6])
                    self._download_track(song_url, self._get_file_name(item[0]), _dir,item)
            else:
                for i in ids:
                    item = tracks_list[i]
                    song_url = self._get_song_url(item[7], item[6])
                    self._download_track(song_url, self._get_file_name(item[0]), _dir,item)
        else:
            print 'Ooopsss!!! Sorry no such album found.'
            print 'Why not try another Album? :)'


    def search_playlist(self, query, _dir = None):
        from pprint import pprint
        url = self.urls['search_playlist_new']
        url = url.format(query = query)
        print url
        response = self._get_url_contents(url)
#        print response.text
        playlists = response.json()['results']
        if playlists:
            pl_list = map(lambda x:[x['listid'],x['listname'],  x['uid']], playlists)
            tabledata = [['S No.', 'Playlist', 'uid' ]]
            for idx, value in enumerate(pl_list):
                tabledata.append([str(idx), value[1], value[2]])
            table = AsciiTable(tabledata)
            print table.table
            idx = int(raw_input('Which playlis do you wish to download? Enter S No. :'))
            playlist_details_url = self.urls['playlist_details']
            playlist_details_url = playlist_details_url.format(playlist_id = pl_list[idx][0])
            #response = requests.get(playlist_details_url , headers = {'deviceType':'GaanaAndroidApp', 'appVersion':'V5'})
            response = requests.get(playlist_details_url , headers = {})
            tracks = response.json()['songs']
            tracks_list = map(lambda x:[x['song'],x['id'],x['albumid'],x['album'],x['singers'],x['image'],x['encrypted_media_url'],x['320kbps']], tracks)
            print 'List of tracks for ', pl_list[idx][1]
            tabledata = [['S No.', 'Track Title', 'Track Artist','Album']]
            for idy, value in enumerate(tracks_list):
                tabledata.append([str(idy), value[0], value[4], value[3]])
            tabledata.append([str(idy+1), 'Enter this to download them all.',''])
            table = AsciiTable(tabledata)
            print table.table
            print 'Downloading tracks to %s folder'%pl_list[idx][2]
            ids = raw_input('Please enter csv of S no. to download:')
            while not self._check_input(ids, len(tracks_list)) or not ids:
                print 'Oops!! You made some error in entering input'
                ids = raw_input('Please enter csv of S no. to download:')
            if not _dir:
                _dir = "_".join(pl_list[idx][1].split())
            self._check_path(_dir)
            ids = map(int,map(lambda x:x.strip(),ids.split(',')))
            if len(ids) == 1 and ids[0] == idy + 1:
                for item in tracks_list:
                    song_url = self._get_song_url(item[7], item[6])
                    self._download_track(song_url, self._get_file_name(item[0]), _dir,item)
            else:
                for i in ids:
                    item = tracks_list[i]
                    song_url = self._get_song_url(item[7], item[6])
                    self._download_track(song_url, self._get_file_name(item[0]), _dir,item)
        else:
            print 'Ooopsss!!! Sorry no such playlist found.'
            print 'Why not try another Playlist? :)'

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-a', '--album', nargs='?', help="choose this to search albums. Space seperated query must be enclosed in quotes('')", type = str )
    parser.add_argument('-p', '--playlist', nargs='?', help="choose this to search playlist. Space seperated query must be enclosed in quotes('')", type = str )
    parser.add_argument('-s', '--song', nargs='?', help="choose this to search songs. Space seperated query must be enclosed in quotes('')", type = str)
    parser.add_argument('-d', '--dir', nargs='?', help="can be used to specify directory to download songs to", type = str)
    args = parser.parse_args()
    d = SaavnDownloader()
    if args.album:
        if args.dir:
            d.search_albums(args.album, args.dir)
        else:
            d.search_albums(args.album)
    elif args.playlist:
        if args.dir:
            d.search_playlist(args.playlist, args.dir)
        else:
            d.search_playlist(args.playlist)
    elif args.song:
        if args.dir:
            d.search_songs(args.song, args.dir)
        else:
            d.search_songs(args.song)
    else:
        print parser.parse_args(['--help'])
