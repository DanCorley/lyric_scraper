import time
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup
from textblob import TextBlob
import requests, json, collections
import numpy as np
import pandas as pd
import string
from multiprocessing import Pool


def load_database(file_name):
    
    '''
    loading all saved/ loaded songs until S3 is implemented
    '''
    
    return pd.read_pickle(file_name)

class Artist:
    
    '''
    class to retrieve information about any artist.
    initialize with the artist's title (str).

    needs to run in order:
        .get_albums() - return all albums
        .get_songs() - return all songs in albums
        .get_lyrics() - return lyrics from all songs
    '''
    
    def __init__(self, name):
        self.name = name
        self.albums = 'none yet. run get_albums'
        self.songs = 'none yet. run get_songs'
        self.lyrics = 'none yet. run_get lyrics'
    
    def get_albums(self):
        '''
        input: artist's name 
        output: 
        '''
        # initialize the selenium driver and open the artist's page
        driver = webdriver.Chrome('/Users/dcorley/Documents/Flatiron/Lyrics/lyric_scraper/chromedriver')
        driver.get(f'https://genius.com/artists/{self.name}')

        class_name = 'full_width_button.u-clickable.u-quarter_top_margin'
        driver.find_element_by_class_name(class_name).click()

        # wait for the page to load
        time.sleep(.5)

        # click the modal, and scroll to load all albums
        modal_name = 'act-show.cont-artists.snarly.u-noscroll.u-dark_overlay'
        modal = driver.find_element_by_class_name(modal_name)
        modal.click()
        modal.send_keys(Keys.END)
        time.sleep(.5)

        # return html and close connection
        source = driver.page_source
        driver.quit()

        # initialize soup object and find all albums
        soup = BeautifulSoup(source, features='lxml')
        modal = soup.find_all('mini-album-card')

        # function to help out for getting links below
        def get_link(x):
            return x.find('a', href=True)['href']
        
        def get_title(x):
            x = x.find('div', class_='mini_card-title')
            x = x.get_text()
            return x
        
        def get_year(x):
            x = x.find('div', class_='mini_card-subtitle')
            x = x.get_text()
            return x
    
        # return paths to all albums
        album_links = [get_link(x) for x in modal]
        titles = [get_title(x) for x in modal]
        year = [get_year(x) for x in modal]
        
        zipped = zip(titles, year, album_links)
        columns = ['albums', 'release_year', 'links']
        albums = pd.DataFrame(zipped, columns=columns)
        
        self.albums = albums
    
    
    def get_track_list(self, link):
        
        '''
        Return all tracks from an artist's album
        To be used inside .get_songs() to return for all albums
        
        '''
        
        # helper fuction for clean track names
        def song_names(string):
            string = string.get_text()
            string = string.split('\n')[2].strip()
            return string
        
        # make request and create soup object
        request = requests.get(link)
        soup = BeautifulSoup(request.content, features='lxml')
        
        # find the album title
        alb_text = 'header_with_cover_art-primary_info-title header_with_cover_art-primary_info-title--white'
        album = soup.find('h1', class_=alb_text).get_text()
        print(f'finding {album}')
        
        # find the list of songs in album
        songs = soup.find_all('a', class_='u-display_block')
        links = [song['href'] for song in songs]
        names = [song_names(song) for song in songs]
        zipped = zip(names, links)
        
        # create df containing names, links, and albums
        columns = ['names', 'links']
        new_df = pd.DataFrame(zipped, columns=columns)
        new_df['album'] = album
        return new_df
    
    
    def get_songs(self, end=None):
    
        '''
        input: dataframe of albums
        output: dataframe of all songs
        '''
        if type(self.albums) != pd.DataFrame:
            raise NotImplementedError('You need to run .get_albums first')
        
        # create empty df
        df = pd.DataFrame()
        
        # create list of the unique album names
        iterable = self.albums.links[:end]
        
        # 
        with Pool() as pool:
            lst = pool.map(self.get_track_list, iterable=iterable)
        pool.close()
        
        # create df 
        for x in lst:
            df = df.append(x)

        self.songs = df
        
    def get_lyrics(self, alert_pct=20, verbose=True):

        '''
        input: list of lyric paths
        params: alert = number of 
        output: dataframe containing info for all songs
        '''
        song_links = self.songs.links

        # to print out the retrieval % completion of songs
        if verbose == True:
            num_links = len(song_links)
            alert = round((alert_pct/100) * num_links, 0)
            alert_num = [i for i in range(num_links) if not i % alert and i !=0]

        # set up and get all lyrics from songs
        lyrics = []

        for i, path in enumerate(song_links):

            # let user know where the scraping is
            if verbose == True:
                if i in alert_num:
                    print(f'Completed scraping {round((i/num_links)*100, 0)}% of songs.')

            request = requests.get(path)

            # Check to make sure the request didn't return a 404
            if request.status_code != 200:
                print(f'Error code: {request.status_code}')
                print(f'Completed {(i/num_links)*100}% of scraping')
                song_df = pd.DataFrame(lyrics)
                return song_df

            # turn the content into a BeautifulSoup object
            soup = BeautifulSoup(request.content, features='lxml')

            # find the lyrics and clean
            song_lyrics = soup.find('div', class_='lyrics').get_text()
            song_lyrics = song_lyrics.split('\n')
            song_lyrics = [line for line in song_lyrics if not line.startswith('[')]
            song_lyrics = [line for line in song_lyrics if len(line)]

            # find the song's title
            song_title = soup.find('h1', class_='header_with_cover_art-primary_info-title')
            song_title = song_title.get_text()

            # find the artist of the song
            artist = soup.find('a', class_='header_with_cover_art-primary_info-primary_artist')
            artist = artist.get_text()

            # find the song's album
            album = soup.find('a', class_='song_album-info-title').get_text()
            album = album.split('\n')[1].strip()

            # return all 
            lyrics.append({'artist': artist, 'album': album, 'song_title': song_title, 'lyrics': song_lyrics})
        
        lyric_df = pd.DataFrame(lyrics)
        
        self.lyrics = lyric_df
        
        
    def get_sentiment(self):
        
        lyric_df = self.lyrics
        
        lyric_df['num_lines'] = lyric_df['lyrics'].map(lambda x: len(x))

        lyric_df = lyric_df[lyric_df['num_lines'] > 1]

        def get_words(lines):
            words = [word.lower() for word in lines]
            words = ' '.join(words)
            return words

        lyric_df['words'] = lyric_df['lyrics'].map(lambda x: get_words(x))

        def get_sentiment(lyrics):
            blob = TextBlob(lyrics)
            sentiment = blob.sentiment.polarity
            return sentiment

        # calculate sentiment    
        lyric_df['sentiment'] = lyric_df['words'].map(lambda x: get_sentiment(x))
        
        self.lyrics = lyric_df