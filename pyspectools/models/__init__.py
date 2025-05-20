from logging import getLogger
from importlib.util import find_spec

from pyspectools.models.classes import SpecConstants, MoleculeResult, MoleculeDetective

logger = getLogger("pyspectools.ml")
logger.setLevel("WARNING")

if find_spec("torch"):
    from pyspectools.models.torch_models import (
        VarMolDetect,
        VariationalDecoder,
        VariationalSpecDecoder,
    )
else:
    logger.warning(
        "PyTorch is not installed. To use ML models, please run `pip install torch`."
    )

__all__ = [
    "SpecConstants",
    "MoleculeDetective",
    "MoleculeResult",
    "VarMolDetect",
    "VariationalSpecDecoder",
    "VariationalDecoder",
]
