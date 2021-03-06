"""
<copyright
notice="lm-source-program"
pids="5725-P60"
years="2013,2015"
crc="3568777996" >
Licensed Materials - Property of IBM

5725-P60

(C) Copyright IBM Corp. 2013, 2015

US Government Users Restricted Rights - Use, duplication or
disclosure restricted by GSA ADP Schedule Contract with
IBM Corp.
</copyright>
"""
# pylint: disable=bare-except,broad-except,invalid-name,no-self-use
# pylint: disable=too-many-public-methods,unused-argument
import pytest
import threading
from mock import Mock
import mqlight
from mqlight.exceptions import StoppedError, RangeError, InvalidArgumentError,\
    UnsubscribedError, MQLightError


class TestUnsubscribe(object):
    """
    Unit tests for client.unsubscribe()
    """
    TEST_TIMEOUT = 10.0

    def test_unsubscribe_too_few_arguments(self):
        """
        Test a calling client.unsubscribe(...) with too few arguments
        (no arguments) causes an Error to be thrown.
        """
        # pylint: disable=no-value-for-parameter
        client = mqlight.Client(
            'amqp://host',
            'test_unsubscribe_too_few_arguments')
        with pytest.raises(TypeError):
            client.unsubscribe()
        client.stop()

    def test_unsubscribe_too_many_arguments(self):
        """
        Test that calling client.unsubscribe(...) with too many arguments
        causes an Error to be thrown.
        """
        # pylint: disable=too-many-function-args
        test_is_done = threading.Event()

        def started(client):
            """started listener"""
            client.subscribe('/foo', 'share1')
            with pytest.raises(TypeError):
                client.unsubscribe('/foo', 'share1', {}, func, 'stowaway')
            client.stop()
            test_is_done.set()
        client = mqlight.Client(
            'amqp://host',
            'test_unsubscribe_too_many_arguments',
            on_started=started)
        func = Mock()
        test_is_done.wait(self.TEST_TIMEOUT)
        assert test_is_done.is_set()

    class Counter(object):
        def __init__(self, count):
            self.count = count

        def decrementAndGet(self):
            self.count -= 1
            return self.count

    def test_unsubscribe_callback_must_be_function(self):
        """
        Test that the callback argument to client.unsubscribe(...) must be a
        function
        """
        test_is_done = threading.Event()

        def on_stopped(self):
            """client stop callback"""
            test_is_done.set()

        def started(client):
            """started listener"""
            COUNTER = self.Counter(3)

            def func(*args):
                if COUNTER.decrementAndGet() <= 0:
                    client.stop(on_stopped=on_stopped)

            def subscribed1(err, pattern, share):
                with pytest.raises(TypeError):
                    client.unsubscribe('/foo1', 'share', {}, on_unsubscribed=7)
            client.subscribe('/foo1', 'share', on_subscribed=subscribed1)

            def subscribed2(err, pattern, share):
                client.unsubscribe('/foo2', on_unsubscribed=func)
            client.subscribe('/foo2', on_subscribed=subscribed2)

            def subscribed3(err, pattern, share):
                client.unsubscribe('/foo3', 'share', on_unsubscribed=func)
            client.subscribe('/foo3', 'share', on_subscribed=subscribed3)

            def subscribed4(err, pattern, share):
                client.unsubscribe('/foo4', 'share', {}, on_unsubscribed=func)
            client.subscribe('/foo4', 'share', on_subscribed=subscribed4)

        client = mqlight.Client(
            'amqp://host',
            'test_unsubscribe_callback_must_be_function',
            on_started=started
        )

        test_is_done.wait(self.TEST_TIMEOUT)
        assert test_is_done.is_set()

    def test_unsubscribe_ok_callback(self):
        """
        Test that the callback (invoked when the unsubscribe operation
        completes successfully) specifies the right number of arguments.
        """
        test_is_done = threading.Event()

        def on_stopped(client):
            """client stop callback"""
            test_is_done.set()

        def started(client):
            """started listener"""
            def unsub(err, topic, share):
                """unsubscribe callback"""
                assert topic == '/foo'
                assert share is None

            def sub(err, topic, share):
                """subscribe callback"""
                client.unsubscribe('/foo', on_unsubscribed=unsub)
            client.subscribe('/foo', on_subscribed=sub)

            def unsub2(err, topic, share):
                """unsubscribe callback"""
                assert err is None
                assert topic == '/foo2'
                assert share == 'share'
                client.stop(on_stopped=on_stopped)

            def sub2(err, topic, share):
                """subscribe callback"""
                client.unsubscribe('/foo2', 'share', on_unsubscribed=unsub2)
            client.subscribe('/foo2', 'share', on_subscribed=sub2)

        client = mqlight.Client(
            'amqp://host',
            'test_unsubscribe_ok_callback',
            on_started=started)
        test_is_done.wait(self.TEST_TIMEOUT)
        assert test_is_done.is_set()

    def test_unsubscribe_when_stopped(self):
        """
        Test that trying to remove a subscription, while the client is in
        stopped state, throws an Error.
        """
        test_is_done = threading.Event()
        client = mqlight.Client('amqp://host', 'test_unsubscribe_when_stopped')

        def stopped(client):
            """stopped listener"""
            with pytest.raises(StoppedError):
                client.unsubscribe('/foo')
            test_is_done.set()
        client.stop(stopped)
        test_is_done.wait(self.TEST_TIMEOUT)
        assert test_is_done.is_set()

    def test_unsubscribe_when_not_subscribed(self):
        """
        Test that trying to remove a subscription that does not exist throws an
        Error.
        """
        test_is_done = threading.Event()

        def started(client):
            """started listener"""
            subscribe_event = threading.Event()
            client.subscribe(
                '/bar',
                on_subscribed=lambda _x, _y, _z: subscribe_event.set())
            subscribe_event.wait(2.0)
            assert subscribe_event.is_set()
            with pytest.raises(UnsubscribedError):
                client.unsubscribe('/foo')
            client.stop()
            test_is_done.set()
        client = mqlight.Client(
            'amqp://host',
            'test_unsubscribe_when_not_subscribed',
            on_started=started)
        test_is_done.wait(self.TEST_TIMEOUT)
        assert test_is_done.is_set()

    def test_unsubscribe_returns_client(self):
        """
        Test that calling the unsubscribe(...) method returns, as a value, the
        client object that the method was invoked on (for method chaining
        purposes).
        """
        test_is_done = threading.Event()
        def started(client):
            """started listener"""
            subscribe_event = threading.Event()
            client.subscribe(
                '/foo',
                on_subscribed=lambda _x, _y, _z: subscribe_event.set())
            subscribe_event.wait(2.0)
            assert  subscribe_event.is_set()
            assert client.unsubscribe('/foo') == client
            client.stop()
            test_is_done.set()
        client = mqlight.Client(
            'amqp://host',
            'test_unsubscribe_returns_client',
            on_started=started)
        test_is_done.wait(self.TEST_TIMEOUT)
        assert test_is_done.is_set()

    def test_unsubscribe_topics(self):
        """
        Test a variety of valid and invalid patterns.  Invalid patterns
        should result in the client.unsubscribe(...) method throwing a
        TypeError.
        """
        test_is_done = threading.Event()
        data = [
            {'valid': False, 'pattern': ''},
            {'valid': False, 'pattern': None},
            {'valid': True, 'pattern': 1234},
            {'valid': True, 'pattern': lambda *args: 'topic'},
            {'valid': True, 'pattern': 'kittens'},
            {'valid': True, 'pattern': '/kittens'},
            {'valid': True, 'pattern': '+'},
            {'valid': True, 'pattern': '#'},
            {'valid': True, 'pattern': '/#'},
            {'valid': True, 'pattern': '/+'}
        ]

        def started(client):
            """started listener"""
            try:
                for test in data:
                    if test['valid']:
                        test_pattern = test['pattern']
                        client.subscribe(
                            test['pattern'],
                            on_subscribed=lambda pattern=test_pattern:
                            client.unsubscribe(pattern))
                    else:
                        with pytest.raises(TypeError):
                            client.unsubscribe(test['pattern'])
            except Exception as exc:
                pytest.fail('Unexpected Exception ' + str(exc))
            finally:
                client.stop()
                test_is_done.set()
        client = mqlight.Client(
            'amqp://host',
            'test_unsubscribe_topics',
            on_started=started)

        test_is_done.wait(self.TEST_TIMEOUT)
        assert test_is_done.is_set()

    def test_unsubscribe_share_names(self):
        """
        Tests a variety of valid and invalid share names to check that they are
        accepted or rejected (by throwing an Error) as appropriate.
        """
        test_is_done = threading.Event()
        data = [
            {'valid': True, 'share': 'abc'},
            {'valid': True, 'share': 7},
            {'valid': False, 'share': ':'},
            {'valid': False, 'share': 'a:'},
            {'valid': False, 'share': ':a'}
        ]

        def started(client):
            """started listener"""
            try:
                for test in data:
                    if test['valid']:
                        test_share = test['share']
                        client.subscribe(
                            '/foo',
                            test_share,
                            on_subscribed=lambda share=test_share:
                            client.unsubscribe('/foo', share))
                    else:
                        with pytest.raises(InvalidArgumentError):
                            client.unsubscribe('/foo', test['share'])
            except Exception as exc:
                pytest.fail('Unexpected Exception ' + str(exc))
            finally:
                client.stop()
                test_is_done.set()
        client = mqlight.Client(
            'amqp://host',
            'test_unsubscribe_share_names',
            on_started=started)

        test_is_done.wait(self.TEST_TIMEOUT)
        assert test_is_done.is_set()

    def test_unsubscribe_options(self):
        """
        Test a variety of valid and invalid options values. Invalid options
        should result in the client.unsubscribe(...) method throwing a
        TypeError.

        Note that this test just checks that the options parameter is only
        accepted when it is of the correct type. The actual validation of
        individual options will be in separate tests.
        """
        test_is_done = threading.Event()
        func = Mock()
        data = [
            {'valid': False, 'options': ''},
            {'valid': True, 'options': None},
            {'valid': False, 'options': func},
            {'valid': False, 'options': '1'},
            {'valid': False, 'options': 2},
            {'valid': False, 'options': True},
            {'valid': True, 'options': {}},
            {'valid': True, 'options': {'a': 1}}
        ]

        def started(client):
            """started listener"""
            try:
                test_pattern = 0
                for test in data:
                    if test['valid']:
                        test_pattern += 1
                        test_options = test['options']
                        client.subscribe(
                            test_pattern,
                            'share',
                            on_subscribed=lambda pattern=test_pattern, options=test_options:
                            client.unsubscribe(
                                pattern,
                                'share',
                                options,
                                func))
                    else:
                        with pytest.raises(TypeError):
                            client.unsubscribe('testpattern',
                                               'share',
                                               test['options'],
                                               func)
            except Exception as exc:
                pytest.fail('Unexpected Exception ' + str(exc))
            finally:
                client.stop()
                test_is_done.set()
        client = mqlight.Client(
            'amqp://host',
            'test_unsubscribe_options',
            on_started=started)

        test_is_done.wait(self.TEST_TIMEOUT)
        assert test_is_done.is_set()

    def test_unsubscribe_ttl_validity(self):
        """
        Test a variety of valid and invalid ttl options.  Invalid ttl values
        should result in the client.unsubscribe(...) method throwing a
        TypeError.
        """
        test_is_done = threading.Event()
        func = Mock()
        data = [
            {'valid': False, 'ttl': None},
            {'valid': False, 'ttl': func},
            {'valid': False, 'ttl': -9007199254740992},
            {'valid': False, 'ttl': float('-nan')},
            {'valid': False, 'ttl': float('nan')},
            {'valid': False, 'ttl': float('-inf')},
            {'valid': False, 'ttl': float('inf')},
            {'valid': False, 'ttl': -1},
            {'valid': False, 'ttl': 1},
            {'valid': False, 'ttl': 9007199254740992},
            {'valid': True, 'ttl': 0},
            {'valid': False, 'ttl': ''}
        ]

        def started(client):
            """started listener"""
            try:
                for test in data:
                    test_opts = {'ttl': test['ttl']}
                    if test['valid']:
                        client.subscribe(
                            'testpattern',
                            on_subscribed=lambda opts=test_opts:
                            client.unsubscribe(
                                'testpattern', options=opts)
                        )
                    else:
                        with pytest.raises(RangeError):
                            client.unsubscribe(
                                'testpattern', options=test_opts)
            except Exception as exc:
                pytest.fail('Unexpected Exception ' + str(exc))
            finally:
                client.stop()
                test_is_done.set()
        client = mqlight.Client(
            'amqp://host',
            'test_unsubscribe_ttl_validity',
            on_started=started)

        test_is_done.wait(self.TEST_TIMEOUT)
        assert test_is_done.is_set()
