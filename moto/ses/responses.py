import base64
from typing import Any, Dict, List, Optional

from moto.core.responses import ActionResult, BaseResponse, EmptyResult
from moto.core.utils import utcnow

from .exceptions import ValidationError
from .models import SESBackend, ses_backends


class EmailResponse(BaseResponse):
    def __init__(self) -> None:
        super().__init__(service_name="ses")
        self.automated_parameter_parsing = True

    @property
    def backend(self) -> SESBackend:
        return ses_backends[self.current_account][self.region]

    def verify_email_identity(self) -> ActionResult:
        address = self.querystring.get("EmailAddress")[0]  # type: ignore
        self.backend.verify_email_identity(address)
        return EmptyResult()

    def verify_email_address(self) -> ActionResult:
        address = self.querystring.get("EmailAddress")[0]  # type: ignore
        self.backend.verify_email_address(address)
        return EmptyResult()

    def list_identities(self) -> ActionResult:
        identity_type = self._get_param("IdentityType")
        if identity_type not in [None, "EmailAddress", "Domain"]:
            raise ValidationError(
                f"Value '{identity_type}' at 'identityType' failed to satisfy constraint: Member must satisfy enum value set: [Domain, EmailAddress]"
            )
        identities = self.backend.list_identities(identity_type)
        result = {"Identities": identities}
        return ActionResult(result)

    def list_verified_email_addresses(self) -> ActionResult:
        email_addresses = self.backend.list_verified_email_addresses()
        result = {"VerifiedEmailAddresses": email_addresses}
        return ActionResult(result)

    def verify_domain_dkim(self) -> ActionResult:
        domain = self.querystring.get("Domain")[0]  # type: ignore
        self.backend.verify_domain(domain)
        result = {
            "DkimTokens": [
                "vvjuipp74whm76gqoni7qmwwn4w4qusjiainivf6sf",
                "3frqe7jn4obpuxjpwpolz6ipb3k5nvt2nhjpik2oy",
                "wrqplteh7oodxnad7hsl4mixg2uavzneazxv5sxi2",
            ]
        }
        return ActionResult(result)

    def verify_domain_identity(self) -> ActionResult:
        domain = self.querystring.get("Domain")[0]  # type: ignore
        self.backend.verify_domain(domain)
        result = {"VerificationToken": "QTKknzFg2J4ygwa+XvHAxUl1hyHoY0gVfZdfjIedHZ0="}
        return ActionResult(result)

    def delete_identity(self) -> ActionResult:
        domain = self.querystring.get("Identity")[0]  # type: ignore
        self.backend.delete_identity(domain)
        return EmptyResult()

    def send_email(self) -> ActionResult:
        bodydatakey = "Message.Body.Text.Data"
        if "Message.Body.Html.Data" in self.querystring:
            bodydatakey = "Message.Body.Html.Data"
        body = self.querystring.get(bodydatakey)[0]  # type: ignore
        source = self.querystring.get("Source")[0]  # type: ignore
        subject = self.querystring.get("Message.Subject.Data")[0]  # type: ignore
        destinations = self.params.get("Destination", {})
        message = self.backend.send_email(source, subject, body, destinations)
        result = {"MessageId": message.id}
        return ActionResult(result)

    def send_templated_email(self) -> ActionResult:
        source = self.querystring.get("Source")[0]  # type: ignore
        template: List[str] = self.querystring.get("Template")  # type: ignore
        template_data: List[str] = self.querystring.get("TemplateData")  # type: ignore
        destinations = self.params.get("Destination", {})
        message = self.backend.send_templated_email(
            source, template, template_data, destinations
        )
        result = {"MessageId": message.id}
        return ActionResult(result)

    def send_bulk_templated_email(self) -> ActionResult:
        source = self.querystring.get("Source")[0]  # type: ignore
        template = self.querystring.get("Template")
        template_data = self.querystring.get("DefaultTemplateData")
        destinations = self.params.get("Destinations", [])
        message = self.backend.send_bulk_templated_email(
            source,
            template,  # type: ignore
            template_data,  # type: ignore
            destinations,
        )
        result = {"Status": [{"MessageId": msg_id} for msg_id in message.ids]}
        return ActionResult(result)

    def send_raw_email(self) -> ActionResult:
        source = self.querystring.get("Source")
        if source is not None:
            (source,) = source

        raw_data = self.querystring.get("RawMessage.Data")[0]  # type: ignore
        raw_data = base64.b64decode(raw_data)
        raw_data = raw_data.decode("utf-8")
        destinations = self.params.get("Destinations", [])
        message = self.backend.send_raw_email(source, destinations, raw_data)  # type: ignore[arg-type]
        result = {"MessageId": message.id}
        return ActionResult(result)

    def get_send_quota(self) -> ActionResult:
        quota = self.backend.get_send_quota()
        return ActionResult(quota)

    def get_identity_notification_attributes(self) -> ActionResult:
        identities = self._get_params()["Identities"]
        identities = self.backend.get_identity_notification_attributes(identities)
        result = {"NotificationAttributes": identities}
        return ActionResult(result)

    def set_identity_feedback_forwarding_enabled(self) -> ActionResult:
        identity = self._get_param("Identity")
        enabled = self._get_bool_param("ForwardingEnabled")
        self.backend.set_identity_feedback_forwarding_enabled(identity, enabled)
        return EmptyResult()

    def set_identity_notification_topic(self) -> ActionResult:
        identity = self.querystring.get("Identity")[0]  # type: ignore
        not_type = self.querystring.get("NotificationType")[0]  # type: ignore
        sns_topic = self.querystring.get("SnsTopic")
        if sns_topic:
            sns_topic = sns_topic[0]
        self.backend.set_identity_notification_topic(identity, not_type, sns_topic)
        return EmptyResult()

    def get_send_statistics(self) -> ActionResult:
        statistics = self.backend.get_send_statistics()
        result = {"SendDataPoints": [statistics]}
        return ActionResult(result)

    def create_configuration_set(self) -> ActionResult:
        configuration_set_name = self.querystring.get("ConfigurationSet.Name")[0]  # type: ignore
        self.backend.create_configuration_set(
            configuration_set_name=configuration_set_name
        )
        return EmptyResult()

    def describe_configuration_set(self) -> ActionResult:
        configuration_set_name = self.querystring.get("ConfigurationSetName")[0]  # type: ignore
        config_set = self.backend.describe_configuration_set(configuration_set_name)

        attribute_names = self._get_multi_param(
            "ConfigurationSetAttributeNames.member."
        )

        event_destination: Optional[Dict[str, Any]] = None
        if "eventDestinations" in attribute_names:
            event_destination = self.backend.config_set_event_destination.get(
                configuration_set_name
            )

        result = {
            "ConfigurationSet": {"Name": config_set.configuration_set_name},
            "EventDestinations": [event_destination],
        }
        return ActionResult(result)

    def create_configuration_set_event_destination(self) -> ActionResult:
        configuration_set_name = self._get_param("ConfigurationSetName")
        event_destination = self._get_params().get("EventDestination", {})
        self.backend.create_configuration_set_event_destination(
            configuration_set_name=configuration_set_name,
            event_destination=event_destination,
        )
        return EmptyResult()

    def create_template(self) -> ActionResult:
        template_data = self._get_dict_param("Template")
        template_info = {}
        template_info["text_part"] = template_data.get("._text_part", "")
        template_info["html_part"] = template_data.get("._html_part", "")
        template_info["template_name"] = template_data.get("._name", "")
        template_info["subject_part"] = template_data.get("._subject_part", "")
        template_info["Timestamp"] = utcnow()
        self.backend.add_template(template_info=template_info)
        return EmptyResult()

    def update_template(self) -> ActionResult:
        template_data = self._get_dict_param("Template")
        template_info = {}
        template_info["text_part"] = template_data.get("._text_part", "")
        template_info["html_part"] = template_data.get("._html_part", "")
        template_info["template_name"] = template_data.get("._name", "")
        template_info["subject_part"] = template_data.get("._subject_part", "")
        template_info["Timestamp"] = utcnow()
        self.backend.update_template(template_info=template_info)
        return EmptyResult()

    def get_template(self) -> ActionResult:
        template_name = self._get_param("TemplateName")
        template_data = self.backend.get_template(template_name)
        result = {"Template": template_data}
        return ActionResult(result)

    def list_templates(self) -> ActionResult:
        email_templates = self.backend.list_templates()
        metadata = [
            {"Name": t["template_name"], "CreatedTimestamp": t["Timestamp"]}
            for t in email_templates
        ]
        result = {"TemplatesMetadata": metadata}
        return ActionResult(result)

    def test_render_template(self) -> ActionResult:
        render_info = self._get_dict_param("Template")
        rendered_template = self.backend.render_template(render_info)
        result = {"RenderedTemplate": rendered_template}
        return ActionResult(result)

    def delete_template(self) -> ActionResult:
        name = self._get_param("TemplateName")
        self.backend.delete_template(name)
        return EmptyResult()

    def create_receipt_rule_set(self) -> ActionResult:
        rule_set_name = self._get_param("RuleSetName")
        self.backend.create_receipt_rule_set(rule_set_name)
        return EmptyResult()

    def create_receipt_rule(self) -> ActionResult:
        params = self._get_params()
        rule_set_name = params.get("RuleSetName", "")
        rule = params.get("Rule", {})
        self.backend.create_receipt_rule(rule_set_name, rule)
        return EmptyResult()

    def describe_receipt_rule_set(self) -> ActionResult:
        rule_set_name = self._get_param("RuleSetName")
        rule_set = self.backend.describe_receipt_rule_set(rule_set_name)
        result = {"Metadata": {"Name": rule_set_name}, "Rules": rule_set}
        return ActionResult(result)

    def describe_receipt_rule(self) -> ActionResult:
        rule_set_name = self._get_param("RuleSetName")
        rule_name = self._get_param("RuleName")
        receipt_rule = self.backend.describe_receipt_rule(rule_set_name, rule_name)
        result = {"Rule": receipt_rule}
        return ActionResult(result)

    def update_receipt_rule(self) -> ActionResult:
        params = self._get_params()
        rule_set_name = params.get("RuleSetName", "")
        rule = params.get("Rule", {})
        self.backend.update_receipt_rule(rule_set_name, rule)
        return EmptyResult()

    def set_identity_mail_from_domain(self) -> ActionResult:
        identity = self._get_param("Identity")
        mail_from_domain = self._get_param("MailFromDomain")
        behavior_on_mx_failure = self._get_param("BehaviorOnMXFailure")

        self.backend.set_identity_mail_from_domain(
            identity, mail_from_domain, behavior_on_mx_failure
        )
        return EmptyResult()

    def get_identity_mail_from_domain_attributes(self) -> ActionResult:
        identities = self._get_multi_param("Identities.member.")
        attributes_by_identity = self.backend.get_identity_mail_from_domain_attributes(
            identities
        )
        result = {"MailFromDomainAttributes": attributes_by_identity}
        return ActionResult(result)

    def get_identity_verification_attributes(self) -> ActionResult:
        params = self._get_params()
        identities = params.get("Identities")
        verification_attributes = self.backend.get_identity_verification_attributes(
            identities=identities,
        )
        result = {"VerificationAttributes": verification_attributes}
        return ActionResult(result)

    def delete_configuration_set(self) -> ActionResult:
        params = self._get_params()
        configuration_set_name = params.get("ConfigurationSetName")
        self.backend.delete_configuration_set(
            configuration_set_name=str(configuration_set_name)
        )
        return EmptyResult()

    def list_configuration_sets(self) -> ActionResult:
        params = self._get_params()
        next_token = params.get("NextToken")
        max_items = params.get("MaxItems")
        configuration_sets, next_token = self.backend.list_configuration_sets(
            next_token=next_token,
            max_items=max_items,
        )
        config_set_names = [c.configuration_set_name for c in configuration_sets]
        result = {
            "ConfigurationSets": [{"Name": name} for name in config_set_names],
            "NextToken": next_token,
        }
        return ActionResult(result)

    def update_configuration_set_reputation_metrics_enabled(self) -> ActionResult:
        configuration_set_name = self._get_param("ConfigurationSetName")
        enabled = self._get_param("Enabled")
        self.backend.update_configuration_set_reputation_metrics_enabled(
            configuration_set_name=configuration_set_name,
            enabled=enabled,
        )
        return EmptyResult()

    def get_identity_dkim_attributes(self) -> ActionResult:
        identities = self._get_multi_param("Identities.member.")
        dkim_attributes = self.backend.get_identity_dkim_attributes(identities)
        result = {"DkimAttributes": dkim_attributes}
        return ActionResult(result)
