# -*- coding: utf-8 -*-
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from base64 import b64encode as b64e
import unittest

from apiclient.errors import HttpError

from airflow.contrib.hooks.gcp_pubsub_hook import PubSubException, PubSubHook

try:
    from unittest import mock
except ImportError:
    try:
        import mock
    except ImportError:
        mock = None

BASE_STRING = 'airflow.contrib.hooks.gcp_api_base_hook.{}'
PUBSUB_STRING = 'airflow.contrib.hooks.gcp_pubsub_hook.{}'

TEST_PROJECT = 'test-project'
TEST_TOPIC = 'test-topic'
TEST_SUBSCRIPTION = 'test-subscription'
TEST_UUID = 'abc123-xzy789'
TEST_MESSAGES = [
    {
        'data': b64e('Hello, World!'),
        'attributes': {'type': 'greeting'}
    },
    {'data': b64e('Knock, knock')},
    {'attributes': {'foo': ''}}]

EXPANDED_TOPIC = 'projects/%s/topics/%s' % (TEST_PROJECT, TEST_TOPIC)
EXPANDED_SUBSCRIPTION = 'projects/%s/subscriptions/%s' % (TEST_PROJECT,
                                                          TEST_SUBSCRIPTION)


def mock_init(self, gcp_conn_id, delegate_to=None):
    pass


