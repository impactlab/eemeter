import scipy.optimize as opt
import numpy as np

class ModelBase(object):
    def __init__(self,x0=None,bounds=None,precompute=False):
        self.x0 = x0
        self.bounds = bounds
        self.precompute = precompute

    def parameter_optimization(self,average_daily_usages,observed_daily_temps, weights=None):
        """Returns parameters which, according to an optimization routine in
        `scipy.optimize`, minimize the sum of squared errors between observed
        usages and the output of the a model which takes observed_daily_temps
        and returns usage estimates.
        """
        # ignore nans
        average_daily_usages = np.ma.masked_array(average_daily_usages,np.isnan(average_daily_usages))

        # precalculate temps
        n_daily_temps = np.array([len(temps) for temps in observed_daily_temps])
        
        if weights == None:
            weights = np.ones(len(average_daily_usages))
        
        if self.precompute:
            compute = precompute_usage_estimates(observed_daily_temps, self.bounds, 10)
        else:
            compute = lambda x: self.compute_usage_estimates(x, observed_daily_temps)
        
        
        def objective_function(params):
            usages_est = compute(params)
            avg_usages_est = usages_est/n_daily_temps
            return np.sum(((average_daily_usages - avg_usages_est)**2)*weights)

        assert len(average_daily_usages) == len(observed_daily_temps)

        result = opt.minimize(objective_function,x0=self.x0,bounds=self.bounds)
        params = result.x
        return params

    @staticmethod
    def compute_usage_estimates(params,observed_daily_temps):
        """Return usage estimates given model parameters and temperature
        observations as an iterable of iterables containing daily temperatures
        (e.g. [[70.1,71.7,46.3],[10.1,15.1,16.0]]). Content and format of
        `params` must be determined by inheriting classes. Function must be
        implemented by all inheriting classes.
        """
        raise NotImplementedError

class HDDCDDBalancePointModel(ModelBase):

    @staticmethod
    def compute_usage_estimates(params,observed_daily_temps):
        """Returns usage estimates for a combined, dual balance point,
        heating/cooling degree day model. Parameters are given in the form
        `params = (ts_low, ts_high, base_load, bp_low, bp_diff)`, in which:

        - `ts_low` is the (generally positive) temperature sensitivity
          (units: usage per hdd) beyond the lower (heating degree day)
          balance point
        - `ts_high` is the (generally positive) temperature sensitivity
          (units: usage per cdd) beyond the upper (cooling degree day balance
          point
        - `base_load` is the daily non-temperature-related usage
        - `bp_low` is the reference temperature of the lower (hdd) balance
          point
        - `bd_diff` is the (generally positive) difference between the
          implicitly defined `bp_high` and `bp_low`

        """
        # get parameters
        ts_low,ts_high,base_load,bp_low,bp_diff = params
        bp_high = bp_low + bp_diff
        
        result = []
        for interval_daily_temps in observed_daily_temps:
            cooling = np.maximum(interval_daily_temps - bp_high, 0)*ts_high
            heating = np.maximum(bp_low - interval_daily_temps, 0)*ts_low
            total = np.sum(cooling+heating) + base_load*len(interval_daily_temps)
            result.append(total)
        return result

class HDDBalancePointModel(ModelBase):

    @staticmethod
    def compute_usage_estimates(params,observed_daily_temps):
        """Returns usage estimates for a simple single balance point, heating
        degree day model. Parameters are given in the form
        `params = (reference_temperature, base_level_consumption,
        heating_slope)`, in which:

        - `reference_temperature` is the temperature base of the heating
          degree day balance point
        - `base_level_consumption` is the daily non-temperature-related
          usage
        - `heating_slope` is the (generally positive) temperature
          sensitivity (units: usage per hdd) beyond the heating degree day
          reference temperature

        """
        # get parameters
        reference_temperature,base_level_consumption,heating_slope = params
        
        result = []
        for interval_daily_temps in observed_daily_temps:
            heating = np.maximum(reference_temperature - interval_daily_temps, 0)*heating_slope
            total = np.sum(heating) + base_level_consumption*len(interval_daily_temps)
            result.append(total)
        return result

