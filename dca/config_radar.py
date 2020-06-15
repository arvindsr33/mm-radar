#from mmwave.dataloader.radars import TI
from mmwave.dataloader.radars import TI
import math 

class CustomConfig:
    """
    read the default configuration file 
    take the radar specification inputs and modify the config values accordingly

    Modifications:
    v1.0.1: default config option enabled 

    """

    def __init__(self, cli_loc='/dev/ttyS4', data_loc='/dev/ttyS3', num_tx=1, num_rx=4, res_range=0.05, max_range=8, max_velocity=2, fps=20, fs=3200, use_defaults=False, config_file='profiles/profile_default.cfg'):
        # (0) instantiate the class parameters 
        self.cli_loc = cli_loc
        self.data_loc = data_loc
        self.num_rx = num_rx
        self.num_tx = num_tx
        self.range_resolution = res_range
        self.max_range = max_range
        self.max_velocity = max_velocity
        self.frames_per_second = fps
        self.dig_out_sample_rate = fs
        self.config_file = config_file
        self.use_defaults = use_defaults

    def _run_config(self):
        """
        The parameters in the default config file are appropriately modified using radar specifications provided. Afterwards, the radar is programmed and resultant specifications are retured. 

        """
        # (1) compute config parameters from specification provided 

        # (1.1) defaults
        # num_frames = 0 # infinite
        start_freq = 77
        wavelength = 3e8 / start_freq / 1e9
        duty_cycle = 0.5

        # (1.2) compute parameters  
        num_samples = round(self.max_range / self.range_resolution / 0.9)   # max achievable range is 90% of the computed value
        freq_slope_const = 0.9 * 3e8 * self.dig_out_sample_rate / 2 / self.max_range / 1e9
        ramp_end_time = round(num_samples * 1e3/ self.dig_out_sample_rate ) + 9 # keeping bandwith 10% higher than sampling duration
        idle_time = round(wavelength * 1e6 / 4 / self.max_velocity - ramp_end_time)
        frame_periodicity = 1e3 / self.frames_per_second # frame duration in ms
        num_chirps = math.floor(duty_cycle * frame_periodicity * 1e3 / (ramp_end_time + idle_time))  # calculate num_chirps at 50% frame cycle
        num_chirps -= num_chirps % 4 # dsp dpu requirements 

        # (1.3) assert errors if constraints violated 
        effective_duty_cycle = duty_cycle * idle_time / (idle_time + ramp_end_time)
        print('Effective duty cycle: ' + str(round(effective_duty_cycle*100)) + ' %')
        assert effective_duty_cycle <= 0.5, 'Effective duty cycle exceeds 50 %'
        assert freq_slope_const * ramp_end_time < 4e3, 'Invalid parameters... bandwidth exceeds 4 GHz! '
        assert num_chirps <= 255, 'Number of chirps per frame exceed 255... increase chirps period and/or frame rate'
        assert num_samples >= 64 , 'Number of samples per chirp less than 64... '
        assert num_samples <= 32 * 1024 / 4 / self.num_rx, 'Number of samples per chirp exceed ADC buffer capacity...'
        assert freq_slope_const < 99.9, 'Chirp slope exceeds max limit of 100 MHz/us...'
        assert self.dig_out_sample_rate <= 12500, 'Sampling rate exceeds 1843 max limit...'
        # assert num_samples * num_chirps <= 128 * 128, 'Radarcube size larger than limit...'

        # (1.4) modify configuration file entries unless default config is requested
        config = [line.rstrip('\r\n') for line in open(self.config_file)]  

        if self.use_defaults == False: 

            for index in range(len(config)):

                # Split the line
                split_words = config[index].split(" ")

                # (1.4.1) modify profile configuration parameters 
                if "profileCfg" in split_words[0]:
                    # split_words[2] = str(start_freq)
                    split_words[3] = str(idle_time)
                    split_words[5] = str(ramp_end_time)
                    split_words[8] = str(round(freq_slope_const,2))
                    split_words[10] = str(num_samples)
                    split_words[11] = str(self.dig_out_sample_rate)
                    config[index] = " ".join(split_words)
                    
                # (1.4.2) modify frame configuration parameters   
                if "frameCfg" in split_words[0]:
                    split_words[3] = str(num_chirps)
                    # split_words[4] = str(num_frames)
                    split_words[5] = str(round(frame_periodicity,2))
                    config[index] = " ".join(split_words)

        # (1.5) print constraints
        print('\n')
        print('{:-^50}'.format(' radar critical specs '))
        print('{:20}'.format('num samples:') + str(num_samples))
        print('{:20}'.format('num chirps:') + str(num_chirps))
        print('{:20}'.format('slope:') + str(freq_slope_const))
        print('{:20}'.format('idle time:') + str(idle_time))
        print('{:20}'.format('ramp end time:') + str(ramp_end_time))
        print('{:20}'.format('bandwidth:') + str(round(freq_slope_const * ramp_end_time / 1e3, 2)))
        print('{:20}'.format('duty cycle: ') + str(round( num_chirps * (ramp_end_time + idle_time) * self.frames_per_second / 1e6 , 2)))
        # print('{:20}'.format('') + str())
        print('{:-^50}'.format(''))
        print('\n')

        # (1.6) save modified config to profiles/profile_custom.cfg file
        file_out = open('profiles/profile_custom.cfg', 'w+')
        for line in config:
            file_out.write('%s\n' %line)
        file_out.close()
        # (2) write configuration to radar 

        # (2.1) instantiate radar 
        awr1843 = TI(cli_loc=self.cli_loc, data_loc=self.data_loc, num_rx=self.num_rx, num_tx=self.num_tx, mode=1)
        # (2.2) compute resultant radar specifications
        config_params = awr1843._initialize('profiles/profile_custom.cfg')
        print('\n')
        print('{:-^50}'.format(' resultant parameters '))
        print('{:25} {}'.format('numDopplerBins:', int(config_params["numDopplerBins"])))
        print('{:25} {}'.format('numRangeBins:', config_params["numRangeBins"]))
        print('{:25} {} cm'.format('rangeResolutionMeters:', round(config_params["rangeResolutionMeters"]*100, 1)))
        print('{:25} {} m'.format('rangeIdxToMeters:', round(config_params["rangeIdxToMeters"]*100, 1)))
        print('{:25} {} cm/s'.format('dopplerResolutionMps:', round(config_params["dopplerResolutionMps"]*100, 1)))
        print('{:25} {} m'.format('maxRange:', round(config_params["maxRange"], 1)))
        print('{:25} {} m/s'.format('maxVelocity:', round(config_params["maxVelocity"], 1)))
        print('{:-^50}'.format(''))
        print('\n')

        
        #for key, value in config_params.items():
        #    print(key + '= ' + str(round(value,4)))

        # (2.3) configure the radar 
        #awr1843._configure_radar(config)

        return