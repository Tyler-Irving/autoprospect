import { useState, useEffect, useRef, useCallback } from "react";

// ─── TUNING & FINGERING ───────────────────────────────────────────────────────
const Bb1 = 58.2705;
const PARTIALS      = [2,3,4,5,6,7,8,9,10,11,12];
const PARTIAL_NAMES = ["2nd","3rd","4th","5th","6th","7th♭","8th","9th","10th","11th♯","12th"];
const PARTIAL_NOTES_BASE = ["Bb2","F3","Bb3","D4","F4","Ab4","Bb4","C5","D5","Eb5","F5"];
const NOTE_NAMES = ["C","C#","D","Eb","E","F","F#","G","Ab","A","Bb","B"];

function noteToMidi(name) {
  const m = name.match(/^([A-G](?:#|b)?)(\d)$/);
  if (!m) return 60;
  const chroma = NOTE_NAMES.indexOf(m[1]);
  return (parseInt(m[2]) + 1) * 12 + chroma;
}
function midiToName(midi) {
  const chroma = ((midi % 12) + 12) % 12;
  const oct = Math.floor(midi / 12) - 1;
  return NOTE_NAMES[chroma] + oct;
}
function getValveSemitones(v) { return (v[0]?2:0)+(v[1]?1:0)+(v[2]?3:0); }
function getFreq(pi, v) { return Bb1 * PARTIALS[pi] * Math.pow(2, -getValveSemitones(v)/12); }
function getNoteLabel(pi, v) { return midiToName(noteToMidi(PARTIAL_NOTES_BASE[pi]) - getValveSemitones(v)); }

// ─── AUDIO ENGINE ─────────────────────────────────────────────────────────────
class HornSynth {
  constructor() { this.ctx=null; this.oscs=null; this.playing=false; }

  _init() {
    if (this.ctx) return;
    this.ctx = new (window.AudioContext||window.webkitAudioContext)();
    const ctx = this.ctx;

    // Hall reverb impulse response
    this.reverb = ctx.createConvolver();
    const sr=ctx.sampleRate, len=Math.floor(sr*3.2);
    const ir=ctx.createBuffer(2,len,sr);
    for(let c=0;c<2;c++){
      const d=ir.getChannelData(c);
      for(let i=0;i<len;i++) d[i]=(Math.random()*2-1)*Math.pow(1-i/len,1.5)*(i<sr*0.01?i/(sr*0.01):1);
    }
    this.reverb.buffer=ir;

    // Breath noise (attack transient layer)
    this.noiseGain=ctx.createGain(); this.noiseGain.gain.value=0;
    const nb=ctx.createBuffer(1,sr*4,sr);
    const nd=nb.getChannelData(0);
    for(let i=0;i<sr*4;i++) nd[i]=Math.random()*2-1;
    this.noiseSource=ctx.createBufferSource();
    this.noiseSource.buffer=nb; this.noiseSource.loop=true;
    const nf=ctx.createBiquadFilter();
    nf.type="bandpass"; nf.frequency.value=900; nf.Q.value=0.6;
    this.noiseSource.connect(nf); nf.connect(this.noiseGain);
    this.noiseSource.start();

    // Main tone gain (ADSR)
    this.toneGain=ctx.createGain(); this.toneGain.gain.value=0;

    // Bell simulation: multi-band EQ
    this.hiShelf=ctx.createBiquadFilter();
    this.hiShelf.type="highshelf"; this.hiShelf.frequency.value=3200; this.hiShelf.gain.value=-8;
    this.midPeak=ctx.createBiquadFilter();
    this.midPeak.type="peaking"; this.midPeak.frequency.value=420; this.midPeak.gain.value=5; this.midPeak.Q.value=1.4;
    this.lowCut=ctx.createBiquadFilter();
    this.lowCut.type="highpass"; this.lowCut.frequency.value=55;
    this.lpf=ctx.createBiquadFilter();
    this.lpf.type="lowpass"; this.lpf.frequency.value=2400; this.lpf.Q.value=0.5;

    // Compressor (subtle — just prevents clipping)
    this.comp=ctx.createDynamicsCompressor();
    this.comp.threshold.value=-14; this.comp.knee.value=6; this.comp.ratio.value=2.5;
    this.comp.attack.value=0.004; this.comp.release.value=0.18;

    // Master
    this.master=ctx.createGain(); this.master.gain.value=0.68;

    // Dry / wet split
    this.dryG=ctx.createGain(); this.dryG.gain.value=0.60;
    this.wetG=ctx.createGain(); this.wetG.gain.value=0.40;

    // Chain
    this.toneGain.connect(this.lowCut);
    this.lowCut.connect(this.midPeak);
    this.midPeak.connect(this.hiShelf);
    this.hiShelf.connect(this.lpf);
    this.lpf.connect(this.dryG);
    this.lpf.connect(this.reverb);
    this.reverb.connect(this.wetG);
    this.dryG.connect(this.comp);
    this.wetG.connect(this.comp);
    this.noiseGain.connect(this.comp);
    this.comp.connect(this.master);
    this.master.connect(ctx.destination);

    // Vibrato LFO
    this.lfo=ctx.createOscillator();
    this.lfoAmt=ctx.createGain(); this.lfoAmt.gain.value=0;
    this.lfo.type="sine"; this.lfo.frequency.value=5.4;
    this.lfo.connect(this.lfoAmt); this.lfo.start();
  }

  play(freq) {
    this._init();
    this._stopOscs();
    const ctx=this.ctx, now=ctx.currentTime;

    // Harmonic series (rich brass timbre)
    const harms=[
      [1,0.55],[2,0.35],[3,0.24],[4,0.17],[5,0.12],
      [6,0.085],[7,0.06],[8,0.042],[9,0.028],[10,0.018],
    ];
    this.oscs=harms.map(([mult,amp])=>{
      const o=ctx.createOscillator(), g=ctx.createGain();
      o.type="sawtooth";
      o.frequency.value=freq*mult;
      o.detune.value=(Math.random()-0.5)*5;
      g.gain.value=amp*0.20;
      this.lfoAmt.connect(o.frequency);
      o.connect(g); g.connect(this.toneGain);
      o.start(now); return {o,g,mult};
    });
    this.currentFreq=freq;

    // ADSR: attack 80ms, instant sustain
    this.toneGain.gain.cancelScheduledValues(now);
    this.toneGain.gain.setValueAtTime(0,now);
    this.toneGain.gain.linearRampToValueAtTime(0.08,now+0.010); // lip buzz transient
    this.toneGain.gain.linearRampToValueAtTime(1.0,now+0.082);

    // Breath noise burst
    this.noiseGain.gain.cancelScheduledValues(now);
    this.noiseGain.gain.setValueAtTime(0,now);
    this.noiseGain.gain.linearRampToValueAtTime(0.035,now+0.014);
    this.noiseGain.gain.exponentialRampToValueAtTime(0.006,now+0.18);
    this.noiseGain.gain.setTargetAtTime(0.003,now+0.18,0.4);

    // Vibrato: delayed onset, natural ramp-in
    this.lfoAmt.gain.cancelScheduledValues(now);
    this.lfoAmt.gain.setValueAtTime(0,now);
    this.lfoAmt.gain.setValueAtTime(0,now+0.40);
    this.lfoAmt.gain.linearRampToValueAtTime(freq*0.009,now+0.95);

    this.playing=true;
  }

  setFreq(freq) {
    if(!this.playing||!this.oscs) return;
    const ctx=this.ctx, now=ctx.currentTime;
    this.oscs.forEach(({o,mult})=>o.frequency.setTargetAtTime(freq*mult,now,0.022));
    this.lfoAmt.gain.setTargetAtTime(freq*0.009,now,0.06);
    this.currentFreq=freq;
  }

  _stopOscs() {
    if(!this.oscs) return;
    const o=this.oscs;
    setTimeout(()=>o.forEach(({o})=>{try{o.stop();}catch(e){}}),600);
    this.oscs=null;
  }

  stop() {
    if(!this.ctx||!this.playing) return;
    const ctx=this.ctx, now=ctx.currentTime;
    this.toneGain.gain.setTargetAtTime(0,now,0.10);
    this.noiseGain.gain.setTargetAtTime(0,now,0.04);
    this.lfoAmt.gain.setTargetAtTime(0,now,0.04);
    this._stopOscs();
    this.playing=false;
  }

  resume() { if(this.ctx?.state==="suspended") this.ctx.resume(); }
}

const synth = new HornSynth();

// ─── SVG: Tube helper (3-layer cylindrical shading) ──────────────────────────
function Tube({ d, r=11, shadow=true }) {
  return (
    <g>
      {shadow&&<path d={d} fill="none" stroke="rgba(0,0,0,0.6)" strokeWidth={r*2+6} strokeLinecap="round"/>}
      {/* Dark underside */}
      <path d={d} fill="none" stroke="url(#tDark)" strokeWidth={r*2+1} strokeLinecap="round"/>
      {/* Main brass body */}
      <path d={d} fill="none" stroke="url(#tBody)" strokeWidth={r*2-1} strokeLinecap="round"/>
      {/* Bright midtone */}
      <path d={d} fill="none" stroke="url(#tMid)" strokeWidth={r*1.1} strokeLinecap="round" opacity="0.8"/>
      {/* Specular streak */}
      <path d={d} fill="none" stroke="url(#tSpec)" strokeWidth={r*0.38} strokeLinecap="round" opacity="0.7"/>
      {/* Hot spot */}
      <path d={d} fill="none" stroke="rgba(255,252,200,0.30)" strokeWidth={r*0.14} strokeLinecap="round"/>
    </g>
  );
}

function SlideH({ x, y, w, h=9 }) {
  return (
    <g>
      <rect x={x} y={y} width={w} height={h+5} rx={h/2+2.5} fill="rgba(0,0,0,0.55)"/>
      <rect x={x} y={y} width={w} height={h+3} rx={h/2+1.5} fill="url(#tDark)"/>
      <rect x={x} y={y+1} width={w} height={h+1} rx={h/2+0.5} fill="url(#tBody)"/>
      <rect x={x+2} y={y+2} width={w-4} height={h-3} rx={h/2-1} fill="url(#tSpec)" opacity="0.55"/>
      <rect x={x+4} y={y+2.5} width={w-8} height={2.5} rx={1.2} fill="rgba(255,252,180,0.18)"/>
    </g>
  );
}

// ─── ROTARY VALVE ─────────────────────────────────────────────────────────────
function RotaryValve({ x, y, index, active, keyLabel }) {
  const rot = active ? 90 : 0;
  // Blued steel palette per valve
  const blues=[["#263f6a","#3f63a8","#6a96d8"],["#1e3460","#375a98","#5f88cc"],["#2b4672","#4570b2","#7aa2e0"]];
  const [dark,mid,lite]=blues[index];

  return (
    <g transform={`translate(${x},${y})`} style={{cursor:"pointer"}}>
      {/* Active glow */}
      {active&&<>
        <circle r="34" fill="rgba(70,130,255,0.04)">
          <animate attributeName="r" values="32;40;32" dur="2.2s" repeatCount="indefinite"/>
        </circle>
        <circle r="28" fill="none" stroke="#5090e8" strokeWidth="1.2" opacity="0.22">
          <animate attributeName="opacity" values="0.22;0.05;0.22" dur="2.2s" repeatCount="indefinite"/>
        </circle>
      </>}

      {/* Cast housing — drop shadow */}
      <circle r="25" fill="rgba(0,0,0,0.6)" cx="2" cy="3"/>
      {/* Housing outer ring (brass) */}
      <circle r="25" fill="url(#housingRing)" stroke="#5a3e08" strokeWidth="1.2"/>
      <circle r="23.5" fill="none" stroke="rgba(220,180,60,0.15)" strokeWidth="0.7"/>
      {/* Housing bore (rotor sits inside) */}
      <circle r="21" fill="url(#housingBore)"/>
      {/* Bore chamfer */}
      <circle r="21" fill="none" stroke="rgba(80,50,10,0.5)" strokeWidth="1"/>

      {/* Rotor disc */}
      <g style={{transform:`rotate(${rot}deg)`,transformOrigin:"0 0",
                 transition:"transform 0.26s cubic-bezier(0.34,1.56,0.64,1)"}}>
        <circle r="19" fill="url(#rotorFace)" stroke="#6a4a0a" strokeWidth="0.8"/>
        {/* Air passage channels (dark bores) */}
        <path d="M-19,0 C-12,-8 -5,-10 0,-10 L0,10 C-5,10 -12,8 -19,0Z" fill="#060402" opacity="0.92"/>
        <path d="M0,-19 C8,-12 10,-5 10,0 L-10,0 C-10,-5 -8,-12 0,-19Z" fill="#060402" opacity="0.92"/>
        {/* Channel entry rims (catch light) */}
        <path d="M-19,0 C-14,-6 -7,-9.5 0,-9.5" fill="none" stroke="rgba(200,170,60,0.35)" strokeWidth="1.2"/>
        <path d="M0,-19 C6,-14 9.5,-7 9.5,0" fill="none" stroke="rgba(200,170,60,0.35)" strokeWidth="1.2"/>
        {/* Rotor face etching */}
        <circle r="6" fill="url(#rotorCenterGrad)" stroke="rgba(180,140,40,0.3)" strokeWidth="0.5"/>
        <circle r="3" fill="rgba(80,55,10,0.7)"/>
        <circle r="1.2" fill="rgba(220,190,80,0.2)"/>
        {/* Alignment marks */}
        <line x1="-18" y1="0" x2="-7" y2="0" stroke="rgba(200,160,40,0.18)" strokeWidth="0.8"/>
        <line x1="7" y1="0" x2="18" y2="0" stroke="rgba(200,160,40,0.18)" strokeWidth="0.8"/>
        <line x1="0" y1="-18" x2="0" y2="-7" stroke="rgba(200,160,40,0.18)" strokeWidth="0.8"/>
        <line x1="0" y1="7" x2="0" y2="18" stroke="rgba(200,160,40,0.18)" strokeWidth="0.8"/>
      </g>

      {/* Cap (blued steel) — sits over rotor */}
      {/* Cap drop shadow */}
      <circle r="16" fill="rgba(0,0,0,0.45)" cx="1" cy="1.5"/>
      {/* Cap body */}
      <circle r="16" fill={dark}/>
      <circle r="16" fill="url(#capRadial)" opacity="0.9"/>
      {/* Cap bevel ring */}
      <circle r="16" fill="none" stroke="rgba(150,200,255,0.22)" strokeWidth="1.4"/>
      <circle r="14.8" fill="none" stroke="rgba(80,120,200,0.18)" strokeWidth="0.6"/>
      {/* Cap surface sheen */}
      <ellipse cx="-4" cy="-6" rx="5.5" ry="3.5" fill="rgba(180,220,255,0.16)" transform="rotate(-30,-4,-6)"/>
      <circle r="2" fill="rgba(210,235,255,0.5)" cx="-5" cy="-7"/>
      {/* Steel surface micro-texture: four faint concentric rings */}
      {[5,8,11,13.5].map((rr,i)=>(
        <circle key={i} r={rr} fill="none" stroke="rgba(150,190,255,0.05)" strokeWidth="0.5"/>
      ))}
      {/* Center screw (slotted hex) */}
      <circle r="4.5" fill={dark} stroke="rgba(160,210,255,0.3)" strokeWidth="0.8"/>
      <circle r="3" fill={mid} stroke="rgba(140,190,255,0.2)" strokeWidth="0.5"/>
      <circle r="1.4" fill={lite} opacity="0.7"/>
      <line x1="-4" y1="0" x2="4" y2="0" stroke="rgba(160,210,255,0.35)" strokeWidth="0.9"/>
      <line x1="0" y1="-4" x2="0" y2="4" stroke="rgba(160,210,255,0.35)" strokeWidth="0.9"/>

      {/* Lever arm (rotates with rotor) */}
      <g style={{transform:`rotate(${rot}deg)`,transformOrigin:"0 0",
                 transition:"transform 0.26s cubic-bezier(0.34,1.56,0.64,1)"}}>
        {/* Arm shadow */}
        <rect x="-4" y="24" width="8" height="34" rx="3" fill="rgba(0,0,0,0.45)" transform="translate(1.5,1.5)"/>
        {/* Arm body (brass) */}
        <rect x="-4" y="24" width="8" height="34" rx="3" fill="url(#leverBody)" stroke="#5a3808" strokeWidth="0.8"/>
        {/* Arm highlight */}
        <rect x="-1.5" y="25" width="2.5" height="31" rx="1.2" fill="rgba(255,240,140,0.18)"/>
        {/* Thumb plate */}
        <rect x="-10" y="54" width="20" height="7.5" rx="3.8" fill="url(#leverPaddle)" stroke="#5a3808" strokeWidth="0.8"/>
        <rect x="-7.5" y="55.5" width="15" height="3.5" rx="1.8" fill="rgba(255,240,140,0.14)"/>
        {/* Pivot knuckle */}
        <circle cx="0" cy="24" r="4.5" fill="url(#pivotBall)" stroke="#5a3808" strokeWidth="0.8"/>
        <circle cx="-1.2" cy="22.8" r="1.5" fill="rgba(255,240,150,0.32)"/>
      </g>

      {/* Key indicator */}
      <g transform={`translate(0,${-38})`}>
        <rect x="-11" y="-8.5" width="22" height="15" rx="4"
          fill={active?"rgba(60,120,240,0.28)":"rgba(15,10,2,0.75)"}
          stroke={active?"rgba(100,170,255,0.55)":"rgba(180,140,40,0.2)"}
          strokeWidth="0.9" style={{transition:"all 0.2s"}}/>
        <text textAnchor="middle" y="2" fontSize="8.5" fontFamily="monospace"
          fill={active?"#a0d4ff":"rgba(200,168,75,0.65)"} style={{userSelect:"none",transition:"fill 0.2s"}}>
          {keyLabel}
        </text>
      </g>
    </g>
  );
}

// ─── MAIN COMPONENT ───────────────────────────────────────────────────────────
export default function FrenchHorn() {
  const [valves,setValves]         = useState([false,false,false]);
  const [blowing,setBlowing]       = useState(false);
  const [partialIdx,setPartialIdx] = useState(4);
  const [started,setStarted]       = useState(false);
  const blowRef    = useRef(false);
  const valvesRef  = useRef([false,false,false]);
  const partialRef = useRef(4);

  useEffect(()=>{ valvesRef.current=valves; },[valves]);
  useEffect(()=>{ partialRef.current=partialIdx; },[partialIdx]);

  const pressValve   = useCallback((i)=>setValves(v=>{const n=[...v];n[i]=true;return n;}),[]);
  const releaseValve = useCallback((i)=>setValves(v=>{const n=[...v];n[i]=false;return n;}),[]);
  const toggleValve  = useCallback((i)=>setValves(v=>{const n=[...v];n[i]=!n[i];return n;}),[]);

  const startBlow = useCallback(()=>{
    if(blowRef.current) return;
    blowRef.current=true; setBlowing(true); setStarted(true);
    synth.resume();
    synth.play(getFreq(partialRef.current, valvesRef.current));
  },[]);

  const stopBlow = useCallback(()=>{
    if(!blowRef.current) return;
    blowRef.current=false; setBlowing(false);
    synth.stop();
  },[]);

  useEffect(()=>{
    if(blowRef.current) synth.setFreq(getFreq(partialIdx,valves));
  },[valves,partialIdx]);

  useEffect(()=>{
    const kd=(e)=>{
      if(e.repeat) return;
      if(e.code==="Space"){e.preventDefault();startBlow();}
      if(e.key==="1") pressValve(0);
      if(e.key==="2") pressValve(1);
      if(e.key==="3") pressValve(2);
      if(e.code==="ArrowUp"){e.preventDefault();setPartialIdx(p=>Math.min(PARTIALS.length-1,p+1));}
      if(e.code==="ArrowDown"){e.preventDefault();setPartialIdx(p=>Math.max(0,p-1));}
    };
    const ku=(e)=>{
      if(e.code==="Space"){e.preventDefault();stopBlow();}
      if(e.key==="1") releaseValve(0);
      if(e.key==="2") releaseValve(1);
      if(e.key==="3") releaseValve(2);
    };
    window.addEventListener("keydown",kd);
    window.addEventListener("keyup",ku);
    return()=>{window.removeEventListener("keydown",kd);window.removeEventListener("keyup",ku);};
  },[startBlow,stopBlow,pressValve,releaseValve]);

  const noteLabel  = getNoteLabel(partialIdx,valves);
  const freq       = getFreq(partialIdx,valves);
  const semitones  = getValveSemitones(valves);
  const activeCount= valves.filter(Boolean).length;

  return (
    <div style={{
      minHeight:"100vh",
      background:"radial-gradient(ellipse 90% 65% at 38% 48%, #1c1306 0%, #0d0c08 45%, #050504 100%)",
      display:"flex",flexDirection:"column",alignItems:"center",justifyContent:"center",
      fontFamily:"'Palatino Linotype','Book Antiqua',Palatino,serif",
      padding:"16px 12px",position:"relative",overflow:"hidden",
    }}>
      {/* Stage light bloom */}
      <div style={{position:"absolute",top:"38%",left:"58%",transform:"translate(-50%,-50%)",
        width:"560px",height:"380px",borderRadius:"50%",pointerEvents:"none",
        background:"radial-gradient(ellipse,rgba(190,148,45,0.08) 0%,transparent 68%)"}}/>
      <div style={{position:"absolute",top:"55%",left:"50%",transform:"translate(-50%,-50%)",
        width:"700px",height:"200px",borderRadius:"50%",pointerEvents:"none",
        background:"radial-gradient(ellipse,rgba(0,0,0,0) 0%,rgba(0,0,0,0.5) 100%)"}}/>

      {/* Title */}
      <div style={{textAlign:"center",marginBottom:"10px"}}>
        <div style={{fontSize:"8.5px",letterSpacing:"7px",color:"#4a380f",textTransform:"uppercase",marginBottom:"5px"}}>
          Bb / F Double · Hand-lacquered Yellow Brass
        </div>
        <h1 style={{margin:"0 0 3px",fontSize:"clamp(20px,3.8vw,38px)",color:"#c8a84c",fontWeight:400,
          letterSpacing:"3px",textShadow:"0 0 55px rgba(195,160,55,0.38),0 2px 6px rgba(0,0,0,0.9)"}}>
          French Horn
        </h1>
        <div style={{fontSize:"8px",letterSpacing:"4px",color:"#3a2c0a",textTransform:"uppercase"}}>
          Rotary Valve Mechanism · Concert Pitch
        </div>
      </div>

      {/* ── SVG ─────────────────────────────────────────────────────────── */}
      <svg viewBox="0 0 840 575" width="min(840px,98vw)"
        style={{overflow:"visible",filter:"drop-shadow(0 28px 90px rgba(0,0,0,0.97))"}}>
        <defs>
          {/* Tube layers */}
          <linearGradient id="tDark" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#6a4010"/><stop offset="50%" stopColor="#361c04"/><stop offset="100%" stopColor="#140800"/>
          </linearGradient>
          <linearGradient id="tBody" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#e8c855"/><stop offset="22%" stopColor="#d4aa3c"/>
            <stop offset="55%" stopColor="#a07820"/><stop offset="82%" stopColor="#6a4610"/><stop offset="100%" stopColor="#3c2004"/>
          </linearGradient>
          <linearGradient id="tMid" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#f8e070"/><stop offset="40%" stopColor="#dbb840"/>
            <stop offset="80%" stopColor="#a07820"/><stop offset="100%" stopColor="rgba(100,60,10,0)"/>
          </linearGradient>
          <linearGradient id="tSpec" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#fffae0"/><stop offset="35%" stopColor="#f0d868"/>
            <stop offset="100%" stopColor="rgba(200,160,40,0)"/>
          </linearGradient>

          {/* Bell */}
          <radialGradient id="bellFill" cx="62%" cy="26%" r="65%">
            <stop offset="0%"  stopColor="#faf080"/><stop offset="15%" stopColor="#ead060"/>
            <stop offset="40%" stopColor="#c09530"/><stop offset="70%" stopColor="#8a5e14"/>
            <stop offset="100%" stopColor="#4a2c06"/>
          </radialGradient>

          {/* Valve housing */}
          <radialGradient id="housingRing" cx="36%" cy="30%" r="70%">
            <stop offset="0%"  stopColor="#e0b840"/><stop offset="35%" stopColor="#b88c28"/>
            <stop offset="72%" stopColor="#7a5010"/><stop offset="100%" stopColor="#402204"/>
          </radialGradient>
          <radialGradient id="housingBore" cx="33%" cy="28%" r="65%">
            <stop offset="0%"  stopColor="#c8a030"/><stop offset="50%" stopColor="#8c6015"/>
            <stop offset="100%" stopColor="#4a2808"/>
          </radialGradient>
          <radialGradient id="rotorFace" cx="32%" cy="27%" r="65%">
            <stop offset="0%"  stopColor="#b89030"/><stop offset="50%" stopColor="#7a5515"/>
            <stop offset="100%" stopColor="#3e2006"/>
          </radialGradient>
          <radialGradient id="rotorCenterGrad" cx="38%" cy="32%">
            <stop offset="0%"  stopColor="#d0a838"/><stop offset="100%" stopColor="#5a3808"/>
          </radialGradient>

          {/* Blued cap radial overlay */}
          <radialGradient id="capRadial" cx="33%" cy="27%" r="68%">
            <stop offset="0%"  stopColor="rgba(180,220,255,0.45)"/>
            <stop offset="45%" stopColor="rgba(80,130,220,0.08)"/>
            <stop offset="100%" stopColor="rgba(20,50,140,0)"/>
          </radialGradient>

          {/* Levers & hardware */}
          <linearGradient id="leverBody" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%"  stopColor="#6a4010"/><stop offset="35%" stopColor="#d0a030"/>
            <stop offset="65%" stopColor="#e8c050"/><stop offset="100%" stopColor="#7a4c14"/>
          </linearGradient>
          <linearGradient id="leverPaddle" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%"  stopColor="#7a5014"/><stop offset="40%" stopColor="#c89830"/><stop offset="100%" stopColor="#6a4010"/>
          </linearGradient>
          <radialGradient id="pivotBall" cx="33%" cy="28%">
            <stop offset="0%"  stopColor="#e0be48"/><stop offset="100%" stopColor="#5a3408"/>
          </radialGradient>

          {/* Mouthpiece */}
          <linearGradient id="mpG" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%"  stopColor="#e4e4e4"/><stop offset="28%" stopColor="#f8f8f4"/>
            <stop offset="68%" stopColor="#acacac"/><stop offset="100%" stopColor="#c8c8c8"/>
          </linearGradient>

          {/* Floor reflection gradient */}
          <linearGradient id="floorGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%"  stopColor="rgba(170,130,35,0.20)"/>
            <stop offset="100%" stopColor="rgba(0,0,0,0)"/>
          </linearGradient>

          {/* Filters */}
          <filter id="sfShadow"><feDropShadow dx="2" dy="5" stdDeviation="9" floodColor="#000" floodOpacity="0.75"/></filter>
          <filter id="patina" x="-8%" y="-8%" width="116%" height="116%">
            <feTurbulence type="fractalNoise" baseFrequency="0.55" numOctaves="4" seed="8" result="n"/>
            <feColorMatrix type="saturate" values="0" in="n" result="gn"/>
            <feBlend in="SourceGraphic" in2="gn" mode="overlay" result="b"/>
            <feComposite in="b" in2="SourceGraphic" operator="in"/>
          </filter>
        </defs>

        {/* Floor reflection */}
        <ellipse cx="420" cy="548" rx="270" ry="24" fill="url(#floorGrad)" opacity="0.9"/>

        {/* ── COILED TUBING ── */}
        {/* Outer main loop */}
        <Tube r={12.5} shadow
          d="M 395,415 C 238,418 95,350 78,232 C 61,114 158,40 272,35 C 365,31 448,78 478,158"/>
        {/* Second inner loop */}
        <Tube r={10.5}
          d="M 420,372 C 296,375 196,318 182,242 C 168,166 236,102 318,97 C 385,93 445,132 466,198"/>
        {/* Third loop */}
        <Tube r={9.5}
          d="M 432,332 C 340,332 268,298 256,240 C 244,182 294,138 358,134 C 406,131 450,162 465,208"/>

        {/* Valve inlet/outlet verticals */}
        <Tube r={11} shadow={false} d="M 478,158 L 480,205"/>
        <Tube r={11} shadow={false} d="M 480,335 L 482,355 C 492,390 524,430 570,452 C 608,470 648,465 678,445"/>

        {/* Bell throat */}
        <Tube r={14} d="M 678,445 C 696,432 714,412 722,388 C 733,356 728,316 712,286"/>

        {/* ── Bell flare ── */}
        <g filter="url(#sfShadow)">
          <path d="M 712,286
                   C 698,258 668,240 642,242
                   C 614,244 592,262 580,286
                   C 565,318 572,356 592,376
                   C 610,394 638,402 662,400
                   C 688,398 710,382 720,360
                   C 732,336 726,304 712,286Z"
            fill="url(#bellFill)" stroke="rgba(90,58,8,0.55)" strokeWidth="1.5"/>
        </g>
        {/* Bell inner */}
        <ellipse cx="712" cy="287" rx="36" ry="44" fill="#060402" opacity="0.98"/>
        <ellipse cx="710" cy="285" rx="26" ry="33" fill="#020101"/>
        {/* Bell rim specular */}
        <path d="M 678,445 C 696,432 714,412 722,388 C 733,356 728,316 712,286"
          fill="none" stroke="rgba(255,248,140,0.52)" strokeWidth="2.2"/>
        {/* Bell body highlight (upper curve) */}
        <path d="M 580,286 C 565,318 572,356 592,376 C 610,394 638,402 662,400"
          fill="none" stroke="rgba(220,175,55,0.22)" strokeWidth="3.5"/>
        {/* Patina/texture on bell */}
        <path d="M 712,286
                 C 698,258 668,240 642,242 C 614,244 592,262 580,286
                 C 565,318 572,356 592,376 C 610,394 638,402 662,400
                 C 688,398 710,382 720,360 C 732,336 726,304 712,286Z"
          fill="rgba(255,220,80,0.04)" style={{filter:"url(#patina)"}} strokeWidth="0"/>
        {/* Hand-engraving */}
        <g opacity="0.40" strokeLinecap="round">
          <path d="M 625,248 Q 640,236 646,244 Q 655,256 644,265 Q 632,270 624,261" fill="none" stroke="#c8a040" strokeWidth="1.3"/>
          <path d="M 620,267 Q 626,255 637,253 Q 647,257 643,268" fill="none" stroke="#c8a040" strokeWidth="1"/>
          <path d="M 617,282 Q 628,274 636,279 Q 641,286 633,291" fill="none" stroke="#c8a040" strokeWidth="0.9"/>
          <path d="M 606,256 Q 616,248 623,254" fill="none" stroke="#c8a040" strokeWidth="0.8"/>
          <path d="M 609,270 Q 614,265 620,268" fill="none" stroke="#c8a040" strokeWidth="0.7"/>
        </g>

        {/* ── Tuning slides ── */}
        {[0,1,2].map(i=>(
          <g key={i}>
            <SlideH x={498} y={208+i*46} w={108} h={10}/>
            {/* U-bend return */}
            <path d={`M 606,${208+i*46} Q 636,${208+i*46} 636,${213+i*46+5} Q 636,${222+i*46} 606,${222+i*46}`}
              fill="none" stroke="rgba(0,0,0,0.55)" strokeWidth="18" strokeLinecap="round"/>
            <path d={`M 606,${208+i*46} Q 632,${208+i*46} 632,${213+i*46+5} Q 632,${221+i*46} 606,${221+i*46}`}
              fill="none" stroke="url(#tBody)" strokeWidth="14" strokeLinecap="round"/>
            <path d={`M 606,${208+i*46} Q 627,${209+i*46} 627,${213+i*46+5} Q 627,${220+i*46} 606,${220+i*46}`}
              fill="none" stroke="rgba(255,248,160,0.12)" strokeWidth="5" strokeLinecap="round"/>
          </g>
        ))}

        {/* Vertical cluster tubes */}
        <Tube r={10.5} shadow={false} d="M 480,205 L 480,335"/>
        <Tube r={10.5} shadow={false} d="M 502,205 L 502,335"/>

        {/* ── Leadpipe ── */}
        <Tube r={10.5} d="M 395,415 C 380,436 356,452 326,458 C 300,463 274,455 252,446"/>
        {/* Mouthpiece receiver */}
        <path d="M 252,446 L 205,442" fill="none" stroke="rgba(0,0,0,0.55)" strokeWidth="20" strokeLinecap="round"/>
        <path d="M 252,446 L 205,442" fill="none" stroke="url(#mpG)" strokeWidth="16" strokeLinecap="round"/>
        <path d="M 252,446 L 205,442" fill="none" stroke="rgba(255,255,255,0.13)" strokeWidth="5.5" strokeLinecap="round"/>
        {/* Shank */}
        <path d="M 205,442 L 165,439" fill="none" stroke="rgba(0,0,0,0.45)" strokeWidth="15" strokeLinecap="round"/>
        <path d="M 205,442 L 165,439" fill="none" stroke="url(#mpG)" strokeWidth="11" strokeLinecap="round"/>
        <path d="M 205,442 L 165,439" fill="none" stroke="rgba(255,255,255,0.16)" strokeWidth="3.5" strokeLinecap="round"/>
        {/* Cup */}
        <ellipse cx="162" cy="439" rx="14" ry="12" fill="url(#mpG)" stroke="rgba(155,155,155,0.55)" strokeWidth="1.3"/>
        <ellipse cx="160" cy="438" rx="10" ry="8.5" fill="#d4d4d4"/>
        <ellipse cx="162" cy="439" rx="6.5" ry="6" fill="#141414"/>
        <ellipse cx="159" cy="437" rx="2.8" ry="2.2" fill="rgba(255,255,255,0.07)"/>

        {/* ── Braces / stays ── */}
        <line x1="335" y1="140" x2="395" y2="415" stroke="#8a6218" strokeWidth="5.5" strokeLinecap="round" opacity="0.65"/>
        <circle cx="335" cy="140" r="7.5" fill="url(#pivotBall)" stroke="#6a4810" strokeWidth="1"/>
        <circle cx="335" cy="140" r="3.2" fill="rgba(255,240,150,0.32)"/>
        <circle cx="395" cy="415" r="7.5" fill="url(#pivotBall)" stroke="#6a4810" strokeWidth="1"/>
        <circle cx="395" cy="415" r="3.2" fill="rgba(255,240,150,0.32)"/>

        <line x1="284" y1="188" x2="420" y2="372" stroke="#8a6218" strokeWidth="4.5" strokeLinecap="round" opacity="0.52"/>
        <circle cx="284" cy="188" r="6" fill="url(#pivotBall)" stroke="#6a4810" strokeWidth="0.9"/>
        <circle cx="420" cy="372" r="6" fill="url(#pivotBall)" stroke="#6a4810" strokeWidth="0.9"/>

        {/* ── Water key ── */}
        <circle cx="308" cy="468" r="7" fill="#b09030" stroke="#7a6018" strokeWidth="1.1"/>
        <line x1="308" y1="461" x2="308" y2="452" stroke="#9a8020" strokeWidth="3"/>
        <circle cx="308" cy="450" r="4" fill="#c8a040" stroke="#8a6010" strokeWidth="0.9"/>
        <circle cx="306.5" cy="448.5" r="1.8" fill="rgba(255,240,150,0.32)"/>

        {/* ── ROTARY VALVES (main subject) ── */}
        {[0,1,2].map(i=>(
          <RotaryValve key={i} x={480} y={227+i*46}
            index={i} active={valves[i]}
            keyLabel={String(i+1)}
            onToggle={()=>toggleValve(i)}/>
        ))}

        {/* Annotation lines */}
        {[0,1,2].map(i=>(
          <g key={i} opacity="0.85">
            <line x1="234" y1={227+i*46} x2={444} y2={227+i*46}
              stroke="rgba(200,168,75,0.12)" strokeWidth="0.7" strokeDasharray="4,6"/>
            <text x="229" y={222+i*46} textAnchor="end" fontSize="8.5" fill={valves[i]?"rgba(110,185,255,0.72)":"rgba(200,168,75,0.38)"} fontFamily="Palatino,serif" style={{transition:"fill 0.25s"}}>
              {["1st Valve","2nd Valve","3rd Valve"][i]}
            </text>
            <text x="229" y={232+i*46} textAnchor="end" fontSize="7" fill="rgba(140,106,30,0.5)" fontFamily="Palatino,serif">
              {["−2 semitones","−1 semitone","−3 semitones"][i]}
            </text>
          </g>
        ))}
      </svg>

      {/* ── INSTRUMENT PANEL ────────────────────────────────────────── */}
      <div style={{marginTop:"8px",display:"flex",alignItems:"stretch",gap:"8px",flexWrap:"wrap",justifyContent:"center"}}>

        {/* Pitch display */}
        <div style={{
          background:"linear-gradient(150deg,rgba(28,20,4,0.92),rgba(10,8,2,0.96))",
          border:"1px solid rgba(200,168,75,0.16)",borderRadius:"12px",
          padding:"12px 22px",textAlign:"center",minWidth:"96px",
          boxShadow:"inset 0 1px 0 rgba(255,240,120,0.06),0 4px 24px rgba(0,0,0,0.6)",
        }}>
          <div style={{fontSize:"7.5px",letterSpacing:"4px",color:"#45330c",textTransform:"uppercase",marginBottom:"4px"}}>Concert Pitch</div>
          <div style={{fontSize:"44px",lineHeight:1,color:"#c8a84c",fontWeight:400,
            textShadow:"0 0 26px rgba(198,162,55,0.65)",transition:"all 0.12s"}}>
            {noteLabel}
          </div>
          <div style={{fontSize:"8px",color:"rgba(155,118,28,0.55)",marginTop:"4px"}}>{freq.toFixed(1)} Hz</div>
          {blowing&&<div style={{marginTop:"6px",display:"flex",justifyContent:"center",gap:"3px"}}>
            {[0,1,2,3,4].map(i=>(
              <div key={i} style={{width:"3px",background:"#c8a84c",borderRadius:"1.5px",
                animation:`breathBar 0.5s ${i*0.08}s ease-in-out infinite alternate`,
                height:"6px",opacity:0.7}}/>
            ))}
          </div>}
        </div>

        {/* Harmonic partial selector */}
        <div style={{
          background:"linear-gradient(150deg,rgba(28,20,4,0.92),rgba(10,8,2,0.96))",
          border:"1px solid rgba(200,168,75,0.16)",borderRadius:"12px",
          padding:"10px 14px",
          boxShadow:"inset 0 1px 0 rgba(255,240,120,0.06),0 4px 24px rgba(0,0,0,0.6)",
        }}>
          <div style={{fontSize:"7.5px",letterSpacing:"4px",color:"#45330c",textTransform:"uppercase",marginBottom:"7px",textAlign:"center"}}>
            Harmonic · ↑ ↓
          </div>
          <div style={{display:"flex",flexDirection:"column",gap:"1.5px"}}>
            {PARTIALS.map((_,i)=>(
              <div key={i} onClick={()=>setPartialIdx(i)}
                style={{
                  cursor:"pointer",padding:"1.5px 10px",borderRadius:"4px",fontSize:"8.5px",
                  background:i===partialIdx?"rgba(195,162,58,0.18)":"transparent",
                  color:i===partialIdx?"#c8a84c":"rgba(148,114,36,0.42)",
                  border:`1px solid ${i===partialIdx?"rgba(195,162,58,0.28)":"transparent"}`,
                  transition:"all 0.12s",display:"flex",justifyContent:"space-between",gap:"16px",letterSpacing:"0.4px",
                }}>
                <span>{PARTIAL_NAMES[i]}</span>
                <span style={{opacity:0.65}}>{PARTIAL_NOTES_BASE[i]}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Play controls */}
        <div style={{
          background:"linear-gradient(150deg,rgba(28,20,4,0.92),rgba(10,8,2,0.96))",
          border:"1px solid rgba(200,168,75,0.16)",borderRadius:"12px",
          padding:"12px 16px",display:"flex",flexDirection:"column",gap:"9px",alignItems:"center",
          boxShadow:"inset 0 1px 0 rgba(255,240,120,0.06),0 4px 24px rgba(0,0,0,0.6)",
        }}>
          <div style={{fontSize:"7.5px",letterSpacing:"4px",color:"#45330c",textTransform:"uppercase"}}>Controls</div>

          {/* Blow button */}
          <button
            onMouseDown={startBlow} onMouseUp={stopBlow} onMouseLeave={stopBlow}
            onTouchStart={e=>{e.preventDefault();startBlow();}} onTouchEnd={stopBlow}
            style={{
              background:blowing
                ?"radial-gradient(ellipse,rgba(210,172,55,0.28),rgba(140,105,18,0.12))"
                :"rgba(255,255,255,0.025)",
              border:`1.5px solid ${blowing?"rgba(210,172,55,0.6)":"rgba(195,160,55,0.18)"}`,
              borderRadius:"10px",padding:"10px 22px",cursor:"pointer",
              color:blowing?"#e8c850":"rgba(195,160,55,0.55)",
              fontSize:"10px",letterSpacing:"3px",textTransform:"uppercase",
              boxShadow:blowing?"0 0 20px rgba(210,172,55,0.22)":"none",
              transition:"all 0.10s",userSelect:"none",
              display:"flex",alignItems:"center",gap:"8px",
            }}>
            <span style={{fontSize:"18px",lineHeight:1}}>{blowing?"◉":"◎"}</span>
            <span>SPACE to Blow</span>
          </button>

          {/* Valve buttons */}
          <div style={{display:"flex",gap:"6px"}}>
            {valves.map((v,i)=>(
              <button key={i}
                onMouseDown={()=>pressValve(i)} onMouseUp={()=>releaseValve(i)} onMouseLeave={()=>releaseValve(i)}
                onTouchStart={e=>{e.preventDefault();pressValve(i);}} onTouchEnd={()=>releaseValve(i)}
                style={{
                  display:"flex",flexDirection:"column",alignItems:"center",gap:"3px",
                  background:v?"rgba(65,125,238,0.20)":"rgba(255,255,255,0.02)",
                  border:`1.2px solid ${v?"rgba(95,158,255,0.52)":"rgba(195,160,55,0.16)"}`,
                  borderRadius:"10px",padding:"8px 13px",cursor:"pointer",
                  transition:"all 0.11s",color:v?"#8ec8ff":"rgba(195,160,55,0.48)",
                  boxShadow:v?"0 0 14px rgba(70,135,255,0.16)":"none",
                }}>
                <span style={{fontSize:"14px",fontFamily:"Palatino,serif",lineHeight:1}}>{["F","Bb","T"][i]}</span>
                <span style={{
                  fontSize:"8px",fontFamily:"monospace",
                  background:v?"rgba(70,130,255,0.22)":"rgba(195,160,55,0.07)",
                  border:`1px solid ${v?"rgba(90,155,255,0.38)":"rgba(195,160,55,0.14)"}`,
                  borderRadius:"3px",padding:"1px 4.5px",letterSpacing:0,
                  color:v?"#aadaff":"rgba(195,160,55,0.42)",transition:"all 0.11s",
                }}>{i+1}</span>
              </button>
            ))}
          </div>

          <div style={{fontSize:"8px",letterSpacing:"1.8px",color:"rgba(108,82,22,0.65)",textTransform:"uppercase",textAlign:"center",lineHeight:1.7}}>
            {activeCount===0?"All valves open":`Valves ${valves.map((v,i)=>v?i+1:null).filter(Boolean).join("+")} · −${semitones}st`}
            <br/>
            {PARTIAL_NAMES[partialIdx]} harmonic
          </div>
        </div>
      </div>

      {/* Breath bar */}
      <div style={{marginTop:"8px",width:"min(380px,90vw)",height:"2px",
        background:"rgba(255,255,255,0.04)",borderRadius:"1px",overflow:"hidden"}}>
        <div style={{
          height:"100%",borderRadius:"1px",
          background:"linear-gradient(90deg,#b8900c,#e8c840,#fffac0)",
          width:blowing?"100%":"0%",
          transition:blowing?"width 0.10s ease-out":"width 0.45s ease-in",
          boxShadow:blowing?"0 0 10px rgba(210,175,50,0.7)":"none",
        }}/>
      </div>

      {!started&&(
        <p style={{marginTop:"10px",fontSize:"9px",letterSpacing:"3.5px",
          color:"rgba(110,85,22,0.45)",textTransform:"uppercase",textAlign:"center"}}>
          Hold <b>Space</b> to blow · <b>1 2 3</b> for valves · <b>↑↓</b> to change harmonic
        </p>
      )}

      <style>{`@keyframes breathBar{from{height:4px}to{height:14px}}`}</style>
    </div>
  );
}
