// src/Pages/ISLConvert.jsx
import React, { useEffect, useRef, useState, useCallback } from 'react';
import axios from 'axios';
import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader';
import { defaultPose } from '../defaultpose';
import ybotModel from '../Model/model.glb';

const API_BASE  = 'http://127.0.0.1:5000';
const ANIM_STEP = 0.1;
const ANIM_FPS  = 60;

const delay = ms => new Promise(r => setTimeout(r, ms));

function runKeyframes(boneMap, keyframes) {
  return new Promise(resolve => {
    const active = keyframes.map(([bone,, axis, target, dir]) => ({
      bone, axis, target, dir, done: false
    }));
    const iv = setInterval(() => {
      let allDone = true;
      active.forEach(kf => {
        if (kf.done) return;
        const bone = boneMap[kf.bone];
        if (!bone) { kf.done = true; return; }
        const diff = Math.abs(kf.target - bone.rotation[kf.axis]);
        if (diff < ANIM_STEP * 0.5) {
          bone.rotation[kf.axis] = kf.target;
          kf.done = true;
        } else {
          bone.rotation[kf.axis] += kf.dir === '+' ? ANIM_STEP : -ANIM_STEP;
          if (kf.dir === '+' && bone.rotation[kf.axis] > kf.target) bone.rotation[kf.axis] = kf.target;
          if (kf.dir === '-' && bone.rotation[kf.axis] < kf.target) bone.rotation[kf.axis] = kf.target;
          allDone = false;
        }
      });
      if (allDone) { clearInterval(iv); resolve(); }
    }, 1000 / ANIM_FPS);
  });
}

async function doDefaultPose(boneMap) {
  const ref = { characters: [], animations: [], pending: false, animate: () => {} };
  defaultPose(ref);
  if (ref.animations[0]) await runKeyframes(boneMap, ref.animations[0]);
}

const FOLDER_MAP = { words: 'Words', alphabets: 'Alphabets' };

async function playSignFile(boneMap, token, folder) {
  if (folder === 'none') return;
  const srcFolder = FOLDER_MAP[folder] || folder;
  const ref = { animations: [], pending: false, animate: () => {} };
  try {
    const mod    = await import(`../${srcFolder}/${token}`);
    const signFn = mod[token] || mod.default;
    if (typeof signFn !== 'function') throw new Error('not a function');
    signFn(ref);
  } catch (e) {
    console.warn(`[Sign] "${token}" in ${srcFolder}:`, e.message);
    return;
  }
  const frames = ref.animations;
  if (!frames.length) return;
  if (frames.length === 1) {
    await runKeyframes(boneMap, frames[0]);
    await delay(300);
    await doDefaultPose(boneMap);
  } else {
    for (let f = 0; f < frames.length; f++) {
      await runKeyframes(boneMap, frames[f]);
      if (f < frames.length - 1) await delay(150);
    }
  }
  await delay(150);
}

