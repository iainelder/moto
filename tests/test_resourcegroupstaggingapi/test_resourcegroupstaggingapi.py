import json
import typing

import boto3
import pytest
from botocore.client import ClientError

from moto import mock_aws
from moto.core import DEFAULT_ACCOUNT_ID as ACCOUNT_ID
from tests import EXAMPLE_AMI_ID, EXAMPLE_AMI_ID2
from tests.test_ds.test_ds_simple_ad_directory import create_test_directory


@mock_aws
def test_get_resources_cloudformation():
    template = {
        "AWSTemplateFormatVersion": "2010-09-09",
        "Resources": {"test": {"Type": "AWS::S3::Bucket"}},
    }
    template_json = json.dumps(template)

    cf_client = boto3.client("cloudformation", region_name="us-east-1")

    stack_one = cf_client.create_stack(
        StackName="stack-1",
        TemplateBody=template_json,
        Tags=[{"Key": "tag", "Value": "one"}],
    ).get("StackId")
    stack_two = cf_client.create_stack(
        StackName="stack-2",
        TemplateBody=template_json,
        Tags=[{"Key": "tag", "Value": "two"}],
    ).get("StackId")
    stack_three = cf_client.create_stack(
        StackName="stack-3",
        TemplateBody=template_json,
        Tags=[{"Key": "tag", "Value": "three"}],
    ).get("StackId")

    rgta_client = boto3.client("resourcegroupstaggingapi", region_name="us-east-1")

    resp = rgta_client.get_resources(TagFilters=[{"Key": "tag", "Values": ["one"]}])
    assert len(resp["ResourceTagMappingList"]) == 1
    assert stack_one in resp["ResourceTagMappingList"][0]["ResourceARN"]

    resp = rgta_client.get_resources(
        TagFilters=[{"Key": "tag", "Values": ["one", "three"]}]
    )
    assert len(resp["ResourceTagMappingList"]) == 2
    assert stack_one in resp["ResourceTagMappingList"][0]["ResourceARN"]
    assert stack_three in resp["ResourceTagMappingList"][1]["ResourceARN"]

    kms_client = boto3.client("kms", region_name="us-east-1")
    kms_client.create_key(
        KeyUsage="ENCRYPT_DECRYPT", Tags=[{"TagKey": "tag", "TagValue": "two"}]
    )

    resp = rgta_client.get_resources(TagFilters=[{"Key": "tag", "Values": ["two"]}])
    assert len(resp["ResourceTagMappingList"]) == 2
    assert stack_two in resp["ResourceTagMappingList"][0]["ResourceARN"]
    assert "kms" in resp["ResourceTagMappingList"][1]["ResourceARN"]

    resp = rgta_client.get_resources(
        ResourceTypeFilters=["cloudformation:stack"],
        TagFilters=[{"Key": "tag", "Values": ["two"]}],
    )
    assert len(resp["ResourceTagMappingList"]) == 1
    assert stack_two in resp["ResourceTagMappingList"][0]["ResourceARN"]


@mock_aws
def test_get_resources_acm():
    client = boto3.client("acm", region_name="us-east-1")
    cert_blue = client.request_certificate(
        DomainName="helloworldone.com",
        ValidationMethod="DNS",
        Tags=[
            {"Key": "TagKey1", "Value": "TagValue1"},
            {"Key": "TagKey2", "Value": "TagValue2"},
            {"Key": "Color", "Value": "Blue"},
        ],
    )
    client.request_certificate(
        DomainName="helloworldtwo.com",
        ValidationMethod="DNS",
        Tags=[
            {"Key": "TagKey1", "Value": "TagValue1"},
            {"Key": "TagKey2", "Value": ""},
            {"Key": "Color", "Value": "Green"},
        ],
    )
    rgta_client = boto3.client("resourcegroupstaggingapi", region_name="us-east-1")
    resources_no_filter = rgta_client.get_resources(
        ResourceTypeFilters=["acm"],
    )
    assert len(resources_no_filter["ResourceTagMappingList"]) == 2

    resources_blue_filter = rgta_client.get_resources(
        TagFilters=[{"Key": "Color", "Values": ["Blue"]}]
    )
    assert len(resources_blue_filter["ResourceTagMappingList"]) == 1
    assert (
        cert_blue["CertificateArn"]
        == resources_blue_filter["ResourceTagMappingList"][0]["ResourceARN"]
    )


@mock_aws
def test_get_resources_backup():
    backup = boto3.client("backup", region_name="eu-central-1")

    # Create two tagged Backup Vaults
    for i in range(1, 3):
        i_str = str(i)

        backup.create_backup_vault(
            BackupVaultName="backup-vault-tag-" + i_str,
            BackupVaultTags={
                "Test": i_str,
            },
        )

    rtapi = boto3.client("resourcegroupstaggingapi", region_name="eu-central-1")

    # Basic test
    resp = rtapi.get_resources(ResourceTypeFilters=["backup"])
    assert len(resp["ResourceTagMappingList"]) == 2

    # Test tag filtering
    resp = rtapi.get_resources(
        ResourceTypeFilters=["backup"],
        TagFilters=[{"Key": "Test", "Values": ["1"]}],
    )
    assert len(resp["ResourceTagMappingList"]) == 1
    assert {"Key": "Test", "Value": "1"} in resp["ResourceTagMappingList"][0]["Tags"]


@mock_aws
def test_get_resources_dms_endpoint():
    client = boto3.client("dms", region_name="us-east-1")
    endpoint = client.create_endpoint(
        EndpointIdentifier="test-endpoint",
        EndpointType="source",
        EngineName="mysql",
        ResourceIdentifier="sample_identifier",
        Tags=[{"Key": "tag", "Value": "a tag"}],
    )
    endpoint_arn = endpoint["Endpoint"]["EndpointArn"]
    rgta_client = boto3.client("resourcegroupstaggingapi", region_name="us-east-1")
    resp = rgta_client.get_resources(
        ResourceTypeFilters=["dms:endpoint"],
        TagFilters=[{"Key": "tag", "Values": ["a tag"]}],
    )
    assert len(resp["ResourceTagMappingList"]) == 1
    assert endpoint_arn == resp["ResourceTagMappingList"][0]["ResourceARN"]


@mock_aws
def test_get_resources_dms_replication_instance():
    client = boto3.client("dms", region_name="us-east-1")
    replication_instance = client.create_replication_instance(
        ReplicationInstanceIdentifier="test-instance-1",
        ReplicationInstanceClass="dms.t2.micro",
        EngineVersion="3.4.5",
        Tags=[{"Key": "tag", "Value": "a tag"}],
    )

    replication_instance_arn = replication_instance["ReplicationInstance"][
        "ReplicationInstanceArn"
    ]
    rgta_client = boto3.client("resourcegroupstaggingapi", region_name="us-east-1")
    resp = rgta_client.get_resources(
        ResourceTypeFilters=["dms:replication-instance"],
        TagFilters=[{"Key": "tag", "Values": ["a tag"]}],
    )
    assert len(resp["ResourceTagMappingList"]) == 1
    assert replication_instance_arn == resp["ResourceTagMappingList"][0]["ResourceARN"]


