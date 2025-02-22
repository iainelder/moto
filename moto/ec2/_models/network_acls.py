from moto.core import ACCOUNT_ID
from ..exceptions import (
    InvalidNetworkAclIdError,
    InvalidRouteTableIdError,
    NetworkAclEntryAlreadyExistsError,
)
from .core import TaggedEC2Resource
from ..utils import (
    generic_filter,
    random_network_acl_id,
    random_network_acl_subnet_association_id,
)


OWNER_ID = ACCOUNT_ID


class NetworkAclBackend(object):
    def __init__(self):
        self.network_acls = {}
        super().__init__()

    def get_network_acl(self, network_acl_id):
        network_acl = self.network_acls.get(network_acl_id, None)
        if not network_acl:
            raise InvalidNetworkAclIdError(network_acl_id)
        return network_acl

    def create_network_acl(self, vpc_id, tags=None, default=False):
        network_acl_id = random_network_acl_id()
        self.get_vpc(vpc_id)
        network_acl = NetworkAcl(self, network_acl_id, vpc_id, default)
        for tag in tags or []:
            network_acl.add_tag(tag.get("Key"), tag.get("Value"))
        self.network_acls[network_acl_id] = network_acl
        if default:
            self.add_default_entries(network_acl_id)
        return network_acl

    def add_default_entries(self, network_acl_id):
        default_acl_entries = [
            {"rule_number": "100", "rule_action": "allow", "egress": "true"},
            {"rule_number": "32767", "rule_action": "deny", "egress": "true"},
            {"rule_number": "100", "rule_action": "allow", "egress": "false"},
            {"rule_number": "32767", "rule_action": "deny", "egress": "false"},
        ]
        for entry in default_acl_entries:
            self.create_network_acl_entry(
                network_acl_id=network_acl_id,
                rule_number=entry["rule_number"],
                protocol="-1",
                rule_action=entry["rule_action"],
                egress=entry["egress"],
                cidr_block="0.0.0.0/0",
                icmp_code=None,
                icmp_type=None,
                port_range_from=None,
                port_range_to=None,
            )

    def get_all_network_acls(self, network_acl_ids=None, filters=None):
        self.describe_network_acls(network_acl_ids, filters)

    def delete_network_acl(self, network_acl_id):
        deleted = self.network_acls.pop(network_acl_id, None)
        if not deleted:
            raise InvalidNetworkAclIdError(network_acl_id)
        return deleted

    def create_network_acl_entry(
        self,
        network_acl_id,
        rule_number,
        protocol,
        rule_action,
        egress,
        cidr_block,
        icmp_code,
        icmp_type,
        port_range_from,
        port_range_to,
    ):

        network_acl = self.get_network_acl(network_acl_id)
        if any(
            entry.egress == egress and entry.rule_number == rule_number
            for entry in network_acl.network_acl_entries
        ):
            raise NetworkAclEntryAlreadyExistsError(rule_number)
        network_acl_entry = NetworkAclEntry(
            self,
            network_acl_id,
            rule_number,
            protocol,
            rule_action,
            egress,
            cidr_block,
            icmp_code,
            icmp_type,
            port_range_from,
            port_range_to,
        )

        network_acl.network_acl_entries.append(network_acl_entry)
        return network_acl_entry

    def delete_network_acl_entry(self, network_acl_id, rule_number, egress):
        network_acl = self.get_network_acl(network_acl_id)
        entry = next(
            entry
            for entry in network_acl.network_acl_entries
            if entry.egress == egress and entry.rule_number == rule_number
        )
        if entry is not None:
            network_acl.network_acl_entries.remove(entry)
        return entry

    def replace_network_acl_entry(
        self,
        network_acl_id,
        rule_number,
        protocol,
        rule_action,
        egress,
        cidr_block,
        icmp_code,
        icmp_type,
        port_range_from,
        port_range_to,
    ):

        self.delete_network_acl_entry(network_acl_id, rule_number, egress)
        network_acl_entry = self.create_network_acl_entry(
            network_acl_id,
            rule_number,
            protocol,
            rule_action,
            egress,
            cidr_block,
            icmp_code,
            icmp_type,
            port_range_from,
            port_range_to,
        )
        return network_acl_entry

    def replace_network_acl_association(self, association_id, network_acl_id):

        # lookup existing association for subnet and delete it
        default_acl = next(
            value
            for key, value in self.network_acls.items()
            if association_id in value.associations.keys()
        )

        subnet_id = None
        for key in default_acl.associations:
            if key == association_id:
                subnet_id = default_acl.associations[key].subnet_id
                del default_acl.associations[key]
                break

        new_assoc_id = random_network_acl_subnet_association_id()
        association = NetworkAclAssociation(
            self, new_assoc_id, subnet_id, network_acl_id
        )
        new_acl = self.get_network_acl(network_acl_id)
        new_acl.associations[new_assoc_id] = association
        return association

    def associate_default_network_acl_with_subnet(self, subnet_id, vpc_id):
        association_id = random_network_acl_subnet_association_id()
        acl = next(
            acl
            for acl in self.network_acls.values()
            if acl.default and acl.vpc_id == vpc_id
        )
        acl.associations[association_id] = NetworkAclAssociation(
            self, association_id, subnet_id, acl.id
        )

    def describe_network_acls(self, network_acl_ids=None, filters=None):
        network_acls = self.network_acls.copy().values()

        if network_acl_ids:
            network_acls = [
                network_acl
                for network_acl in network_acls
                if network_acl.id in network_acl_ids
            ]
            if len(network_acls) != len(network_acl_ids):
                invalid_id = list(
                    set(network_acl_ids).difference(
                        set([network_acl.id for network_acl in network_acls])
                    )
                )[0]
                raise InvalidRouteTableIdError(invalid_id)

        return generic_filter(filters, network_acls)


