#!/usr/bin/env python3
"""Real FFmpeg/PySceneDetect/faster-whisper processing. No fabricated completions."""
import argparse,json,pathlib,subprocess,sys,re,math

def run(argv):
 p=subprocess.run(argv,capture_output=True,text=True)
 if p.returncode:raise RuntimeError('Process failed: '+argv[0]+'\n'+p.stderr[-3000:])
 return p.stdout

def probe(path):
 d=json.loads(run(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(path)]))
 duration=float(d['format'].get('duration',0));assert math.isfinite(duration) and duration>0,'Source duration unavailable'
 return {'duration':duration,'video':any(x['codec_type']=='video' for x in d['streams']),'audio':any(x['codec_type']=='audio' for x in d['streams'])}

def timestamp(seconds):
 n=round(seconds*1000);return f'{n//3600000:02}:{n//60000%60:02}:{n//1000%60:02},{n%1000:03}'

def process(source,out,options):
 source=pathlib.Path(source);out=pathlib.Path(out);out.mkdir(parents=True,exist_ok=True);profiles=options.get('profiles',['shorts']);info=({'duration':float(options.get('animationSeconds',10)),'video':True,'audio':False} if 'animate' in profiles else probe(source)) if str(source)!='-' else {'duration':10,'video':False,'audio':False};assert profiles and all(x in ['shorts','long','podcast','voiceover','animate'] for x in profiles),'Unsupported processing profile'
 start=float(options.get('start',0));end=min(float(options.get('end',info['duration'])),info['duration']);assert 0<=start<end,'Invalid source range'
 scenes=[]
 if info['video'] and 'shorts' in profiles:
  from scenedetect import detect,ContentDetector
  scenes=[(a.get_seconds(),b.get_seconds()) for a,b in detect(str(source),ContentDetector(threshold=27.0))]
  scenes=[(max(a,start),min(b,end)) for a,b in scenes if b>start and a<end]
 transcript=[];transcription={'state':'not-requested'}
 if options.get('transcribe'):
  if not info['audio']:raise RuntimeError('Transcription requested, but no audio stream exists')
  from faster_whisper import WhisperModel
  model_path=options.get('modelPath')
  if not model_path or not pathlib.Path(model_path).is_dir():raise RuntimeError('A downloaded faster-whisper model is required; no transcript was invented')
  model=WhisperModel(model_path,device='cpu',compute_type='int8',local_files_only=True)
  segments,language=model.transcribe(str(source),beam_size=5,vad_filter=True)
  transcript=[{'start':s.start,'end':s.end,'text':s.text.strip()} for s in segments]
  transcription={'state':'observed','language':language.language,'languageProbability':language.language_probability,'model':str(model_path),'engine':'faster-whisper'}
  (out/'transcript.json').write_text(json.dumps(transcript,indent=2));(out/'transcript.txt').write_text('\n'.join(x['text'] for x in transcript))
 outputs=[];base=['ffmpeg','-nostdin','-hide_banner','-loglevel','error','-y','-threads','2']
 def export(name,offset,duration,kind,filters=None):
  target=out/name;args=base+['-ss',str(offset),'-i',str(source),'-t',str(duration)]
  if kind=='video':
   if not info['video']:raise RuntimeError('Video profile requires a video source; choose podcast for audio sources')
   args+=['-vf',filters,'-c:v','libx264','-preset','veryfast','-crf','20','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-movflags','+faststart']
  else:args+=['-vn','-af','loudnorm=I=-16:TP=-1.5:LRA=11','-c:a','libmp3lame','-b:a','192k']
  run(args+[str(target)]);observed=probe(target);assert abs(observed['duration']-duration)<max(1,duration*.1),'Export duration readback differs'
  captions=[{'start':max(0,x['start']-offset),'end':min(duration,x['end']-offset),'text':x['text']} for x in transcript if x['end']>offset and x['start']<offset+duration]
  title=(captions[0]['text'] if captions else options.get('title') or source.stem)[:90]
  metadata={'transcript':'\n'.join(x['text'] for x in captions),'title':title,'description':options.get('description',''),'sourceRange':{'start':offset,'end':offset+duration},'captionState':'transcribed' if captions else 'not-transcribed','chapters':[{'seconds':max(0,a-offset),'title':f'Section {i+1}'} for i,(a,b) in enumerate(scenes) if offset<=a<offset+duration], 'audiencePromptDraft':'What would you like us to explore next?','reviewRequired':'Check cut coherence, factual claims, caption accuracy, rights and audience context before public publication.'}
  srt='\n\n'.join(f'{i+1}\n{timestamp(x["start"])} --> {timestamp(x["end"])}\n{x["text"]}' for i,x in enumerate(captions));(out/(name+'.srt')).write_text(srt);(out/(name+'.metadata.json')).write_text(json.dumps(metadata,indent=2));outputs.append({'path':str(target),'name':name,'kind':kind,'mime':'video/mp4' if kind=='video' else 'audio/mpeg','duration':observed['duration'],'bytes':target.stat().st_size,'metadata':metadata,'captions':srt})
 if 'voiceover' in profiles:
  script=options.get('voiceScript','').strip()
  if not script:raise RuntimeError('Voice-over script is empty')
  scriptfile=out/'voiceover-script.txt';scriptfile.write_text(script)
  target=out/'voiceover.wav';run(base+['-f','lavfi','-i',f"flite=textfile='{scriptfile}':voice=slt",'-c:a','pcm_s16le',str(target)]);observed=probe(target)
  outputs.append({'path':str(target),'name':'voiceover.wav','kind':'audio','mime':'audio/wav','duration':observed['duration'],'bytes':target.stat().st_size,'metadata':{'title':options.get('title','Voice-over'),'description':options.get('description',''),'transcript':script,'voice':'Flite slt synthetic English voice','reviewRequired':'Review pronunciation, consent and final script before use.'}})
 if 'animate' in profiles:
  target=out/'frame-animation.mp4';duration=float(options.get('animationSeconds',10));assert 1<=duration<=60,'Animation length must be 1–60 seconds'
  run(base+['-loop','1','-i',str(source),'-t',str(duration),'-vf',"scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,zoompan=z='min(zoom+0.0015,1.12)':d=1:s=1280x720:fps=24",'-c:v','libx264','-preset','veryfast','-pix_fmt','yuv420p','-movflags','+faststart',str(target)]);observed=probe(target)
  outputs.append({'path':str(target),'name':'frame-animation.mp4','kind':'video','mime':'video/mp4','duration':observed['duration'],'bytes':target.stat().st_size,'metadata':{'title':options.get('title','Frame animation'),'description':options.get('description',''),'reviewRequired':'Review image rights and motion suitability.'}})
 if 'shorts' in profiles:
  seconds=float(options.get('shortSeconds',30));assert 5<=seconds<=60,'Short length must be 5–60 seconds'
  count=int(options.get('maxShorts',3));assert 1<=count<=10,'Choose 1–10 shorts per batch'
  candidates=[a for a,b in scenes if b-a>=min(5,end-start)] or [start+i*seconds for i in range(count) if start+i*seconds<end]
  if transcript:
   speech=[x['start'] for x in transcript if start<=x['start']<end];candidates=speech or candidates
  for i,offset in enumerate(candidates[:count]):
   duration=min(seconds,end-offset)
   if duration<=0:continue
   export(f'short-{i+1:02}.mp4',offset,duration,'video','scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,setsar=1')
 if 'long' in profiles:export('long-form.mp4',start,end-start,'video','scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1')
 if 'podcast' in profiles:
  if not info['audio']:raise RuntimeError('Podcast export requires a source audio stream')
  export('podcast.mp3',start,end-start,'audio')
 result={'schema':'braink.media.processing.v1','source':str(source),'sourceObservation':({'kind':'script','duration':None,'note':'Text source has no measured media duration'} if str(source)=='-' else {'kind':'image','duration':None,'requestedAnimationSeconds':options.get('animationSeconds',10)} if 'animate' in profiles else info),'sceneBoundaries':scenes,'transcription':transcription,'outputs':outputs,'scope':'Actual file/process observations. Clip candidates use scene/speech boundaries, not a claim of semantic quality or guaranteed engagement.'};(out/'processing.json').write_text(json.dumps(result,indent=2));return result
if __name__=='__main__':
 try:
  p=argparse.ArgumentParser();p.add_argument('source');p.add_argument('output');p.add_argument('--options',required=True);a=p.parse_args();r=process(a.source,a.output,json.loads(pathlib.Path(a.options).read_text()));print(json.dumps(r))
 except Exception as e:print(json.dumps({'state':'failed','error':str(e)}),file=sys.stderr);sys.exit(1)
