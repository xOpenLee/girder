#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
#  Copyright 2013 Kitware Inc.
#
#  Licensed under the Apache License, Version 2.0 ( the "License" );
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
###############################################################################

import os

from .. import base
from girder.models.model_base import AccessControlledModel, Model, AccessType, AccessException
from girder.utility.acl_mixin import AccessControlMixin
from girder.utility.model_importer import ModelImporter


class FakeAcModel(AccessControlledModel):
    def initialize(self):
        self.name = 'fake_ac'

        self.exposeFields(level=AccessType.READ, fields='read')
        self.exposeFields(level=AccessType.WRITE, fields=('write', 'write2'))
        self.exposeFields(level=AccessType.ADMIN, fields='admin')
        self.exposeFields(level=AccessType.SITE_ADMIN, fields='sa')

    def validate(self, doc):
        return doc


class FakeModel(Model):
    def initialize(self):
        self.name = 'fake'

        self.exposeFields(level=AccessType.READ, fields='read')
        self.exposeFields(level=AccessType.SITE_ADMIN, fields='sa')

    def validate(self, doc):
        return doc


class FakeAcMixinModel(AccessControlMixin, Model):
    def initialize(self):
        self.name = 'fake_ac_mixin'
        self.resourceColl = 'fake_ac'
        self.resourceParent = 'fakeParentId'

    def validate(self, doc):
        return doc


class FakeAttachedModel(AccessControlMixin, Model):
    def initialize(self):
        self.name = 'fake_attached'

    def validate(self, doc):
        return doc


def setUpModule():
    base.mockPluginDir(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'test_plugins'))
    base.enabledPlugins.append('has_model')

    base.startServer()


def tearDownModule():
    base.stopServer()


