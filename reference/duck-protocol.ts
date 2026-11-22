import crypto from 'crypto';

export const BASE_URL = 'https://duck.ai';

export const DEFAULT_UA =
  'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36';

export const MODELS: Record<string, string> = {
  luna: 'gpt-6-luna',
  'gpt-6-luna': 'gpt-6-luna',
  'gpt-5.6-luna': 'gpt-5.6-luna',
  mini: 'gpt-5.4-mini',
  'gpt-5.4-mini': 'gpt-5.4-mini',
  nano: 'gpt-5.4-nano',
  'gpt-5.4-nano': 'gpt-5.4-nano',
  'haiku-5.5': 'claude-haiku-5-5',
  'claude-haiku-5-5': 'claude-haiku-5-5',
  haiku: 'claude-haiku-4-5',
  'claude-haiku-4-5': 'claude-haiku-4-5',
  gemma: 'tinfoil/gemma4-31b',
  'gemma4-31b': 'tinfoil/gemma4-31b',
  'tinfoil/gemma4-31b': 'tinfoil/gemma4-31b',
  'gpt-oss': 'tinfoil/gpt-oss-120b',
  'gpt-oss-120b': 'tinfoil/gpt-oss-120b',
  'tinfoil/gpt-oss-120b': 'tinfoil/gpt-oss-120b',
  mistral: 'mistral-small-2603',
  'mistral-small-2603': 'mistral-small-2603',
};

export interface ModelOption {
  id: string;
  alias: string;
  name: string;
  provider: string;
  badge: string;
  description: string;
  supportsVision: boolean;
  supportsDraw: boolean;
}

export const MODEL_OPTIONS: ModelOption[] = [
  {
    id: 'gpt-6-luna',
    alias: 'luna',
    name: 'GPT-6 Luna',
    provider: 'OpenAI',
    badge: 'پیش‌فرض',
    description: 'پرچمدار رایگان چندوجهی با پشتیبانی کامل از دیدن تصویر، ساخت تصویر و جستجو',
    supportsVision: true,
    supportsDraw: true,
  },
  {
    id: 'gpt-5.6-luna',
    alias: 'gpt-5.6-luna',
    name: 'GPT-5.6 Luna',
    provider: 'OpenAI',
    badge: 'تحلیلی',
    description: 'نسخه ۵.۶ لونا با دقت بالا در استدلال، کدنویسی و تحلیل تصاویر',
    supportsVision: true,
    supportsDraw: true,
  },
  {
    id: 'gpt-5.4-mini',
    alias: 'mini',
    name: 'GPT-5.4 Mini',
    provider: 'OpenAI',
    badge: 'متوازن',
    description: 'مدل سریع و بهینه برای گفتگوهای روزمره، ترجمه، دیدن و ساخت تصویر',
    supportsVision: true,
    supportsDraw: true,
  },
  {
    id: 'gpt-5.4-nano',
    alias: 'nano',
    name: 'GPT-5.4 Nano',
    provider: 'OpenAI',
    badge: 'فوق سریع',
    description: 'سبک‌ترین مدل با کمترین زمان پاسخ‌دهی برای پرسش‌های کوتاه',
    supportsVision: true,
    supportsDraw: false,
  },
  {
    id: 'claude-haiku-5-5',
    alias: 'haiku-5.5',
    name: 'Claude Haiku 5.5',
    provider: 'Anthropic',
    badge: 'جدید',
    description: 'نسل جدید کلود هایکو ۵.۵ با هوش بالا در کدنویسی، متن فارسی و دیدن تصویر',
    supportsVision: true,
    supportsDraw: false,
  },
  {
    id: 'claude-haiku-4-5',
    alias: 'haiku',
    name: 'Claude Haiku 4.5',
    provider: 'Anthropic',
    badge: 'کد و متن',
    description: 'کلود هایکو ۴.۵ با نگارش طبیعی و دقت عالی در بررسی فایل‌های کد',
    supportsVision: true,
    supportsDraw: false,
  },
  {
    id: 'tinfoil/gemma4-31b',
    alias: 'gemma',
    name: 'Gemma 4 31B',
    provider: 'Google · Tinfoil',
    badge: 'متن‌باز گوگل',
    description: 'مدل ۳۱ میلیارد پارامتری جما ۴ گوگل با رمزنگاری Tinfoil و پشتیبانی از تصویر',
    supportsVision: true,
    supportsDraw: false,
  },
  {
    id: 'tinfoil/gpt-oss-120b',
    alias: 'gpt-oss',
    name: 'GPT-OSS 120B',
    provider: 'OpenAI · Tinfoil',
    badge: '۱۲۰B متن‌باز',
    description: 'مدل بزرگ ۱۲۰ میلیارد پارامتری متن‌باز OpenAI با استدلال گام‌به‌گام',
    supportsVision: false,
    supportsDraw: false,
  },
  {
    id: 'mistral-small-2603',
    alias: 'mistral',
    name: 'Mistral Small 4 (2603)',
    provider: 'Mistral AI',
    badge: 'اروپایی',
    description: 'مدل میسترال اسمال ۴ (نسخه ۲۶۰۳) سریع و متن‌باز',
    supportsVision: false,
    supportsDraw: false,
  },
];

