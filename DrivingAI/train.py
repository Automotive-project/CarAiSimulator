from timeit import default_timer as timer
import tensorflow as tf
import numpy as np
from model import Session, get_network
from communication import Driver
from data import IMAGE_DEPTH, IMAGE_HEIGHT, IMAGE_WIDTH, VARIABLE_COUNT, score_buffer, get_shuffle_batch


def get_input(driver, session, neta, netb, tensor_img, tensor_vars, tensor_out, tensor_weights, tensor_examples, buffer=None, array=None):
    if buffer is None:
        buffer = score_buffer()
    if array is None:
        array = []
    def fill_buffer(output):
        print("Filling the reinforcement buffer...     ", end='\r')
        while buffer.get_num_scored() < 200:
            x, v, y, s = driver.get_status()
            y = session.run(output, feed_dict={ tensor_examples: 0, tensor_img: [x], tensor_vars: [v] })
            y1 = y[0][0]
            y2 = y[0][1]
            if np.random.uniform() < 0.1:
                y1 = np.clip(y1 + np.random.normal(0, 0.3), -1, 1)
                y2 = np.clip(y2 + np.random.normal(0, 0.3), -1, 1)
            driver.set_action(y1, y2)
            buffer.add_item(x, v, [y1, y2], score=s)
        for i in buffer.get_items():
            array.append(i)
            array.append(i)
    for _ in range(5):
        fill_buffer(neta.output)
        fill_buffer(netb.output)
    for i in buffer.clear_buffer():
        array.append(i)
        array.append(i)
    np.random.shuffle(array)
    return array

def get_batch_feed(array, tensor_img, tensor_vars, tensor_output, tensor_weights, tensor_examples, batch=32, example_count=8):
    x = []
    v = []
    y = []
    s = []
    for _ in range(batch-example_count):
        x_, v_, y_, s_ = array.pop()
        x.append(x_)
        v.append(v_)
        y.append(y_)
        s.append(s_)
    return { tensor_img: x, tensor_vars: v, tensor_output: y, tensor_weights: s, tensor_examples: example_count }

def create_placeholders():
    #placeholders
    xp = tf.placeholder(tf.float32, None, "image")
    vp = tf.placeholder(tf.float32, None, "variables")
    yp = tf.placeholder(tf.float32, None, "steering")
    sp = tf.placeholder(tf.float32, None, "weights")
    batch = tf.placeholder(tf.int32, None, "example_size")
    #reshapes
    xs = tf.reshape(xp, [-1, IMAGE_WIDTH, IMAGE_HEIGHT, IMAGE_DEPTH])
    vs = tf.reshape(vp, [-1, VARIABLE_COUNT])
    ys = tf.reshape(yp, [-1, 2])
    ss = tf.reshape(sp, [-1, 1])
    #examples
    xe, ve, ye, se = get_shuffle_batch(batch, capacity=2000)
    #combines
    xc = tf.concat((xs, xe), 0)
    vc = tf.concat((vs, ve), 0)
    yc = tf.concat((ys, ye), 0)
    sc = tf.concat((ss, se), 0)
    return xp, vp, yp, sp, batch, xs, vs, ys, ss


def train(iterations=80000, summary_interval=100, batch=32):
    tf.logging.set_verbosity(tf.logging.INFO)
    with Driver() as driver:
        placeholders = create_placeholders()
        global_step, network_a, network_b = get_network(*placeholders[-4:], True)
        with Session(True, True, global_step) as sess:
            try:
                last_save = timer()
                buffer = score_buffer()
                array = []
                step = 1
                time = 1
                for _ in range(iterations):
                    if len(array) < batch*2:
                        get_input(driver, sess.session, network_a, network_b, *placeholders[:5], buffer, array)
                    pre = timer()
                    fd = get_batch_feed(array, *placeholders[:5], batch)
                    _, aloss, step = sess.session.run([network_a.trainer, network_a.loss, global_step], feed_dict=fd)
                    fd = get_batch_feed(array, *placeholders[:5], batch)
                    _, bloss = sess.session.run([network_b.trainer, network_b.loss], feed_dict=fd)
                    if step%summary_interval == 0:
                        print()
                    time = 0.9*time + 0.1 *(timer()-pre)
                    if step%10 == 0:
                        print("Training step: %i, Loss A: %.3f, Loss B: %.3f (%.2f s)  "%(step, aloss, bloss, time), end='\r')
                    if timer() - last_save > 1800:
                        sess.save_network()
                        last_save = timer()
            except (KeyboardInterrupt, StopIteration):
                print("\nStopping the training")


if __name__ == "__main__":
    train()