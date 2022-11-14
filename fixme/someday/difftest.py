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
import os
import filecmp
import pathlib
import shutil
from typing import Optional, Union
import gdstk

from gdsfactory.component import Component
from gdsfactory.config import CONFIG, logger
from gdsfactory.read.import_gds import import_gds
from gdsfactory.types import PathType
import gdsfactory as gf


class GeometryDifference(Exception):
    pass


def run_xor_gdstk(
    operand1: Union[PathType, Component],
    operand2: Union[PathType, Component],
    precision: float = 1e-3,
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


def run_xor_klayout(
    file1: str,
    file2: str,
    tolerance: int = 1,
    verbose: bool = False,
) -> Component:
    """Returns XOR boolean between two files.

    Raises a GeometryDifference if files are different.

    FIXME!

    Args:
        file1:
        file2:
        tolerance:
        verbose:
    """
    import klayout.db as kdb

    _library = kdb.Library()
    layout = _library.layout()

    l1 = kdb.Layout()
    l1.read(str(file1))

    l2 = kdb.Layout()
    l2.read(str(file2))

    l3 = kdb.Layout()

    # Check that same set of layers are present
    layer_pairs = []
    for ll1 in l1.layer_indices():
        li1 = l1.get_info(ll1)
        ll2 = l2.find_layer(l1.get_info(ll1))
        if ll2 is None:
            raise GeometryDifference(
                f"Layer {li1} of layout {file1!r} not present in layout {file2!r}."
            )

        layer_pairs.append((ll1, ll2))

    for ll2 in l2.layer_indices():
        li2 = l2.get_info(ll2)
        ll1 = l1.find_layer(l2.get_info(ll2))
        if ll1 is None:
            raise GeometryDifference(
                f"Layer {li2} of layout {file2!r} not present in layout {file1!r}."
            )

    # Check that topcells are the same
    tc1_names = [tc.name for tc in l1.top_cells()]
    tc2_names = [tc.name for tc in l2.top_cells()]
    tc1_names.sort()
    tc2_names.sort()
    if tc1_names != tc2_names:
        raise GeometryDifference(
            f"Missing topcell on one of the layouts, or name differs:\n{tc1_names!r}\n{tc2_names!r}"
        )
    topcell_pairs = [(l1.cell(tc1_n), l2.cell(tc1_n)) for tc1_n in tc1_names]
    # Check that dbu are the same
    if (l1.dbu - l2.dbu) > 1e-6:
        raise GeometryDifference(
            f"Database unit of layout {file1!r} ({l1.dbu}) differs from that of layout {file2!r} ({l2.dbu})."
        )

    # Run the difftool
    diff = False
    for tc1, tc2 in topcell_pairs:
        for ll1, ll2 in layer_pairs:
            r1 = kdb.Region(tc1.begin_shapes_rec(ll1))
            r2 = kdb.Region(tc2.begin_shapes_rec(ll2))

            rxor = r1 ^ r2
            l3.shapes(layout.layer(ll1[0], ll1[1])).insert(rxor)

            if tolerance > 0:
                rxor.size(-tolerance)

            if not rxor.is_empty():
                diff = True
                if verbose:
                    print(
                        f"{rxor.size()} differences found in {tc1.name!r} on layer {l1.get_info(ll1)}."
                    )

            elif verbose:
                print(
                    f"No differences found in {tc1.name!r} on layer {l1.get_info(ll1)}."
                )

    if diff:
        fn_abgd = []
        for fn in [file1, file2]:
            head, tail = os.path.split(fn)
            abgd = os.path.join(os.path.basename(head), tail)
            fn_abgd.append(abgd)
        raise GeometryDifference(
            "Differences found between layouts {} and {}".format(*fn_abgd)
        )


def difftest(
    component: Component,
    test_name: Optional[str] = None,
    xor: bool = True,
    dirpath: pathlib.Path = CONFIG["gdsdiff"],
    with_gdstk: bool = True,
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
        with_gdstk: boolean using gdstk. False uses klayout.
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

    if with_gdstk:
        xor = run_xor_gdstk(c1, c2, precision=1 / 1e3)
    else:
        xor = run_xor_klayout(str(ref_file), str(run_file), tolerance=1, verbose=False)

    if len(xor.get_polygons()) > 0:
        error = f"XOR polygons {c1.name!r} in {str(run_file)!r} changed from {str(run_file)!r}"

    elif c1.layers != c2.layers:
        error = (
            f"Layers {c1.name!r} {c1.layers} changed from {run_file.stem!r} {c2.layers}"
        )

    elif c1.name != c2.name:
        error = f"Cell name {c1.name!r} changed from {c2.name!r}"

    else:
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
    assert not c.get_polygons(), c.get_polygons()


if __name__ == "__main__":
    # test_xor_no_error()
    # test_xor_no_error()
    # c1 = gf.components.circle(layer=(1, 0), radius=5)
    # c2 = gf.components.circle(layer=(2, 0), radius=5)

    # c1 = c1.write_gds()
    # c2 = c2.write_gds()
    # c = run_xor_gdstk(c1, c2)
    # c.show()

    c = gf.components.circle(radius=10, layer=(1, 0))
    # c = gf.components.circle()
    difftest(c, test_name="circle")
    # test_component(c, None, None)
