import typing
from typing import Dict, List, Tuple, Union

import klayout.db as kdb
import numpy as np
from numpy import cos, float64, int64, mod, ndarray, pi, sin

from gdsfactory.component_layout import _GeometryHelper, _parse_coordinate, layout
from gdsfactory.port import Port, select_ports

if typing.TYPE_CHECKING:
    from gdsfactory.component import Component

Number = Union[float64, int64, float, int]
Coordinate = Union[Tuple[Number, Number], ndarray, List[Number]]
Coordinates = Union[List[Coordinate], ndarray, List[Number], Tuple[Number, ...]]


class SizeInfo:
    def __init__(self, bbox: ndarray) -> None:
        """Initialize this object."""
        self.west = bbox[0, 0]
        self.east = bbox[1, 0]
        self.south = bbox[0, 1]
        self.north = bbox[1, 1]

        self.width = self.east - self.west
        self.height = self.north - self.south

        xc = 0.5 * (self.east + self.west)
        yc = 0.5 * (self.north + self.south)

        self.sw = np.array([self.west, self.south])
        self.se = np.array([self.east, self.south])
        self.nw = np.array([self.west, self.north])
        self.ne = np.array([self.east, self.north])

        self.cw = np.array([self.west, yc])
        self.ce = np.array([self.east, yc])
        self.nc = np.array([xc, self.north])
        self.sc = np.array([xc, self.south])
        self.cc = self.center = np.array([xc, yc])

    def get_rect(
        self, padding=0, padding_w=None, padding_e=None, padding_n=None, padding_s=None
    ) -> Tuple[Coordinate, Coordinate, Coordinate, Coordinate]:
        w, e, s, n = self.west, self.east, self.south, self.north

        padding_n = padding if padding_n is None else padding_n
        padding_e = padding if padding_e is None else padding_e
        padding_w = padding if padding_w is None else padding_w
        padding_s = padding if padding_s is None else padding_s

        w = w - padding_w
        e = e + padding_e
        s = s - padding_s
        n = n + padding_n

        return ((w, s), (e, s), (e, n), (w, n))

    @property
    def rect(self) -> Tuple[Coordinate, Coordinate]:
        return self.get_rect()

    def __str__(self) -> str:
        """Return a string representation of the object."""
        return f"w: {self.west}\ne: {self.east}\ns: {self.south}\nn: {self.north}\n"


def _rotate_points(
    points: Coordinates,
    angle: float = 45.0,
    center: Coordinate = (
        0.0,
        0.0,
    ),
) -> ndarray:
    """Rotates points around a center point.

    accepts single points [1,2] or array-like[N][2], and will return in kind

    Args:
        points: rotate points around center point.
        angle: in degrees.
        center: x, y.
    """
    # First check for common, easy values of angle
    p_arr = np.asarray(points)
    if angle == 0:
        return p_arr

    c0 = np.asarray(center)
    displacement = p_arr - c0
    if angle == 180:
        return c0 - displacement

    if p_arr.ndim == 2:
        perpendicular = displacement[:, ::-1]
    elif p_arr.ndim == 1:
        perpendicular = displacement[::-1]

    # Fall back to trigonometry
    angle = angle * pi / 180
    ca = cos(angle)
    sa = sin(angle)
    sa = np.array((-sa, sa))
    return displacement * ca + perpendicular * sa + c0


reference_orphanage = layout.create_cell("reference_orphanage")


