#!/usr/bin/env python3
#
#  Copyright (C) 2016 Codethink Limited
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 2 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.	 See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library. If not, see <http://www.gnu.org/licenses/>.
#
#  Authors:
#        Tristan Van Berkom <tristan.vanberkom@codethink.co.uk>

# Plugin auther facing APIs
from .sandbox import Sandbox, SandboxFlags
from .plugin import Plugin
from .source import Source, SourceError, Consistency
from .element import Element, ElementError, Scope
from .buildelement import BuildElement
from .scriptelement import ScriptElement

try:
    from .version import VERSION
except ImportError:
    VERSION = '0.0.0 (uninstalled)'
