"""Throw-away code I'm writing just to facilitate learning eemeter,
oeem-client and oeem-energy-datastore.
"""
from eemeter.examples import get_example_project, one_resi_gbutton_project
from eemeter.meter import DefaultResidentialMeter
from eemeter.meter import DataCollection

from datetime import datetime

def test_existing_meter():
    """Step through the example from eemeter.readthedocs.org.
    """

    project = get_example_project("94087")
    meter = DefaultResidentialMeter()
    results = meter.evaluate(DataCollection(project=project))
    electricity_usage_pre = results.get_data("annualized_usage", ["electricity", "baseline"]).value
    electricity_usage_post = results.get_data("annualized_usage", ["electricity", "reporting"]).value
    natural_gas_usage_pre = results.get_data("annualized_usage", ["natural_gas", "baseline"]).value
    natural_gas_usage_post = results.get_data("annualized_usage", ["natural_gas", "reporting"]).value
    electricity_savings = (electricity_usage_pre - electricity_usage_post) / electricity_usage_pre
    natural_gas_savings = (natural_gas_usage_pre - natural_gas_usage_post) / natural_gas_usage_pre
    assert str(electricity_savings) == '[ 0.49999999]'
    assert str(natural_gas_savings) == '[ 0.50000001]'

def test_my_greenbutton_data():
    """Pass in the xml download filenames for residential green button data.
    """
    myzip = "95030"
    my_gb_e = '/Users/marla/Downloads/pge_interval_data_2013-06-01_to_2016-03-01/pge_electric_interval_data_0622457062_2013-06-01_to_2016-03-01.xml'
    my_gb_g = '/Users/marla/Downloads/pge_interval_data_2013-06-01_to_2016-03-01/pge_gas_interval_data_0622457010_2013-06-01_to_2016-03-01.xml'
    project = one_resi_gbutton_project("95030",
                                    baseline_start_dt=datetime(2013,6,1),
                                    report_start_dt=datetime(2015,10,9),
                                    report_end_dt=datetime(2016,3,1)
                                    )
    meter = DefaultResidentialMeter()
    results = meter.evaluate(DataCollection(project=project))
    electricity_usage_pre = results.get_data("annualized_usage", ["electricity", "baseline"]).value
    electricity_usage_post = results.get_data("annualized_usage", ["electricity", "reporting"]).value
    natural_gas_usage_pre = results.get_data("annualized_usage", ["natural_gas", "baseline"]).value
    natural_gas_usage_post = results.get_data("annualized_usage", ["natural_gas", "reporting"]).value
    electricity_savings = (electricity_usage_pre - electricity_usage_post) / electricity_usage_pre
    natural_gas_savings = (natural_gas_usage_pre - natural_gas_usage_post) / natural_gas_usage_pre
    assert str(electricity_savings) == '[ 0.50180845]'
    assert str(natural_gas_savings) == '[ 0.49530758]'
