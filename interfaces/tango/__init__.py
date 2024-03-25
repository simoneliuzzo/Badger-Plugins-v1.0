import tango
from badger import interface
import os
import time
from typing import Any, Dict, List

class Interface(interface.Interface):

    name = 'tango'

    # _tango_host = 'tango://acs.esrf.fr:10000/'
    # os.environ['TANGO_HOST'] = 'acs.esrf.fr:10000'

    _tango_host = 'tango://ebs-simu-1.esrf.fr:10000/'
    os.environ['TANGO_HOST'] = 'ebs-simu-1:10000'

    def __init__(self):
        super().__init__()

    @staticmethod
    def get_default_params():
        return None

    def get_values(self, channel_names: List[str]) -> Dict[str, Any]:

        channel_outputs = {}

        for attributename in channel_names:
            try:
                attrprox = tango.AttributeProxy(self._tango_host + attributename)
            except tango.DevFailed as err:
                print('DevFailed, try once more')
                time.sleep(2)
                attrprox = tango.AttributeProxy(self._tango_host + attributename)
            # print(attrprox)
            val = None
            if 'srdiag' in attributename:
                val = attrprox.read().value
            if 'srmag' in attributename:
                val = attrprox.read().w_value  # read set point
            if 'tl2' in attributename:
                val = attrprox.read().w_value
            if 'sr/ps' in attributename:
                val = attrprox.read().w_value
            if 'sy/ps' in attributename:
                val = attrprox.read().w_value
            if 'infra' in attributename:
                val = attrprox.read().w_value
            # print(val)
            channel_outputs[attributename] = val

        return channel_outputs

    def set_values(self, channel_inputs: Dict[str, Any]):

        for attributename, value in channel_inputs.items():

            try:
                dev = tango.AttributeProxy(self._tango_host + attributename)
                dev.write(value)
            except tango.DevFailed as err:
                print('DevFailed, try once more')
                time.sleep(2)
                dev = tango.AttributeProxy(self._tango_host + attributename)
                dev.write(value)