export const IMG_MAX_DIM = 1568;
export const IMG_WEBP_QUALITY = 85;
export const IMG_MAX_PAYLOAD = 3_500_000;

export const TEXT_EXTS = new Set([
  'txt', 'md', 'markdown', 'rst', 'log', 'csv', 'tsv', 'json',
  'jsonl', 'xml', 'yaml', 'yml', 'ini', 'cfg', 'conf', 'toml',
  'env', 'py', 'js', 'mjs', 'cjs', 'ts', 'tsx', 'jsx', 'java',
  'c', 'h', 'cpp', 'hpp', 'cc', 'cs', 'go', 'rs', 'rb', 'php',
  'swift', 'kt', 'kts', 'sh', 'bash', 'zsh', 'ps1', 'bat', 'cmd',
  'sql', 'html', 'htm', 'css', 'scss', 'less', 'vue', 'svelte',
  'dart', 'lua', 'pl', 'r', 'm', 'asm', 'gradle', 'cmake',
  'dockerfile', 'gitignore', 'properties', 'prisma', 'graphql',
]);

export interface DuckImagePart {
  type: 'image';
  mimeType: 'image/webp';
  image: string; // data:image/webp;base64,...
}

export interface DuckTextPart {
  type: 'text';
  text: string;
}

export interface DuckGeneratedImagePart {
  type: 'generated-image';
  result: string;
  width?: number;
  height?: number;
  format?: string;
}

export interface DuckHistoryMessage {
  role: 'user' | 'assistant';
  content: string | Array<DuckTextPart | DuckImagePart>;
  parts?: Array<DuckGeneratedImagePart | DuckTextPart>;
}

export type DuckStreamEvent =
  | { kind: 'message'; value: string }
  | { kind: 'image_title'; value: string }
  | { kind: 'image_partial'; value: Record<string, unknown> }
  | {
      kind: 'image';
      value: {
        b64: string;
        width?: number;
        height?: number;
        format: string;
      };
    }
  | {
      kind: 'tool';
      value: {
        toolName?: string;
        state?: string;
        toolArguments?: unknown;
      };
    }
  | { kind: 'error'; value: string };

export function b64EncodeString(text: string): string {
  return Buffer.from(text, 'utf-8').toString('base64');
}

export function sha256B64(text: string): string {
  return crypto.createHash('sha256').update(text, 'utf-8').digest('base64');
}

export function b64Json(obj: unknown): string {
  return Buffer.from(JSON.stringify(obj), 'utf-8').toString('base64');
}

export function resolveModel(name?: string | null, defaultModel = 'gpt-6-luna'): string {
  if (!name) return defaultModel;
  const trimmed = name.trim().toLowerCase();
  return MODELS[trimmed] || name.trim() || defaultModel;
}

