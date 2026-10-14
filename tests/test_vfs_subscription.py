import base64
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from keddeh_namespace.vfs_subscription import VFSSubscription
class Controller:
    def __init__(self,root):self.state=Path(root);self.config={'family_id':'family','repository':'owner/repo','vfs':{'endpoint':'http://127.0.0.1:17887','token_file':'/private/token'}}
class SubscriptionTests(unittest.TestCase):
    def test_unavailability_preserves_cursor_for_retry(self):
        with tempfile.TemporaryDirectory() as root:
            sub=VFSSubscription(Controller(root));sub.state['cursor']=4
            with patch.object(sub,'request',side_effect=OSError('offline')):sub.tick()
            self.assertEqual(sub.state['cursor'],4);self.assertEqual(sub.state['status'],'retrying')
            self.assertEqual(VFSSubscription(Controller(root)).state['cursor'],4)
    def test_tampered_package_does_not_acknowledge_event(self):
        with tempfile.TemporaryDirectory() as root:
            sub=VFSSubscription(Controller(root))
            with patch.object(sub,'request',side_effect=[{}, {'events':[{'seq':1,'path':'/packages/web4/a','kind':'VFS_ARTIFACT_WRITE','artifact_digest':'a'*64}]},{'content_b64':base64.b64encode(b'tampered').decode()}]):sub.tick()
            self.assertEqual(sub.state['cursor'],0);self.assertEqual(sub.state['objects'],{})
            self.assertEqual(sub.state['status'],'retrying')
