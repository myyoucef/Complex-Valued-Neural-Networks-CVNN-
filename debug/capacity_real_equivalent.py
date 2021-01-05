import numpy as np
import cvnn.layers as layers
from time import sleep
from cvnn.layers import ComplexDense
from cvnn.real_equiv_tools import _get_real_equivalent_multiplier
from tensorflow.keras.models import Sequential
from tensorflow.keras.losses import categorical_crossentropy


def test_shape(input_size, output_size, shape_raw, classifier=True, capacity_equivalent=True, expected_result=None):
    shape = [
        layers.ComplexInput(input_shape=input_size, dtype=np.complex64)
    ]
    if len(shape_raw) == 0:
        print("No hidden layers are used. activation and dropout will be ignored")
        shape.append(
            ComplexDense(units=output_size, activation='softmax_real', dtype=np.complex64)
        )
    else:  # len(shape_raw) > 0:
        for s in shape_raw:
            shape.append(ComplexDense(units=s, activation='cart_relu'))  # Add dropout!
        shape.append(ComplexDense(units=output_size, activation='softmax_real'))

    complex_network = Sequential(shape, name="complex_network")
    complex_network.compile(optimizer='sgd', loss=categorical_crossentropy, metrics=['accuracy'])
    result = _get_real_equivalent_multiplier(complex_network.layers, classifier=classifier,
                                             capacity_equivalent=capacity_equivalent,
                                             equiv_technique='alternate')
    # rvnn = complex_network.get_real_equivalent(classifier, capacity_equivalent)
    # complex_network.training_param_summary()
    # rvnn.training_param_summary()
    if expected_result is not None:
        assert np.all(expected_result == result), f"Expecting result {expected_result} but got {result}."
    else:
        print(result)


if __name__ == '__main__':
    # test_shape(100, 2, [100, 30, 50, 40, 60, 50, 30], classifier=True)
    # sleep(2)
    # test_shape(100, 2, [100, 30, 50, 60, 50, 30], classifier=True)
    # sleep(2)
    # test_shape(100, 2, [100, 30, 50, 60, 50, 30], classifier=False)
    # sleep(2)
    # test_shape(100, 2, [100, 30, 50, 40, 60, 50, 30], classifier=False)
    # sleep(2)
    # test_shape(100, 2, [100, 30, 50, 40, 60, 50, 30], capacity_equivalent=False)
    test_shape(100, 2, [], expected_result=[1])
    sleep(2)
    test_shape(100, 2, [64], expected_result=[2, 1])
    sleep(2)
    test_shape(100, 2, [100, 64], expected_result=[1, 2, 1])
    sleep(2)
    test_shape(100, 2, [100, 30, 64], expected_result=[1, 2, 2, 1])
    sleep(2)
    test_shape(100, 2, [100, 30, 40, 50], expected_result=[1, 2, 1, 2, 1])
    sleep(2)
    test_shape(100, 2, [100, 30, 40, 60, 30], expected_result=[1, 2, 2, 1, 2, 1])
    sleep(2)
    test_shape(100, 2, [100, 30, 40, 60, 50, 30], expected_result=[1, 2, 1, 2, 1, 2, 1])
    sleep(2)
    test_shape(100, 2, [100, 30, 40, 60, 50, 30, 60], expected_result=[1, 2, 1, 2, 2, 1, 2, 1])

    # Not capacity equivalent
    sleep(2)
    test_shape(100, 2, [], capacity_equivalent=False, expected_result=[1])
    sleep(2)
    test_shape(100, 2, [64], capacity_equivalent=False, expected_result=[2, 1])
    sleep(2)
    test_shape(100, 2, [100, 64], capacity_equivalent=False, expected_result=[2, 2, 1])
    sleep(2)
    test_shape(100, 2, [100, 30, 64], capacity_equivalent=False, expected_result=[2, 2, 2, 1])
    sleep(2)
    test_shape(100, 2, [100, 30, 40, 50], capacity_equivalent=False, expected_result=[2, 2, 2, 2, 1])
    sleep(2)
    test_shape(100, 2, [100, 30, 40, 60, 50, 30], capacity_equivalent=False, expected_result=[2, 2, 2, 2, 2, 2, 1])
    sleep(2)
    test_shape(100, 2, [100, 30, 40, 60, 50, 30], classifier=False, capacity_equivalent=False,
               expected_result=[2, 2, 2, 2, 2, 2, 2])
    # sleep(2)
    # test_shape(100, 2, [100, 30, 40, 60, 50, 30], classifier=False)