export function extractFeVersion(html: string): string {
  const tagMatch = html.match(/data-version-tag="([^"]*)"/);
  const shaMatch = html.match(/data-version-sha="([^"]*)"/);
  const tag = tagMatch ? tagMatch[1] : 'dev';
  const sha = shaMatch ? shaMatch[1] : 'hash';
  return `${tag}-${sha}`;
}

export function decodeChallengeHeader(rawHeader: string): string {
  const padLen = (4 - (rawHeader.length % 4)) % 4;
  const padded = rawHeader + '='.repeat(padLen);
  return Buffer.from(padded, 'base64').toString('utf-8');
}

export interface SolvedChallenge {
  server_hashes?: string[];
  client_hashes: string[];
  signals?: Record<string, unknown>;
  meta?: Record<string, unknown>;
  __error?: string;
}

export function buildProof(solved: SolvedChallenge): string {
  const proof: Record<string, unknown> = { ...solved };
  proof.client_hashes = (solved.client_hashes || []).map((x) => sha256B64(x));
  const meta: Record<string, unknown> = { ...(solved.meta || {}) };
  Object.assign(meta, {
    origin: BASE_URL,
    stack:
      'Error\nat l (https://duck.ai/dist/duckai-dist/entry.duckai.js:2:2129171)\n' +
      'at async https://duck.ai/dist/duckai-dist/entry.duckai.js:2:1859809',
    duration: '58',
  });
  proof.meta = meta;
  return b64Json(proof);
}

export function buildFeSignals(nowMs = Date.now()): string {
  return b64Json({
    start: nowMs,
    events: [{ name: 'action', delta: 1200, trusted: true }],
    end: 1500,
  });
}

export function isSupportedTextFile(filename: string, mimeType = ''): boolean {
  const parts = filename.toLowerCase().split('.');
  const ext = parts.length > 1 ? parts[parts.length - 1] : '';
  return TEXT_EXTS.has(ext) || mimeType.startsWith('text/') || ext === '';
}

export function formatFileToPromptChunk(
  filename: string,
  content: string,
  maxChars = 60_000
): string {
  const parts = filename.toLowerCase().split('.');
  const ext = parts.length > 1 ? parts[parts.length - 1] : '';
  let body = content;
  let truncated = '';
  if (body.length > maxChars) {
    body = body.slice(0, maxChars);
    truncated = `\n\n[… فایل طولانی بود و به ${maxChars} کاراکتر برش خورد]`;
  }
  const lang = ext || 'text';
  return `\n\nمحتوای فایل «${filename}»:\n\`\`\`${lang}\n${body}\n\`\`\`${truncated}\n`;
}

export interface BuildChatBodyOptions {
  prompt: string;
  model?: string;
  tools?: boolean;
  history?: DuckHistoryMessage[];
  images?: DuckImagePart[];
  draw?: boolean;
  promptExtra?: string;
}

export function getFallbackFreeDuckModel(model: string): string | null {
  const m = resolveModel(model);
  if (m === 'claude-sonnet-5-5' || m === 'claude-opus-5-5') {
    return 'claude-haiku-5-5';
  }
  if (m === 'gpt-5.6-terra' || m === 'gpt-5.6-sol') {
    return 'gpt-6-luna';
  }
  if (
    m === 'meta-llama/Llama-4-Scout-17B-16E-Instruct' ||
    m === 'meta-llama/Llama-3.3-70B-Instruct-Turbo' ||
    m === 'o4-mini' ||
    m === 'gpt-4o-mini'
  ) {
    return 'gpt-5.4-nano';
  }
  return null;
}