@mock_aws
def test_get_resources_ecs():
    # ecs:cluster
    client = boto3.client("ecs", region_name="us-east-1")
    cluster_one = (
        client.create_cluster(
            clusterName="cluster-a", tags=[{"key": "tag", "value": "a tag"}]
        )
        .get("cluster")
        .get("clusterArn")
    )
    cluster_two = (
        client.create_cluster(
            clusterName="cluster-b", tags=[{"key": "tag", "value": "b tag"}]
        )
        .get("cluster")
        .get("clusterArn")
    )

    rgta_client = boto3.client("resourcegroupstaggingapi", region_name="us-east-1")
    resp = rgta_client.get_resources(TagFilters=[{"Key": "tag", "Values": ["a tag"]}])
    assert len(resp["ResourceTagMappingList"]) == 1
    assert cluster_one in resp["ResourceTagMappingList"][0]["ResourceARN"]

    # ecs:service
    service_one = (
        client.create_service(
            cluster=cluster_one,
            serviceName="service-a",
            tags=[{"key": "tag", "value": "a tag"}],
        )
        .get("service")
        .get("serviceArn")
    )

    service_two = (
        client.create_service(
            cluster=cluster_two,
            serviceName="service-b",
            tags=[{"key": "tag", "value": "b tag"}],
        )
        .get("service")
        .get("serviceArn")
    )

    resp = rgta_client.get_resources(TagFilters=[{"Key": "tag", "Values": ["a tag"]}])
    assert len(resp["ResourceTagMappingList"]) == 2
    assert service_one in resp["ResourceTagMappingList"][0]["ResourceARN"]
    assert cluster_one in resp["ResourceTagMappingList"][1]["ResourceARN"]

    resp = rgta_client.get_resources(
        ResourceTypeFilters=["ecs:cluster"],
        TagFilters=[{"Key": "tag", "Values": ["b tag"]}],
    )
    assert len(resp["ResourceTagMappingList"]) == 1
    assert service_two not in resp["ResourceTagMappingList"][0]["ResourceARN"]
    assert cluster_two in resp["ResourceTagMappingList"][0]["ResourceARN"]

    resp = rgta_client.get_resources(
        ResourceTypeFilters=["ecs:service"],
        TagFilters=[{"Key": "tag", "Values": ["b tag"]}],
    )
    assert len(resp["ResourceTagMappingList"]) == 1
    assert service_two in resp["ResourceTagMappingList"][0]["ResourceARN"]
    assert cluster_two not in resp["ResourceTagMappingList"][0]["ResourceARN"]

    # ecs:task
    resp = client.register_task_definition(
        family="test_ecs_task",
        containerDefinitions=[
            {
                "name": "hello_world",
                "image": "docker/hello-world:latest",
                "cpu": 1024,
                "memory": 400,
                "essential": True,
                "environment": [
                    {"name": "AWS_ACCESS_KEY_ID", "value": "SOME_ACCESS_KEY"}
                ],
                "logConfiguration": {"logDriver": "json-file"},
            }
        ],
    )

    ec2_client = boto3.client("ec2", region_name="us-east-1")
    vpc = ec2_client.create_vpc(CidrBlock="10.0.0.0/16").get("Vpc").get("VpcId")
    subnet = (
        ec2_client.create_subnet(VpcId=vpc, CidrBlock="10.0.0.0/18")
        .get("Subnet")
        .get("SubnetId")
    )
    sg = ec2_client.create_security_group(
        VpcId=vpc, GroupName="test-ecs", Description="moto ecs"
    ).get("GroupId")

    task_one = (
        client.run_task(
            cluster="cluster-a",
            taskDefinition="test_ecs_task",
            launchType="FARGATE",
            networkConfiguration={
                "awsvpcConfiguration": {
                    "subnets": [subnet],
                    "securityGroups": [sg],
                }
            },
            tags=[{"key": "tag", "value": "a tag"}],
        )
        .get("tasks")[0]
        .get("taskArn")
    )

    task_two = (
        client.run_task(
            cluster="cluster-b",
            taskDefinition="test_ecs_task",
            launchType="FARGATE",
            networkConfiguration={
                "awsvpcConfiguration": {
                    "subnets": [subnet],
                    "securityGroups": [sg],
                }
            },
            tags=[{"key": "tag", "value": "b tag"}],
        )
        .get("tasks")[0]
        .get("taskArn")
    )

    resp = rgta_client.get_resources(TagFilters=[{"Key": "tag", "Values": ["b tag"]}])
    assert len(resp["ResourceTagMappingList"]) == 3
    assert service_two in resp["ResourceTagMappingList"][0]["ResourceARN"]
    assert cluster_two in resp["ResourceTagMappingList"][1]["ResourceARN"]
    assert task_two in resp["ResourceTagMappingList"][2]["ResourceARN"]

    resp = rgta_client.get_resources(
        ResourceTypeFilters=["ecs:task"],
        TagFilters=[{"Key": "tag", "Values": ["a tag"]}],
    )
    assert len(resp["ResourceTagMappingList"]) == 1
    assert task_one in resp["ResourceTagMappingList"][0]["ResourceARN"]
    assert task_two not in resp["ResourceTagMappingList"][0]["ResourceARN"]

    # ecs:task-definition
    task_def_one = client.register_task_definition(
        family="test_ecs_task_def_1",
        containerDefinitions=[
            {
                "name": "hello_world",
                "image": "docker/hello-world:latest",
                "cpu": 1024,
                "memory": 400,
                "essential": True,
            }
        ],
        tags=[{"key": "tag", "value": "a tag"}],
    )
    task_def_one_arn = task_def_one["taskDefinition"]["taskDefinitionArn"]

    resp = rgta_client.get_resources(
        ResourceTypeFilters=["ecs:task-definition"],
        TagFilters=[{"Key": "tag", "Values": ["a tag"]}],
    )
    assert len(resp["ResourceTagMappingList"]) == 1
    assert task_def_one_arn == resp["ResourceTagMappingList"][0]["ResourceARN"]


@mock_aws
def test_get_resources_ec2():
    client = boto3.client("ec2", region_name="eu-central-1")

    instances = client.run_instances(
        ImageId=EXAMPLE_AMI_ID,
        MinCount=1,
        MaxCount=1,
        InstanceType="t2.micro",
        TagSpecifications=[
            {
                "ResourceType": "instance",
                "Tags": [
                    {"Key": "MY_TAG1", "Value": "MY_VALUE1"},
                    {"Key": "MY_TAG2", "Value": "MY_VALUE2"},
                ],
            },
            {
                "ResourceType": "instance",
                "Tags": [{"Key": "MY_TAG3", "Value": "MY_VALUE3"}],
            },
        ],
    )
    instance_id = instances["Instances"][0]["InstanceId"]
    image_id = client.create_image(Name="testami", InstanceId=instance_id)["ImageId"]

    client.create_tags(Resources=[image_id], Tags=[{"Key": "ami", "Value": "test"}])

    rtapi = boto3.client("resourcegroupstaggingapi", region_name="eu-central-1")
    resp = rtapi.get_resources()
    # Check we have 1 entry for Instance, 1 Entry for AMI
    assert len(resp["ResourceTagMappingList"]) == 2

    # 1 Entry for AMI
    resp = rtapi.get_resources(ResourceTypeFilters=["ec2:image"])
    assert len(resp["ResourceTagMappingList"]) == 1
    assert "image/" in resp["ResourceTagMappingList"][0]["ResourceARN"]

    # As were iterating the same data, this rules out that the test above was a fluke
    resp = rtapi.get_resources(ResourceTypeFilters=["ec2:instance"])
    assert len(resp["ResourceTagMappingList"]) == 1
    assert "instance/" in resp["ResourceTagMappingList"][0]["ResourceARN"]

    # Basic test of tag filters
    resp = rtapi.get_resources(
        TagFilters=[{"Key": "MY_TAG1", "Values": ["MY_VALUE1", "some_other_value"]}]
    )
    assert len(resp["ResourceTagMappingList"]) == 1
    assert "instance/" in resp["ResourceTagMappingList"][0]["ResourceARN"]


