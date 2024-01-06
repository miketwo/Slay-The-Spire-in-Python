from ansi_tags import ansiprint
from definitions import Topic

class MessageBus():
  '''This is a Pub/Sub, or Publish/Subscribe, message bus. It allows components to subscribe to messages,
  registering a callback function that will be called when that message is published.
  '''
  def __init__(self, debug=True):
    self.subscribers = dict(dict())
    self.debug = debug

  def subscribe(self, event_type: Topic, callback, uid):
    if event_type not in self.subscribers:
      self.subscribers[event_type] = dict()
    self.subscribers[event_type][uid] = callback
    if self.debug:
      ansiprint(f"<basic>MESSAGEBUS</basic>: <blue>{event_type}</blue> | Subscribed <bold>{callback.__qualname__}</bold>")

  def publish(self, event_type: Topic, data):
    if event_type in self.subscribers:
      for uid, callback in self.subscribers[event_type].items():
        if self.debug:
          ansiprint(f"<basic>MESSAGEBUS</basic>: <blue>{event_type}</blue> | Calling <bold>{callback.__qualname__}</bold>")
        callback(event_type, data)
    return data