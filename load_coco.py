import os
import json
from random import sample

from PIL import Image
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

# function to load coco annotations
def load_coco_annotations(coco_file):
    with open(coco_file, 'r') as f:
        data = json.load(f)
    return data


# function to associate categories with file
def link_annotations(data):
    file_list = []
    for item in data['images']:
        file = {
            'name': item['file_name'],
            'id': item['id'],
            'annotations': [],
            'categories': []
        }

        for annotation in data["annotations"]:
            if annotation['image_id'] == item['id']:
                file['annotations'].append(annotation['id'])
                file['categories'].append(annotation['category_id'])
        
        file_list.append(file)
    
    return file_list

def main():
    data = load_coco_annotations('./data_annotated/DCLDE_2015_v2.json')
    summary = link_annotations(data)

    label_6_only = [x for x in summary if 6 in x['categories'] and 7 not in x['categories']]
    label_7_only = [x for x in summary if 7 in x['categories'] and 6 not in x['categories']]
    both = [x for x in summary if 6 in x['categories'] and 7 in x['categories']]

    print(f"label 6 only : {len(label_6_only)}", '\n', 
          f"label 7 only : {len(label_7_only)}", '\n', 
          f"both : {len(both)}")
    
    train_list = sample(label_6_only, round(len(label_6_only)*0.8)) + sample(label_7_only, round(len(label_7_only)*0.8)) + sample(both, round(len(both)*0.8))

    train = {
        'type': 'instances',
        'images': [],
        'annotations': [],
        'categories': data['categories']
    }

    id_im_train = []
    id_an_train = []

    for item in train_list:
        bbox = []
        train['images'].append(data['images'][item['id']])
        id_im_train.append(item['id'])

        for annot_id in item['annotations']:
            train['annotations'].append(data['annotations'][annot_id])
            id_an_train.append(annot_id)
            bbox.append(data['annotations'][annot_id]['bbox'])

        # verif_by_plot(data['images'][item['id']]['file_name'], bbox=bbox)
        
        
    json_object = json.dumps(train, indent=4)
    with open('./data_annotated/train.json', "w") as f:
        f.write(json_object)

    val = {
        'type': 'instances',
        'images': [x for x in data['images'] if x['id'] not in id_im_train],
        'annotations': [x for x in data['annotations'] if x['id'] not in id_an_train],
        'categories': data['categories']
    }
    
    json_object = json.dumps(val, indent=4)
    with open('./data_annotated/val.json', "w") as f:
        f.write(json_object)


def round_values():
    # path of file
    path = "./data_annotated/"
    # file list
    files = ['train.json', 'val.json']

    for i in files:
        # load coco annotations
        data = load_coco_annotations(os.path.join(path, i))
        

def verif_by_plot(img_name, bbox):

    img_path = os.path.join("./data_annotated", img_name)

    img = Image.open(img_path)

    fig, ax = plt.subplots()
    plt.imshow(img)
    plt.axis("off")

    for b in bbox:
        rect = Rectangle((b[0], b[1]), b[2], b[3], edgecolor="red", facecolor="none", lw=2)
        ax.add_patch(rect)
    
    plt.show()

    input("Press Enter to continue...")

    plt.close(fig=fig)
 

if __name__ == '__main__':
    main()