from utils import CheXpert_Dataset
from utils.metric import multi_class_F1
from utils.evaluate import evaluate

from torch.utils.data import DataLoader
from trainer import train_batch
from utils.load_config import _choose_model, _choose_optim, _choose_criterion, load_configfile, _choose_augmentation

import torch
import argparse

dict_config = (
    'train_folder', #
    'train_csv', #
    
    'handle_uncertain',
    'class_list', #
    'img_size',
    'greyscale',

    'val_folder', #
    'val_csv', #

    'shuffle',
    'batch_size',

    'num_workers',
    'nEpochs',

    'train_pfeq',   #Print frequent for train
    'val_pfeq',     #Print frequent for val


    'pretrain'
)

if __name__ == '__main__':
    # Get command line argument
    parser = argparse.ArgumentParser(description='Training script for CheXpert')
    configpath = './configfiles/devTest_config.ini'    
    parser.add_argument('--config-path', '-c', help='Path to config path', default=configpath)

    args = parser.parse_args()
    configpath = args.config_path

    # Actual code
    print("---------------load dict_config----------------------------------")
    dict_config = load_configfile(dict_config, configpath)
    dict_config = _choose_model(dict_config)
    dict_config = _choose_optim(dict_config)
    dict_config = _choose_criterion(dict_config)
    
    # augmentation
    transform_augment = _choose_augmentation(dict_config)

    print("---------------create Dataset/Dataloader-------------------------")
    trainDataset = CheXpert_Dataset(dict_config['train_folder'], dict_config['train_csv'], mode='train', greyscale=dict_config['greyscale'],
                                    handle_uncertain=dict_config['handle_uncertain'], transform=transform_augment, 
                                    class_list=dict_config['class_list'], size=dict_config['img_size'])

    trainDataloader = DataLoader(trainDataset, batch_size=dict_config['batch_size'], shuffle=dict_config['shuffle'],
                                 num_workers=dict_config['num_workers'], pin_memory=dict_config['pin_memory'])

    valDataset = CheXpert_Dataset(dict_config['val_folder'], dict_config['val_csv'], mode='val', greyscale=dict_config['greyscale'],
                                  handle_uncertain=dict_config['handle_uncertain'], transform=None, 
                                  class_list=dict_config['class_list'], size=dict_config['img_size'])

    valDataloader = DataLoader(valDataset, batch_size=32, shuffle=False, num_workers=dict_config['num_workers'])

    print("---------------training------------------------------------------")
    model = dict_config['model']
    optimizer = dict_config['optimizer']
    criterion = dict_config['criterion']

    model.cuda()
    criterion.cuda()


    best_F1_score = 0
    best_val_loss = 10000
    for e in range(dict_config['nepochs']):
        model.train()
        train_iter = iter(trainDataloader)
        eLoss = 0
        emetric_value = {'F1':0}
        for b in range(len(trainDataloader)):
            bLoss, bMetrics = train_batch(model, optimizer, criterion, train_iter, dict_config, metric_funcs=[multi_class_F1])
            
            eLoss += bLoss 

            emetric_value['F1'] += bMetrics[0]

            if b % dict_config['train_pfeq'] == 0:
                print(f'Epoch {e} - [{b} / {len(trainDataloader)}]:\nLoss: {eLoss / (b + 1)}')
                print(f"F1: {emetric_value['F1'] / (b + 1)}")
        
        if e % dict_config['save_checkpoint_feq'] == 0:
            checkpoint = {
                'epochs': e,
                'dict_config': dict_config,
                'state_dict': model.state_dict()
            }
            torch.save(checkpoint, dict_config['checkpoint_path'])
        
        model.eval()
        val_loss, val_F1  = evaluate(model, valDataloader, criterion, None, dict_config['val_pfeq'])

        if best_F1_score < val_F1:            
            print(f'Updated best F1 from {best_F1_score} to {val_F1}')
            torch.save(model.state_dict(), dict_config['bestF1_path'])
            best_F1_score = val_F1

        if best_val_loss > val_loss:
            print(f"Update best loss from {best_val_loss} to {val_loss}")
            torch.save(model.state_dict(), dict_config['best_valLoss_path'])
            best_val_loss = val_loss
