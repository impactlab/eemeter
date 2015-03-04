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

def precompute_usage_estimates(observed_daily_temps, bounds, bp_scale):
    """returns function which computes usage estimates in constant time
    since GSOD temperatures only take discrete values
    can find CDD and HDD simply by precomputing them at those values
    and then adding a remainder term, which simply 
    the product of (distance to the reference temp) and (number of days above/below the balance point)
    
    TODO: adapt this for one-sided (CDD or HDD) models
    """
    # expand by 1/scale because floats are funny
    bps = [t*1.0/bp_scale for t in range(bounds[3][0]*bp_scale-1, (bounds[3][1]+bounds[4][1])*bp_scale+2)]
    bp_cool_min = bounds[3][0]+bounds[4][0]-1.0/bp_scale
    bp_heat_max = bounds[3][1]+1.0/bp_scale
    n_bps = len(bps)
    
    # min and max daily temps for each interval
    # used to avoid calculating cdd and hdd in intervals where there is none
    # e.g. cooling in winter or heating in summer
    max_daily_temps = [np.max(temps) for temps in observed_daily_temps]
    min_daily_temps = [np.min(temps) for temps in observed_daily_temps]
    n_periods = len(observed_daily_temps)
    
    shape = (n_bps, n_periods)
    cdd = np.zeros(shape); hdd = np.zeros(shape);
    cdd_margin = np.zeros(shape); hdd_margin = np.zeros(shape);
    
    for i in xrange(n_bps):
        for j in xrange(n_periods):
            if bps[i] >= bp_cool_min and bps[i] < max_daily_temps[j]:
                c_array = np.maximum(observed_daily_temps[j] - bps[i], 0)
                cdd[i][j] = np.sum(c_array)
                cdd_margin[i][j] = np.count_nonzero(c_array)
            
            if bps[i] <= bp_heat_max and bps[i] > min_daily_temps[j]:
                h_array = np.maximum(bps[i] - observed_daily_temps[j], 0)
                hdd[i][j] = np.sum(h_array)
                hdd_margin[i][j] = np.count_nonzero(h_array)
    
    n_days = np.array([len(temps) for temps in observed_daily_temps])
    min_index = bounds[3][0]*bp_scale-1
    
    def __cdd(bp):
        r = np.ceil(bp*bp_scale)
        index = int(r)-min_index
        
        remainder = r/bp_scale - bp
        return (cdd[index] + remainder*cdd_margin[index])
    
    def __hdd(bp):
        r = np.floor(bp*bp_scale)
        index = int(r)-min_index
        remainder = bp - r/bp_scale 
        return (hdd[index] + remainder*hdd_margin[index])
    
    def compute_usage_estimates(params):
        ts_low,ts_high,base_load,bp_low,bp_diff = params
        bp_high = bp_low + bp_diff
        
        cooling = __cdd(bp_high)*ts_high
        heating = __hdd(bp_low)*ts_low
        base = n_days * base_load
        
        return (heating+cooling)+base
    
    return compute_usage_estimates