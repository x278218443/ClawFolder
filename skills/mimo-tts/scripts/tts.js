#!/usr/bin/env node

/**
 * MiMo V2-TTS 语音合成核心脚本
 * 使用 OpenAI SDK 兼容格式调用 MiMo API
 * 文档：https://platform.xiaomimimo.com/#/docs/usage-guide/speech-synthesis
 */

const fs = require('fs');
const path = require('path');
const https = require('https');

// ---- 常量 ----
const API_BASE = process.env.MIMO_API_BASE || 'https://api.xiaomimimo.com/v1';
const MAX_TEXT_LENGTH = 2000;
const REQUEST_TIMEOUT_MS = 120000;
const MAX_RETRIES = 3;
const RETRY_DELAY_MS = 2000;
const SEGMENT_GAP_MS = 300;

// ---- WAV 解析 ----
function parseWavHeader(buf) {
  return {
    format:        buf.readUInt16LE(20),
    channels:      buf.readUInt16LE(22),
    sampleRate:    buf.readUInt32LE(24),
    byteRate:      buf.readUInt32LE(28),
    blockAlign:    buf.readUInt16LE(32),
    bitsPerSample: buf.readUInt16LE(34),
    dataSize:      buf.readUInt32LE(40),
  };
}

function buildWavHeader(dataSize, info) {
  const h = Buffer.alloc(44);
  h.write('RIFF', 0);
  h.writeUInt32LE(36 + dataSize, 4);
  h.write('WAVE', 8);
  h.write('fmt ', 12);
  h.writeUInt32LE(16, 16);
  h.writeUInt16LE(info.format, 20);
  h.writeUInt16LE(info.channels, 22);
  h.writeUInt32LE(info.sampleRate, 24);
  h.writeUInt32LE(info.byteRate, 28);
  h.writeUInt16LE(info.blockAlign, 32);
  h.writeUInt16LE(info.bitsPerSample, 34);
  h.write('data', 36);
  h.writeUInt32LE(dataSize, 40);
  return h;
}

// ---- 文本分段 ----
function splitText(text, maxLen = MAX_TEXT_LENGTH) {
  if (text.length <= maxLen) return [text];

  // 提取 style 标签（支持属性和空格）
  const styleMatch = text.match(/^(<style\b[^>]*>.*?<\/style>\s*)/is);
  const styleTag = styleMatch ? styleMatch[1] : '';
  const body = styleMatch ? text.slice(styleTag.length) : text;

  const segments = [];
  const sentences = body.split(/(?<=[。！？；…\n])/);
  let current = '';

  for (const s of sentences) {
    const limit = styleTag ? maxLen - styleTag.length : maxLen;
    if ((current + s).length > limit && current.length > 0) {
      segments.push(styleTag + current.trim());
      current = s;
    } else {
      current += s;
    }
  }
  if (current.trim()) segments.push(styleTag + current.trim());

  // 超长强制截断
  const result = [];
  for (const seg of segments) {
    if (seg.length <= maxLen) {
      result.push(seg);
    } else {
      for (let i = 0; i < seg.length; i += maxLen) {
        result.push(seg.substring(i, i + maxLen));
      }
    }
  }
  return result;
}

