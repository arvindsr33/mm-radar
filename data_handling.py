'''
Issues:
    1. The signatures are more prominent in negative range bins frequencies (first half of the fftshift output)
    2. Accumulate with logAbs isn't working well 

To-do's:
    1. 
'''

import numpy as np 
import time 
from mmwave.dsp.range_processing import *   # pip install openradar
from mmwave.dsp.utils import *
from processing_chain import * 
import skvideo.io # pip install scikit-video
import matplotlib.pyplot as plt
import cv2
import os
import tkinter as tk
from tkinter import filedialog
import time 
import shutil
import glob

class DataHandling: 

    def __init__(self, num_samples=256, num_chirps=64, num_tx=1, num_rx=4, fps=10):
        self.num_samples = num_samples
        self.num_chirps = num_chirps
        self.num_tx = num_tx
        self.num_rx = num_rx
        self.frames_per_second = fps

    def organize_captured_data(self, experiment_name='', src_dir='/mnt/c/work/rcube_extract/dca_capture/captured_data/'):
        """
        Organizes raw captured data into a directory named with data specifications and given experiment name (e.g. 'walk').

            Inputs:
                - data specifications provided with class instantiation
                - experiment name
                - src_dir (initialized to arvind's default data capture directory)
            Outputs:
                - None # // destination directory name 
        """ 
        # (1) create destination directory

        # (1.1) create time now string mmmdd_hhmm_
        time_now = time.ctime().lower()
        str_time = time_now[4:7] + time_now[8:10] + '_' + time_now[11:13] + time_now[14:16] + '_'

        # (1.2) create destination folder string using all specifications provided 
        subdir_name = 'dca_' + str_time + 'trx' + str(self.num_tx) + str(self.num_rx) + '_n' + str(self.num_samples) + 'xp' + str(self.num_chirps) 
        subdir_name = subdir_name + '_fps' + str(self.frames_per_second) + '_' + experiment_name 

        # (1.3) create the destination directory 
        dst_dir = src_dir + subdir_name + '/'
        os.mkdir(dst_dir)

        # (2) read all captured data and move into the destination directory 
        captured_files = glob.glob(src_dir + '/*.*')
        if len(captured_files) == 0:
            print('No new data present. Exiting...')
            return 0

        for i in captured_files:
            dst_file = dst_dir + i.split("/")[-1]
            shutil.move(i, dst_file)

        print('\n recorded data organized into ' + str(dst_dir) + ' successfully...\n')
        return 


    def raw_data_cube(self, dir_name):
        '''
        Generator function that yeilds raw_data_cube iterator for each ADC raw data file.
            Inputs:
                - full path of raw data directory
            Outputs:
                - raw data cube  
        '''
        # (1) parameters

        # (1.1) vary with every iteration
        file_index = 0
        prev_file_data = np.array([])
        data_flag = 1
        # (1.2) fixed parameters
        header_size = 32
        packet_len = self.num_samples *  self.num_rx * 2 + header_size 
        data_files = glob.glob(dir_name + '/datacard_record_hdr_0ADC*.bin')
        # print(data_files)
        # (1.3) file reading status parameter

        # (2) yield rawdatacube while data_flag active 
        while data_flag:
            # (2.1) read data from file in current iteration and append data left in previous iteration 
            current_file = data_files[file_index]
            raw_data = np.fromfile(current_file, dtype=np.int16)
            raw_appended = np.insert(raw_data, 0, prev_file_data) #insert in the beginning

            # (2.2) select HSI header as first 32 words of ADC0 file
            if file_index == 0:
                hsi_header = raw_data[0:header_size]

            # (2.2.1) sanity check for header locations and proper rcube size 
            error1 = np.array_equal(raw_appended[0 : np.size(hsi_header)], hsi_header) == 0
            error2 = np.array_equal(raw_appended[packet_len:packet_len+np.size(hsi_header)], hsi_header) == 0
            if error1 or error2:
                print("Warning: headers don't match... something wrong with data unwrapping")

            # (2.3) call raw_radarcube script to reshape the data into data_cube and incomplete next frame data
            data_cube, next_frame_data = raw_radarcube(raw_appended, self.num_samples, self.num_chirps, self.num_rx, header_size)
            print('file index: ' + str(file_index) + ' | datacube shape' + str(data_cube.shape))  # for debug, print the shape
            
            # (2.4) change variable values for next iteration 
            prev_file_data = next_frame_data     
            file_index += 1  
            data_flag = file_index < len(data_files) 

            yield data_cube


    def range_doppler_process(self, dir_name, save_path='/mnt/c/work/rcube_extract/dca_capture/video_write/'):

        """
        Compute range-doppler fft on raw data and save the output as a video 
            Inputs:
                - data specifications provided with class instantiation
                - full filename of the data directory 
                - save path 
            Outputs:
                - None
        """

        # (1) define video writing object 

        # (1.1) video specs 
        frame_width = self.num_samples # // 2 # To remove the part correpsonding to negative frequencies
        frame_height = self.num_chirps

        video_file = save_path + dir_name.split('/')[-1] + '.avi'

        # (1.2) instantiate video writer object 
        out = cv2.VideoWriter(video_file, cv2.VideoWriter_fourcc('M','J','P','G'), self.frames_per_second, (frame_width, frame_height), isColor=False)

        # (2) implement range-doppler processing
        
        axis_range = 0
        axis_doppler = 1

        # (2.1) initiate the raw_data generator function
        raw_data = self.raw_data_cube(dir_name)
        data_status = True

        while data_status:
            rcube = next(raw_data, [])   # output 0 when no done reading all data files
            data_status = np.size(rcube)
            if len(rcube) == 0:
                break
            # (2.2) peform range-doppler ffts 
            rcube_fft1 = range_processing(rcube, window_type_1d=Window.HAMMING, axis=axis_range) 
            accumulateStatus = False
            rcube_fft2 = doppler_processing_custom(rcube_fft1, num_tx=1, clutter_removal_enabled=True, 
            interleaved=False, window_type_2d=Window.HAMMING, accumulate=accumulateStatus, axis=axis_doppler)
                    
            # (2.3) transpose to obtain dopper axis as first dimension
            #       if accumulate false, then select first channel   
            if accumulateStatus:
                rcube_fft2_tr = np.transpose(rcube_fft2, (1,0,2))
            else:
                rcube_fft2_tr = np.transpose(rcube_fft2[:,:,0,:], (1,0,2))

            # (2.4) select range spectrum in video and compute magnitude of complex data
            # video_in = np.abs(rcube_fft2_tr[:, :num_samples//2, :])   # remove negative frequencies 
            video_in = np.abs(rcube_fft2_tr)    # for full range spectrum 
            # print(video_in.shape)

            # plot sample images 
            # plt.imshow(video_in[:,:,1])
            # plt.show()

            # (2.5) normalize and write the frame to video object
            for frame in range(video_in.shape[2]):
                # (2.5.1) normalize to [0, 255] for each frame
                # img_normalize = cv2.normalize(src=video_in[:, :, frame], dst=None, alpha=0, beta=255, norm_type=cv2.NORM_L1, dtype=cv2.CV_8U)
                min = np.amin(video_in[:, :, frame], (0,1))
                max = np.amax(video_in[:, :, frame], (0,1))
                img_normalize = (video_in[:, :, frame] - min) / (max - min)
                img_normalize = np.round(img_normalize * 255).astype(np.uint8)

                out.write(img_normalize)
                #if frame == 0: # // for debugging 
                    # print(img_normalize)
                
        # (3) release the video object    
        out.release()
        print('range-doppler video written successfully ...\n')
        return

    def micro_doppler_stft(self, dir_name, max_velocity, save_path = '/mnt/c/work/rcube_extract/dca_capture/micro_doppler/'):

        '''
        Steps for short-time Fourier tranform based micro-Doppler processing:
            1. Perform windowing and fft in range for each frame
            2. Compress over range in each frame 
            3. Perform windowing followed by fft in Doppler 

        Inputs:
            - data specifications provided with class instantiation
            - full filename of data directory
            - path to save micro-doppler image  
        Outputs:
            - numpy array of micro-doppler spectrogram
        '''
        # (0) variables and parameters 
        axis_range = 0
        axis_doppler = 0 # range axis is removed during range accumulation
        data_status = True
        micro_doppler_spectrum = np.zeros((self.num_chirps, 0))

        # (1) instantiate the raw_data generator
        raw_data = self.raw_data_cube(dir_name)
        # print(type(raw_data))

        # (2) keep appending micro-doppler spectrogram while data_status is active
        while data_status:
            # (2.0) read the next data_cube from generator
            data_cube = next(raw_data, [0]) 

            # (2.1) perform range-fft and sum over range axis
            if len(data_cube) == 1:
                break 

            data_cube_fft1 = range_processing(data_cube, window_type_1d=Window.HAMMING, axis=axis_range)
            data_range_accum = np.sum(data_cube_fft1, axis=axis_range)
            # print(data_range_accum.shape)

            # (2.2) perform doppler-fft 
            accumulateStatus = True
            micro_doppler_file_raw = doppler_processing_custom(data_range_accum, num_tx=1, clutter_removal_enabled=True, 
            interleaved=False, window_type_2d=Window.HAMMING, accumulate=accumulateStatus, axis=axis_doppler)

            # (2.3) resize based on accumulation status and compute magnitude of complex data
            if accumulateStatus:
                micro_doppler_file = np.abs(micro_doppler_file_raw)
            else:
                micro_doppler_file = np.abs(micro_doppler_file_raw[:,0,:]) # first channel selected 

            micro_doppler_spectrum = np.append(micro_doppler_spectrum, micro_doppler_file, axis=1)
            print('micro-doppler dimensions: ' + str(micro_doppler_spectrum.shape))

            # update the active status for next iteration
            data_status = np.size(data_cube)

        # (3) image is names as the raw_data directory     
        image_name = dir_name.split('/')[-1]
        save_file = save_path + image_name + '.jpg'       
        plt.imshow(micro_doppler_spectrum, aspect=2, extent=[0, micro_doppler_spectrum.shape[1]/self.frames_per_second, -max_velocity, max_velocity])
        plt.ylabel('velocity [m/s]')
        plt.xlabel('time [s]')
        
        plt.savefig(save_file, dpi=1000, bbox_inches = 'tight', pad_inches = 0.1)
        #plt.show()
    
        print('micro-doppler image written successfully ...\n')

        return micro_doppler_spectrum





