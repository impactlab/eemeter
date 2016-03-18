from eemeter.location import Location
from eemeter.evaluation import Period
from eemeter.weather import GSODWeatherSource
from eemeter.generator import MonthlyBillingConsumptionGenerator
from eemeter.generator import generate_monthly_billing_datetimes
from eemeter.consumption import ConsumptionData
from eemeter.models import AverageDailyTemperatureSensitivityModel
from eemeter.project import Project
from eemeter.importers import import_green_button_xml
from scipy.stats import randint

from datetime import datetime
import pytz


def get_example_project(zipcode):

    return one_resi_gbutton_project(zipcode,
                                    baseline_start_dt=datetime(2011,1,1,tzinfo=pytz.utc),
                                    report_start_dt=datetime(2013,1,1,tzinfo=pytz.utc),
                                    report_end_dt=datetime(2015,1,1,tzinfo=pytz.utc)
                                    )

def generate_consumptions(weather_source, period, reporting_period):

    # model
    model_e = AverageDailyTemperatureSensitivityModel(cooling=True, heating=True)
    model_g = AverageDailyTemperatureSensitivityModel(cooling=False, heating=True)

    # model params
    params_e_b = {
        "cooling_slope": 1,
        "heating_slope": 1,
        "base_daily_consumption": 30,
        "cooling_balance_temperature": 73,
        "heating_balance_temperature": 68,
    }
    params_e_r = {
        "cooling_slope": .5,
        "heating_slope": .5,
        "base_daily_consumption": 15,
        "cooling_balance_temperature": 73,
        "heating_balance_temperature": 68,
    }
    params_g_b = {
        "heating_slope": .2,
        "base_daily_consumption": 2,
        "heating_balance_temperature": 68,
    }
    params_g_r = {
        "heating_slope": .1,
        "base_daily_consumption": 1,
        "heating_balance_temperature": 68,
    }

    #generators
    gen_e_b = MonthlyBillingConsumptionGenerator("electricity", "kWh", "degF",
            model_e, params_e_b)
    gen_e_r = MonthlyBillingConsumptionGenerator("electricity", "kWh", "degF",
            model_e, params_e_r)
    gen_g_b = MonthlyBillingConsumptionGenerator("natural_gas", "therm", "degF",
            model_g, params_g_b)
    gen_g_r = MonthlyBillingConsumptionGenerator("natural_gas", "therm", "degF",
            model_g, params_g_r)

    datetimes = generate_monthly_billing_datetimes(period, dist=randint(30,31))

    # consumption data - optionally pass in consumpton data here instead
    cd_e_b = gen_e_b.generate(weather_source, datetimes, daily_noise_dist=None)
    cd_e_r = gen_e_r.generate(weather_source, datetimes, daily_noise_dist=None)
    cd_g_b = gen_g_b.generate(weather_source, datetimes, daily_noise_dist=None)
    cd_g_r = gen_g_r.generate(weather_source, datetimes, daily_noise_dist=None)

    periods = cd_e_b.periods()

    # records
    records_e = []
    records_g = []
    for e_b, e_r, g_b, g_r, p in zip(cd_e_b.data, cd_e_r.data, cd_g_b.data, cd_g_r.data, periods):
        e = e_r if p in reporting_period else e_b
        g = g_r if p in reporting_period else g_b
        record_e = {"start": p.start, "end": p.end, "value": e}
        record_g = {"start": p.start, "end": p.end, "value": g}
        records_e.append(record_e)
        records_g.append(record_g)

    # consumption_data
    cd_e = ConsumptionData(records_e, "electricity", "kWh",
            record_type="arbitrary")
    cd_g = ConsumptionData(records_g, "natural_gas", "therm",
            record_type="arbitrary")

    return [cd_e, cd_g]

def one_resi_gbutton_project(zipcode, baseline_start_dt,
                             report_start_dt, report_end_dt,
                             gbutton_e=None, gbutton_g=None):

    # location - optionally pass in lat_lng here
    location = Location(zipcode=zipcode)
    station = location.station
    weather_source = GSODWeatherSource(station,baseline_start_dt.year,report_end_dt.year)

    # time periods
    period = Period(baseline_start_dt, report_end_dt)

    # periods
    reporting_period = Period(report_start_dt, report_end_dt)
    baseline_period = Period(baseline_start_dt, report_start_dt)

    if not (gbutton_e and gbutton_g):
        consumptions = generate_consumptions(weather_source, period, reporting_period)
    else:
        cd_e = import_green_button_xml(gbutton_e)
        # since the resi meter cannot handle 15 min data, convert to day
        cd_e.data = cd_e.data.resample('D').sum()
        cd_g = import_green_button_xml(gbutton_g)
        consumptions = [cd_e, cd_g]

    # project
    project = Project(location, consumptions, baseline_period, reporting_period)

    return project
