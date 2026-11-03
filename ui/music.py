"""Músicas de fundo geradas por código (Web Audio API, sem arquivos de áudio).

Duas trilhas 100% originais (melodia, harmonia, baixo e percussão próprios):

- **Tela inicial** ("home"): chiptune alegre com sabor de baião/forró na floresta.
  Sol mixolídio (A) e Dó lídio-mixolídio (B), 120 BPM, A A' B B' (32 compassos).
  Lead em onda quadrada/pulso, pífano com vibrato, baixo em triângulo, zabumba,
  triângulo, ganzá e agogô sintetizados; grilos e pássaros bem baixinhos.
- **Sala e partida** ("game"): aventura misteriosa e um pouco melancólica, clima de
  RPG 16-bit. Ré dórico com empréstimos modais, acordes de sétima/nona, pad de cordas,
  arpejo com eco, flauta de bambu e oboé, baixo caminhando, percussão leve e mata
  noturna. 88 BPM, A B A' C (32 compassos). Volume ~38% da trilha inicial e com
  "ducking": abaixa quando um efeito sonoro toca (bem mais na vitória/derrota).

O motor fica em ``window.parent.__unoMusic`` (instalado uma única vez, com guarda):
os reruns do Streamlit só chamam ``set(trilha, mudo)``; trocar de trilha faz crossfade
e nada reinicia nem duplica. O navegador só libera áudio depois de um gesto: a música
começa no primeiro clique/toque/tecla. O botão "Música" (canto inferior esquerdo)
liga/desliga e guarda a preferência no ``localStorage``; o mudo do app também vale.
"""

from __future__ import annotations

import json

VOLUME = 0.25  # volume do master da tela inicial (moderado)
GAME_VOLUME = round(VOLUME * 0.38, 4)  # trilha do jogo: bem mais baixa (~38% da inicial)
STORAGE_KEY = "uno_music"