@mock_aws
def test_get_resources_ec2_vpc():
    ec2 = boto3.resource("ec2", region_name="us-west-2")
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")
    ec2.create_tags(Resources=[vpc.id], Tags=[{"Key": "test", "Value": "test_vpc"}])
    subnet = ec2.create_subnet(VpcId=vpc.id, CidrBlock="10.0.1.0/24")
    ec2.create_tags(
        Resources=[subnet.id], Tags=[{"Key": "test", "Value": "test_subnet"}]
    )

    rtapi = boto3.client("resourcegroupstaggingapi", region_name="us-west-2")
    # Check that we have one entry for VPC, one for the subnet
    resp = rtapi.get_resources(ResourceTypeFilters=["ec2"])
    assert len(resp["ResourceTagMappingList"]) == 2

    # 1 Entry for VPC
    resp = rtapi.get_resources(ResourceTypeFilters=["ec2:vpc"])
    assert len(resp["ResourceTagMappingList"]) == 1
    assert "vpc/" in resp["ResourceTagMappingList"][0]["ResourceARN"]
    resp = rtapi.get_resources(TagFilters=[{"Key": "test", "Values": ["test_vpc"]}])
    assert len(resp["ResourceTagMappingList"]) == 1
    assert "vpc/" in resp["ResourceTagMappingList"][0]["ResourceARN"]

    # 1 Entry for Subnet
    resp = rtapi.get_resources(ResourceTypeFilters=["ec2:subnet"])
    assert len(resp["ResourceTagMappingList"]) == 1
    assert "subnet/" in resp["ResourceTagMappingList"][0]["ResourceARN"]
    resp = rtapi.get_resources(TagFilters=[{"Key": "test", "Values": ["test_subnet"]}])
    assert len(resp["ResourceTagMappingList"]) == 1
    assert "subnet/" in resp["ResourceTagMappingList"][0]["ResourceARN"]


@mock_aws
def test_get_tag_keys_ec2():
    client = boto3.client("ec2", region_name="eu-central-1")

    client.run_instances(
        ImageId=EXAMPLE_AMI_ID,
        MinCount=1,
        MaxCount=1,
        InstanceType="t2.micro",
        TagSpecifications=[
            {
                "ResourceType": "instance",
                "Tags": [
                    {"Key": "MY_TAG1", "Value": "MY_VALUE1"},
                    {"Key": "MY_TAG2", "Value": "MY_VALUE2"},
                ],
            },
            {
                "ResourceType": "instance",
                "Tags": [{"Key": "MY_TAG3", "Value": "MY_VALUE3"}],
            },
        ],
    )

    rtapi = boto3.client("resourcegroupstaggingapi", region_name="eu-central-1")
    resp = rtapi.get_tag_keys()

    assert "MY_TAG1" in resp["TagKeys"]
    assert "MY_TAG2" in resp["TagKeys"]
    assert "MY_TAG3" in resp["TagKeys"]

    # TODO test pagenation


@mock_aws
def test_get_tag_values_ec2():
    client = boto3.client("ec2", region_name="eu-central-1")

    client.run_instances(
        ImageId=EXAMPLE_AMI_ID,
        MinCount=1,
        MaxCount=1,
        InstanceType="t2.micro",
        TagSpecifications=[
            {
                "ResourceType": "instance",
                "Tags": [
                    {"Key": "MY_TAG1", "Value": "MY_VALUE1"},
                    {"Key": "MY_TAG2", "Value": "MY_VALUE2"},
                ],
            },
            {
                "ResourceType": "instance",
                "Tags": [{"Key": "MY_TAG3", "Value": "MY_VALUE3"}],
            },
        ],
    )
    client.run_instances(
        ImageId=EXAMPLE_AMI_ID,
        MinCount=1,
        MaxCount=1,
        InstanceType="t2.micro",
        TagSpecifications=[
            {
                "ResourceType": "instance",
                "Tags": [
                    {"Key": "MY_TAG1", "Value": "MY_VALUE4"},
                    {"Key": "MY_TAG2", "Value": "MY_VALUE5"},
                ],
            },
            {
                "ResourceType": "instance",
                "Tags": [{"Key": "MY_TAG3", "Value": "MY_VALUE6"}],
            },
        ],
    )

    rtapi = boto3.client("resourcegroupstaggingapi", region_name="eu-central-1")
    resp = rtapi.get_tag_values(Key="MY_TAG1")

    assert "MY_VALUE1" in resp["TagValues"]
    assert "MY_VALUE4" in resp["TagValues"]


@mock_aws
def test_get_tag_values_event_bus():
    client = boto3.client("events", "us-east-1")
    client.create_event_bus(Name="test-bus1")
    event_bus_2 = client.create_event_bus(
        Name="test-bus2", Tags=[{"Key": "Test", "Value": "Test2"}]
    )
    event_bus_3 = client.create_event_bus(Name="test-bus3")
    client.tag_resource(
        ResourceARN=event_bus_3["EventBusArn"], Tags=[{"Key": "Test", "Value": "Added"}]
    )

    rtapi = boto3.client("resourcegroupstaggingapi", "us-east-1")
    resp = rtapi.get_resources(ResourceTypeFilters=["events:event-bus"])
    assert len(resp["ResourceTagMappingList"]) == 2
    assert event_bus_2["EventBusArn"] in [
        x["ResourceARN"] for x in resp["ResourceTagMappingList"]
    ]
    assert event_bus_3["EventBusArn"] in [
        x["ResourceARN"] for x in resp["ResourceTagMappingList"]
    ]


