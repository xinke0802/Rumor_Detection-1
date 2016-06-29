# -*- encoding: utf-8 -*-
# author: Qiaoan Chen <kazenoyumechen@gmail.com>

import tensorflow as tf

MOMENTUM = 0.9
MOVING_AVG_RATE = 0.999


def train(loss, global_step, decay_steps,
          initial_learning_rate=0.01, decay_rate=0.1,
          max_gradient_norm=None):
    # create learning rate
    lr = tf.train.exponential_decay(
        learning_rate=initial_learning_rate,
        global_step=global_step,
        decay_steps=decay_steps,
        decay_rate=decay_rate,
        staircase=True
    )
    tf.scalar_summary('learning rate', lr)

    # compute and apply gradients
    opt = tf.train.MomentumOptimizer(lr, MOMENTUM)
    gradvars = opt.compute_gradients(loss)
    if max_gradient_norm:
        gradvars = [(tf.clip_by_norm(gv[0], max_gradient_norm), gv[1])
                    for gv in gradvars]
    apply_grads = opt.apply_gradients(gradvars, global_step)

    # add histograms for variables and gradients
    for var in tf.trainable_variables():
        tf.histogram_summary(var.op.name, var)

    for grad, var in gradvars:
        if grad is not None:
            tf.histogram_summary(var.op.name + '/gradient', grad)

    # smoothing loss and variables
    ema = tf.train.ExponentialMovingAverage(MOVING_AVG_RATE, global_step)
    ema_op = ema.apply(tf.trainable_variables() + [loss])
    tf.scalar_summary('moving_loss', ema.average(loss))

    # combine all op into a train_op
    with tf.control_dependencies([apply_grads]):
        train_op = tf.group(ema_op, name='train')

    return train_op


def loss(logits, y):
    cross_ent = tf.nn.sparse_softmax_cross_entropy_with_logits(
        logits=logits,
        labels=y
    )
    cross_ent_mean = tf.reduce_mean(cross_ent, name='empirical_loss')
    reg_losses = tf.get_collection(tf.GraphKeys.REGULARIZATION_LOSSES)
    loss_op = tf.add_n(reg_losses + [cross_ent_mean], "loss")

    tf.scalar_summary('empirical loss', cross_ent_mean)
    tf.scalar_summary('loss', loss_op)

    return loss_op


def accuracy(logits, y):
    correct = tf.nn.in_top_k(logits, y, 1)
    correct_mean = tf.reduce_mean(tf.cast(correct, tf.float32))
    tf.scalar_summary('accuracy', correct_mean)
    return correct_mean


def predict(logits):
    return tf.nn.softmax(logits)