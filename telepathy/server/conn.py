# telepathy-spec - Base classes defining the interfaces of the Telepathy framework
#
# Copyright (C) 2005,2006 Collabora Limited
# Copyright (C) 2005,2006 Nokia Corporation
# Copyright (C) 2006 INdT
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Library General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

import dbus.service
import re
import weakref

from telepathy import *
from handle import Handle

from telepathy._generated.Connection import Connection as _Connection
from telepathy._generated.ConnectionInterfaceAliasing \
        import ConnectionInterfaceAliasing \
        as _ConnectionInterfaceAliasing
from telepathy._generated.ConnectionInterfaceAvatars \
        import ConnectionInterfaceAvatars
from telepathy._generated.ConnectionInterfaceCapabilities \
        import ConnectionInterfaceCapabilities \
        as _ConnectionInterfaceCapabilities
from telepathy._generated.ConnectionInterfaceContactInfo \
        import ConnectionInterfaceContactInfo
from telepathy._generated.ConnectionInterfaceForwarding \
        import ConnectionInterfaceForwarding \
        as _ConnectionInterfaceForwarding
from telepathy._generated.ConnectionInterfacePresence \
        import ConnectionInterfacePresence
from telepathy._generated.ConnectionInterfacePrivacy \
        import ConnectionInterfacePrivacy \
        as _ConnectionInterfacePrivacy
from telepathy._generated.ConnectionInterfaceRenaming \
        import ConnectionInterfaceRenaming

