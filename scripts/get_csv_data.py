"""
Extract certain fields from a csv file and create a new csv.
"""
import sys
import os
import csv
import argparse
import logging
log = logging.getLogger(__name__)
from datetime import datetime, timedelta


class GetDataSet(object):
    """Base class that reads one csv and writes another.
    """

    def __init__(self, csv_filename):
        self.fieldnames_in = None
        self.fieldnames_out = None
        self.csv_filename = csv_filename
        self.new_csv_name = None
        self.list_of_dicts = None
        self.get_rows = self.get_csv_bits

    def get_csv_bits(self):
        """Yield some rows from a csv file.
        """
        with open(self.csv_filename, 'rb') as f:
            reader = csv.DictReader(f)
            try:
                for row in reader:
                    if self.keep_me(row):
                        x = {k: row[k] for k in self.fieldnames_in}
                        yield x
            except csv.Error as e:
                sys.exit('line %d: %s' % (reader.line_num, e))

    def keep_me(self, row):
        """Keep this row?
        """
        try:
            for c in self.fieldnames_in:
                if not row[c]:
                    log.info('Skipping row with null %r', c)
                    return False
        except KeyError:
            log.debug("There is no %s in this row." % c)
            return False
        else:
            return True

    def write_new_csv(self):
        """Write out the new csv with only the given fieldnames_out.
        """
        with open(self.new_csv_name, 'wb') as new_csv:
            writer = csv.DictWriter(new_csv, self.fieldnames_out)
            # write the header row out first
            writer.writerow(dict(zip(self.fieldnames_out, self.fieldnames_out)))
            self.save_list_of_dicts()
            for row in self.list_of_dicts:
                writer.writerow(row)
        return(len(self.list_of_dicts))
        # would be nice to return the length of the new file
        # and then print that out with self.new_csv_name

    def save_list_of_dicts(self):
        """Instead of writing out the new csv, maybe we need to save it as a
        list, for subsequent processing or whatever.
        """
        self.list_of_dicts = list()
        for row in self.get_rows():
            self.list_of_dicts.append(row)
        return self.list_of_dicts

    def read_and_write_each_row(self):
        """Immediately write each row that is accepted from the input.
        """
        with open(self.new_csv_name, 'wb') as new_csv:
            writer = csv.DictWriter(new_csv, self.fieldnames_out)
            # write the header row out first
            writer.writerow(dict(zip(self.fieldnames_out, self.fieldnames_out)))
            for row in self.get_rows():
                writer.writerow(row)


class EemeterImporterCSV(GetDataSet):
    """Create a data set with a fixed subset of the columns from the
    assumed columns in the input file.

                project_id,start,end,fuel_type,unit_name,value,estimated

    - project_id: str (basename of csv file here)
    - start: str (ISO 8601 combined date time)
    - end: str (ISO 8601 combined date time)
    - fuel_type: {"natural gas", "electricity"}
    - unit_name: {"therms", "kWh"}
    - value: float
    - estimated: boolean
    """
    def __init__(self, csv_filename, date_start=None, date_end=None):
        super(EemeterImporterCSV, self).__init__(csv_filename)
        self.fieldnames_in = ['Period', 'Consumption']
        self.fieldnames_out = ['project_id', 'start', 'end',
                               'fuel_type', 'unit_name', 'value',
                               'estimated']
        csv_input = os.path.splitext(self.csv_filename)[0]
        self.new_csv_name =  csv_input + '-api.csv'
        self.project_id = os.path.basename(csv_input)
        self.new_csv = None
        self.get_rows = self.fixup_output_rows
        self.date_start = datetime.strptime(
            date_start, '%Y-%m-%d').date() if date_start else None
        self.date_end = datetime.strptime(
            date_end, '%Y-%m-%d').date() if date_end else None

    def keep_me(self, row):
        """Could be slightly different.
        """
        if super(EemeterImporterCSV, self).keep_me(row):
            # so far so good
            # but 'Period' a datetime? and the 'Consumption' a float?
            # if Period is a datetime, is it outside of the given date range?
            # blind faith for now
            return True

    def fixup_output_rows(self):
        mins15 = timedelta(0, 900)
        out_constants = dict()
        out_constants['unit_name'] = 'kWh'
        out_constants['estimated'] = 'False'
        out_constants['fuel_type'] = 'electricity'
        out_constants['project_id'] = self.project_id
        for row in self.get_csv_bits():
            out_row = out_constants.copy()
            out_row['value'] = row['Consumption']
            end_time = datetime.strptime(row['Period'], "%m/%d/%Y %I:%M %p")
            out_row['end'] = str(end_time)
            out_row['start'] = str(end_time - mins15)
            yield out_row




class DatastoreUploaderCSV(GetDataSet):
    """Create a data set with a fixed subset of the columns from the
    assumed columns in the input file.

    - end: str (ISO 8601 combined date time)
    - fuel_type: {"natural gas", "electricity"}
    - project_id: string
    - start: str (ISO 8601 combined date time)
    - unit_name: {"therms", "kWh"}
    - value: float

    """
    def __init__(self, csv_filename):
        super(DatastoreUploaderCSV, self).__init__(csv_filename)
        # would be better to read in 'Period' and one or more columns
        # taking the project_ids from the headers in those columns
        self.fieldnames_in = ['Period', '8189246983-tracy', '5553847436-eureka',
                              '4590556115-richmond']
        self.fieldnames_out = ['end', 'fuel_type', 'project_id',
                               'start', 'unit_name', 'value']
        self.new_csv_name = os.path.splitext(self.csv_filename)[0] + '-ds.csv'
        self.new_csv = None
        self.get_rows = self.triple_output_rows

    def triple_output_rows(self):
        mins15 = timedelta(0, 900)
        out_constants = dict()
        out_constants['unit_name'] = 'kWh'
        out_constants['fuel_type'] = 'electricity'
        for row in self.get_csv_bits():
            for project_id in self.fieldnames_in[-3:]:
                out_row = out_constants.copy()
                out_row['project_id'] = project_id
                end_time = datetime.strptime(row['Period'], "%m/%d/%Y %I:%M %p")
                out_row['end'] = str(end_time)
                out_row['start'] = str(end_time - mins15)
                out_row['value'] = row[project_id]
                yield out_row


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-s',
        '--start_date',
        help='(not implemented yet) Inclusive data start date. yyyy-mm-dd',
    )
    parser.add_argument(
        '-e',
        '--end_date',
        help='(not implemented yet) Exclusive data end date. yyyy-mm-dd',
    )
    parser.add_argument(
        'csv_filename',
        help='The name of the input csv file containing consumption data.',
    )
    parser.add_argument(
        '-d',
        '--datastore',
        action="store_true",
        help='Produce datastore upload format instead of core meter.'
    )
    # add option for different interval length, default 15 mins
    args = parser.parse_args()
    if args.datastore:
        interval_data = DatastoreUploaderCSV(args.csv_filename)
    else:
        interval_data = EemeterImporterCSV(args.csv_filename, args.start_date, args.end_date)
    interval_data.read_and_write_each_row()

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    main()
