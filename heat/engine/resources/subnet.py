# vim: tabstop=4 shiftwidth=4 softtabstop=4

#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from quantumclient.common.exceptions import QuantumClientException

from heat.common import exception
from heat.openstack.common import log as logging
from heat.engine import resource

logger = logging.getLogger(__name__)


class Subnet(resource.Resource):
    tags_schema = {'Key': {'Type': 'String',
                           'Required': True},
                   'Value': {'Type': 'String',
                             'Required': True}}

    properties_schema = {
        'AvailabilityZone': {'Type': 'String'},
        'CidrBlock': {
            'Type': 'String',
            'Required': True},
        'VpcId': {
            'Type': 'String',
            'Required': True},
        'Tags': {'Type': 'List', 'Schema': {
            'Type': 'Map',
            'Implemented': False,
            'Schema': tags_schema}}
    }

    def __init__(self, name, json_snippet, stack):
        super(Subnet, self).__init__(name, json_snippet, stack)

    def handle_create(self):
        client = self.quantum()
        # TODO sbaker Verify that this CidrBlock is within the vpc CidrBlock
        (network_id, router_id) = self.properties.get('VpcId').split(':')
        props = {
            'network_id': network_id,
            'cidr': self.properties.get('CidrBlock'),
            'name': self.name,
            'ip_version': 4
        }
        subnet = client.create_subnet({'subnet': props})['subnet']

        client.add_interface_router(
            router_id,
            {'subnet_id': subnet['id']})
        self.resource_id_set(subnet['id'])

    def handle_delete(self):
        client = self.quantum()
        (network_id, router_id) = self.properties.get('VpcId').split(':')
        try:
            client.remove_interface_router(
                router_id,
                {'subnet_id': self.resource_id})
        except QuantumClientException as ex:
            if ex.status_code != 404:
                raise ex

        try:
            client.delete_subnet(self.resource_id)
        except QuantumClientException as ex:
            if ex.status_code != 404:
                raise ex

    def handle_update(self, json_snippet):
        return self.UPDATE_REPLACE

    def FnGetAtt(self, key):
        if key == 'AvailabilityZone':
            return self.properties.get(key, '')
        raise exception.InvalidTemplateAttribute(resource=self.name, key=key)


def resource_mapping():
    return {
        'AWS::EC2::Subnet': Subnet,
    }