class Connection(_Connection, dbus.service.Object):
    def __init__(self, proto, account):
        """
        Parameters:
        proto - the name of the protcol this conection should be handling.
        account - a protocol-specific account name
        account - a unique identifier for this account which is used to identify this connection
        """
        clean_account = re.sub('[^a-zA-Z0-9_]', '_', account)
        bus_name = dbus.service.BusName('org.freedesktop.Telepathy.Connection.' + clean_account)
        object_path = '/org/freedesktop/Telepathy/Connection/' + clean_account
        dbus.service.Object.__init__(self, bus_name, object_path)

        # monitor clients dying so we can release handles
        self._bus.add_signal_receiver(self.name_owner_changed_callback,
                                      'NameOwnerChanged',
                                      'org.freedesktop.DBus',
                                      'org.freedesktop.DBus',
                                      '/org/freedesktop/DBus')

        self._proto = proto

        self._status = CONNECTION_STATUS_CONNECTING
        self._interfaces = set()

        self._handles = weakref.WeakValueDictionary()
        self._next_handle_id = 1
        self._client_handles = {}

        self._channels = set()
        self._next_channel_id = 0

    def check_parameters(self, parameters):
        """
        Uses the values of self._mandatory_parameters and
        self._optional_parameters to validate and type check all of the
        provided parameters, and check all mandatory parameters are present.
        Sets defaults according to the defaults if the client has not
        provided any.
        """
        for (parm, value) in parameters.iteritems():
            if parm in self._mandatory_parameters.keys():
                sig = self._mandatory_parameters[parm]
            elif parm in self._optional_parameters.keys():
                sig = self._optional_parameters[parm]
            else:
                raise InvalidArgument('unknown parameter name %s' % parm)

            if sig == 's':
                if not isinstance(value, unicode):
                    raise InvalidArgument('incorrect type to %s parameter, got %s, expected a string' % (parm, type(value)))
            elif sig == 'q':
                if not isinstance(value, int):
                    raise InvalidArgument('incorrect type to %s parameter, got %s, expected an int' % (parm, type(value)))
            elif sig == 'b':
                if not isinstance(value, bool):
                    raise InvalidArgument('incorrect type to %s parameter, got %s, expected an boolean' % (parm, type(value)))
            else:
                raise TypeError('unknown type signature %s in protocol parameters' % type)

        for (parm, value) in self._parameter_defaults.iteritems():
            if parm not in parameters:
                parameters[parm] = value

        missing = set(self._mandatory_parameters.keys()).difference(parameters.keys())
        if missing:
            raise InvalidArgument('required parameters %s not given' % missing)

    def check_connected(self):
        if self._status != CONNECTION_STATUS_CONNECTED:
            raise Disconnected('method cannot be called unless status is CONNECTION_STATUS_CONNECTED')

    def check_handle(self, handle_type, handle):
        if (handle_type, handle) not in self._handles:
            print "Connection.check_handle", handle, handle_type, self._handles.keys()
            print str(list( [ self._handles[x] for x in self._handles.keys() ] ) )
            raise InvalidHandle('handle number %s not valid' % handle)

    def check_handle_type(self, type):
        if (type < CONNECTION_HANDLE_TYPE_CONTACT or
            type > CONNECTION_HANDLE_TYPE_LIST):
            raise InvalidArgument('handle type %s not known' % type)

    def get_handle_id(self):
        id = self._next_handle_id
        self._next_handle_id += 1
        return id

    def add_client_handle(self, handle, sender):
        if sender in self._client_handles:
            self._client_handles[sender].add((handle.get_type(), handle))
        else:
            self._client_handles[sender] = set([(handle.get_type(), handle)])

    def name_owner_changed_callback(self, name, old_owner, new_owner):
        # when name and old_owner are the same, and new_owner is
        # blank, it is the client itself releasing its name... aka exiting
        if (name == old_owner and new_owner == "" and name in self._client_handles):
            print "deleting handles for", name
            del self._client_handles[name]

    def set_self_handle(self, handle):
        self._self_handle = handle

    def get_channel_path(self):
        ret = '%s/channel%d' % (self._object_path, self._next_channel_id)
        self._next_channel_id += 1
        return ret

    def add_channel(self, channel, handle, suppress_handler):
        """ add a new channel and signal its creation""" 
        self._channels.add(channel)
        self.NewChannel(channel._object_path, channel._type, handle.get_type(), handle.get_id(), suppress_handler)

    def remove_channel(self, channel):
        self._channels.remove(channel)

    @dbus.service.method(CONN_INTERFACE, in_signature='', out_signature='as')
    def GetInterfaces(self):
        self.check_connected()
        return self._interfaces

    @dbus.service.method(CONN_INTERFACE, in_signature='', out_signature='s')
    def GetProtocol(self):
        return self._proto

    @dbus.service.method(CONN_INTERFACE, in_signature='uau', out_signature='as')
    def InspectHandles(self, handle_type, handles):
        self.check_connected()
        self.check_handle_type(handle_type)

        for handle in handles:
            self.check_handle(handle_type, handle)

        ret = []
        for handle in handles:
            ret.append(self._handles[handle_type, handle].get_name())

        return ret

    @dbus.service.method(CONN_INTERFACE, in_signature='uas', out_signature='au', sender_keyword='sender')
    def RequestHandles(self, handle_type, names, sender):
        self.check_connected()
        self.check_handle_type(handle_type)

        ret = {}
        for name in names:
            id = self.get_handle_id()
            handle = Handle(id, handle_type, name)
            self._handles[handle_type, id] = handle
            self.add_client_handle(handle, sender)
            ret[name] = id

        return id

    @dbus.service.method(CONN_INTERFACE, in_signature='uau', out_signature='', sender_keyword='sender')
    def HoldHandles(self, handle_type, handles, sender):
        self.check_connected()
        self.check_handle_type(handle_type)

        for handle in handles:
            self.check_handle(handle_type, handle)

        for handle in handles:
            hand = self._handles[handle_type, handle]
            self.add_client_handle(hand, sender)

    @dbus.service.method(CONN_INTERFACE, in_signature='uau', out_signature='', sender_keyword='sender')
    def ReleaseHandles(self, handle_type, handles, sender):
        self.check_connected()
        self.check_handle_type(handle_type)

        for handle in handles:
            self.check_handle(handle_type, handle)
            hand = self._handles[handle_type, handle]
            if sender in self._client_handles:
                if hand not in self._client_handles[sender]:
                    raise NotAvailable('client is not holding handle %s' % handle)
            else:
                raise NotAvailable('client does not hold any handles')

        for handle in handles:
            hand = self._handles[handle_type, handle]
            self._client_handles[sender].remove(hand)

    @dbus.service.method(CONN_INTERFACE, in_signature='', out_signature='u')
    def GetSelfHandle(self):
        self.check_connected()
        return self._self_handle

    @dbus.service.signal(CONN_INTERFACE, signature='uu')
    def StatusChanged(self, status, reason):
        self._status = status

    @dbus.service.method(CONN_INTERFACE, in_signature='', out_signature='u')
    def GetStatus(self):
        return self._status

    @dbus.service.method(CONN_INTERFACE, in_signature='', out_signature='a(osuu)')
    def ListChannels(self):
        self.check_connected()
        ret = []
        for channel in self._channels:
            chan = (channel._object_path, channel._type, channel._handle.get_type(), channel._handle)
            ret.append(chan)
        return ret

    @dbus.service.method(CONN_INTERFACE, in_signature='suub', out_signature='o')
    def RequestChannel(self, type, handle_type, handle, suppress_handler):
        self.check_connected()
        raise NotImplemented('unknown channel type %s' % type)


