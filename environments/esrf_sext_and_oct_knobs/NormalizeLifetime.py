import math
from at.acceptance.touschek import get_bunch_length_espread


__author__ = 'S.M.Liuzzo'


def normalize_lifetime(lt_tot,
                       lt_single,
                       I_tot,
                       I_single,
                       eh,
                       ev,
                       en_spread=None,
                       r=None,  # AT lattice
                       n_bunches = 882,
                       vacuum_lifetime=120,  # hours
                       ref_I=0.200,  # Ampere
                       ref_eh=140e-12,  # m rad
                       ref_ev=10e-12,  # m rad
                       ref_en_spread=1e-3,  #
                       ref_bunch_length=0.003  # m
                       ):
    """
    normalized Touschek lifetime
    :param lt_tot: total lifetime measured in hours
    :param lt_single: single bunch lifetime in hours
    :param I_tot: total current at measurement time in A
    :param eh: horizontal emittance at measurement time in A
    :param ev: vertical emittance at measurement time in mrad
    :param en_spread: energy spread at measurement time
    :param r: AT lattice for bunch length and energy spread computation.
              if None, bunch length and energy spread normalizations are ignored.
    :param vacuum_lifetime: expected or measured vacuum lifetime
    :param ref_I: (default 0.2A) reference current for normalization
    :param ref_eh: (default 140*1e-12 mrad) reference hor. emittance for normalization
    :param ref_ev: (default 10*1e-12 mrad) reference ver. emittance for normalization
    :param ref_en_spread: (default 0.1%) reference energy spread for normalization
    :param ref_bunch_length: (default 0.003m) reference energy spread for normalization
    :return:
    """
    if ev < 0.01 * 1e-12:
        print('too small vertical emittance, setting to 0.1')
        ev = 0.1 * 1e-12

    if I_single > 0.003:
        LT_tou_train = I_tot / (
                    I_tot / lt_tot - I_single / lt_single - I_tot / vacuum_lifetime)
    else:
        LT_tou_train = I_tot / (
                I_tot / lt_tot - I_tot / vacuum_lifetime)

    # normalize to 200mA
    LT = LT_tou_train * I_tot / ref_I

    # normalize to ev = 10pm
    LT = LT / math.sqrt(ev) * math.sqrt(ref_ev)

    # normalize to eh = 140 pm
    LT = LT / math.sqrt(eh) * math.sqrt(ref_eh)

    # if input AT lattice is provided, compute bunch length and energy spread normalization
    if r is not None:

        # get expected bunch length and energy spread for the given current and filling pattern
        I_bunch = I_tot / n_bunches

        bl_I, en_spread_I = get_bunch_length_espread(r, zn=0.35, bunch_curr=I_bunch)

        # normalize with bunch length
        LT = LT / bl_I * ref_bunch_length

    if en_spread is not None:
        # remove energy spread contribution from microwave instability,
        # en_spread(current per bunch) is approximated with two straight lines
        # THIS is not needed. Even if en_spread(cur_bunch), this is of no interest, 1/LT propto 1/en_spread.

        # normalize for energy spread
        LT = LT / en_spread * ref_en_spread

    # convert to h
    lt_norm_hours = LT

    return lt_norm_hours


def normalize_total_losses(lt_tot,
                       lt_single,
                       I_tot,
                       I_single,
                       eh,
                       ev,
                       en_spread=None,
                       r=None,  # AT lattice
                       n_bunches = 882,
                       vacuum_lifetime=120,  # hours
                       ref_I=0.200,  # Ampere
                       ref_eh=140e-12,  # m rad
                       ref_ev=10e-12,  # m rad
                       ref_en_spread=1e-3,  #
                       ref_bunch_length=0.003  # m
                       ):
    """
    normalized total losses
    :param lt_tot: total losses measured in arb.units
    :param I_tot: total current at measurement time in A
    :param eh: horizontal emittance at measurement time in A
    :param ev: vertical emittance at measurement time in mrad
    :param en_spread: energy spread at measurement time
    :param r: AT lattice for bunch length and energy spread computation.
              if None, bunch length and energy spread normalizations are ignored.
    :param vacuum_lifetime: expected or measured vacuum lifetime
    :param ref_I: (default 0.2A) reference current for normalization
    :param ref_eh: (default 140*1e-12 mrad) reference hor. emittance for normalization
    :param ref_ev: (default 10*1e-12 mrad) reference ver. emittance for normalization
    :param ref_en_spread: (default 0.1%) reference energy spread for normalization
    :param ref_bunch_length: (default 0.003m) reference energy spread for normalization
    :return:
    """

    if I_single > 0.003:
        LT_tou_train = I_tot / (
                    I_tot / lt_tot - I_single / lt_single - I_tot / vacuum_lifetime)
    else:
        LT_tou_train = I_tot / (
                I_tot / lt_tot - I_tot / vacuum_lifetime)

    # normalize to 200mA
    LT = LT_tou_train * I_tot / ref_I

    # normalize to ev = 10pm
    LT = LT / math.sqrt(ev) * math.sqrt(ref_ev)

    # normalize to eh = 140 pm
    LT = LT / math.sqrt(eh) * math.sqrt(ref_eh)

    # if input AT lattice is provided, compute bunch length and energy spread normalization
    if r is not None:

        # get expected bunch length and energy spread for the given current and filling pattern
        I_bunch = I_tot / n_bunches

        bl_I, en_spread_I = get_bunch_length_espread(r, zn=0.35, bunch_curr=I_bunch)

        # normalize with bunch length
        LT = LT / bl_I * ref_bunch_length

    if en_spread is not None:
        # remove energy spread contribution from microwave instability,
        # en_spread(current per bunch) is approximated with two straight lines
        # THIS is not needed. Even if en_spread(cur_bunch), this is of no interest, 1/LT propto 1/en_spread.

        # normalize for energy spread
        LT = LT / en_spread * ref_en_spread

    # convert to h
    lt_norm_hours = LT

    return lt_norm_hours


if __name__ == '__main__':
    lt_tot = 22.0
    lt_single = 5.0
    I_tot = 0.194
    I_single = 0.006
    eh = 122e-12
    ev = 10e-12
    print(f'tot LT = {lt_tot:2.2f} h')
    print(f'single LT = {lt_single:2.2f} h')
    print(f'total I = {I_tot*1e3:2.2f} mA')
    print(f'single I = {I_single*1e3:2.2f} mA')
    print(f'hor. emit. = {eh * 1e12:2.2f} pmrad')
    print(f'ver. emit. = {ev * 1e12:2.2f} pmrad')

    norm_lt = normalize_lifetime(lt_tot,
                                 lt_single,
                                 I_tot,
                                 I_single,
                                 eh,
                                 ev)

    print(f'normalized LT = {norm_lt:2.2f} h')

    pass