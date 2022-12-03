from __future__ import annotations

from typing import Tuple, Union

import gdstk

import gdsfactory as gf
from gdsfactory.component import Component
from gdsfactory.types import ComponentOrReference, Int2, LayerSpec


@gf.cell
def boolean(
    A: Union[ComponentOrReference, Tuple[ComponentOrReference, ...]],
    B: Union[ComponentOrReference, Tuple[ComponentOrReference, ...]],
    operation: str,
    precision: float = 1e-4,
    num_divisions: Union[int, Int2] = (1, 1),
    layer: LayerSpec = (1, 0),
) -> Component:
    """Performs boolean operations between 2 Component/Reference/list objects.

    ``operation`` should be one of {'not', 'and', 'or', 'xor', 'A-B', 'B-A', 'A+B'}.
    Note that 'A+B' is equivalent to 'or', 'A-B' is equivalent to 'not', and
    'B-A' is equivalent to 'not' with the operands switched

    based on phidl.geometry.boolean
    You can also use gdsfactory.drc.boolean_klayout

    Args:
        A: Component(/Reference) or list of Component(/References).
        B: Component(/Reference) or list of Component(/References).
        operation: {'not', 'and', 'or', 'xor', 'A-B', 'B-A', 'A+B'}.
        precision: float Desired precision for rounding vertex coordinates..
        num_divisions: number of divisions with which the geometry is divided into
          multiple rectangular regions. This allows for each region to be
          processed sequentially, which is more computationally efficient.
        layer: Specific layer to put polygon geometry on.

    Returns: Component with polygon(s) of the boolean operations between
      the 2 input Components performed.

    Notes
    -----
    'A+B' is equivalent to 'or'.
    'A-B' is equivalent to 'not'.
    'B-A' is equivalent to 'not' with the operands switched.

    """
    c = Component()

    layers = A.layers.union(B.layers)

    for layer in layers:
        polygons = gdstk.boolean(
            operand1=A.get_polygons(by_spec=layer),
            operand2=B.get_polygons(by_spec=layer),
            operation=operation,
            precision=precision,
            layer=layer[0],
            datatype=layer[1],
        )

        if polygons is not None:
            for polygon in polygons:
                c.add_polygon(polygon, layer=layer)
    return c


def test_boolean() -> None:
    c = gf.Component()
    e1 = c << gf.components.ellipse()
    e2 = c << gf.components.ellipse(radii=(10, 6))
    e3 = c << gf.components.ellipse(radii=(10, 4))
    e3.movex(5)
    e2.movex(2)
    c = boolean(A=[e1, e3], B=e2, operation="A-B")
    assert len(c.polygons) == 2, len(c.polygons)


if __name__ == "__main__":
    # c = gf.Component()
    # e1 = c << gf.components.ellipse()
    # e2 = c << gf.components.ellipse(radii=(10, 6))
    # e3 = c << gf.components.ellipse(radii=(10, 4))
    # e3.movex(5)
    # e2.movex(2)
    # c = boolean(A=[e1, e3], B=e2, operation="A-B")

    import time

    n = 50
    c1 = gf.c.array(gf.c.circle(radius=10), columns=n, rows=n)
    c2 = gf.c.array(gf.c.circle(radius=9), columns=n, rows=n).movex(5)

    t0 = time.time()
    c = boolean(c1, c2, operation="xor")
    t1 = time.time()
    print(t1 - t0)

    c.show(show_ports=True)
