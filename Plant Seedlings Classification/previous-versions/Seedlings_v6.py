import os
import matplotlib.pyplot as plt
import numpy as np
import cv2
from glob import glob

# sklearn

from sklearn.preprocessing import StandardScaler
from sklearn.cross_validation import train_test_split

# Keras

import keras
from keras.layers import Dense, Dropout, Flatten, Conv2D, MaxPooling2D
from keras.models import Sequential, Input, Model
from keras.layers.normalization import BatchNormalization
from keras.layers.advanced_activations import LeakyReLU
from keras.callbacks import EarlyStopping
from keras.utils import to_categorical
from keras.optimizers import RMSprop, SGD
from keras.preprocessing.image import ImageDataGenerator
from keras.models import model_from_json
import keras.backend as K

import h5py

# Data Folders
TRAIN_DATA_FOLDER = '.../Seedlings/train'
TEST_DATA_FOLDER = '.../Seedlings/test'

# Default Filters

lower_HSV = np.array([35, 100, 5]) 
upper_HSV = np.array([200, 255, 255])

# Definitions

# HSV Definitions
def HSV_mask(image, lower_HSV, upper_HSV):
    mask = cv2.inRange(image, lower_HSV, upper_HSV)
    
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11,11))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    return mask
    
def sharpen_image(image):
    #image_blurred = cv2.GaussianBlur(image, (0, 0), 3)
    image_blurred = cv2.bilateralFilter(image, 9, 75,75)
    image_sharp = cv2.addWeighted(image, 1.5, image_blurred, -0.5, 0)
    return image_sharp
 
def process_image(image, lower_HSV=lower_HSV, upper_HSV=upper_HSV):
    image = sharpen_image(image)
    mask = HSV_mask(image, lower_HSV, upper_HSV)
    output = cv2.bitwise_and(image, image, mask = mask)
    (_, contours, heiarchy) = cv2.findContours(mask, cv2.RETR_TREE, 
    cv2.CHAIN_APPROX_SIMPLE)
    return output, contours, heiarchy

# Sliders for adjusting HSV on sample image 
def LowerH(val, lower_HSV=lower_HSV):
    global sample_image
    lower_HSV[0] = val
    image, contours, heiarchy = process_image(sample_image, lower_HSV)
    cv2.drawContours(image, contours, -1, (0, 0, 255), 1)
    cv2.imshow('Filtered Image', image)
    
def LowerS(val, lower_HSV=lower_HSV):
    global sample_image
    lower_HSV[1] = val
    image, contours, heiarchy = process_image(sample_image, lower_HSV)
    cv2.drawContours(image, contours, -1, (0, 0, 255), 1)
    cv2.imshow('Filtered Image', image)
    
def LowerV(val, lower_HSV=lower_HSV):
    global sample_image
    lower_HSV[2] = val
    image, contours, heiarchy = process_image(sample_image, lower_HSV)
    cv2.drawContours(image, contours, -1, (0, 0, 255), 1)
    cv2.imshow('Filtered Image', image)
    
# Summary of countours found for each species in training set

def contour_summary(labels, filenames, n_contours): 
    df_contours = pd.DataFrame()
    df_contours = pd.DataFrame({'label':labels,'filename':filenames, 'n_contours':n_contours})
    df_contours = df_contours.set_index(['label','filename'])
    df_contours = df_contours.sort_index()
    
    df_summary = pd.DataFrame(index=np.unique(labels), columns=['min num contours','max num contours','frac_with_contours'])
    
    for label in np.unique(labels):
        desc = df_contours.loc[(label)].describe()
        df_summary.loc[(label)]['min num contours'] = desc.loc[('min','n_contours')]
        df_summary.loc[(label)]['max num contours'] = desc.loc[('max','n_contours')]
        df_summary.loc[(label)]['frac_with_contours'] = np.count_nonzero(df_contours.loc[(label)]) / desc.loc[('count','n_contours')]
    
    print(df_summary)

# Adjustable Filter to pick out the plant

def create_mask(image, upper_HSV, lower_HSV):
    mask = cv2.inRange(image, lower_HSV, upper_HSV)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11,11))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    masked_image = cv2.bitwise_and(image, image, mask = mask)
    (_, contours, _) = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    return masked_image, contours
    
def count_contours(contours, min_shape_size):
    num = 0
    for c in contours:
        area = cv2.contourArea(c)
        if area >= min_shape_size:
            num = num + 1
    return(num)

def tune_hue(image, upper_HSV, lower_HSV, min_shape_size, contour_threshold_upper, contour_threshold_lower):
    
    contour_counter = 0

    while contour_counter <= contour_threshold_lower or contour_counter >= contour_threshold_upper:
        masked_image, contours = create_mask(image, upper_HSV, lower_HSV)
        contour_counter = count_contours(contours, min_shape_size)
        
        # 1
        lower_HSV[0] = lower_HSV[0] - 2
        upper_HSV[0] = upper_HSV[0] + 2
        
        #print('Hue', lower_HSV[0])
        
        if lower_HSV[0] < 20:
            break
        
        # if lower_HSV[0] >= upper_HSV[0]:
        #     break
    
    return(masked_image, contours, upper_HSV, lower_HSV)
        
