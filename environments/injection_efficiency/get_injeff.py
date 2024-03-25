import numpy as np
import tango
from tango import DevState
from statistics import mean
from ringcontrol.utils.timing import wait_for
import time

# tango devices
rips = tango.DeviceProxy('sy/ps-rips/manager')
gun = tango.DeviceProxy('elin/beam/run')
KE = tango.DeviceProxy('sy/ps-ke/1')
treflite = tango.DeviceProxy('srdiag/trefflite/sy-sr')
cur = tango.DeviceProxy('srdiag/beam-current/total')

# __authors__ = 'S.Liuzzo, T.Perron, N.Leclercq, L.Carver, N.CArmignani, P.Raimondi'


def is_not_on(dev):
    return dev.state() != DevState.ON


def get_injection_efficiency(n_shots=10.0):
    """
    get injection efficiency. ALL injectors should be on. guan off and rips not ramping

    """

    if cur.Current > 198.0:
        # input('Please kill beam. Press any key to continue')
        input('Please kill beam before injection. After killing, please press any key to continue.')

    if cur.Current > 198.0:
        raise ValueError('current is still above 198mA')

    _ie = []

    # rips on
    if rips.state() != DevState.RUNNING:
        if rips.state() != DevState.MOVING:
            time.sleep(1)
        # RIPS with one retry
        try:
            rips.StartRamping()
        except Exception as ex:
            print('failed to start RIPS ramp, wait 5s and try again.')
            time.sleep(5)
            rips.StartRamping()
        time.sleep(1)  # wait for rips to start

    # gun on
    if gun.state() == DevState.OFF:
        gun.On()

    # trig KE for a given number of time
    if KE.state() == DevState.STANDBY:
        cm = KE.CounterMode
        KE.CounterMode = n_shots  # set number of shots
        # print(f'{n_shots}')

        # KE ON, with 1 retry
        try:
            KE.On()  # shoot
        except Exception as ex:
            KE.Reset()
            time.sleep(0.5)
            KE.On()  # try again

        time.sleep(0.25 * n_shots + 1.0)

        # KE Standby, with 1 retry
        try:
            KE.Standby()
        except Exception as ex:
            KE.Reset()
            time.sleep(0.5)
            KE.Standby()  # try again

        KE.CounterMode = cm  # restore initial counter mode state
    else:
        if rips.state() != DevState.MOVING:
            time.sleep(1)

        # RIPS with one retry
        try:
            rips.StopRamping()
        except Exception as ex:
            print('failed to stop RIPS ramp, wait 5s and try again.')
            time.sleep(5)
            rips.StopRamping()  # try again

        gun.Off()
        KE.Standby()
        raise ValueError('KE not in standby')

    # wait for shots
    # wait_for(is_not_on(KE), period=0.25, ini=0, timeout=5)

    # rips stop ramp
    if rips.state() == DevState.RUNNING:
        if rips.state() != DevState.MOVING:
            time.sleep(1)
        # RIPS with one retry
        try:
            rips.StopRamping()
        except Exception as ex:
            print('failed to stop RIPS ramp, wait 5s and try again.')
            time.sleep(5)
            rips.StopRamping()  # try again

    # gun off
    if gun.state() == DevState.ON:
        gun.Off()

    # get last train of non zero or NaN acquisition from HDB
    last_treflite = [a.value for a in treflite.attribute_history('InjectionEfficiency', 50)]

    print(f'last Inj. Eff. data: {last_treflite}')

    # get good data
    good_treff = []
    for t in last_treflite:
        if t is not None:
            if t > 0:
                good_treff.append(t)

    print(f'good Inj. Eff. data: {good_treff}')

    if len(good_treff) == 0:
        mean_ie = 0.0
    else:
        mean_ie = mean(np.array(good_treff))

    print(f'Inj.Eff. <{n_shots} shots> is: {mean_ie * 100}%')

    return mean_ie


if __name__ == '__main__':
    get_injection_efficiency(10)