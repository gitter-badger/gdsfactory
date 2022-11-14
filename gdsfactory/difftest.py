"""GDS regression test. Adapted from lytest.

TODO: adapt it into pytest_regressions

from pytest_regressions.file_regression import FileRegressionFixture

class GdsRegressionFixture(FileRegressionFixture):
    def check(self,
        contents,
        extension=".gds",
        basename=None,
        fullpath=None,
        binary=False,
        obtained_filename=None,
        check_fn=None,
            ):
        try:
            difftest(c)
"""
import filecmp
import pathlib
import shutil
from typing import Optional, Union

import gdstk

import gdsfactory as gf
from gdsfactory.component import Component
from gdsfactory.config import CONFIG, logger
from gdsfactory.geometry.boolean_klayout import boolean_klayout
from gdsfactory.read.import_gds import import_gds
from gdsfactory.types import PathType

nm = 1e-3


class GeometryDifference(Exception):
    pass


def run_xor_gdstk(
    operand1: Union[PathType, Component],
    operand2: Union[PathType, Component],
    precision: float = 1 * nm,
) -> Component:
    """Returns XOR boolean between two Component or files.

    Raises a GeometryDifference if files are different.

    FIXME!

    Args:
        operand1: Component or gdspath.
        operand2: Component or gdspath.
        precision: defaults to 1e-3 (1nm).
    """
    c1 = import_gds(operand1) if isinstance(operand1, (str, pathlib.Path)) else operand1
    c2 = import_gds(operand2) if isinstance(operand2, (str, pathlib.Path)) else operand2

    xor_polygons = gdstk.boolean(
        operand1=c1.get_polygons(as_array=False),
        operand2=c2.get_polygons(as_array=False),
        operation="xor",
        precision=precision,
        layer=1,
        datatype=0,
    )

    xor = Component("diff")
    xor._cell.add(*xor_polygons)
    return xor


def difftest(
    component: Component,
    test_name: Optional[str] = None,
    xor: bool = True,
    dirpath: pathlib.Path = CONFIG["gdsdiff"],
    with_klayout: bool = True,
) -> None:
    """Avoids GDS regressions tests on the GeometryDifference.

    If files are the same it returns None. If files are different runs XOR
    between new component and the GDS reference stored in dirpath and
    raises GeometryDifference if there are differences and show differences in klayout.

    If it runs for the fist time it just stores the GDS reference.

    Args:
        component: to test if it has changed.
        test_name: used to store the GDS file.
        xor: runs xor if there is difference.
        dirpath: defaults to cwd refers to where the test is being invoked.
    """
    # containers function_name is different from component.name
    # we store the container with a different name from original component
    test_name = test_name or (
        f"{component.function_name}_{component.name}"
        if hasattr(component, "function_name")
        and component.name != component.function_name
        else f"{component.name}"
    )
    filename = f"{test_name}.gds"
    ref_file = dirpath / "gds_ref" / filename
    run_file = dirpath / "gds_run" / filename

    if not ref_file.exists():
        component.write_gds(gdspath=ref_file)
        raise AssertionError(
            f"Reference GDS file for {test_name!r} not found. Writing to {ref_file!r}"
        )
    else:
        component.write_gds(gdspath=run_file)

    if filecmp.cmp(ref_file, run_file, shallow=False):
        return

    c1 = component
    c2 = import_gds(ref_file)
    c = Component(f"{c2.name}_diff")

    if with_klayout:
        xor = Component("diff")
        for layer in c1.layers.union(c2.layers):
            xor.add_ref(
                boolean_klayout(c1, c2, layer1=layer, layer2=layer, layer3=layer)
            )
        xor = xor.flatten()

    else:
        xor = run_xor_gdstk(c1, c2, precision=0.1 * nm)

    if len(xor.get_polygons()) > 0:
        error = f"XOR polygons {c1.name!r} in {str(run_file)!r} changed from {str(run_file)!r}"

    elif c1.layers != c2.layers:
        error = (
            f"Layers {c1.name!r} {c1.layers} changed from {run_file.stem!r} {c2.layers}"
        )

    elif c1.name != c2.name:
        error = f"Top Cell name {c1.name!r} changed from {c2.name!r}"

    else:  # no errors
        return

    logger.error(error)

    c << xor
    c << c1
    c << c2
    c.show(show_ports=False)

    try:
        val = input("Would you like to save current GDS as the new reference? [Y/n] ")
        if val.upper().startswith("N"):
            raise GeometryDifference(error)
        logger.info(f"Deleting file {str(ref_file)!r}")
        ref_file.unlink()
        shutil.copy(run_file, ref_file)
        raise
    except OSError as exc:
        raise GeometryDifference(
            "\n"
            f"{filename!r} changed from reference {str(ref_file)!r}\n"
            "To step over each error you can run `pytest -s`\n"
            "So you can check the differences in Klayout GUI\n"
        ) from exc


def test_xor_no_error():
    c1 = gf.components.rectangle(layer=(1, 0), size=(1, 1))
    c2 = gf.components.rectangle(layer=(1, 0), size=(1, 1), cache=False)
    c = run_xor_gdstk(c1, c2)
    assert not c.get_polygons(), c.get_polygons()


def test_xor_different_layer():
    c1 = gf.components.rectangle(layer=(1, 0), size=(1, 1))
    c2 = gf.components.rectangle(layer=(2, 0), size=(1, 1), cache=False)
    c = run_xor_gdstk(c1, c2)
    assert c.get_polygons(), c.get_polygons()


if __name__ == "__main__":
    # test_xor_no_error()
    # test_xor_no_error()
    # c1 = gf.components.circle(layer=(1, 0), radius=5)
    # c2 = gf.components.circle(layer=(2, 0), radius=5)

    # c1 = c1.write_gds()
    # c2 = c2.write_gds()
    # c = run_xor_gdstk(c1, c2)
    # c.show()

    # c = gf.components.circle(radius=10, layer=(1, 0))
    c = gf.components.circle()
    difftest(c, test_name="circle")
    # test_component(c, None, None)
