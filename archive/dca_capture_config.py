"""
@date 03/24/2020
@author: Arvind (parts taken from Soheil's radar config script)
@about:
    The newer SDK's from TI enable recording raw data from DCA1000 using serial. The pipeline for this requires configuring the radar module with lvdsStreamCfg enabled. In addition, the steps for the pipeline are different (explained below) from the conventional radar configuration:
    1. The radar should be configured after and within 30 seconds the DCA is programmed using command prompt in Windows. 
    2. The radar should only be configured and the sensorStop command should not be sent while the DCA is capturing data. (p. 15, mmwave_sdk_user_guide)
    3. 
"""

import serial
import threading
import time
import struct


class awr1843_config:
    def __init__(self, radar_name='Radar1843', cmd_serial_port='COM10', dat_serial_port='COM9', config_file_name=''):

        self.radar_name = radar_name
        self.recieved_data = b''
        self.loaded_config = []
        self.config_file_name = config_file_name

        # open serial ports with 1 sec timeout
        self.serial_cmd = serial.Serial(cmd_serial_port, 115200, timeout=1)
        self.serial_data = serial.Serial(dat_serial_port, 921600, timeout=1)

        self.data_recieved_flag = threading.Event()
        self.active_flag = threading.Event()
        self.buffer_busy_flag = threading.Event()

        self.serial_thread = threading.Thread(target=self.worker_serial_read)
        self.file_thread = threading.Thread(target=self.worker_file_write)
        # t_s = threading.Thread(target=worker_serial_read,args=(0,))
        self.setup()

    def open_serial(self):
        # first close and then open command and data ports

        self.serial_cmd.close()
        self.serial_cmd.open()

        self.serial_data.close()
        self.serial_data.open()
        return

    def close_serial(self):
        # close command and data ports

        self.serial_cmd.close()
        self.serial_data.close()
        return

    def load_config(self, file_name, print_outputs=True):
        # config file has commented text till 'sensorStop', the config data after which is read using 'list_tmp'
        
        file_tmp = open(file_name, 'r')
        str_tmp = file_tmp.read() + '\n'
        self.loaded_config = str_tmp
        tmp_idx = str_tmp.find('sensorStop\n')

        # print(self.radar_name + ' config:\n' + str_tmp[0:tmp_idx])
        file_tmp.close()
        list_tmp = str_tmp[tmp_idx:].splitlines(True)
        time.sleep(0.3)

        # write configs to radar 
        for cnt in range(len(list_tmp)):
            self.serial_cmd.write(list_tmp[cnt].encode('ASCII'))
            time.sleep(0.1)
            if print_outputs:
                print(str(self.serial_cmd.read_until(terminator=b'Done\n')))
            
        print('Configuration successful!\n')
        return

    def stop_radar(self):
        self.serial_cmd.write(b"sensorStop\n")
        strtmp = self.serial_cmd.read_until(terminator=b'Done\n')
        if strtmp != b'':
            print('\n' + self.radar_name + ' Stop successful!\n')
        #            self.active_flag.clear()
        else:
            print('\n' + self.radar_name + ' Stop failed!\nReason:\n')
            print(strtmp)
        self.serial_cmd.read_all()
        return

    def start_radar(self):
        self.serial_cmd.write(b"sensorStart\n")
        strtmp = self.serial_cmd.read_until(terminator=b'Done\n')
        if strtmp != b'':
            print('\n' + self.radar_name + ' Start successful!\n')
            self.active_flag.set()
        else:
            print('\n' + self.radar_name + ' Start failed!\nReason:\n')
            print(strtmp)
        # @arvind
        # stop recording data after record_duration seconds    
        time.sleep(30)  
        print('Recording completed! Exiting ...\n')  
        self.stop_radar()
        return

    def worker_serial_read(self):
        """thread worker serial read function"""
        while self.active_flag.is_set():
            if not self.data_recieved_flag.is_set() and self.serial_data.in_waiting > 0:
                # strtmp=self.serial_data.read_until(b'\x02\x01\x04\x03\x06\x05\x08\x07');
                strtmp = self.serial_data.read_all()
                if (strtmp != b''):
                    # self.buffer_busy_flag.wait();
                    self.buffer_busy_flag.clear()
                    # self.recieved_data=[self.recieved_data,strtmp];
                    self.recieved_data = strtmp
                    self.buffer_busy_flag.set()
                    self.data_recieved_flag.set()
            else:
                time.sleep(0.001)

        return

    def worker_file_write(self):
        """thread worker file write function"""

        """ time-based file naming"""
        time_now = time.ctime().lower()
        str_time = time_now[4:7] + time_now[8:10] + '_' + time_now[11:13] + time_now[14:16] + '_'
        # file format: mrr_mmmdd_hhmm_filname.dat
        full_f_name = 'C:\\work\\rcube_extract\\demo_project\\captured_data\\soheil_rcube\\demo_' + str_time + 'out' + self.data_file_name + '.dat'
        
        while self.active_flag.is_set():
            self.data_recieved_flag.wait()
            
            file_dat = open(full_f_name,'ab+')
            # file_dat = open('captured_data\Record_' + self.radar_name + '_' + str_time + '.dat', 'ab+')
            
            # self.buffer_busy_flag.wait();
            self.buffer_busy_flag.clear()
            tmpdat = self.recieved_data
            # self.recieved_data=b'';
            self.buffer_busy_flag.set()
            file_dat.write(tmpdat)
            # print(tmpdat)
            #            file_dat.write(self.recieved_data)
            file_dat.close()
            #            self.recieved_data=b'';
            self.data_recieved_flag.clear()
        return

    def read_time_stamp(self):

        data = self.recieved_data
        # print(data)
        d1 = data.split(b'\x02\x01\x04\x03\x06\x05\x08\x07')
        print(d1)
        data = d1[1]
        [vrsn, plen, pltfrm, f_no, t_stamp, n_obj, n_tlv, sf_no] = struct.unpack('LLLLLLLL', data[0:32])
        return [t_stamp, f_no]

    def setup(self):
        self.open_serial()
        self.load_config(self.config_file_name)
        #   self.stop_radar()
        #   self.serial_data.flush()
        #   self.active_flag.set()
        #   self.buffer_busy_flag.set()
        #   self.file_thread.start()
        #   self.serial_thread.start()
        return

    def kill(self):
        self.stop_radar()
        self.active_flag.clear()
        self.close_serial()
        return
# -*- coding: utf-8 -*-

