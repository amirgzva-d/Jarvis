import json
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib import request, error

from jarvis_core import JarvisState, build_galaxy, export_galaxy, score_nodes, note_answer, safe_config
from server import JarvisServer

class NotesTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='jarvis-test-')
        self.root=Path(self.tmp.name)
        (self.root/'notes'/'موضوع').mkdir(parents=True)
        (self.root/'web').mkdir()
        (self.root/'web'/'index.html').write_text('<h1>Jarvis</h1>', 'utf-8')
        (self.root/'notes'/'موضوع'/'داده.md').write_text('# داده\n\nداده برای [[مدل]] مفید است.','utf-8')
        (self.root/'notes'/'موضوع'/'مدل.md').write_text('# مدل\n\nمدل با داده آموزش می‌بیند.','utf-8')
        self.cfg={'provider':'notes-only','notes_folder':'notes','online_tts':False,'port':8800,'voice':'fa-IR-FaridNeural'}
        self.state=JarvisState(self.root,self.cfg)
    def tearDown(self):self.tmp.cleanup()
    def test_index_links_and_stable_id(self):
        g=self.state.graph
        self.assertEqual(len(g['nodes']),2)
        self.assertEqual(len(g['links']),1)
        self.assertEqual([n['id'] for n in g['nodes']],[0,1])
        self.assertEqual(g['nodes'][0]['category'],'موضوع')
    def test_retrieval_grounded_and_empty(self):
        ranked=score_nodes('مدل چیست',self.state.graph)
        self.assertTrue(ranked)
        self.assertIn('مدل',note_answer('مدل چیست',ranked))
        self.assertIn('اطلاعات مرتبطی پیدا نکردم',note_answer('بیولوژی کوانتومی',[]))
    def test_memory_saved_and_galaxy_live(self):
        before=len(self.state.graph['nodes'])
        res=self.state.ask('یادت باشه که فردا مطالعه هوش مصنوعی دارم')
        self.assertTrue(res['created'])
        self.assertEqual(len(self.state.graph['nodes']),before+1)
        self.assertIn('inbox/',res['note']['path'])
        self.assertTrue((self.root/'notes'/res['note']['path']).exists())
        self.assertEqual(res['sources'],[res['note']['id']])
    def test_unsafe_length_and_path(self):
        with self.assertRaises(ValueError):self.state.remember('x'*2401)
        for n in self.state.graph['nodes']:
            self.assertNotIn('_content',n)
    def test_provider_fallback_when_missing_cli(self):
        self.cfg['provider']='totally-unknown'
        self.state.cfg=self.cfg
        r=self.state.ask('مدل چیست؟')
        self.assertIn('fallback',r['mode'])
        self.assertIsNotNone(r['warning'])
    def test_index_export_script_safety(self):
        p=self.root/'notes'/'موضوع'/'injection.md'
        p.write_text('# test\n\n</script><script>alert(1)</script>','utf-8')
        export_galaxy(self.root/'notes',self.root/'web'/'data.js')
        script=(self.root/'web'/'data.js').read_text('utf-8')
        self.assertNotIn('</script>',script)
        self.assertIn('\\u003c',script)

class HTTPTest(NotesTest):
    def setUp(self):
        super().setUp()
        self.server=JarvisServer(('127.0.0.1',0),self.state)
        self.port=self.server.server_address[1]
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True)
        self.thread.start()
    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.thread.join(timeout=3)
        super().tearDown()
    def url(self,p):return f'http://127.0.0.1:{self.port}{p}'
    def post(self,path,data,origin=None):
        headers={'Content-Type':'application/json'}
        if origin:headers['Origin']=origin
        req=request.Request(self.url(path),json.dumps(data).encode('utf-8'),headers=headers,method='POST')
        return request.urlopen(req,timeout=5)
    def test_status_graph_ask_and_write(self):
        with request.urlopen(self.url('/api/status')) as r:
            self.assertEqual(json.load(r)['notes'],2)
        with self.post('/ask',{'question':'مدل چیست'}) as r:
            result=json.load(r)
            self.assertTrue(result['sources'])
        with self.post('/remember',{'text':'از این به بعد بخوان'},origin=f'http://127.0.0.1:{self.port}') as r:
            res=json.load(r)
            self.assertEqual(len(res['graph']['nodes']),3)
        with request.urlopen(self.url('/api/graph')) as r:
            self.assertEqual(len(json.load(r)['nodes']),3)
    def test_private_source_is_not_served(self):
        for p in ('/config.json','/notes/%D9%85%D9%88%D8%B6%D9%88%D8%B9/%D9%85%D8%AF%D9%84.md','/../jarvis_core.py','/server.py','/.env'):
            with self.assertRaises(error.HTTPError) as context:request.urlopen(self.url(p))
            self.assertEqual(context.exception.code,404)
    def test_origin_host_and_tts_rejection(self):
        with self.assertRaises(error.HTTPError) as context:
            self.post('/remember',{'text':'secret'},'https://evil.example')
        self.assertEqual(context.exception.code,403)
        with self.assertRaises(error.HTTPError) as context:self.post('/speak',{'text':'سلام'})
        self.assertEqual(context.exception.code,403)
        with self.assertRaises(error.HTTPError) as context:
            req=request.Request(self.url('/api/status'),headers={'Host':'evil.example'})
            request.urlopen(req)
        self.assertEqual(context.exception.code,403)
    def test_input_limit(self):
        with self.assertRaises(error.HTTPError) as context:self.post('/ask',{'question':'x'*13000})
        self.assertEqual(context.exception.code,413)

if __name__=='__main__':unittest.main()
