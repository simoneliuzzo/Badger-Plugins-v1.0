import time
import numpy as np
from badger import environment
import pathlib
from statistics import mean
from itertools import compress
from badger.errors import BadgerNoInterfaceError, BadgerEnvObsError
from .NormalizeLifetime import normalize_lifetime


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

    name = 'esrf_sext_and_oct_knobs'

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

    observables = ['total_losses', 'libera_lifetime', 'normalized_libera_lifetime']

    # initial values for variables
    _variables = {v: 0.0 for v in variables.keys()}
    _initial_sext = None
    _initial_oct = None
    _cur_0 = None

    # Environment parameters
    waiting_time: int = 8
    number_of_acquisitions: int = 2
    seconds_between_acquisitions: int = 2


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

        [print(f'sext knob {c}: {k}') for c, k in enumerate(_x[0:sum(mask_sext_vars)])]
        self.interface.set_value(channel_name='srmag/m-s/all/CorrectionStrengths',
                                 channel_value=self._initial_sext + sext)
        # set octupoles
        oct = np.sum(_x[sum(mask_sext_vars):] * np.transpose(
            self._knobs_oct.gen_matrix(list(compress(vars, mask_oct_vars)))), axis=1)

        [print(f'oct knob {c}: {k}') for c, k in enumerate(_x[sum(mask_sext_vars):])]
        self.interface.set_value(channel_name='srmag/m-o/all/CorrectionStrengths',
                                 channel_value=self._initial_oct + oct)


    def get_observables(self, observable_names: list[str]) -> dict:

        if self.interface is None:
            raise BadgerNoInterfaceError

        cur_0 = self._cur_0

        time.sleep(self.waiting_time)
        n_acq = self.number_of_acquisitions
        dt_acq = self.seconds_between_acquisitions

        observable_outputs = {}
        for obs in observable_names:
            if obs == 'total_losses':
                _totloss = []
                for i in range(n_acq):
                    # get acquisition i
                    cur = self.interface.get_value(channel_name='srdiag/beam-current/total/Current')
                    _totloss.append(self.interface.get_value(channel_name='srdiag/blm/all/TotalLoss')*(cur_0/cur)**2)
                    # wait before next acquisition
                    if n_acq > 1:
                        time.sleep(dt_acq)

                mean_totloss = mean(_totloss)
                observable_outputs[obs]=mean_totloss

            elif obs == 'libera_lifetime':
                _LT = []
                for i in range(n_acq):
                    # get acquisition i
                    cur = self.interface.get_value(channel_name='srdiag/beam-current/total/Current')
                    _LT.append(self.interface.get_value(channel_name='srdiag/bpm/lifetime/Lifetime')/3600*cur/cur_0)  # convert to h
                    # wait before next acquisition
                    if n_acq > 1:
                        time.sleep(dt_acq)

                mean_lifetime = mean(_LT)
                observable_outputs[obs] = mean_lifetime

            elif obs == 'normalized_libera_lifetime':
                _LT = []
                for i in range(n_acq):
                    # get acquisition i
                    cur = self.interface.get_value('srdiag/beam-current/total/Current')
                    # eh = self.interface.get_value('srdiag/beam-emittance/main-h/Emittance_H')
                    # ev = self.interface.get_value('srdiag/beam-emittance/main-v/Emittance_V')
                    eh = self.interface.get_value('srdiag/emittance/id25/Emittance_h')
                    ev = self.interface.get_value('srdiag/emittance/id25/Emittance_v')
                    lt_tot = self.interface.get_value('srdiag/bpm/lifetime/Lifetime')

                    print(f'cur {cur:2.2f} mA')
                    print(f'lt tot {lt_tot / 3600:2.2f} h')

                    print(f'eh {eh*1e12:2.2f} pmrad')
                    print(f'ev {ev*1e12:2.2f} pmrad')

                    # import math
                    # print(math.sqrt(ev))

                    # normalize with measured current and emittances
                    norm_LT = normalize_lifetime(lt_tot/3600,  # h
                                                 0.0,
                                                 cur/1e3,  # A
                                                 0.0,
                                                 eh,  # mrad
                                                 ev)
                    _LT.append(norm_LT)

                    print(f'normalized LT: {norm_LT:2.2f} h')

                    # wait before next acquisition
                    if n_acq > 1:
                        time.sleep(dt_acq)

                mean_lifetime = mean(_LT)
                observable_outputs[obs] = mean_lifetime

        return observable_outputs


if __name__ =='__main__':
    envi = Environment()
    envi.get_variables()