@mock_aws
def test_get_tag_values_cloudfront():
    client = boto3.client("cloudfront", "us-east-1")
    for i in range(1, 3):
        caller_reference = f"distribution{i}"
        origin_id = f"origin{i}"

        client.create_distribution_with_tags(
            DistributionConfigWithTags={
                "DistributionConfig": {
                    "CallerReference": caller_reference,
                    "Origins": {
                        "Quantity": 1,
                        "Items": [
                            {
                                "Id": origin_id,
                                "DomainName": "example-bucket.s3.amazonaws.com",
                                "S3OriginConfig": {"OriginAccessIdentity": ""},
                            }
                        ],
                    },
                    "DefaultCacheBehavior": {
                        "TargetOriginId": origin_id,
                        "ViewerProtocolPolicy": "allow-all",
                        "TrustedSigners": {"Enabled": False, "Quantity": 0},
                        "ForwardedValues": {
                            "QueryString": False,
                            "Cookies": {"Forward": "none"},
                        },
                        "MinTTL": 0,
                    },
                    "Comment": f"Sample distribution {i}",
                    "Enabled": True,
                },
                "Tags": {"Items": [{"Key": "Test", "Value": f"Test{i}"}]},
            }
        )
    rtapi = boto3.client("resourcegroupstaggingapi", "us-east-1")

    # Test tag filtering
    resp = rtapi.get_resources(
        ResourceTypeFilters=["cloudfront"],
        TagFilters=[{"Key": "Test", "Values": ["Test1"]}],
    )
    assert len(resp["ResourceTagMappingList"]) == 1
    assert {"Key": "Test", "Value": "Test1"} in resp["ResourceTagMappingList"][0][
        "Tags"
    ]


@mock_aws
def test_get_tag_values_lexv2_models():
    client = boto3.client("lexv2-models", "us-east-1")
    # Create a bot
    bot = client.create_bot(
        botName="TestBot",
        description="A test bot",
        roleArn="arn:aws:iam::123456789012:role/service-role/AmazonLexV2BotRole",
        dataPrivacy={"childDirected": False},
        idleSessionTTLInSeconds=300,
        botTags={"Test": "Test1"},
    )
    bot_id = bot["botId"]
    # Create a bot alias with tags
    client.create_bot_alias(
        botAliasName="TestBotAlias",
        botId=bot_id,
        description="A test bot alias",
        tags={"Test": "Test2"},
    )

    rtapi = boto3.client("resourcegroupstaggingapi", "us-east-1")

    # Test bot tag filtering
    resp = rtapi.get_resources(
        ResourceTypeFilters=["lexv2:bot"],
        TagFilters=[{"Key": "Test", "Values": ["Test1"]}],
    )
    assert len(resp["ResourceTagMappingList"]) == 1
    assert {"Key": "Test", "Value": "Test1"} in resp["ResourceTagMappingList"][0][
        "Tags"
    ]

    # Test bot-alias tag filtering
    resp = rtapi.get_resources(
        ResourceTypeFilters=["lexv2:bot-alias"],
        TagFilters=[{"Key": "Test", "Values": ["Test2"]}],
    )
    assert len(resp["ResourceTagMappingList"]) == 1
    assert {"Key": "Test", "Value": "Test2"} in resp["ResourceTagMappingList"][0][
        "Tags"
    ]


@mock_aws
def test_get_tag_values_cloudwatch():
    cloudwatch = boto3.client("cloudwatch", "us-east-1")

    name = "tester"
    cloudwatch.put_metric_alarm(
        AlarmActions=["arn:alarm"],
        AlarmDescription="A test",
        AlarmName=name,
        ComparisonOperator="GreaterThanOrEqualToThreshold",
        Dimensions=[{"Name": "InstanceId", "Value": "i-0123457"}],
        EvaluationPeriods=5,
        InsufficientDataActions=["arn:insufficient"],
        Namespace=f"{name}_namespace",
        MetricName=f"{name}_metric",
        OKActions=["arn:ok"],
        Period=60,
        Statistic="Average",
        Threshold=2,
        Unit="Seconds",
        Tags=[{"Key": "key-1", "Value": "value-1"}],
    )

    cloudwatch.put_insight_rule(
        RuleName=name,
        RuleDefinition="""{"Schema": "CloudWatchLogRule}""",
        RuleState="ENABLED",
        Tags=[{"Key": "key-2", "Value": "value-2"}],
    )
    rtapi = boto3.client("resourcegroupstaggingapi", "us-east-1")

    # Test alarm tag filtering
    resp = rtapi.get_resources(
        ResourceTypeFilters=["cloudwatch:alarm"],
        TagFilters=[{"Key": "key-1", "Values": ["value-1"]}],
    )
    assert len(resp["ResourceTagMappingList"]) == 1
    assert {"Key": "key-1", "Value": "value-1"} in resp["ResourceTagMappingList"][0][
        "Tags"
    ]

    # Test insight-rule tag filtering
    resp = rtapi.get_resources(
        ResourceTypeFilters=["cloudwatch:insight-rule"],
        TagFilters=[{"Key": "key-2", "Values": ["value-2"]}],
    )

    assert len(resp["ResourceTagMappingList"]) == 1
    assert {"Key": "key-2", "Value": "value-2"} in resp["ResourceTagMappingList"][0][
        "Tags"
    ]


@mock_aws
def test_get_many_resources():
    elbv2 = boto3.client("elbv2", region_name="us-east-1")
    ec2 = boto3.resource("ec2", region_name="us-east-1")
    kms = boto3.client("kms", region_name="us-east-1")

    security_group = ec2.create_security_group(
        GroupName="a-security-group", Description="First One"
    )
    vpc = ec2.create_vpc(CidrBlock="172.28.7.0/24", InstanceTenancy="default")
    subnet1 = ec2.create_subnet(
        VpcId=vpc.id, CidrBlock="172.28.7.192/26", AvailabilityZone="us-east-1a"
    )
    subnet2 = ec2.create_subnet(
        VpcId=vpc.id, CidrBlock="172.28.7.0/26", AvailabilityZone="us-east-1b"
    )

    elbv2.create_load_balancer(
        Name="my-lb",
        Subnets=[subnet1.id, subnet2.id],
        SecurityGroups=[security_group.id],
        Scheme="internal",
        Tags=[
            {"Key": "key_name", "Value": "a_value"},
            {"Key": "key_2", "Value": "val2"},
        ],
    )

    elbv2.create_load_balancer(
        Name="my-other-lb",
        Subnets=[subnet1.id, subnet2.id],
        SecurityGroups=[security_group.id],
        Scheme="internal",
    )

    kms.create_key(
        KeyUsage="ENCRYPT_DECRYPT",
        Tags=[
            {"TagKey": "key_name", "TagValue": "a_value"},
            {"TagKey": "key_2", "TagValue": "val2"},
        ],
    )

    rtapi = boto3.client("resourcegroupstaggingapi", region_name="us-east-1")

    resp = rtapi.get_resources(
        ResourceTypeFilters=["elasticloadbalancing:loadbalancer"]
    )

    assert len(resp["ResourceTagMappingList"]) == 2
    assert "loadbalancer/" in resp["ResourceTagMappingList"][0]["ResourceARN"]
    resp = rtapi.get_resources(
        ResourceTypeFilters=["elasticloadbalancing:loadbalancer"],
        TagFilters=[{"Key": "key_name"}],
    )

    assert len(resp["ResourceTagMappingList"]) == 1
    assert {"Key": "key_name", "Value": "a_value"} in resp["ResourceTagMappingList"][0][
        "Tags"
    ]

    # TODO test pagination


