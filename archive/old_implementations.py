

'''
Old implementations
'''

import numpy as np 
import time 
from mmwave.dsp.range_processing import *   # pip install openradar
from mmwave.dsp.utils import *
from processing_chain import * 
import skvideo.io # pip install scikit-video
import matplotlib.pyplot as plt
import cv2
from config_radar import custom_config
import os
import tkinter as tk
from tkinter import filedialog
import time 
import shutil
import glob


def range_doppler_process2(dir_name, num_samples=256, num_chirps=64, num_tx=1, num_rx=4, frames_per_second=10):

    # parameters
    header_size = 32
    # define video writing object 
    frame_width = num_samples # // 2 # To remove the part correpsonding to negative frequencies
    frame_height = num_chirps

    save_path = '/mnt/c/work/rcube_extract/dca_capture/video_write/'
    video_file = save_path + dir_name.split('/')[-1] + '.avi'

    out = cv2.VideoWriter(video_file, cv2.VideoWriter_fourcc('M','J','P','G'), frames_per_second, (frame_width,frame_height), isColor=False)

    # read all the data files present in the folder
    # Note: radarcube axes [fast time, slow time, channels, frames (time progression)]
    file_index = 0 
    prev_file_data = np.array([])

    hsi_header = [2780, 3290, 2780, 3290,   48,    1,    0,    0, 1731,   32,  515,  512,  271,    1,  512,    0]
    packet_len = num_samples *  num_rx * 2 + 32 

    data_files = glob.glob(dir_name + '/datacard_record_hdr_0ADC*.bin')
    # print(data_files)
    
    for files in data_files:
        raw_data = np.fromfile(files, dtype=np.int16)
        raw_appended = np.insert(raw_data, 0, prev_file_data) #insert in the beginning

        # sanity check
        error1 = np.array_equal(raw_appended[0 : np.size(hsi_header)], hsi_header) == 0
        error2 = np.array_equal(raw_appended[packet_len:packet_len+np.size(hsi_header)], hsi_header) == 0
        if error1 or error2:  
            print('Something wrong with data unwrapping!')

        rcube, next_frame_data = raw_radarcube(raw_appended, num_samples, num_chirps, num_rx, header_size)

        
        # range-doppler proessing of the raw data
        axis_range = 0
        axis_doppler = 1

        rcube_fft1 = range_processing(rcube, window_type_1d=Window.HAMMING, axis=axis_range) 
        accumulateStatus = False
        rcube_fft2 = doppler_processing_custom(rcube_fft1, num_tx=1, clutter_removal_enabled=True, 
        interleaved=False, window_type_2d=Window.HAMMING, accumulate=accumulateStatus, axis=axis_doppler)
            

        # convert to proper format  
        # (2.3) transpose to obtain dopper axis as first dimension
        #       if accumulate false, then select first channel   
        if accumulateStatus:
            rcube_fft2_tr = np.transpose(rcube_fft2, (1,0,2))
        else:
            rcube_fft2_tr = np.transpose(rcube_fft2[:,:,0,:], (1,0,2))
            print('rcube dimensions : ' + str(rcube_fft2_tr.shape))

        # video_in = rcube_fft2_tr[:, :num_samples//2, :]   # to remove the part correpsonding to negative frequencies 
        video_in = rcube_fft2_tr    # for full range bins video 
        # print(video_in.shape)

        # plot sample images 
        # plt.imshow(video_in[:,:,1])
        # plt.show()

        # normalize and write the frame to video object
        for frame in range(video_in.shape[2]):
            # img_normalize = cv2.normalize(src=video_in[:, :, frame], dst=None, alpha=0, beta=255, norm_type=cv2.NORM_L1, dtype=cv2.CV_8U)
            min = np.amin(video_in[:, :, frame], (0,1))
            max = np.amax(video_in[:, :, frame], (0,1))
            img_normalize = (video_in[:, :, frame] - min) / (max - min)
            img_normalize = np.round(img_normalize * 255).astype(np.uint8)

            out.write(img_normalize)
            if frame == 0 and file_index == 1:
                print(img_normalize)
            
        prev_file_data = next_frame_data     
        file_index += 1

    # release the video object    
    out.release()

    print('range-doppler video written successfully ...')
    return

