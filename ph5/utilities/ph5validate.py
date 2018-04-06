# Derick Hess, Oct 2017

"""
Runs a set of checks on PH5 archive to test for
errors and make sur eit is ready for archival at IRIS DMC
"""
import logging
import subprocess
import sys
from ph5.core import ph5api

PROG_VERSION = "2018.096"


class PH5ValidateException(Exception):
    pass


class PH5Validate(object):
    def __init__(self, ph5API_object, ph5path,
                 level, outfile):
        if level == "ERROR":
            logging.basicConfig(filename=outfile,
                                format='%(levelname)s: %(message)s',
                                filemode='w',
                                level=logging.ERROR)
        elif level == "WARNING":
            logging.basicConfig(filename=outfile,
                                format='%(levelname)s: %(message)s',
                                filemode='w',
                                level=logging.WARNING)
        elif level == "DEBUG":
            logging.basicConfig(filename=outfile,
                                format='%(levelname)s: %(message)s',
                                filemode='w',
                                level=logging.DEBUG)
        else:
            raise PH5ValidateException("Invalid Level %s" % level)

        self.ph5 = ph5API_object
        self.path = ph5path
        if not self.ph5.Array_t_names:
            self.ph5.read_array_t_names()
        if not self.ph5.Experiment_t:
            self.ph5.read_experiment_t()
        # Set up logging. Do not append

        return

    def read_arrays(self, name):

        if name is None:
            for n in self.ph5.Array_t_names:
                self.ph5.read_array_t(n)
        else:
            self.ph5.read_array_t(name)

    def read_events(self, name):

        if name is None:
            for n in self.ph5.Event_t_names:
                self.ph5.read_event_t(n)
        else:
            self.ph5.read_event_t(name)

    def check_experiment_t(self):
        experiment_t = self.ph5.Experiment_t['rows']
        logging.info("Checking Experiment Table")
        if len(experiment_t) == 0:
            logging.error("Experiment_t does not exist. "
                          "run experiment_t_gen to create table")
            return
        if len(experiment_t) > 1:
            logging.error("Metadata for more than one experiment found "
                          "in experiment_t")
            return
        if not experiment_t[0]['net_code_s']:
            logging.error('Network code was not found: '
                          'A 2 character network code is required.')

        if not experiment_t[0]['experiment_id_s']:
            logging.error('Experiment ID was not found: '
                          'An experiment id (YY-XXX) is required.')

        if not experiment_t[0]['nickname_s']:
            logging.warning('Nickname was not found: '
                            'It is suggested you include a nickname '
                            'for your experiment')

        if not experiment_t[0]['longname_s']:
            logging.warning('long name was not found: '
                            'It is suggested you include a long name '
                            'for your experiment')

        if not experiment_t[0]['PIs_s']:
            logging.warning('PIs were not found: '
                            'It is suggested you include the PIs '
                            'for your experiment')

        if not experiment_t[0]['institutions_s']:
            logging.warning("Institutions were not found: "
                            "It is suggested you include the institutions "
                            "for your experiment")

        if (experiment_t[0]['north_west_corner/X/value_d'] == 0.0):
            logging.warning('A bounding box was not detected: '
                            'A suggested bounding box has been calculated '
                            'and saved in experiment_t_bounding_box.kef')
            max_lat = None
            min_lat = None
            max_lon = None
            min_lon = None

            array_names = sorted(self.ph5.Array_t_names)

            for array_name in array_names:
                self.read_arrays(array_name)
                arraybyid = self.ph5.Array_t[array_name]['byid']
                arrayorder = self.ph5.Array_t[array_name]['order']
                for ph5_station in arrayorder:
                    station_list = arraybyid.get(ph5_station)
                    for deployment in station_list:
                        station_len = len(station_list[deployment])
                        for st_num in range(0, station_len):

                            latitude = station_list[deployment][
                                st_num]['location/Y/value_d']
                            longitude = station_list[deployment][
                                st_num]['location/X/value_d']

                            if max_lat is None:
                                max_lat = latitude
                            elif latitude > max_lat:
                                max_lat = latitude
                            if min_lat is None:
                                min_lat = latitude
                            elif latitude < min_lat:
                                min_lat = latitude
                            if max_lon is None:
                                max_lon = longitude
                            elif longitude > max_lon:
                                max_lon = longitude
                            if min_lon is None:
                                min_lon = longitude
                            elif longitude < min_lon:
                                min_lon = longitude

            shot_lines = sorted(self.ph5.Event_t_names)

            for line in shot_lines:
                event_t = self.ph5.Event_t[line]['byid']
                for shot_id, _ in event_t.iteritems():
                    event_t = self.ph5.Event_t[
                        line]['byid'][shot_id]
                    latitude = event_t[
                        'location/Y/value_d']
                    longitude = event_t[
                        'location/X/value_d']
                    if max_lat is None:
                        max_lat = latitude
                    elif latitude > max_lat:
                        max_lat = latitude
                    if min_lat is None:
                        min_lat = latitude
                    elif latitude < min_lat:
                        min_lat = latitude
                    if max_lon is None:
                        max_lon = longitude
                    elif longitude > max_lon:
                        max_lon = longitude
                    if min_lon is None:
                        min_lon = longitude
                    elif longitude < min_lon:
                        min_lon = longitude

            process = subprocess.Popen(
                "ph5tokef -n master.ph5 -p %s -E >"
                "experiment_t_bounding_box.kef" % (str(self.path)),
                shell=True,
                stdout=subprocess.PIPE)
            process.wait()
            new_kef = []
            with open("experiment_t_bounding_box.kef") as f:
                kef = f.readlines()
            for line in kef:
                if line.startswith("	north_west_corner/X/value_d="):
                    new_kef.append("	north_west_corner/X/value_d=%s\n" %
                                   str(min_lon))
                elif line.startswith("	north_west_corner/Y/value_d="):
                    new_kef.append("	north_west_corner/Y/value_d=%s\n" %
                                   str(max_lat))
                elif line.startswith("	south_east_corner/X/value_d="):
                    new_kef.append("	south_east_corner/X/value_d=%s\n" %
                                   str(max_lon))
                elif line.startswith("	south_east_corner/Y/value_d"):
                    new_kef.append("	south_east_corner/Y/value_d=%s\n" %
                                   str(min_lat))
                else:
                    new_kef.append(line)
            outfile = open("experiment_t_bounding_box.kef", 'w')
            for line in new_kef:
                outfile.write("%s" % line)
        return

    def check_stations(self):
            logging.info("Checking Stations...")
            array_names = sorted(self.ph5.Array_t_names)

            for array_name in array_names:
                self.read_arrays(array_name)
                arraybyid = self.ph5.Array_t[array_name]['byid']
                arrayorder = self.ph5.Array_t[array_name]['order']
                for ph5_station in arrayorder:
                    station_list = arraybyid.get(ph5_station)
                    for deployment in station_list:
                        station_len = len(station_list[deployment])
                        for st_num in range(0, station_len):
                            station_id = station_list[deployment][
                                st_num]['id_s']
                            serial = station_list[deployment][
                                st_num]['das/serial_number_s']
                            channel = station_list[deployment][
                                st_num]['channel_number_i']
                            logging.info("Station %s Channel %s"
                                         % (str(station_id),
                                            str(channel)))
                            if not station_list[deployment][
                                   st_num]['seed_station_name_s']:
                                logging.error("SEED station name required.")

                            response_t = self.ph5.get_response_t_by_n_i(
                                         station_list[deployment][
                                             st_num]['response_table_n_i'])
                            if response_t is None:
                                logging.error("No Response table found."
                                              "Have you run load_resp yet?")

                            deploy_time = station_list[deployment][
                                         st_num]['deploy_time/epoch_l']
                            pickup_time = station_list[deployment][
                                         st_num]['pickup_time/epoch_l']

                            self.ph5.read_das_t(serial, deploy_time,
                                                pickup_time, reread=False)

                            if serial not in self.ph5.Das_t:
                                logging.error("No data found for: %s"
                                              " You may need "
                                              "to reload the raw data for "
                                              "this station."
                                              % (str(station_id)))
                            try:
                                ph5api.filter_das_t(self.ph5.Das_t[
                                                    serial]['rows'],
                                                    channel)
                            except:
                                logging.warning("No data found for channel %s"
                                                " Other channels seem to exist"
                                                % (str(channel)))

                            if station_list[deployment][
                                         st_num]['sample_rate_i'] == 0:
                                logging.warning("Sample rate seems to be 0."
                                                " Is this correct???")
                            if station_list[deployment][
                                         st_num][
                                         'sample_rate_multiplier_i'] == 0:
                                logging.warning("Sample rate multiplier 0."
                                                " Is this correct???")

            return