class ModelTestCase(base.TestCase):
    """
    Unit test the model-related functionality and utilities.
    """
    def setUp(self):
        base.TestCase.setUp(self)

        ModelImporter.registerModel('fake_ac', FakeAcModel())
        ModelImporter.registerModel('fake', FakeModel())
        ModelImporter.registerModel('fake_ac_mixin', FakeAcMixinModel())
        ModelImporter.registerModel('fake_attached', FakeAttachedModel())

    def testModelFiltering(self):
        users = ({
            'email': 'good@email.com',
            'login': 'goodlogin',
            'firstName': 'First',
            'lastName': 'Last',
            'password': 'goodpassword'
        }, {
            'email': 'regularuser@email.com',
            'login': 'regularuser',
            'firstName': 'First',
            'lastName': 'Last',
            'password': 'goodpassword'
        })
        adminUser, regUser = [
            self.model('user').createUser(**user) for user in users]

        fields = {
            'hidden': 1,
            'read': 1,
            'write': 1,
            'write2': 1,
            'admin': 1,
            'sa': 1
        }
        # Test filter behavior on access controlled model
        fakeAc = self.model('fake_ac').save(fields)
        fakeAc = self.model('fake_ac').setUserAccess(
            fakeAc, regUser, level=AccessType.READ)

        filtered = self.model('fake_ac').filter(fakeAc, adminUser)
        self.assertTrue('sa' in filtered)
        self.assertTrue('write' in filtered)
        self.assertFalse('hidden' in filtered)

        self.model('fake_ac').exposeFields(
            level=AccessType.READ, fields='hidden')

        filtered = self.model('fake_ac').filter(fakeAc, regUser)
        self.assertTrue('hidden' in filtered)
        self.assertTrue('read' in filtered)
        self.assertFalse('write' in filtered)
        self.assertFalse('admin' in filtered)
        self.assertFalse('sa' in filtered)

        self.model('fake_ac').hideFields(level=AccessType.READ, fields='read')

        fakeAc = self.model('fake_ac').setUserAccess(
            fakeAc, regUser, level=AccessType.ADMIN)

        filtered = self.model('fake_ac').filter(fakeAc, regUser)
        self.assertTrue('hidden' in filtered)
        self.assertTrue('write' in filtered)
        self.assertTrue('admin' in filtered)
        self.assertFalse('read' in filtered)
        self.assertFalse('sa' in filtered)

        # Test Model implementation
        fake = self.model('fake').save(fields)
        filtered = self.model('fake').filter(fake, regUser)
        self.assertEqual(filtered, {'read': 1, '_modelType': 'fake'})

        filtered = self.model('fake').filter(fake, adminUser)
        self.assertEqual(filtered, {
            'read': 1,
            'sa': 1,
            '_modelType': 'fake'
        })

    def testAccessControlCleanup(self):
        # Create documents
        user1 = self.model('user').createUser(
            email='guy@place.com',
            login='someguy',
            firstName='Some',
            lastName='Guy',
            password='mypassword'
        )
        user2 = self.model('user').createUser(
            email='other@place.com',
            login='otherguy',
            firstName='Other',
            lastName='Guy',
            password='mypassword2'
        )
        group1 = self.model('group').createGroup(
            name='agroup',
            creator=user2
        )
        doc1 = {
            'creatorId': user1['_id'],
            'field1': 'value1',
            'field2': 'value2'
        }
        doc1 = self.model('fake_ac').setUserAccess(
            doc1, user1, level=AccessType.ADMIN)
        doc1 = self.model('fake_ac').setUserAccess(
            doc1, user2, level=AccessType.READ)
        doc1 = self.model('fake_ac').setGroupAccess(
            doc1, group1, level=AccessType.WRITE)
        doc1 = self.model('fake_ac').save(doc1)
        doc1Id = doc1['_id']

        # Test pre-delete
        # The raw ACL properties must be examined directly, as the
        # "getFullAccessList" method will silently remove leftover invalid
        # references, which this test is supposed to find
        doc1 = self.model('fake_ac').load(doc1Id, force=True, exc=True)
        self.assertEqual(len(doc1['access']['users']), 2)
        self.assertEqual(len(doc1['access']['groups']), 1)
        self.assertEqual(doc1['creatorId'], user1['_id'])

        # Delete user and test post-delete
        self.model('user').remove(user1)
        doc1 = self.model('fake_ac').load(doc1Id, force=True, exc=True)
        self.assertEqual(len(doc1['access']['users']), 1)
        self.assertEqual(len(doc1['access']['groups']), 1)
        self.assertIsNone(doc1.get('creatorId'))

        # Delete group and test post-delete
        self.model('group').remove(group1)
        doc1 = self.model('fake_ac').load(doc1Id, force=True, exc=True)
        self.assertEqual(len(doc1['access']['users']), 1)
        self.assertEqual(len(doc1['access']['groups']), 0)
        self.assertIsNone(doc1.get('creatorId'))

    def _assertWriteAccess(self, instanceId, user, modelType, modelPlugin=None):
        self.assertRaises(AccessException, self.model(modelType, modelPlugin).load, instanceId)
        self.assertRaises(
            AccessException, self.model(modelType, modelPlugin).load,
            instanceId, level=AccessType.READ)
        self.assertIsNotNone(self.model(modelType, modelPlugin).load(instanceId, force=True))
        self.assertIsNotNone(self.model(modelType, modelPlugin).load(
            instanceId, user=user, level=AccessType.READ))
        self.assertRaises(
            AccessException, self.model(modelType, modelPlugin).load,
            instanceId, user=user, level=AccessType.ADMIN)

    def _assertPublicAccess(self, instanceId, user, modelType, modelPlugin=None):
        self.assertRaises(AccessException, self.model(modelType, modelPlugin).load, instanceId)
        self.assertIsNotNone(self.model(modelType, modelPlugin).load(
            instanceId, level=AccessType.READ))
        self.assertIsNotNone(self.model(modelType, modelPlugin).load(instanceId, force=True))
        self.assertIsNotNone(self.model(modelType, modelPlugin).load(
            instanceId, user=user, level=AccessType.READ))
        self.assertRaises(
            AccessException, self.model(modelType, modelPlugin).load,
            instanceId, user=user, level=AccessType.ADMIN)

    def testAccessControlMixin(self):
        users = ({
             'email': 'good@email.com',
             'login': 'goodlogin',
             'firstName': 'First',
             'lastName': 'Last',
             'password': 'goodpassword'
         }, {
             'email': 'regularuser@email.com',
             'login': 'regularuser',
             'firstName': 'First',
             'lastName': 'Last',
             'password': 'goodpassword'
         })
        adminUser, regUser = [self.model('user').createUser(**user) for user in users]

        # Set up a parent model, and check access
        parentInstance = self.model('fake_ac').save({})
        self.assertHasKeys(parentInstance, ['_id'])
        parentInstance = self.model('fake_ac').setUserAccess(
            parentInstance, regUser, level=AccessType.WRITE, save=True)
        self._assertWriteAccess(parentInstance['_id'], regUser, 'fake_ac')

        # Set up an access control mixin model, and check access
        dependentInstance = self.model('fake_ac_mixin').save({
            'fakeParentId': parentInstance['_id']})
        self.assertHasKeys(dependentInstance, ['_id', 'fakeParentId'])
        self._assertWriteAccess(dependentInstance['_id'], regUser, 'fake_ac_mixin')

        # Set up an attached model, and check access
        attachedInstance1 = self.model('fake_attached').save({
            'attachedToId': parentInstance['_id'],
            'attachedToType': 'fake_ac'})
        self.assertHasKeys(attachedInstance1, ['_id', 'attachedToId', 'attachedToType'])
        self._assertWriteAccess(attachedInstance1['_id'], regUser, 'fake_attached')

        # Set up a parent model from a plugin, and check access
        parentPluginInstance = self.model('fake_ac_plugin_model', 'has_model').save({})
        self.assertHasKeys(parentPluginInstance, ['_id'])
        parentPluginInstance = self.model('fake_ac_plugin_model', 'has_model').setUserAccess(
            parentPluginInstance, regUser, level=AccessType.WRITE, save=True)
        self._assertWriteAccess(
            parentPluginInstance['_id'], regUser, 'fake_ac_plugin_model', 'has_model')

        # Set up an attached model, resourcing a plugin model, and check access
        attachedInstance2 = self.model('fake_attached').save({
            'attachedToId': parentPluginInstance['_id'],
            'attachedToType': ['fake_ac_plugin_model', 'has_model']})
        self.assertHasKeys(attachedInstance2, ['_id', 'attachedToId', 'attachedToType'])
        self._assertWriteAccess(attachedInstance2['_id'], regUser, 'fake_attached')

        # Set up a non-AccessControlled parent model
        parentBasicInstance = self.model('fake').save({})
        self.assertHasKeys(parentBasicInstance, ['_id'])

        # Set up an attached model, resourcing a non-AccessControlled model, and check access
        attachedInstance3 = self.model('fake_attached').save({
            'attachedToId': parentBasicInstance['_id'],
            'attachedToType': 'fake'})
        self.assertHasKeys(attachedInstance3, ['_id', 'attachedToId', 'attachedToType'])
        # Everything should be allowed
        self.assertIsNotNone(self.model('fake_attached').load(attachedInstance3['_id']))
        self.assertIsNotNone(self.model('fake_attached').load(
            attachedInstance3['_id'], level=AccessType.READ))
        self.assertIsNotNone(self.model('fake_attached').load(attachedInstance3['_id'], force=True))
        self.assertIsNotNone(self.model('fake_attached').load(
            attachedInstance3['_id'], user=user, level=AccessType.READ))
        self.assertIsNotNone(self.model('fake_attached').load(
            attachedInstance3['_id'], user=user, level=AccessType.ADMIN))

        # Ensure that making access controlled parent public also makes resourcing models public
        parentInstance = self.model('fake_ac').setPublic(parentInstance, True, save=True)
        self._assertPublicAccess(parentInstance['_id'], regUser, 'fake_ac')
        self._assertPublicAccess(dependentInstance['_id'], regUser, 'fake_ac_mixin')
        self._assertPublicAccess(attachedInstance1['_id'], regUser, 'fake_attached')
        parentPluginInstance = self.model('fake_ac_plugin_model', 'has_model').setPublic(
            parentPluginInstance, True, save=True)
        self._assertPublicAccess(
            parentPluginInstance['_id'], regUser, 'fake_ac_plugin_model', 'has_model')
        self._assertPublicAccess(attachedInstance2['_id'], regUser, 'fake_attached')
