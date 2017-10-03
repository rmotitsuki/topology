"""Most relevant classes to be used on the topology."""
from enum import Enum, IntEnum, unique

from napps.kytos.topology.exceptions import (DeviceException, DeviceNotFound,
                                             InterfaceConnected,
                                             InterfaceDisconnected,
                                             InterfaceException, PortNotFound,
                                             TopologyException)

__all__ = ('Device', 'DeviceType', 'Interface', 'Port', 'PortState',
           'Topology')


@unique
class DeviceType(Enum):
    """Device types."""

    SWITCH = 0
    HOST = 1


@unique
class PortState(IntEnum):
    """Port states."""

    DOWN = 0
    UP = 1  # pylint: disable=invalid-name


class Port:
    """Represent a port from a Device.

    Each device can hold one or more ports.

    """

    def __init__(self, number=None, mac=None, properties=None, state=None):
        """Init the port."""
        #: Port number
        self.number = number
        #: Port mac address
        self.mac = mac
        #: Dict with port properties , such as speed, bandwith, etc.
        self.properties = properties or {}
        #: Port state, one of PortState enum values.
        self._state = state or PortState.UP

    @property
    def id_(self):
        """Port ID is based on its MACAddress.

        The ID will be the MAC Address without ':' and no left zeroes.

        Returns:
            Port ID (string).

        """
        return self.number or ''.join(self.mac.split(':')).lstrip('0')

    @property
    def state(self):
        """State property, accepts one of PortState values."""
        return self._state

    @state.setter
    def state(self, value):
        """Set state checking if it is an instance of PortState enum."""
        if isinstance(value, PortState):
            self._state = value
        elif isinstance(value, int):
            self._state = PortState(value)
        else:
            self._state = PortState[value]


class Device:
    """Class that represent a 'NODE' in the topology graph.

    A Device can be one of the 'DeviceType' values from DeviceType enum.

    Each device will hold one or more ports.

    A port is how Devices connects between themselves and also each
    port can be connected to only one other device/port.

    """

    def __init__(self, device_id, dtype=DeviceType.SWITCH, ports=None):
        """Instantiate a device."""
        #: Switch or host ID
        self.device_id = device_id
        #: DeviceType
        self._dtype = dtype
        #: Dict <port_id_>: <port>
        self.ports = {}
        if ports:
            self.ports.update(ports)

    @property
    def id_(self):
        """Return the device_id as the device id."""
        return self.device_id

    @property
    def dtype(self):
        """Return the device type."""
        return self._dtype

    @dtype.setter
    def dtype(self, dtype):
        """Set the device type checking if it is a DeviceType.

        Args:
            dtype (:class:`DeviceType`): One of the existent devices type.

        Raises:
            KeyError if there is no such device type on DeviceType.

        """
        if isinstance(dtype, DeviceType):
            self._dtype = dtype
        elif isinstance(dtype, int):
            self._dtype = DeviceType(dtype)
        else:
            self._dtype = DeviceType[dtype]

    def add_port(self, port):
        """Add a port to the device.

        Args:
            port (:class:`Port`): An instance of Port.

        Raises:
            DeviceException if port is not an instance of Port or if the given
                port was already added to the device.

        """
        if not isinstance(port, Port):
            raise DeviceException('Port must be an instance of Port.')

        if self.has_port(port):
            msg = f'Port {port.id_} already added to the device {self.id_}'
            raise DeviceException(msg)

        self.ports[port.id_] = port

    def has_port(self, port):
        """Check if the device have the given port.

        Args:
            port (int, str, Port): May be either an instance of Port or an int
                or a string. Both int and str would be the id of the port.

        Returns:
            True if the port was found on the device.
            False otherwise.

        """
        try:
            self.get_port(port)
            return True
        except PortNotFound:
            return False

    def get_port(self, port):
        """Get a Port from the current device.

        Args:
            port (int, str, Port): May be either an instance of Port or an int
                or a string. Both int and str would be the id of the port.

        Returns:
            The registered port instance from the Device if it was found by
                its id.
            None if the por was not found.

        """
        try:
            if isinstance(port, Port):
                return self.ports[port.id_]
            # Assuming that port is the id of a port.
            return self.ports[port]
        except KeyError:
            return None