class CDDBalancePointModel(ModelBase):

    @staticmethod
    def compute_usage_estimates(params,observed_daily_temps):
        """Returns usage estimates for a simple single balance point, heating
        degree day model. Parameters are given in the form
        `params = (reference_temperature, base_level_consumption,
        cooling_slope)`, in which:

        - `reference_temperature` is the temperature base of the cooling
          degree day balance point
        - `base_level_consumption` is the daily non-temperature-related
          usage
        - `cooling_slope` is the (generally positive) temperature
          sensitivity (units: usage per cdd) beyond the cooling degree day
          reference temperature

        """
        # get parameters
        reference_temperature,base_level_consumption,cooling_slope = params

        result = []
        for interval_daily_temps in observed_daily_temps:
            cooling = np.maximum(interval_daily_temps - reference_temperature, 0)*cooling_slope
            total = np.sum(cooling) + base_level_consumption*len(interval_daily_temps)
            result.append(total)
        return result

def memoize(f):
    class memodict(dict):
         __slots__ = ()
         def __missing__(self, key):
             self[key] = ret = f(key)
             return ret
    return memodict().__getitem__

def memodict(f):
    """ Memoization decorator for a function taking a single argument """
    class memodict(dict):
        def __missing__(self, key):
            ret = self[key] = f(key)
            return ret 
    return memodict().__getitem__

def precompute_usage_estimates(observed_daily_temps, bounds, bp_scale):
    """When observed_daily_temps only take values on a grid
    we can *precisely* compute hdd and cdd at any temperature by computing on the grid and interpolating.
    Here we  use memoization of those gridded calculations to optimize the calculation
    
    bp_scale is an integer representing the grid spacing of 1/bp_scale.
    E.g. bp_scale = 2 means spacing of .5=1/2, bp_scale = 10 means spacing of .1, etc.
    
    TODO: adapt this for one-sided (CDD or HDD) models
    """
    # expand by 1/scale because floats are funny
    bp_cool_min = bounds[3][0]+bounds[4][0]-1.0/bp_scale
    bp_heat_max = bounds[3][1]+1.0/bp_scale
    
    # min and max daily temps for each interval
    # used to avoid calculating cdd and hdd in intervals where there is none
    # e.g. cooling in winter or heating in summer
    max_daily_temps = [np.max(temps) for temps in observed_daily_temps]
    min_daily_temps = [np.min(temps) for temps in observed_daily_temps]
    n_periods = len(observed_daily_temps)
    
    n_days = np.array([len(temps) for temps in observed_daily_temps])
    
    # for a given balance point returns two arrays
    # hdd is an array of heated degree days for each period
    # margin is the number of days in each period with tmperature >= bp
    # intended to be called only for balance points on the grid
    # but works for any balance point
    @memoize
    def __hdd_and_margin(bp):
        hdd = np.zeros(n_periods)
        margin = np.zeros(n_periods)
        for j in xrange(n_periods):
            if bp <= bp_heat_max and bp > min_daily_temps[j]:
                h_array = np.maximum(bp - observed_daily_temps[j], 0)
                hdd[j] = np.sum(h_array)
                margin[j] = np.count_nonzero(h_array)
        return hdd,margin
    
    # uses the hdd_and_margin to precisely calculate hdd at any point
    # the interpolation is precise because it is assumed that observed_daily_temps
    # fall only on the bp_scale grid
    def __hdd(bp):
        rounded = np.floor(bp*bp_scale)/bp_scale
        remainder = bp - rounded
        hdd,margin = __hdd_and_margin(rounded)
        return hdd + remainder*margin
    
    @memoize
    def __cdd_and_margin(bp):
        cdd = np.zeros(n_periods)
        margin = np.zeros(n_periods)
        for j in xrange(n_periods):
            if bp >= bp_cool_min and bp < max_daily_temps[j]:
                c_array = np.maximum(observed_daily_temps[j] - bp, 0)
                cdd[j] = np.sum(c_array)
                margin[j] = np.count_nonzero(c_array)
        return cdd,margin
    
    def __cdd(bp):
        rounded = np.ceil(bp*bp_scale)/bp_scale
        remainder = rounded - bp
        cdd,margin = __cdd_and_margin(rounded)
        return cdd + remainder*margin
    
    def compute_usage_estimates(params):
        ts_low,ts_high,base_load,bp_low,bp_diff = params
        bp_high = bp_low + bp_diff
        
        cooling = __cdd(bp_high)*ts_high
        heating = __hdd(bp_low)*ts_low
        base = n_days * base_load
        
        return (heating+cooling)+base
    
    return compute_usage_estimates