from __future__ import annotations

from indicators.greeks import OptionType, black_scholes_greeks


def test_atm_call_delta_near_half():
    greeks = black_scholes_greeks(spot=100, strike=100, time_to_expiry_years=7 / 365, iv=0.18, option_type=OptionType.CALL)
    assert 0.4 < greeks.delta < 0.65


def test_atm_put_delta_near_negative_half():
    greeks = black_scholes_greeks(spot=100, strike=100, time_to_expiry_years=7 / 365, iv=0.18, option_type=OptionType.PUT)
    assert -0.65 < greeks.delta < -0.35


def test_deep_itm_call_delta_near_one():
    greeks = black_scholes_greeks(spot=200, strike=100, time_to_expiry_years=7 / 365, iv=0.18, option_type=OptionType.CALL)
    assert greeks.delta > 0.9


def test_degenerate_inputs_return_zeroed_greeks():
    greeks = black_scholes_greeks(spot=0, strike=100, time_to_expiry_years=1, iv=0.2, option_type=OptionType.CALL)
    assert greeks == greeks.__class__(delta=0.0, gamma=0.0, theta=0.0, vega=0.0)


def test_gamma_and_vega_non_negative():
    greeks = black_scholes_greeks(spot=100, strike=105, time_to_expiry_years=10 / 365, iv=0.2, option_type=OptionType.CALL)
    assert greeks.gamma >= 0
    assert greeks.vega >= 0
