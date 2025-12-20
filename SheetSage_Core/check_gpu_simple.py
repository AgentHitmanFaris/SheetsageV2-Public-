import tensorflow as tf
print("Num GPUs Available: ", len(tf.config.list_physical_devices('GPU')))
try:
    print(tf.config.list_physical_devices('GPU'))
except:
    pass
