from functools import partial
import time
from message_bus import MessageBus
from unittest.mock import Mock
from definitions import Topic


def test_message_bus_basic_flow():
  mb = MessageBus(debug=True)
  mock_callback = Mock()
  mock_callback.__qualname__ = "test_callback_basic_flow"
  topic = Topic.TEST
  mb.subscribe(event_type=topic, callback=mock_callback, uid="test_id")
  mb.publish(event_type=topic, data="test_data")
  mock_callback.assert_called_once_with(topic, "test_data")

def test_message_bus_multiple_subscribers():
  mb = MessageBus(debug=True)
  mock_callback1 = Mock()
  mock_callback1.__qualname__ = "test_callback1_multiple_subscribers"
  mock_callback2 = Mock()
  mock_callback2.__qualname__ = "test_callback2_multiple_subscribers"
  topic = Topic.TEST
  mb.subscribe(event_type=topic, callback=mock_callback1, uid="test_id1")
  mb.subscribe(event_type=topic, callback=mock_callback2, uid="test_id2")
  mb.publish(event_type=topic, data="test_data")
  mock_callback1.assert_called_once_with(topic, "test_data")
  mock_callback2.assert_called_once_with(topic, "test_data")

def test_message_bus_multiple_topics_single_subscriber():
  mb = MessageBus(debug=True)
  mock_callback = Mock()
  mock_callback.__qualname__ = "test_callback_multiple_topics_single_subscriber"
  topic1 = Topic.TEST
  topic2 = Topic.TEST2
  mb.subscribe(event_type=topic1, callback=mock_callback, uid="test_id")
  mb.subscribe(event_type=topic2, callback=mock_callback, uid="test_id")
  mb.publish(event_type=topic1, data="test_data")
  mb.publish(event_type=topic2, data="test_data2")
  assert mock_callback.call_count == 2
  mock_callback.assert_any_call(topic1, "test_data")
  mock_callback.assert_any_call(topic2, "test_data2")

def test_message_bus_deduplicates_subscribers_with_same_uid():
  mb = MessageBus(debug=True)
  mock_callback1 = Mock()
  mock_callback1.__qualname__ = "test_callback1_deduplicates_subscribers_with_same_uid"
  mock_callback2 = Mock()
  mock_callback2.__qualname__ = "test_callback2_deduplicates_subscribers_with_same_uid"
  topic = Topic.TEST
  mb.subscribe(event_type=topic, callback=mock_callback1, uid="test_id")
  mb.subscribe(event_type=topic, callback=mock_callback2, uid="test_id")
  mb.publish(event_type=topic, data="test_data")
  mock_callback1.assert_called_once_with(topic, "test_data")
  mock_callback2.assert_not_called()

def test_message_bus_prioritized_subscribers():
  '''This test is a little tricky, because I have to assert that the callbacks are done in order. I do this by having
  the callbacks record the time they were called, and then asserting that the times are in order.'''
  mb = MessageBus(debug=True)
  timings = {}
  def generic_callback(topic, data, name):
    timings[name] = time.time()
    time.sleep(0.1)  # give a tiny bit of time between the callbacks
  # Make several callbacks off a template
  callback1 = partial(generic_callback, name="callback1")
  callback1.__qualname__ = "callback1"
  callback2 = partial(generic_callback, name="callback2")
  callback2.__qualname__ = "callback2"
  callback3 = partial(generic_callback, name="callback3")
  callback3.__qualname__ = "callback3"
  topic = Topic.TEST
  # Subscribe them out of order
  mb.subscribe(event_type=topic, callback=callback2, uid="test_id2", priority=50)
  mb.subscribe(event_type=topic, callback=callback1, uid="test_id1", priority=0)
  mb.subscribe(event_type=topic, callback=callback3, uid="test_id3", priority=100)
  mb.publish(event_type=topic, data="test_data")

  assert timings["callback3"] < timings["callback2"]
  assert timings["callback2"] < timings["callback1"]

