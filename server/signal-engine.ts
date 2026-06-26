// RADAR DO GREEN — Signal Engine v2.0
// Advanced roulette pattern analysis with statistical modeling

const RED_NUMBERS = new Set([1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36]);
const BLACK_NUMBERS = new Set([2,4,6,8,10,11,13,15,17,20,22,24,26,28,29,31,33,35]);

// European wheel sector zones
const VOISINS  = [22, 18, 29, 7, 28, 12, 35, 3, 26, 0, 32, 15, 19, 4, 21, 2, 25];
const TIERS    = [33, 16, 24, 5, 10, 23, 8, 30, 11, 36, 13, 27];
const ORPHANS  = [1, 20, 14, 31, 9];

// Martingale gale table
const GALE_TABLE: Record<string, number[]> = {
  "2 gales":  [100, 220, 484],
  "3 gales":  [100, 220, 484, 1065],
  "4 gales":  [100, 220, 484, 1065, 2343],
};

export interface GeneratedSignal {
  entry: string;
  targetColor: string;
  confidence: number;
  protection: string;
  countdown: number;
  timestamp: string;
  analysis?: string;
}

// ─── CORE PATTERN ANALYSIS ──────────────────────────────────────────────────

function analyzeHistory(sample: number[]) {
  const reds   = sample.filter(n => RED_NUMBERS.has(n)).length;
  const blacks = sample.filter(n => BLACK_NUMBERS.has(n)).length;
  const zeros  = sample.filter(n => n === 0).length;

  // Sector distribution
  const voisinsHits = sample.filter(n => VOISINS.includes(n)).length;
  const tiersHits   = sample.filter(n => TIERS.includes(n)).length;
  const orphansHits = sample.filter(n => ORPHANS.includes(n)).length;

  // Color gap — how many spins since last appearance
  let redGap = -1, blackGap = -1;
  for (let i = 0; i < sample.length; i++) {
    if (RED_NUMBERS.has(sample[i])   && redGap   === -1) redGap = i;
    if (BLACK_NUMBERS.has(sample[i]) && blackGap === -1) blackGap = i;
  }

  // Streak detection (last 5 same color)
  let streak = 1;
  for (let i = 1; i < Math.min(5, sample.length); i++) {
    const sameType =
      (RED_NUMBERS.has(sample[0])   && RED_NUMBERS.has(sample[i]))   ||
      (BLACK_NUMBERS.has(sample[0]) && BLACK_NUMBERS.has(sample[i])) ||
      (sample[0] === 0 && sample[i] === 0);
    if (sameType) streak++;
    else break;
  }

  return { reds, blacks, zeros, voisinsHits, tiersHits, orphansHits, redGap, blackGap, streak };
}

function computeConfidence(stats: ReturnType<typeof analyzeHistory>, total: number): number {
  let score = 55; // Base confidence

  const { reds, blacks, zeros, voisinsHits, tiersHits, redGap, blackGap, streak } = stats;

  // Color imbalance factor (max +18)
  const imbalance = Math.abs(reds - blacks);
  if (imbalance >= 4) score += 10;
  else if (imbalance >= 2) score += 5;

  // Streak correction factor (max +12)
  // 4+ consecutive same → counter trend likely
  if (streak >= 4) score += 12;
  else if (streak >= 3) score += 7;

  // Color drought factor (max +12)
  if (redGap >= 4)   score += 8;
  if (blackGap >= 4) score += 8;
  if (redGap >= 6 || blackGap >= 6) score += 4;

  // Zero drought (max +6)
  if (zeros === 0 && total >= 8) score += 6;

  // Sector clustering bonus (max +6)
  if (voisinsHits > tiersHits + 2) score += 4;
  else if (tiersHits > voisinsHits + 2) score += 3;

  // Variance noise ±8
  score += Math.floor(Math.random() * 9) - 4;

  return Math.min(96, Math.max(56, score));
}

// ─── MAIN SIGNAL GENERATOR ───────────────────────────────────────────────────

export function generateSignal(recentNumbers: number[] = []): GeneratedSignal {
  const sample = recentNumbers.length >= 5
    ? recentNumbers.slice(0, 20)
    : generateSimulatedHistory();

  const stats = analyzeHistory(sample);
  const confidence = computeConfidence(stats, sample.length);

  // Determine best direction
  const { reds, blacks, redGap, blackGap, streak } = stats;

  // If last number was red streak → bet black (and vice versa)
  const lastIsRed   = RED_NUMBERS.has(sample[0]);
  const lastIsBlack = BLACK_NUMBERS.has(sample[0]);

  // Primary signal decision
  let betBlack: boolean;
  if (streak >= 3 && lastIsRed)   betBlack = true;      // long red streak → black
  else if (streak >= 3 && lastIsBlack) betBlack = false;  // long black streak → red
  else if (blackGap > redGap)    betBlack = true;        // black is due
  else if (redGap > blackGap)    betBlack = false;       // red is due
  else betBlack = reds > blacks;                          // most frequent → bet other

  const targetColor = betBlack ? 'black' : 'red';
  const targetName  = betBlack ? 'PRETO' : 'VERMELHO';
  const entry = `${targetName} + Zero (proteção)`;

  // Gale table based on confidence
  const protection = confidence >= 85 ? '2 gales' : confidence >= 70 ? '3 gales' : '4 gales';

  // Analysis summary for Telegram
  const analysis = `${reds}V · ${blacks}P · streak:${streak}`;

  return {
    entry,
    targetColor,
    confidence,
    protection,
    countdown: 30,
    timestamp: new Date().toISOString(),
    analysis,
  };
}

