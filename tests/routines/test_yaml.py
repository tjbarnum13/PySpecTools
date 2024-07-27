from __future__ import annotations

import pytest

from pyspectools.routines import read_yaml, dump_yaml


@pytest.mark.dependency()
def test_read_linelist():
    data = read_yaml("example.yml")
    assert data
    assert "2-phenylacetonitrile" in data
    for key in ["formula", "filepath"]:
        assert key in data["2-phenylacetonitrile"]


@pytest.mark.dependency(depends=["test_read_linelist"])
def test_write_yaml(tmpdir):
    tmp_file = tmpdir.mkdir("temp_yml").join("tmp_file.yml")
    dumb_data = {"ch3cn": {"formula": "ch3cn", "filepath": None}}
    dump_yaml(tmp_file, dumb_data)
    # now do a round trip
    reload = read_yaml(tmp_file)
    assert "ch3cn" in reload
