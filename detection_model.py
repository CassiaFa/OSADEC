import torch
import cv2
from PIL import Image
import matplotlib.pyplot as plt


class Model_detection():

    def __init__(self, model_name):
        self.model = self.load_model(model_name)
        self.classes = self.model.names
        
    
    def load_model(self, model_name):

        '''
        Loads Yolo5 model from pytorch hub. If model_name is given loads a custom model, else loads the pretrained model.
        :return: Trained Pytorch model.
        '''
        
        if model_name:
            model = torch.hub.load('ultralytics/yolov5', 'custom', path=model_name)  # local model
        else:
            model = torch.hub.load('ultralytics/yolov5', 'yolov5m', pretrained=True)
        
        return model

    def image_detection(self, image):
        results = self.model(image)

        image = results.ims[0]

        labels, cord = results.xyxyn[0][:, -1], results.xyxyn[0][:, :-1]
        
        print("\n ========== \n", len(image), "\n ========== \n")

        n = len(labels)
        x_shape, y_shape = image.shape[1], image.shape[0]
        

        for i in range(n):
            row = cord[i]
            if row[4] >= 0.3:
                x1, y1, x2, y2 = int(row[0]*x_shape), int(row[1]*y_shape), int(row[2]*x_shape), int(row[3]*y_shape)
                bgr = (0, 255, 0)
                cv2.rectangle(image, (x1, y1), (x2, y2), bgr, 2)
                cv2.putText(image, f"{self.classes[int((labels[i]))]}  {row[4]:.2f}", (x1, y1), cv2.FONT_HERSHEY_SIMPLEX, 0.9, bgr, 2)

        return image

    # def detection(self, image):
    #     results = self.model(image)

    #     image = results.ims[0]

    #     x_shape, y_shape = image.shape[1], image.shape[0]

    #     labels, cord = results.xyxyn[0][:, -1], results.xyxyn[0][:, :-1]

    #     n = len(labels)
        


    #     for i in range(n):
    #         print("\n ==== label and coord ====== \n", n, cord[i], "\n ========== \n")
    #         row = cord[i]
    #         if row[4] >= 0.3:
    #             x1, y1, x2, y2 = int(row[0]*x_shape), int(row[1]*y_shape), int(row[2]*x_shape), int(row[3]*y_shape)
    #             print("\n ========== \n", x1, y1, x2, y2, "\n ========== \n")
    #             # x3, y3, x4, y4 = int(row[0]), int(row[1]), int(row[2]*x_shape), int(row[3]*y_shape)
    #             bgr = (0, 255, 0)
    #             cv2.rectangle(image, (x1, y1), (x2, y2), bgr, 2)
    #             # cv2.rectangle(image, (x3, y3), (x4, y4), bgr, 3)
    #             cv2.putText(image, f"{self.classes[int((labels[i]))]}  {row[4]:.2f}", (x1, y1), cv2.FONT_HERSHEY_SIMPLEX, 0.9, bgr, 2)

    #     return image

    # def __call__(self, capture_index):

    #     self.cam = cv2.VideoCapture(capture_index)

    #     while True:
    #         _, frame = self.cam.read()
            
    #         frame = cv2.resize(frame, (640,640))

    #         results = self.model(frame)

    #         labels, cord = results.xyxyn[0][:, -1], results.xyxyn[0][:, :-1]

    #         n = len(labels)
    #         x_shape, y_shape = frame.shape[1], frame.shape[0]
    #         for i in range(n):
    #             row = cord[i]
    #             if row[4] >= 0.3:
    #                 x1, y1, x2, y2 = int(row[0]*x_shape), int(row[1]*y_shape), int(row[2]*x_shape), int(row[3]*y_shape)
    #                 bgr = (0, 255, 0)
    #                 cv2.rectangle(frame, (x1, y1), (x2, y2), bgr, 2)
    #                 cv2.putText(frame, f"{self.classes[int((labels[i]))]}  {row[4]:.2f}", (x1, y1), cv2.FONT_HERSHEY_SIMPLEX, 0.9, bgr, 2)

    #         cv2.imshow('Video', frame)

    #         if cv2.waitKey(1) & 0xFF == ord('q'):
    #             break

def main():
    pass

if __name__ == "__main__":

    detector = Model_detection("./weight/last.pt")
    
    # import glob
    # for i in glob.glob("./data_img/*png"):
    i = "./test2.png"
    img = cv2.imread(i)
    # img = Image.open("./test2.png")

    # plt.figure()
    # plt.imshow(img)
    # plt.show()
    
    # model_name="./weight/last.pt"
    # model = torch.hub.load('ultralytics/yolov5', 'custom', path=model_name)
    
    
    result = detector.image_detection(img)
    
    import matplotlib
    matplotlib.use('QtAgg') # Change backend after loading model
    
    plt.figure()
    plt.imshow(result)
    plt.show()

    pass