class PubSubHookTest(unittest.TestCase):
    def setUp(self):
        with mock.patch(BASE_STRING.format('GoogleCloudBaseHook.__init__'),
                        new=mock_init):
            self.pubsub_hook = PubSubHook(gcp_conn_id='test')

    @mock.patch(PUBSUB_STRING.format('PubSubHook.get_conn'))
    def test_create_nonexistent_topic(self, mock_service):
        self.pubsub_hook.create_topic(TEST_PROJECT, TEST_TOPIC)

        create_method = (mock_service.return_value.projects.return_value.topics
                         .return_value.create)
        create_method.assert_called_with(body={}, name=EXPANDED_TOPIC)
        create_method.return_value.execute.assert_called_with()

    @mock.patch(PUBSUB_STRING.format('PubSubHook.get_conn'))
    def test_delete_topic(self, mock_service):
        self.pubsub_hook.delete_topic(TEST_PROJECT, TEST_TOPIC)

        delete_method = (mock_service.return_value.projects.return_value.topics
                         .return_value.delete)
        delete_method.assert_called_with(topic=EXPANDED_TOPIC)
        delete_method.return_value.execute.assert_called_with()

    @mock.patch(PUBSUB_STRING.format('PubSubHook.get_conn'))
    def test_delete_nonexisting_topic_failifnotexists(self, mock_service):
        (mock_service.return_value.projects.return_value.topics
         .return_value.delete.return_value.execute.side_effect) = HttpError(
            resp={'status': '404'}, content='')

        with self.assertRaises(PubSubException) as e:
            self.pubsub_hook.delete_topic(TEST_PROJECT, TEST_TOPIC, True)

        self.assertEquals(e.exception.message,
                          'Topic does not exist: %s' % EXPANDED_TOPIC)

    @mock.patch(PUBSUB_STRING.format('PubSubHook.get_conn'))
    def test_create_preexisting_topic_failifexists(self, mock_service):
        (mock_service.return_value.projects.return_value.topics.return_value
         .create.return_value.execute.side_effect) = HttpError(
            resp={'status': '409'}, content='')

        with self.assertRaises(PubSubException) as e:
            self.pubsub_hook.create_topic(TEST_PROJECT, TEST_TOPIC, True)
        self.assertEquals(e.exception.message,
                          'Topic already exists: %s' % EXPANDED_TOPIC)

    @mock.patch(PUBSUB_STRING.format('PubSubHook.get_conn'))
    def test_create_preexisting_topic_nofailifexists(self, mock_service):
        (mock_service.return_value.projects.return_value.topics.return_value
         .get.return_value.execute.side_effect) = HttpError(
            resp={'status': '409'}, content='')

        self.pubsub_hook.create_topic(TEST_PROJECT, TEST_TOPIC)

    @mock.patch(PUBSUB_STRING.format('PubSubHook.get_conn'))
    def test_create_nonexistent_subscription(self, mock_service):
        response = self.pubsub_hook.create_subscription(
            TEST_PROJECT, TEST_TOPIC, TEST_SUBSCRIPTION)

        create_method = (
            mock_service.return_value.projects.return_value.subscriptions.
            return_value.create)
        expected_body = {
            'topic': EXPANDED_TOPIC,
            'ackDeadlineSeconds': 10
        }
        create_method.assert_called_with(name=EXPANDED_SUBSCRIPTION,
                                         body=expected_body)
        create_method.return_value.execute.assert_called_with()
        self.assertEquals(TEST_SUBSCRIPTION, response)

    @mock.patch(PUBSUB_STRING.format('PubSubHook.get_conn'))
    def test_create_subscription_different_project_topic(self, mock_service):
        response = self.pubsub_hook.create_subscription(
            TEST_PROJECT, TEST_TOPIC, TEST_SUBSCRIPTION, 'a-different-project')

        create_method = (
            mock_service.return_value.projects.return_value.subscriptions.
            return_value.create)

        expected_subscription = 'projects/%s/subscriptions/%s' % (
            'a-different-project', TEST_SUBSCRIPTION)
        expected_body = {
            'topic': EXPANDED_TOPIC,
            'ackDeadlineSeconds': 10
        }
        create_method.assert_called_with(name=expected_subscription,
                                         body=expected_body)
        create_method.return_value.execute.assert_called_with()
        self.assertEquals(TEST_SUBSCRIPTION, response)

    @mock.patch(PUBSUB_STRING.format('PubSubHook.get_conn'))
    def test_delete_subscription(self, mock_service):
        self.pubsub_hook.delete_subscription(TEST_PROJECT, TEST_SUBSCRIPTION)

        delete_method = (mock_service.return_value.projects
                         .return_value.subscriptions.return_value.delete)
        delete_method.assert_called_with(subscription=EXPANDED_SUBSCRIPTION)
        delete_method.return_value.execute.assert_called_with()

    @mock.patch(PUBSUB_STRING.format('PubSubHook.get_conn'))
    def test_delete_nonexisting_subscription_failifnotexists(self,
                                                             mock_service):
        (mock_service.return_value.projects.return_value.subscriptions.
         return_value.delete.return_value.execute.side_effect) = HttpError(
            resp={'status': '404'}, content='')

        with self.assertRaises(PubSubException) as e:
            self.pubsub_hook.delete_subscription(
                TEST_PROJECT, TEST_SUBSCRIPTION, fail_if_not_exists=True)

        self.assertEquals(e.exception.message,
                          'Subscription does not exist: %s' %
                          EXPANDED_SUBSCRIPTION)

    @mock.patch(PUBSUB_STRING.format('PubSubHook.get_conn'))
    @mock.patch(PUBSUB_STRING.format('uuid4'),
                new_callable=mock.Mock(return_value=lambda: TEST_UUID))
    def test_create_subscription_without_name(self, mock_uuid, mock_service):
        response = self.pubsub_hook.create_subscription(TEST_PROJECT,
                                                        TEST_TOPIC)
        create_method = (
            mock_service.return_value.projects.return_value.subscriptions.
            return_value.create)
        expected_body = {
            'topic': EXPANDED_TOPIC,
            'ackDeadlineSeconds': 10
        }
        expected_name = EXPANDED_SUBSCRIPTION.replace(
            TEST_SUBSCRIPTION, 'sub-%s' % TEST_UUID)
        create_method.assert_called_with(name=expected_name,
                                         body=expected_body)
        create_method.return_value.execute.assert_called_with()
        self.assertEquals('sub-%s' % TEST_UUID, response)

    @mock.patch(PUBSUB_STRING.format('PubSubHook.get_conn'))
    def test_create_subscription_with_ack_deadline(self, mock_service):
        response = self.pubsub_hook.create_subscription(
            TEST_PROJECT, TEST_TOPIC, TEST_SUBSCRIPTION, ack_deadline_secs=30)

        create_method = (
            mock_service.return_value.projects.return_value.subscriptions.
            return_value.create)
        expected_body = {
            'topic': EXPANDED_TOPIC,
            'ackDeadlineSeconds': 30
        }
        create_method.assert_called_with(name=EXPANDED_SUBSCRIPTION,
                                         body=expected_body)
        create_method.return_value.execute.assert_called_with()
        self.assertEquals(TEST_SUBSCRIPTION, response)

    @mock.patch(PUBSUB_STRING.format('PubSubHook.get_conn'))
    def test_create_subscription_failifexists(self, mock_service):
        (mock_service.return_value.projects.return_value.
         subscriptions.return_value.create.return_value
         .execute.side_effect) = HttpError(resp={'status': '409'},
                                           content='')

        with self.assertRaises(PubSubException) as e:
            self.pubsub_hook.create_subscription(
                TEST_PROJECT, TEST_TOPIC, TEST_SUBSCRIPTION,
                fail_if_exists=True)

        self.assertEquals(e.exception.message,
                          'Subscription already exists: %s' %
                          EXPANDED_SUBSCRIPTION)

    @mock.patch(PUBSUB_STRING.format('PubSubHook.get_conn'))
    def test_create_subscription_nofailifexists(self, mock_service):
        (mock_service.return_value.projects.return_value.topics.return_value
         .get.return_value.execute.side_effect) = HttpError(
            resp={'status': '409'}, content='')

        response = self.pubsub_hook.create_subscription(
            TEST_PROJECT, TEST_TOPIC, TEST_SUBSCRIPTION
        )
        self.assertEquals(TEST_SUBSCRIPTION, response)

    @mock.patch(PUBSUB_STRING.format('PubSubHook.get_conn'))
    def test_publish(self, mock_service):
        self.pubsub_hook.publish(TEST_PROJECT, TEST_TOPIC, TEST_MESSAGES)

        publish_method = (mock_service.return_value.projects.return_value
                          .topics.return_value.publish)
        publish_method.assert_called_with(
            topic=EXPANDED_TOPIC, body={'messages': TEST_MESSAGES})
