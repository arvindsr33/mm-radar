from config_radar import CustomConfig
from data_handling2 import DataHandling2
import tkinter as tk
from tkinter import filedialog
import matplotlib.pyplot as plt 
# What would you like to do? 

objective = int(input('what would you like to do? \n 1 - configure radar \n 2 - organize new data \n 3 - range-doppler processing \n 4 - micro-doppler processing \n Enter here: '))

isConfig = (objective == 1)
isNewData = (objective == 2)
isRangeDopplerProcess = (objective == 3)
isMicroDopplerProcess = (objective == 4)

if isNewData:
    num_samples = int(input('enter num samples per frame: ') or 122)
    num_chirps = int(input('enter num of chirps per frame: ') or 128)
    experiment_name = input('enter experiment name: ') or 'test'

# global variables
num_tx = 1
num_rx = 4
res_range = 0.05
max_range = 5.5
max_velocity = 5
fps = 20
fs = 3200
config_params_1843 = {}
use_defaults = False

def config_1843():
    # (1) configure radar and print resultant radarcube parameters

    # (1.2) instantiate radar and run config script 
    awr1843_config = CustomConfig(num_tx=num_tx, num_rx=num_rx, res_range=res_range, max_range=max_range, max_velocity=max_velocity, fps=fps, fs=fs, use_defaults=use_defaults)    
    config_params_1843 = awr1843_config._run_config()
    print("\nIf sensorStart status is not 'Done', something could be wrong in configuring the radar! \n")

    # (1.3) print resultant rcube parameters
    print('{:-^60}'.format(' resultant rcube parameters '))
    for key, value in config_params_1843.items():
        print('{:25}'.format(key + ':') + str(round(value,4)))
    print('{:-^60}'.format(''))

def organize_rawdata(num_samples, num_chirps, experiment_name):
    # (2) organize raw data 

    # (2.2) instantiate DataHandling class
    data_handle = DataHandling2(num_samples=num_samples, num_chirps=num_chirps, num_tx=num_tx, num_rx=num_rx, fps=fps)
    # (2.3) organize data if new data is present
    data_directory = data_handle.organize_captured_data(experiment_name=experiment_name)

    return data_directory

def perform_rangedoppler_processing():
    data_directory =    filedialog.askdirectory(initialdir='/mnt/c/work/rcube_extract/dca_capture/captured_data')
 
    dir_name = data_directory.split("/")[-1]
    print(dir_name)
    params = dir_name.split('_')

    num_samples = int(params[4].split('x')[0][1:])
    num_chirps = int(params[4].split('x')[1][1:])
    num_tx = int(params[3][3])
    num_rx = int(params[3][4])
    fps = int(params[5][3:])

    data_handle = DataHandling2(num_samples=num_samples, num_chirps=num_chirps, num_tx=num_tx, num_rx=num_rx, fps=fps)
    data_handle.range_doppler_process(data_directory)
    return

def perform_microdoppler_processing():
    #data_directory =    filedialog.askdirectory(initialdir='/mnt/c/work/rcube_extract/dca_capture/captured_data')
    data_directory =    '/mnt/c/work/rcube_extract/dca_capture/captured_data/dca_apr19_2051_trx14_n122xp128_fps20_walk_no_gesture'  
    dir_name = data_directory.split("/")[-1]
    
    params = dir_name.split('_')
    print('params: ' + str(params))
    num_samples = int(params[4].split('x')[0][1:])
    num_chirps = int(params[4].split('x')[1][1:])
    num_tx = int(params[3][3])
    num_rx = int(params[3][4])
    fps = int(params[5][3:])

    # calculate max velocity (assuming 50% duty cycle)
    # if use_defaults == False:
    #max_velocity = max_velocity if use_defaults else (3e8/77e9) / 4 * (2 *fps * num_chirps) # vmax = lambda / 4 / T
    #print('max_velocity: ' + str(max_velocity))
    data_handle = DataHandling2(num_samples=num_samples, num_chirps=num_chirps, num_tx=num_tx, num_rx=num_rx, fps=fps)
    data_handle.micro_doppler_stft(data_directory, max_velocity)

    # plot 
    # plt.ion()
    #plt.imshow(micro_doppler_spectrogram, aspect=2, extent=[0, micro_doppler_spectrogram.shape[1]/fps, -max_velocity, max_velocity], cmap='plasma')
    #plt.ylabel('velocity [m/s]')
    #plt.xlabel('time [s]')
    #plt.colorbar(label='log scale')
    #plt.show()
    return 

def main():

    if isConfig:
        config_1843()
    if isNewData:
        organize_rawdata(num_samples, num_chirps, experiment_name)

    if isRangeDopplerProcess:
        perform_rangedoppler_processing()

    if isMicroDopplerProcess:
        perform_microdoppler_processing()


if __name__ == "__main__":
    main()

