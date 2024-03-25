import time
import numpy as np
import tango
from tango import DevState
from badger import environment
from badger.interface import Interface
from statistics import mean
from itertools import compress
from ringcontrol.utils.timing import wait_for
import pathlib
import sys

rips = tango.DeviceProxy('sy/ps-rips/manager')
gun = tango.DeviceProxy('elin/beam/run')
KE = tango.DeviceProxy('sy/ps-ke/1')
treflite = tango.DeviceProxy('srdiag/trefflite/sy-sr')

# __authors__ = 'S.Liuzzo, T.Perron, N.Leclercq, L.Carver'

class Knobs:
    def __init__(self, csv_file_name, name):
        self._matrix = self.load_knob_from_csv(csv_file_name)
        # there are no names in csv so generate names
        self._row_names = [f"knob-{name}-{i}" for i in range(self.get_count())]

    @staticmethod
    def load_knob_from_csv(filename) -> np.ndarray:
        return np.genfromtxt(filename, delimiter=',')

    def get_count(self):
        return self._matrix.shape[0]

    def get_names(self):
        return self._row_names

    def gen_matrix(self, vars):
        if len(vars) == len(self._row_names):
            return self._matrix
        vars_hash = set(vars)
        remove_row_idx = [idx for idx, name in enumerate(self._row_names) if not name in vars_hash]
        return np.delete(self._matrix, remove_row_idx, axis=0)  # remove rows


class Environment(environment.Environment):

    name = 'injection_efficiency_SR_knobs'

    # define knobs and add them to variables
    _path = pathlib.Path(__file__).parent.resolve()
    _knobs_sext = Knobs(_path / "data" / "SextKnob.csv", "sext")
    _knobs_oct = Knobs(_path / "data" / "OctKnob.csv", "octu")
    _limits_knobs_sext = {name: [-1, 1] for name in _knobs_sext.get_names()}
    _limits_knobs_sext['knob-sext-2'] = [-2, 2]
    _limits_knobs_oct = {name: [-1, 1] for name in _knobs_oct.get_names()}
    variables = {}
    for _d in (_limits_knobs_sext, _limits_knobs_oct):
        variables.update(_d)

    observables =  ['inj_eff_shooting', 'inj_eff_continuous']

    # initial values for variables
    _variables = {v: 0.0 for v in variables.keys()}
    _initial_sext = None
    _initial_oct = None
    _cur_0 = None

    # Environment parameters
    wait_time: int = 1
    number_of_shots: int = 10
    number_aquisitions: int = 2
    seconds_between_acquisitions: int = 2
    verbose: bool = False

    def get_variables(self, variable_names: list[str]) -> dict:

        if self.interface is None:
            raise BadgerNoInterfaceError

        # store initial values if not available
        if self._cur_0 == None:
            print(f'store intitial values of strengths and currents')
            self._initial_sext = self.interface.get_value(channel_name='srmag/m-s/all/CorrectionStrengths')
            self._initial_oct = self.interface.get_value(channel_name='srmag/m-o/all/CorrectionStrengths')
            self._cur_0 = self.interface.get_value(channel_name='srdiag/beam-current/total/Current')
            # print(self._cur_0)
            # print(self._initial_oct)
            # print(self._initial_sext)

        variable_outputs = {v: self._variables[v] for v in variable_names}

        return variable_outputs


    def set_variables(self, variable_inputs: dict[str, float]):

        if self.interface is None:
            raise BadgerNoInterfaceError

        __x=[]
        vars = []
        for var, x in variable_inputs.items():
            self._variables[var] = x  # store in private variable the present amplitude of the knobs
            __x.append(x)
            vars.append(var)

        _x = np.array(__x)

        # selected varaibles may be sext or oct. Order will be always sext first and then oct.
        # prepare mask of sext and oct selected variables
        mask_sext_vars = [v.find('sext') >= 0 for v in vars]
        mask_oct_vars = [v.find('octu') >= 0 for v in vars]

        # set sextupoles
        sext = np.sum(_x[0:sum(mask_sext_vars)] * np.transpose(
            self._knobs_sext.gen_matrix(list(compress(vars, mask_sext_vars)))), axis=1)

        if self.verbose:
            [print(f'sext knob {c}: {k}') for c, k in enumerate(_x[0:sum(mask_sext_vars)])]

        self.interface.set_value(channel_name='srmag/m-s/all/CorrectionStrengths',
                                 channel_value=self._initial_sext + sext)
        # set octupoles
        oct = np.sum(_x[sum(mask_sext_vars):] * np.transpose(
            self._knobs_oct.gen_matrix(list(compress(vars, mask_oct_vars)))), axis=1)

        if self.verbose:
            [print(f'oct knob {c}: {k}') for c, k in enumerate(_x[sum(mask_sext_vars):])]

        self.interface.set_value(channel_name='srmag/m-o/all/CorrectionStrengths',
                                 channel_value=self._initial_oct + oct)

    def get_observables(self, observable_names: list[str]) -> dict:

        if self.interface is None:
            raise BadgerNoInterfaceError

        def is_not_on(dev):
            return dev.state() != DevState.ON

        dt = self.waiting_time
        time.sleep(dt)  # wait for magnets set point reached

        n_acq = self.number_aquisitions
        dt_acq = self.seconds_between_acquisitions
        n_shots = self.number_of_shots

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


