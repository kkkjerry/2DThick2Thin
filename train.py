#from IPython.display import clear_output
from tensorflow.keras import models, optimizers, losses
from tensorflow.keras import backend as K
from tensorflow.keras.utils import Progbar
from loss import *
from utils import *
from network import *
from matplotlib import pyplot as plt

import cv2, random
import argparse
import numpy as np
import pandas as pd
import tensorflow as tf

random.seed(777)
np.random.seed(777)
tf.set_random_seed(777)

parser = argparse.ArgumentParser()
parser.add_argument("--save_dir", dest="save_dir", type=str, help="Path of Save")
parser.add_argument("--input_dir", dest="input_dir", type=str, help="Path of Input")
parser.add_argument("--mode", dest="mode", type=str, help="Mode of I/O")
parser.add_argument("--encoder", dest="encoder", type=str, help="Type of Encoder")
parser.add_argument("--loss", dest="loss", type=str, help="Type of Loss")
parser.add_argument("--batch", dest="batch", type=int, help="Size of Batch")
parser.add_argument("--epochs", dest="epochs", type=int, help="Number of Epochs")
parser.add_argument("--aux", dest="aux", type=bool, help="Number of Epochs", default=True)

args = parser.parse_args()

dict_args = vars(args)

for i in dict_args.keys():
    assert dict_args[i]!=None, '"%s" key is None Value!'%i
print("\n=======Training Options=======")
print("Save dir : ", args.save_dir)
print("Input dir : ", args.input_dir)
print("Mode : ", args.mode)
print("Encoder Type: ", args.encoder)
print("Loss Function: ", args.loss.upper())
print("Batch Size : ", args.batch)
print("Epochs : ", args.epochs)
print("Using Auxilary : ", args.aux)
print("==============================\n")
      
loss_dict = {"L1" : Custom_L1, 
             "L2" : Custom_MSE,
             "RMSE" : Custom_RMSE,
             "SSIM" : Custom_SSIM,
             "L1SSIM" : multi_loss(95, 5, args.loss.upper()).loss,
             "L2SSIM" : multi_loss(95, 5, args.loss.upper()).loss, 
             "MI" : mutual_information, 
             "L1MI": multi_loss(95, 5, args.loss.upper()).loss,
             "L2MI" : multi_loss(95, 5, args.loss.upper()).loss}




if args.mode == '3to6':
    N_SLICES = 6
    Loader = data_loader_v2
elif args.mode == '3to12':
    N_SLICES = 12
    Loader = data_loader_v3

ROOT_DIR = args.save_dir
    
train_low, train_high, val_low, val_high, test_low = Loader(args.input_dir)
print("Train X's shape : ", train_low.shape)
print("Train Y's shape : ", train_high.shape)
print("Validation X's shape : ", val_low.shape)
print("Validation Y's shape : ", val_high.shape)
print("Test X's shape : ", test_low.shape)    
print("\n")



print("Build a Generator !")      
if args.encoder == "unet":
    G = unet(n_slice=N_SLICES, case=2)
elif args.encoder =="res_unet":
    G = res_unet(n_slice=N_SLICES, case=2)
    
print("\n===================================\n")

G.compile(optimizer=optimizers.Adam(lr=0.0001, epsilon=1e-8), loss=loss_dict[args.loss.upper()])

shuffle_idx = np.random.choice(len(train_low), len(train_low), replace=False)
train_low = train_low[shuffle_idx]
train_high = train_high[shuffle_idx]
batch = args.batch
steps = len(train_low)//batch +1

epochs = args.epochs
train_loss = {"Generator_Total" : []}
val_loss = {"Generator_Total" : []}

total_progbar = Progbar(epochs)
save_root = args.save_dir

try:
    os.makedirs(save_root)
    print("\nMake Save Directory!\n")
except:
    print("\nDirectory Already Exist!\n")
         

model_json = G.to_json()
with open(os.path.join(save_root, "model.json"), "w") as json_file:
    json_file.write(model_json)
    
print("\nModel Saved!\n")    
#A.save(os.path.join(save_root + "model.h5"))

for epoch in range(epochs):
    #print("Epochs : %03d/%03d"%(epoch+1, epochs))
    epoch_progbar = Progbar(steps)
    epoch_t_g_total = 0
    
    epoch_v_g_total = 0
    
    for step in range(steps):
        
        idx = step*batch
        
        if step+1 == steps:
            step_train_low = train_low[-batch:]
            step_train_high = train_high[-batch:]
        else:
            step_train_low = train_low[idx:idx+batch]
            step_train_high = train_high[idx:idx+batch]
        
        # Traininig Phase
        G_Loss = G.train_on_batch(step_train_low, step_train_high)
        
        epoch_t_g_total += G_Loss    
    
    train_loss["Generator_Total"].append(epoch_t_g_total/steps)
    
    for idx_v in range(0, len(val_low), batch):
        if idx_v == len(val_low)//batch * batch:
            V_loss = G.test_on_batch(val_low[idx_v:], val_high[idx_v:])
        else:
            V_loss = G.test_on_batch(val_low[idx_v:idx_v+batch], val_high[idx_v:idx_v+batch])

        epoch_v_g_total += V_loss  
        
    val_loss["Generator_Total"].append(epoch_v_g_total/len(val_low))    
#     ran_idx = np.random.choice(len(train_low)-1, 1)
#     test_in = train_low[ran_idx[0]:ran_idx[0]+1]
#     test, _ = A.predict(test_in)
    
    total_progbar.update(epoch+1, [("G_Total", epoch_t_g_total/steps)])
#     clear_output(wait=True)
# #     plt.plot(train_loss['Generator_Style'], '.-')
# #     plt.plot(val_loss['Generator_Style'], '.-')
# #     plt.legend(['Train_Style', 'Validation_Style'], loc=0)
# #     plt.show()
#     plot_fn(train_loss, val_loss, test, train_high[ran_idx[0]:ran_idx[0]+1])
    if (epoch+1)%100 == 0:
        G.save_weights(os.path.join(save_root,'%04d_%.2f_%.2f.h5'%(epoch+1, epoch_t_g_total/steps, epoch_v_g_total/len(val_low))))
        
        

train_df = pd.DataFrame(train_loss)
train_df.to_csv(os.path.join(save_root,'train_loss.csv'))

val_df = pd.DataFrame(val_loss)
val_df.to_csv(os.path.join(save_root, 'val_loss.csv'))