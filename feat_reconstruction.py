import os
import numpy as np

from keras import backend as K

from vgg16.model import VGG_16_mean 
from vgg16.model_headless import *

from utils.imutils import *
from utils.lossutils import *
from utils.optimizers import adam

dir = os.path.dirname(os.path.realpath(__file__))
vgg16Dir = dir + '/vgg16'
resultsDir = dir + '/models/results/vgg16'
if not os.path.isdir(resultsDir): 
    os.makedirs(resultsDir)
dataDir = dir + '/data'

print('Loading a cat image')
X_train = load_image(dataDir + '/overfit/000.jpg')
print("X_train shape:", X_train.shape)

print('Loading Van Gogh')
vanGoghPath = dataDir + '/paintings/vangogh.jpg'
X_train_paint = np.array([load_image(vanGoghPath)])
print("X_train_paint shape:", X_train_paint.shape)

print('Loading mean')
meanPath = vgg16Dir + '/vgg-16_mean.npy'
mean = VGG_16_mean(path=meanPath)

print('Loading VGG headless 5')
modelWeights = vgg16Dir + '/vgg-16_headless_5_weights.hdf5'
model = VGG_16_headless_5(modelWeights, trainable=False)
layer_dict = dict([(layer.name, layer) for layer in model.layers])
input_img = layer_dict['input'].input

print('Building white noise images')
input_style_data = create_noise_tensor(3, 256, 256)
input_feat_data = create_noise_tensor(3, 256, 256)

layers_names = reversed([l for l in layer_dict if len(re.findall('conv_', l))])
current_iter = 1
for layer_name in layers_names:
    print('Creating labels for ' + layer_name)
    out = layer_dict[layer_name].output
    predict = K.function([input_img], [out])

    out_plabels = predict([X_train_paint - mean])
    out_ilabels = predict([X_train - mean])

    print('Compiling VGG headless 1 for ' + layer_name + ' style reconstruction')
    loss_style = grams_frobenius_error(out_plabels[0], out)
    grads_style = K.gradients(loss_style, input_img)[0]
    grads_style /= (K.sqrt(K.mean(K.square(grads_style))) + 1e-5)
    iterate_style = K.function([input_img], [loss_style, grads_style])

    print('Compiling VGG headless 1 for ' + layer_name + ' feature reconstruction')
    loss_feat = euclidian_error(out_ilabels[0], out)
    grads_feat = K.gradients(loss_feat, input_img)[0]
    grads_feat /= (K.sqrt(K.mean(K.square(grads_feat))) + 1e-5)
    iterate_feat = K.function([input_img], [loss_feat, grads_feat])

    prefix = str(current_iter).zfill(4)

    print('Training the image for style')
    config = {'learning_rate': 1e-00}
    best_input_style_data = train_on_input(input_style_data - mean, iterate_style, adam, config)
    best_input_style_data += mean
    fullOutPath = resultsDir + '/' + prefix + '_style_' + layer_name + ".png"
    deprocess_image(best_input_style_data[0], fullOutPath)

    print('Training the image for feature')
    config = {'learning_rate': 1e-00}
    best_input_feat_data = train_on_input(input_feat_data - mean, iterate_feat, adam, config)
    best_input_feat_data += mean
    fullOutPath = resultsDir + '/' + prefix + '_feat_' + layer_name + ".png"
    deprocess_image(best_input_feat_data[0], fullOutPath)

    current_iter += 1
