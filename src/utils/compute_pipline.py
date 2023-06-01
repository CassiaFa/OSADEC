import os
from db_tools import Database
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.io import wavfile
import soundfile as sf

from pixlabel import Spectrogram, COCO_label
from matplotlib.patches import Rectangle

from PIL import Image

from tqdm import tqdm

# MMDET imports
import mmcv
from mmcv.runner import load_checkpoint

from mmdet.apis import inference_detector
from mmdet.models import build_detector

def detections2coco():

    img_path = "./data_anotated"
    
    if not os.path.exists(img_path):
        os.makedirs(img_path)

    img_id = 0
    annot_id = 0

    coco = COCO_label()

    # open database connexion
    Database.open_connexion()

    # Add categories to coco object
    for cat in Database.get_categories():
        coco.add_categorie(id=cat["id_species"], name=cat["english_name"])

    # Get files in database
    files = Database.get_files(id_file=None)

    for f in tqdm(files):
        
        timestamp_file = datetime.timestamp(f["date"])

        end_file = f["date"] + timedelta(seconds=f["duration"])

        # size of file loaded in seconds
        sec = 300
        spectro_time = timedelta(seconds=sec) # duration of spectro
        
        # spectro start and end
        spectro_start = f["date"]
        spectro_end = spectro_start + spectro_time

        while spectro_end <= end_file - spectro_time :

            time_min = spectro_start.strftime("%Y-%m-%d %H:%M:%S")
            time_max = spectro_end.strftime("%Y-%m-%d %H:%M:%S")

            detections = Database.get_detections(id_file=f["id_file"], time_min=time_min, time_max=time_max)

            # if no detection continue the loop
            if not detections:
                # spectro start and end
                spectro_start += spectro_time
                spectro_end += spectro_time
                continue
            else:

                # spectro start and end
                sample_start = int(datetime.timestamp(spectro_start) - timestamp_file) * f["fs"]
                sample_end =  int(datetime.timestamp(spectro_end) - timestamp_file) * f["fs"]
                
                # load sound file
                s, fs = sf.read(os.path.join('data',f["name"]), start=sample_start, stop=sample_end)

                # image name
                fn_split = f["name"].split("_")
                img_name = "_".join(fn_split[:4]) + "_" + spectro_start.strftime("%y%m%d_%H%M%S")  + ".png"

                nfft = 2048*2
                overlap = 90
                nwin = 2000 # nfft
                window = np.hamming(nwin)
                spectro = Spectrogram(s=s, fs=fs, img_name=img_name, nfft=nfft, win_size=nwin, overlap=overlap)

                # Add image to coco object
                coco.add_image(id=img_id, width=spectro.width, height=spectro.height, file_name=img_name)

                # save image
                spectro.save_img(path=img_path)

                for det in detections:

                    # duration of detection
                    # duration = det["stop"] - det["start"]
                    
                    # Frequency limit of signal
                    if det["id_species"] == 6:
                        # blue whale
                        fmin = 35 # 27
                        fmax= 150 # 75
                    elif det["id_species"] == 7:
                        # fine whale 
                        fmin = 40 # 35
                        fmax = 75 # 75
                    

                    duration = 5
                    det_start = (det["start"] - spectro_start).total_seconds() - 1


                    # compute coordinates of bounding box
                    x, y, w, h = spectro.get_coordinates(det_start, fmin, det_start + duration, fmax)

                    bbox = [x, y, w, h]

                    # test(x, y, w, h, os.path.join(img_path, img_name))

                    # Add annotation to coco object
                    coco.add_annotation(id=annot_id, img_id=img_id, cat_id=det["id_species"], bbox=bbox)
                    
                    annot_id += 1

                spectro.close()
                del spectro

                img_id += 1

            # spectro start and end
            spectro_start += spectro_time
            spectro_end += spectro_time

    Database.close_connexion()

    coco.save("DCLDE_2015.json", path=img_path)

    print("Task Done !")


def plot_image_bbox(x, y, w, h, img_name="test.png"):
    fig, ax = plt.subplots()

    rect = Rectangle((x,y), w, h, linewidth=2, edgecolor='r', facecolor='none')
    
    img = Image.open(img_name)
    plt.imshow(np.flipud(img), origin="lower")
    ax.add_patch(rect)
    plt.show()

def load_detector():
    """Function to detect objects in an image.
    
    Keyword arguments:
    img_path -- Path to the image.
    Return: result -- List of detected objects.
    """
    
    # Choose to use a config and initialize the detector
    config_file = '/home/fabio/Documents/fabito_bueno/mmdetection/configs/fabio_custom_config.py'

    # Setup a checkpoint file to load
    # checkpoint_file = './exp/exp1_paulobis/epoch_12.pth'
    checkpoint_file = '/home/fabio/Documents/fabito_bueno/mmdetection/exp/exp1/epoch_24/epoch_12.pth'

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