class ConnectionInterfaceAliasing(_ConnectionInterfaceAliasing):

    @dbus.service.method(CONN_INTERFACE_ALIASING, in_signature='', out_signature='u')
    def GetAliasFlags(self):
        return 0

class ConnectionInterfaceCapabilities(_ConnectionInterfaceCapabilities):
    def __init__(self):
        """
        Initialise the capabilities interface.
        """
        _ConnectionInterfaceCapabilities.__init__(self)
        self._own_caps = set()
        self._caps = {}

    # FIXME: this code is completely broken!
    @dbus.service.method(CONN_INTERFACE_CAPABILITIES, in_signature='au', out_signature='a(usuu)')
    def GetCapabilities(self, handles):
        if (handle != 0 and handle not in self._handles):
            raise InvalidHandle
        elif handle in self._caps:
            return self._caps[handle]
        else:
            return []

    @dbus.service.signal(CONN_INTERFACE_CAPABILITIES, signature='a(usuuuu)')
    def CapabilitiesChanged(self, caps):
        if handle not in self._caps:
            self._caps[handle] = set()

        self._caps[handle].update(added)
        self._caps[handle].difference_update(removed)

    @dbus.service.method(CONN_INTERFACE_CAPABILITIES, in_signature='a(su)as', out_signature='a(su)')
    def AdvertiseCapabilities(self, add, remove):
        # no-op implementation
        self.AdvertisedCapabilitiesChanged(self._self_handle, add, remove)


class ConnectionInterfaceForwarding(_ConnectionInterfaceForwarding):
    def __init__(self):
        _ConnectionInterfaceForwarding.__init__(self)
        self._forwarding_handle = 0

    @dbus.service.method(CONN_INTERFACE_FORWARDING, in_signature='', out_signature='u')
    def GetForwardingHandle(self):
        return self._forwarding_handle

    @dbus.service.signal(CONN_INTERFACE_FORWARDING, signature='u')
    def ForwardingChanged(self, forward_to):
        self._forwarding_handle = forward_to


class ConnectionInterfacePrivacy(_ConnectionInterfacePrivacy):
    def __init__(self, modes):
        """
        Initialise privacy interface.

        Parameters:
        modes - a list of privacy modes available on this interface
        """
        _ConnectionInterfacePrivacy.__init__(self)
        self._privacy_mode = ''
        self._privacy_modes = modes

    @dbus.service.method(CONN_INTERFACE_PRIVACY, in_signature='', out_signature='as')
    def GetPrivacyModes(self):
        return self._privacy_modes

    @dbus.service.method(CONN_INTERFACE_PRIVACY, in_signature='', out_signature='s')
    def GetPrivacyMode(self):
        return self._privacy_mode

    @dbus.service.signal(CONN_INTERFACE_PRIVACY, signature='s')
    def PrivacyModeChanged(self, mode):
        self._privacy_mode = mode
