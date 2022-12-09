import klayout.db as pya

import gdsfactory as gf
from gdsfactory.component import Component

valid_operations = ("xor", "not", "and", "or")


def boolean(
    A: Component,
    B: Component,
    operation: str = "xor",
):
    """Returns a boolean operation between two components Uses klayout python API.

    Args:
        A: Component.
        B: Component.
        operation: can be xor, not, and, or.

    """

    if operation not in valid_operations:
        raise ValueError(f"{operation} not in {valid_operations}")

    cell1 = A._cell
    cell2 = B._cell

    layout = pya.Layout()
    c = layout.create_cell("boolean")

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

        layout3.shapes(layout.layer(layer[0], layer[1])).insert(result)
    return c


if __name__ == "__main__":
    # _show_shapes()
    c1 = gf.components.ellipse(radii=[8, 8], layer=(1, 0))
    c2 = gf.components.ellipse(radii=[11, 4], layer=(1, 0))
    c = boolean(c1, c2, operation="not")
    c.show(show_ports=True)