@mock_aws
def test_get_resources_target_group():
    ec2 = boto3.resource("ec2", region_name="eu-central-1")
    elbv2 = boto3.client("elbv2", region_name="eu-central-1")

    vpc = ec2.create_vpc(CidrBlock="172.28.7.0/24", InstanceTenancy="default")

    # Create two tagged target groups
    for i in range(1, 3):
        i_str = str(i)

        target_group = elbv2.create_target_group(
            Name="test" + i_str,
            Protocol="HTTP",
            Port=8080,
            VpcId=vpc.id,
            TargetType="instance",
        )["TargetGroups"][0]

        elbv2.add_tags(
            ResourceArns=[target_group["TargetGroupArn"]],
            Tags=[{"Key": "Test", "Value": i_str}],
        )

    rtapi = boto3.client("resourcegroupstaggingapi", region_name="eu-central-1")

    # Basic test
    resp = rtapi.get_resources(ResourceTypeFilters=["elasticloadbalancing:targetgroup"])
    assert len(resp["ResourceTagMappingList"]) == 2

    # Test tag filtering
    resp = rtapi.get_resources(
        ResourceTypeFilters=["elasticloadbalancing:targetgroup"],
        TagFilters=[{"Key": "Test", "Values": ["1"]}],
    )
    assert len(resp["ResourceTagMappingList"]) == 1
    assert {"Key": "Test", "Value": "1"} in resp["ResourceTagMappingList"][0]["Tags"]


@pytest.mark.parametrize("resource_type", ["s3", "s3:bucket"])
@mock_aws
def test_get_resources_s3(resource_type):
    # Tests pagination
    s3_client = boto3.client("s3", region_name="eu-central-1")

    # Will end up having key1,key2,key3,key4
    response_keys = set()

    # Create 4 buckets
    for i in range(1, 5):
        i_str = str(i)
        s3_client.create_bucket(
            Bucket="test_bucket" + i_str,
            CreateBucketConfiguration={"LocationConstraint": "eu-central-1"},
        )
        s3_client.put_bucket_tagging(
            Bucket="test_bucket" + i_str,
            Tagging={"TagSet": [{"Key": "key" + i_str, "Value": "value" + i_str}]},
        )
        response_keys.add("key" + i_str)

    rtapi = boto3.client("resourcegroupstaggingapi", region_name="eu-central-1")
    resp = rtapi.get_resources(ResourcesPerPage=2, ResourceTypeFilters=[resource_type])
    for resource in resp["ResourceTagMappingList"]:
        response_keys.remove(resource["Tags"][0]["Key"])

    assert len(response_keys) == 2

    resp = rtapi.get_resources(
        ResourcesPerPage=2,
        PaginationToken=resp["PaginationToken"],
        ResourceTypeFilters=[resource_type],
    )
    for resource in resp["ResourceTagMappingList"]:
        response_keys.remove(resource["Tags"][0]["Key"])

    assert len(response_keys) == 0


@mock_aws
def test_multiple_tag_filters():
    client = boto3.client("ec2", region_name="eu-central-1")

    resp = client.run_instances(
        ImageId=EXAMPLE_AMI_ID,
        MinCount=1,
        MaxCount=1,
        InstanceType="t2.micro",
        TagSpecifications=[
            {
                "ResourceType": "instance",
                "Tags": [
                    {"Key": "MY_TAG1", "Value": "MY_UNIQUE_VALUE"},
                    {"Key": "MY_TAG2", "Value": "MY_SHARED_VALUE"},
                ],
            },
            {
                "ResourceType": "instance",
                "Tags": [{"Key": "MY_TAG3", "Value": "MY_VALUE3"}],
            },
        ],
    )
    instance_1_id = resp["Instances"][0]["InstanceId"]

    resp = client.run_instances(
        ImageId=EXAMPLE_AMI_ID2,
        MinCount=1,
        MaxCount=1,
        InstanceType="t2.micro",
        TagSpecifications=[
            {
                "ResourceType": "instance",
                "Tags": [
                    {"Key": "MY_TAG1", "Value": "MY_ALT_UNIQUE_VALUE"},
                    {"Key": "MY_TAG2", "Value": "MY_SHARED_VALUE"},
                ],
            },
            {
                "ResourceType": "instance",
                "Tags": [{"Key": "MY_ALT_TAG3", "Value": "MY_VALUE3"}],
            },
        ],
    )
    instance_2_id = resp["Instances"][0]["InstanceId"]

    rtapi = boto3.client("resourcegroupstaggingapi", region_name="eu-central-1")
    results = rtapi.get_resources(
        TagFilters=[
            {"Key": "MY_TAG1", "Values": ["MY_UNIQUE_VALUE"]},
            {"Key": "MY_TAG2", "Values": ["MY_SHARED_VALUE"]},
        ]
    ).get("ResourceTagMappingList", [])
    assert len(results) == 1
    assert instance_1_id in results[0]["ResourceARN"]
    assert instance_2_id not in results[0]["ResourceARN"]


@mock_aws
def test_get_resources_lambda():
    def get_role_name():
        iam = boto3.client("iam", region_name="us-west-2")
        try:
            return iam.get_role(RoleName="my-role")["Role"]["Arn"]
        except ClientError:
            return iam.create_role(
                RoleName="my-role",
                AssumeRolePolicyDocument="some policy",
                Path="/my-path/",
            )["Role"]["Arn"]

    client = boto3.client("lambda", region_name="us-west-2")

    zipfile = """
              def lambda_handler(event, context):
                  print("custom log event")
                  return event
              """

    # create one lambda without tags
    client.create_function(
        FunctionName="lambda-no-tag",
        Runtime="python3.11",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"ZipFile": zipfile},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
    )

    # create second & third lambda with tags
    circle_arn = client.create_function(
        FunctionName="lambda-tag-value-1",
        Runtime="python3.11",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"ZipFile": zipfile},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
        Tags={"Color": "green", "Shape": "circle"},
    )["FunctionArn"]

    rectangle_arn = client.create_function(
        FunctionName="lambda-tag-value-2",
        Runtime="python3.11",
        Role=get_role_name(),
        Handler="lambda_function.lambda_handler",
        Code={"ZipFile": zipfile},
        Description="test lambda function",
        Timeout=3,
        MemorySize=128,
        Publish=True,
        Tags={"Color": "green", "Shape": "rectangle"},
    )["FunctionArn"]

    def assert_response(response, expected_arns):
        results = response.get("ResourceTagMappingList", [])
        resultArns = []
        for item in results:
            resultArns.append(item["ResourceARN"])
        for arn in resultArns:
            assert arn in expected_arns
        for arn in expected_arns:
            assert arn in resultArns

    rtapi = boto3.client("resourcegroupstaggingapi", region_name="us-west-2")
    resp = rtapi.get_resources(ResourceTypeFilters=["lambda"])
    assert_response(resp, [circle_arn, rectangle_arn])

    resp = rtapi.get_resources(ResourceTypeFilters=["lambda:function"])
    assert_response(resp, [circle_arn, rectangle_arn])

    resp = rtapi.get_resources(TagFilters=[{"Key": "Color", "Values": ["green"]}])
    assert_response(resp, [circle_arn, rectangle_arn])

    resp = rtapi.get_resources(TagFilters=[{"Key": "Shape", "Values": ["circle"]}])
    assert_response(resp, [circle_arn])

    resp = rtapi.get_resources(TagFilters=[{"Key": "Shape", "Values": ["rectangle"]}])
    assert_response(resp, [rectangle_arn])


