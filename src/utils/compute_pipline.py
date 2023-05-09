import os
from src.utils import Database
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.io import wavfile
import soundfile as sf

from src.utils.pixlabel import Spectrogram, COCO_label
from matplotlib.patches import Rectangle

from PIL import Image

from tqdm import tqdm

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

    for f in files:
        
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
                nwin = nfft
                window = np.hamming(nwin)
                spectro = Spectrogram(s=s, fs=fs, img_name=img_name, nfft=nfft, win_size=nwin, overlap=overlap)

                # Add image to coco object
                coco.add_image(id=img_id, width=spectro.width, height=spectro.height, file_name=img_name)

                # save image
                spectro.save_img(path=img_path)

                img_id += 1

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
                    x, y, w, h = spectro.get_coordinates(det_start, fmin, det_start + duration, fmin + fmax)

                    bbox = [x, y, w, h]

                    test(x, y, w, -h, os.path.join(img_path, img_name))

                    # Add annotation to coco object
                    coco.add_annotation(id=annot_id, img_id=img_id, cat_id=det["id_species"], bbox=bbox)
                    
                    annot_id += 1

                spectro.close()

            # spectro start and end
            spectro_start += spectro_time
            spectro_end += spectro_time

    Database.close_connexion()

    coco.save("DCLDE_2015.json", path=img_path)

    print("Task Done !")


def test(x, y, w, h, img_name="test.png"):
    fig, ax = plt.subplots()

    rect = Rectangle((x,y), w, h, linewidth=2, edgecolor='r', facecolor='none')
    
    img = Image.open(img_name)
    plt.imshow(np.flipud(img), origin="lower")
    ax.add_patch(rect)
    plt.show()

if __name__ == "__main__":

    detections2coco()