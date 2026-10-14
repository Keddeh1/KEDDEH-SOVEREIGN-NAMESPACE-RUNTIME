"""Operational adapter of the owner's Shared KEDDEH HCI contract.

Source: owner upload SHA256 recorded in docs/OWNER_ENVIRONMENT.md.
Supplied layout's fixed hardware/quorum assertions are replaced by readbacks.
"""
import hashlib
class KEDDEHHCIContract:
    def __init__(self, project_name, secure_context=True):
        self.project_name=project_name.upper();self.secure_context=secure_context
        self.active_state='IDLE';self.evidence_manifest={}
    def render_iso_compliant_header(self, contextual_action_label):
        return '\n'.join(['='*69,f' CORE CONSOLE SURFACE // SYSTEM ENGINE: {self.project_name}',
                          f' CURRENT WORKING STATE : [{self.active_state}]',f' ACTIVE VIEW CONTEXT   : {contextual_action_label}','-'*69])
    def render_iso_compliant_footer(self, action_mapping):
        return '\n'.join(['-'*69,' [AVAILABLE SYSTEM CONTROLS]:','   '+' | '.join(f'[{k}] - {v}' for k,v in action_mapping.items()),'='*69])
    def commit_evidence_trace(self, input_action, processing_digest):
        trace=hashlib.sha256(f'{self.project_name}:{input_action}:{processing_digest}'.encode()).hexdigest()[:16]
        self.evidence_manifest[input_action]='EVIDENCE_OK:0x'+trace
        return self.evidence_manifest[input_action]
    def render(self, readback):
        import json
        self.active_state=readback['bilateral']['status'].upper()
        payload=json.dumps(readback,sort_keys=True)
        trace=self.commit_evidence_trace('LIVE_READBACK',hashlib.sha256(payload.encode()).hexdigest())
        return '\n'.join([self.render_iso_compliant_header('KEX / BRAINK / CONTROL PLANE LIVE STATE'),
                          payload,trace,self.render_iso_compliant_footer({'S':'Read state','B':'Bilateral start','P':'Pause actuation','D':'Read domains'})])
