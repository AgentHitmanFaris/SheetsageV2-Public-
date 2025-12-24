import sys
try:
    import numpy
    print(f"NumPy Version: {numpy.__version__}")
    
    import tensorflow
    print(f"TensorFlow Version: {tensorflow.__version__}")
    
    from basic_pitch.inference import predict_and_save
    print("Basic Pitch imported successfully.")
    
except Exception as e:
    print(f"Import Failed: {e}")
    sys.exit(1)