MUSIC_ENGINE = r"""
(function(){
  const W = window;
  if (W.__unoMusic) return;  // guarda: um motor só por página, mesmo com vários reruns
  const M = W.__unoMusic = { ctx: null, mode: '', muted: false, duckSeq: -1, tensionLevel: W.__unoMusicTension | 0 };
  const VOL_HOME = __VOLUME__, VOL_GAME = __GAME_VOLUME__, KEY = '__KEY__', LOOK = 0.15;

  // ================================================================== TRILHA DA TELA INICIAL
  const HOME = (function(){
  const BPM = 120, SPB = 16, STEP = 60 / BPM / 4;

  // ------------------------------------------------------------------ partitura (original)
  const PC = {C:0, D:2, E:4, F:5, G:7, A:9, B:11};
  function midi(s){
    const m = /^([A-G])(#|b)?(\d)$/.exec(s);
    return PC[m[1]] + (m[2] === '#' ? 1 : m[2] === 'b' ? -1 : 0) + 12 * (+m[3] + 1);
  }
  function bar(str){ return str.trim().split(/\s+/).map(t => { const p = t.split(':'); return [midi(p[0]), +p[1], +p[2]]; }); }
  const A1 = [
    'G4:0:2 B4:2:2 D5:4:3 C5:7:1 B4:8:2 A4:10:2 B4:12:4',
    'D5:0:2 E5:2:2 F5:4:3 E5:7:1 D5:8:4 B4:12:2 G4:14:2',
    'F5:0:3 E5:3:1 C5:4:2 A4:6:2 C5:8:2 F5:10:2 E5:12:2 C5:14:2',
    'D5:0:3 B4:3:1 G4:4:4 A4:10:2 B4:12:2 D5:14:2',
    'G5:0:3 F5:3:1 D5:4:2 B4:6:2 D5:8:2 G5:10:2 F5:12:4',
    'E5:0:2 G5:2:2 E5:4:2 C5:6:2 E5:8:3 D5:11:1 C5:12:4',
    'A4:0:2 C5:2:2 F5:4:2 A5:6:2 G5:8:2 F5:10:2 D5:12:2 C5:14:2',
    'B4:0:3 A4:3:1 G4:4:8 A4:12:2 B4:14:2'];
  const A2 = A1.slice();
  A2[3] = 'D5:0:2 E5:2:2 F5:4:2 E5:6:2 D5:8:2 B4:10:2 A4:12:2 B4:14:2';
  A2[7] = 'B4:0:2 D5:2:2 G5:4:4 F5:8:2 E5:10:2 D5:12:2 C5:14:2';
  const B1 = [
    'E5:0:2 F#5:2:2 G5:4:4 E5:8:2 C5:10:2 D5:12:4',
    'E5:0:1 F#5:1:1 G5:2:2 A5:4:2 G5:6:2 F#5:8:2 E5:10:2 D5:12:2 E5:14:2',
    'D5:0:3 F5:3:1 Bb5:4:4 A5:8:2 G5:10:2 F5:12:4',
    'A5:0:2 G5:2:2 F5:4:2 C5:6:2 A4:8:4 C5:12:2 E5:14:2',
    'G5:0:3 E5:3:1 C5:4:2 E5:6:2 G5:8:2 A5:10:2 Bb5:12:4',
    'A5:0:2 F#5:2:2 D5:4:2 F#5:6:2 A5:8:3 G5:11:1 F#5:12:4',
    'G5:0:2 D5:2:2 B4:4:2 D5:6:2 F5:8:2 E5:10:2 D5:12:2 B4:14:2',
    'A4:0:2 B4:2:2 C5:4:2 D5:6:2 F#5:8:2 E5:10:2 D5:12:2 C5:14:2'];
  const B2 = B1.slice();
  B2[7] = 'D5:0:3 C5:3:1 B4:4:2 A4:6:2 F#4:8:2 A4:10:2 C5:12:2 D5:14:2';
  const CH_A = ['G','G','F','G','G','C','F','G'], CH_B = ['C','C','Bb','F','C','D','G','D'];
  const CHORDS = {  // raiz do baixo + terça/quinta/oitava (chiptune) no registro 5
    G:  {r: midi('G2'),  t: [midi('B4'), midi('D5'), midi('G5')]},
    F:  {r: midi('F2'),  t: [midi('A4'), midi('C5'), midi('F5')]},
    C:  {r: midi('C3'),  t: [midi('E5'), midi('G5'), midi('C6')]},
    D:  {r: midi('D3'),  t: [midi('F#5'), midi('A5'), midi('D6')]},
    Bb: {r: midi('Bb2'), t: [midi('D5'), midi('F5'), midi('Bb5')]}};
  const SONG = [];
  [[A1, CH_A, 'A'], [A2, CH_A, 'A2'], [B1, CH_B, 'B'], [B2, CH_B, 'B2']].forEach(([mel, ch, sec]) => {
    mel.forEach((s, i) => SONG.push({lead: bar(s), ch: CHORDS[ch[i]], sec: sec, last: false}));
  });
  SONG[SONG.length - 1].last = true;

  // ------------------------------------------------------------------ instrumentos
  function build(c, out){
    const mtof = n => 440 * Math.pow(2, (n - 69) / 12);
    const noise = c.createBuffer(1, c.sampleRate, c.sampleRate);
    const nd = noise.getChannelData(0);
    for (let i = 0; i < nd.length; i++) nd[i] = Math.random() * 2 - 1;
    const N = 24, re = new Float32Array(N), im = new Float32Array(N);
    for (let k = 1; k < N; k++) re[k] = (2 / (k * Math.PI)) * Math.sin(k * Math.PI * 0.25);
    const pulse = c.createPeriodicWave(re, im);  // pulso 25%
    const comp = c.createDynamicsCompressor(); comp.threshold.value = -14; comp.ratio.value = 4;
    comp.connect(out);
    const leadBus = c.createBiquadFilter(); leadBus.type = 'lowpass'; leadBus.frequency.value = 3200; leadBus.connect(comp);
    const pan = (p) => { if (!c.createStereoPanner) return comp; const s = c.createStereoPanner(); s.pan.value = p; s.connect(comp); return s; };

    function tone(o, t, dur, peak, dest, a, rel){
      const g = c.createGain();
      g.gain.setValueAtTime(0.0001, t);
      g.gain.linearRampToValueAtTime(peak, t + a);
      g.gain.setTargetAtTime(peak * 0.65, t + a, Math.max(0.03, dur * 0.4));
      g.gain.setTargetAtTime(0.0001, t + dur, rel / 3);
      o.connect(g); g.connect(dest);
      o.start(t); o.stop(t + dur + rel * 2 + 0.05);
    }
    function osc(type, f, t){
      const o = c.createOscillator();
      if (type === 'pulse') o.setPeriodicWave(pulse); else o.type = type;
      o.frequency.setValueAtTime(f, t);
      return o;
    }
    function lead(type, n, t, dur, peak){ tone(osc(type, mtof(n), t), t, dur, peak, leadBus, 0.006, 0.05); }
    function fife(n, t, dur, peak, dest){
      const f = mtof(n), o = osc('triangle', f, t), o2 = osc('sine', f * 2, t);
      const l = c.createOscillator(), lg = c.createGain();
      l.frequency.value = 5.6;
      lg.gain.setValueAtTime(0, t); lg.gain.linearRampToValueAtTime(f * 0.007, t + Math.min(0.25, dur));
      l.connect(lg); lg.connect(o.frequency); lg.connect(o2.frequency);
      l.start(t); l.stop(t + dur + 0.3);
      tone(o, t, dur, peak, dest, 0.03, 0.08);
      tone(o2, t, dur, peak * 0.18, dest, 0.03, 0.08);
    }
    const fifeOut = pan(0.25);
    function bass(n, t, dur, peak){ tone(osc('triangle', mtof(n), t), t, dur, peak, comp, 0.004, 0.04); }
    function nz(t, dur, peak, type, freq, q, dest){
      const s = c.createBufferSource(); s.buffer = noise;
      const f = c.createBiquadFilter(); f.type = type; f.frequency.value = freq; f.Q.value = q || 1;
      const g = c.createGain();
      g.gain.setValueAtTime(peak, t); g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
      s.connect(f); f.connect(g); g.connect(dest || comp);
      s.start(t, Math.random() * 0.5); s.stop(t + dur + 0.02);
    }
    function kick(t, v){  // zabumba: grave
      const o = c.createOscillator(), g = c.createGain();
      o.type = 'sine'; o.frequency.setValueAtTime(115, t); o.frequency.exponentialRampToValueAtTime(46, t + 0.13);
      g.gain.setValueAtTime(0.0001, t); g.gain.linearRampToValueAtTime(0.85 * v, t + 0.004);
      g.gain.exponentialRampToValueAtTime(0.0001, t + 0.34);
      o.connect(g); g.connect(comp); o.start(t); o.stop(t + 0.4);
      nz(t, 0.02, 0.12 * v, 'lowpass', 900);
    }
    function snap(t, v){ nz(t, 0.05, 0.22 * v, 'bandpass', 2300, 1.4); }  // zabumba: estalo do bacalhau
    const triOut = pan(-0.3), shakeOut = pan(0.35), agoOut = pan(-0.15);
    function tri(t, open, v){  // triângulo de metal: parciais inarmônicas
      [4350, 6810].forEach((f, i) => {
        const o = c.createOscillator(), g = c.createGain();
        o.type = 'sine'; o.frequency.value = f;
        const d = open ? 0.26 : 0.045;
        g.gain.setValueAtTime(0.0001, t); g.gain.linearRampToValueAtTime((i ? 0.025 : 0.04) * v, t + 0.002);
        g.gain.exponentialRampToValueAtTime(0.0001, t + d);
        o.connect(g); g.connect(triOut); o.start(t); o.stop(t + d + 0.02);
      });
    }
    function ganza(t, v){ nz(t, 0.055, 0.07 * v, 'bandpass', 6200, 0.9, shakeOut); }
    function agogo(t, high){
      const f = high ? 1046 : 784;
      [1, 2.68].forEach((m, i) => {
        const o = c.createOscillator(), g = c.createGain();
        o.type = 'sine'; o.frequency.value = f * m;
        g.gain.setValueAtTime(0.0001, t); g.gain.linearRampToValueAtTime(i ? 0.015 : 0.05, t + 0.003);
        g.gain.exponentialRampToValueAtTime(0.0001, t + 0.22);
        o.connect(g); g.connect(agoOut); o.start(t); o.stop(t + 0.25);
      });
    }
    // floresta: grilos e pássaros, bem baixinho e em lugares aleatórios do estéreo
    function cricket(t){
      const out2 = pan(Math.random() * 1.6 - 0.8), f = 4300 + Math.random() * 900;
      const n = 3 + Math.floor(Math.random() * 3);
      for (let k = 0; k < n; k++) {
        const o = c.createOscillator(), g = c.createGain(), s = t + k * 0.085;
        o.type = 'sine'; o.frequency.value = f;
        g.gain.setValueAtTime(0.0001, s); g.gain.linearRampToValueAtTime(0.012, s + 0.01);
        g.gain.exponentialRampToValueAtTime(0.0001, s + 0.05);
        o.connect(g); g.connect(out2); o.start(s); o.stop(s + 0.06);
      }
    }
    function bird(t){
      const out2 = pan(Math.random() * 1.6 - 0.8), base = 2200 + Math.random() * 900;
      const n = 2 + Math.floor(Math.random() * 2);
      for (let k = 0; k < n; k++) {
        const o = c.createOscillator(), g = c.createGain(), s = t + k * 0.2;
        o.type = 'sine';
        o.frequency.setValueAtTime(base, s); o.frequency.exponentialRampToValueAtTime(base * 1.45, s + 0.07);
        o.frequency.exponentialRampToValueAtTime(base * 0.9, s + 0.14);
        g.gain.setValueAtTime(0.0001, s); g.gain.linearRampToValueAtTime(0.016, s + 0.02);
        g.gain.exponentialRampToValueAtTime(0.0001, s + 0.15);
        o.connect(g); g.connect(out2); o.start(s); o.stop(s + 0.17);
      }
    }

    // ------------------------------------------------------------------ um passo (semicolcheia)
    function step(i, t0){
      const b = Math.floor(i / SPB) % SONG.length, s = i % SPB, B = SONG[b], sec = B.sec;
      const t = t0 + (s % 2 ? STEP * 0.12 : 0);  // leve balanço de forró
      const r = B.ch.r, tones = B.ch.t;
      const next = SONG[(b + 1) % SONG.length].ch.r;
      // melodia
      B.lead.forEach(([n, st, len]) => {
        if (st !== s) return;
        const dur = len * STEP * 0.9;
        if (sec === 'B2') fife(n, t, dur, 0.2, fifeOut);
        else lead(sec === 'A2' ? 'pulse' : 'square', n, t, dur, sec === 'A2' ? 0.15 : 0.12);
      });
      // contra-melodia do pífano (A', B) e arpejo chiptune (B')
      if ((sec === 'A2' || sec === 'B') && (s === 0 || s === 8 || s === 12)) {
        const n = s === 0 ? tones[0] : s === 8 ? tones[1] : tones[0];
        fife(n - 12 * (n > 81 ? 1 : 0), t, (s === 0 ? 7 : 3.6) * STEP, 0.09, fifeOut);
      }
      if (sec === 'B2' && s % 2 === 0) lead('pulse', tones[(s / 2) % 3] + 12 * (s % 8 === 6 ? 1 : 0) - 12, t, STEP * 1.6, 0.045);
      // baixo de baião
      if (s === 0) bass(r, t, STEP * 2.8, 0.42);
      if (s === 3) bass(r, t, STEP * 0.9, 0.3);
      if (s === 8) bass(r + 7, t, STEP * 3.6, 0.38);
      if (s === 12 && sec !== 'A') bass(r + 12, t, STEP * 1.8, 0.3);
      if (s === 14 && sec[0] === 'B') bass(next - 1 + (next - 1 < r ? 12 : 0), t, STEP * 1.8, 0.3);
      // zabumba, triângulo, ganzá, agogô
      if (B.last) {
        if ([0, 4, 8, 10, 12, 14].includes(s)) kick(t, s ? 0.75 : 1);
        if ([6, 13, 15].includes(s)) snap(t, 0.8);
      } else {
        if (s === 0) kick(t, 1);
        if (s === 3) kick(t, 0.5);
        if (s === 8) kick(t, 0.8);
        if (s === 11 && sec[0] === 'B') kick(t, 0.45);
        if (s === 4 || s === 12) snap(t, 1);
        if (s === 14 && sec !== 'A') snap(t, 0.5);
      }
      if (s % 2 === 0) tri(t, s % 4 === 2, s % 4 === 2 ? 1 : 0.7);
      else if (sec[0] === 'B') tri(t, false, 0.35);
      if (sec !== 'A') ganza(t, s % 4 === 2 ? 1 : 0.55);
      if (sec === 'B2' && [0, 6, 8, 10, 14].includes(s)) agogo(t, s === 0 || s === 8 || s === 10);
      // floresta
      if (s === 0) {
        if (Math.random() < 0.55) cricket(t + Math.random() * STEP * 14);
        if (Math.random() < 0.3) bird(t + Math.random() * STEP * 12);
      }
    }
    return { step: step };
  }
  return { name: 'home', step: STEP, steps: SONG.length * SPB, build: build, vol: VOL_HOME, fadeIn: 2.5 };
  })();

  // ================================================================== TRILHA DO JOGO
  // Aventura misteriosa e um pouco melancólica: ré dórico com empréstimos modais,
  // acordes de sétima/nona, pad de cordas, arpejo suave com eco, flauta de bambu e
  // oboé, baixo caminhando, percussão leve e mata noturna. 88 BPM, A B A' C (32 compassos).
  const GAME = (function(){
    const BPM = 88, SPB = 16, STEP = 60 / BPM / 4, TEMPO = [1, 1.18, 1.25];
    const NOTE = {C:0, D:2, E:4, F:5, G:7, A:9, B:11};
    function midi(s){
      const m = /^([A-G])(#|b)?(\d)$/.exec(s);
      return NOTE[m[1]] + (m[2] === '#' ? 1 : m[2] === 'b' ? -1 : 0) + 12 * (+m[3] + 1);
    }
    function bar(str){ return str.trim() ? str.trim().split(/\s+/).map(t => { const p = t.split(':'); return [midi(p[0]), +p[1], +p[2]]; }) : []; }
    const CH = {  // pad (4 vozes) + raiz do baixo
      Dm9: ['F3 A3 C4 E4', 'D2'], Bbmaj7: ['Bb3 D4 F4 A4', 'Bb2'], C69: ['E3 A3 D4 G4', 'C2'],
      Am7: ['G3 C4 E4 A4', 'A2'], Gm9: ['Bb3 D4 F4 A4', 'G2'], A7sus: ['G3 D4 E4 A4', 'A2'],
      A7: ['G3 C#4 E4 A4', 'A2'], Fmaj9: ['A3 E4 G4 C5', 'F2'], Em7: ['G3 B3 D4 E4', 'E2'],
      Cmaj7: ['C4 E4 G4 B4', 'C2'], Bbmaj7s11: ['D4 E4 F4 A4', 'Bb2'], Ebmaj7s11: ['G3 Bb3 Eb4 A4', 'D2'],
      Dadd9: ['F3 A3 D4 E4', 'D2'], CmajD: ['C4 E4 G4 B4', 'D2'], GmBb: ['Bb3 D4 F4 A4', 'Bb2'],
      Asus4: ['D4 E4 A4 A3', 'A2']};
    const A1 = [['Dm9', 'A4:0:6 C5:6:2 D5:8:4 E5:12:4'], ['Bbmaj7', 'F5:0:8 E5:8:2 D5:10:2 A4:12:4'],
      ['C69', 'G4:0:4 A4:4:2 C5:6:2 E5:8:6 D5:14:2'], ['Am7', 'C5:0:6 B4:6:2 A4:8:8'],
      ['Dm9', 'A4:0:4 D5:4:4 F5:8:4 E5:12:2 D5:14:2'], ['Gm9', 'A5:0:6 G5:6:2 F5:8:4 D5:12:4'],
      ['Bbmaj7', 'F5:0:4 E5:4:4 D5:8:2 C5:10:2 D5:12:4'], ['A7', 'E5:0:12 C#5:12:4']];
    const B1 = [['Fmaj9', 'C5:0:4 E5:4:4 G5:8:6 A5:14:2'], ['Em7', 'G5:0:8 B4:8:4 D5:12:4'],
      ['Dm9', 'F5:0:6 E5:6:2 D5:8:4 A4:12:4'], ['Cmaj7', 'E5:0:12 G5:12:4'],
      ['Bbmaj7s11', 'D5:0:4 E5:4:4 F5:8:4 A5:12:4'], ['Am7', 'G5:0:6 E5:6:2 C5:8:8'],
      ['Gm9', 'D5:0:4 F5:4:4 A5:8:4 Bb5:12:4'], ['A7sus', 'A5:0:8 G5:8:4 E5:12:4']];
    const A2 = A1.slice(0, 4).concat([['Dm9', 'D5:0:4 F5:4:4 A5:8:6 G5:14:2'], ['Gm9', 'F5:0:8 D5:8:4 Bb4:12:4'],
      ['Bbmaj7', 'C5:0:4 D5:4:4 F5:8:4 E5:12:4'], ['A7sus', 'E5:0:8 D5:8:8']]);
    const C1 = [['Dadd9', 'D5:0:3 E5:3:1 F5:4:12'], ['Ebmaj7s11', 'G5:0:8 F5:8:4 Eb5:12:4'],
      ['Dm9', 'D5:0:16'], ['CmajD', 'E5:4:4 G5:8:4 B4:12:4'], ['Bbmaj7', 'A4:0:8 C5:8:4 D5:12:4'],
      ['GmBb', 'F5:0:8 E5:8:4 D5:12:4'], ['Asus4', 'D5:0:8 E5:8:8'], ['A7', 'C#5:0:4 E5:4:4 G5:8:4 A5:12:4']];
    const SONG = [];
    [[A1, 'A'], [B1, 'B'], [A2, 'A2'], [C1, 'C']].forEach(([sec, name]) => sec.forEach(([ch, mel]) => {
      SONG.push({sec: name, pad: CH[ch][0].split(' ').map(midi), r: midi(CH[ch][1]), mel: bar(mel)});
    }));

    function build(c, out){
      const mtof = n => 440 * Math.pow(2, (n - 69) / 12);
      const noise = c.createBuffer(1, c.sampleRate, c.sampleRate), nd = noise.getChannelData(0);
      for (let i = 0; i < nd.length; i++) nd[i] = Math.random() * 2 - 1;
      const comp = c.createDynamicsCompressor(); comp.threshold.value = -18; comp.ratio.value = 3; comp.connect(out);
      // sala de reverberação (resposta ao impulso sintetizada)
      const len = Math.floor(c.sampleRate * 2.8), ir = c.createBuffer(2, len, c.sampleRate);
      for (let ch = 0; ch < 2; ch++) { const d = ir.getChannelData(ch); for (let i = 0; i < len; i++) d[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / len, 2.6); }
      const rev = c.createConvolver(); rev.buffer = ir;
      const revOut = c.createGain(); revOut.gain.value = 0.45; rev.connect(revOut); revOut.connect(comp);
      function bus(amt, pan){
        const g = c.createGain(), sg = c.createGain(); sg.gain.value = amt;
        let o = g;
        if (pan && c.createStereoPanner) { const p = c.createStereoPanner(); p.pan.value = pan; g.connect(p); o = p; }
        o.connect(comp); o.connect(sg); sg.connect(rev);
        return g;
      }
      const padF = c.createBiquadFilter(); padF.type = 'lowpass'; padF.frequency.value = 1400; padF.Q.value = 0.4;
      padF.connect(bus(0.7));
      const arpBus = bus(0.6, -0.25), leadBus = bus(0.5, 0.1), bassBus = bus(0.1), percBus = bus(0.25);
      const echo = c.createDelay(1.5), fb = c.createGain(), echoOut = c.createGain();
      echo.delayTime.value = STEP * 3; fb.gain.value = 0.32; echoOut.gain.value = 0.5;
      echo.connect(fb); fb.connect(echo); echo.connect(echoOut); echoOut.connect(arpBus);
      const arpIn = c.createGain(); arpIn.connect(arpBus); arpIn.connect(echo);

      function g0(t, a, peak, hold, rel){
        const g = c.createGain();
        g.gain.setValueAtTime(0.0001, t); g.gain.linearRampToValueAtTime(peak, t + a);
        g.gain.setValueAtTime(peak, t + Math.max(a, hold)); g.gain.linearRampToValueAtTime(0.0001, t + Math.max(a, hold) + rel);
        return g;
      }
      function pad(notes, t, dur){
        notes.forEach(n => [-7, 7].forEach(det => {
          const o = c.createOscillator(); o.type = 'sawtooth'; o.frequency.value = mtof(n); o.detune.value = det;
          const g = g0(t, 0.8, 0.016, dur - 0.05, 1.1);
          o.connect(g); g.connect(padF); o.start(t); o.stop(t + dur + 1.2);
        }));
      }
      function vibrato(o, f, t, dur, depth){
        const l = c.createOscillator(), lg = c.createGain(); l.frequency.value = 4.8;
        lg.gain.setValueAtTime(0, t); lg.gain.setValueAtTime(0, t + 0.25); lg.gain.linearRampToValueAtTime(f * depth, t + 0.6);
        l.connect(lg); lg.connect(o.frequency); l.start(t); l.stop(t + dur + 0.5);
      }
      function flute(n, t, dur, peak){  // flauta de bambu: seno + triângulo + sopro
        const f = mtof(n);
        [['sine', 1, 1], ['triangle', 1, 0.3], ['sine', 2, 0.07]].forEach(([type, m, k]) => {
          const o = c.createOscillator(); o.type = type; o.frequency.value = f * m;
          vibrato(o, f * m, t, dur, 0.006);
          const g = g0(t, 0.07, peak * k, dur * 0.92, 0.25);
          o.connect(g); g.connect(leadBus); o.start(t); o.stop(t + dur + 0.4);
        });
        const s = c.createBufferSource(); s.buffer = noise;
        const bp = c.createBiquadFilter(); bp.type = 'bandpass'; bp.frequency.value = f * 2; bp.Q.value = 1.2;
        const g = c.createGain();
        g.gain.setValueAtTime(peak * 0.35, t); g.gain.exponentialRampToValueAtTime(peak * 0.04, t + 0.12);
        g.gain.setValueAtTime(peak * 0.04, t + dur * 0.9); g.gain.linearRampToValueAtTime(0.0001, t + dur + 0.1);
        s.connect(bp); bp.connect(g); g.connect(leadBus); s.start(t, Math.random() * 0.4); s.stop(t + dur + 0.15);
      }
      function oboe(n, t, dur, peak){  // oboé: dente de serra num filtro nasal
        const f = mtof(n), o = c.createOscillator(); o.type = 'sawtooth'; o.frequency.value = f;
        vibrato(o, f, t, dur, 0.005);
        const bp = c.createBiquadFilter(); bp.type = 'bandpass'; bp.frequency.value = 1300; bp.Q.value = 1.1;
        const lp = c.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = 3200;
        const g = g0(t, 0.05, peak, dur * 0.92, 0.2);
        o.connect(bp); bp.connect(lp); lp.connect(g); g.connect(leadBus); o.start(t); o.stop(t + dur + 0.3);
      }
      function arp(n, t, peak){  // dedilhado de harpa
        [['triangle', 1, 1], ['sine', 2, 0.25]].forEach(([type, m, k]) => {
          const o = c.createOscillator(); o.type = type; o.frequency.value = mtof(n) * m;
          const g = c.createGain();
          g.gain.setValueAtTime(0.0001, t); g.gain.linearRampToValueAtTime(peak * k, t + 0.006);
          g.gain.exponentialRampToValueAtTime(0.0001, t + 0.9);
          o.connect(g); g.connect(arpIn); o.start(t); o.stop(t + 1);
        });
      }
      function bass(n, t, dur){
        [['triangle', 1, 0.34], ['sine', 0.5, 0.12]].forEach(([type, m, k]) => {
          const o = c.createOscillator(); o.type = type; o.frequency.value = mtof(n) * m;
          const g = g0(t, 0.015, k, dur * 0.9, 0.12);
          o.connect(g); g.connect(bassBus); o.start(t); o.stop(t + dur + 0.2);
        });
      }
      function drum(t, f1, f2, dur, peak){
        const o = c.createOscillator(), g = c.createGain(); o.type = 'sine';
        o.frequency.setValueAtTime(f1, t); o.frequency.exponentialRampToValueAtTime(f2, t + dur * 0.5);
        g.gain.setValueAtTime(0.0001, t); g.gain.linearRampToValueAtTime(peak, t + 0.005);
        g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
        o.connect(g); g.connect(percBus); o.start(t); o.stop(t + dur + 0.05);
      }
      function nz(t, dur, peak, type, freq, q){
        const s = c.createBufferSource(); s.buffer = noise;
        const f = c.createBiquadFilter(); f.type = type; f.frequency.value = freq; f.Q.value = q || 0.8;
        const g = c.createGain(); g.gain.setValueAtTime(peak, t); g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
        s.connect(f); f.connect(g); g.connect(percBus); s.start(t, Math.random() * 0.5); s.stop(t + dur + 0.02);
      }
      function cricket(t){
        const f = 3900 + Math.random() * 700;
        for (let k = 0; k < 3; k++) {
          const o = c.createOscillator(), g = c.createGain(), s = t + k * 0.11;
          o.type = 'sine'; o.frequency.value = f;
          g.gain.setValueAtTime(0.0001, s); g.gain.linearRampToValueAtTime(0.006, s + 0.012);
          g.gain.exponentialRampToValueAtTime(0.0001, s + 0.06);
          o.connect(g); g.connect(arpBus); o.start(s); o.stop(s + 0.07);
        }
      }
      function owl(t){  // coruja ao longe
        [0, 0.5].forEach((d, k) => {
          const o = c.createOscillator(), g = c.createGain(), s = t + d;
          o.type = 'sine'; o.frequency.setValueAtTime(390 - k * 25, s); o.frequency.linearRampToValueAtTime(350 - k * 25, s + 0.32);
          g.gain.setValueAtTime(0.0001, s); g.gain.linearRampToValueAtTime(0.012, s + 0.06);
          g.gain.exponentialRampToValueAtTime(0.0001, s + 0.36);
          o.connect(g); g.connect(leadBus); o.start(s); o.stop(s + 0.4);
        });
      }
      const UPDOWN = [0, 1, 2, 3, 2, 1, 3, 1];
      function step(i, t, lvl){
        lvl = lvl || 0;
        const ST = STEP / TEMPO[Math.min(lvl, 2)];  // reta final: andamento mais rápido
        const b = Math.floor(i / SPB) % SONG.length, s = i % SPB, B = SONG[b], sec = B.sec;
        const nxt = SONG[(b + 1) % SONG.length];
        if (s === 0) pad(B.pad, t, ST * SPB);
        // melodia: flauta (A, A', C) e oboé (B); no A' o oboé sustenta a voz de cima do acorde
        B.mel.forEach(([n, st, l]) => {
          if (st !== s) return;
          const dur = l * ST;
          if (sec === 'B') oboe(n, t, dur, 0.09); else flute(n, t, dur, sec === 'C' ? 0.1 : 0.12);
        });
        if (sec === 'A2' && (s === 0 || s === 8)) oboe(B.pad[3] + (s ? 0 : -12) + 12 * (B.pad[3] < 60), t, ST * 7.5, 0.04);
        // arpejo
        const every = sec === 'C' ? 4 : 2;
        if (s % every === 0) arp(B.pad[UPDOWN[(s / 2) % 8]] + 12, t, sec === 'C' ? 0.05 : 0.04);
        // baixo: mínimas (A), caminhando (B, A'), pedal (C)
        const r = B.r, nr = nxt.r;
        if (sec === 'C') { if (s === 0) bass(r, t, ST * 15); }
        else if (sec === 'A') { if (s === 0) bass(r, t, ST * 7); if (s === 8) bass(r + 7, t, ST * 7); }
        else {
          if (s === 0) bass(r, t, ST * 3.6);
          if (s === 4) bass(r + 7, t, ST * 3.6);
          if (s === 8) bass(r + (sec === 'B' ? 12 : 10), t, ST * 3.6);
          if (s === 12) bass(nr + (nr > r ? -1 : 1), t, ST * 3.6);
        }
        // reta final (alguém com 3 cartas ou menos): percussão mais presente e camada de tensão
        if (lvl >= 1) {
          if (s % 4 === 0) drum(t, 95, 45, 0.3, s % 8 === 0 ? 0.3 : 0.2);
          if (s === 4 || s === 12) nz(t, 0.05, 0.06, 'bandpass', 1900, 1.4);
          nz(t, 0.035, s % 2 ? 0.014 : 0.03, 'highpass', 7200);
          if (s % 2 === 0) bass(r + (s % 4 ? 12 : 0), t, ST * 1.6);  // ostinato pulsante no baixo
          if (lvl >= 2 && s % 2 === 0) arp(B.pad[3] + 24, t, 0.025);  // UNO na mesa: brilho agudo insistente
        } else
        // percussão leve
        if (sec === 'C') {
          if (s === 0 || s === 6 || s === 12) drum(t, 150, 72, 0.5, s ? 0.14 : 0.2);
        } else {
          if (s === 0) drum(t, 90, 45, 0.35, 0.28);
          if (sec !== 'A' && s === 10) drum(t, 90, 45, 0.3, 0.16);
          if (sec !== 'A' && s === 8) nz(t, 0.04, 0.05, 'bandpass', 1900, 1.4);
          if (s % 2 === 0) nz(t, 0.045, s % 4 === 2 ? 0.035 : 0.018, 'highpass', 7000);
        }
        // mata noturna
        if (s === 0) {
          if (Math.random() < 0.35) cricket(t + Math.random() * ST * 12);
          if (Math.random() < 0.1) owl(t + Math.random() * ST * 8);
        }
      }
      return { step: step };
    }
    return { name: 'game', tempo: TEMPO, step: STEP, steps: SONG.length * SPB, build: build, vol: VOL_GAME, fadeIn: 3.5 };
  })();

  // ------------------------------------------------------------------ sequenciador
  function pref(){ try { return W.localStorage.getItem(KEY) !== 'off'; } catch (e) { return true; } }
  function setPref(on){ try { W.localStorage.setItem(KEY, on ? 'on' : 'off'); } catch (e) {} }
  M.enabled = pref;

  M.tracks = { home: HOME, game: GAME };
  function tick(T){
    const c = M.ctx;
    if (!c || !T.playing) return;
    if (T.next < c.currentTime - 0.2) T.next = c.currentTime + 0.05;  // aba ficou parada: não despeja notas atrasadas
    while (T.next < c.currentTime + LOOK) {
      // a tensão (reta final) só muda no começo de um compasso: sem cortar a frase
      if (T.i % 16 === 0) T.lvl = T.tempo ? Math.max(0, Math.min(2, M.tensionLevel | 0)) : 0;
      T.voices.step(T.i, T.next, T.lvl || 0);
      T.i = (T.i + 1) % T.steps;
      T.next += T.step / (T.tempo ? T.tempo[T.lvl || 0] : 1);
    }
  }
  function ramp(param, value, secs){
    const now = M.ctx.currentTime;
    param.cancelScheduledValues(now); param.setValueAtTime(Math.max(0.0001, param.value), now);
    param.linearRampToValueAtTime(value, now + secs);
  }
  function start(T){
    const c = M.ctx;
    if (!T.master) {
      T.duck = c.createGain(); T.duck.connect(c.destination);
      T.master = c.createGain(); T.master.gain.value = 0.0001; T.master.connect(T.duck);
      T.voices = T.build(c, T.master);
    }
    if (T.stopT) { clearTimeout(T.stopT); T.stopT = null; }
    ramp(T.master.gain, T.vol, T.fadeIn);  // fade-in (ou volta do fade-out sem reiniciar)
    if (T.playing) return;  // já tocando: não reinicia nem duplica
    T.playing = true; T.i = 0; T.next = c.currentTime + 0.08;
    T.timer = W.setInterval(function(){ tick(T); }, 25);
    tick(T);
  }
  function stop(T){
    if (!T.playing || T.stopT) return;
    ramp(T.master.gain, 0.0001, 1.6);  // fade-out (crossfade com a outra trilha)
    T.stopT = W.setTimeout(function(){ W.clearInterval(T.timer); T.timer = null; T.playing = false; T.stopT = null; }, 1700);
  }
  Object.defineProperty(M, 'playing', { get: function(){ return HOME.playing === true || GAME.playing === true; } });
  Object.defineProperty(M, 'want', { get: function(){ return !!M.mode; } });
  M.unlock = function(){  // dentro de um gesto (clique/toque/tecla): iOS exige criar/retomar aqui
    if (!M.ctx) {
      try { M.ctx = new (W.AudioContext || W.webkitAudioContext)(); } catch (e) { return; }
    }
    if (M.ctx.state !== 'running') M.ctx.resume().then(M.sync).catch(function(){});
    M.sync();
  };
  M.sync = function(){
    const ok = !M.muted && pref() && M.ctx && M.ctx.state === 'running';
    [HOME, GAME].forEach(function(T){
      if (ok && M.mode === T.name) start(T);
      else if (M.ctx && T.master) stop(T);
    });
    paint();
  };
  // efeito sonoro tocando: a música do jogo abaixa um pouco e volta suave;
  // vitória/derrota abaixam bem mais, para o efeito aparecer
  M.duck = function(names, seq){
    if (seq !== undefined) { if (seq <= M.duckSeq) return; M.duckSeq = seq; }
    if (!M.ctx || !names || !names.length) return;
    const big = names.some(function(n){ return n === 'win' || n === 'defeat' || n === 'fanfare'; });
    const low = big ? 0.15 : 0.55, hold = big ? 4.5 : 0.9, now = M.ctx.currentTime;
    [HOME, GAME].forEach(function(T){
      if (!T.duck) return;
      const g = T.duck.gain;
      g.cancelScheduledValues(now); g.setValueAtTime(g.value, now);
      g.linearRampToValueAtTime(low, now + 0.15);
      g.setValueAtTime(low, now + hold); g.linearRampToValueAtTime(1, now + hold + 1.5);
    });
  };
  M.setTension = function(level){ M.tensionLevel = Math.max(0, Math.min(2, level | 0)); };
  M.set = function(mode, muted){ M.mode = mode === true ? 'home' : (mode || ''); M.muted = !!muted; M.sync(); };
  ['pointerdown', 'touchend', 'keydown'].forEach(function(ev){
    W.document.addEventListener(ev, function(){ if (M.mode && pref()) M.unlock(); }, {capture: true, passive: true});
  });

  // ------------------------------------------------------------------ botão "Música"
  const SVG = '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2"'
    + ' stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    + '<ellipse cx="8" cy="18" rx="3.6" ry="2.7" transform="rotate(-22 8 18)"/><path d="M11.2 17V3.5"/>'
    + '<path d="M11.2 3.5c3.4.3 6.3 2.4 7.3 5.6-2.3-1.3-4.7-1.4-7.3-.4"/>'
    + '<path class="off" d="M4 4l16 16"/></svg>';
  function button(){
    let b = W.document.getElementById('uno-music');
    if (b || !W.document.body) return b;
    b = W.document.createElement('button');
    b.id = 'uno-music'; b.type = 'button';
    b.innerHTML = SVG + '<span>Música</span>';
    b.style.cssText = 'position:fixed;left:12px;bottom:12px;z-index:999991;display:none;align-items:center;gap:6px;'
      + 'padding:6px 11px;border-radius:999px;border:1px solid #8a6a2c;background:rgba(18,13,8,.86);color:#e8c46a;'
      + 'font:600 12px/1 inherit;font-family:inherit;letter-spacing:.03em;cursor:pointer;box-shadow:0 2px 10px #0008;';
    b.addEventListener('click', function(){ setPref(!pref()); M.unlock(); paint(); });
    W.document.body.appendChild(b);
    return b;
  }
  function paint(){
    const b = button();
    if (!b) return;
    const on = pref();
    b.style.display = M.mode ? 'inline-flex' : 'none';
    const label = b.querySelector('span'); if (label) label.style.display = M.mode === 'game' ? 'none' : 'inline';  // no jogo: só o ícone
    b.style.padding = M.mode === 'game' ? '7px' : '6px 11px';
    b.style.opacity = on && !M.muted ? '1' : '.6';
    b.setAttribute('aria-pressed', on ? 'true' : 'false');
    b.setAttribute('aria-label', 'Música');
    b.title = on ? 'Música: ligada (clique para desligar)' : 'Música: desligada (clique para ligar)';
    const off = b.querySelector('.off'); if (off) off.style.display = on ? 'none' : 'inline';
  }
})();
"""