@mock_aws
def test_get_resources_sqs():
    sqs = boto3.resource("sqs", region_name="eu-central-1")

    # Create two tagged SQS queues
    for i in range(1, 3):
        i_str = str(i)

        sqs.create_queue(
            QueueName="sqs-tag-value-" + i_str,
            tags={
                "Test": i_str,
            },
        )

    rtapi = boto3.client("resourcegroupstaggingapi", region_name="eu-central-1")

    # Basic test
    resp = rtapi.get_resources(ResourceTypeFilters=["sqs"])
    assert len(resp["ResourceTagMappingList"]) == 2

    # Test tag filtering
    resp = rtapi.get_resources(
        ResourceTypeFilters=["sqs"],
        TagFilters=[{"Key": "Test", "Values": ["1"]}],
    )
    assert len(resp["ResourceTagMappingList"]) == 1
    assert {"Key": "Test", "Value": "1"} in resp["ResourceTagMappingList"][0]["Tags"]


def create_directory():
    ec2_client = boto3.client("ec2", region_name="eu-central-1")
    ds_client = boto3.client("ds", region_name="eu-central-1")
    directory_id = create_test_directory(ds_client, ec2_client)
    return directory_id


@mock_aws
def test_get_resources_workspaces():
    workspaces = boto3.client("workspaces", region_name="eu-central-1")

    # Create two tagged Workspaces
    directory_id = create_directory()
    workspaces.register_workspace_directory(DirectoryId=directory_id)
    workspaces.create_workspaces(
        Workspaces=[
            {
                "DirectoryId": directory_id,
                "UserName": "Administrator",
                "BundleId": "wsb-bh8rsxt14",
                "Tags": [
                    {"Key": "Test", "Value": "1"},
                ],
            },
            {
                "DirectoryId": directory_id,
                "UserName": "Administrator",
                "BundleId": "wsb-bh8rsxt14",
                "Tags": [
                    {"Key": "Test", "Value": "2"},
                ],
            },
        ]
    )

    rtapi = boto3.client("resourcegroupstaggingapi", region_name="eu-central-1")

    # Basic test
    resp = rtapi.get_resources(ResourceTypeFilters=["workspaces"])
    assert len(resp["ResourceTagMappingList"]) == 2

    # Test tag filtering
    resp = rtapi.get_resources(
        ResourceTypeFilters=["workspaces"],
        TagFilters=[{"Key": "Test", "Values": ["1"]}],
    )
    assert len(resp["ResourceTagMappingList"]) == 1
    assert {"Key": "Test", "Value": "1"} in resp["ResourceTagMappingList"][0]["Tags"]


@mock_aws
def test_get_resources_workspace_directories():
    workspaces = boto3.client("workspaces", region_name="eu-central-1")

    # Create two tagged Workspaces Directories
    for i in range(1, 3):
        i_str = str(i)
        directory_id = create_directory()
        workspaces.register_workspace_directory(
            DirectoryId=directory_id,
            Tags=[{"Key": "Test", "Value": i_str}],
        )

    rtapi = boto3.client("resourcegroupstaggingapi", region_name="eu-central-1")

    # Basic test
    resp = rtapi.get_resources(ResourceTypeFilters=["workspaces-directory"])
    assert len(resp["ResourceTagMappingList"]) == 2

    # Test tag filtering
    resp = rtapi.get_resources(
        ResourceTypeFilters=["workspaces-directory"],
        TagFilters=[{"Key": "Test", "Values": ["1"]}],
    )
    assert len(resp["ResourceTagMappingList"]) == 1
    assert {"Key": "Test", "Value": "1"} in resp["ResourceTagMappingList"][0]["Tags"]


@mock_aws
def test_get_resources_workspace_images():
    workspaces = boto3.client("workspaces", region_name="eu-central-1")

    # Create two tagged Workspace Images
    directory_id = create_directory()
    workspaces.register_workspace_directory(DirectoryId=directory_id)
    resp = workspaces.create_workspaces(
        Workspaces=[
            {
                "DirectoryId": directory_id,
                "UserName": "Administrator",
                "BundleId": "wsb-bh8rsxt14",
            },
        ]
    )
    workspace_id = resp["PendingRequests"][0]["WorkspaceId"]
    for i in range(1, 3):
        i_str = str(i)
        _ = workspaces.create_workspace_image(
            Name=f"test-image-{i_str}",
            Description="Test workspace image",
            WorkspaceId=workspace_id,
            Tags=[{"Key": "Test", "Value": i_str}],
        )
    rtapi = boto3.client("resourcegroupstaggingapi", region_name="eu-central-1")

    # Basic test
    resp = rtapi.get_resources(ResourceTypeFilters=["workspaces-image"])
    assert len(resp["ResourceTagMappingList"]) == 2

    # Test tag filtering
    resp = rtapi.get_resources(
        ResourceTypeFilters=["workspaces-image"],
        TagFilters=[{"Key": "Test", "Values": ["1"]}],
    )
    assert len(resp["ResourceTagMappingList"]) == 1
    assert {"Key": "Test", "Value": "1"} in resp["ResourceTagMappingList"][0]["Tags"]


@mock_aws
def test_get_resources_sns():
    sns = boto3.client("sns", region_name="us-east-1")

    sns.create_topic(Name="test", Tags=[{"Key": "Shape", "Value": "Square"}])

    rtapi = boto3.client("resourcegroupstaggingapi", region_name="us-east-1")
    resp = rtapi.get_resources(ResourceTypeFilters=["sns"])

    assert len(resp["ResourceTagMappingList"]) == 1
    assert {"Key": "Shape", "Value": "Square"} in resp["ResourceTagMappingList"][0][
        "Tags"
    ]


@mock_aws
def test_get_resources_ssm():
    import yaml

    from tests.test_ssm.test_ssm_docs import _get_yaml_template

    template_file = _get_yaml_template()
    json_doc = yaml.safe_load(template_file)

    ssm = boto3.client("ssm", region_name="us-east-1")
    ssm.create_document(
        Content=json.dumps(json_doc),
        Name="TestDocument",
        DocumentType="Command",
        DocumentFormat="JSON",
        Tags=[{"Key": "testing", "Value": "testingValue"}],
    )

    rtapi = boto3.client("resourcegroupstaggingapi", region_name="us-east-1")
    resp = rtapi.get_resources(ResourceTypeFilters=["ssm"])

    assert len(resp["ResourceTagMappingList"]) == 1
    assert {"Key": "testing", "Value": "testingValue"} in resp[
        "ResourceTagMappingList"
    ][0]["Tags"]


@mock_aws
def test_tag_resources_for_unknown_service():
    rtapi = boto3.client("resourcegroupstaggingapi", region_name="us-west-2")
    missing_resources = rtapi.tag_resources(
        ResourceARNList=["arn:aws:service_x"], Tags={"key1": "k", "key2": "v"}
    )["FailedResourcesMap"]

    assert "arn:aws:service_x" in missing_resources
    assert (
        missing_resources["arn:aws:service_x"]["ErrorCode"]
        == "InternalServiceException"
    )


