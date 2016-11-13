#! python3
#search amazon for watches and store the images found in a directory 'rawimages'
#use machine learning to identify a watch and store the image in the dataset
#TO DO : download page range instead of all pages
#TO DO : rewrite with scrappy
#UPDATE 12/11 - Added save scraped data to CSV file

import requests
import os
import bs4
from pathlib import Path
from fake_useragent import UserAgent
import time
import cv2
import threading
from redis import Redis
import csv


#will work better when connecting on avast secure line
#altenative is to implement a rotating public proxy
#doc: http://www.doc.ic.ac.uk/~pg1712/blog/python-proxy/

#0.0 ---- define some parameters
#url = 'https://www.amazon.fr/s/url=search-alias%3Dwatches&field-keywords=montres'
url = 'https://www.amazon.fr/s/url=search-alias%3Dwatches&field-keywords=citizen'
directoryImages = Path("D:/Users/olivi/ComputerVision/amazonScraper/rawImages/_")
NB_PAGES_TO_DOWNLOAD = 1
REDIS_PORT = 6379
ASIN_POS = 0 #location in the redisDB of the ASIN


#the following function get an url and return the request object
# it encapsulate error handling when getting an URL
# options are random useragent and timeout
#TO DO : add possibility to call a proxy

def getPageContent(url, userAgent = None, reqTimeout = 20):
    try:
        if userAgent == True:
            ua= UserAgent()
            userAgent={'User-Agent': ua.random}
            res = requests.get(url, headers=userAgent, timeout=reqTimeout)
        else:
            res = requests.get(url, timeout=reqTimeout)

    except ConnectionError:
        print("Error connecting : " + str(url))
        print("CONNECTION ABORTED")
        pass
    except requests.exceptions.ReadTimeout:
        print("Read timed out after "+str(reqTimeout)+ "seconds")
        print("CONNECTION ABORTED")
        pass
    return(res)

def saveImageToDisk(index, soupObject, redisPipeline):
    #Use chrome F12 - right click - copy selector on the element
    selector = "#result_"+str(index)+" > div > div.a-row.a-spacing-base > div > div > a > img"
    asinSelector = "#result_"+str(index)
    asin = 'NA'
    pathImage = 'NA'
    pictureUrl= ""

    #Extract the ASIN
    asin = soupObject.select(asinSelector)
    if asin == []:
        print("Could not find an element with asin selector." + str(asinSelector))
    else: #get the asin
        asin=asin[0].get('data-asin')

    #Extract the image path,
    element =  soupObject.select(selector)

    if element == []:
        print("Could not find an element with selector." + str(selector))
    else: #get image path
        pictureUrl = element[0].get('src')
        print('{0} - Downloading image {1}...'.format(str(index),pictureUrl))
        image=getPageContent(pictureUrl, True) #get the picture with random UA and 5s timeout
        #save the images to the imagedirectory
        pathImage = str(directoryImages)+pictureUrl[49:60]+".jpg"
        imageFile=open(pathImage, 'wb')
        for chunk in image.iter_content(100000):
            imageFile.write(chunk)
        imageFile.close()

    #store the image path and corresponding "AMZ" + ASIN in the redis pipeline
    if asin != 'NA' and pathImage!= 'NA':
        redisPipeline.rpush("path:{}".format(pathImage), "AMZ"+str(asin))
        

def getNextPage():
    selector = "#pagnNextLink"
    element = soup.select(selector)
    url = "https://www.amazon.fr"+element[0].get('href')
    return(url)


for page in range (0, NB_PAGES_TO_DOWNLOAD): #download NB_PAGES_TO_DOWNLOAD pages
#open a Redis pipeline, it will be used to store the scraped data and save to CSV
    redisDB = Redis(host="localhost", port=REDIS_PORT, db=0, charset="utf-8", decode_responses=True)
    #SOURCE: http://stackoverflow.com/questions/25745053/about-char-b-prefix-in-python3-4-1-client-connect-to-redis
    
    redisPipeline = redisDB.pipeline()

    #1.1 --- Download the page ---
    print('Downloading page %s...' %url)
    res = getPageContent(url, True) #request url with random ua and 20s 
    soup=bs4.BeautifulSoup(res.text, "html.parser") #create an object containing the HTML of the page

    #1.2 --- Save images of this page to disk
    #There are 50 elements per page, loop 50 triggering 50 times

    saveThreads=[]
    for i in range(0, 48):
        index=  page * 48 + i 
        #save the image to the disk AND save scraped data to the Redis pipeline
        saveThread=threading.Thread(target=saveImageToDisk, args=(index, soup, redisPipeline )) 
        saveThreads.append(saveThread)
        saveThread.start()
        #wait for all threads to end for this page
    for saveThread in saveThreads:
        saveThread.join()  
    #execute the redis pipeline and save the data to a CSV file       
    redisPipeline.execute()
    redisDB.save()

    #saveScrapedPageToCSV(redisDB) #will also delete the rediskeys 
    #(will be done after enrichment in automated classifier


    print('Page ' +str(page+1)+ ' Scraped !')

    #1.3 --- get next page and continue the download
    try:
        url=getNextPage()
    except Exception as error:
        print("Waiting 15s because of error: " + str(error.__doc__)+ str(error.message))
        time.sleep(15) #wait for the connection to be back or button to appear
        url=getNextPage()
    

