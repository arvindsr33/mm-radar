# install required libraries
# for mmwave - pip install openradar

import numpy as np 
import time 
from mmwave.dsp.range_processing import *  
from processing_chain import * 
import skvideo.io 
import matplotlib.pyplot as plt
import cv2

time_ms = lambda: int(round(time.time() * 1000))
start_time = time_ms()

# radar specifications 
num_samples = 256
num_chirps = 64
num_tx = 1
num_rx = 4
frames_per_second = 20

# enter the directory and specify data parameters
header_size = 32
pathname = '/mnt/c/work/rcube_extract/dca_capture/mySavedData/record_trx14_230_64mb_P64/'
filename = 'datacard_record_hdr_0ADC_{0}.bin'

fullfile = pathname + filename
raw_data = np.fromfile(filename, dtype=np.int16)

# radarcube dimensions:  0 - fast time; 1 - slow time; 2 - channels; 3 - time progression (frames)
rcube = organize(raw_data, num_chirps, num_rx, num_samples, header_size)
print('radarcube dimensions: ' + str(rcube.shape))
rcube_formattime = time_ms()
print('rcube formatting time: ' + str(rcube_formattime - start_time) + ' ms\n')

'''
Now, start processing the data. 
Firstly, perform 2-D FFT to obtain range-Doppler FFT plot.
Save the output as video for interpretation and further use. 
Also, create plot for verification of range-Doppler FFT. 
'''

axis_range = 0
axis_doppler = 1

rcube_fft1 = range_processing(rcube, window_type_1d=None, axis=axis_range)
rcube_fft2 = doppler_processing_custom(rcube_fft1, num_tx_antennas=1, clutter_removal_enabled=False, interleaved=False, window_type_2d=None, accumulate=False, axis=axis_doppler)
print('accumulated rcube dimensions: ' + str(rcube_fft2.shape))

fft_processtime = time_ms()
print('fft processing time: ' + str(fft_processtime - rcube_formattime) + ' ms\n')

'''
Write the output as a video
'''
# convert to proper format 
rcube_fft2_tr = np.transpose(rcube_fft2, (1,0,2))
video_in = rcube_fft2_tr #[:, :num_samples//2, :]
print(video_in.shape)

# plot sample images 
plt.imshow(video_in[:,:,1])
plt.show()

# Define the codec and create VideoWriter object.The output is stored in 'outpy.avi' file.
# Define the fps to be equal to 10. Also frame size is passed.
frame_width = video_in.shape[1]
frame_height = video_in.shape[0]

out = cv2.VideoWriter('/mnt/c/work/rcube_extract/dca_capture/video_write/rcube_test.avi',cv2.VideoWriter_fourcc(*'DIVX'), frames_per_second, (frame_width,frame_height), isColor=False)

for frame in range(video_in.shape[2]):        
    img_normalize = cv2.normalize(src=video_in[:,:,frame], dst=None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX, dtype=cv2.CV_8U)
    out.write(img_normalize)

out.release()