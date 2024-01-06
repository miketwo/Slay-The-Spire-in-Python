from ansi_tags import ansiprint
from definitions import Topic

class MessageBus():
  '''This is a Pub/Sub, or Publish/Subscribe, message bus. It allows components to subscribe to messages,
  registering a callback function that will be called when that message is published.

  All callbacks are called with two arguments: the message type, and the data associated with that message.
  '''
  def __init__(self, debug=False):
    self.subscribers = dict(dict())
    self.debug = debug

  def subscribe(self, event_type: Topic, callback, uid, priority=0):
    assert 0 <= priority <= 100, "Priority must be between 0 and 100"
    if event_type not in self.subscribers:
      self.subscribers[event_type] = dict()
    if uid in self.subscribers[event_type]:
      if self.debug:
        name = callback.__qualname__ if hasattr(callback, "__qualname__") else callback
        ansiprint(f"<basic>MESSAGEBUS</basic>: <blue>{event_type}</blue> | <bold>{name}</bold> already subscribed. Skipping.")
      return
    self.subscribers[event_type][uid] = (priority, callback)
    if self.debug:
      name = callback.__qualname__ if hasattr(callback, "__qualname__") else callback
      ansiprint(f"<basic>MESSAGEBUS</basic>: <blue>{event_type}</blue> | Subscribed <bold>{name}</bold>")

  def publish(self, event_type: Topic, data):
    if event_type in self.subscribers:
      prioritized_callbacks = self.subscribers[event_type].values()
      prioritized_callbacks = sorted(prioritized_callbacks, key=lambda x: x[0], reverse=True)
      for priority, callback in prioritized_callbacks:
        if self.debug:
          ansiprint(f"<basic>MESSAGEBUS</basic>: <blue>{event_type}</blue> | Calling <bold>{callback.__qualname__}</bold> (Priority: {priority})")
        callback(event_type, data)
    return data