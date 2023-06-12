import os
import errno
import re

from datetime import datetime, timedelta
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import soundfile as sf
import librosa

from .db_tools import Database
from .pixlabel import Spectrogram

from PIL import Image

# MMDET imports
import mmcv
from mmcv.runner import load_checkpoint
from mmdet.apis import inference_detector
from mmdet.models import build_detector


def plot_image_bbox(x, y, w, h, img_path):
    
    """
    Plots an image with a bounding box overlayed on top of it.

    Args:
        x (int): The x-coordinate of the top-left corner of the bounding box.
        y (int): The y-coordinate of the top-left corner of the bounding box.
        w (int): The width of the bounding box.
        h (int): The height of the bounding box.
        img_path (str): The name of the image file to display.

    Returns:
        None

    Example:
        >>> plot_image_bbox(1872.808, 444.459, 38.615, 164.912, "example/example.png")

    """
     
    fig, ax = plt.subplots()

    rect = Rectangle((x,y), w, h, linewidth=2, edgecolor='r', facecolor='none')
    
    img = Image.open(img_path)
    plt.imshow(np.flipud(img), origin="lower")
    ax.add_patch(rect)
    plt.show()

def load_detector(config_path=None, checkpoint_path=None):
    """
    Loads the object detector from the specified config and checkpoint.
    
    Args:
        config_path : (str) Path to the config file. By default, it is set to None.
        checkpoint_path : (str) Path to the checkpoint file. By default, it is set to None.
    Returns:
        model : (torch.nn.Module) The loaded model

    Example:
        >>> config_path = "../../models/lowfreq_faster-rcnn_config.py"
        >>> checkpoint_path = "../../models/latest_lowfreq_faster-rcnn.pth"
        >>> model = load_detector(config_path, checkpoint_path)
        >>> assert isinstance(model, mmdet.models.detectors.faster_rcnn.FasterRCNN)

    """

    # Config path
    if not config_path:
        config_file = "models/lowfreq_faster-rcnn_config.py"
    else:
        config_file = config_path

    # Checkpoint path
    if not checkpoint_path:
        checkpoint_file = "models/latest_lowfreq_faster-rcnn.pth"
    else:
        checkpoint_file = checkpoint_path

    # Set the device to be used for evaluation
    device='cpu'

    # Load the config
    config = mmcv.Config.fromfile(config_file)
    # Set pretrained to be None since we do not need pretrained model here
    config.model.pretrained = None
    config.model.roi_head.bbox_head.num_classes = 2 # <- ligne a rajouter sinon la taille mismatch et ton modele crash je pense

    # Initialize the detector
    model = build_detector(config.model)

    # Load checkpoint
    checkpoint = load_checkpoint(model, checkpoint_file, map_location=device)

    # Set the classes of models for inference
    model.CLASSES = checkpoint['meta']['CLASSES']

    # We need to set the model's cfg for inference
    model.cfg = config

    # Convert the model to GPU
    model.to(device)
    # Convert the model into evaluation mode
    model.eval()

    return model

def compute_spectro(filepath, start, stop, fs, img_name, path):
    
    """
    Computes the spectrogram of the sound file given by `filepath`, from `start` to `stop` seconds, 
    with a sampling rate of `fs` Hz, and saves the resulting image with name `img_name` at `img_path`.

    Args:
        filepath: A string representing the path to the sound file to compute the spectrogram from.
        start: A float representing the starting time (in seconds) from which to compute the spectrogram.
        stop: A float representing the stopping time (in seconds) until which to compute the spectrogram.
        fs: An integer representing the sampling rate (in Hz) of the sound file.
        img_name: A string representing the name of the image file to save the spectrogram to.
        img_path: A string representing the path to save the image file to.

    Returns:
        A Spectrogram object representing the spectrogram of the sound file.

    Example:
        >>> import os
        >>> from pixlabel import Spectrogram
        >>> img_path = "./example"
        >>> img_name = "spectrogram.png"
        >>> spectro = compute_spectro('example.wav', 0, 300, 44100, img_name, img_path)
        >>> assert os.path.exists(img_path)
        >>> assert isinstance(spectro, Spectrogram)

    """

    # load sound file
    s, fs = librosa.load(filepath, sr=2000, offset=start, duration=stop-start)
    # s, fs = sf.read(filepath, start=start, stop=stop)

    spectro = Spectrogram(s=s, fs=fs, img_name=img_name)

    # Path to the image
    img_path = os.path.join(path, img_name)

    # Save temporary image
    spectro.save_img(path=img_path)

    return spectro

