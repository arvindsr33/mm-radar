import numpy as np 
import cv2
import os, shutil, glob
import tkinter as tk
from tkinter import filedialog
import time 
import skvideo.io # pip install scikit-video
import matplotlib.pyplot as plt
from mmwave import dsp
from data_handling import DataHandling


class ProcessingChain:

    def __init__(self, num_samples=256, num_chirps=64, num_tx=1, num_rx=4, fps=10, accumulate_channels=True):

        self.num_samples = num_samples
        self.num_chirps = num_chirps
        self.num_tx = num_tx
        self.num_rx = num_rx
        self.fps = fps
        self.accumulate_channels = accumulate_channels
        self.data_handle = DataHandling(self.num_samples, self.num_chirps, self.num_tx, self.num_rx, self.fps)

    def doppler_processing_custom(self, radar_cube, clutter_removal_enabled=False, interleaved=False, window_type_2d=None, axis=1):

        '''
        Custom Doppler processing module for obtaining Doppler FFT on the N-D FFT data. 

        Args:
            - radar_cube : raw data 3/4-D cube
        Output:
            - FFT across defined axis and in same shape and input 
        Issues and To-do's:
            1. Interleaved implementation
        '''

        # assign doppler_axis as first axis (0). It's required for broadcasting and subsequent processing
        axes_vals = np.arange(len(radar_cube.shape))
        axes_vals[0] = axis
        axes_vals[axis] = 0
        fft2d_in = np.transpose(radar_cube, axes_vals)

        # (Optional) Static Clutter Removal
        if clutter_removal_enabled:
            fft2d_in = dsp.compensation.clutter_removal(fft2d_in, axis=0)

        # Windowing 16x32
        if window_type_2d:
            fft2d_in = dsp.utils.windowing(fft2d_in, window_type_2d, axis=0)

        fft2d_out = np.fft.fft(fft2d_in, axis=0)
        fft2d_out = np.fft.fftshift(fft2d_out, axes=0)

        # transpose back the radarcube to original format before returning the output
        fft2d_out = np.transpose(fft2d_out, axes_vals)

        return fft2d_out

    def range_doppler_process(self, dir_name, save_path='/mnt/c/work/rcube_extract/dca_capture/video_write/', log_scaled=False):

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
        out = cv2.VideoWriter(video_file, cv2.VideoWriter_fourcc('M','J','P','G'), self.fps, (frame_width, frame_height), isColor=False)

        # (2) implement range-doppler processing
        
        axis_range = 0
        axis_doppler = 1
        axis_channel = 2

        index_channel = 0   # if accumulation disabled 

        # (2.1) initiate the raw_data generator function
        raw_data = self.data_handle.raw_data_cube(dir_name)
        data_status = True

        while data_status:
            rcube = next(raw_data, [])   # output 0 when no done reading all data files
            data_status = np.size(rcube)
            if len(rcube) == 0:
                break

            # (2.2) peform range-doppler ffts 
            fft1d_out = dsp.range_processing(rcube, window_type_1d=dsp.Window.HAMMING, axis=axis_range) 
            fft2d_out = self.doppler_processing_custom(fft1d_out, clutter_removal_enabled=True, 
            interleaved=False, window_type_2d=dsp.Window.HAMMING, axis=axis_doppler)
                    
            # (2.3) data shaping (log scaling followed by accumulation/channel selection)
            
            fft2d_log_process = 10*np.log10(np.abs(fft2d_out) + 1e-4) if log_scaled else fft2d_out 
            fft2d_channel_process = np.sum(fft2d_log_process, axis=axis_channel) if self.accumulate_channels else fft2d_log_process[:,:,index_channel,:] 

            # (2.4) select range spectrum in video and compute magnitude of complex data
            # video_in = np.abs(rcube_fft2_tr[:, :num_samples//2, :])   # remove negative frequencies 
            video_in = np.abs(np.transpose(fft2d_channel_process, (1,0,2)))    # for full range spectrum 
            # print(video_in.shape)

            # (2.4.1) debug: plot sample images 
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
                if frame == 0: # // for debugging 
                    print(img_normalize)
                
        # (3) release the video object    
        out.release()
        print('range-doppler video written successfully ...\n')
        return
        
    def micro_doppler_stft(self, dir_name, max_velocity, save_path = '/mnt/c/work/rcube_extract/dca_capture/micro_doppler/', accumulate_channels=False):

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
        axis_channel = 1 # since range axis is removed

        index_channel = 0

        data_status = True
        micro_doppler_spectrum = np.zeros((self.num_chirps, 0))

        # (1) instantiate the raw_data generator

        raw_data = self.data_handle.raw_data_cube(dir_name)
        # print(type(raw_data))

        # (2) keep appending micro-doppler spectrogram while data_status is active
        while data_status:
            # (2.0) read the next data_cube from generator
            data_cube = next(raw_data, [0]) 

            # (2.1) perform range-fft and sum over range axis
            if len(data_cube) == 1:
                break 

            data_cube_fft1 = dsp.range_processing(data_cube, window_type_1d=dsp.Window.HAMMING, axis=axis_range)
            data_range_accum = np.sum(data_cube_fft1, axis=axis_range)
            # print(data_range_accum.shape)

            # (2.2) perform doppler-fft 
            micro_doppler_raw = self.doppler_processing_custom(data_range_accum,  clutter_removal_enabled=True, 
            interleaved=False, window_type_2d=dsp.Window.HAMMING, axis=axis_doppler)
            
            micro_doppler = np.sum(10*np.log(np.abs(micro_doppler_raw) + 1e-4), axis=axis_channel) if self.accumulate_channels else 10*np.log(np.abs(micro_doppler_raw[:,index_channel,:]))

            micro_doppler_spectrum = np.append(micro_doppler_spectrum, micro_doppler, axis=1)
            print('micro-doppler dimensions: ' + str(micro_doppler_spectrum.shape))

            # update the active status for next iteration
            data_status = np.size(data_cube)

        # (3) image is names as the raw_data directory     
        image_name = dir_name.split('/')[-1]
        save_file = save_path + image_name + '.jpg'       
        plt.imshow(micro_doppler_spectrum, aspect=2, extent=[0, micro_doppler_spectrum.shape[1]/self.fps, -max_velocity, max_velocity], cmap='gnuplot2')
        plt.ylabel('velocity [m/s]')
        plt.xlabel('time [s]')
        plt.colorbar(label='log scale')
        plt.savefig(save_file, dpi=1000, bbox_inches = 'tight', pad_inches = 0.1)
        plt.close()
    
        print('micro-doppler image written successfully ...\n')

        return micro_doppler_spectrum

