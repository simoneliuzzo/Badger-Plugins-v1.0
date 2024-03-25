import tango
import numpy as np

limits_knobs = {'tl2/ps/qf1/Current': [51.0 -5, 51.0 +5],    # quadruoples
                'tl2/ps/qd2/Current': [30.0 -5, 30.0 +5],
                 'tl2/ps/qf3/Current': [14.0 -5, 14.0 +5],
                 'tl2/ps/qf4/Current': [76.0 -5, 76.0 + 5],
                 'tl2/ps/qd5/Current': [64.0-5, 64.0 +5],
                 'tl2/ps/qf6/Current': [33.0 -5, 33.0 +5],
                 'tl2/ps-sx/bs/Current': [10.0-5, 10.0 +20],  # sextupole
                 'tl2/ps/qf7/Current': [10.0 -5, 10.0 +5],     # quadruoples
                 'tl2/ps/qd8/Current': [18.0 -5, 18.0 +5],
                 'tl2/ps/qf9/Current': [3.0 -2, 3.0 +7],
                 'tl2/ps/qd10/Current': [7.0 -5, 7.0 +5],
                 'tl2/ps/qf11/Current': [55.0-5, 55.0+5],
                 'tl2/ps/qd12/Current': [56.0-5, 56.0+5],
                 'tl2/ps/qf13/Current': [12.0-5, 12.0+5],
                 'tl2/ps/qf14/Current': [51.0-5, 51.0+5],
                 'tl2/ps-c1/cv7/Current': [-2.0, 2.0],  # steerers
                 'tl2/ps-c1/cv8/Current': [-2.0, 2.0],
                 'tl2/ps-c1/cv9/Current': [-2.0, 2.0],
                 # 'sr/ps-si/2/Current': [9400.0, 10600.0],  # septa
                 # 'sr/ps-si/3/Current': [7100.0, 7700.0],
                 # 'infra/t-whist/bunchclock/Text': [0.1441550-0.0005, 0.144155+0.0005],  # Text
                 # 'infra/t-phase/all/phase_SY_SR': [100.0, 160.0],     # phase
                 # 'sy/ps-ke/1/Current': [980.0-100, 985.0],  # KE
                 # 'sy/ps-se/1/Current': [2750.0, 3030.0],  # SE1
                 # 'sy/ps-se/2-1/Current': [9700.0, 10500.0],  # SE2
                 }


for dev in limits_knobs.keys():
    d = tango.AttributeProxy(dev)
    lowval = limits_knobs[dev][0]
    higval = limits_knobs[dev][1]
    newval = lowval + np.random.rand(1)*(higval-lowval)  # uniform in the range
    print(newval)
    d.write(newval)




