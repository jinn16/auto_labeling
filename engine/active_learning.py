import os
from engine.trainer.train import Trainer
from engine.inferencer.inference import detect_image
import torch
from engine.utils.control_xml import create_label_map, load_label_map
from engine.utils.voc2coco import convert_annot
from engine.cfg.config import Config
import glob
import time

class ActiveLearning(object):
    def __init__(self):
        super(ActiveLearning, self).__init__()
        self.config = Config()

    def run(self, img_dir, xml_dir):

        if os.path.isfile(self.config.label_map_path):
            load_label_map(self.config.label_map_path)
            print('loading label map')
        else:
            create_label_map(xml_dir, self.config.label_map_path)
            print('creating label map')

        coco_dir = os.path.join(os.getcwd(), '/annotations')
        print(f'COCO PATH {coco_dir}')
        convert_annot(xml_dir, self.config.label_map_path, coco_dir)

        trainer = Trainer(self.config, img_dir, coco_dir)

        progress_range = range(trainer.config.start_epoch, trainer.config.epoch)
        progress_len = len(progress_range)
        print(0, 'Start training')

        for epoch in range(trainer.config.start_epoch, trainer.config.epoch):
            trainer.train(epoch)
            trainer.validation(epoch)
            progress = (epoch + 1) / progress_len * 100
            print(progress, f'epoch {epoch} complete')

        if self.config.tensorboard:
            trainer.writer.close()

        # 추론부
        # 1. 사용자가 Labeling했던 data는 제외시키기(덮어쓰기가 되면 안되기 때문)

        ann_name = [os.path.splitext(f.name)[0] for f in os.scandir(xml_dir)]
        img_name_dict = {os.path.splitext(f.name)[0]: os.path.splitext(f.name)[1] for f in os.scandir(img_dir)}
        img_names = list(set(img_name_dict.keys()).difference(set(ann_name)))

        # 2. Best Model Checkpoint 로드하기
        model_path = f'./engine/run/{self.config.projectname}/best_f1_score_model.pth.tar'

        if not os.path.isfile(model_path):
            print('The amount of training data is insufficient.')
        model = torch.load(model_path)

        # 3. 모델에 이미지 하나씩 넣어서 추론하고, entropy 구하기

        all_entropy = {}
        total_img_cnt = len(img_names)
        for i, img_name in enumerate(img_names):
            progress = (i + 1) / total_img_cnt * 100

            ext = img_name_dict[img_name]
            img_path = os.path.join(img_dir, img_name + ext)

            entropy = detect_image(img_path, model, self.config.label_map_path, al=True)
            all_entropy[img_path] = entropy
            print(progress, f'Inferencing image : {i} / {total_img_cnt} complete')

            if i+1 == int(total_img_cnt * 0.1) or i+1 == 1000:
                break;
        all_entropy = sorted(all_entropy.items(), key=lambda x: x[1], reverse=True)
        img_list = list(dict(all_entropy[:100]).keys())
        # print('img list hard to label', img_list)