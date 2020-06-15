import numpy as np 
import time
import os, glob, shutil

class DataHandling:

    """
    Tasks related to data capturing, organizing, and preprocessing. 

    """

    def __init__(self, num_samples=256, num_chirps=64, num_tx=1, num_rx=4, fps=10, header_size=32):

        """
        Args:
        - num_samples:      number of samples per chirp (fast time)
        - num_chirps:       number of chirps per frame    (slow time)
        - num_rx:           number of receivers
        - fps:              frame rate (per seconds)
        - header_size:      the actual header size (usually 32 bytes)
        """

        self.num_samples = num_samples
        self.num_chirps = num_chirps
        self.num_tx = num_tx
        self.num_rx = num_rx
        self.fps = fps
        self.header_size = header_size

    def organize_captured_data(self, experiment_name='test', src_dir='/mnt/c/work/mmw_pc/single_chip/datasets/'):
        """
        Organizes raw captured data into a directory named with data specifications and given experiment name (e.g. 'walk').
x
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
        subdir_name = subdir_name + '_fps' + str(self.fps) + '_' + experiment_name 

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
        
    def raw_radarcube(self, raw_data):
        '''
        Obtain raw radarcube from captured binary data file.

        Args:
            - raw_data:         the raw data read from file

        Outputs:
            - radarcube:        raw data radarcube (axes: fast_time, slow_time, channels, frames)
            - next_frame_data:  data of unifinished next frame

        Issues and To-do's:
            - for multiple-tx case
        '''

        IQ = 2
        chirp_data_size = self.num_samples * self.num_rx * IQ + self.header_size  # across all receivers 

        # (1) compute last unfinished frame data 
        count_remove = np.size(raw_data) % (chirp_data_size * self.num_chirps)   
        next_frame_data = raw_data[-count_remove:] # second return object

        # (2) reshape complete frames to total_chirps x chirp_data_size format
        # the first 32 entries in each row belong to the HSI header data
        num_frames = np.size(raw_data[:-count_remove]) // (chirp_data_size * self.num_chirps)
        data_mat = np.reshape(raw_data[:-count_remove], (num_frames * self.num_chirps, chirp_data_size))
        # print('number of samples removed: ' + str(count_remove))
        # print('reshaped raw data size: ' + str(data_mat.shape))

        # (3) convert data to complex format 
        data_mat_complex = np.zeros((num_frames * self.num_chirps, self.num_samples * self.num_rx), dtype=complex)
        data_mat_complex = data_mat[:,self.header_size::2]   + data_mat[:,self.header_size+1::2]*1j  

        # (3.1) 18xx format (suggested by TI - but did not work, used above instead)
        #data_mat_complex[:,0::2] = data_mat[:,header_size::4] + data_mat[:,header_size+2::4]*1j
        #data_mat_complex[:,1::2] = data_mat[:,header_size+1::4] + data_mat[:,header_size+3::4]*1j

        # (4) reshape to 4D datacube (particular axes due to C-type reshaping, transposed later)

        # (4.1) the strange order of radarcube dimensions is due to order of reshaping in C-type order  
        radarcube = np.zeros((num_frames, self.num_chirps, self.num_rx, self.num_samples), dtype=complex)
        radarcube = np.reshape(data_mat_complex, (num_frames, self.num_chirps, self.num_rx, self.num_samples))

        # (4.2) radarcube output (axes: fast_time, slow_time, channels, frames)
        return np.transpose(radarcube,(3,1,2,0)), next_frame_data

    
    def raw_data_cube(self, dir_name):
        '''
        Generator function that yeilds raw_data_cube iterator for each ADC raw data file.
            Inputs:
                - dir_name:     full path of raw data directory
            Outputs:
                - data_cube:    generator output for raw data cube. Usage: generator_name = DataHandling.raw_data_cube(dir_name); data_cube = next(generator_name) 
        '''
        # (1) parameters

        # (1.1) vary with every iteration
        file_index = 0
        prev_file_data = np.array([])
        data_flag = 1
        # (1.2) fixed parameters
        packet_len = self.num_samples *  self.num_rx * 2 + self.header_size 
        data_files = glob.glob(dir_name + '/datacard_record_hdr_0ADC*.bin')
        #print(data_files)
        # (1.3) file reading status parameter

        # (2) yield rawdatacube while data_flag active 
        while data_flag:
            # (2.1) read data from file in current iteration and append data left in previous iteration 
            #print(file_index)
            current_file = data_files[file_index]
            raw_data = np.fromfile(current_file, dtype=np.int16)
            raw_appended = np.insert(raw_data, 0, prev_file_data) #insert in the beginning

            # (2.2) select HSI header as first 32 words of ADC0 file
            if file_index == 0:
                hsi_header = raw_data[0 : self.header_size]

            # (2.2.1) sanity check for header locations and proper rcube size 
            error1 = np.array_equal(raw_appended[0 : np.size(hsi_header)], hsi_header) == 0
            error2 = np.array_equal(raw_appended[packet_len:packet_len+np.size(hsi_header)], hsi_header) == 0
            if error1 or error2:
                print("Warning: headers don't match... something wrong with data unwrapping")
                print('hsi_header:                  ' + str(hsi_header))
                print('1st hsi header in next file: ' + str(raw_appended[0 : np.size(hsi_header)]))
                print('2nd hsi header in next file: ' + str(raw_appended[packet_len:packet_len+np.size(hsi_header)]))
                assert 1==0, "HSI headers don't match..."

            # (2.3) call raw_radarcube script to reshape the data into data_cube and incomplete next frame data
            data_cube, next_frame_data = self.raw_radarcube(raw_appended)
            #print('file index: ' + str(file_index) + ' | datacube shape' + str(data_cube.shape))  # for debug, print the shape
        
            # (2.4) change variable values for next iteration 
            prev_file_data = next_frame_data     
            file_index += 1  
            data_flag = file_index < len(data_files) 

            yield data_cube