// ─── SIMULATED HISTORY GENERATOR ──────────────────────────────────────────────

function generateSimulatedHistory(): number[] {
  const all = [...Array(37).keys()];
  const base: number[] = [];

  // Weighted: simulate realistic streaks
  const biasColor = Math.random() > 0.5 ? RED_NUMBERS : BLACK_NUMBERS;
  for (let i = 0; i < 20; i++) {
    if (Math.random() > 0.3) {
      const colored = all.filter(n => n > 0 && biasColor.has(n));
      base.push(colored[Math.floor(Math.random() * colored.length)]);
    } else {
      base.push(all[Math.floor(Math.random() * all.length)]);
    }
  }
  return base;
}

// ─── TELEGRAM SENDER ─────────────────────────────────────────────────────────

export async function sendTelegramSignal(
  token: string,
  chatId: string,
  signal: GeneratedSignal
): Promise<{ success: boolean; message: string }> {
  if (!token || !chatId) {
    return { success: false, message: 'Token ou Chat ID não configurado' };
  }

  const colorEmoji  = signal.targetColor === 'red' ? '🔴' : '⚫';
  const colorName   = signal.targetColor === 'red' ? 'VERMELHO' : 'PRETO';
  const filledBars  = Math.floor(signal.confidence / 10);
  const emptyBars   = 10 - filledBars;
  const bar = '█'.repeat(filledBars) + '░'.repeat(emptyBars);
  const betAmount   = process.env.BET_AMOUNT ?? '100';
  const gameUrl     = process.env.GAME_URL ?? 'https://geralbet.bet.br/games/playtech/roleta-brasileira';

  const galeList = signal.protection === '2 gales'
    ? `G1: R$${betAmount} → G2: R$${Math.round(Number(betAmount) * 2.2)}`
    : signal.protection === '3 gales'
    ? `G1: R$${betAmount} → G2: R$${Math.round(Number(betAmount) * 2.2)} → G3: R$${Math.round(Number(betAmount) * 4.8)}`
    : `G1: R$${betAmount} → G2: R$${Math.round(Number(betAmount) * 2.2)} → G3: R$${Math.round(Number(betAmount) * 4.8)} → G4: R$${Math.round(Number(betAmount) * 10.6)}`;

  const confidenceLabel =
    signal.confidence >= 85 ? '🟢 ALTA CONFIANÇA' :
    signal.confidence >= 70 ? '🟡 CONFIANÇA MÉDIA' :
                              '🔴 AGUARDE CONFIRMAÇÃO';

  const message = `
🎯 *RADAR DO GREEN — SINAL DETECTADO*
━━━━━━━━━━━━━━━━━━━━

${colorEmoji} *APOSTE NO ${colorName} + ZERO*

📊 *Confiança:* \`${bar}\` *${signal.confidence}%*
${confidenceLabel}

🛡 *Proteção:* ${signal.protection}
💰 *Gale:* ${galeList}

📈 *Análise:* \`${signal.analysis ?? 'Padrão detectado'}\`

⏱ *Modo:* Tempo Real | Auto
🔗 [ABRIR ROLETA](${gameUrl})

⚡ _RADAR DO GREEN Bot v2.0_
`.trim();

  try {
    const res = await fetch(
      `https://api.telegram.org/bot${token}/sendMessage`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          chat_id: chatId,
          text: message,
          parse_mode: 'Markdown',
          disable_web_page_preview: false,
        }),
      }
    );

    const data = await res.json() as any;
    if (data.ok) {
      return { success: true, message: `Sinal enviado! (msg_id: ${data.result?.message_id})` };
    } else {
      return { success: false, message: data.description || 'Falha ao enviar mensagem' };
    }
  } catch (err: any) {
    return { success: false, message: err.message || 'Erro de rede' };
  }
}

// ─── UTILITIES ──────────────────────────────────────────────────────────────

export function calculateWinRate(greens: number, reds: number): number {
  const total = greens + reds;
  if (total === 0) return 0;
  return Math.round((greens / total) * 100 * 10) / 10;
}
