# encoding: UTF-8
# Copyright 2016 Google.com
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software

# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import tensorflow as tf
import time
import tensorflowvisu
from tensorflow.python.client import timeline
import math
import os
from tensorflow.contrib.learn.python.learn.datasets.mnist import read_data_sets
tf.set_random_seed(0)

# neural network with 1 layer of 10 softmax neurons
#
# · · · · · · · · · ·       (input data, flattened pixels)       X [batch, 784]        # 784 = 28 * 28
# \x/x\x/x\x/x\x/x\x/    -- fully connected layer (softmax)      W [784, 10]     b[10]
#   · · · · · · · ·                                              Y [batch, 10]

# The model is:
#
# Y = softmax( X * W + b)
#              X: matrix for 100 grayscale images of 28x28 pixels, flattened (there are 100 images in a mini-batch)
#              W: weight matrix with 784 lines and 10 columns
#              b: bias vector with 10 dimensions
#              +: add with broadcasting: adds the vector to each line of the matrix (numpy)
#              softmax(matrix) applies softmax on each line
#              softmax(line) applies an exp to each value then divides by the norm of the resulting line
#              Y: output matrix with 100 lines and 10 columns

# Download images and labels into mnist.test (10K images+labels) and mnist.train (60K images+labels)
mnist = read_data_sets(".", one_hot=True, reshape=False, validation_size=0)

# input X: 28x28 grayscale images, the first dimension (None) will index the images in the mini-batch
X = tf.placeholder(tf.float32, [None, 28, 28, 1])
# correct answers will go here
Y_ = tf.placeholder(tf.float32, [None, 10])
lr = tf.placeholder(tf.float32)
# weights W[784, 10]   784=28*28

W1 = tf.Variable(tf.truncated_normal([5, 5, 1, 6], stddev = 0.1))
B1 = tf.Variable(tf.ones([6])/10)
W2 = tf.Variable(tf.truncated_normal([5,5,6,16], stddev = 0.1))
B2 = tf.Variable(tf.ones([16])/10)
W3 = tf.Variable(tf.truncated_normal([400,120], stddev = 0.1))
B3 = tf.Variable(tf.ones([120])/10)
W4 = tf.Variable(tf.truncated_normal([120,84], stddev = 0.1))
B4 = tf.Variable(tf.ones([84])/10)
W5 = tf.Variable(tf.truncated_normal([84,10], stddev = 0.1))
B5 = tf.Variable(tf.ones([10])/10)

stride = 1
Y1 = tf.nn.conv2d(X, W1, strides=[1, stride, stride, 1], padding = 'SAME')
C1 = tf.nn.relu(Y1+B1)
S2 = tf.nn.max_pool(C1, ksize= [1,2,2,1], strides= [1,2,2,1],padding= 'SAME')
Y3 = tf.nn.conv2d(S2, W2, strides=[1, stride, stride, 1], padding = 'VALID')
C3 = tf.nn.relu(Y3+B2)
S4 = tf.nn.max_pool(C3, ksize= [1,2,2,1], strides= [1,2,2,1],padding= 'SAME')

fc1 = tf.reshape(S4, [-1, 400])
fc1 = tf.nn.relu(tf.matmul(fc1,W3)+B3)

fc2 = tf.nn.relu(tf.matmul(fc1,W4)+B4)
fc3 = tf.matmul(fc2,W5)+B5

Y = tf.nn.softmax(fc3)



# loss function: cross-entropy = - sum( Y_i * log(Yi) )
#                           Y: the computed output vector
#                           Y_: the desired output vector

# cross-entropy
# log takes the log of each element, * multiplies the tensors element by element
# reduce_mean will add all the components in the tensor
# so here we end up with the total cross-entropy for all images in the batch
cross_entropy = tf.nn.softmax_cross_entropy_with_logits(logits = fc3, labels = Y_)
cross_entropy = tf.reduce_mean(cross_entropy) * 16.0  # normalized for batches of 100 images,
                                                          # *10 because  "mean" included an unwanted division by 10

# accuracy of the trained model, between 0 (worst) and 1 (best)
correct_prediction = tf.equal(tf.argmax(Y, 1), tf.argmax(Y_, 1))
accuracy = tf.reduce_mean(tf.cast(correct_prediction, tf.float32))

# training, learning rate = 0.005
train_step = tf.train.AdamOptimizer(lr).minimize(cross_entropy)

# matplotlib visualisation
allweights = tf.reshape(W1, [-1])
allbiases = tf.reshape(B1, [-1])
It = tensorflowvisu.tf_format_mnist_images(X, Y, Y_, 1000, lines=25)  # 1000 images on 25 lines
datavis = tensorflowvisu.MnistDataVis()

# init
init = tf.global_variables_initializer()
sess = tf.Session()
sess.run(init)




# You can call this function in a loop to train the model, 100 images at a time
def training_step(i, update_test_data, update_train_data):
    batchSize = 128
    # training on batches of 100 images with 100 labels
    batch_X, batch_Y = mnist.train.next_batch(batchSize)

    lr_max = 0.005
    lr_min = 0.0003
    learning_rate = lr_min + (lr_max-lr_min)*math.exp(-i/2000.0)


    # compute training values for visualisation
    if update_train_data:
        run_options = tf.RunOptions(trace_level=tf.RunOptions.FULL_TRACE)
        run_metadata = tf.RunMetadata()
        a, c, w, b = sess.run([accuracy, cross_entropy,  allweights, allbiases], feed_dict={X: batch_X, Y_: batch_Y },options=run_options, run_metadata=run_metadata)
        tl = timeline.Timeline(run_metadata.step_stats)
        ctf = tl.generate_chrome_trace_format()
        with open('timeline.json', 'w') as f:
            f.write(ctf)
        datavis.append_training_curves_data(i, a, c)
        datavis.append_data_histograms(i, w, b)
        print(str(i) + ": accuracy:" + str(a) + " loss: " + str(c))

    # compute test values for visualisation
    if update_test_data:
        run_options = tf.RunOptions(trace_level=tf.RunOptions.FULL_TRACE)
        run_metadata = tf.RunMetadata()
        a, c, im = sess.run([accuracy, cross_entropy, It], feed_dict={X: mnist.test.images, Y_: mnist.test.labels },options=run_options, run_metadata=run_metadata)
        tl = timeline.Timeline(run_metadata.step_stats)
        ctf = tl.generate_chrome_trace_format()
        with open('timelin.json', 'w') as f:
            f.write(ctf)
        datavis.append_test_curves_data(i, a, c)
        datavis.update_image2(im)
        print(str(i) + ": ********* epoch " + str(i*batchSize//mnist.train.images.shape[0]+1) + " ********* test accuracy:" + str(a) + " test loss: " + str(c))

    # the backpropagation training step
    sess.run(train_step, feed_dict={X: batch_X, Y_: batch_Y, lr: learning_rate})


datavis.animate(training_step, iterations=975+1, train_data_update_freq=39, test_data_update_freq=39, more_tests_at_start=True,save_movie=True)

# to save the animation as a movie, add save_movie=True as an argument to datavis.animate
# to disable the visualisation use the following line instead of the datavis.animate line
#for i in range(2000+1): training_step(i, i % 50 == 0, i % 10 == 0)
print("max test accuracy: " + str(datavis.get_max_test_accuracy()))

time.sleep(50)
# final max test accuracy = 0.9268 (10K iterations). Accuracy should peak above 0.92 in the first 2000 iterations.
