#!python3

#This is a module that scan a directory of images (rawImages) and identify watches in it
#if yes it is saved in the \watches directory with a watch_randomnb file name
#else it is saved in the \notwatch directory
#the model is trained with images found in \dataset directory
#[12-11-2016] Saved additional scraped data in a csv file in the watches directory
#TO DO: use the descriptor object in the descriptorWatches.py file
#TO DO: use the progressbar object (cf example in indexwatchescaltalog.py
#TO DO: tell when finished

import cv2
from pathlib import Path
import datetime
from hog import HOG
from skimage import feature
from sklearn.ensemble import RandomForestClassifier
#[12-11-2016] scraped data
from redis import Redis
import csv


class isThatAWatch:
    def __init__(self, pathImage):
        self.savedWatchPath = str(directoryWatches)+"_"
        self.savedNotWatchPath = str(directoryNotWatches)+"_"
        #load the image and call the model to define if it is a watch or not
        imageToRecognize=cv2.imread(pathImage)
        features=describe(imageToRecognize)
        prediction=model.predict(features.reshape(1,-1))[0]

        if prediction == WATCH: #save it to the watch directory
            fileName=str(self.savedWatchPath)+"watch_"+str(datetime.datetime.now())[20:]+".jpg"
            cv2.imwrite(fileName, imageToRecognize)

            #[22-11-2016]-Scraped Data
            #get the additional data from the redis with key = pathImage
            REDIS_PORT = 6379 
            ASIN_POS = 0 #Scraped data: location in the redisDB of the ASI
            redisDB = Redis(host="localhost", port=REDIS_PORT, db=0, charset="utf-8", decode_responses=True)
            key = "path:{}".format(pathImage)
            redisData = redisDB.lrange(key, 0, -1)
            asinCSV = redisData[ASIN_POS]
            csvFile=open(str(directoryWatches)+"images.csv", 'a+', newline='') #append to the file and create it if needed
            outputWriter = csv.writer(csvFile)
            outputWriter.writerow([fileName, asinCSV])
            #cleanup
            redisDB.delete(key) #delete the key now useless
            csvFile.close()
            #[22-11-2016]-Scraped Data
            print("[INFO] Stored watch in: "+fileName)
        elif prediction == NOTWATCH: #save it to the notwatch directory
            fileName=str(self.savedNotWatchPath)+"notwatch_"+str(datetime.datetime.now())[20:]+".jpg"
            cv2.imwrite(fileName, imageToRecognize)
            print("[INFO] Stored not_watch in: "+fileName)

   
def initializeRandomForest():
    #this function willtrain a randomforest and return the corresponding model
    print("[INFO] extracting features...")
    imagePaths = sorted(list(directoryDataset.glob('**/*.jpg')))
    trainLabels=[]
    trainData=[]
    
    # loop over the images in the input directory
    for imagePath in imagePaths:
            # extract the label and load the image from disk
            label = str(imagePath)[str(imagePath).find("_") + 1:].split("_")[0]
            image = cv2.imread(str(imagePath))
            # extract features from the image, then update the list of labels and
            # features
            features = describe(image)
            trainLabels.append(label)
            trainData.append(features)
    model = RandomForestClassifier(n_estimators=20, random_state=42)
    # train the decision tree
    print("[INFO] training model...")
    model.fit(trainData, trainLabels)
    print("[INFO] model is trained...")
    return(model)
            
def describe(image):
    
    # extract HOG features of the image and return it
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    standardized=cv2.resize(gray, STANDARD_SIZE)
    equalized = cv2.equalizeHist(standardized)
    hog = feature.hog(equalized, orientations= HOG_ORIENTATIONS,
                      pixels_per_cell= HOG_PIXELS,
                      cells_per_block= HOG_CELLS,
                      transform_sqrt= True)
        
    # return a concatenated feature vector of color statistics and Haralick
    # texture features
    #return np.hstack([colorStats, haralick])
    return hog


# 1.0 --- initialize some variables
basePath="D:/Users/olivi/ComputerVision/amazonScraper"
directoryDataset = Path(basePath+"/dataset")
directoryWatches= Path(basePath+"/watches/_")
directoryNotWatches= Path(basePath+"/notwatches/_")
directoryRawImages= Path(basePath+"/rawImages")

HOG_ORIENTATIONS = 14
HOG_PIXELS = (8,8)
HOG_CELLS = (4,4)
STANDARD_SIZE = (190, 246) #new size of individual digit
WATCH = 'watch'
NOTWATCH = 'notwatch'


model=initializeRandomForest()


listOfImages=list(directoryRawImages.glob('**/*.jpg'))

for filename in (listOfImages):
    isThatAWatch(str(filename))
    


