# selenium and BeautifulSoup for pulling info
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.expected_conditions import presence_of_element_located
from bs4 import BeautifulSoup

# sentiment analysis
from textblob import TextBlob

import time
import requests
import os
import re
import pandas as pd
import multiprocess as mp


class Artist:
    
    '''
    class to retrieve information about any artist.
    initialize with the artist's title (str).

    needs to run in order:
        .get_albums() - return all albums
        .get_songs() - return all songs in albums
        .get_lyrics() - return lyrics from all songs
    '''
    
    def __init__(self, name, driver_path='webdrivers/chromedriver'):
        self.name = name
        self.albums = 'none yet. run get_albums'
        self.songs = 'none yet. run get_songs'
        self.lyrics = 'none yet. run_get lyrics'
        try:
            self.path = os.path.dirname(__file__)
        except NameError:
            # file path working in Jupyter
            self.path = os.getcwd()
            
        self.chromedriver_path = os.path.join(self.path, driver_path)
        
        
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
            presence_of_element_located((By.CLASS_NAME, modal_name))
        )
        
        # click the modal, and scroll to load all albums
        time.sleep(.5)
        modal.click()
        modal.send_keys(Keys.END)
        time.sleep(.2)
        modal.send_keys(Keys.END)
        time.sleep(.2)

        # return html and close connection
        source = driver.page_source
        driver.close()
        driver.quit()

        # initialize soup object and find all albums
        soup = BeautifulSoup(source, features='lxml')
        albums = soup.find_all('mini-album-card')

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
        artist = artist.text.strip().split('\n')[0]
    
        # return paths to all albums
        album_links = [get_link(x) for x in albums]
        titles = [get_title(x) for x in albums]
        year = [get_year(x) for x in albums]
        
        zipped = zip(titles, year, album_links)
        columns = ['albums', 'release_year', 'links']
        albums = pd.DataFrame(zipped, columns=columns)
        albums['artist'] = artist
        
        self.albums = albums
    
    
    def _song_helper(self, album, verbose=True):
        
        '''
        Return all tracks from an artist's album
        Optimally used inside .get_songs() to return for all albums
        
        '''

        if verbose:
            print(f'finding album {album.albums}')

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

        self.songs = df

        
    def _lyric_helper(self, row):
        
        request = requests.get(row.links)

        # turn the content into a BeautifulSoup object
        soup = BeautifulSoup(request.content, features='lxml')

        # find the lyrics and clean
        lyric_list = soup.find_all('div', class_='Lyrics__Container-sc-1ynbvzw-7')
        song_lyrics = ' '.join([x.get_text(';') for x in lyric_list if x.text])
        clean_lyrics = re.sub(r'\[(.*?)\];', "", song_lyrics)

        lyrics = {
            'artist': row.artist,
            'album': row.album,
            'song_title': row.names,
            'lyrics': clean_lyrics
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
        pool = mp.Pool(5)
        lyric_lst = pool.map(self._lyric_helper, iterable=iterable)
        pool.close()
        pool.join()
    
        lyric_df = pd.DataFrame(lyric_lst)
        
        self.lyrics = lyric_df
        
        
    def get_sentiment(self):
        
        df = self.lyrics
        
        df['num_words'] = df.lyrics.str.split(' ').str.len()

        df['words'] = df.lyrics.str.lower()

        def get_sentiment(lyrics):
            blob = TextBlob(lyrics)
            return blob.sentiment

        # calculate sentiment
        _ = df['words'].map(lambda x: get_sentiment(x))
        df[['polarity', 'subjectivity']]  = pd.DataFrame(_.tolist(),index=df.index)
        
        self.lyrics = df