class NetworkAclAssociation(object):
    def __init__(self, ec2_backend, new_association_id, subnet_id, network_acl_id):
        self.ec2_backend = ec2_backend
        self.id = new_association_id
        self.new_association_id = new_association_id
        self.subnet_id = subnet_id
        self.network_acl_id = network_acl_id
        super().__init__()


class NetworkAcl(TaggedEC2Resource):
    def __init__(
        self, ec2_backend, network_acl_id, vpc_id, default=False, owner_id=OWNER_ID
    ):
        self.ec2_backend = ec2_backend
        self.id = network_acl_id
        self.vpc_id = vpc_id
        self.owner_id = owner_id
        self.network_acl_entries = []
        self.associations = {}
        self.default = "true" if default is True else "false"

    def get_filter_value(self, filter_name):
        if filter_name == "default":
            return self.default
        elif filter_name == "vpc-id":
            return self.vpc_id
        elif filter_name == "association.network-acl-id":
            return self.id
        elif filter_name == "association.subnet-id":
            return [assoc.subnet_id for assoc in self.associations.values()]
        elif filter_name == "owner-id":
            return self.owner_id
        else:
            return super().get_filter_value(filter_name, "DescribeNetworkAcls")


class NetworkAclEntry(TaggedEC2Resource):
    def __init__(
        self,
        ec2_backend,
        network_acl_id,
        rule_number,
        protocol,
        rule_action,
        egress,
        cidr_block,
        icmp_code,
        icmp_type,
        port_range_from,
        port_range_to,
    ):
        self.ec2_backend = ec2_backend
        self.network_acl_id = network_acl_id
        self.rule_number = rule_number
        self.protocol = protocol
        self.rule_action = rule_action
        self.egress = egress
        self.cidr_block = cidr_block
        self.icmp_code = icmp_code
        self.icmp_type = icmp_type
        self.port_range_from = port_range_from
        self.port_range_to = port_range_to
