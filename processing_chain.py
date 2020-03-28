import numpy as np 
from mmwave.dsp.doppler_processing import *


def organize(raw_data, num_chirps, num_rx, num_samples, header_size=32):
    '''
    Preprocessing of raw data to obtain raw-data radarcube. 
    '''
    IQ = 2
    header_data_size = num_samples*num_rx*IQ + header_size  

    # the last frame in current data file would generally continue to next file
    # so the incomplete frame data is removed and saved to be used with next file. 
    count_remove = np.size(raw_data) % (header_data_size * num_chirps)    
    total_chirps = np.size(raw_data) // (header_data_size)
    num_frames = total_chirps // num_chirps
    print('number of frames in the data: ' + str(num_frames))
    # print('number of samples removed: ' + str(count_remove))

    # reshape the data to total_chirps * num_samples_raw matrix format
    # the first 32 entries in each row belong to the HSI header data
    data_mat = np.reshape(raw_data[:-count_remove], (num_frames*num_chirps, header_data_size))
    # print('reshaped raw data size: ' + str(data_mat.shape))

    # defining complex matrix to overcome potential complex to real value casting (ComplexWarning)
    data_mat_complex = np.zeros((num_frames*num_chirps, num_samples*num_rx), dtype=np.int16) + np.zeros((num_frames*num_chirps, num_samples*num_rx), dtype=np.int16)*1j
    data_mat_complex[:,0::2] = data_mat[:,header_size::4] + data_mat[:,header_size+2::4]*1j
    data_mat_complex[:,1::2] = data_mat[:,header_size+1::4] + data_mat[:,header_size+3::4]*1j

    # converting data to radarcube, which is a 4D array 

    # the strange order of radarcube dimensions is due to order of reshaping in C-type order  
    radarcube = np.zeros((num_frames, num_chirps, num_rx, num_samples), dtype=np.int16) + np.zeros((num_frames, num_chirps, num_rx, num_samples), dtype=np.int16)*1j

    radarcube = np.reshape(data_mat_complex, (num_frames, num_chirps, num_rx, num_samples))

    # radarcube output dimensions:  0 - fast time; 1 - slow time; 2 - channels; 3 - time progression (frames)
    return np.transpose(radarcube,(3,1,2,0))


def doppler_processing_custom(radar_cube, num_tx_antennas=1, clutter_removal_enabled=False, interleaved=False, window_type_2d=None, accumulate=False, axis=1):

    '''
    Custom Doppler processing module for obtaining Doppler FFT on the 4-D FFT data.
    Default axes are: (range, doppler, channel, frame), so the default doppler axis is 1
    Not implemented: 
        interleaving
        windowing
    To-do's:
        automate the axis selection
    '''
    
    fft2d_in = radar_cube

    # transpose to create doppler_axis as first axis (0). It's required for broadcasting and subsequent processing
    fft2d_in = np.transpose(fft2d_in, axes=(1, 0, 2, 3))

    # (Optional) Static Clutter Removal
    if clutter_removal_enabled:
        fft2d_in = compensation.clutter_removal(fft2d_in, axis=0)

    # Windowing 16x32
    #if window_type_2d:
    #    fft2d_in = utils.windowing(fft2d_in, window_type_2d, axis=0)

    fft2d_out = np.fft.fft(fft2d_in, axis=0)
    fft2d_out = np.fft.fftshift(fft2d_out, axes=0)

    # transpose back the radarcube to original format before returning the output
    fft2d_out = np.transpose(fft2d_out, (1,0,2,3))

    # Log_2 Absolute Value
    fft2d_log_abs = np.log2(np.abs(fft2d_out) + 1e-4) #add a dummy for zero values  

    if accumulate:
        # accumulate
        return np.sum(fft2d_log_abs, axis=2) 
    else:
        # return absolute value of first rx channel data
        # third axis (2) is channel axis
        return np.abs(fft2d_out[:,:,0,:])