class ComponentReference(_GeometryHelper):
    """Pointer to a Component with x, y, rotation, mirror.

    Args:
        component: Component The referenced Component.
        columns: Number of columns in the array.
        rows: Number of rows in the array.
        spacing: Distances between adjacent columns and adjacent rows.

    """

    def __init__(
        self,
        component: "Component",
        columns: int = 1,
        rows: int = 1,
        origin: Coordinate = (0, 0),
        spacing: Coordinate = (100, 100),
        magnification: float = 1,
        rotation: float = 0,
        x_reflection: bool = False,
        parent=None,
    ) -> None:
        transformation = kdb.DCplxTrans(
            magnification,  # Magnification
            rotation,  # Rotation
            x_reflection,  # X-axis mirroring
            origin[0],  # X-displacement
            origin[1],  # Y-displacement
        )
        a = kdb.DVector(float(spacing[0]), 0)
        b = kdb.DVector(0, float(spacing[1]))
        kl_instance = kdb.DCellInstArray(
            component._cell.cell_index(),
            transformation,
            a,
            b,
            round(columns),
            round(rows),
        )
        self.parent = component
        self.owner = None

        # self._kl_instance = kdb.Instance(layout=layout)
        # self._kl_instance.layout = layout
        # self._kl_instance.cell_inst = kl_instance
        # self._kl_instance = None

        if parent:
            self._kl_instance = parent._cell.insert(kl_instance)
        else:
            self._kl_instance = reference_orphanage.insert(kl_instance)

        # The ports of a ComponentReference have their own unique id (uid),
        # since two ComponentReferences of the same parent Component can be
        # in different locations and thus do not represent the same port
        self._local_ports = {
            name: port._copy() for name, port in component.ports.items()
        }
        self._name = None
        self.rows = rows
        self.columns = columns
        self.spacing = spacing
        self.magnification = magnification

    @classmethod
    def __get_validators__(cls):
        """For pydantic."""
        yield cls.validate

    @classmethod
    def validate(cls, v):
        """Check with pydantic Label valid type."""
        return v

    def __del__(self):
        """We want to delete the ComponentReference (kdb.Instance) from the \
        KLayout database when it's deleted/garbage collected from Python."""
        if not self._kl_instance.destroyed():
            self._kl_instance._destroy()

    @property
    def kl_instance(self):
        if not self._kl_instance.is_valid():
            raise ReferenceError(
                f"The ComponentReference in Component {self.parent.name!r} (referencing Component {self.owner.name!r})"
                " is no longer valid, it has been removed or its owner cell has"
                " been flattened."
            )
        return self._kl_instance

    def _kl_transform(self, magnification, rotation, x_reflection, dx, dy):
        transformation = kdb.DCplxTrans(
            float(magnification),  # Magnification
            float(rotation),  # Rotation
            x_reflection,  # X-axis mirroring
            float(dx),  # X-displacement
            float(dy),  # Y-displacement
        )
        return transformation

    def _apply_kl_transform(self, transformation):
        self.kl_instance.transform(transformation)

    def get_polygons(self, by_spec=True, depth=None):
        from gdsfactory.component import Component

        temp_device = Component()
        # self.temp_device = temp_device
        transformation = self.kl_instance.dcplx_trans
        temp_device._cell.insert(
            kdb.DCellInstArray(self.parent._cell.cell_index(), transformation)
        )
        polygons = temp_device.get_polygons(by_spec=by_spec, depth=depth)
        temp_device._cell.delete()  # Use this instead of _destroy()!
        return polygons

    def rotate(self, angle=45, center=(0, 0)):
        if angle == 0:
            return self
        center = _parse_coordinate(center)
        klt = self._kl_transform(
            magnification=1, rotation=0, x_reflection=False, dx=center[0], dy=center[1]
        )
        klt *= self._kl_transform(
            magnification=1, rotation=angle, x_reflection=False, dx=0, dy=0
        )
        klt *= self._kl_transform(
            magnification=1,
            rotation=0,
            x_reflection=False,
            dx=-center[0],
            dy=-center[1],
        )
        self._apply_kl_transform(klt)
        return self

    def move(self, origin=(0, 0), destination=None, axis=None):
        """Moves elements of the Component from the origin point to the destination.

        Both origin and destination can be 1x2 array-like, Port, or a key
        corresponding to one of the Ports in this component"""

        # If only one set of coordinates is defined, make sure it's used to move things
        if destination is None:
            destination = origin
            origin = [0, 0]

        if isinstance(origin, Port):
            o = origin.center
        elif np.array(origin).size == 2:
            o = origin
        elif origin in self.ports:
            o = self.ports[origin].center
        else:
            raise ValueError(
                "Component.move() ``origin`` not array-like, a port, or port name"
            )

        if isinstance(destination, Port):
            d = destination.center
        elif np.array(destination).size == 2:
            d = destination
        elif destination in self.ports:
            d = self.ports[destination].center
        else:
            raise ValueError(
                "Component.move() ``destination`` not array-like, a port, or port name"
            )

        if axis == "x":
            d = (d[0], o[1])
        if axis == "y":
            d = (o[0], d[1])

        dx, dy = np.array(d) - o

        # Move geometries
        klt = self._kl_transform(
            magnification=1, rotation=0, x_reflection=False, dx=dx, dy=dy
        )
        self._apply_kl_transform(klt)
        for p in self.ports.values():
            p.center = np.array(p.center) + np.array(d) - np.array(o)

        return self

    def mirror(self, p1=(0, 1), p2=(0, 0)):
        theta = np.arctan2(p2[1] - p1[1], p2[0] - p1[0]) / np.pi * 180
        # Last transformation applied first
        klt = self._kl_transform(
            magnification=1, rotation=0, x_reflection=False, dx=p1[0], dy=p1[1]
        )
        klt *= self._kl_transform(
            magnification=1, rotation=theta, x_reflection=False, dx=0, dy=0
        )
        klt *= self._kl_transform(
            magnification=1, rotation=0, x_reflection=True, dx=0, dy=0
        )
        klt *= self._kl_transform(
            magnification=1, rotation=-theta, x_reflection=False, dx=0, dy=0
        )
        klt *= self._kl_transform(
            magnification=1, rotation=0, x_reflection=False, dx=-p1[0], dy=-p1[1]
        )
        self._apply_kl_transform(klt)

        return self

    def __repr__(self):
        return (
            'Component (parent Component "%s", ports %s, origin %s, rotation %s, x_reflection %s)'
            % (
                self.parent.name,
                list(self.ports.keys()),
                self.origin,
                self.rotation,
                self.x_reflection,
            )
        )

    def __str__(self):
        return self.__repr__()

    def __getitem__(self, val):
        print(val)
        return self

    @property
    def ports(self):
        """This property allows you to access myref.ports, and receive a copy
        of the ports dict which is correctly rotated and translated"""
        for name, port in self.parent.ports.items():
            port = self.parent.ports[name]
            new_center, new_orientation = self._transform_port(
                port.center,
                port.orientation,
                self.origin,
                self.rotation,
                self.x_reflection,
            )
            if name not in self._local_ports:
                self._local_ports[name] = port._copy(new_uid=True)
            self._local_ports[name].center = new_center
            self._local_ports[name].orientation = mod(new_orientation, 360)
            self._local_ports[name].parent = self
        # Remove any ports that no longer exist in the reference's parent
        parent_names = self.parent.ports.keys()
        local_names = list(self._local_ports.keys())
        for name in local_names:
            if name not in parent_names:
                self._local_ports.pop(name)
        return self._local_ports

    @property
    def info(self):
        return self.parent.info

    @property
    def bbox(self):
        b = self.kl_instance.dbbox()
        bbox = np.array(((b.left, b.bottom), (b.right, b.top)))
        return bbox

    @property
    def origin(self):
        kl_transform = self.kl_instance.dcplx_trans
        return (kl_transform.disp.x, kl_transform.disp.y)

    @property
    def rotation(self):
        kl_transform = self.kl_instance.dcplx_trans
        return kl_transform.angle

    @property
    def x_reflection(self):
        kl_transform = self.kl_instance.dcplx_trans
        return kl_transform.is_mirror()

    def _transform_port(
        self, point, orientation, origin=(0, 0), rotation=None, x_reflection=False
    ):
        # Apply GDS-type transformations to a port (x_ref)
        new_point = np.array(
            point
        )  # Make a new copy of point so we don't modify the old
        new_orientation = orientation

        if x_reflection:
            new_point[1] = -new_point[1]
            new_orientation = -orientation
        if rotation is not None:
            new_point = _rotate_points(new_point, angle=rotation, center=[0, 0])
            new_orientation += rotation
        if origin is not None:
            new_point = new_point + np.array(origin)
        new_orientation = mod(new_orientation, 360)

        return new_point, new_orientation

    def connect(self, port, destination, overlap=0):
        # ``port`` can either be a string with the name or an actual Port
        if port in self.ports:  # Then ``port`` is a key for the ports dict
            p = self.ports[port]
        elif type(port) is Port:
            p = port
        else:
            raise ValueError(
                "connect() did not receive a Port or valid port name"
                + " - received (%s), ports available are (%s)"
                % (port, tuple(self.ports.keys()))
            )
        self.rotate(
            angle=180 + destination.orientation - p.orientation, center=p.center
        )
        self.move(origin=p, destination=destination)
        self.move(
            -overlap
            * np.array(
                [
                    cos(destination.orientation * pi / 180),
                    sin(destination.orientation * pi / 180),
                ]
            )
        )
        return self

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value: str):
        if value != self._name:
            if self.owner and value in self.owner.named_references:
                raise ValueError(
                    f"This reference's owner already has a reference with name {value!r}. Please choose another name."
                )
            self._name = value
            self.owner._reference_names_used.add(value)

    @property
    def size_info(self) -> SizeInfo:
        return SizeInfo(self.bbox)

    def get_ports_list(self, **kwargs) -> List[Port]:
        """Return a list of ports.

        Keyword Args:
            layer: port GDS layer.
            prefix: port name prefix.
            orientation: in degrees.
            width: port width.
            layers_excluded: List of layers to exclude.
            port_type: optical, electrical, ...
            clockwise: if True, sort ports clockwise, False: counter-clockwise.
        """
        return list(select_ports(self.ports, **kwargs).values())

    def get_ports_dict(self, **kwargs) -> Dict[str, Port]:
        """Return a dict of ports.

        Keyword Args:
            layer: port GDS layer.
            prefix: port name prefix.
            orientation: in degrees.
            width: port width.
            layers_excluded: List of layers to exclude.
            port_type: optical, electrical, ...
            clockwise: if True, sort ports clockwise, False: counter-clockwise.
        """
        return select_ports(self.ports, **kwargs)


