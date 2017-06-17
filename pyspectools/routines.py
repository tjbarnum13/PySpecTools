""" Routines to:
    Parse cat files
    Run SPFIT and/or SPCAT
"""

import os
import subprocess
import shutil
import json
from pyspectools import pypickett as pp
from pyspectools import parsecat as pc
from glob import glob

def run_spcat(filename):
    # Run SPCAT
    parameter_file = filename + ".var"
    if os.path.isfile(filename + ".var") is False:
        print("VAR file unavailable. Attempting to run with PAR file.")
        if os.path.isfile(filename + ".par") is False:
            raise FileNotFoundError("No .var or .par file found.")
        else:
            shutil.copy2(filename + ".par", parameter_file)
    process = subprocess.Popen(["spcat", filename + ".int", parameter_file],
                     stdout=subprocess.DEVNULL            # suppress stdout
                     )
    process.wait()


def run_calbak(filename):
    """ Runs the calbak routine, which generates a .lin file from the .cat """
    if os.path.isfile(filename + ".cat") is False:
        raise FileNotFoundError(filename + ".cat is missing; cannot run calbak.")
    process = subprocess.Popen(
        [
            "calbak",
            filename + ".cat",
            filename + ".lin"
        ],
        stdout=subprocess.DEVNULL
    )
    process.wait()
    with open(filename + ".lin") as read_file:
        lin_length = read_file.readlines()
    if lin_length == 0:
        raise RuntimeError("No lines produced in calbak! Check .cat file.")


def run_spfit(filename):
    """ Runs the SPFIT program to fit the lines extracted from the .lin file """
    process = subprocess.Popen(["spfit", filename + ".lin", filename + ".par"],
                               stdout=subprocess.DEVNULL
                               )
    process.wait()


def pickett_molecule(json_filepath=None):
    # Provide a JSON file with all the Pickett settings, and generate an
    # instance of the molecule class
    if json_filepath is None:
        print("No JSON input file specified.")
        print("A template file will be created in your directory; please rerun\
               after setting up the parameters.")
        copy_template()
        raise FileNotFoundError("No input file specified.")
    json_data = read_json(json_filepath)
    molecule_object = pp.molecule(json_data)
    return molecule_object


def human2pickett(name, reduction="A", linear=True, nuclei=0):
    """ Function for translating a Hamiltonian parameter to a Pickett
        identifier.

        An alternative way of doing this is to programmatically
        generate the Pickett identifiers, and just use format string
        to output the identifier.
    """
    pickett_parameters = {
        "B": {                         # B rotational constant for
            "linear": 100,             # linear molecule
            "top": 20000,              # top molecule
        },
        "A": 10000,                    # A rotational constant
        "C": 30000,                    # C rotational constant
        "D": 200,                      # quartic centrifugal, linear
        "H": 300,                      # sextic centrifugal, linear
        "D_J": {             # centrifugal, J
            "A": 200,
            "S": 200,
        },
        "D_K": {             # centrifugal, K
            "A": 2000,
            "S": 2000,
        },
        "D_JK": {            # centrifugal, JK
            "A": 1100,
            "S": 1100,
        },
        "del J": {
            "A": 40100,
            "S": 40100,
        },
        "del K": {
            "A": 41000,
            "S": 50000,
        },
        "gamma": "10000000",           # spin-rotation
        "gammaD": "10000100",          # spin-rotation, quadratic distortion
        "gammaH": "10000200",          # spin-rotation, sextic distortion
        "bF": "120000000",             # Fermi contact interaction
        "c": "120010000",       # electron spin/nuclear spin, diagonal
        "eQq": "{0}20010000",     # quadrupole, diagonal; note this is 1.5x!
        "eQq/2": "-{0}20010000",  # quadrupole, off-diagonal
        "C_I": "20000000",             # nuclear spin-rotation, diagonal
        "C_I_prime": "0"                    # off-diagonal
    }
    if name is "B" and linear is True:
        # Haven't thought of a clever way of doing this yet...
        identifier = 100
    elif name is "B" and linear is False:
        identifier = 20000
    else:
        # Hyperfine terms
        if name in ["eQq", "eQq/2"]:
            identifier = str(pickett_parameters[name]).format(nuclei)
        elif "D_" in name or "del" in name:
            identifier = str(pickett_parameters[name][reduction])
        else:
            try:
                identifier = pickett_parameters[name]
            except KeyError:
                print("Parameter name unknown!")
    return identifier