def tune_sat(image, upper_HSV, lower_HSV, min_shape_size, contour_threshold_upper, contour_threshold_lower):
    
    contour_counter = 0
    init_hue_upper = upper_HSV[0]
    init_hue_lower = lower_HSV[0]
    
    while contour_counter <= contour_threshold_lower or contour_counter >= contour_threshold_upper:
        
        processed_image, contours, upper_HSV, lower_HSV = tune_hue(image, upper_HSV, lower_HSV, min_shape_size, contour_threshold_upper, contour_threshold_lower)
        
        contour_counter = count_contours(contours, min_shape_size)
        
        if contour_counter >= contour_threshold_lower and contour_counter <= contour_threshold_upper:
            break
        
        # 1
        lower_HSV[1] = lower_HSV[1] - 5
        
        upper_HSV[0] = init_hue_upper
        lower_HSV[0] = init_hue_lower
        
        #print('SAT:' , lower_HSV[1])
        
        if lower_HSV[1] <= 45:
            break
    
    return(processed_image, contours, upper_HSV, lower_HSV)    

def find_shapes(image, upper_HSV, lower_HSV, contour_threshold_upper = 3, contour_threshold_lower = 1):
    
    contour_counter = 0
    min_shape_size = 700
      
    image = cv2.resize(image, (300, 300))
    image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    image = sharpen_image(image)
    
    init_sat_upper = upper_HSV[1]
    init_sat_lower = lower_HSV[1]
    
    while contour_counter <= contour_threshold_lower or contour_counter >= contour_threshold_upper:
        
        processed_image, contours, upper_HSV, lower_HSV = tune_sat(image, upper_HSV, lower_HSV, min_shape_size, contour_threshold_upper, contour_threshold_lower)
        
        contour_counter = count_contours(contours, min_shape_size)
        
        # 100
        min_shape_size = min_shape_size -200
        #print(min_shape_size)
        
        if contour_counter >= contour_threshold_lower and contour_counter <= contour_threshold_upper:
            break
        
        upper_HSV[1] = init_sat_upper
        lower_HSV[1] = init_sat_lower
        
        if min_shape_size < 50:
            print('No contours found')
            break
    
    return(processed_image, contours, upper_HSV, lower_HSV)

def find_the_plant(image):
    
    # Initial filter
    upper_HSV = np.array([50, 255, 255])
    lower_HSV = np.array([35, 50, 10]) 
    contour_threshold_upper = 6
    contour_threshold_lower = 1
    
    processed_image, contours, upper_HSV, lower_HSV = find_shapes(image, upper_HSV, lower_HSV, contour_threshold_upper, contour_threshold_lower)
    
    return(processed_image, contours, upper_HSV, lower_HSV)

def initialize_weights(model, filepath, X_train, X_test, y_train, y_test):
    early_stopping_monitor = EarlyStopping(patience=3)
    model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])
    model.fit(X_train, y_train, epochs=20, batch_size=64, validation_data=(X_test, y_test), callbacks=[early_stopping_monitor], verbose=False)
    model.save_weights(filepath)

############################################################################# 

# Main

# 1 Read and pre-process images

images = []
labels = []
filenames = []
n_contours = []

for class_folder_name in os.listdir(TRAIN_DATA_FOLDER):
    class_folder_path = os.path.join(TRAIN_DATA_FOLDER, class_folder_name)
    print(class_folder_name)
    for image_path in glob(os.path.join(class_folder_path, "*.png")):
        image = cv2.imread(image_path, cv2.IMREAD_COLOR)
        processed_image, contours, upper_HSV, lower_HSV = find_the_plant(image)
        #processed_image = cv2.cvtColor(processed_image, cv2.COLOR_BGR2GRAY)
        processed_image = cv2.resize(processed_image, (300,300))
        processed_image = processed_image.flatten()
        images.append(processed_image)
        labels.append(class_folder_name)
        filenames.append(os.path.basename(image_path))
        n_contours.append(len(contours))
        
images = np.array(images) 
labels = np.array(labels)
filenames = np.array(filenames)
n_contours = np.array(n_contours)
unique_labels = np.unique(labels)
images.shape
label_to_id_dict = {v:i for i, v in enumerate(np.unique(labels))}
label_ids = np.array([label_to_id_dict[x] for x in labels])

contour_summary(labels, filenames, n_contours)
# Model parameters

batch_size = 64
epochs = 50
num_classes = 12

# Load previously trained model

json_file = open('CNN_4block_2Dense_1_26_18.json', 'r')
loaded_CNN_json = json_file.read()
json_file.close()

X = StandardScaler().fit_transform(images)
X = X.reshape(-1,300,300,3)

y = to_categorical(label_ids)

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.1, random_state=42)