class CellArray(ComponentReference):
    def __init__(
        self,
        component,
        parent,
        columns,
        rows,
        spacing,
        origin=(0, 0),
        rotation=0,
        magnification=None,
        x_reflection=False,
    ):
        if magnification is None:
            magnification = 1
        transformation = kdb.DCplxTrans(
            magnification,  # Magnification
            rotation,  # Rotation
            x_reflection,  # X-axis mirroring
            origin[0],  # X-displacement
            origin[1],  # Y-displacement
        )
        kl_instance = kdb.DCellInstArray(
            component._cell.cell_index(),
            transformation,
            spacing[0],  # a:  The displacement vector of the array in the 'a' axis
            spacing[1],  # b:  The displacement vector of the array in the 'b' axis
            columns[0],  # na: The number of placements in the 'a' axis
            rows[0],  # nb: The number of placements in the 'b' axis
        )
        self.kl_instance = parent._cell.insert(kl_instance)
        self._name = None

    # def __init__(
    #     self,
    #     component: "Component",
    #     origin: Coordinate = (0, 0),
    #     rotation: float = 0,
    #     magnification: float = 1,
    #     x_reflection: bool = False,
    #     visual_label: str = "",
    #     columns: int = 1,
    #     rows: int = 1,
    #     spacing=None,
    # ) -> None:
    #     """Initialize the ComponentReference object."""
    #     self._reference = gdstk.Reference(
    #         cell=component._cell,
    #         origin=origin,
    #         rotation=np.deg2rad(rotation),
    #         magnification=magnification,
    #         x_reflection=x_reflection,
    #         columns=columns,
    #         rows=rows,
    #         spacing=spacing,
    #     )

    #     self.ref_cell = component
    #     self._owner = None
    #     self._name = None

    #     self.rows = rows
    #     self.columns = columns
    #     self.spacing = spacing

    #     # The ports of a ComponentReference have their own unique id (uid),
    #     # since two ComponentReferences of the same parent Component can be
    #     # in different locations and thus do not represent the same port
    #     self._local_ports = {
    #         name: port._copy() for name, port in component.ports.items()
    #     }
    #     self.visual_label = visual_label
    #     # self.uid = str(uuid.uuid4())[:8]

    # @property
    # def parent(self):
    #     return self.ref_cell

    # @property
    # def origin(self):
    #     return self._reference.origin

    # @origin.setter
    # def origin(self, value):
    #     self._reference.origin = value

    # @property
    # def magnification(self):
    #     return self._reference.magnification

    # @magnification.setter
    # def magnification(self, value):
    #     self._reference.magnification = value

    # @property
    # def rotation(self) -> float:
    #     return np.rad2deg(self._reference.rotation)

    # @rotation.setter
    # def rotation(self, value):
    #     self._reference.rotation = np.deg2rad(value)

    # @property
    # def x_reflection(self):
    #     return self._reference.x_reflection

    # @x_reflection.setter
    # def x_reflection(self, value):
    #     self._reference.x_reflection = value

    # @parent.setter
    # def parent(self, value):
    #     self.ref_cell = value

    # def get_polygons(self, by_spec=False, depth=None):
    #     """Return the list of polygons created by this reference.

    #     Args:
    #         by_spec : bool or tuple
    #             If True, the return value is a dictionary with the
    #             polygons of each individual pair (layer, datatype).
    #             If set to a tuple of (layer, datatype), only polygons
    #             with that specification are returned.
    #         depth : integer or None
    #             If not None, defines from how many reference levels to
    #             retrieve polygons.  References below this level will result
    #             in a bounding box.  If `by_spec` is True the key will be the
    #             name of the referenced cell.

    #     Returns
    #         out : list of array-like[N][2] or dictionary
    #             List containing the coordinates of the vertices of each
    #             polygon, or dictionary with the list of polygons (if
    #             `by_spec` is True).

    #     Note:
    #         Instances of `FlexPath` and `RobustPath` are also included in
    #         the result by computing their polygonal boundary.
    #     """
    #     if not by_spec:
    #         return self._reference.get_polygons(depth=depth)
    #     elif by_spec is True:
    #         layers = self.parent.get_layers()
    #         return {
    #             layer: self._reference.get_polygons(
    #                 depth=depth, layer=layer[0], datatype=layer[1]
    #             )
    #             for layer in layers
    #         }

    #     else:
    #         return self._reference.get_polygons(
    #             depth=depth, layer=by_spec[0], datatype=by_spec[1]
    #         )

    # def get_labels(self, depth=None, set_transform=False):
    #     """Return the list of labels created by this reference.

    #     Args:
    #         depth : integer or None
    #             If not None, defines from how many reference levels to
    #             retrieve labels from.
    #         set_transform : bool
    #             If True, labels will include the transformations from
    #             the reference.

    #     Returns:
    #         out : list of `Label`
    #             List containing the labels in this cell and its references.
    #     """
    #     return self._reference.get_labels(depth=depth, set_transform=set_transform)

    # def get_bounding_box(self):
    #     return self._reference.bounding_box()

    # def get_paths(self, depth=None):
    #     """Return the list of paths created by this reference.

    #     Args:
    #         depth : integer or None
    #             If not None, defines from how many reference levels to
    #             retrieve paths from.

    #     Returns:
    #         list of `FlexPath` or `RobustPath`
    #             List containing the paths in this cell and its references.
    #     """
    #     return self._reference.get_paths(depth=depth)

    # def translate(self, dx, dy):
    #     return self._reference.translate(dx, dy)

    # def area(self, by_spec=False):
    #     """Calculate total area.

    #     Args:
    #         by_spec : bool
    #             If True, the return value is a dictionary with the areas
    #             of each individual pair (layer, datatype).

    #     Returns:
    #         out : number, dictionary
    #             Area of this cell.
    #     """
    #     return self._reference.area(by_spec=by_spec)

    # @property
    # def owner(self):
    #     return self._owner

    # @owner.setter
    # def owner(self, value):
    #     if self.owner is None or value is None:
    #         self._owner = value
    #     elif value != self._owner:
    #         raise ValueError(
    #             f"Cannot reset owner of a reference once it has already been set!"
    #             f" Reference: {self}. Current owner: {self._owner}. "
    #             f"Attempting to re-assign to {value!r}"
    #         )

    # @property
    # def alias(self):
    #     warnings.warn(
    #         "alias attribute is deprecated and may be removed in a future version of gdsfactory",
    #         DeprecationWarning,
    #     )
    #     return self.name

    # def __repr__(self) -> str:
    #     """Return a string representation of the object."""
    #     return (
    #         'ComponentReference (parent Component "%s", ports %s, origin %s, rotation %s,'
    #         " x_reflection %s)"
    #         % (
    #             self.parent.name,
    #             list(self.ports.keys()),
    #             self.origin,
    #             self.rotation,
    #             self.x_reflection,
    #         )
    #     )

    # def to_dict(self):
    #     d = self.parent.to_dict()
    #     d.update(
    #         origin=self.origin,
    #         rotation=self.rotation,
    #         magnification=self.magnification,
    #         x_reflection=self.x_reflection,
    #     )
    #     return d

    # @property
    # def bbox(self):
    #     """Return the bounding box of the ComponentReference.

    #     it snaps to 3 decimals in um (0.001um = 1nm precision)
    #     """
    #     bbox = self.get_bounding_box()
    #     if bbox is None:
    #         bbox = ((0, 0), (0, 0))
    #     return np.round(bbox, 3)

    # @classmethod
    # def __get_validators__(cls):
    #     """Get validators."""
    #     yield cls.validate

    # @classmethod
    # def validate(cls, v):
    #     """Check with pydantic ComponentReference valid type."""
    #     assert isinstance(
    #         v, ComponentReference
    #     ), f"TypeError, Got {type(v)}, expecting ComponentReference"
    #     return v

    # def __getitem__(self, key):
    #     """Access reference ports."""
    #     if key not in self.ports:
    #         ports = list(self.ports.keys())
    #         raise ValueError(f"{key!r} not in {ports}")

    #     return self.ports[key]

    # @property
    # def ports(self) -> Dict[str, Port]:
    #     """This property allows you to access myref.ports, and receive a copy.

    #     of the ports dict which is correctly rotated and translated.
    #     """
    #     for name, port in self.parent.ports.items():
    #         port = self.parent.ports[name]
    #         new_center, new_orientation = self._transform_port(
    #             port.center,
    #             port.orientation,
    #             self.origin,
    #             self.rotation,
    #             self.x_reflection,
    #         )
    #         if name not in self._local_ports:
    #             self._local_ports[name] = port.copy(new_uid=True)
    #         self._local_ports[name].center = new_center
    #         self._local_ports[name].orientation = (
    #             mod(new_orientation, 360) if new_orientation else new_orientation
    #         )
    #         self._local_ports[name].parent = self
    #     # Remove any ports that no longer exist in the reference's parent
    #     parent_names = self.parent.ports.keys()
    #     local_names = list(self._local_ports.keys())
    #     for name in local_names:
    #         if name not in parent_names:
    #             self._local_ports.pop(name)
    #     return self._local_ports

    # @property
    # def info(self) -> Dict[str, Any]:
    #     return self.parent.info

    # @property
    # def metadata_child(self) -> Dict[str, Any]:
    #     return self.parent.metadata_child

    # def pprint_ports(self) -> None:
    #     """Pretty print component ports."""
    #     ports_list = self.get_ports_list()
    #     for port in ports_list:
    #         print(port)

    # def _transform_port(
    #     self,
    #     point: ndarray,
    #     orientation: float,
    #     origin: Coordinate = (0, 0),
    #     rotation: Optional[int] = None,
    #     x_reflection: bool = False,
    # ) -> Tuple[ndarray, float]:
    #     """Apply GDS-type transformation to a port (x_ref)."""
    #     new_point = np.array(point)
    #     new_orientation = orientation

    #     if orientation is None:
    #         if origin is not None:
    #             new_point = new_point + np.array(origin)
    #         if x_reflection:
    #             new_point[1] = -new_point[1]
    #         return new_point, new_orientation

    #     if x_reflection:
    #         new_point[1] = -new_point[1]
    #         new_orientation = -orientation
    #     if rotation is not None:
    #         new_point = _rotate_points(new_point, angle=rotation, center=[0, 0])
    #         new_orientation += rotation
    #     if origin is not None:
    #         new_point = new_point + np.array(origin)
    #     new_orientation = mod(new_orientation, 360)

    #     return new_point, new_orientation

    # def _transform_point(
    #     self,
    #     point: ndarray,
    #     origin: Coordinate = (0, 0),
    #     rotation: Optional[int] = None,
    #     x_reflection: bool = False,
    # ) -> ndarray:
    #     """Apply GDS-type transformation to a point."""
    #     new_point = np.array(point)

    #     if x_reflection:
    #         new_point[1] = -new_point[1]
    #     if rotation is not None:
    #         new_point = _rotate_points(new_point, angle=rotation, center=[0, 0])
    #     if origin is not None:
    #         new_point = new_point + np.array(origin)

    #     return new_point

    # def move(
    #     self,
    #     origin: Union[Port, Coordinate, str] = (0, 0),
    #     destination: Optional[Union[Port, Coordinate, str]] = None,
    #     axis: Optional[str] = None,
    # ) -> "ComponentReference":
    #     """Move the ComponentReference from the origin point to the.

    #     destination.

    #     Both origin and destination can be 1x2 array-like, Port, or a key
    #     corresponding to one of the Ports in this device_ref.

    #     Args:
    #         origin: Port, port_name or Coordinate.
    #         destination: Port, port_name or Coordinate.
    #         axis: for the movemenent.

    #     Returns:
    #         ComponentReference.
    #     """
    #     # If only one set of coordinates is defined, make sure it's used to move things
    #     if destination is None:
    #         destination = origin
    #         origin = (0, 0)

    #     if isinstance(origin, str):
    #         if origin not in self.ports:
    #             raise ValueError(f"{origin} not in {self.ports.keys()}")

    #         origin = self.ports[origin]
    #         origin = cast(Port, origin)
    #         o = origin.center
    #     elif hasattr(origin, "center"):
    #         origin = cast(Port, origin)
    #         o = origin.center
    #     elif np.array(origin).size == 2:
    #         o = origin
    #     else:
    #         raise ValueError(
    #             f"move(origin={origin})\n"
    #             f"Invalid origin = {origin!r} needs to be"
    #             f"a coordinate, port or port name {list(self.ports.keys())}"
    #         )

    #     if isinstance(destination, str):
    #         if destination not in self.ports:
    #             raise ValueError(f"{destination} not in {self.ports.keys()}")

    #         destination = self.ports[destination]
    #         destination = cast(Port, destination)
    #         d = destination.center
    #     if hasattr(destination, "center"):
    #         destination = cast(Port, destination)
    #         d = destination.center
    #     elif np.array(destination).size == 2:
    #         d = destination

    #     else:
    #         raise ValueError(
    #             f"{self.parent.name}.move(destination={destination}) \n"
    #             f"Invalid destination = {destination!r} needs to be"
    #             f"a coordinate, a port, or a valid port name {list(self.ports.keys())}"
    #         )

    #     # Lock one axis if necessary
    #     if axis == "x":
    #         d = (d[0], o[1])
    #     if axis == "y":
    #         d = (o[0], d[1])

    #     # This needs to be done in two steps otherwise floating point errors can accrue
    #     dxdy = np.array(d) - np.array(o)
    #     self.origin = np.array(self.origin) + dxdy
    #     self._bb_valid = False
    #     return self

    # def rotate(
    #     self,
    #     angle: float = 45,
    #     center: Union[Coordinate, str, int] = (0.0, 0.0),
    # ) -> "ComponentReference":
    #     """Return rotated ComponentReference.

    #     Args:
    #         angle: in degrees.
    #         center: x, y.
    #     """
    #     if angle == 0:
    #         return self
    #     if isinstance(center, (int, str)):
    #         center = self.ports[center].center

    #     if isinstance(center, Port):
    #         center = center.center
    #     self.rotation += angle
    #     self.rotation %= 360
    #     self.origin = _rotate_points(self.origin, angle, center)
    #     self._bb_valid = False
    #     return self

    # def reflect_h(
    #     self, port_name: Optional[str] = None, x0: Optional[Coordinate] = None
    # ) -> "ComponentReference":
    #     """Perform horizontal mirror using x0 or port as axis (default, x0=0).

    #     This is the default for mirror along X=x0 axis
    #     """
    #     if port_name is None and x0 is None:
    #         x0 = -self.x

    #     if port_name is not None:
    #         position = self.ports[port_name]
    #         x0 = position.x
    #     self.reflect((x0, 1), (x0, 0))
    #     return self

    # def reflect_v(
    #     self, port_name: Optional[str] = None, y0: Optional[float] = None
    # ) -> "ComponentReference":
    #     """Perform vertical mirror using y0 as axis (default, y0=0)."""
    #     if port_name is None and y0 is None:
    #         y0 = 0.0

    #     if port_name is not None:
    #         position = self.ports[port_name]
    #         y0 = position.y
    #     self.reflect((1, y0), (0, y0))
    #     return self

    # def mirror(
    #     self,
    #     p1: Coordinate = (0.0, 1.0),
    #     p2: Coordinate = (0.0, 0.0),
    # ) -> "ComponentReference":
    #     """Mirrors.

    #     Args:
    #         p1: point 1.
    #         p2: point 2.
    #     """
    #     if isinstance(p1, Port):
    #         p1 = p1.center
    #     if isinstance(p2, Port):
    #         p2 = p2.center
    #     p1 = np.array(p1)
    #     p2 = np.array(p2)
    #     # Translate so reflection axis passes through origin
    #     self.origin = self.origin - p1

    #     # Rotate so reflection axis aligns with x-axis
    #     angle = np.arctan2((p2[1] - p1[1]), (p2[0] - p1[0])) * 180 / pi
    #     self.origin = _rotate_points(self.origin, angle=-angle, center=(0, 0))
    #     self.rotation -= angle

    #     # Reflect across x-axis
    #     self.x_reflection = not self.x_reflection
    #     self.origin = (self.origin[0], -1 * self.origin[1])

    #     self.rotation = -1 * self.rotation

    #     # Un-rotate and un-translate
    #     self.origin = _rotate_points(self.origin, angle=angle, center=(0, 0))
    #     self.rotation += angle
    #     self.rotation = self.rotation % 360
    #     self.origin = self.origin + p1

    #     self._bb_valid = False
    #     return self

    # def reflect(self, *args, **kwargs):
    #     warnings.warn(
    #         "reflect is deprecated and may be removed in a future version of gdsfactory. Use mirror instead.",
    #         DeprecationWarning,
    #     )
    #     return self.mirror(*args, **kwargs)

    # def connect(
    #     self,
    #     port: Union[str, Port],
    #     destination: Port,
    #     overlap: float = 0.0,
    # ) -> "ComponentReference":
    #     """Return ComponentReference where port connects to a destination.

    #     Args:
    #         port: origin (port, or port name) to connect.
    #         destination: destination port.
    #         overlap: how deep does the port go inside.

    #     Returns:
    #         ComponentReference: with correct rotation to connect to destination.
    #     """
    #     # port can either be a string with the name, port index, or an actual Port
    #     if port in self.ports:
    #         p = self.ports[port]
    #     elif isinstance(port, Port):
    #         p = port
    #     else:
    #         ports = list(self.ports.keys())
    #         raise ValueError(
    #             f"port = {port!r} not in {self.parent.name!r} ports {ports}"
    #         )

    #     angle = 180 + destination.orientation - p.orientation
    #     angle = angle % 360

    #     self.rotate(angle=angle, center=p.center)

    #     self.move(origin=p, destination=destination)
    #     self.move(
    #         -overlap
    #         * np.array(
    #             [
    #                 cos(destination.orientation * pi / 180),
    #                 sin(destination.orientation * pi / 180),
    #             ]
    #         )
    #     )

    #     return self

    # @property
    # def ports_layer(self) -> Dict[str, str]:
    #     """Return a mapping from layer0_layer1_E0: portName."""
    #     return map_ports_layer_to_orientation(self.ports)

    # def port_by_orientation_cw(self, key: str, **kwargs):
    #     """Return port by indexing them clockwise."""
    #     m = map_ports_to_orientation_cw(self.ports, **kwargs)
    #     if key not in m:
    #         raise KeyError(f"{key} not in {list(m.keys())}")
    #     key2 = m[key]
    #     return self.ports[key2]

    # def port_by_orientation_ccw(self, key: str, **kwargs):
    #     """Return port by indexing them clockwise."""
    #     m = map_ports_to_orientation_ccw(self.ports, **kwargs)
    #     if key not in m:
    #         raise KeyError(f"{key} not in {list(m.keys())}")
    #     key2 = m[key]
    #     return self.ports[key2]

    # def snap_ports_to_grid(self, nm: int = 1) -> None:
    #     for port in self.ports.values():
    #         port.snap_to_grid(nm=nm)

    # def get_ports_xsize(self, **kwargs) -> float:
    #     """Return xdistance from east to west ports.

    #     Keyword Args:
    #         kwargs: orientation, port_type, layer.
    #     """
    #     ports_cw = self.get_ports_list(clockwise=True, **kwargs)
    #     ports_ccw = self.get_ports_list(clockwise=False, **kwargs)
    #     return snap_to_grid(ports_ccw[0].x - ports_cw[0].x)

    # def get_ports_ysize(self, **kwargs) -> float:
    #     """Returns ydistance from east to west ports."""
    #     ports_cw = self.get_ports_list(clockwise=True, **kwargs)
    #     ports_ccw = self.get_ports_list(clockwise=False, **kwargs)
    #     return snap_to_grid(ports_ccw[0].y - ports_cw[0].y)


def test_move():
    import gdsfactory as gf

    c = gf.Component()
    mzi = c.add_ref(gf.components.mzi())
    bend = c.add_ref(gf.components.bend_euler())
    bend.move("o1", mzi.ports["o2"])


if __name__ == "__main__":
    import gdsfactory as gf

    # c = gf.Component("parent")
    # c2 = gf.Component("child")
    # length = 10
    # width = 0.5
    # layer = (1, 0)
    # c2.add_polygon([(0, 0), (length, 0), (length, width), (0, width)], layer=layer)
    # c << c2

    c = gf.c.dbr()
    c.show()

    # import gdsfactory as gf

    # c = gf.Component()
    # mzi = c.add_ref(gf.components.mzi())
    # bend = c.add_ref(gf.components.bend_euler())
    # bend.move("o1", mzi.ports["o2"])
    # bend.move("o1", "o2")
    # c.show()