export default function ISLConvert() {
  const canvasRef     = useRef(null);
  const boneMapRef    = useRef({});
  const animatingRef  = useRef(false);
  const pausedRef     = useRef(false);
  const signsRef      = useRef([]);
  const currentIdxRef = useRef(-1);
  const lastGlossRef  = useRef('');
  const lastInputRef  = useRef('');

  const [inputText, setInputText] = useState('');
  const [gloss,     setGloss]     = useState('');
  const [intent,    setIntent]    = useState('');
  const [tags,      setTags]      = useState([]);
  const [signs,     setSigns]     = useState([]);
  const [currentIdx,setCurrentIdx]= useState(-1);
  const [paused,    setPaused]    = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [feedback,  setFeedback]  = useState(null);
  const [sessionId, setSessionId] = useState(null);

  // ── Three.js ────────────────────────────────────────────────────────────────
  useEffect(() => {
    const el = canvasRef.current;
    if (!el) return;
    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setPixelRatio(window.devicePixelRatio);
    el.innerHTML = '';
    el.appendChild(renderer.domElement);
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x1a1a2e);
    scene.add(new THREE.SpotLight(0xffffff, 2).position.set(0, 5, 5) && new THREE.SpotLight(0xffffff, 2));
    scene.add(new THREE.AmbientLight(0xffffff, 0.8));
    const fill = new THREE.DirectionalLight(0xffffff, 0.5);
    fill.position.set(-2, 2, 2);
    scene.add(fill);
    const camera = new THREE.PerspectiveCamera(30, 1, 0.1, 1000);
    camera.position.set(0, 1.4, 2.1);
    const resize = () => {
      const w = el.clientWidth || 1, h = el.clientHeight || 1;
      renderer.setSize(w, h);
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
    };
    window.addEventListener('resize', resize);
    setTimeout(resize, 50);
    let frameId;
    const loop = () => { frameId = requestAnimationFrame(loop); renderer.render(scene, camera); };
    loop();
    new GLTFLoader().load(ybotModel, async gltf => {
      const model = gltf.scene;
      model.traverse(c => { if (c.type === 'SkinnedMesh') c.frustumCulled = false; });
      scene.add(model);
      const bm = {};
      model.traverse(n => {
        if (n.isBone || n.type === 'Bone') bm[n.name] = n;
        if (n.isSkinnedMesh) n.skeleton.bones.forEach(b => { bm[b.name] = b; });
      });
      boneMapRef.current = bm;
      await delay(200);
      await doDefaultPose(bm);
    }, undefined, err => console.error('[GLB]', err));
    return () => { window.removeEventListener('resize', resize); cancelAnimationFrame(frameId); renderer.dispose(); };
  }, []);

  // ── Playback ─────────────────────────────────────────────────────────────────
  const stopPlayback = useCallback(() => {
    animatingRef.current  = false;
    pausedRef.current     = false;
    currentIdxRef.current = -1;
    setPaused(false);
    setIsPlaying(false);
    setCurrentIdx(-1);
    doDefaultPose(boneMapRef.current);
  }, []);

  const playAll = useCallback(async (sequence, startIdx = 0) => {
    // Cancel any existing playback before starting
    animatingRef.current = false;
    await delay(50);
    animatingRef.current = true;
    pausedRef.current    = false;
    setIsPlaying(true);
    setPaused(false);
    await doDefaultPose(boneMapRef.current);

    for (let i = startIdx; i < sequence.length; i++) {
      while (pausedRef.current) await delay(100);
      if (!animatingRef.current) return;

      currentIdxRef.current = i;
      setCurrentIdx(i);

      // Play sign fully FIRST, then wait gap — no racing
      await playSignFile(boneMapRef.current, sequence[i].token, sequence[i].folder);

      // Check again after sign finishes — user may have pressed stop
      if (!animatingRef.current) return;
      while (pausedRef.current) await delay(100);

      // Small gap between signs
      await delay(200);
    }

    if (!animatingRef.current) return;
    await doDefaultPose(boneMapRef.current);
    currentIdxRef.current = sequence.length;
    setCurrentIdx(sequence.length);
    setIsPlaying(false);
    animatingRef.current = false;
    setPaused(false);
  }, []);

  // ── Handlers ─────────────────────────────────────────────────────────────────
  const handleConvert = useCallback(async () => {
    if (!inputText.trim()) return;
    stopPlayback();
    setSigns([]); setGloss(''); setIntent(''); setTags([]);
    try {
      const { data } = await axios.post(`${API_BASE}/translate`, {
        text: inputText.trim(), mode: 'word'
      });
      if (!data.success) throw new Error(data.error);
      const seq = data.sequence || [];
      signsRef.current     = seq;
      setSigns(seq);
      setGloss((data.gloss_words || []).join(' – '));
      setIntent(data.intent || '');
      setTags(data.tags || []);
      setFeedback(null);
      setSessionId(data.session_id || null);
      lastGlossRef.current = (data.gloss_words || []).join(' ');
      lastInputRef.current = inputText.trim();
      playAll(seq, 0);
    } catch (err) {
      setIsPlaying(false);
      console.error('Translate error:', err.message);
    }
  }, [inputText, stopPlayback, playAll]);

  const handlePauseResume = useCallback(() => {
    if (!isPlaying) return;
    if (pausedRef.current) {
      pausedRef.current = false;
      setPaused(false);
    } else {
      pausedRef.current = true;
      setPaused(true);
    }
  }, [isPlaying]);

  const handleBackward = useCallback(() => {
    const seq = signsRef.current;
    if (!seq.length) return;
    const cur     = currentIdxRef.current;
    const prevIdx = cur >= seq.length ? seq.length - 1 : Math.max(0, cur - 1);
    animatingRef.current = false;
    pausedRef.current    = false;
    // Longer delay to ensure previous loop fully exits before starting new one
    setTimeout(() => {
      if (!animatingRef.current) playAll(seq, prevIdx);
    }, 300);
  }, [playAll]);

  const handleForward = useCallback(() => {
    const seq = signsRef.current;
    if (!seq.length) return;
    const cur     = currentIdxRef.current;
    const nextIdx = cur >= seq.length ? 0 : Math.min(seq.length - 1, cur + 1);
    animatingRef.current = false;
    pausedRef.current    = false;
    setTimeout(() => {
      if (!animatingRef.current) playAll(seq, nextIdx);
    }, 300);
  }, [playAll]);

  const handleReplay = useCallback(() => {
    const seq = signsRef.current;
    if (!seq.length) return;
    animatingRef.current = false;
    pausedRef.current    = false;
    setTimeout(() => playAll(seq, 0), 200);
  }, [playAll]);

  const handleFeedback = useCallback(async (rating) => {
    if (!lastInputRef.current || !lastGlossRef.current) return;
    setFeedback(rating);
    try {
      await axios.post(`${API_BASE}/feedback`, {
        session_id: sessionId,
        input_text: lastInputRef.current,
        gloss:      lastGlossRef.current,
        rating:     rating === 'up' ? 1 : -1,
      });
    } catch (e) {
      console.warn('Feedback error:', e.message);
    }
  }, [sessionId]);

  const handleClear = useCallback(() => {
    stopPlayback();
    setInputText(''); setGloss(''); setIntent('');
    setTags([]); setSigns([]); setCurrentIdx(-1);
    setFeedback(null);
    signsRef.current      = [];
    currentIdxRef.current = -1;
    lastGlossRef.current  = '';
    lastInputRef.current  = '';
  }, [stopPlayback]);

  const progress = signs.length
    ? Math.round((Math.max(0, currentIdx) / signs.length) * 100)
    : 0;

  // ── Render ───────────────────────────────────────────────────────────────────
  return (
    <div style={S.page}>
      <div style={S.grid}>

        {/* LEFT — Input */}
        <div style={S.panel}>
          <div style={S.panelHead}>
            <span style={S.panelTitle}>Input Text</span>
            <span style={S.badge}>ISL</span>
          </div>
          <textarea
            style={S.textarea}
            value={inputText}
            maxLength={200}
            placeholder={'Type a word or sentence…\n\ne.g. Hello, My name is Riya'}
            onChange={e => setInputText(e.target.value)}
          />
          <div style={S.charCount}>{inputText.length} / 200</div>
          <div style={S.btnRow}>
            <button style={S.btnConvert} onClick={handleConvert}>▶ Convert</button>
            <button style={S.btnClear}   onClick={handleClear}>Clear</button>
          </div>
        </div>

        {/* CENTER — Avatar */}
        <div style={S.avatarPanel}>
          <div style={S.panelHead}>
            <span style={S.panelTitle}>Animation Box</span>
            <div style={{ display: 'flex', gap: 5 }}>
              <button style={S.ctrlBtn(!signs.length)} onClick={handleBackward}    disabled={!signs.length}>◀</button>
              <button style={S.ctrlBtn(!isPlaying)}    onClick={handlePauseResume} disabled={!isPlaying}>{paused ? '▶' : '⏸'}</button>
              <button style={S.ctrlBtn(!signs.length)} onClick={handleForward}     disabled={!signs.length}>▶</button>
              <button style={S.ctrlBtn(!signs.length)} onClick={handleReplay}      disabled={!signs.length}>↺</button>
            </div>
          </div>

          {/* Current sign label */}
          <div style={S.currentWord}>
            {currentIdx >= 0 && currentIdx < signs.length ? signs[currentIdx]?.token : ''}
          </div>

          {/* Token queue — clickable, strikethrough on done */}
          {signs.length > 0 && (
            <div style={S.queueArea}>
              <div style={S.progressTrack}>
                <div style={{ ...S.progressFill, width: `${progress}%` }} />
              </div>
              <div style={S.queue}>
                {signs.map((s, i) => {
                  const st = i < currentIdx ? 'done' : i === currentIdx ? 'cur' : 'idle';
                  return (
                    <span
                      key={i}
                      title={`Click to replay: ${s.token}`}
                      onClick={() => {
                        animatingRef.current = false;
                        pausedRef.current    = false;
                        setTimeout(() => playAll(signs, i), 200);
                      }}
                      style={{
                        ...S.qToken(st),
                        cursor: 'pointer',
                        textDecoration: st === 'done' ? 'line-through' : 'none',
                        opacity: st === 'done' ? 0.6 : 1,
                        userSelect: 'none',
                      }}
                    >
                      {s.token}
                    </span>
                  );
                })}
              </div>
            </div>
          )}

          {/* 3D canvas */}
          <div ref={canvasRef} style={S.canvas} />
        </div>

        {/* RIGHT — Info */}
        <div style={S.rightCol}>
          <div style={S.infoCard}>
            <div style={S.panelHead}>
              <span style={S.panelTitle}>ISL Gloss Notation</span>
              {gloss && (
                <button style={S.copyBtn} onClick={() => navigator.clipboard.writeText(gloss)}>⧉</button>
              )}
            </div>
            <div style={S.infoBody}>
              {gloss ? gloss : <span style={S.ph}>ISL gloss notation will appear here…</span>}
            </div>
          </div>

          <div style={S.infoCard}>
            <div style={S.panelHead}>
              <span style={S.panelTitle}>Intent of the Text</span>
            </div>
            <div style={S.infoBody}>
              {intent ? intent : <span style={S.ph}>Meaning & context will appear here…</span>}
            </div>
            <div style={S.tagRow}>
              {tags.map(t => <span key={t} style={S.tag}>{t}</span>)}
            </div>

            {/* Feedback */}
            {gloss && (
              <div style={{ display: 'flex', gap: 8, padding: '0 16px 14px', alignItems: 'center' }}>
                <span style={{ fontSize: '.72rem', color: '#64748B' }}>Was this correct?</span>
                <button
                  onClick={() => handleFeedback('up')}
                  style={{
                    background: feedback === 'up' ? 'rgba(74,222,128,0.2)' : 'rgba(148,163,184,0.1)',
                    border: `1px solid ${feedback === 'up' ? 'rgba(74,222,128,0.5)' : 'rgba(148,163,184,0.2)'}`,
                    borderRadius: 8, padding: '4px 10px', cursor: 'pointer',
                    fontSize: '1rem', color: feedback === 'up' ? '#4ADE80' : '#94A3B8',
                  }}
                >👍</button>
                <button
                  onClick={() => handleFeedback('down')}
                  style={{
                    background: feedback === 'down' ? 'rgba(248,113,113,0.2)' : 'rgba(148,163,184,0.1)',
                    border: `1px solid ${feedback === 'down' ? 'rgba(248,113,113,0.5)' : 'rgba(148,163,184,0.2)'}`,
                    borderRadius: 8, padding: '4px 10px', cursor: 'pointer',
                    fontSize: '1rem', color: feedback === 'down' ? '#F87171' : '#94A3B8',
                  }}
                >👎</button>
                {feedback && (
                  <span style={{ fontSize: '.72rem', color: feedback === 'up' ? '#4ADE80' : '#F87171' }}>
                    {feedback === 'up' ? 'Great!' : 'Got it — will improve!'}
                  </span>
                )}
              </div>
            )}
          </div>
        </div>

      </div>
    </div>
  );
}

