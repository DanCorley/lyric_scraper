# pulling info
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.expected_conditions import presence_of_element_located
from bs4 import BeautifulSoup
import multiprocess as mp
import requests

# sentiment analysis
from textblob import TextBlob

# file management
import boto3
import io
import os

# data processing
import re
import pandas as pd

import time
import sys


class Artist:
    
    '''
    class to retrieve information about any artist.
    initialize with the artist's title (str).

    needs to run in order:
        .get_albums() - return all albums
        .get_songs() - return all songs in albums
        .get_lyrics() - return lyrics from all songs
    '''
        
    def __init__(self, artist_name, driver_path='webdrivers/chromedriver'):
        self.name = artist_name
        self.albums = 'none yet. run get_albums'
        self.songs = 'none yet. run get_songs'
        self.lyrics = 'none yet. run get_lyrics'
        try:
            self.path = os.path.dirname(__file__)
        except NameError:
            # file path working in Jupyter
            self.path = os.getcwd()
            
        self.chromedriver_path = os.path.join(self.path, driver_path)
        self.found = False
        
        self._access = os.environ.get('AWS_ACCESS_KEY')
        self._secret = os.environ.get('AWS_SECRET_KEY')
        self.s3_setup = False

        self.force_download = False
        self._not_loaded = True
        
        self.verbose = True
    
        
    def _sys_print(self, x):
        a = str(x)
        padding = " " * (130 - len(a))
        sys.stdout.flush()
        sys.stdout.write(a+padding+'\r')
        
    def get_albums(self, headless=True):
        '''
        input: artist's name 
        output: None, .albums
        '''
        
        # if you'd like the scraping to be visible
        chrome_options = webdriver.chrome.options.Options()
        chrome_options.headless = headless
        
        # initialize the selenium driver and open the artist's page
        try:
            driver = webdriver.Chrome(
                executable_path = self.chromedriver_path,
                options = chrome_options
            )
        except Exception as e:
            ns = 'this version of chromedriver is not supported, go get your supported version'
            dl = 'https://chromedriver.chromium.org/downloads'
            raise RuntimeError(ns+'\n'+dl)
        
        driver.get(f'https://genius.com/artists/{self.name}')
        
        try:
            driver.find_element_by_class_name('render_404-headline')
            raise AttributeError(f'{self.name} was not found - did you spell it correctly?')
        except Exception:
            pass
        
        class_name = 'full_width_button.u-clickable.u-quarter_top_margin'
        driver.find_element_by_class_name(class_name).click()
    
        # wait for the page to load
        modal_name = 'act-show.cont-artists.snarly.u-noscroll.u-dark_overlay'
        
        modal = WebDriverWait(driver, 60).until(
            presence_of_element_located(('class name', modal_name))
        )
        
        # click the modal, and scroll to load all albums
        time.sleep(.5)
        modal.click()
        modal.send_keys('\ue010')
        time.sleep(.2)
        modal.send_keys('\ue010')
        time.sleep(.2)

        # return html and close connection
        source = driver.page_source
        driver.close()
        driver.quit()

        # initialize soup object and find all albums
        soup = BeautifulSoup(source, features='lxml')
        albums = soup.find_all('mini-album-card')
        
        artist = soup.find('h1', 'profile_identity-name_iq_and_role_icon')
        self.name = artist.text.strip().split('\n')[0]
        
        try:
            if not self.force_download:
                self.s3_initialize()
                self.read_file_from_s3()
                self.albums = 'loaded from storage'
                self.songs = 'loaded from storage'
                self._not_loaded = False
                return None                
        except:
            print('No file found for that artist. Scraping....')
        
        # function to help out for getting links below
        def get_link(x):
            return x.find('a', href=True)['href']
        
        def get_title(x):
            x = x.find('div', class_='mini_card-title')
            return x.get_text()
        
        def get_year(x):
            x = x.find('div', class_='mini_card-subtitle')
            return x.get_text()
        
        artist = soup.find('h1', 'profile_identity-name_iq_and_role_icon')
        self.name = artist.text.strip().split('\n')[0]
    
        # return paths to all albums
        album_links = [get_link(x) for x in albums]
        titles = [get_title(x) for x in albums]
        year = [get_year(x) for x in albums]
        
        zipped = zip(titles, year, album_links)
        columns = ['albums', 'release_year', 'links']
        albums = pd.DataFrame(zipped, columns=columns)
        albums['artist'] = self.name
        
        print(f"found {len(titles)} albums for artist {self.name}")
        
        self.albums = albums
    
    
    def _song_helper(self, album):
        
        '''
        Return all tracks from an artist's album
        Optimally used inside .get_songs() to return for all albums
        
        '''

        if self.verbose:
            self._sys_print(f'finding album - {album.albums}')

        # helper fuction for clean track names
        def song_names(string):
            string = string.get_text()
            return string.split('\n')[2].strip()
        
        # make request and create soup object
        request = requests.get(album.links)
        soup = BeautifulSoup(request.content, features='lxml')
                
        # find the list of songs in album
        songs = soup.find_all('a', class_='u-display_block')
        links = [song['href'] for song in songs]
        names = [song_names(song) for song in songs]
        zipped = zip(names, links)
        
        # create df containing names, links, and albums
        columns = ['names', 'links']
        new_df = pd.DataFrame(zipped, columns=columns)
        new_df['album'] = album.albums
        new_df['artist'] = album.artist
        new_df['album_link'] = album.links
        new_df['album_year'] = album.release_year
        
        return new_df
    
    
    def get_songs(self, end=None):
        '''
        input: dataframe of albums
        output: dataframe of all songs
        '''
        if type(self.albums) != pd.DataFrame:
            raise NotImplementedError('You need to run .get_albums first')
                    
        # create list of the unique album names
        iterable = [x for i,x in self.albums.iloc[:end].iterrows()]
                
        # multiprocessing ftw
        pool = mp.Pool(5)
        album_lst = pool.map(self._song_helper, iterable=iterable)
        pool.close()
        pool.join()
        
        # create df 
        df = pd.concat([album for album in album_lst])

        print(f"finished finding {len(df):,} songs"+(" "*50))
        
        self.songs = df

        
    def _lyric_helper(self, row):
        
        request = requests.get(row.links)
        
        if self.verbose:
            self._sys_print(f'finding song lyrics - {row.names}')

        # turn the content into a BeautifulSoup object
        soup = BeautifulSoup(request.content, features='lxml')

        # find the lyrics and clean
        lyric_list = soup.find_all('div', class_='Lyrics__Container-sc-1ynbvzw-7')
        song_lyrics = ' '.join([x.get_text(';') for x in lyric_list if x.text])
        song_lyrics = re.sub(r'\[(.*?)\];', "", song_lyrics)
        clean_lyrics = re.sub("[^a-zA-Z\d\s:;']", '', song_lyrics).replace(';', '. ')

        lyrics = {
            'artist': row.artist,
            'album': row.album,
            'song_title': row.names,
            'song_link': row.links,
            'album_link': row.album_link,
            'album_year': row.album_year,
            'rough_lyrics': song_lyrics,
            'lyrics': TextBlob(clean_lyrics)
        }

        return lyrics
        

    def get_lyrics(self, end=None):

        '''
        input: list of lyric paths
        params: alert = number of 
        output: dataframe containing info for all songs
        '''
        if type(self.songs) != pd.DataFrame:
            raise NotImplementedError('You need to run .get_songs first')
    
        iterable = [x for i,x in self.songs.iloc[:end].iterrows()]
        
        # multiprocessing ftw
        pool = mp.Pool(7)
        lyric_lst = pool.map(self._lyric_helper, iterable=iterable)
        pool.close()
        pool.join()
    
        lyric_df = pd.DataFrame(lyric_lst)
        
        print(f"finished grabbing lyrics for {len(lyric_df):,} songs"+(" "*50))
        
        self.lyrics = lyric_df
        
    
    def print_one_lyric(self, song):
        '''
        a convenience function to return a _better_ printed version of lyrics
        ( list containing separate )
        '''
        
        song = str(song).lower()
        mask = self.lyrics.song_title.str.lower().str.contains(song)
        lyric = self.lyrics.loc[mask, 'lyrics'].iloc[0]
        
        if len(lyric):
            return lyric
        print(f'No song found for {song}! Check your spelling.')
    
        
    def get_sentiment(self):
        
        df = self.lyrics
        
        df['num_words'] = df.lyrics.map(lambda x: len(x.words))
        
        df['unique_words'] = df.lyrics.map(lambda x: len(x.word_counts))

        # calculate sentiment
        _ = df.lyrics.map(lambda x: x.sentiment)
        df[['polarity', 'subjectivity']]  = pd.DataFrame(_.tolist(),index=df.index)
        
        self.lyrics = df
        
        
    def s3_initialize(self):
        
        if not all((self._access, self._secret)):
            print('aws access keys not found in env variables')
            print('please set AWS_ACCESS_KEY and AWS_SECRET_KEY')
            return None
        
        self.s3 = boto3.client(
            's3',
            aws_access_key_id=self._access,
            aws_secret_access_key=self._secret,
        )
        self.bucket = 'geniuslyrics'
        
        self.s3_setup = True
        
        
    def save_file_to_s3(self):
        
        if not self.s3_setup:
            self.s3_initialize()
        
        df = self.lyrics.copy()
        
        df.lyrics = df.lyrics.apply(lambda x: x.raw)

        buffer = io.BytesIO()
        df.to_feather(buffer)
        buffer.seek(0)

        self.s3_meta = self.s3.put_object(Body=buffer, Bucket=self.bucket, Key=self.name)

        
    def read_file_from_s3(self):
        
        if not self.s3_setup:
            self.s3_initialize()
            
        retr = self.s3.get_object(Bucket=self.bucket, Key=self.name)

        df = pd.read_feather(io.BytesIO(retr['Body'].read()))

        df.lyrics = df.lyrics.apply(TextBlob)

        self.lyrics = df
        
    
    def run_all_artist(self, num_albums=None, num_songs=None, headless=True):
        then = time.perf_counter()
        self.get_albums(headless)
        if self._not_loaded:
            self.get_songs(num_albums)
            self.get_lyrics(num_songs)
            self.get_sentiment()
            self.save_file_to_s3()
            print(f"finished in {time.perf_counter() - then:.2f} seconds")
        else:
            print(f'Loaded {self.name} from storage')