def read_json(json_filepath):
    with open(json_filepath, "r") as read_file:
        json_data = json.load(read_file)
    return json_data


def dump_json(json_filepath, json_dict):
    with open(json_filepath, "w+") as write_file:
        json.dump(json_dict, write_file, indent=4, sort_keys=True)


def generate_folder():
    """ Generates the folder for the next calculation
    and returns the next calculation number
    """
    folderlist = list_directories()      # get every file/folder in directory
    # filter out any non-folders that happen to be here
    shortlist = list()
    for folder in folderlist:
        try:
            shortlist.append(int(folder))
        except ValueError:                  # if it's not an integer
            pass
    if len(shortlist) == 0:
        lastcalc = 0
    else:
        lastcalc = max(shortlist)
    #lastcalc = len(folderlist)
    os.mkdir(str(lastcalc + 1))
    return lastcalc + 1


def format_uncertainty(value, uncertainty):
    """ Function to determine the number of decimal places to
        format the uncertainty. Probably not the most elegant way of doing this.
    """
    # Convert the value into a string, then determine the length by
    # splitting at the decimal point
    decimal_places = decimal_length(value)
    uncertainty = float(uncertainty)           # make sure we're dealing floats
    uncertainty_places = decimal_length(uncertainty)
    # Force the uncertainty into decimals
    uncertainty = uncertainty * 10**-uncertainty_places[1]
    # Work out how many places we've moved now
    uncertainty_places = decimal_length(uncertainty)
    # Move the precision of the uncertainty to match the precision of the value
    uncertainty = uncertainty * 10**(uncertainty_places[1] - decimal_places[1])
    return uncertainty


def decimal_length(value):
    # Function that determines the decimal length of a float; convert the value
    # into a string, then work out the length by splitting at the decimal point
    decimal_split = str(value).split(".")
    return [len(position) for position in decimal_split]


def copy_template():
    script_location = os.path.dirname(os.path.realpath(__file__))
    templates_folder = script_location + "/templates/"
    available_templates = glob(templates_folder + "*.json")
    available_templates = [template.split("/")[-1] for template in available_templates]
    print("The templates available are:")
    for template in available_templates:
        print(template)
    target = input("Please specify which template to copy:      ")
    if target not in available_templates:
        print("Not a template; probably a typo.")
        print("Please re-run the script.")
    else:
        shutil.copy2(templates_folder + target, os.getcwd() + "/parameters.json")
        print("Copied template " + target + " to your folder as parameters.json.")
        print("Edit the .json input file and re-run the script.")


def list_directories():
    return [directory for directory in os.listdir() if os.path.isdir(directory)]


def backup_files(molecule_name, save_location):
    extensions = [".cat", ".var", ".par", ".int", ".json", ".lin"]
    filenames = [molecule_name + ext for ext in extensions]
    for filename in filenames:
        if os.path.isfile(filename) is True:
            shutil.copy2(filename, save_location)
            print("Backing up " + filename + " to " + save_location)
        else:
            pass


def isnotebook():
    # Check if the code is being run in a notebook, IPython shell, or Python
    try:
        shell = get_ipython().__class__.__name__
        if shell == 'ZMQInteractiveShell':  # Jupyter notebook or qtconsole?
            return True
        elif shell == 'TerminalInteractiveShell':  # Terminal running IPython?
            return False
        else:
            return False  # Other type (?)
    except NameError:
        return False      # Probably standard Python interpreter
