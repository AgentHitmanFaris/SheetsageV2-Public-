class Representation:
    """
    Base class for audio representations.
    """
    def __call__(self, audio_path, offset=0.0, duration=None):
        """
        Extracts features from an audio file.

        Args:
            audio_path (str or pathlib.Path): Path to the audio file.
            offset (float): Start time in seconds.
            duration (float, optional): Duration to extract in seconds.

        Returns:
            tuple: (frame_rate (float), features (np.ndarray))

        Raises:
            NotImplementedError: Must be implemented by subclasses.
        """
        # NOTE: Should return tuple containing (rate: float, features: np.ndarray)
        raise NotImplementedError()