def get_results(result, spectro, detection, spectro_start, class_names):

    """
    Function to check and get the results of the detection.
    
    Args:
        result : (list) List of numpy arrays representing the results of the detection.
        spectro : (Spectrogram) Spectrogram object.
        detection : (list) List of detected objects.
        spectro_start : (datetime) Start time of spectrogram.

    Returns:
        detection : (list) List of detected objects.

    Example:
        >>> import numpy as np
        >>> from pixlabel import Spectrogram
        >>> detection = []
        >>> spectro_start = 0
        >>> result = [np.array([[1,2,3,4,5],[6,7,8,9,10]]), np.array([[1,2,3,4,5],[6,7,8,9,10]])]
        >>> spectro = Spectrogram(s=np.array([[1,2,3,4,5],[6,7,8,9,10]]), fs=44100, img_name="spectrogram.png")
        >>> detection = get_results(result, spectro, detection, spectro_start)

    """

    for i, name in enumerate(class_names):

        # Database.open_connexion()

        # Get the id of the class
        id_class = Database.get_categories(english_name=name)["id_species"]

        # Database.close_connexion()

        if result[i].shape[0] == 0:
            continue
        else:
            for d in result[i]:
                x, y, x2, y2, confidence = d

                det_start, det_end, fmin, fmax = spectro.get_values(x, y, x2 - x, y2 - y)

                det_start, det_end =  spectro_start + timedelta(seconds=det_start), spectro_start + timedelta(seconds=det_end)

                event = {
                    "id_species": id_class,
                    "start": datetime.strftime(det_start, "%Y-%m-%d %H:%M:%S"),
                    "end": datetime.strftime(det_end, "%Y-%m-%d %H:%M:%S"),
                    "fmin": fmin,
                    "fmax:": fmax,
                    "confidence": confidence
                }

                detection.append(event)

    return detection


def pipeline(filepath: str, date: datetime, duration: int, fs: int):
    """
    Runs a pipeline to detect objects in a spectrogram generated from a given audio file.

    Args:
        filepath: A string representing the path to the audio file.
        date: A datetime object representing the start time of the audio file.
        duration: An integer representing the duration of the audio file in seconds.
        fs: An integer representing the frequency of the audio file.

    Returns:
        A list of dictionaries, where each dictionary corresponds to a detected object and contains the following keys:
        - "class": the class of the object
        - "score": the confidence score of the detection
        - "bbox": the bounding box coordinates of the detection

    Raises:
        FileNotFoundError: If the file at the given filepath does not exist.

    Example:
        >>> filepath = "path/to/audio/file.wav"
        >>> date = datetime(2022, 1, 1, 0, 0, 0)
        >>> duration = 3600
        >>> fs = 44100
        >>> results = pipeline(filepath, date, duration, fs)
    """

    model = load_detector()

    # Folder of temporary image
    i_path = "./tmp"

    # Check if folder exists
    if not os.path.exists(i_path):
        os.makedirs(i_path)

    # Name of temporary image
    img_name = "tmp.png"

    img_path = os.path.join(i_path, img_name)

    detection = []

    if not os.path.exists(filepath):
        raise  FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), filepath)
    
    # timestamp of file
    timestamp_file = datetime.timestamp(date)

    # end date of file
    end_file = date + timedelta(seconds=duration)

    # size of file loaded in seconds
    sec = 300
    spectro_time = timedelta(seconds=sec) # duration of spectro

    # spectro start
    spectro_start = date

    # spectro end
    spectro_end = spectro_start + timedelta(seconds=sec)

    while spectro_end < end_file:
        
        # spectro start and end
        sample_start = int(datetime.timestamp(spectro_start) - timestamp_file)
        sample_end =  int(datetime.timestamp(spectro_end) - timestamp_file)

        # Get the spectrogramme object
        spectro = compute_spectro(filepath, sample_start, sample_end, fs, img_name, i_path)
        
        result = inference_detector(model, img_path)

        detection = get_results(result, spectro, detection, spectro_start, model.CLASSES)

        # Close the spectro figure
        spectro.close()

        # Delete spectro variables
        del spectro

        # spectro start and end
        spectro_start += spectro_time
        spectro_end += spectro_time

    
    spectro_start = end_file - timedelta(seconds=sec)
    spectro_end = end_file

    # spectro start and end
    sample_start = int(datetime.timestamp(spectro_start) - timestamp_file)
    sample_end =  int(datetime.timestamp(spectro_end) - timestamp_file)

    spectro = compute_spectro(filepath, sample_start, sample_end, fs, img_name, i_path)
    
    result = inference_detector(model, img_path)
        
    detection = get_results(result, spectro, detection, spectro_start, model.CLASSES)

    # Close the spectro figure
    spectro.close()

    # Delete spectro variables
    del spectro

    if os.path.exists(img_path):
        os.remove(img_path)

    return detection



if __name__ == "__main__":

    import tkinter
    import doctest
    import mmdet
    import matplotlib
    matplotlib.use('TkAgg')

    # doctest.testmod()

    filename = "./example/test_230603_175500.wav"
    
    # date =''.join(re.split('[_ .]',os.path.split(filename)[-1])[4:6])
    date = datetime.strptime('111202012730', '%y%m%d%H%M%S')

    f = sf.SoundFile(filename)

    fs = f.samplerate
    duration = f.frames / fs

    results = pipeline(filename, date, duration, fs)