@mock_aws
def test_get_resources_elb():
    client = boto3.client("elb", region_name="us-east-1")
    lb_name = "my-lb"
    lb2_name = "second-lb"
    client.create_load_balancer(
        LoadBalancerName=lb_name,
        Listeners=[
            {"Protocol": "tcp", "LoadBalancerPort": 80, "InstancePort": 8080},
            {"Protocol": "http", "LoadBalancerPort": 81, "InstancePort": 9000},
        ],
        Scheme="internal",
    )
    client.add_tags(
        LoadBalancerNames=[lb_name],
        Tags=[
            {"Key": "burger", "Value": "krabby patty"},
        ],
    )
    client.create_load_balancer(
        LoadBalancerName=lb2_name,
        Listeners=[
            {"Protocol": "tcp", "LoadBalancerPort": 80, "InstancePort": 8080},
            {"Protocol": "http", "LoadBalancerPort": 81, "InstancePort": 9000},
        ],
        Scheme="internal",
    )
    client.add_tags(
        LoadBalancerNames=[lb2_name],
        Tags=[
            {"Key": "color", "Value": "blue"},
            {"Key": "shape", "Value": "square"},
        ],
    )
    rgta_client = boto3.client("resourcegroupstaggingapi", region_name="us-east-1")
    resources_no_filter = rgta_client.get_resources(
        ResourceTypeFilters=["elb"],
    )
    assert len(resources_no_filter["ResourceTagMappingList"]) == 2

    resources_burger_filter = rgta_client.get_resources(
        TagFilters=[{"Key": "burger", "Values": ["krabby patty"]}]
    )
    assert len(resources_burger_filter["ResourceTagMappingList"]) == 1
    assert (
        f"arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/{lb_name}"
        == resources_burger_filter["ResourceTagMappingList"][0]["ResourceARN"]
    )


@mock_aws
def test_get_resources_sagemaker_cluster():
    sagemaker = boto3.client("sagemaker", region_name="us-east-1")
    sagemaker.create_cluster(
        ClusterName="testcluster",
        InstanceGroups=[
            {
                "InstanceCount": 10,
                "InstanceGroupName": "testgroup",
                "InstanceType": "ml.p4d.24xlarge",
                "LifeCycleConfig": {
                    "SourceS3Uri": "s3://sagemaker-lifecycleconfig",
                    "OnCreate": "filename",
                },
                "ExecutionRole": "arn:aws:iam::123456789012:role/service-role/AmazonSageMaker-TestExecutionRole",
                "ThreadsPerCore": 2,
            },
            {
                "InstanceCount": 15,
                "InstanceGroupName": "testgroup2",
                "InstanceType": "ml.g5.8xlarge",
                "LifeCycleConfig": {
                    "SourceS3Uri": "s3://sagemaker-lifecycleconfig2",
                    "OnCreate": "filename",
                },
                "ExecutionRole": "arn:aws:iam::123456789012:role/service-role/AmazonSageMaker-TestExecutionRole",
                "ThreadsPerCore": 1,
            },
        ],
        VpcConfig={
            "SecurityGroupIds": [
                "sg-12345678901234567",
            ],
            "Subnets": [
                "subnet-12345678901234567",
            ],
        },
        Tags=[
            {"Key": "sagemakerkey", "Value": "sagemakervalue"},
        ],
    )

    rtapi = boto3.client("resourcegroupstaggingapi", region_name="us-east-1")
    resp = rtapi.get_resources(ResourceTypeFilters=["sagemaker"])

    assert len(resp["ResourceTagMappingList"]) == 1
    assert {"Key": "sagemakerkey", "Value": "sagemakervalue"} in resp[
        "ResourceTagMappingList"
    ][0]["Tags"]


@mock_aws
def test_get_resources_sagemaker_automljob():
    sagemaker = boto3.client("sagemaker", region_name="us-east-1")
    sagemaker.create_auto_ml_job_v2(
        AutoMLJobName="testautomljob",
        AutoMLJobInputDataConfig=[
            {
                "ChannelType": "training",
                "ContentType": "ContentType",
                "CompressionType": "None",
                "DataSource": {
                    "S3DataSource": {"S3DataType": "S3Prefix", "S3Uri": "s3://data"}
                },
            },
        ],
        OutputDataConfig={"KmsKeyId": "kms", "S3OutputPath": "s3://output"},
        AutoMLProblemTypeConfig={
            "ImageClassificationJobConfig": {
                "CompletionCriteria": {
                    "MaxCandidates": 123,
                    "MaxRuntimePerTrainingJobInSeconds": 123,
                    "MaxAutoMLJobRuntimeInSeconds": 123,
                }
            },
        },
        RoleArn="arn:aws:iam::123456789012:role/FakeRole",
        Tags=[
            {"Key": "sagemakerkey", "Value": "sagemakervalue"},
        ],
    )

    rtapi = boto3.client("resourcegroupstaggingapi", region_name="us-east-1")
    resp = rtapi.get_resources(ResourceTypeFilters=["sagemaker"])

    assert len(resp["ResourceTagMappingList"]) == 1
    assert {"Key": "sagemakerkey", "Value": "sagemakervalue"} in resp[
        "ResourceTagMappingList"
    ][0]["Tags"]


@mock_aws
def test_tag_resources_sagemaker():
    sagemaker = boto3.client("sagemaker", region_name="us-east-1")
    rtapi = boto3.client("resourcegroupstaggingapi", region_name="us-east-1")
    resp = sagemaker.create_cluster(
        ClusterName="testcluster",
        InstanceGroups=[
            {
                "InstanceCount": 10,
                "InstanceGroupName": "testgroup",
                "InstanceType": "ml.p4d.24xlarge",
                "LifeCycleConfig": {
                    "SourceS3Uri": "s3://sagemaker-lifecycleconfig",
                    "OnCreate": "filename",
                },
                "ExecutionRole": "arn:aws:iam::123456789012:role/service-role/AmazonSageMaker-TestExecutionRole",
                "ThreadsPerCore": 2,
            },
        ],
        Tags=[
            {"Key": "sagemakerkey", "Value": "sagemakervalue"},
        ],
    )
    rtapi.tag_resources(
        ResourceARNList=[resp["ClusterArn"]], Tags={"key1": "k", "key2": "v"}
    )

    assert sagemaker.list_tags(ResourceArn=resp["ClusterArn"])["Tags"] == [
        {"Key": "sagemakerkey", "Value": "sagemakervalue"},
        {"Key": "key1", "Value": "k"},
        {"Key": "key2", "Value": "v"},
    ]


