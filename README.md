# Genius Lyric Scraper

This project aims to help in downloading all lyrics for any musical artist from the web, to be able to compile them into an easily manageable dataset. The overall goal is to create a cookie-cutter template that anyone can easily use to scrape their own data. The bulk of this project includes methods to pull lyrics by artist, album, and song levels.

#### -- Project Status: [On-Going]

### Methods/ Technologies
* Web Scraping:
    *  selenium, requests, BeautifulSoup
* Amazon S3
    * boto3 - storage of the lyrical data
* Sentiment Analysis
    * TextBlob
* Multiprocessing

## Package Description

The lyric_scraper package through a few quick methods to gather lyrical data:


```python
a = Artist({artist_name})
    # class instantiation of the musical artist you would like to find lyrics for

a.get_albums():
    # method to pull all of the albums and URLs from and artist's Genius page
    # pulls from storage if Artist is already found (set a.force_download to refresh)

a.get_songs()
    # method to pull all of the songs and URLs from artist page
    # utilizes multiprocessing to pull each album asynchronously

a.get_lyrics()
    # method to scrape all of the lyrics from the songs pages

a.get_sentiment()
    # return scores for the overall sentiment of a song

a.save_file_to_s3()
    # uploads the lyric dataframe to an s3 bucket
```
    
##### OR
  
```python
a.run_all_artist()
    # conveinence function for everything above
```

## Contact
* Feel free to contact me if any questions, or comments on the project - [hello@dancorley.com]