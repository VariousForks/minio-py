# -*- coding: utf-8 -*-
# MinIO Python Library for Amazon S3 Compatible Cloud Storage, (C)
# 2015, 2016, 2017, 2018, 2019 MinIO, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
minio.xml_marshal
~~~~~~~~~~~~~~~

This module contains the simple wrappers for XML marshaller's.

:copyright: (c) 2015 by MinIO, Inc.
:license: Apache 2.0, see LICENSE for more details.

"""

from __future__ import absolute_import
import io

import xml.etree.ElementTree as ET
from collections import defaultdict

_S3_NAMESPACE = 'http://s3.amazonaws.com/doc/2006-03-01/'


def Element(tag, with_namespace=False):
    if with_namespace:
        return ET.Element(tag, {'xmlns': _S3_NAMESPACE})
    return ET.Element(tag)


def SubElement(parent, tag, text=None):
    subElement = ET.SubElement(parent, tag)
    if text is not None:
        subElement.text = text
    return subElement


def get_xml_data(element):
    data = io.BytesIO()
    ET.ElementTree(element).write(data, encoding=None, xml_declaration=False)
    return data.getvalue()


def xml_to_dict(in_xml):
    # Converts xml to dict
    elem = ET.XML(in_xml)
    return etree_to_dict(elem)


def etree_to_dict(elem):
    # Converts ElementTree object to dict
    ns = '{' + _S3_NAMESPACE + '}'
    elem.tag = elem.tag.replace(ns, '')

    d = {elem.tag: {} if elem.attrib else None}
    children = list(elem)
    if children:
        dd = defaultdict(list)
        if children[0].tag.replace(ns, '') == 'Rule':
            for dc in map(etree_to_dict, children):
                for k, v in dc.items():
                    dd[k].append([v])
        else:
            for dc in map(etree_to_dict, children):
                for k, v in dc.items():
                    dd[k].append(v)
        d = {elem.tag: {k: v[0] if len(v) == 1 else v for k, v in dd.items()}}
    if elem.attrib:
        d[elem.tag].update(('@' + k, v) for k, v in elem.attrib.items())
    if elem.text:
        text = elem.text.strip()
        if children or elem.attrib:
            if text:
                d[elem.tag]['#text'] = text
        else:
            d[elem.tag] = text
    return d


def xml_marshal_bucket_encryption(rules):
    root = Element('ServerSideEncryptionConfiguration')

    if rules:
        # As server supports only one rule, the first rule is taken due to
        # no validation is done at server side.
        apply_element = SubElement(SubElement(root, 'Rule'),
                                   'ApplyServerSideEncryptionByDefault')
        SubElement(apply_element, 'SSEAlgorithm',
                   rules[0]['ApplyServerSideEncryptionByDefault'].get(
                       'SSEAlgorithm', 'AES256'))
        kms_text = rules[0]['ApplyServerSideEncryptionByDefault'].get(
            'KMSMasterKeyID')
        if kms_text:
            SubElement(apply_element, 'KMSMasterKeyID', kms_text)

    return get_xml_data(root)


def xml_marshal_bucket_constraint(region):
    """
    Marshal's bucket constraint based on *region*.

    :param region: Region name of a given bucket.
    :return: Marshalled XML data.
    """
    root = Element('CreateBucketConfiguration', with_namespace=True)
    SubElement(root, 'LocationConstraint', region)
    return get_xml_data(root)


def xml_marshal_select(opts):
    root = Element('SelectObjectContentRequest')
    SubElement(root, 'Expression', opts.expression)
    SubElement(root, 'ExpressionType', 'SQL')

    input_serialization = SubElement(root, 'InputSerialization')
    SubElement(input_serialization, 'CompressionType',
               opts.in_ser.compression_type)

    if opts.in_ser.csv_input:
        csv = SubElement(input_serialization, 'CSV')
        SubElement(csv, 'FileHeaderInfo', opts.in_ser.csv_input.FileHeaderInfo)
        SubElement(csv, 'RecordDelimiter',
                   opts.in_ser.csv_input.RecordDelimiter)
        SubElement(csv, 'FieldDelimiter', opts.in_ser.csv_input.FieldDelimiter)
        SubElement(csv, 'QuoteCharacter', opts.in_ser.csv_input.QuoteCharacter)
        SubElement(csv, 'QuoteEscapeCharacter',
                   opts.in_ser.csv_input.QuoteEscapeCharacter)
        SubElement(csv, 'Comments', opts.in_ser.csv_input.Comments)
        SubElement(csv, 'AllowQuotedRecordDelimiter',
                   opts.in_ser.csv_input.AllowQuotedRecordDelimiter.lower())

    if opts.in_ser.json_input:
        SubElement(SubElement(input_serialization, 'JSON'), 'Type',
                   opts.in_ser.json_input.Type)

    if opts.in_ser.parquet_input:
        SubElement(input_serialization, 'Parquet')

    output_serialization = SubElement(root, 'OutputSerialization')
    if opts.out_ser.csv_output:
        csv = SubElement(output_serialization, 'CSV')
        SubElement(csv, 'QuoteFields', opts.out_ser.csv_output.QuoteFields)
        SubElement(csv, 'RecordDelimiter',
                   opts.out_ser.csv_output.RecordDelimiter)
        SubElement(csv, 'FieldDelimiter',
                   opts.out_ser.csv_output.FieldDelimiter)
        SubElement(csv, 'QuoteCharacter',
                   opts.out_ser.csv_output.QuoteCharacter)
        SubElement(csv, 'QuoteEscapeCharacter',
                   opts.out_ser.csv_output.QuoteEscapeCharacter)

    if opts.out_ser.json_output:
        SubElement(SubElement(output_serialization, 'JSON'), 'RecordDelimiter',
                   opts.out_ser.json_output.RecordDelimiter)

    SubElement(SubElement(root, 'RequestProgress'), 'Enabled',
               opts.req_progress.enabled.lower())

    return get_xml_data(root)


def xml_marshal_complete_multipart_upload(uploaded_parts):
    """
    Marshal's complete multipart upload request based on *uploaded_parts*.

    :param uploaded_parts: List of all uploaded parts, ordered by part number.
    :return: Marshalled XML data.
    """
    root = Element('CompleteMultipartUpload', with_namespace=True)
    for uploaded_part in uploaded_parts:
        part = SubElement(root, 'Part')
        SubElement(part, 'PartNumber', str(uploaded_part.part_number))
        SubElement(part, 'ETag', '"' + uploaded_part.etag + '"')

    return get_xml_data(root)


def xml_marshal_bucket_notifications(notifications):
    """
    Marshals the notifications structure for sending to S3 compatible storage

    :param notifications: Dictionary with following structure:

    {
        'TopicConfigurations': [
            {
                'Id': 'string',
                'Arn': 'string',
                'Events': [
                    's3:ReducedRedundancyLostObject'|'s3:ObjectCreated:*'|'s3:ObjectCreated:Put'|'s3:ObjectCreated:Post'|'s3:ObjectCreated:Copy'|'s3:ObjectCreated:CompleteMultipartUpload'|'s3:ObjectRemoved:*'|'s3:ObjectRemoved:Delete'|'s3:ObjectRemoved:DeleteMarkerCreated',
                ],
                'Filter': {
                    'Key': {
                        'FilterRules': [
                            {
                                'Name': 'prefix'|'suffix',
                                'Value': 'string'
                            },
                        ]
                    }
                }
            },
        ],
        'QueueConfigurations': [
            {
                'Id': 'string',
                'Arn': 'string',
                'Events': [
                    's3:ReducedRedundancyLostObject'|'s3:ObjectCreated:*'|'s3:ObjectCreated:Put'|'s3:ObjectCreated:Post'|'s3:ObjectCreated:Copy'|'s3:ObjectCreated:CompleteMultipartUpload'|'s3:ObjectRemoved:*'|'s3:ObjectRemoved:Delete'|'s3:ObjectRemoved:DeleteMarkerCreated',
                ],
                'Filter': {
                    'Key': {
                        'FilterRules': [
                            {
                                'Name': 'prefix'|'suffix',
                                'Value': 'string'
                            },
                        ]
                    }
                }
            },
        ],
        'CloudFunctionConfigurations': [
            {
                'Id': 'string',
                'Arn': 'string',
                'Events': [
                    's3:ReducedRedundancyLostObject'|'s3:ObjectCreated:*'|'s3:ObjectCreated:Put'|'s3:ObjectCreated:Post'|'s3:ObjectCreated:Copy'|'s3:ObjectCreated:CompleteMultipartUpload'|'s3:ObjectRemoved:*'|'s3:ObjectRemoved:Delete'|'s3:ObjectRemoved:DeleteMarkerCreated',
                ],
                'Filter': {
                    'Key': {
                        'FilterRules': [
                            {
                                'Name': 'prefix'|'suffix',
                                'Value': 'string'
                            },
                        ]
                    }
                }
            },
        ]
    }

    :return: Marshalled XML data
    """
    root = Element('NotificationConfiguration', with_namespace=True)
    _add_notification_config_to_xml(
        root,
        'TopicConfiguration',
        notifications.get('TopicConfigurations', [])
    )
    _add_notification_config_to_xml(
        root,
        'QueueConfiguration',
        notifications.get('QueueConfigurations', [])
    )
    _add_notification_config_to_xml(
        root,
        'CloudFunctionConfiguration',
        notifications.get('CloudFunctionConfigurations', [])
    )

    return get_xml_data(root)


NOTIFICATIONS_ARN_FIELDNAME_MAP = {
    'TopicConfiguration': 'Topic',
    'QueueConfiguration': 'Queue',
    'CloudFunctionConfiguration': 'CloudFunction',
}


def _add_notification_config_to_xml(node, element_name, configs):
    """
    Internal function that builds the XML sub-structure for a given
    kind of notification configuration.

    """
    for config in configs:
        config_node = SubElement(node, element_name)

        if 'Id' in config:
            SubElement(config_node, 'Id', config['Id'])

        SubElement(config_node, NOTIFICATIONS_ARN_FIELDNAME_MAP[element_name],
                   config['Arn'])

        for event in config['Events']:
            SubElement(config_node, 'Event', event)

        filter_rules = config.get('Filter', {}).get(
            'Key', {}).get('FilterRules', [])
        if filter_rules:
            s3key_node = SubElement(SubElement(config_node, 'Filter'), 'S3Key')
            for filter_rule in filter_rules:
                filter_rule_node = SubElement(s3key_node, 'FilterRule')
                SubElement(filter_rule_node, 'Name', filter_rule['Name'])
                SubElement(filter_rule_node, 'Value', filter_rule['Value'])
    return node


def xml_marshal_delete_objects(object_names):
    """
    Marshal Multi-Object Delete request body from object names.

    :param object_names: List of object keys to be deleted.
    :return: Serialized XML string for multi-object delete request body.
    """
    root = Element('Delete')

    # use quiet mode in the request - this causes the S3 Server to
    # limit its response to only object keys that had errors during
    # the delete operation.
    SubElement(root, 'Quiet', "true")

    # add each object to the request.
    for object_name in object_names:
        SubElement(SubElement(root, 'Object'), 'Key', object_name)

    return get_xml_data(root)
