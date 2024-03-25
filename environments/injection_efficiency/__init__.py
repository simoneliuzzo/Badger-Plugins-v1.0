import time
import numpy as np
import tango
from tango import DevState
from badger import environment
from statistics import mean
from ringcontrol.utils.timing import wait_for
import sys
from badger.errors import BadgerNoInterfaceError


rips = tango.DeviceProxy('sy/ps-rips/manager')
gun = tango.DeviceProxy('elin/beam/run')
KE = tango.DeviceProxy('sy/ps-ke/1')
treflite = tango.DeviceProxy('srdiag/trefflite/sy-sr')

# __authors__ = 'S.Liuzzo, T.Perron, N.Leclercq, L.Carver'


class Environment(environment.Environment):

    name = 'inj_eff'

    variables = {'tl2/ps/qf1/Current': [51.0 -5, 51.0 +5],    # quadruoples
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
                 'sr/ps-si/2/Current': [9400.0, 10600.0],  # septa
                 'sr/ps-si/3/Current': [7100.0, 7700.0],
                 'infra/t-whist/bunchclock/Text': [0.1441550-0.0005, 0.144155+0.0005],  # Text
                 'infra/t-phase/all/phase_SY_SR': [40.0, 80.0], #[100.0, 160.0],     # phase
                 'sy/ps-ke/1/Current': [980.0-100, 985.0],  # KE
                 'sy/ps-se/1/Current': [2750.0, 3030.0],  # SE1
                 'sy/ps-se/2-1/Current': [9700.0, 10500.0]  # SE2
                 }

    observables = ['inj_eff_shooting', 'inj_eff_continuous']

    wait_time: int = 1
    number_of_shots: int = 10
    number_aquisitions: int = 2
    seconds_between_acquisitions: int = 2
    verbose: bool = False

    # print limits
    if verbose:
        print('limits set in environment')
        [print(f'{k} : {v}') for k, v in self.variables.items()]

    self.current_vars = []

    initial_values = {}


    # get current if 200mA, pause
    # self.cur_0 = self.interface.get_value('srdiag/beam-current/total/Current')

    # if cur_0 < 0.01  (less than 10mA) then stop optimization, beam is lost.
    # self.SI3 = self.interface.get_value('sr/ps-si/3/State');
    # if SI3 is 'On' (string of char) refill is in progress. Revert to last step and wait untill not 'On'.


    def get_variables(self, variable_names: list[str]) -> dict:

        variable_outputs = {}

        if self.interface is None:
            raise BadgerNoInterfaceError

        if self.verbose:
            print(f"requested values: {variable_names}")

        self.current_vars=[]
        for attr in variable_names:
            val = self.interface.get_value(attr)
            if not self.initial_values:
                self.initial_values[attr] = val
            self.current_vars.append(val)
            variable_outputs.update({attr: val})

        if self.verbose:
            print('initial values of variables')
            [print(f'{k} : initial = {self.initial_values[k]}, present = {v}')
             for k, v in zip(self.initial_values.keys(), self.current_vars)]

        return variable_outputs

    def set_variables(self, variable_inputs: dict[str, float]):

        if self.interface is None:
            raise BadgerNoInterfaceError

        self.interface.set_values(variable_inputs)

    def get_observables(self, observable_names: list[str]) -> dict:

        if self.interface is None:
            raise BadgerNoInterfaceError

        def is_not_on(dev):
            return dev.state() != DevState.ON

        dt=self.waiting_time
        time.sleep(dt)  # wait for magnets set point reached

        n_acq=self.number_aquisitions
        dt_acq =self.seconds_between_acquisitions
        n_shots =  self.number_of_shots

        observable_outputs = {}

        for obs in observable_names:
            if obs == 'inj_eff_continuous':
                _ie = []
                for i in range(n_acq):
                    # get acquisition i
                    ie = self.interface.get_value('srdiag/trefflite/sy-sr/InjectionEfficiency')
                    _ie.append(ie)
                    # wait before next acquisition
                    if n_acq > 1:
                        time.sleep(dt_acq)

                mean_ie = mean(_ie)
                observable_outputs[obs] = mean_ie

            if obs == 'inj_eff_shooting':

                _ie = []

                # check if need to kill in case stop till key
                cur = self.interface.get_value('srdiag/beam-current/total/Current')
                if cur > 198.0:
                    # input('Please kill beam. Press any key to continue')
                    input('Please kill beam before injection. After killing, please press any key to continue.')

                if cur > 198.0:
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

                observable_outputs[obs] = mean_ie

        return observable_outputs


