# -*- coding: utf-8 -*-
"""
Copyright (c) 2019 beyond-blockchain.org.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""
import bbc1
import binascii
import datetime
import hashlib
import os
import string
import sys
import time
import xml.etree.ElementTree as ET

from bbc1.core.ethereum import bbc_ethereum
from brownie import *
from flask import render_template, request, redirect, url_for


S_CONTRACT_ADDRESS = '0xd123Ec03ACdbC36e4fA818c983C259049EE705e0'
S_NETWORK = 'ropsten'


def failure_template(dir, reason, root=''):

    return render_template(os.path.join(dir, 'failure.html'),
            title='Certificate Verification - Failure',
            network=S_NETWORK, contract=S_CONTRACT_ADDRESS,
            reason=reason, root=root,
            get_date_string=get_date_string)


def get_date_string(timestamp):

    try:
        s = str(datetime.datetime.fromtimestamp(int(timestamp))).split()

    except ValueError:
        return 'N/A'

    return s[0]


def index(dir):

    cert_xml = request.args.get('certificate')
    subtree_string = request.args.get('subtree')

    if cert_xml is None or subtree_string is None:
        return failure_template(dir, 'no-query')

    try:
        root = ET.fromstring(cert_xml)

    except ET.ParseError:
        return failure_template(dir, 'xml-syntax')

    dat = bytearray()
    for e in root:
        if e.tag == 'digest':
            if all(c in string.hexdigits for c in e.text):
                digest0 = binascii.a2b_hex(e.text)
            else:
                digest0 = bytes()
            dat.extend(digest0)
        else:
            s = ET.tostring(e, encoding='utf-8')
            dat.extend(hashlib.sha256(s).digest())

    digest = hashlib.sha256(bytes(dat)).digest()

    subtree = []
    nodes = subtree_string.split(':')

    for node in nodes:
        s = node.split('-')
        if len(s) != 2 or not all(c in string.hexdigits for c in s[1]):
            return failure_template(dir, 'subtree-syntax', root=root)
        dic = {}
        dic['position'] = 'right' if s[0] == 'r' else 'left'
        dic['digest'] = s[1]
        subtree.append(dic)

    prevdir = os.getcwd()
    os.chdir(bbc1.__path__[0] + '/core/ethereum')

    eth = bbc_ethereum.BBcEthereum(
        S_NETWORK,
        private_key=None,
        contract_address=S_CONTRACT_ADDRESS
    )

    os.chdir(prevdir)

    block_no, digest0 = eth.verify_and_get_root(digest, subtree)

    if block_no <= 0:
        return failure_template(dir, 'digest-mismatch', root=root)

    block = network.web3.eth.getBlock(block_no)

    realtime = datetime.datetime.fromtimestamp(block['timestamp'])

    return render_template(os.path.join(dir, 'success.html'),
            title='Certificate Vefirication - Success',
            root=root, network=S_NETWORK, contract=S_CONTRACT_ADDRESS,
            block_no=block_no, realtime=realtime,
            get_date_string=get_date_string,
            merkle_root=binascii.b2a_hex(digest0).decode())


# end of cert_flask.py