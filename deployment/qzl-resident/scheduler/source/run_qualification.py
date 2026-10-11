import argparse,json,subprocess,hashlib
from pathlib import Path
p=Path(__file__).resolve().parent
ap=argparse.ArgumentParser();ap.add_argument('--yosys',default='yosys');a=ap.parse_args()
prefix='read_verilog -formal {rtl} formal.v; prep -top formal -flatten; async2sync; opt; '
proof='sat -seq 5 -tempinduct -prove-asserts -set-assumes -set-init-zero -verify'
reach='; '.join('sat -seq 5 -set-assumes -set-init-zero -set-at 5 '+n+' 1 -show '+n for n in ['witness_intmin','witness_double','witness_zero'])
def run(rtl,commands,log):
 r=subprocess.run([a.yosys,'-p',prefix.format(rtl=rtl)+commands],cwd=p,capture_output=True,text=True)
 (p/log).write_text(r.stdout+r.stderr);return r
fixed=run('quantum_state_register_128.v',proof+'; '+reach,'corrected-proof.log')
original=run('original.v','sat -seq 5 -prove-asserts -set-assumes -set-init-zero -verify -show in_sreg,out_sreg,operand,opcode,rst_n,align_flag -dump_vcd original-counterexample.vcd','original-proof.log')
checks={'corrected_induction':fixed.returncode==0 and 'Induction step proven: SUCCESS!' in fixed.stdout,'reachable_cases':fixed.stdout.count('SAT solving finished - model found:')==3,'original_counterexample':original.returncode!=0 and 'proof did fail' in (original.stdout+original.stderr) and (p/'original-counterexample.vcd').exists()}
assert all(checks.values()),checks
result={'status':'PASS_WITH_LIMITATIONS','checks':checks,'method':'Yosys SAT temporal induction after async2sync; bounded reachability witnesses','initial_condition':'Reset asserted at first sampled cycle; zero-initialized formal state; subsequent inputs/reset unconstrained','scope':'RTL-level, two-state, sampled-clock behavior; no physical or quantum-hardware qualification','changes':['align_flag now reflects registered out_sreg coordinate','Harness instantiates DUT as formal top','History guards added','Double involution requires feedback of first result','Timestamp checked modulo 2^32'],'unresolved':['Asynchronous reset pulses between clock samples are not independently event-level proven by async2sync','Reset intentionally clears identity/frame; retention excludes reset','32-bit timestamp wraps and follows external input, so global strict monotonicity is not established','16-bit complement is parity-bit encoding, not signed +/-1 arithmetic','null_trap is only this module output; no CPU fault-suppression proof','No silicon synthesis/timing/place-and-route or runtime hardware deployment','Original SVA syntax is not executed with a commercial SVA frontend; replacement harness is Yosys-compatible','Supplied numbered citations have not been independently validated'],'sha256':{n:hashlib.sha256((p/n).read_bytes()).hexdigest() for n in ['original.v','quantum_state_register_128.v','formal.v','formal.sby','corrected-proof.log','original-proof.log','original-counterexample.vcd']}}
(p/'qualification.json').write_text(json.dumps(result,indent=2));print(json.dumps(checks))
