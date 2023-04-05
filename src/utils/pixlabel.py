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
                    "heigh":height,
                    "file_name":file_name
                }
        self.images.append(image)
    
    def add_annotation(self, id:int, img_id:int, cat_id:int, bbox:list):
        annotation = {
                        "id": id,
                        "image_id": img_id,
                        "category_id": cat_id,
                        "bbox": bbox
                    }
        
        self.annotations.append(annotation)

    def save(self, filename, path=None):
        # Create the dictonary with the dat of object
        dictionary = {
                        "categories":self.categories,
                        "images":self.images,
                        "annotations":self.annotations
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
        return str(self.min) + str(self.max)  #f"Range({self.min}:{self.max})"

class Spectrogram():

    def __init__(self, s, fs:int, nfft=2048, win_size=2048, overlap=.5, cmap_color='Greys') -> None:

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
        # if self.min_freq_plot:
        #     freqs_to_keep *= self.min_freq_plot <= frequencies
        # if self.max_freq_plot:
        #     freqs_to_keep *= frequencies <= self.max_freq_plot
        frequencies = frequencies[freqs_to_keep]
        spectro = spectro[freqs_to_keep, :]

        # # Setting self.max_w and normalising spectro as needed
        # if main_ref:
        #     # Restricting spectro frenquencies for dynamic range
        #     freqs_to_keep = (frequencies == frequencies)
        #     if self.min_freq_dyn:
        #         freqs_to_keep *= self.min_freq_dyn <= frequencies
        #     if self.max_freq_dyn:
        #         freqs_to_keep *= frequencies <= self.max_freq_dyn
        #     self.max_w = np.amax(spectro[freqs_to_keep, :])
        # spectro = spectro / self.max_w

        # # This is needed to match end of tile n with start of tile n+1
        # if shorten:
        #     segment_times = segment_times[:-1]
        #     spectro = spectro[:,:-1]

        # Switching to log spectrogram
        log_spectro = 10 * np.log10(np.array(spectro))

        # Ploting spectrogram
        my_dpi = 100
        fact_x = 1 # 1.3
        fact_y = 1 # 1.3
        y = 1500 # 512
        color_val_range = Range("-100:-80")
        
        min_color_val = color_val_range.min if color_val_range else None
        max_color_val = color_val_range.max if color_val_range else None

        self.fig = plt.figure(figsize=(fact_x * 1800 / my_dpi, fact_y * y / my_dpi), dpi=my_dpi)
        plt.pcolormesh(segment_times, frequencies, log_spectro, cmap=cmap_color)
        plt.clim(vmin=min_color_val, vmax=max_color_val)

        plt.ylim(15, 80)

        plt.axis('off')
        self.fig.tight_layout()

        self.fig.savefig('test.png', dpi=my_dpi)
        # plt.show()
        # self.fig, self.ax = plt.subplots()
        # self.points, = self.ax.plot(range(10), 'ro')
        # self.ax.axis([-1, 10, -1, 10])

    def get_coordinates(self, x, y, w, h):
        # Get the x and y data and transform it into pixel coordinates
        ax = plt.gca()
        xywh_pixels = ax.transData.transform(np.vstack([x,y,w,h]).T)
        # xy_pixels = self.ax.transData.transform(np.vstack([x,y]).T)
        [xpix, wpix], [ypix, hpix] = xywh_pixels.T
        # self.xpix, self.ypix = xy_pixels.T
        _, height = self.fig.canvas.get_width_height()
        # self.ypix = height - self.ypix
        ypix, hpix = height - ypix, height - hpix
        # print('Coordinates of the points in pixel coordinates...')

        # for xp, yp in zip(self.xpix, self.ypix):
        #     print('{x:0.2f}\t{y:0.2f}'.format(x=xp, y=yp))

        # We have to be sure to save the figure with it's current DPI
        # (savfig overrides the DPI of the figure, by default)
        self.fig.savefig('test.png', dpi=self.fig.dpi)

        return xpix, ypix, wpix, hpix

def main():
    test = Spectrogram()

    test.get_coordinates()

    img = Image.open("test.png")
    plt.figure()
    plt.imshow(img)

    plt.show()


if __name__ == "__main__":
    main()