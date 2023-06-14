import os
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
from scipy import signal

import json

class COCO_label():

    def __init__(self):
        self.categories = []
        self.images = []
        self.annotations = []
    
    def add_categorie(self, id:int, name:str):
        new_category = {
                        "id":id,
                        "name":name
                        }
        self.categories.append(new_category)

    def add_image(self, id:int, width:int, height:int, file_name:str):
        image = {
                    "id":id,
                    "width":width,
                    "height":height,
                    "file_name":file_name
                }
        self.images.append(image)
    
    def add_annotation(self, id:int, img_id:int, cat_id:int, bbox:list):
        annotation = {
                        "id": id,
                        "image_id": img_id,
                        "category_id": cat_id,
                        # "segmentation": [bbox[0], bbox[1], bbox[0]+bbox[2], bbox[1], bbox[0]+bbox[2], bbox[1]+bbox[-1], bbox[0], bbox[1]+bbox[-1]],
                        "area": bbox[-2]*bbox[-1],
                        "bbox": bbox,
                        "iscrowd": 0
                    }
        
        self.annotations.append(annotation)

    def save(self, filename, path=None):
        # Create the dictonary with the dat of object
        dictionary = {
                        "type": "instances",
                        "images":self.images,
                        "annotations":self.annotations,
                        "categories":self.categories
                    }
        # Serializing json
        json_object = json.dumps(dictionary, indent=4)

        # Writing to filename.json
        if path:
            with open(os.path.join(path, filename), "w") as f:
                f.write(json_object)
        else:
            with open(filename, "w") as f:
                f.write(json_object)

class Range:
    def __init__(self, string=None, min=None, max=None):
        self.min = None
        self.max = None
        if string != None:
            format_prompt = 'Range input should have MIN:MAX, or MIN: or :MAX format'
            if type(string) == str and string != '':
                if string.startswith(':'):
                    self.max = float(string[1:])
                elif string.endswith(':'):
                    self.min = float(string[:-1])
                else:
                    string_split = string.split(':')
                    if len(string_split) != 2:
                        raise ValueError(format_prompt)
                    self.min = float(string_split[0])
                    self.max = float(string_split[1])
            else:
                raise ValueError(format_prompt)
        else:
            if min:
                self.min = min
            if max:
                self.max = max
        if self.min != None and self.max != None:
            if self.min > self.max:
                raise ValueError('Max value should be bigger than min value')

    def __repr__(self):
        return str(self.min) + str(self.max) 

class Spectrogram():

    def __init__(self, s, fs:int, img_name, nfft=2048*2, win_size=2000, overlap=90, cmap_color='Greys') -> None:
        
        self.mw = 0.000844055830808625

        butter_cutoff = 20
        s = butter_highpass_filter(s, butter_cutoff, fs, 5)

        self.img_name = img_name

        noverlap = int(win_size * overlap/100)
        nperseg = win_size
        nstep = nperseg - noverlap

        win = signal.get_window('hamming', nperseg)

        x = np.asarray(s)
        shape = x.shape[:-1] + ((x.shape[-1] - noverlap) // nstep, nperseg)
        strides = x.strides[:-1] + (nstep * x.strides[-1], x.strides[-1])
        xinprewin = np.lib.stride_tricks.as_strided(x, shape=shape, strides=strides)
        xinwin = win * xinprewin

        result = xinwin.real
        func = np.fft.rfft
        fftraw = func(result, n=nfft)

        scale_psd = 1.0 / (fs * (win * win).sum())
        vPSD_noBB = np.conjugate(fftraw) * fftraw
        vPSD_noBB *= scale_psd

        if nfft % 2:
            vPSD_noBB[..., 1:] *= 2
        else:
            vPSD_noBB[..., 1:-1] *= 2

        spectro = vPSD_noBB.real
        segment_times = np.arange(nperseg / 2, x.shape[-1] - nperseg / 2 + 1, nperseg - noverlap) / float(fs)
        frequencies = np.fft.rfftfreq(nfft, 1 / fs)
        spectro = spectro.transpose()

        # Restricting spectro frenquencies
        freqs_to_keep = (frequencies == frequencies)
        frequencies = frequencies[freqs_to_keep]
        spectro = spectro[freqs_to_keep, :]
        freqs_to_keep = (frequencies == frequencies)
        self.max_w = np.amax(spectro[freqs_to_keep, :])
        spectro = spectro / self.max_w

        log_spectro = 10 * np.log10(np.array(spectro))

        # Ploting spectrogram
        my_dpi = 100
        fact_x = 1.3 # 1.3
        fact_y = 1.3 # 1.3
        y = 512 # 1500
        color_val_range = Range("-30:0")#("-100:-80")
        
        min_color_val = color_val_range.min if color_val_range else None
        max_color_val = color_val_range.max if color_val_range else None

        self.fig = plt.figure(figsize=(fact_x * 1800 / my_dpi, fact_y * y / my_dpi), dpi=my_dpi)
        
        plt.pcolormesh(segment_times, frequencies, log_spectro, cmap=cmap_color)
        plt.clim(vmin=min_color_val, vmax=max_color_val)

        plt.ylim(15, 200)

        plt.axis('off')
        self.fig.tight_layout()

        self.width, self.height = self.fig.canvas.get_width_height()

    

    def get_coordinates(self, start, fmin, end, fmax):

        # Get the x and y data and transform it into pixel coordinates
        ax = self.fig.gca()

        # Get the size of the plot in pixels
        _, height = self.fig.get_size_inches() * self.fig.dpi

        # Convert the data coordinates to pixel coordinates
        x1, y1 = ax.transData.transform((start, fmin))
        x2, y2 = ax.transData.transform((end, fmax))
        x, y, w, h = x1, height - y2, x2 - x1, y2 - y1

        return x, y, w, h

    def get_values(self, x, y, w, h):
        # Get the temporal and frequential values from the pixel values of the bbox
        ax = self.fig.gca()

        # Get the size of the plot in pixels
        _, height = self.fig.get_size_inches() * self.fig.dpi

        # Convert the pixel values to data coordinates
        x1, y1 = x, height - (y + h)
        x2, y2 = x + w, height - y
        start, fmin = ax.transData.inverted().transform((x1, y1))
        end, fmax = ax.transData.inverted().transform((x2, y2))

        return start, end, fmin, fmax

    def save_img(self, path=None):
        if path:
            self.fig.savefig(os.path.join(path,self.img_name), dpi=self.fig.dpi)
        else:
            self.fig.savefig(self.img_name, dpi=self.fig.dpi)

    def close(self):

        plt.close(self.fig)

def butter_highpass_filter(data, cutoff, sample_rate, order):
    """Applies highpass (above cutoff) Butterworth digital filter of given order on data"""
    normal_cutoff = cutoff / (0.5 * sample_rate)
    numerator, denominator = signal.butter(order, normal_cutoff, btype='high', analog=False)
    return signal.filtfilt(numerator, denominator, data)

def main():
    test = Spectrogram()

    test.get_coordinates()

    img = Image.open("test.png")
    plt.figure()
    plt.imshow(img)

    plt.show()


if __name__ == "__main__":
    main()