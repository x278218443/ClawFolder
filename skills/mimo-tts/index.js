#!/usr/bin/env node

/**
 * MiMo V2-TTS 语音合成技能
 * 入口文件 - 直接 require tts 模块
 */

const fs = require('fs');
const path = require('path');
const { tts, readStdin } = require('./scripts/tts');

const VALID_VOICES = ['mimo_default', 'default_zh', 'default_en'];
const VALID_FORMATS = ['wav', 'pcm16'];

// 短参数映射
const SHORT_FLAGS = { '-t': '--text', '-o': '--output', '-v': '--voice', '-f': '--format', '-h': '--help' };

function parseArgs(argv) {
  const opts = { voice: 'mimo_default', format: 'wav', stream: false };
  for (let i = 0; i < argv.length; i++) {
    let a = argv[i];
    if (SHORT_FLAGS[a]) a = SHORT_FLAGS[a];

    if ((a === '--text' || a === '--output' || a === '--voice' || a === '--format' || a === '--input') && i + 1 < argv.length) {
      opts[a.slice(2)] = argv[++i];
    } else if (a === '--stream') {
      opts.stream = true;
    } else if (a === '--help') {
      opts.help = true;
    }
  }
  return opts;
}

function showHelp() {
  console.log(`
MiMo V2-TTS 语音合成技能 v1.2.0

用法: mimo-tts [选项]
      echo "文本" | mimo-tts -o out.wav
      mimo-tts -i script.txt -v default_zh -o narration.wav

选项:
  -t, --text <文本>    要转换的文本（--text / --input / stdin 三选一）
  -i, --input <文件>   从文件读取文本
  -o, --output <文件>  输出音频文件路径 (必填)
  -v, --voice <音色>   音色 (默认: mimo_default)
                       可选: mimo_default, default_zh, default_en
  -f, --format <格式>  输出格式 (默认: wav)
                       可选: wav, pcm16
      --stream         流式模式
  -h, --help           帮助信息

示例:
  mimo-tts -t "你好" -o hello.wav
  mimo-tts -i long-script.txt -v default_zh -o narrate.wav
  echo "快速测试" | mimo-tts -o quick.wav
  mimo-tts -t "<style>唱歌</style>原谅我这一生" -o sing.wav

特性:
  - 文本超过 2000 字自动分段合成，段间 300ms 静音
  - 网络失败自动重试（最多 3 次，指数退避）
  - 长文本超时 120s
  - 支持 stdin 管道输入
  - API 地址可通过 MIMO_API_BASE 环境变量覆盖
`);
}

async function main() {
  const opts = parseArgs(process.argv.slice(2));

  if (opts.help) { showHelp(); process.exit(0); }

  // 优先级: --text > --input > stdin
  if (!opts.text && !opts.input && !process.stdin.isTTY) {
    try {
      opts.text = await readStdin();
      if (opts.text) console.log(`📥 从 stdin 读取文本（${opts.text.length} 字）`);
    } catch (err) {
      console.error(`❌ stdin 读取失败：${err.message}`);
      process.exit(1);
    }
  }

  if (opts.input) {
    if (opts.text) {
      console.error('❌ --text 和 --input 不能同时使用');
      process.exit(1);
    }
    try {
      opts.text = fs.readFileSync(opts.input, 'utf-8').trim();
      console.log(`📄 从文件读取：${opts.input}（${opts.text.length} 字）`);
    } catch (err) {
      console.error(`❌ 读取文件失败：${err.message}`);
      process.exit(1);
    }
  }

  if (!opts.text) {
    console.error('❌ 错误：--text / --input / stdin 三选一必填');
    console.error('使用 --help 查看用法');
    process.exit(1);
  }
  if (!opts.output) {
    console.error('❌ 错误：--output 参数是必填的');
    console.error('使用 --help 查看用法');
    process.exit(1);
  }
  if (!VALID_VOICES.includes(opts.voice)) {
    console.error(`❌ 无效音色 "${opts.voice}"，可选：${VALID_VOICES.join(', ')}`);
    process.exit(1);
  }
  if (!VALID_FORMATS.includes(opts.format)) {
    console.error(`❌ 无效格式 "${opts.format}"，可选：${VALID_FORMATS.join(', ')}`);
    process.exit(1);
  }

  // 相对路径 → workspace
  let output = opts.output;
  if (!path.isAbsolute(output)) {
    output = path.join(process.env.HOME, '.openclaw/workspace', output);
  }

  console.log(`🎙️  MiMo TTS | 音色：${opts.voice} | 格式：${opts.format}`);

  try {
    await tts({ ...opts, output });
  } catch (err) {
    console.error(`❌ 合成失败：${err.message}`);
    process.exit(1);
  }
}

main();
