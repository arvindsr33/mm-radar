import numpy as np 
from mmwave.dsp.doppler_processing import *


def raw_radarcube(raw_data, num_samples, num_chirps, num_rx, header_size=32):
    '''
    Obtain raw radarcube from captured binary data file.

    Args:
        - raw_data:         the raw data read from file
        - num_samples:      number of samples per chirp (fast time)
        - num_chirps:       number of chirps per frame    (slow time)
        - num_rx:           number of receivers
        - header_size:      the actual header size (usually 32 bytes)

    Outputs:
        - radarcube:        raw data radarcube (axes: fast_time, slow_time, channels, frames)
        - next_frame_data:  data of unifinished next frame

    Issues and To-do's:
        - for multiple-tx case
    '''
 
    IQ = 2
    chirp_data_size = num_samples*num_rx*IQ + header_size  # across all receivers 

    # (1) compute last unfinished frame data 
    count_remove = np.size(raw_data) % (chirp_data_size * num_chirps)   
    next_frame_data = raw_data[-count_remove:] # second return object

    # (2) reshape complete frames to total_chirps x chirp_data_size format
    # the first 32 entries in each row belong to the HSI header data
    num_frames = np.size(raw_data[:-count_remove]) // (chirp_data_size * num_chirps)
    data_mat = np.reshape(raw_data[:-count_remove], (num_frames*num_chirps, chirp_data_size))
    # print('number of samples removed: ' + str(count_remove))
    # print('reshaped raw data size: ' + str(data_mat.shape))

    # (3) convert data to complex format 
    data_mat_complex = np.zeros((num_frames*num_chirps, num_samples*num_rx), dtype=np.int16) + np.zeros((num_frames*num_chirps, num_samples*num_rx), dtype=np.int16)*1j # complex initialization
    data_mat_complex[:,0::2] = data_mat[:,header_size::4] + data_mat[:,header_size+2::4]*1j
    data_mat_complex[:,1::2] = data_mat[:,header_size+1::4] + data_mat[:,header_size+3::4]*1j

    # (4) reshape to 4D datacube (particular axes due to C-type reshaping, transposed later)

    # the strange order of radarcube dimensions is due to order of reshaping in C-type order  
    radarcube = np.zeros((num_frames, num_chirps, num_rx, num_samples), dtype=np.int16) + np.zeros((num_frames, num_chirps, num_rx, num_samples), dtype=np.int16)*1j
    radarcube = np.reshape(data_mat_complex, (num_frames, num_chirps, num_rx, num_samples))

    # radarcube output (axes: fast_time, slow_time, channels, frames)
    return np.transpose(radarcube,(3,1,2,0)), next_frame_data


def doppler_processing_custom(radar_cube, num_tx=1, clutter_removal_enabled=False, interleaved=False, window_type_2d=None, accumulate=False, axis=1):

    '''
    Custom Doppler processing module for obtaining Doppler FFT on the N-D FFT data. 
    Steps:
        - static clutter removal
        - windowing
        - fft followed by fftshift in the doppler dimension

    Args:
        - radar_cube : raw data 3/4-D cube
        - num_tx: for interleaved processing
    Output:
        - N-1 dimension output if accumulate otherwise N dimension cube 

    The axes, if present, are assumed in the following order:
        - range
        - doppler
        - channel
        - frame

    Issues and To-do's:
        1. Interleaved implementation
    '''
    channel_axis = axis + 1 # num channels axis 

    # assign doppler_axis as first axis (0). It's required for broadcasting and subsequent processing
    axes_vals = np.arange(len(radar_cube.shape))
    axes_vals[0] = axis
    axes_vals[axis] = 0
    fft2d_in = np.transpose(radar_cube, axes_vals)

    # (Optional) Static Clutter Removal
    if clutter_removal_enabled:
        fft2d_in = compensation.clutter_removal(fft2d_in, axis=0)

    # Windowing 16x32
    if window_type_2d:
        fft2d_in = utils.windowing(fft2d_in, window_type_2d, axis=0)

    fft2d_out = np.fft.fft(fft2d_in, axis=0)
    fft2d_out = np.fft.fftshift(fft2d_out, axes=0)

    # transpose back the radarcube to original format before returning the output
    fft2d_out = np.transpose(fft2d_out, axes_vals)

    # Log_2 Absolute Value
    fft2d_log_abs = np.log2(np.abs(fft2d_out) + 1e-4) #add a dummy for zero values  

    if accumulate:
        # accumulate
        return np.sum(fft2d_log_abs, axis=channel_axis) 
    else:
        return fft2d_out