def get_args():

    import argparse

    parser = argparse.ArgumentParser(
        description='Runs set of checks on PH5 archvive',
        usage=('Version: %s ph5validate--nickname="Master_PH5_file" [options]'
               % (PROG_VERSION)))

    parser.add_argument(
        "-n", "--nickname", action="store", default="master.ph5",
        type=str, metavar="nickname")

    parser.add_argument(
        "-p", "--ph5path", action="store", default=".",
        type=str, metavar="ph5_path")

    parser.add_argument(
        "-l", "--level", action="store", default="ERROR",
        type=str, metavar="level",
        help="Level of logging detail. Choose from ERROR, WARNING, DEBUG")

    parser.add_argument("-o", "--outfile", action="store",
                        default="PH5Validate.log", type=str,
                        metavar="outfile",
                        )

    the_args = parser.parse_args()
    return the_args


def main():
    try:
        args = get_args()
        ph5API_object = ph5api.PH5(path=args.ph5path, nickname=args.nickname,)
        ph5validate = PH5Validate(ph5API_object,
                                  args.ph5path,
                                  args.level.upper(),
                                  args.outfile)
        ph5validate.check_experiment_t()
        ph5validate.check_stations()
        ph5API_object.close()
        sys.stdout.write("\nWarnings, Errors and suggestions written "
                         "to logfile: %s\n\n" % (args.outfile))
    except ph5api.APIError as err:
        sys.stdout.write("%s\n" % err)
    except PH5ValidateException as err:
        sys.stdout.write("%s\n" % err)


if __name__ == '__main__':
    main()
