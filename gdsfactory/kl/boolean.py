from typing import Tuple

import klayout.db as pya

import gdsfactory as gf
from gdsfactory.kl.component import Component
from gdsfactory.kl.component_layout import layout

valid_operations = ("xor", "not", "and", "or")


def boolean(
    A: Component,
    B: Component,
    layer1: Tuple[int, int] = (1, 0),
    layer2: Tuple[int, int] = (1, 0),
    layer3: Tuple[int, int] = (2, 0),
    operation: str = "xor",
    tolerance: int = 0,
) -> Component:
    """Returns a boolean operation between two components Uses klayout python API.

    Args:
        A: Component.
        B: Component.
        layer1: tuple for gdspath1.
        layer2: tuple for gdspath2.
        layer3: for the result of the operation.
        operation: can be xor, not, and, or.
        tolerance: in database units.

    """

    if operation not in valid_operations:
        raise ValueError(f"{operation} not in {valid_operations}")

    cell1 = A._cell
    cell2 = B._cell

    c = Component()

    layers = A.get_layers() + B.get_layers()
    layout3 = c._cell

    for layer in layers:
        a = pya.Region(cell1.begin_shapes_rec(layout.layer(layer[0], layer[1])))
        b = pya.Region(cell2.begin_shapes_rec(layout.layer(layer[0], layer[1])))

        if operation == "xor":
            result = a ^ b
        elif operation == "not":
            result = a - b
        elif operation == "and":
            result = a & b
        elif operation == "or":
            result = a | b

        if tolerance > 0:
            result.size(-tolerance)

        layout3.shapes(layout.layer(layer3[0], layer3[1])).insert(result)
    return c


if __name__ == "__main__":
    # _show_shapes()
    c1 = gf.components.ellipse(radii=[8, 8], layer=(1, 0))
    c2 = gf.components.ellipse(radii=[11, 4], layer=(1, 0))

    c1 = c1.to_component_klayout()
    c2 = c2.to_component_klayout()
    c = boolean(c1, c2, operation="not")
    c.show(show_ports=True)
