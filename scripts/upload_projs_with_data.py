"""
Call eemeter.uploader.api.upload_csvs

>>> proj = open("data/sears-3-apiprojects.csv", 'rb')
>>> reco = open("data/sears-3-api.csv", 'rb')
>>> upload_csvs(proj, reco, "http://127.0.0.1:8001", "mychosentoken", 1)

"""
import argparse
import logging
log = logging.getLogger(__name__)
from eemeter.uploader.api import upload_csvs


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        'projects_csv_filename',
        help='The name of the input csv file containing project(s) data.',
    )
    parser.add_argument(
        'consumption_csv_filename',
        help='The name of the input csv file containing consumption data.',
    )
    # add option for different interval length, default 15 mins
    args = parser.parse_args()
    proj = open(args.projects_csv_filename, 'rb')
    reco = open(args.consumption_csv_filename, 'rb')
    print("Uploading %s and %s." %
          (args.projects_csv_filename, args.consumption_csv_filename))
    upload_csvs(proj, reco, "http://127.0.0.1:8001", "mychosentoken", 1)

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    main()
