import os
import tensorflow as tf
from keras.optimizers.optimizer_v2 import adam as adam_v2
from keras.layers import Input, Conv2D, BatchNormalization, Activation, MaxPooling2D, Conv2DTranspose, concatenate, Reshape, Permute, Bidirectional, LSTM
from keras.callbacks import EarlyStopping, ModelCheckpoint
from keras import losses
from keras.models import Model

from sklearn.model_selection import train_test_split
from utils import *

os.environ['CUDA_VISIBLE_DEVICES'] = '0'
tf.compat.v1.enable_eager_execution()

gpus = tf.config.experimental.list_physical_devices('GPU')
if gpus:
    try:
        tf.config.experimental.set_virtual_device_configuration(gpus[0], [tf.config.experimental.VirtualDeviceConfiguration(memory_limit=19000)])
    except RuntimeError as e:
        print(e)


def cnn_sqd_lstm_model():
    """
    Defines the joint convolutional and spatial quad-directional LSTM network
    """

    # input to the network
    input = Input((512, 512, 1))  # Input size changed to 512x512

    # encoder network
    c1 = Conv2D(filters=16, kernel_size=(3,3), kernel_initializer='he_normal', padding='same')(input)
    c1 = BatchNormalization()(c1)
    c1 = Activation('relu')(c1)
    p1 = MaxPooling2D()(c1)
    #p1 = AveragePooling2D()(c1)

    c2 = Conv2D(filters=32, kernel_size=(3,3), kernel_initializer='he_normal', padding='same')(p1)
    c2 = BatchNormalization()(c2)
    c2 = Activation('relu')(c2)
    p2 = MaxPooling2D()(c2)
    #p2 = AveragePooling2D()(c2)

    c3 = Conv2D(filters=64, kernel_size=(3,3), kernel_initializer='he_normal', padding='same')(p2)
    c3 = BatchNormalization()(c3)
    c3 = Activation('relu')(c3)
    p3 = MaxPooling2D()(c3)
    #p3 = AveragePooling2D()(c3)

    c4 = Conv2D(filters=128, kernel_size=(3,3), kernel_initializer='he_normal', padding='same')(p3)
    c4 = BatchNormalization()(c4)
    c4 = Activation('relu')(c4)
    p4 = MaxPooling2D()(c4)
    #p4 = AveragePooling2D()(c4)

    c5 = Conv2D(filters=256, kernel_size=(3,3), kernel_initializer='he_normal', padding='same')(p4)
    c5 = BatchNormalization()(c5)
    c5 = Activation('relu')(c5)
    p5 = MaxPooling2D()(c5)
    #p5 = AveragePooling2D()(c5)

    c6 = Conv2D(filters=512, kernel_size=(3,3), kernel_initializer='he_normal', padding='same')(p5)
    c6 = BatchNormalization()(c6)
    c6 = Activation('relu')(c6)
    p6 = MaxPooling2D()(c6)
    #p6 = AveragePooling2D()(c6)


    # SQD-LSTM Block
    x_hor_1 = Reshape((8 * 8, 512))(p6)
    x_ver_1 = Reshape((8 * 8, 512))(Permute((2, 1, 3))(p6))

    h_hor_1 = Bidirectional(LSTM(units=128, activation='tanh', return_sequences=True, go_backwards=False))(x_hor_1)
    h_ver_1 = Bidirectional(LSTM(units=128, activation='tanh', return_sequences=True, go_backwards=False))(x_ver_1)

    H_hor_1 = Reshape((8, 8, 256))(h_hor_1)
    H_ver_1 = Permute((2, 1, 3))(Reshape((8, 8, 256))(h_ver_1))

    c_hor_1 = Conv2D(filters=64, kernel_size=(3, 3),
                     kernel_initializer='he_normal', padding='same')(H_hor_1)
    c_ver_1 = Conv2D(filters=64, kernel_size=(3, 3),
                     kernel_initializer='he_normal', padding='same')(H_ver_1)

    H = concatenate([c_hor_1, c_ver_1])

    # decoder network
    u7 = Conv2DTranspose(512, (3, 3), strides=(2, 2), padding='same')(H)
    u7 = concatenate([u7, c6])
    c7 = Conv2D(filters=512, kernel_size=(3,3), kernel_initializer='he_normal', padding='same')(u7)
    c7 = BatchNormalization()(c7)
    c7 = Activation('relu')(c7)

    u8 = Conv2DTranspose(256, (3, 3), strides=(2, 2), padding='same')(c7)
    u8 = concatenate([u8, c5])
    c8 = Conv2D(filters=256, kernel_size=(3,3), kernel_initializer='he_normal', padding='same')(u8)
    c8 = BatchNormalization()(c8)
    c8 = Activation('relu')(c8)

    u9 = Conv2DTranspose(128, (3, 3), strides=(2, 2), padding='same')(c8)
    u9 = concatenate([u9, c4])
    c9 = Conv2D(filters=128, kernel_size=(3,3), kernel_initializer='he_normal', padding='same')(u9)
    c9 = BatchNormalization()(c9)
    c9 = Activation('relu')(c9)

    u10 = Conv2DTranspose(64, (3, 3), strides=(2, 2), padding='same')(c9)
    u10 = concatenate([u10, c3])
    c10 = Conv2D(filters=64, kernel_size=(3,3), kernel_initializer='he_normal', padding='same')(u10)
    c10 = BatchNormalization()(c10)
    c10 = Activation('relu')(c10)

    u11 = Conv2DTranspose(32, (3, 3), strides=(2, 2), padding='same')(c10)
    u11 = concatenate([u11, c2])
    c11 = Conv2D(filters=32, kernel_size=(3,3), kernel_initializer='he_normal', padding='same')(u11)
    c11 = BatchNormalization()(c11)
    c11 = Activation('relu')(c11)

    u12 = Conv2DTranspose(16, (3, 3), strides=(2, 2), padding='same')(c11)
    u12 = concatenate([u12, c1])
    c12 = Conv2D(filters=16, kernel_size=(3,3), kernel_initializer='he_normal', padding='same')(u12)
    #c12 = Conv2D(filters=32, kernel_size=(3,3), kernel_initializer='he_normal', padding='same')(u12)
    c12 = BatchNormalization()(c12)
    c12 = Activation('relu')(c12)

    ## output layer
    output = Conv2D(filters=1, kernel_size=(1, 1), padding='same', name='out1')(c12)
    output = Activation('linear')(output)

    model = Model(inputs=[input], outputs=[output])

    return model