export function buildChatRequestBody(opts: BuildChatBodyOptions): Record<string, unknown> {
  const model = resolveModel(opts.model);
  const tools =
    model === 'mistral-small-2603' ? false : (opts.tools ?? true);
  const reasoningEffort =
    model === 'tinfoil/gpt-oss-120b' ? 'low' : 'none';
  const promptExtra = opts.promptExtra ?? '';
  const content: Array<DuckTextPart | DuckImagePart> = [
    { type: 'text', text: opts.prompt + promptExtra },
  ];
  if (opts.images && opts.images.length > 0) {
    content.push(...opts.images);
  }
  const msgs: DuckHistoryMessage[] = [...(opts.history || []), { role: 'user', content }];
  const body: Record<string, unknown> = {
    model,
    messages: msgs,
    canUseTools: tools,
    reasoningEffort,
    canUseApproxLocation: null,
    canDelegateImageGeneration: null,
    canShowGreeting: false,
  };
  if (opts.draw) {
    body.metadata = { toolChoice: { GenerateImage: true } };
  }
  return body;
}

export function parseSseLine(rawLine: string): DuckStreamEvent | null {
  const line = rawLine.trim();
  if (!line || !line.startsWith('data: ')) {
    return null;
  }
  const payload = line.slice(6).trim();
  if (!payload || payload.startsWith('[')) {
    // [PING] / [DONE] / [CHAT_TITLE:...]
    return null;
  }
  let ev: Record<string, any>;
  try {
    ev = JSON.parse(payload);
  } catch {
    return null;
  }

  if (ev.action === 'error') {
    return {
      kind: 'error',
      value: `خطای سرور (${ev.status ?? '?'}): ${ev.type ?? '?'}`,
    };
  }

  const role = ev.role || '';
  const name = ev.name || '';

  if (typeof ev.message === 'string' && ev.message.length > 0) {
    return { kind: 'message', value: ev.message };
  }

  if (role === 'ui-component' && name === 'generate-image') {
    const data = ev.data || {};
    const dtype = data.type;
    if (dtype === 'image-title') {
      return { kind: 'image_title', value: String(data.title || '') };
    }
    if (dtype === 'image-partial' || data.status === 'partial') {
      return { kind: 'image_partial', value: data };
    }
    if (data.status === 'success' && data.b64Image) {
      return {
        kind: 'image',
        value: {
          b64: String(data.b64Image),
          width: data.width,
          height: data.height,
          format: String(data.format || 'jpeg'),
        },
      };
    }
  }

  if (role === 'tool-invocation') {
    return {
      kind: 'tool',
      value: {
        toolName: ev.toolName,
        state: ev.state,
        toolArguments: ev.toolArguments,
      },
    };
  }

  return null;
}

export type CouncilMode = 'synthesis' | 'debate';

export interface CouncilMemberSpec {
  id: string;
  name: string;
  provider: string;
  roleTitleSynthesis: string;
  roleTitleDebate: string;
}

export const COUNCIL_DEFAULT_MEMBERS: CouncilMemberSpec[] = [
  {
    id: 'gpt-6-luna',
    name: 'GPT-6 Luna',
    provider: 'OpenAI',
    roleTitleSynthesis: 'تحلیل جامع و کاربردی',
    roleTitleDebate: 'موافق و مدافع ایده',
  },
  {
    id: 'claude-haiku-5-5',
    name: 'Claude Haiku 5.5',
    provider: 'Anthropic',
    roleTitleSynthesis: 'بررسی دقیق و ساختاری',
    roleTitleDebate: 'منتقد و چالش‌گر',
  },
  {
    id: 'tinfoil/gemma4-31b',
    name: 'Gemma 4 31B',
    provider: 'Google',
    roleTitleSynthesis: 'استدلال و نگاه مکمل',
    roleTitleDebate: 'تحلیل‌گر بی‌طرف و ریسک‌سنج',
  },
];

export type ParsedSlashCommand =
  | { type: 'none' }
  | { type: 'clear' }
  | { type: 'help' }
  | { type: 'exit' }
  | { type: 'model'; arg: string }
  | { type: 'draw'; prompt: string }
  | { type: 'council'; prompt: string }
  | { type: 'img'; arg: string }
  | { type: 'file'; arg: string }
  | { type: 'live' }
  | { type: 'mic' }
  | { type: 'unknown'; cmd: string };