def compute_spectro(filepath, start, stop, fs, img_name, img_path):

    # load sound file
    s, fs = sf.read(filepath, start=start, stop=stop)

    nfft = 2048*2
    overlap = 90
    nwin = 2000
    window = np.hamming(nwin)
    spectro = Spectrogram(s=s, fs=fs, img_name=img_name, nfft=nfft, win_size=nwin, overlap=overlap)

    # Save temporary image
    spectro.save_img(path=img_path)

    return spectro

def get_results(result, spectro, detection, spectro_start):

    """Function to get the results of the detection.
    
    Keyword arguments:
    result -- List of detected objects.
    spectro -- Spectrogram object.
    detection -- List of detected objects.
    spectro_start -- Start time of spectrogram
    Return: detection -- List of detected objects.
    """

    for i in result:
        if i.shape[0] == 0:
            continue
        else:
            for d in i:
                x, y, x2, y2, confidence = d

                det_start, det_end, fmin, fmax = spectro.get_values(x, y, x2 - x, y2 - y)

                det_start, det_end =  spectro_start + timedelta(seconds=det_start), spectro_start + timedelta(seconds=det_end)

                detection.append(det_start, det_end, fmin, fmax, confidence)

    return detection


def pipeline(filepath, date, duration, fs):

    """Detection of call in wave files.
    
    Keyword arguments:
    filepath -- Path to the audio file.
    date -- Acquisition date of file.
    duration -- Duration of file.
    fs -- Sampling frequency of file.

    Return: None
    """
    
    model = load_detector()

    # Folder of temporary image
    i_path = "./tmp"
    # Name of temporary image
    img_name = "tmp.png"

    detection = []

    if not os.path.exists(filepath):
        print("File not found")
        return None
    
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
        sample_start = int(datetime.timestamp(spectro_start) - timestamp_file) * fs
        sample_end =  int(datetime.timestamp(spectro_end) - timestamp_file) * fs

        # Get the spectrogramme object
        spectro = compute_spectro(filepath, sample_start, sample_end, fs, img_name, i_path)

        img_path = os.path.join(i_path, img_name)

        
        result = inference_detector(model, img_path)

        date_start = datetime.fromtimestamp(spectro_start/fs + timestamp_file)

        detection = get_results(result, spectro, detection, date_start)

        # Close the spectro figure
        spectro.close()

        # Delete spectro variables
        del spectro

        # spectro start and end
        spectro_start += spectro_time
        spectro_end += spectro_time

    
    spectro_start = end_file - timedelta(seconds=sec)
    spectro_end = end_file

    spectro = compute_spectro(filepath, sample_start, sample_end, fs, img_name)

    img_path = os.path.join('tmp', img_name)
    
    result = inference_detector(model, img_path)

    date_start = datetime.fromtimestamp(spectro_start/fs + timestamp_file)
        
    detection = get_results(result, spectro, detection, date_start)

    # Close the spectro figure
    spectro.close()

    # Delete spectro variables
    del spectro

    if os.path.exists(img_path):
        os.remove(img_path)
    




def plot2Image(fig):
    import io
    from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
    from PIL import Image

    # Create a Matplotlib canvas
    canvas = FigureCanvas(fig)

    # Render the plot on the canvas
    canvas.draw()

    # Get the RGB buffer from the canvas
    buffer = canvas.buffer_rgba()

    # Convert the buffer to a read-only bytes-like object
    buffer = memoryview(buffer).toreadonly()

    # Determine the image mode based on the number of channels
    n_channels = len(buffer) // (canvas.get_width_height()[0] * canvas.get_width_height()[1])
    mode = "RGBA" if n_channels == 4 else "RGB"

    # Convert the buffer to a PIL image
    image = Image.frombuffer(mode, canvas.get_width_height(), buffer, 'raw', mode, 0, 1)

    # Save or display the PIL image as needed
    image.show()

    # image = Image.frombytes('RGB', canvas.get_width_height(), buffer, 'raw', 'RGBA', 0, 1)
    
    # test = Image.frombytes('RGB', fig.canvas.get_width_height(), fig.canvas.tostring_rgb())

    return image


if __name__ == "__main__":
    import re
    from datetime import datetime
    # detections2coco()

    filename = "/home/fabio/Documents/OSADEC/data/CINMS_17_B_d03_111202_012730.d100.x.wav"
    
    date =''.join(re.split('[_ .]',os.path.split(filename)[-1])[4:6])
    date = datetime.strptime('111202012730', '%y%m%d%H%M%S')

    f = sf.SoundFile(filename)

    fs = f.samplerate
    duration = f.frames / fs

    # detection(filename, date, duration, fs)