def model_train_setup():
    model = cnn_sqd_lstm_model() # load neural network layer
    model.summary() # print out summary

    # compile model
    model.compile(
        optimizer=adam_v2.Adam(learning_rate=1e-3),
        loss=losses.mean_squared_error
    )

    return model

def model_train(model_filepath: str):
    earlystopper = EarlyStopping(
        monitor='loss',
        patience=5000,
        verbose=1
    )

    model_checkpoint = ModelCheckpoint(
        filepath=model_filepath,
        monitor='val_loss',  # Use validation loss for saving the best model
        verbose=1,
        save_best_only=True
    )

    history = model.fit(
        x=X_train.reshape(X_train.shape[0], 512, 512, 1),
        y=Y_train.reshape(Y_train.shape[0], 512, 512, 1),
        batch_size=6,
        epochs=500, #20000
        verbose=True,
        validation_data=(X_val.reshape(X_val.shape[0], 512, 512, 1), Y_val.reshape(Y_val.shape[0], 512, 512, 1)),
        callbacks=[model_checkpoint, earlystopper]
    )

    return history

def training_data(data_folder: str, input_filename: str, output_filename: str):
    # TODO: 1000 dataset splitted into Train:Validation:Test = 8:1:1

    X, Y = img_loader(data_folder, input_filename, output_filename)

    # Split the data into train, validation, and test sets
    X_train, X_temp, Y_train, Y_temp = train_test_split(X, Y, test_size=0.1, random_state=42)
    X_val, X_test, Y_val, Y_test = train_test_split(X_temp, Y_temp, test_size=0.1, random_state=42)

    return X_train, X_val, X_test, Y_train, Y_val, Y_test

if __name__ == '__main__':
    '''
    Dataset Info
    Raw (0-2pi)
    - (1) Vertical: img_9.png
    - (2) Horizontal: img_10.png
    Normalized (0-255)
    - (1) Vertical: img_9_norm.png
    - (2) Horizontal: img_10_norm.png
    '''

    # load img data
    data_folder = './dl_data_set/dl_deflec_eye/'
    input_filename = 'img_8.png'
    output_filename = 'img_10.png'
    X_train, X_val, X_test, Y_train, Y_val, Y_test = training_data(data_folder, input_filename, output_filename)

    model = model_train_setup() # create and load the model

    model_filepath = './model/horizontal_raw.h5'
    model_history = model_train(model_filepath)

    # Evaluate on the test set
    test_score = model.evaluate(X_test.reshape(X_test.shape[0], 512, 512, 1), Y_test.reshape(Y_test.shape[0], 512, 512, 1), batch_size=6)
    print(f'Test Loss: {test_score}')