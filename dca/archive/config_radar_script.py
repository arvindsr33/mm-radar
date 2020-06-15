from mmwave.dataloader.radars import TI

# read the default configuration file 
# take the radar specification inputs and modify the config values accordingly

config_file = '/home/arvind/code/mm-radar/profiles/profile_default.cfg'

config = [line.rstrip('\r\n') for line in open(config_file)]  # use '\r\n' in windows 

# write the configuration files to the radar using serial 
# ignore all commented lines 

# Note: keep chirp time 10% higher than sample duration (tested minimum)

# input specifications
num_tx = 1
num_rx = 4
range_resolution = 0.05 
max_range = 8
max_velocity = 6
num_chirps = 128
frames_per_second = 20
# num_frames = 0 # infinite

# defaults
# freq_slope_const = 20
start_freq = 77
dig_out_sample_rate = 3200  

# intermediate parameters
wavelength = 3e8 / start_freq / 1e9

# radar config parameters 
num_samples = round(max_range / range_resolution / 0.9)
freq_slope_const = 0.9 * 3e8 * dig_out_sample_rate / 2 / max_range / 1e9
ramp_end_time = round(1.1 * num_samples * 1e3/ dig_out_sample_rate ) + 6 # 3 us margin both sides
idle_time = round(wavelength * 1e6 / 4 / max_velocity - ramp_end_time)
frame_periodicity = 1e3 / frames_per_second # frame duration in ms

# flag 
flag = (freq_slope_const * ramp_end_time > 4e3)
if flag:
    print('Bandwidth exceeds 4 GHz ... ')

for index in range(len(config)):

    # ensure bandwidth constraint is satisfied
    if flag:
        break

    # Split the line
    split_words = config[index].split(" ")
    # Get the information about the profile configuration
    if "profileCfg" in split_words[0]:
        # split_words[2] = str(start_freq)
        split_words[3] = str(idle_time)
        split_words[5] = str(ramp_end_time)
        split_words[8] = str(round(freq_slope_const,2))
        split_words[10] = str(num_samples)
        split_words[11] = str(dig_out_sample_rate)
        config[index] = " ".join(split_words)
        
    # Get the information about the frame configuration    
    if "frameCfg" in split_words[0]:

        # split_words[1] = str(chirp_start_idx)
        # split_words[2] = str(chirp_end_idx)
        split_words[3] = str(num_chirps)
        # split_words[4] = str(num_frames)
        split_words[5] = str(round(frame_periodicity,2))
        config[index] = " ".join(split_words)


awr1843 = TI(cli_loc='/dev/ttyS4', data_loc='/dev/ttyS3', num_rx=num_rx, num_tx=num_tx)

# critical parameters
print('\nframe duty cycle: ' + str(round((ramp_end_time+idle_time)*num_chirps/frame_periodicity/10,2)) + '%')
print('buffer size: ' + str(round((4 * num_samples * num_rx * num_tx * num_chirps)/1024)) + ' KB')
print('bandwidth: ' + str(round(freq_slope_const * ramp_end_time * 1e-3, 2)) + ' GHz\n')

config_params = awr1843._initialize(config)
for key, value in config_params.items():
    print(key + '= ' + str(round(value,4)))

print('\n ------------------------------------')
awr1843._configure_radar(config, printOutputs=True)