// ---- API 调用 ----
async function callTTSAPI(text, voice, format, stream) {
  const apiKey = process.env.MIMO_API_KEY;
  if (!apiKey) throw new Error('未设置 MIMO_API_KEY 环境变量');

  const requestBody = {
    model: 'mimo-v2-tts',
    messages: [
      { role: 'user', content: 'Please speak the following text.' },
      { role: 'assistant', content: text }
    ],
    audio: { format: stream ? 'pcm16' : format, voice },
    stream
  };

  return new Promise((resolve, reject) => {
    const url = new URL(`${API_BASE}/chat/completions`);
    const postData = JSON.stringify(requestBody);

    const req = https.request({
      hostname: url.hostname,
      port: url.port || 443,
      path: url.pathname,
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${apiKey}`,
        'Content-Type': 'application/json',
        'Content-Length': Buffer.byteLength(postData)
      }
    }, (res) => {
      const chunks = [];
      res.on('data', chunk => chunks.push(chunk));
      res.on('end', () => {
        const body = Buffer.concat(chunks).toString();
        if (res.statusCode === 200) {
          try { resolve(JSON.parse(body)); }
          catch (e) { reject(new Error(`响应解析失败：${e.message}`)); }
        } else if (res.statusCode === 429 || res.statusCode >= 500) {
          reject(new Error(`HTTP_${res.statusCode}`));
        } else {
          reject(new Error(`API 请求失败：HTTP ${res.statusCode}\n${body.substring(0, 300)}`));
        }
      });
    });

    req.on('error', e => reject(new Error(`网络错误：${e.message}`)));
    req.setTimeout(REQUEST_TIMEOUT_MS, () => {
      req.destroy();
      reject(new Error('请求超时'));
    });

    req.write(postData);
    req.end();
  });
}

// 带重试封装
async function callWithRetry(text, voice, format, stream) {
  let lastError;
  for (let i = 1; i <= MAX_RETRIES; i++) {
    try {
      return await callTTSAPI(text, voice, format, stream);
    } catch (err) {
      lastError = err;
      const isRetryable = err.message.startsWith('HTTP_429') ||
                          err.message.startsWith('HTTP_5') ||
                          err.message.includes('网络错误') ||
                          err.message.includes('超时');
      if (!isRetryable || i === MAX_RETRIES) break;
      const delay = RETRY_DELAY_MS * i;
      console.warn(`  ⚠️ 第 ${i}/${MAX_RETRIES} 次失败，${delay}ms 后重试...`);
      await new Promise(r => setTimeout(r, delay));
    }
  }
  throw lastError;
}

// ---- 从响应提取音频 Buffer ----
function extractAudio(response) {
  try {
    const audio = response?.choices?.[0]?.message?.audio;
    if (audio?.data) return Buffer.from(audio.data, 'base64');
    throw new Error('响应中无音频数据，结构: ' + JSON.stringify(response).substring(0, 200));
  } catch (err) {
    if (err.message.includes('无音频数据')) throw err;
    throw new Error(`音频提取失败：${err.message}`);
  }
}

// ---- 合并多个 WAV（支持任意采样率）----
function mergeWavFiles(buffers, gapMs = SEGMENT_GAP_MS) {
  if (buffers.length === 1) return buffers[0];

  const wavInfo = parseWavHeader(buffers[0]);
  const silenceBytes = Math.round(wavInfo.sampleRate * (gapMs / 1000) * wavInfo.blockAlign);
  const silence = Buffer.alloc(silenceBytes, 0);

  const pcmChunks = [];
  for (let i = 0; i < buffers.length; i++) {
    pcmChunks.push(buffers[i].slice(44));
    if (i < buffers.length - 1) pcmChunks.push(silence);
  }
  const pcmData = Buffer.concat(pcmChunks);

  return Buffer.concat([buildWavHeader(pcmData.length, wavInfo), pcmData]);
}

// ---- 读取 stdin ----
function readStdin() {
  return new Promise((resolve, reject) => {
    const chunks = [];
    process.stdin.setEncoding('utf-8');
    process.stdin.on('data', chunk => chunks.push(chunk));
    process.stdin.on('end', () => resolve(chunks.join('').trim()));
    process.stdin.on('error', reject);
  });
}

// ---- 主流程 ----
async function tts(options) {
  const { text, output, voice = 'mimo_default', format = 'wav', stream = false } = options;

  const segments = splitText(text);
  if (segments.length > 1) {
    console.log(`📝 文本 ${text.length} 字，分 ${segments.length} 段合成`);
  }

  const audioBuffers = [];

  for (let i = 0; i < segments.length; i++) {
    const seg = segments[i];
    const label = segments.length > 1
      ? `  🎙️ 第 ${i + 1}/${segments.length} 段（${seg.length} 字）`
      : `  🎙️ 合成（${seg.length} 字）`;

    const response = await callWithRetry(seg, voice, format, stream);
    const buf = extractAudio(response);
    audioBuffers.push(buf);
    console.log(`${label} ✓`);
  }

  const finalAudio = mergeWavFiles(audioBuffers);

  fs.mkdirSync(path.dirname(output), { recursive: true });
  fs.writeFileSync(output, finalAudio);

  const info = parseWavHeader(finalAudio);
  const sizeKB = (finalAudio.length / 1024).toFixed(1);
  const duration = (info.dataSize / info.byteRate).toFixed(1);

  console.log(`✅ 完成 → ${output}`);
  console.log(`   大小：${sizeKB} KB | 时长：约 ${duration}s | ${info.sampleRate}Hz ${info.channels}ch`);

  return { path: output, sizeKB, duration };
}

module.exports = { tts, splitText, readStdin };
