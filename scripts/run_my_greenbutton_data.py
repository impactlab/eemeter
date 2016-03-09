from eemeter.examples import one_resi_gbutton_project
from eemeter.meter import DefaultResidentialMeter
from eemeter.meter import DataCollection

from datetime import datetime


def run_my_greenbutton_data():
    """Pass in the xml download filenames for residential green button data.
    """
    myzip = "95030"
    my_gb_e = '/Users/marla/Downloads/pge_interval_data_2013-06-01_to_2016-03-01b/pge_electric_interval_data_0622457062_2013-06-01_to_2016-03-01.xml'
    my_gb_g = '/Users/marla/Downloads/pge_interval_data_2013-06-01_to_2016-03-01b/pge_gas_interval_data_0622457010_2013-06-01_to_2016-03-01.xml'
    project = one_resi_gbutton_project(myzip,
                                    baseline_start_dt=datetime(2013,6,1),
                                    report_start_dt=datetime(2015,10,9),
                                    report_end_dt=datetime(2016,3,1),
                                    gbutton_e=my_gb_e, gbutton_g=my_gb_g
                                    )
    meter = DefaultResidentialMeter()

    results = meter.evaluate(DataCollection(project=project))
    electricity_usage_pre = results.get_data("annualized_usage", ["electricity", "baseline"]).value
    electricity_usage_post = results.get_data("annualized_usage", ["electricity", "reporting"]).value
    natural_gas_usage_pre = results.get_data("annualized_usage", ["natural_gas", "baseline"]).value
    natural_gas_usage_post = results.get_data("annualized_usage", ["natural_gas", "reporting"]).value
    electricity_savings = (electricity_usage_pre - electricity_usage_post) / electricity_usage_pre
    natural_gas_savings = (natural_gas_usage_pre - natural_gas_usage_post) / natural_gas_usage_pre
    print "electricity_savings: %s" % electricity_savings
    print "natural_gas_savings: %s" % natural_gas_savings


if __name__ == "__main__":
    """TBD: add options to specify the input file(s), zipcode and three dates.
    """
    run_my_greenbutton_data()