export function parseSlashCommand(input: string): ParsedSlashCommand {
  const trimmed = input.trim();
  if (!trimmed.startsWith('/')) {
    return { type: 'none' };
  }
  const spaceIdx = trimmed.indexOf(' ');
  const cmd = (spaceIdx === -1 ? trimmed : trimmed.slice(0, spaceIdx)).toLowerCase();
  const arg = spaceIdx === -1 ? '' : trimmed.slice(spaceIdx + 1).trim();

  switch (cmd) {
    case '/clear':
      return { type: 'clear' };
    case '/help':
      return { type: 'help' };
    case '/exit':
      return { type: 'exit' };
    case '/model':
      return { type: 'model', arg };
    case '/draw':
      return { type: 'draw', prompt: arg };
    case '/council':
      return { type: 'council', prompt: arg };
    case '/img':
      return { type: 'img', arg };
    case '/file':
      return { type: 'file', arg };
    case '/live':
    case '/voice':
      return { type: 'live' };
    case '/mic':
      return { type: 'mic' };
    default:
      return { type: 'unknown', cmd };
  }
}

export function buildCliCommandPreview(opts: {
  prompt: string;
  model: string;
  draw?: boolean;
  imageNames?: string[];
  fileNames?: string[];
  proxy?: string;
}): string {
  const parts = ['python duck_cli.py'];
  const escapedPrompt = (opts.prompt || 'سلام، حالت چطوره؟').replace(/"/g, '\\"');
  if (opts.draw) {
    parts.push(`--draw "${escapedPrompt}"`);
  } else {
    parts.push(`--ask "${escapedPrompt}"`);
  }
  if (opts.imageNames && opts.imageNames.length > 0 && !opts.draw) {
    parts.push(`--image ${opts.imageNames.map((n) => `"${n}"`).join(' ')}`);
  }
  if (opts.fileNames && opts.fileNames.length > 0 && !opts.draw) {
    parts.push(`--file ${opts.fileNames.map((n) => `"${n}"`).join(' ')}`);
  }
  if (opts.model && opts.model !== 'gpt-6-luna') {
    parts.push(`--model ${opts.model}`);
  }
  if (opts.proxy && opts.proxy.trim()) {
    parts.push(`--proxy "${opts.proxy.trim()}"`);
  }
  return parts.join(' ');
}

export function isImageGenerationPrompt(prompt: string): boolean {
  const text = (prompt || '').trim().toLowerCase();
  if (!text) return false;

  const hasImageNoun =
    /(عکس|عکسی|تصویر|تصویری|نقاشی|لوگو|پوستر|والپیپر|آواتار|طرح|کاریکاتور|image|picture|photo|illustration|logo|wallpaper|portrait|sketch)/i.test(
      text
    );
  const hasCreateVerb =
    /(طراحی کن|طراحی بکن|بساز|بکش|تولید کن|درست کن|خلق کن|برام بساز|برام بکش|برام طراحی کن|generate|draw|create|sketch|paint|render|make an image|make a photo)/i.test(
      text
    );

  return hasImageNoun && hasCreateVerb;
}

export type ImageQualityTier = '1K' | '2K' | '4K';
export type ImageAspectRatio = '1:1' | '16:9' | '9:16' | '4:3' | '3:4';

export const IMAGE_QUALITY_OPTIONS: Array<{
  id: ImageQualityTier;
  label: string;
}> = [
  { id: '1K', label: '1K' },
  { id: '2K', label: '2K' },
  { id: '4K', label: '4K' },
];

export const IMAGE_ASPECT_RATIO_OPTIONS: Array<{
  id: ImageAspectRatio;
  label: string;
  title: string;
}> = [
  { id: '1:1', label: '1:1', title: 'مربع (1:1)' },
  { id: '16:9', label: '16:9', title: 'افقی سینمایی (16:9)' },
  { id: '9:16', label: '9:16', title: 'عمودی موبایل (9:16)' },
  { id: '4:3', label: '4:3', title: 'افقی کلاسیک (4:3)' },
  { id: '3:4', label: '3:4', title: 'عمودی پرتره (3:4)' },
];

export function resolveImageDimensions(
  quality: ImageQualityTier = '2K',
  aspectRatio: ImageAspectRatio = '1:1'
): { width: number; height: number } {
  const table: Record<ImageQualityTier, Record<ImageAspectRatio, [number, number]>> = {
    '1K': {
      '1:1': [1024, 1024],
      '16:9': [1360, 768],
      '9:16': [768, 1360],
      '4:3': [1152, 864],
      '3:4': [864, 1152],
    },
    '2K': {
      '1:1': [2048, 2048],
      '16:9': [2560, 1440],
      '9:16': [1440, 2560],
      '4:3': [2048, 1536],
      '3:4': [1536, 2048],
    },
    '4K': {
      '1:1': [3840, 3840],
      '16:9': [3840, 2160],
      '9:16': [2160, 3840],
      '4:3': [3840, 2880],
      '3:4': [2880, 3840],
    },
  };

  const tier = table[quality] || table['2K'];
  const [width, height] = tier[aspectRatio] || tier['1:1'];
  return { width, height };
}

export function buildEnhancedDrawPrompt(
  prompt: string,
  quality: ImageQualityTier = '2K',
  aspectRatio: ImageAspectRatio = '1:1'
): string {
  const qualityDesc =
    quality === '4K'
      ? 'Ultra-high-resolution 4K UHD masterpiece, hyper-detailed textures, razor-sharp focus, studio lighting'
      : quality === '2K'
      ? 'High-resolution 2K QHD quality, crisp details, rich colors, balanced lighting'
      : 'Clean HD 1K quality';

  const ratioDesc: Record<ImageAspectRatio, string> = {
    '1:1': '1:1 square aspect ratio composition',
    '16:9': '16:9 wide horizontal widescreen composition, full scene framed horizontally',
    '9:16': '9:16 vertical tall portrait composition, subject framed vertically',
    '4:3': '4:3 horizontal landscape composition',
    '3:4': '3:4 vertical portrait composition',
  };

  return `${prompt.trim()}\n\n[Image Specification: ${qualityDesc}, ${ratioDesc[aspectRatio] || ratioDesc['1:1']}]`;
}

export function rebuildHistoryFromMessages(
  messages: Array<{
    role: 'user' | 'assistant';
    text: string;
    files?: Array<{ name: string; content: string }>;
    images?: Array<{ part: DuckImagePart }>;
    generatedImage?: { b64: string; width?: number; height?: number; format: string };
  }>
): DuckHistoryMessage[] {
  return messages.map((m) => {
    if (m.role === 'user') {
      let extra = '';
      if (m.files && m.files.length > 0) {
        for (const f of m.files) {
          extra += formatFileToPromptChunk(f.name, f.content);
        }
      }
      const contentParts: Array<DuckTextPart | DuckImagePart> = [
        { type: 'text', text: (m.text || '...') + extra },
      ];
      if (m.images && m.images.length > 0) {
        for (const img of m.images) {
          contentParts.push(img.part);
        }
      }
      return {
        role: 'user',
        content: contentParts,
      };
    }

    if (m.generatedImage) {
      return {
        role: 'assistant',
        content: '',
        parts: [
          {
            type: 'generated-image',
            result: m.generatedImage.b64,
            width: m.generatedImage.width,
            height: m.generatedImage.height,
            format: m.generatedImage.format,
          },
          { type: 'text', text: m.text || '' },
        ],
      };
    }

    return {
      role: 'assistant',
      content: m.text || '',
    };
  });
}

export function extractImageGenPrompt(toolArguments: unknown): string | null {
  if (!toolArguments) return null;
  let parsed: any = toolArguments;
  if (typeof toolArguments === 'string') {
    try {
      parsed = JSON.parse(toolArguments);
    } catch {
      const trimmed = toolArguments.trim();
      return trimmed || null;
    }
  }
  if (parsed && typeof parsed === 'object') {
    const rawPrompt =
      parsed.imageGenPrompt ||
      parsed.prompt ||
      parsed.description ||
      parsed.query;
    if (typeof rawPrompt === 'string' && rawPrompt.trim()) {
      return rawPrompt.trim();
    }
  }
  return null;
}
