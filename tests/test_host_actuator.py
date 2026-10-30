"""Descriptor -> fenced actuator -> real process -> durable outcome."""
import json
import socket
import sys
import time
import unittest
import urllib.request
from unittest.mock import patch
import test_web4_runtime
from keddeh_namespace.web4_runtime import LaunchController, write_json

class HostActuatorTests(unittest.TestCase):
    setUp=test_web4_runtime.Web4RuntimeTests.setUp
    fixture_controller=test_web4_runtime.Web4RuntimeTests.fixture_controller

    def controller(self):
        c=self.fixture_controller();(c.state/'pairing-code').write_text('test-only');self.addCleanup(c.close)
        c.specs['worker']=([sys.executable,'-c','import time; time.sleep(30)'],str(self.root),None,False)
        return c

    def command(self,c,operation,request='one',name='worker'):
        host=c.control({'action':'host'})
        service=next(row for row in host['services'] if row['name']==name)
        return {'action':'host','operation':operation,'request_id':request,'name':name,
                'host_id':host['host_id'],'instance_id':host['instance_id'],'source_digest':host['source_digest'],
                'expected_generation':service['generation'],'expected_pid':service['pid'],
                'pipeline_generation':c.pipeline.status()['generation']}

    def test_start_duplicate_stale_restart_stop_and_recovery(self):
        c=self.controller();command=self.command(c,'start');first=c.control(command)
        self.assertEqual(first['status'],'COMPLETED');self.assertTrue(first['readback']['alive'])
        self.assertEqual(first,c.control(command))
        stale={**command,'request_id':'stale'}
        with self.assertRaisesRegex(ValueError,'stale service'):c.control(stale)
        with self.assertRaisesRegex(ValueError,'reused'):c.control({**command,'operation':'stop'})
        restarted=c.control(self.command(c,'restart','restart'))
        self.assertNotEqual(first['readback']['pid'],restarted['readback']['pid'])
        stopped=c.control(self.command(c,'stop','stop'));self.assertFalse(stopped['readback']['alive'])
        c.recover_services();self.assertFalse(c.service_readback('worker')['alive'])
        saved=json.loads(c.actuator_path.read_text())
        self.assertEqual(saved['requests']['stop']['result'],stopped)
        self.assertEqual(saved['services']['worker']['desired'],'stopped')
        reopened=LaunchController(self.root);self.addCleanup(reopened.close)
        self.assertEqual(c.host_id,reopened.host_id);self.assertNotEqual(c.instance_id,reopened.instance_id)
        spec=c.specs['worker'];self.assertIsNone(reopened.spawn('worker',*spec))
        self.assertNotIn('worker',reopened.processes)
        self.assertEqual(reopened.control(command),first)
        with self.assertRaisesRegex(ValueError,'stale or foreign'):reopened.control({**command,'request_id':'old-instance'})
        new=reopened.control(self.command(reopened,'start','new-controller'))
        self.assertTrue(new['readback']['alive'])

    def test_fences_unknown_service_and_failed_launch(self):
        c=self.controller();command=self.command(c,'start')
        with self.assertRaisesRegex(ValueError,'unknown owned'):c.control({**command,'name':'unknown'})
        with self.assertRaisesRegex(ValueError,'stale projection'):c.control({**command,'pipeline_generation':999})
        c.pipeline.configure(False,'test')
        with self.assertRaises(RuntimeError):c.control(command)
        self.assertEqual(c.control({'action':'host'})['host_id'],c.host_id)
        c.pipeline.configure(True,'test')
        command=self.command(c,'start')
        # Exercise actual Popen cwd failure, not a fake result.
        c.specs['worker']=(c.specs['worker'][0],str(self.root/'missing-directory'),None,False)
        result=c.control(command)
        self.assertEqual(result['status'],'FAILED');self.assertEqual(result['error'],'FileNotFoundError')
        self.assertFalse(result['readback']['alive']);self.assertEqual(result,c.control(command))

    def test_interrupted_command_is_not_reexecuted(self):
        c=self.controller();command=self.command(c,'start')
        c.actuator['requests']['one']={'command':{k:v for k,v in command.items() if k!='action'},'status':'ACCEPTED'}
        write_json(c.actuator_path,c.actuator)
        reopened=LaunchController(self.root);self.addCleanup(reopened.close);reopened.specs.update(c.specs)
        with patch.object(reopened,'spawn') as spawn:
            self.assertEqual(reopened.control(command)['status'],'UNCERTAIN');spawn.assert_not_called()

    def test_real_http_readback_restart_and_stop(self):
        c=self.controller()
        with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        (self.root/'probe.txt').write_text('host-actuator-readback')
        c.specs['worker']=([sys.executable,'-m','http.server',str(port),'--bind','127.0.0.1'],str(self.root),None,False)
        for operation in ('start','restart'):
            result=c.control(self.command(c,operation,operation));self.assertTrue(result['readback']['alive'])
            deadline=time.monotonic()+5
            while True:
                try:
                    with urllib.request.urlopen(f'http://127.0.0.1:{port}/probe.txt',timeout=1) as response:
                        self.assertEqual(response.read(),b'host-actuator-readback')
                    break
                except OSError:
                    if time.monotonic()>=deadline:raise
                    time.sleep(.05)
        c.control(self.command(c,'stop','stop'))
        with socket.socket() as sock:self.assertNotEqual(sock.connect_ex(('127.0.0.1',port)),0)

    def test_crash_after_actual_start_retains_uncertain_outcome(self):
        c=self.controller();command=self.command(c,'start')
        start=c.start_service
        class PowerLoss(BaseException):pass
        def interrupted(name):
            start(name)
            raise PowerLoss()
        with patch.object(c,'start_service',side_effect=interrupted):
            with self.assertRaises(PowerLoss):c.control(command)
        self.assertTrue(c.service_readback('worker')['alive'])
        self.assertEqual(json.loads(c.actuator_path.read_text())['requests']['one']['status'],'ACCEPTED')
        c.close()
        reopened=LaunchController(self.root);self.addCleanup(reopened.close);reopened.specs.update(c.specs)
        with patch.object(reopened,'spawn') as spawn:
            self.assertEqual(reopened.control(command)['status'],'UNCERTAIN');spawn.assert_not_called()
        binding=json.loads((reopened.state/'host-binding.json').read_text())
        self.assertEqual(binding['host_id'],c.host_id)
        self.assertEqual(binding['source_digest'],reopened.source_digest)

    def test_concurrent_stop_fences_stale_start_and_recovery(self):
        import threading
        from concurrent.futures import ThreadPoolExecutor
        c=self.controller()
        c.control(self.command(c,'start','initial'))
        stop=self.command(c,'stop','stop')
        stale_start=self.command(c,'start','delayed-start')
        entered=threading.Event();release=threading.Event();start_attempted=threading.Event()
        terminate=c.terminate
        def delayed_terminate(proc):
            entered.set()
            if not release.wait(5):raise RuntimeError('test release timeout')
            terminate(proc)
        def delayed_start():
            start_attempted.set()
            return c.control(stale_start)
        with patch.object(c,'terminate',side_effect=delayed_terminate):
            with ThreadPoolExecutor(max_workers=3) as pool:
                stopping=pool.submit(c.control,stop)
                try:
                    self.assertTrue(entered.wait(5))
                    stale=pool.submit(delayed_start)
                    recovery=pool.submit(c.recover_services)
                    self.assertTrue(start_attempted.wait(5))
                finally:release.set()
                self.assertEqual(stopping.result(timeout=5)['status'],'COMPLETED')
                with self.assertRaisesRegex(ValueError,'stale service'):stale.result(timeout=5)
                recovery.result(timeout=5)
        self.assertFalse(c.service_readback('worker')['alive'])
        self.assertEqual(c.service_readback('worker')['desired'],'stopped')
        self.assertNotIn('delayed-start',json.loads(c.actuator_path.read_text())['requests'])
        reopened=LaunchController(self.root);self.addCleanup(reopened.close)
        self.assertIsNone(reopened.spawn('worker',*c.specs['worker']))
        self.assertEqual(reopened.service_readback('worker')['desired'],'stopped')

    def test_concurrent_duplicate_restart_executes_once(self):
        from concurrent.futures import ThreadPoolExecutor
        c=self.controller();c.control(self.command(c,'start','initial'))
        restart=self.command(c,'restart','same-restart')
        with patch.object(c,'restart',wraps=c.restart) as dispatch:
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures=[pool.submit(c.control,restart) for _ in range(2)]
                results=[future.result(timeout=5) for future in futures]
            dispatch.assert_called_once_with('worker')
        self.assertEqual(results[0],results[1])