class Interface:
    """Represent an interface on the topology.

    This is the element that can be 'linked' to another on the topology. It is
    composed by a device and a port.

    """

    def __init__(self, device, port):
        """Init the Interface instance."""
        #: instance of Device
        self.device = device
        #: Instance of Port
        self.port = port
        #: Is this an NNI port
        self._nni = False
        #: Is this a UNI port
        self._uni = False
        #: Is this port connected to any other port? True or False
        self._connected = False

    @property
    def id_(self):
        """Return the id of the interface.

        This id is the composition between device id and port id.

        """
        return f'{self.device.id_}:{self.port.id_}'

    def is_connected(self):
        """Check if the device is flagged as connected.

        Returns:
            True if the switch is flagged as connected.
            False if not.

        """
        return self._connected is True

    def connect(self):
        """Flag the switch as connected."""
        self._connected = True

    def disconnect(self):
        """Flag the switch as disconnected.

        It also update the _nni and _uni attributes to False, since we cannot
        have an UNI or a NNI on a disconnected interface.

        """
        self._nni = False
        self._uni = False
        self._connected = False

    def is_nni(self):
        """Is this port a NNI.

        If the port is not connected, then we return False.

        Returns:
            True if it is connected and is flagged as a NNI .
            False if not.

        """
        return self.is_connected() and self._nni

    def is_uni(self):
        """Is this port a UNI.

        If the port is not connected, then we return False.

        Returns:
            True if it is connected and is flagged as an UNI .
            False if not.

        """
        return self.is_connected() and self._uni

    def set_as_nni(self):
        """Set the current port as a NNI port if it is connected."""
        if not self.is_connected():
            msg = 'Disconnected ports cannot be set as NNI.'
            raise InterfaceDisconnected(self.id_, msg)
        self._nni = True
        self._uni = False

    def set_as_uni(self):
        """Set the current port as a UNI port if it is connected.

        Also check if it is not a NNI interface because NNI overcomes UNI.

        """
        if not self.is_connected():
            msg = 'Disconnected ports cannot be set as UNI.'
            raise InterfaceDisconnected(self.id_, msg)

        if self.is_nni():
            raise InterfaceException(self.id_,
                                     'Cannot set a NNI interface as UNI.')
        self._uni = True
        self._nni = False


class Link:
    """Represents a link between two devices/ports."""

    def __init__(self, interface_one, interface_two, properties=None):
        """Create a Link.

        Args:
            interface_one (Interface): holds Device and Port instances.
            interface_two (Interface): holds Device and Port instances.

        """
        msg = ''
        if interface_one.is_connected():
            msg += f'Interface {interface_one.id_} is already connected; '
        if interface_two.is_connected():
            msg += f'Interface {interface_two.id_} is already connected; '

        if msg:
            msg += 'You must disconnect the interfaces before (re)connecting.'
            raise InterfaceConnected(msg)

        self.interface_one = interface_one
        self.interface_two = interface_two
        self.properties = properties

        self.interface_one.connect()
        self.interface_two.connect()

    @property
    def id_(self):
        """Return the Link ID.

        It is a composition between both interfaces ids joined by a dash.

        """
        return f'{self.interface_one.id_}-{self.interface_two.id_}'

    def unlink(self):
        """Unlink the interfaces."""
        self.interface_one.disconnect()
        self.interface_two.disconnect()
        self.interface_one = None
        self.interface_two = None


class Topology:
    """Represents the network topology."""

    _links = {}
    _devices = {}

    def __init__(self):
        """Init a topology object."""
        self._links = {}
        self._devices = {}

    def _replace_by_objects(self, interface):
        """Replace interface device and port ids by objects.

        Args:
            interface (Interface): One Interface instance.

        Returns:
            The interface object with it's attributes (device and port)
            containing instances of Device and Port instead of its IDs.

        Raises:
            DeviceException if interface.device is not known by the topology.
            PortNotFound if the device does not have such Port.

        """
        device = self.get_device(interface.device)
        if device is None:
            raise DeviceNotFound(interface.device)

        port = device.get_port(interface.port)
        if port is None:
            raise PortNotFound(interface.port)

        return Interface(device, port)

    def _unset_link_for_interface(self, interface):
        """Unset the link for the given interface."""
        link = self.get_link(interface)
        if link:
            self.unset_link(link)

    def add_device(self, device):
        """Add a device to the topology known devices.

        Args:
            device (Device): One Device instance.

        """
        if not isinstance(device, Device):
            raise Exception('Device must be an instance of Device.')
        self._devices[device.id_] = device

    @property
    def devices(self):
        """Return all current devices."""
        return self._devices

    @property
    def links(self):
        """Return all current links."""
        return self._links

    @staticmethod
    @devices.setter
    def devices(value):
        """Overriding devices attribute to avoid direct usage."""
        msg = f'To add or change devices use the proper methods. {value}'
        raise TopologyException(msg)

    @staticmethod
    @links.setter
    def links(value):
        """Overriding links attribute to avoid direct usage."""
        msg = f'To add or change links use the proper methods. {value}'
        raise TopologyException(msg)

    def get_device(self, device):
        """Get the device by the device id.

        Args:
            device (str, Device): Either the Device instance or its id.

        Returns:
            The device instance if it exists
            None else

        """
        try:
            if isinstance(device, Device):
                return self._devices[device.id_]
            return self._devices[device]
        except KeyError:
            return None

    def get_link(self, interface):
        """Return the link for the given interface if it exist else None."""
        i_id = interface.id_
        for link in self._links.values():
            if i_id in [link.interface_one.id_, link.interface_two.id_]:
                return link
        return None

    def set_link(self, interface_one, interface_two, properties=None,
                 force=False):
        """Set a new link on the topology."""
        interface_one = self._replace_by_objects(interface_one)
        interface_two = self._replace_by_objects(interface_two)

        if force:
            self._unset_link_for_interface(interface_one)
            self._unset_link_for_interface(interface_two)

        link = Link(interface_one, interface_two, properties)

        self._links[link.id_] = link

    def unset_link(self, link):
        """Unset a link."""
        interface_one = link.interface_one
        interface_two = link.interface_two
        interface_one.disconnect()
        interface_two.disconnect()
        del self._links[link.id_]