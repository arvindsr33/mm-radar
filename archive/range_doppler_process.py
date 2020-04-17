from data_handling import *
import tkinter as tk
from tkinter import filedialog
from mmwave.dsp.range_processing import *   # pip install openradar
from mmwave.dsp.utils import *
from processing_chain import * 
import matplotlib.pyplot as plt


root = tk.Tk()
root.withdraw()

run_annotate = False
run_range_doppler_process = False
run_micro_doppler_process = True

if run_annotate:
    # specify radar params
    num_samples = 124
    num_chirps = 128
    num_tx = 1
    num_rx = 4
    frames_per_second = 20

    annotate_captured_data(num_samples, num_chirps, num_tx, num_rx, frames_per_second)
    
else:
    # get file and radar parameters
    #file_path = filedialog.askdirectory(initialdir='/mnt/c/work/rcube_extract/dca_capture/captured_data')
    #print(file_path)
    file_path = '/mnt/c/work/rcube_extract/dca_capture/captured_data/dca_mar31_1825_trx14_n122xp128_fps20_walk_parade' # for debugging 
    dir_name = file_path.split("/")[-1]
    params = dir_name.split('_')

    num_samples = int(params[4].split('x')[0][1:])
    num_chirps = int(params[4].split('x')[1][1:])
    num_tx = int(params[3][3])
    num_rx = int(params[3][4])
    frames_per_second = int(params[5][3:])

if run_range_doppler_process:
    range_doppler_process(file_path, num_samples, num_chirps, num_tx, num_rx, frames_per_second)

if run_micro_doppler_process:
    micro_doppler_stft(file_path, num_samples, num_chirps, num_tx, num_rx, frames_per_second)
