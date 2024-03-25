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

def query_yes_no(question, default="yes"):
    """Ask a yes/no question via raw_input() and return their answer.

    "question" is a string that is presented to the user.
    "default" is the presumed answer if the user just hits <Enter>.
            It must be "yes" (the default), "no" or None (meaning
            an answer is required of the user).

    The "answer" return value is True for "yes" or False for "no".
    """
    valid = {"yes": True, "y": True, "ye": True, "no": False, "n": False}
    if default is None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)

    while True:
        sys.stdout.write(question + prompt)
        choice = input().lower()
        if default is not None and choice == "":
            return valid[default]
        elif choice in valid:
            return valid[choice]
        else:
            sys.stdout.write("Please respond with 'yes' or 'no' " "(or 'y' or 'n').\n")


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
    path = pathlib.Path(__file__).parent.resolve()
    knobs_sext = Knobs(path / "data" / "SextKnob.csv", "sext")
    knobs_oct = Knobs(path / "data" / "OctKnob.csv", "octu")

    name = 'esrf_sext_and_oct_knobs'

    def __init__(self, interface: Interface, params):
        self.limits_knobs_sext = {name: [-2, 2] for name in Environment.knobs_sext.get_names()}
        self.limits_knobs_oct = {name: [-5, 5] for name in Environment.knobs_oct.get_names()}
        self.limits_knobs = {}
        for d in (self.limits_knobs_sext, self.limits_knobs_oct):
            self.limits_knobs.update(d)

        # print limits
        # [print(f'{k} : {self.limits_knobs[k]}') for k in self.limits_knobs.keys()]

        self.current_vars = []
        super().__init__(interface, params)
        self.initial_sext = self.interface.get_value(attributename='srmag/m-s/all/CorrectionStrengths')
        self.initial_oct = self.interface.get_value(attributename='srmag/m-o/all/CorrectionStrengths')

        self.cur_0 = self.interface.get_value('srdiag/beam-current/total/Current')

        # if cur_0 < 0.01  (less than 10mA) then stop optimization, beam is lost.
        # self.SI3 = self.interface.get_value('sr/ps-si/3/State');
        # if SI3 is 'On' (string of char) refill is in progress. Revert to last step and wait untill not 'On'.

    def _get_vrange(self, var):
        return self.limits_knobs[var]

    @staticmethod
    def list_vars():
        # print(Environment.knobs_sext.get_names() + Environment.knobs_oct.get_names())
        return Environment.knobs_sext.get_names() + Environment.knobs_oct.get_names()

    # TODO: add losses
    @staticmethod
    def list_obses():
        return ['inj_eff_shooting', 'inj_eff_continuous']

    @staticmethod
    def get_default_params():
        return {
            'waiting_time': 8,
            'number_of_shots': 5,
            'number_aquisitions': 2,
            'seconds_between_acquisitions': 2,
        }

    def _get_var(self, var):
        raise Exception("values have to be get at once!")

    def _get_vars(self, vars):
        print(f"requested values: {vars}")
        if len(self.current_vars) == 0:
            self.current_vars = [0.0 for _ in range(len(vars))]     
        return self.current_vars

    def _set_var(self, var, x): 
        raise Exception("values have to be set at once!")

    def _set_vars(self, vars, _x):
        # print('vars')
        # print(vars)
        # print('_x')
        # print(_x)
        # print('current_vars')
        # print(self.current_vars)

        # selected varaibles may be sext or oct. Order will be always sext first and then oct.
        # prepare mask of sext and oct selected variables
        mask_sext_vars = [v.find('sext') >= 0 for v in vars]
        mask_oct_vars = [v.find('octu') >= 0 for v in vars]

        # print(mask_sext_vars)
        # print(mask_oct_vars)
        # print('sext vars:')
        # print(_x[0:sum(mask_sext_vars)])
        # print('oct vars:')
        # print(_x[sum(mask_sext_vars):])

        self.current_vars = _x
        # print(f"value names {vars}")

        # set sextupoles
        sext = np.sum(_x[0:sum(mask_sext_vars)] * np.transpose(
            Environment.knobs_sext.gen_matrix(list(compress(vars, mask_sext_vars)))), axis=1)

        [print(f'sext knob {c}: {k}') for c, k in enumerate(_x[0:sum(mask_sext_vars)])]
        self.interface.set_value(attributename='srmag/m-s/all/CorrectionStrengths',
                                 value=self.initial_sext + sext)
        # set octupoles
        oct = np.sum(_x[sum(mask_sext_vars):] * np.transpose(
            Environment.knobs_oct.gen_matrix(list(compress(vars, mask_oct_vars)))), axis=1)

        [print(f'oct knob {c}: {k}') for c, k in enumerate(_x[sum(mask_sext_vars):])]
        self.interface.set_value(attributename='srmag/m-o/all/CorrectionStrengths',
                                 value=self.initial_oct + oct)

    def _get_obs(self, obs):
        def is_not_on(dev):
            return dev.state() != DevState.ON

        try:
            dt = self.params['waiting_time']
        except KeyError:
            dt = 0
        time.sleep(dt)  # wait for magnets set point reached

        try:
            n_acq = self.params['number_aquisitions']
        except KeyError:
            n_acq = 1

        try:
            dt_acq = self.params['seconds_between_acquisitions']
        except KeyError:
            dt_acq = 1

        try:
            n_shots = self.params['number_of_shots']
        except KeyError:
            n_shots = 5

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

            return mean_ie

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

            return mean_ie