# Load forst 19 layers and weights
# CNN_model = model_from_json(loaded_CNN_json)
# CNN_model.load_weights('CNN_4block_2Dense_1_27_18_weights.h5', by_name=True)
# for i in range(5):
#     CNN_model.pop()

# # Fine-tune the final layers
# # CNN_model.add(Conv2D(256, (3,3), activation='linear'))
# # CNN_model.add(LeakyReLU(alpha=0.1))
# # CNN_model.add(Conv2D(256, (3,3), activation='linear', padding='same'))
# # CNN_model.add(LeakyReLU(alpha=0.1))
# # CNN_model.add(MaxPooling2D(pool_size=(2,2), padding='same'))
# # CNN_model.add(Dropout(0.4))

# CNN_model.add(Flatten())
# CNN_model.add(Dense(256, activation='relu'))
# CNN_model.add(Dropout(0.5))
# CNN_model.add(Dense(num_classes, activation='softmax'))
# len(CNN_model.layers)

# for l in CNN_model.layers[:28]:
#     l.trainable = False

# CNN_model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])

# early_stopping_monitor = EarlyStopping(patience=3)

# CNN_model.fit(X_train, y_train, epochs=epochs, batch_size=batch_size, callbacks=[early_stopping_monitor], validation_data=(X_test,y_test))

# score = CNN_model.evaluate(X_test,y_test, verbose=False)
 
# Create a new model for 300 X 300 X 3 images

model = Sequential()
model.add(Conv2D(32, kernel_size=(3,3), activation='linear', input_shape=(300,300,3)))
model.add(LeakyReLU(alpha=0.1))
model.add(MaxPooling2D(pool_size=(2,2), padding='same'))
model.add(Dropout(0.3))

model.add(Conv2D(64, (3,3), activation='linear', padding='same'))
model.add(LeakyReLU(alpha=0.1))
model.add(MaxPooling2D(pool_size=(2,2), padding='same'))
model.add(Dropout(0.3))

model.add(Conv2D(128, (3,3), activation='linear', padding='same'))
model.add(LeakyReLU(alpha=0.1))
model.add(MaxPooling2D(pool_size=(2,2), padding='same'))
model.add(Dropout(0.4))

model.add(Flatten())
model.add(Dense(128, activation='linear'))
model.add(LeakyReLU(alpha=0.1))
model.add(Dropout(0.4))
model.add(Dense(num_classes, activation='softmax'))

early_stopping_monitor = EarlyStopping(patience=3)

model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])
history = model.fit(X_train, y_train, epochs=epochs, batch_size=batch_size, callbacks=[early_stopping_monitor], validation_data=(X_test, y_test), verbose=True)
X_train[0].shape 

model.save('CNN_3block_300x300_1_28_18.h5')
model.save_weights('CNN_3block_300x300_1_28_18.h5')

model_json = model.to_json()
with open("CNN_3block_300x300_1_28_18.json", "w") as json_file:
    json_file.write(model_json)


#CNN_model_weights = CNN_model.load_weights('CNN_3block_1_22_18_weights.h5', by_name=True)

layer_dict = dict([(layer.name, layer) for layer in CNN_model.layers])

for key in layer_dict.keys():
    print(key)

# Plot validation / training accuracy and loss 
accuracy = history.history['acc']
val_accuracy = history.history['val_acc']
loss = history.history['loss']
val_loss = history.history['val_loss']
epochs = range(len(accuracy))
plt.plot(epochs, accuracy, 'bo', label='Training accuracy')
plt.plot(epochs, val_accuracy, 'b', label='Validation accuracy')
plt.title('Training and validation accuracy')
plt.legend()
plt.figure()
plt.plot(epochs, loss, 'bo', label='Train ing loss')
plt.plot(epochs, val_loss, 'b', label='Validation loss')
plt.title('Training and validation loss')
plt.legend()
plt.show()

   
#preds = model.predict(X)

# View samples

fig = plt.figure(figsize=(12,12))
fig.subplots_adjust(left=0, right=1, bottom=0, top=1, hspace=0.09, wspace=0.09)
#fig.suptitle('Lower HSV Params, Hue: {} Saturation: {} Value: {}'.format(lower_HSV[0], lower_HSV[1], lower_HSV[2]),  y=1.05, fontsize=14)

skip = 10

for class_folder_name, i in zip(os.listdir(TRAIN_DATA_FOLDER), range(12)):
    class_folder_path = os.path.join(TRAIN_DATA_FOLDER, class_folder_name)
    print(class_folder_name)
    for image_path, j in zip(glob(os.path.join(class_folder_path, "*.png")), range(5+skip)):
        image = cv2.imread(image_path, cv2.IMREAD_COLOR)
        if j > skip:
            image, contours, upper_HSV, lower_HSV = find_the_plant(image)
            #image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            image = image.flatten()
            ax = fig.add_subplot(12,5, (i*5 + j+1-skip), xticks=[], yticks=[])
            ax.imshow(np.reshape(image, (300,300, 3)))

fig.tight_layout()
plt.show()











