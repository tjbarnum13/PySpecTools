"""
    database.py

    Routines for managing a spectral line database.

    TODO - set up routines for a persistent database
"""

import os
import warnings
from typing import List, Dict, Union, Any
from ast import literal_eval

import tinydb
from tinydb import TinyDB, Query
from tinydb.middlewares import CachingMiddleware
from tinydb.storages import JSONStorage
import pandas as pd

from pyspectools import parsers
from pyspectools import spectra
from pyspectools.routines import sanitize_formula
from pyspectools.pypickett import load_molecule_yaml


class SpectralCatalog(TinyDB):
    """
    Grand unified experimental catalog. Stores assignment and uline information
    across the board.
    """

    def __init__(self, dbpath=None):
        if dbpath is None:
            dbpath = os.path.expanduser("~/.pyspectools/pyspec_experiment.db")
        super().__init__(
            dbpath,
            sort_keys=True,
            indent=4,
            separators=(",", ": "),
            storage=CachingMiddleware(JSONStorage),
        )

    def __exit__(self, exc_type, exc_value, traceback):
        """
        Dunder method that should be called when the object is destroyed. This will make sure
        the database is saved properly.
        """
        self.close()

    def add_entry(self, assignment, dup_check=True):
        """
        This function adds an Transition object to an existing database. The method will
        check for duplicates before adding.

        Parameters
        ----------
        assignment - Transition object
            Reference to an Transition object
        dup_check - bool, optional
            If True (default), will check to make sure the Transition object doesn't already exist in
            the database.
        """
        add = False
        if type(assignment) != dict:
            new_entry = assignment.__dict__
        else:
            new_entry = assignment
        if dup_check is True:
            if any([new_entry == entry for entry in self.all()]) is False:
                add = True
            else:
                warnings.warn("Entry already exists in database.")
        else:
            add = True
        if add is True:
            self.insert(new_entry)

    def add_catalog(self, catalog_path, name, formula, **kwargs):
        """
        Load a SPCAT catalog file into the database. Creates independent Transition objects
        from each line of the catalog file. Kwargs are passed into the Transition object,
        which will allow additional settings for the Transition object to be accessed.
        :param catalog_path:
        :param name:
        :param formula:
        :param kwargs:
        :return:
        """
        # check if the name and formula exists already
        exist_df = self.search_molecule(name)
        cat_df = parsers.parse_cat(catalog_path)
        if exist_df is not None:
            # drop all of the entries that are already in the catalog
            exist_freqs = exist_df["frequency"].values
            cat_df = cat_df.loc[~cat_df["Frequency"].isin(list(exist_freqs)),]
        assign_dict = {"name": name, "formula": formula}
        assign_dict.update(**kwargs)
        # slice out only the relevant information from the dataframe
        select_df = cat_df[["Frequency", "Intensity", "Lower state energy"]]
        select_df.columns = ["catalog_frequency", "catalog_intensity", "ustate_energy"]
        select_dict = select_df.to_dict(orient="records")
        # update each line with the common data entries
        assignments = [
            spectra.assignment.Transition(**line, **assign_dict).__dict__
            for line in select_dict
        ]
        # Insert all of the documents en masse
        self.insert_multiple(assignments)

    def search_frequency(self, frequency, freq_prox=0.1, freq_abs=True, dataframe=True):
        """\
        :param frequency: float, center frequency to search for in the database
        :param freq_prox: float, search range tolerance. If freq_abs is True, the absolute value is used (in MHz).
                          Otherwise, freq_prox is a decimal percentage of the frequency.
        :param freq_abs: bool, dictates whether the absolute value of freq_prox is used.
        :return:
        """
        frequency = float(frequency)
        if freq_abs is True:
            min_freq = frequency - freq_prox
            max_freq = frequency + freq_prox
        else:
            min_freq = frequency * (1 - freq_prox)
            max_freq = frequency * (1 + freq_prox)
        Entry = tinydb.Query()
        matches = self.search(
            (Entry["frequency"] <= max_freq) & (min_freq <= Entry["frequency"])
            | (Entry["catalog_frequency"] <= max_freq)
            & (min_freq <= Entry["catalog_frequency"])
        )
        if len(matches) != 0:
            if dataframe is True:
                return pd.DataFrame(matches)
            else:
                return matches
        else:
            return None

    def _search_field(self, field, value, dataframe=True):
        """
        Function for querying the database for a particular field and value.
        The option dataframe specifies whether the matches are returned as a
        pandas datafarame, or as a list of Transition objects.
        :param field: str field to query
        :param value: value to compare with
        :param dataframe: bool, if True will return the matches as a pandas dataframe.
        :return:
        """
        matches = self.search(tinydb.where(field) == value)
        if len(matches) != 0:
            if dataframe is True:
                df = pd.DataFrame(matches)
                return df
            else:
                objects = [spectra.transition.Transition(**data) for data in matches]
                return objects
        else:
            return None

    def search_molecule(self, name, dataframe=True):
        """
        Search for a molecule in the database based on its name (not formula!).
        Wraps the _search_field method, which will return None if nothing is found, or either a
        pandas dataframe or a list of Transition objects
        :param name: str, name (not formula) of the molecule to search for
        :param dataframe: bool, if True, returns a pandas dataframe
        :return: matches: a dataframe or list of Transition objects that match the search name
        """
        matches = self._search_field("name", name, dataframe)
        return matches

    def search_experiment(self, exp_id, dataframe=True):
        matches = self._search_field("experiment", exp_id, dataframe)
        return matches

    def search_formula(self, formula, dataframe=True):
        matches = self._search_field("formula", formula, dataframe)
        return matches

    def _remove_field(self, field, value):
        Entry = tinydb.Query()
        self.remove(Entry[field] == value)

    def remove_experiment(self, exp_id):
        """
        Remove all entries based on an experiment ID.
        :param exp_id: int, experiment ID
        """
        self._remove_field("exp_id", exp_id)

    def remove_molecule(self, name):
        self._remove_field("name", name)


