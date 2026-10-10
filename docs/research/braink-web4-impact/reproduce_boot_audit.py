import ast,contextlib,io,json,tempfile,pathlib,hashlib,sys
SOURCE=pathlib.Path(sys.argv[1]) if len(sys.argv)>1 else pathlib.Path('Pasted text.txt')
text=SOURCE.read_text();start=text.index('# test_runtime_contract.py',text.index('Section 7:'));end=text.index('Use code with caution.',start);code=text[start:end]
# Execute only the supplied hash/verifier functions against isolated temporary files.
# Exclude its runtime import, UI launch and all destructive shell provisioning.
tree=ast.parse(code);safe=ast.Module(body=[n for n in tree.body if isinstance(n,(ast.Import,ast.ImportFrom,ast.FunctionDef))],type_ignores=[])
with tempfile.TemporaryDirectory(prefix='kex-boot-audit-') as tmp:
 root=pathlib.Path(tmp);boot=root/'boot';runtime=root/'runtime';boot.mkdir();(runtime/'slot_a/bin').mkdir(parents=True);(boot/'00_KEX_SENTINEL_SEED.txt').write_bytes(b'0'*32);(boot/'boot_manifest.json').write_text('{"active_slot":"A"}');(boot/'slot_A_manifest.sig').write_text('MOCK_FROST_SIG_A');file=runtime/'slot_a/bin/program.py';file.write_text('VALUE = 1\n')
 class Paths(ast.NodeTransformer):
  def visit_Constant(self,node):
   if node.value=='/mnt/KEX_BOOT':return ast.copy_location(ast.Constant(str(boot)),node)
   if node.value=='/mnt/KEX_RUNTIME':return ast.copy_location(ast.Constant(str(runtime)),node)
   return node
 safe=ast.fix_missing_locations(Paths().visit(safe));scope={};exec(compile(safe,'supplied-boot-functions','exec'),scope)
 def verify():
  with contextlib.redirect_stdout(io.StringIO()):return scope['verify_runtime_substrate']()
 before=verify();file.write_text('VALUE = 999\n');after=verify();(runtime/'slot_a/bin/unverified.bin').write_bytes(b'UNVERIFIED');ignored=verify();file.unlink();empty=verify()
 result={'schema':'kex.supplied.boot.audit.v1','sourceSha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'executionBoundary':'Only extracted hash/verifier functions; paths redirected to temporary fixture; no physical disks, no runtime launch, no provisioning script executed','baselineReturnedSlot':before,'modifiedPythonReturnedSlot':after,'nonPythonFileReturnedSlot':ignored,'emptyPythonDirectoryReturnedSlot':empty,'rejectedTampering':False,'signatureVerificationPresent':False,'expectedHashComparisonPresent':False,'finding':'Supplied illustrative verifier accepts changed Python, additional binary and empty code directory. It computes a digest without authenticating an expected manifest. This does not establish that the original BRAINK compiler/runtime shares these defects.'}
 pathlib.Path(__file__).with_name('boot-audit.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
