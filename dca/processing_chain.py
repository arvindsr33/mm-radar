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
from mpl_toolkits.axes_grid1 import make_axes_locatable

class ProcessingChain:
    """
    TO DO: 
        - add description of the class
        - fix issue with range doppler video generation
        - add parameters dict to input processing parameters 
    """

    def __init__(self, num_samples=256, num_chirps=64, num_tx=1, num_rx=4, fps=10, window=3, interp_factor=1, accumulate_channels=True):

        self.num_samples = num_samples
        self.num_chirps = num_chirps
        self.num_tx = num_tx
        self.num_rx = num_rx
        self.fps = fps
        self.window_name = None 
        self.interp_factor = interp_factor
        self.accumulate_channels = accumulate_channels
        self.data_handle = DataHandling(self.num_samples, self.num_chirps, self.num_tx, self.num_rx, self.fps)
        
        # assign window name
        '''
        if window == 0:
            self.window_name == None 
        elif window == 1:
            self.window_name = dsp.Window.BARTLETT
        elif window == 2:
            self.window_name = dsp.Window.HAMMING
        elif window == 3:
            self.window_name = dsp.Window.HANNING
        else:
            self.window_name = dsp.Window.HAMMING'''
        if window == 0:
            self.window_name = None
        elif window == 1:
            self.window_name = dsp.Window.barthann
        elif window == 2:
            self.window_name = dsp.Window.bartlett
        elif window == 3:
            self.window_name = dsp.Window.cosine
        elif window == 4:
            self.window_name = dsp.Window.general_cosine
        elif window == 5:
            self.window_name = dsp.Window.hamming
        elif window == 6:
            self.window_name = dsp.Window.hann
        else:
            self.window_name = dsp.Window.hamming
        

    
    def doppler_processing_custom(self, radar_cube, clutter_removal_enabled=True, interleaved=False, window_type_2d=None, axis=1):

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
        fft1d_out = np.transpose(radar_cube, axes_vals)

        # Static Clutter Removal
        if clutter_removal_enabled:
            fft1d_out = dsp.compensation.clutter_removal(fft1d_out, axis=0)

        # Windowing 16x32
        if window_type_2d:
            fft2d_in = dsp.utils.windowing(fft1d_out, window_type_2d, axis=0)
        else:
            fft2d_in = fft1d_out

        # Perform FFT followed by FFTshift        
        fft2d_out = np.fft.fft(fft2d_in, n=self.num_chirps*self.interp_factor, axis=0)
        fft2d_out = np.fft.fftshift(fft2d_out, axes=0)

        # transpose back the radarcube to original format before returning the output
        fft2d_out = np.transpose(fft2d_out, axes_vals)

        return fft2d_out

    def range_doppler_process(self, dir_name, log_scaled=False, process_single_datafile=False, normalize=True, save_path='/mnt/c/work/mmw_pc/single_chip/processing_results/range_doppler_vidoes/'):
        # NOTE: remove the single iteration limit after this analysis

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
        frame_width = self.num_samples 
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

        # output radarcube np array
        radarcube = np.zeros((self.num_chirps * self.interp_factor, self.num_samples, 0))

        if process_single_datafile:
            rcube = next(raw_data, [])   # output 0 when no done reading all data files

            # (2.2) peform range-doppler ffts 
            fft1d_out = dsp.range_processing(rcube, window_type_1d=self.window_name, axis=axis_range) 
            fft2d_out = self.doppler_processing_custom(fft1d_out, clutter_removal_enabled=True, 
                        interleaved=False, window_type_2d=self.window_name, axis=axis_doppler)
                    
            # (2.3) data shaping (log scaling followed by accumulation/channel selection)
            fft2d_log_process = 10*np.log10(np.abs(fft2d_out) + 1e-4) if log_scaled else fft2d_out 
            fft2d_channel_process = np.sum(fft2d_log_process, axis=axis_channel) if self.accumulate_channels else fft2d_log_process[:,:,index_channel,:] 

            # (2.4) select range spectrum in video and compute magnitude of complex data
            video_in = np.abs(np.transpose(fft2d_channel_process, (1,0,2)))    # for full range spectrum 

            # (2.5) normalize and write the frame to video object
            if normalize:
                for frame in range(video_in.shape[2]):
                    # (2.5.1) normalize to [0, 255] for each frame
                    min = np.amin(video_in[:, :, frame], (0,1))
                    max = np.amax(video_in[:, :, frame], (0,1))
                    video_in[:, :, frame] = (video_in[:, :, frame] - min) / (max - min)
                    video_in[:, :, frame] = np.round(video_in[:, :, frame] * 255).astype(np.uint8)
                    if frame == 0: # // for debugging 
                        print(video_in[:, :, 0])
                
                # append the frame to output radarcube array
                #radarcube = np.append(radarcube, img_normalize.reshape(*img_normalize.shape,1), axis=2)
            
            radarcube = np.append(radarcube, video_in, axis=2)
    
            # (3) release the video object    
            out.release()
            return radarcube
            
        while data_status: # //NOTE: uncomment it after analysis
            rcube = next(raw_data, [])   # output 0 when no done reading all data files
            data_status = np.size(rcube)
            if len(rcube) == 0:
                break     # enable break here

            # (2.2) peform range-doppler ffts 
            fft1d_out = dsp.range_processing(rcube, window_type_1d=self.window_name, axis=axis_range) 
            fft2d_out = self.doppler_processing_custom(fft1d_out, clutter_removal_enabled=True, 
                        interleaved=False, window_type_2d=self.window_name, axis=axis_doppler)
                    
            # (2.3) data shaping (log scaling followed by accumulation/channel selection)
            fft2d_log_process = 10*np.log10(np.abs(fft2d_out) + 1e-4) if log_scaled else fft2d_out 
            fft2d_channel_process = np.sum(fft2d_log_process, axis=axis_channel) if self.accumulate_channels else fft2d_log_process[:,:,index_channel,:] 

            # (2.4) select range spectrum in video and compute magnitude of complex data
            video_in = np.abs(np.transpose(fft2d_channel_process, (1,0,2)))    # for full range spectrum 

            # (2.5) normalize and write the frame to video object
            if normalize:
                for frame in range(video_in.shape[2]):
                    # (2.5.1) normalize to [0, 255] for each frame
                    # img_normalize = cv2.normalize(src=video_in[:, :, frame], dst=None, alpha=0, beta=255, norm_type=cv2.NORM_L1, dtype=cv2.CV_8U)
                    min = np.amin(video_in[:, :, frame], (0,1))
                    max = np.amax(video_in[:, :, frame], (0,1))
                    video_in[:, :, frame] = (video_in[:, :, frame] - min) / (max - min)
                    video_in[:, :, frame] = np.round(video_in[:, :, frame] * 255).astype(np.uint8)
                    if frame == 0: # // for debugging 
                        print(video_in[:, :, 0])
                
                    # append the frame to output radarcube array
                    #radarcube = np.append(radarcube, video_in.reshape(*video_in[:, :, frame].shape,1), axis=2)
            radarcube = np.append(radarcube, video_in, axis=2)

        # (3) release the video object    
        out.release()
        print('range-doppler video written successfully ...\n')
        return radarcube
        
    def micro_doppler_stft(self, dir_name, max_velocity, normalize=False, accum_type=0, save_path='/mnt/c/work/mmw_pc/single_chip/processing_results/micro_doppler_plots/', y_label='frequency'):

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
        #     choose windows from BARTLETT, BLACKMAN, HAMMING, HANNING (default: None)

        axis_range = 0
        axis_doppler = 0 # range axis is removed before doppler processing (during range accumulation)
        axis_channel = 1 # since range axis is removed 
        index_channel = 0

        data_status = True
        micro_doppler_spectrum = np.zeros((self.num_chirps * self.interp_factor, 0))

        # (1) instantiate the raw_data generator
        raw_data = self.data_handle.raw_data_cube(dir_name)
        # print(type(raw_data))

        # (2) keep appending micro-doppler spectrogram while data_status is active
        while data_status:
            # (2.0) read the next data_cube from generator
            data_cube = next(raw_data, [0]) 

            # (2.1) perform range-fft and accumulate over range axis
            if len(data_cube) == 1:
                break 
            data_cube_fft1 = dsp.range_processing(data_cube, window_type_1d=dsp.Window.hamming, axis=axis_range)
            #print(data_cube_fft1.shape)

            # (2.1.1) accumulate power if enabled (accum_type: 1)

            if accum_type == 1: # power accumulation 
                data_range_accum =  np.sum(data_cube_fft1[:, :, :, :] * data_cube_fft1[:, :, :, :], axis=axis_range)
            else: 
                data_range_accum = np.sum(data_cube_fft1[:, :, :, :], axis=axis_range)


            # (2.2) perform doppler-fft and append to output spectrum 
            micro_doppler_raw = self.doppler_processing_custom(data_range_accum, clutter_removal_enabled=True, 
            interleaved=False, window_type_2d=dsp.Window.bartlett, axis=axis_doppler)
            
            if self.accumulate_channels:
                micro_doppler = 10*np.log10(np.sum(np.abs(micro_doppler_raw), axis=axis_channel) + 1e-10) + 30
            else:
                micro_doppler = 10*np.log10(np.abs(micro_doppler_raw[:,index_channel,:]) + 1e-10) + 30

            # (2.3) normalize the micro-Doppler
            if normalize: 
                for frame in range(micro_doppler.shape[1]):
                    # (2.3.1) normalize to [0, 255] for each frame
                    min = np.amin(micro_doppler[:, frame])
                    max = np.amax(micro_doppler[:, frame])
                    micro_doppler[:, frame] = (micro_doppler[:, frame] - min) / (max - min)
                    micro_doppler[:, frame] = np.round(micro_doppler[:, frame] * 255).astype(np.uint8)
                
            micro_doppler_spectrum = np.append(micro_doppler_spectrum, micro_doppler, axis=1)
            #print('micro-doppler dimensions: ' + str(micro_doppler_spectrum.shape))

            # (2.3) update the active status for next iteration
            data_status = np.size(data_cube)

        # (3) image is names as the raw_data directory     
        image_name = dir_name.split('/')[-1]
        save_file = save_path + image_name + '.jpg' 

        # (3.1) use ylabel as frequency if specified in the input
        ymin = -max_velocity / (3e8/77e9/2) /1e3 if y_label == 'frequency' else -max_velocity 
        ymax =  max_velocity / (3e8/77e9/2) /1e3 if y_label == 'frequency' else  max_velocity
        
        plt.rcParams['figure.figsize'] = [micro_doppler_spectrum.shape[1]/50, micro_doppler_spectrum.shape[0]/50]        
        plt.figure()
        ax = plt.gca()
        im = ax.imshow(micro_doppler_spectrum, extent=[0, micro_doppler_spectrum.shape[1]/self.fps, ymin, ymax], cmap='gnuplot2')

        if y_label == 'frequency':
            plt.ylabel('frequency [kHz]') 
        else:
            plt.ylabel('velocity [m/s]')
        plt.xlabel('time [s]')

        divider = make_axes_locatable(ax)
        cax = divider.append_axes("right", size="2%", pad=0.02)
        plt.colorbar(im, label='power (dBm)', cax=cax)
        plt.savefig(save_file, dpi=1000, bbox_inches = 'tight', pad_inches = 0.1)
        plt.close()
    
        print('micro-doppler image written successfully ...\n')

        return micro_doppler_spectrum

