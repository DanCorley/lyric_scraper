# Genius.com Lyric Scraper

This project aims to help in downloading all lyrics for any musical artist from the web, to be able to compile them into an easily manageable dataset. The overall goal is to create a cookie-cutter template that anyone can easily use to scrape their own data. The bulk of this project includes methods to pull lyrics by artist, album, and song levels.

#### -- Project Status: [On-Going]

### Methods/ Technologies
* Web Scraping:
    *  selenium, requests, BeautifulSoup
* Amazon S3
    * boto3 - storage of the lyrical data
* Sentiment Analysis
    * spaCy, TextBlob
* Multiprocessing

## Package Description
* #### Scraping:
The lyric_scraper package through a few quick methods to gather lyrical data:
    
    ```
    Artist()
        * class instantiation of the musical artist you would like to scrape
        
    .get_albums():
        * method to scrape all of the albums and URLs from and artist's page
        
    .get_songs()
        * method to scrape all of the songs and URLs from album pages
        * to improve the speed of the scraping, this method will utilize Pool multiprocessing, and scrape each album
        
    .get_lyrics()
        * method to scrape all of the lyrics from the songs pages
        
    .get_sentiment()
        * return scores for the overall sentiment of a song
    ```
    
* #### Amazon S3:
The amzn package helps store all pulled lyrics, and store all that have been pulled
    ```
    .available_files()
        * show all files available to a user
        
    .download_file()
        * pull file containing 
    
    .upload_file()
        *save current data
    ```

## Contact
* Feel free to contact me if any questions, or comments on the project - [hello@dancorley.com]