// ── Styles ────────────────────────────────────────────────────────────────────
const S = {
  page: {
    height: '100vh',
    background: 'radial-gradient(circle at 20% 20%, #1E293B, #020617)',
    color: '#E2E8F0',
    fontFamily: "'Inter', sans-serif",
    display: 'flex',
    flexDirection: 'column',
    padding: 14,
    gap: 12,
    boxSizing: 'border-box',
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: '1fr 1.5fr 1fr',
    gap: 14,
    flex: 1,
    minHeight: 0,
  },
  panel: {
    background: 'rgba(15,23,42,0.6)',
    backdropFilter: 'blur(12px)',
    border: '1px solid rgba(148,163,184,0.15)',
    borderRadius: 16,
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
    boxShadow: '0 10px 40px rgba(0,0,0,0.4)',
  },
  avatarPanel: {
    background: 'rgba(15,23,42,0.6)',
    backdropFilter: 'blur(12px)',
    border: '1px solid rgba(148,163,184,0.15)',
    borderRadius: 16,
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
    boxShadow: '0 12px 50px rgba(0,0,0,0.5)',
  },
  panelHead: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '12px 18px',
    background: 'rgba(2,6,23,0.6)',
    borderBottom: '1px solid rgba(148,163,184,0.1)',
  },
  panelTitle: {
    fontSize: '.75rem',
    fontWeight: 600,
    letterSpacing: '.1em',
    textTransform: 'uppercase',
    color: '#94A3B8',
  },
  badge: {
    background: 'linear-gradient(135deg,#6366F1,#06B6D4)',
    color: '#fff',
    fontSize: '.65rem',
    fontWeight: 600,
    padding: '4px 10px',
    borderRadius: 999,
  },
  textarea: {
    flex: 1,
    background: 'transparent',
    border: 'none',
    outline: 'none',
    resize: 'none',
    padding: 18,
    fontSize: '.92rem',
    color: '#E2E8F0',
    lineHeight: 1.7,
  },
  charCount: {
    padding: '4px 18px',
    fontSize: '.7rem',
    color: '#64748B',
    borderTop: '1px solid rgba(148,163,184,0.1)',
  },
  btnRow: {
    display: 'flex',
    gap: 10,
    padding: '12px 18px',
  },
  btnConvert: {
    flex: 1,
    padding: 11,
    background: 'linear-gradient(135deg,#6366F1,#06B6D4)',
    color: '#fff',
    border: 'none',
    borderRadius: 10,
    fontWeight: 600,
    cursor: 'pointer',
    boxShadow: '0 0 20px rgba(99,102,241,0.4)',
  },
  btnClear: {
    padding: '11px 14px',
    background: 'rgba(148,163,184,0.1)',
    color: '#CBD5F5',
    border: '1px solid rgba(148,163,184,0.2)',
    borderRadius: 10,
    cursor: 'pointer',
  },
  ctrlBtn: d => ({
    background: d ? 'rgba(148,163,184,0.1)' : 'rgba(99,102,241,0.15)',
    border: '1px solid rgba(99,102,241,0.3)',
    borderRadius: 8,
    color: d ? '#64748B' : '#A5B4FC',
    width: 32,
    height: 32,
    cursor: d ? 'not-allowed' : 'pointer',
    boxShadow: d ? 'none' : '0 0 10px rgba(99,102,241,0.4)',
  }),
  currentWord: {
    fontSize: '1.5rem',
    fontWeight: 600,
    color: '#A5B4FC',
    textAlign: 'center',
    padding: '8px 0',
    textShadow: '0 0 12px rgba(99,102,241,0.6)',
    minHeight: '2.5rem',
  },
  canvas: {
    flex: 1,
    background: 'radial-gradient(circle, #0F172A, #020617)',
    borderRadius: 12,
    margin: '0 10px',
    minHeight: 0,
  },
  queueArea: {
    padding: '10px 14px',
  },
  progressTrack: {
    height: 6,
    background: 'rgba(148,163,184,0.2)',
    borderRadius: 999,
    marginBottom: 10,
  },
  progressFill: {
    height: '100%',
    background: 'linear-gradient(90deg,#6366F1,#06B6D4)',
    borderRadius: 999,
    boxShadow: '0 0 12px rgba(99,102,241,0.6)',
    transition: 'width .3s ease',
  },
  queue: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: 6,
    justifyContent: 'center',
  },
  qToken: s => ({
    fontSize: '.72rem',
    padding: '5px 12px',
    borderRadius: 999,
    background: s === 'cur' ? 'rgba(99,102,241,0.2)' : 'rgba(148,163,184,0.1)',
    border: '1px solid rgba(148,163,184,0.2)',
    color: s === 'cur' ? '#C7D2FE' : '#94A3B8',
    fontWeight: s === 'cur' ? 600 : 400,
  }),
  rightCol: {
    display: 'flex',
    flexDirection: 'column',
    gap: 14,
  },
  infoCard: {
    flex: 1,
    background: 'rgba(15,23,42,0.6)',
    backdropFilter: 'blur(12px)',
    border: '1px solid rgba(148,163,184,0.15)',
    borderRadius: 16,
    display: 'flex',
    flexDirection: 'column',
    boxShadow: '0 10px 40px rgba(0,0,0,0.4)',
  },
  infoBody: {
    flex: 1,
    padding: 18,
    fontSize: '.86rem',
    color: '#CBD5F5',
    overflowY: 'auto',
    lineHeight: 1.7,
  },
  ph: {
    color: '#64748B',
    fontStyle: 'italic',
  },
  tagRow: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: 6,
    padding: '0 16px 14px',
  },
  tag: {
    background: 'rgba(99,102,241,0.15)',
    border: '1px solid rgba(99,102,241,0.3)',
    borderRadius: 999,
    padding: '5px 12px',
    fontSize: '.72rem',
    color: '#C7D2FE',
  },
  copyBtn: {
    background: 'rgba(148,163,184,0.1)',
    border: '1px solid rgba(148,163,184,0.2)',
    borderRadius: 6,
    color: '#CBD5F5',
    cursor: 'pointer',
    padding: '3px 8px',
  },
};