class TheoryCatalog(tinydb.TinyDB):
    """
    Grand unified theory catalog.
    """

    def __init__(self, dbpath=None):
        if dbpath is None:
            dbpath = os.path.expanduser("~/.pyspectools/pyspec_theory.db")
        super().__init__(dbpath)


class MoleculeDatabase(TinyDB):

    default_table_name = "molecule_database"

    """
    Database for molecular parameters, intended for
    use with the `pypickett` module interface.
    
    The main goal of this is for bookkeeping what
    molecules are known, where the Hamiltonian parameters
    come from (i.e. paper), and a simple interface to
    retrieve and regenerate the catalog for that particular
    molecule.
    
    TODO-extend to know what molecule is found in what
    experiment
    """
    def __init__(self, dbpath=None):
        if dbpath is None:
            dbpath = os.path.expanduser("~/.pyspectools/molecules.db")
        super().__init__(
            dbpath,
            sort_keys=True,
            indent=4,
            separators=(",", ": ")
        )

    def get_query(self, field: str, value: Any) -> Union[None, List[Dict[str, Union[str, float]]]]:
        """
        Generic method to retrieve entries in the database for 
        a given field and specified value. This is a lower
        level method, and unless you know what you're looking for,
        it is recommended you use specialized functions like
        `get_formula` and `get_smiles`.

        Parameters
        ----------
        field : str
            Name of the field to search for.
        value : Any
            Value to search a field for.

        Returns
        -------
        Union[None, List[Dict[str, Union[str, float]]]]
            Returns None if no records are found, otherwise
            a list of records with a matching field/value.
        """
        query = getattr(Query(), field)
        return self.get(query == value)

    def get_formula(self, formula: str, sanitize: bool = True) -> Union[None, List[Dict[str, Union[str, float]]]]:
        """
        Search the database for a formula match. For better
        specificity, it is recommended to use SMILES instead.
        
        This function will first 

        Parameters
        ----------
        formula : str
            Chemical formula to query.
    
        sanitize : bool, optional
            Whether or not to sanitize the formula before queries.
            By default, True.

        Returns
        -------
        Union[None, List[Dict[str, Union[str, float]]]]
            [description]
        """
        if sanitize:
            formula = sanitize_formula(formula)
            warnings.warn(f"Formula sanitized to: {formula}. If results not working as intended, rerun with `sanitize=False`.")
        return self.get_query("formula", formula)

    def get_smiles(self, smiles: str) -> Union[None, List[Dict[str, Union[str, float]]]]:
        return self.get_query("smiles", smiles)

    def match_constants(self, percent_tol: float = 0.01, match_all: bool = True, **kwargs) -> Union[None, List[Dict[str, Union[str, float]]]]:
        """
        A generic function for searching the database for approximate
        matches to an arbitrary number of constants. The matching
        is done with a percentage tolerance, and returns records that
        contain records with fields (constants) that are within `percent_tol`
        of the specified value.
        
        A note on security: this method uses `literal_eval`, which executes arbitrary
        code. Please validate all data to ensure there is no malicious code
        before executing this function.

        Parameters
        ----------
        percent_tol : float, optional
            Percentage tolerance to match, by default 0.01

        match_all : bool, optional
            Flag to specify what comparison logic to use; if True,
            all conditions must be satisified, otherwise logical OR.
        
        Kwargs are used to construct the field/value queries.
        Example: `match_constants(percent_tol=0.1, A=10000.)`
        will query the database for records where 9000 <= A <= 11000.

        Returns
        -------
        Union[None, List[Dict[str, Union[str, float]]]]
            [description]
        """
        query = Query()
        commands = []
        condition = " & " if match_all is True else " | "
        for field, value in kwargs.items():
            lower, upper = value * (1 - percent_tol), value * (1 + percent_tol)
            commands.append(f"({lower} <= query.{field} <= {upper})")
        return self.get(literal_eval(condition.join(commands)))

    def add_molecule_yaml(self, yml_path: str) -> None:
        (mol, metadata, var_kwargs) = load_molecule_yaml(yml_path)
        metadata["var_kwargs"] = var_kwargs
        if self.get_query("md5", metadata.get("md5")):
            raise KeyError(f"""Molecule with MD5 hash: {metadata.get("md5")} already exists.""")
        self.insert(metadata)