@mock_aws
def test_get_resources_efs():
    client = boto3.client("resourcegroupstaggingapi", region_name="us-east-1")
    efs = boto3.client("efs", region_name="us-east-1")
    # elasticfilesystem:file-system
    fs_one = efs.create_file_system(
        CreationToken="test-token-1", Tags=[{"Key": "tag", "Value": "a tag"}]
    )
    fs_two = efs.create_file_system(
        CreationToken="test-token-2", Tags=[{"Key": "tag", "Value": "b tag"}]
    )
    resp = client.get_resources(ResourceTypeFilters=["elasticfilesystem:file-system"])
    assert len(resp["ResourceTagMappingList"]) == 2
    resp = client.get_resources(
        ResourceTypeFilters=["elasticfilesystem:file-system"],
        TagFilters=[{"Key": "tag", "Values": ["a tag"]}],
    )
    assert len(resp["ResourceTagMappingList"]) == 1
    returned_arns = [i["ResourceARN"] for i in resp["ResourceTagMappingList"]]
    assert fs_one["FileSystemArn"] in returned_arns
    assert fs_two["FileSystemArn"] not in returned_arns

    # elasticfilesystem:access-point
    ap_one = efs.create_access_point(
        ClientToken="ct-1",
        FileSystemId=fs_one["FileSystemId"],
        Tags=[{"Key": "tag", "Value": "a tag"}],
    )
    ap_two = efs.create_access_point(
        ClientToken="ct-2",
        FileSystemId=fs_two["FileSystemId"],
        Tags=[{"Key": "tag", "Value": "b tag"}],
    )
    resp = client.get_resources(ResourceTypeFilters=["elasticfilesystem:access-point"])
    assert len(resp["ResourceTagMappingList"]) == 2
    resp = client.get_resources(
        ResourceTypeFilters=["elasticfilesystem:access-point"],
        TagFilters=[{"Key": "tag", "Values": ["a tag"]}],
    )
    assert len(resp["ResourceTagMappingList"]) == 1
    returned_arns = [i["ResourceARN"] for i in resp["ResourceTagMappingList"]]
    assert ap_one["AccessPointArn"] in returned_arns
    assert ap_two["AccessPointArn"] not in returned_arns

    resp = client.get_resources(ResourceTypeFilters=["elasticfilesystem"])
    assert len(resp["ResourceTagMappingList"]) == 4
    resp = client.get_resources(
        ResourceTypeFilters=["elasticfilesystem"],
        TagFilters=[{"Key": "tag", "Values": ["b tag"]}],
    )
    assert len(resp["ResourceTagMappingList"]) == 2
    returned_arns = [i["ResourceARN"] for i in resp["ResourceTagMappingList"]]
    assert fs_one["FileSystemArn"] not in returned_arns
    assert fs_two["FileSystemArn"] in returned_arns
    assert ap_one["AccessPointArn"] not in returned_arns
    assert ap_two["AccessPointArn"] in returned_arns


@mock_aws
def test_get_resources_stepfunction():
    simple_definition = (
        '{"Comment": "An example of the Amazon States Language using a choice state.",'
        '"StartAt": "DefaultState",'
        '"States": '
        '{"DefaultState": {"Type": "Fail","Error": "DefaultStateError","Cause": "No Matches!"}}}'
    )
    role_arn = "arn:aws:iam::" + ACCOUNT_ID + ":role/unknown_sf_role"

    client = boto3.client("stepfunctions", region_name="us-east-1")
    client.create_state_machine(
        name="name1",
        definition=str(simple_definition),
        roleArn=role_arn,
        tags=[{"key": "Name", "value": "Alice"}],
    )

    rtapi = boto3.client("resourcegroupstaggingapi", region_name="us-east-1")
    resp = rtapi.get_resources(ResourceTypeFilters=["states:stateMachine"])

    assert len(resp["ResourceTagMappingList"]) == 1
    assert {"Key": "Name", "Value": "Alice"} in resp["ResourceTagMappingList"][0][
        "Tags"
    ]


@mock_aws
def test_get_resources_workspacesweb():
    ww_client = boto3.client("workspaces-web", region_name="ap-southeast-1")
    arn = ww_client.create_portal(
        additionalEncryptionContext={"Key1": "Encryption", "Key2": "Context"},
        authenticationType="Standard",
        clientToken="TestClient",
        customerManagedKey="abcd1234-5678-90ab-cdef-FAKEKEY",
        displayName="TestDisplayName",
        instanceType="TestInstanceType",
        maxConcurrentSessions=5,
        tags=[
            {"Key": "TestKey", "Value": "TestValue"},
            {"Key": "TestKey2", "Value": "TestValue2"},
        ],
    )["portalArn"]
    rtapi = boto3.client("resourcegroupstaggingapi", region_name="ap-southeast-1")
    resp = rtapi.get_resources(ResourceTypeFilters=["workspaces-web"])
    assert len(resp["ResourceTagMappingList"]) == 1
    assert {"Key": "TestKey", "Value": "TestValue"} in resp["ResourceTagMappingList"][
        0
    ]["Tags"]
    resp = rtapi.get_resources(
        ResourceTypeFilters=["workspaces-web"],
        TagFilters=[{"Key": "TestKey3", "Values": ["TestValue3"]}],
    )
    assert len(resp["ResourceTagMappingList"]) == 0
    ww_client.tag_resource(
        resourceArn=arn, tags=[{"Key": "TestKey3", "Value": "TestValue3"}]
    )
    resp = rtapi.get_resources(
        ResourceTypeFilters=["workspaces-web"],
        TagFilters=[{"Key": "TestKey3", "Values": ["TestValue3"]}],
    )
    assert len(resp["ResourceTagMappingList"]) == 1


@pytest.mark.parametrize("resource_type", ["secretsmanager", "secretsmanager:secret"])
@mock_aws
def test_get_resources_secretsmanager(resource_type):
    def assert_tagging_works(region_name: str, regional_response_keys: typing.Set[str]):
        rtapi = boto3.client("resourcegroupstaggingapi", region_name=region_name)
        resp = rtapi.get_resources(
            ResourcesPerPage=2, ResourceTypeFilters=[resource_type]
        )
        for resource in resp["ResourceTagMappingList"]:
            regional_response_keys.remove(resource["Tags"][0]["Key"])

        assert len(regional_response_keys) == 2

        resp = rtapi.get_resources(
            ResourcesPerPage=2,
            PaginationToken=resp["PaginationToken"],
            ResourceTypeFilters=[resource_type],
        )
        for resource in resp["ResourceTagMappingList"]:
            regional_response_keys.remove(resource["Tags"][0]["Key"])

        assert len(regional_response_keys) == 0

    # Tests pagination
    secretsmanager_client = boto3.client("secretsmanager", region_name="eu-central-1")

    # Will end up having key1,key2,key3,key4
    response_keys = set()

    # Create 4 tagged secrets
    for i in range(1, 5):
        i_str = str(i)
        secretsmanager_client.create_secret(
            Name="test_secret" + i_str,
            SecretString="very_secret",
            AddReplicaRegions=[{"Region": "eu-west-1"}],
        )
        secretsmanager_client.tag_resource(
            SecretId="test_secret" + i_str,
            Tags=[{"Key": "key" + i_str, "Value": "value" + i_str}],
        )
        response_keys.add("key" + i_str)

    # add an untagged secret to cover this case as well
    secretsmanager_client: secretsmanager_client.create_secret(
        Name="untagged_secret",
        SecretString="very_secret",
        AddReplicaRegions=[{"Region": "eu-west-1"}],
    )

    # Make sure it works for normal and replicated secrets
    assert_tagging_works("eu-central-1", set(response_keys))
    assert_tagging_works("eu-west-1", set(response_keys))
