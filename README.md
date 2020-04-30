# mm-radar

v1.0.1
- Some minor fixes to v1.0.0 and reorganization of functions into modules.

- The binary data files contain real and complex part of samples as separate words. Earlier the real and complex parts of the samples were combined using the interleaving approach recommended by Texas Instruments, however, it was leading to images present in the micro-Doppler spectrogram as well as range-Doppler FFT video. This issue is fixed in this version after find proper interleaving approach by trial and error. 
- The processing_chain script is updated to ProcessingChain class.
- The following function reoganizations were carried out to make modules more intuitive
  + All raw-data handling related functions are moved to data_handling module while all processing related functions to processing_chain module. i.e.:
    > DataHandling class contains functions organize_captured_data, raw_radarcube, and raw_data_cube.
    > ProcessingChain class contains functions doppler_processing_custom, range_doppler_processing, and micro_doppler_stft. 
    > A short description of these functions is provided in readme for v1.0.0 below as well as with the function in modules. 
    

v1.0.0
- Modules designed to process high-speed raw ADC data captured using AWR1843 + DCA1000 setup. The data recorded is continuously stored into 64 MB files of format datacard_record_hdr_0ADC_{}.bin, where {} has numbers starting from 0. 

- Here's short description of modules:
  + config_radar.py: contains class CustomConfig that programs 1843 with select designed configuations
  
  + processing_chain.py: script that contains the following functions:
    > raw_datacube: Preprocessing of binary data files to obtain raw-data radarcube. 
    > doppler_processing_custom: A custom implementation of doppler dimension FFT using the scripts from OpenRadar project. The dopper_processing function in OpenRadar was not meeting some of the requirements. 
    
  + data_handling.py: contains class DataHandle that has following functions:
    > organize_captured_data: organizes the captured raw data into a folder with name containing current time, number of trx, num of samples and number of chirps per frame, fps, and experiment specifications. This function is run directly after data capture to organize the captured data.  
    > raw_data_cube: Generator function that yeilds raw_data_cube iterator for each ADC raw data file. This function uses the raw_datatcube function in processing_chain.py script.
    > range_doppler_process: Compute range-doppler fft on raw data and save the output as a video. 
    > micro_doppler_stft: generates and saves short-time Fourier transform based micro-Doppler spectrogram image.
   
   + run_main.py: A script to run different actions: configuring radar, organizing data, range-doppler processing, micro-doppler processing