LOADER = r"""<!doctype html><html><body><script>
(function(){
  var W = window;
  try { if (window.parent && window.parent !== window && window.parent.document) W = window.parent; } catch (e) { W = window; }
  if (!W.__unoMusic) {
    try { var tag = W.document.createElement('script'); tag.textContent = __ENGINE__; W.document.head.appendChild(tag); } catch (e) {}
  }
  if (!W.__unoMusic) { W = window; (new Function(__ENGINE__))(); }
  W.__unoMusic.set(__PLAY__, __MUTED__);
})();
</script></body></html>"""


def engine_js() -> str:
    return (MUSIC_ENGINE.replace("__VOLUME__", repr(VOLUME)).replace("__GAME_VOLUME__", repr(GAME_VOLUME))
            .replace("__KEY__", STORAGE_KEY))


MODES = ("home", "game", "")

TENSION_SCRIPT = r"""<!doctype html><html><body><script>
(function(){
  var W = window;
  try { if (window.parent && window.parent !== window && window.parent.document) W = window.parent; } catch (e) { W = window; }
  W.__unoMusicTension = __LEVEL__;
  if (W.__unoMusic && W.__unoMusic.setTension) W.__unoMusic.setTension(__LEVEL__);
})();
</script></body></html>"""


def tension_level(game: dict | None, players: list[dict] | None = None) -> int:
    """Reta final, a partir do estado que todos veem: 0 = normal, 1 = alguém com 3 cartas
    ou menos, 2 = alguém com 1 carta (UNO). Só durante uma rodada em andamento."""
    if not game or game.get("status") != "playing":
        return 0
    active = {p["id"] for p in players or [] if not p.get("left")} or set(game.get("hands", {}))
    sizes = [len(h) for pid, h in game.get("hands", {}).items() if pid in active]
    if not sizes:
        return 0
    least = min(sizes)
    return 2 if least <= 1 else 1 if least <= 3 else 0


def tension_script(level: int) -> str:
    """Iframe minúsculo que só avisa o motor (já tocando) da tensão atual: não reinicia nada."""
    return TENSION_SCRIPT.replace("__LEVEL__", str(max(0, min(2, int(level)))))


def music_script(mode: str, muted: bool = False) -> str:
    """Documento do iframe: instala o motor (uma vez) e diz qual trilha tocar
    ("home" = tela inicial, "game" = sala/partida, "" = nenhuma). Só depende de
    (trilha, mudo): o Streamlit não recria o iframe a cada rerun."""
    mode = mode if mode in MODES else ""
    return (LOADER.replace("__ENGINE__", json.dumps(engine_js()))
            .replace("__PLAY__", json.dumps(mode))
            .replace("__MUTED__", "true" if muted else "false"))
