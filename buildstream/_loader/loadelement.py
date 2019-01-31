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

# System imports
from collections.abc import Mapping

# BuildStream toplevel imports
from .._exceptions import LoadError, LoadErrorReason
from .. import _yaml

# Local package imports
from .types import Symbol, Dependency


# LoadElement():
#
# A transient object breaking down what is loaded allowing us to
# do complex operations in multiple passes.
#
# Args:
#    node (dict): A YAML loaded dictionary
#    name (str): The element name
#    loader (Loader): The Loader object for this element
#
class LoadElement():

    def __init__(self, node, filename, loader):

        #
        # Public members
        #
        self.node = node       # The YAML node
        self.name = filename   # The element name
        self.full_name = None  # The element full name (with associated junction)
        self.deps = None       # The list of Dependency objects

        #
        # Private members
        #
        self._loader = loader   # The Loader object
        self._dep_cache = None  # The dependency cache, to speed up depends()

        #
        # Initialization
        #
        if loader.project.junction:
            # dependency is in subproject, qualify name
            self.full_name = '{}:{}'.format(loader.project.junction.name, self.name)
        else:
            # dependency is in top-level project
            self.full_name = self.name

        # Ensure the root node is valid
        _yaml.node_validate(self.node, [
            'kind', 'depends', 'sources', 'sandbox',
            'variables', 'environment', 'environment-nocache',
            'config', 'public', 'description',
            'build-depends', 'runtime-depends',
        ])

        # Extract the Dependencies
        self.deps = _extract_depends_from_node(self.node)

    # depends():
    #
    # Checks if this element depends on another element, directly
    # or indirectly.
    #
    # Args:
    #    other (LoadElement): Another LoadElement
    #
    # Returns:
    #    (bool): True if this LoadElement depends on 'other'
    #
    def depends(self, other):
        self._ensure_depends_cache()
        return self._dep_cache.get(other.full_name) is not None

    ###########################################
    #            Private Methods              #
    ###########################################
    def _ensure_depends_cache(self):

        if self._dep_cache:
            return

        self._dep_cache = {}
        for dep in self.deps:
            elt = self._loader.get_element_for_dep(dep)

            # Ensure the cache of the element we depend on
            elt._ensure_depends_cache()

            # We depend on this element
            self._dep_cache[elt.full_name] = True

            # And we depend on everything this element depends on
            self._dep_cache.update(elt._dep_cache)


# _extract_depends_from_node():
#
# Creates an array of Dependency objects from a given dict node 'node',
# allows both strings and dicts for expressing the dependency and
# throws a comprehensive LoadError in the case that the node is malformed.
#
# After extracting depends, the symbol is deleted from the node
#
# Args:
#    node (dict): A YAML loaded dictionary
#
# Returns:
#    (list): a list of Dependency objects
#
def _extract_depends_from_node(node, *, key=None):
    if key is None:
        build_depends = _extract_depends_from_node(node, key=Symbol.BUILD_DEPENDS)
        runtime_depends = _extract_depends_from_node(node, key=Symbol.RUNTIME_DEPENDS)
        depends = _extract_depends_from_node(node, key=Symbol.DEPENDS)
        return build_depends + runtime_depends + depends
    elif key == Symbol.BUILD_DEPENDS:
        default_dep_type = Symbol.BUILD
    elif key == Symbol.RUNTIME_DEPENDS:
        default_dep_type = Symbol.RUNTIME
    elif key == Symbol.DEPENDS:
        default_dep_type = None
    else:
        assert False, "Unexpected value of key '{}'".format(key)

    depends = _yaml.node_get(node, list, key, default_value=[])
    output_deps = []

    for index, dep in enumerate(depends):
        dep_provenance = _yaml.node_get_provenance(node, key=key, indices=[index])

        if isinstance(dep, str):
            dependency = Dependency(dep, provenance=dep_provenance, dep_type=default_dep_type)

        elif isinstance(dep, Mapping):
            if default_dep_type:
                _yaml.node_validate(dep, ['filename', 'junction'])
                dep_type = default_dep_type
            else:
                _yaml.node_validate(dep, ['filename', 'type', 'junction'])

                # Make type optional, for this we set it to None
                dep_type = _yaml.node_get(dep, str, Symbol.TYPE, default_value=None)
                if dep_type is None or dep_type == Symbol.ALL:
                    dep_type = None
                elif dep_type not in [Symbol.BUILD, Symbol.RUNTIME]:
                    provenance = _yaml.node_get_provenance(dep, key=Symbol.TYPE)
                    raise LoadError(LoadErrorReason.INVALID_DATA,
                                    "{}: Dependency type '{}' is not 'build', 'runtime' or 'all'"
                                    .format(provenance, dep_type))

            filename = _yaml.node_get(dep, str, Symbol.FILENAME)
            junction = _yaml.node_get(dep, str, Symbol.JUNCTION, default_value=None)
            dependency = Dependency(filename,
                                    dep_type=dep_type,
                                    junction=junction,
                                    provenance=dep_provenance)

        else:
            raise LoadError(LoadErrorReason.INVALID_DATA,
                            "{}: Dependency is not specified as a string or a dictionary".format(dep_provenance))

        output_deps.append(dependency)

    # Now delete the field, we dont want it anymore
    if key in node:
        del node[key]

    return output_deps
