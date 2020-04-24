
import matplotlib.pyplot as plt
from dca_capture_config import awr1843_config
import time

print("\nOh hello! I'm hoping the SOP modes are correct...\n")

#cfg_profile = 'C:\\work\\rcube_extract\\dca_capture\\profile_trx14.cfg'
#cfg_profile = '/mnt/c/work/rcube_extract/dca_capture/profile_trx14.cfg'
cfg_profile = '/mnt/c/work/rcube_extract/dca_capture/profile_trx14.cfg'
rad_back = awr1843_config (radar_name="Radar18",
             cmd_serial_port='/dev/ttyS4',
             dat_serial_port='/dev/ttyS3',
             config_file_name = cfg_profile)










