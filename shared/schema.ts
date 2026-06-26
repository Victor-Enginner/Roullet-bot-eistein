import { pgTable, text, serial, integer, boolean, timestamp, real } from "drizzle-orm/pg-core";
import { createInsertSchema } from "drizzle-zod";
import { z } from "zod";

// === TABLE DEFINITIONS ===
export const users = pgTable("users", {
  id: serial("id").primaryKey(),
  email: text("email").notNull().unique(),
  password: text("password").notNull(),
  name: text("name").notNull(),
});

export const signals = pgTable("sinais", {
  id: serial("id").primaryKey(),
  number: integer("number").notNull(),
  status: text("status").notNull(), // 'green' | 'red' | 'protection'
  confidence: integer("confidence").default(75).notNull(),
  entry: text("entry").default("").notNull(),
  strategy: text("strategy").default("default"), // 'terminal', 'pattern_betting', 'probability', 'deep_scan'
  result: text("result").default("pending"), // 'pending' | 'win' | 'protection' | 'loss'
  protectionAttempts: integer("protection_attempts").default(0),
  terminal: integer("terminal"), // Terminal number (1-12)
  reactThoughts: text("react_thoughts"), // JSON string of ReAct thoughts
  abortReason: text("abort_reason"), // If signal was aborted
  timestamp: timestamp("timestamp").defaultNow().notNull(),
});

export const alerts = pgTable("alertas", {
  id: serial("id").primaryKey(),
  message: text("message").notNull(),
  type: text("type").notNull(), // 'sequencia' | 'manipulacao' | 'vicio_zona' | 'deep_scan'
  details: text("details"), // JSON with additional info
  timestamp: timestamp("timestamp").defaultNow().notNull(),
});

export const reports = pgTable("relatorios", {
  id: serial("id").primaryKey(),
  totalSpins: integer("total_spins").default(0).notNull(),
  greens: integer("greens").default(0).notNull(),
  reds: integer("reds").default(0).notNull(),
  protections: integer("protections").default(0).notNull(), // Total protection wins
  lastNumber: integer("last_number").notNull(),
  signalsToday: integer("signals_today").default(0).notNull(),
  currentStreak: integer("current_streak").default(0).notNull(),
  lastSignalResult: text("last_signal_result").default("none").notNull(), // 'win'|'loss'|'protection'|'none'
  consecutiveProtections: integer("consecutive_protections").default(0).notNull(), // Track for deep scan
  strategyWinRates: text("strategy_win_rates").default("{}"), // JSON: { strategy_id: { wins, total, rate } }
  updatedAt: timestamp("updated_at").defaultNow().notNull(),
});

export const radarConfig = pgTable("radar_config", {
  id: serial("id").primaryKey(),
  telegramToken: text("telegram_token").default("").notNull(),
  chatId: text("chat_id").default("").notNull(),
  signalMode: text("signal_mode").default("auto").notNull(), // 'auto' | 'manual'
  confidenceThreshold: integer("confidence_threshold").default(70).notNull(),
  minConfidence90: boolean("min_confidence_90").default(false).notNull(), // Require 90%+ confidence
  deepScanEnabled: boolean("deep_scan_enabled").default(true).notNull(),
  vicioDetectionEnabled: boolean("vicio_detection_enabled").default(true).notNull(),
  voiceAlerts: boolean("voice_alerts").default(true).notNull(),
  radarActive: boolean("radar_active").default(false).notNull(),
  geminiApiKey: text("gemini_api_key").default("").notNull(),
  updatedAt: timestamp("updated_at").defaultNow().notNull(),
});

// === BASE SCHEMAS ===
export const insertUserSchema = createInsertSchema(users).omit({ id: true });
export const insertSignalSchema = createInsertSchema(signals).omit({ id: true, timestamp: true });
export const insertAlertSchema = createInsertSchema(alerts).omit({ id: true, timestamp: true });
export const insertReportSchema = createInsertSchema(reports).omit({ id: true, updatedAt: true });
export const insertRadarConfigSchema = createInsertSchema(radarConfig).omit({ id: true, updatedAt: true });

// === EXTENDED TYPES ===
export interface AgentSignalResponse {
  id: string;
  number: number;
  status: 'ANALYZING' | 'READY' | 'DEEP_SCAN' | 'ABORTED' | 'REJECTED';
  confidence: number;
  reasoning: string;
  reactThoughts?: string;
  entry: string;
  protection: string;
  strategy: string;
  abortReason?: string;
  timestamp: string;
}

export interface ReactiveMessage {
  text: string;
  type: 'thinking' | 'signal' | 'abort' | 'deep_scan' | 'warning' | 'info';
  timestamp: string;
}

export interface StrategyStats {
  strategyId: string;
  wins: number;
  total: number;
  rate: number;
  last10Results: string[];
}

// === EXPLICIT API CONTRACT TYPES ===
export type User = typeof users.$inferSelect;
export type Signal = typeof signals.$inferSelect;
export type Alert = typeof alerts.$inferSelect;
export type Report = typeof reports.$inferSelect;
export type RadarConfig = typeof radarConfig.$inferSelect;

export type CreateUserRequest = z.infer<typeof insertUserSchema>;
export type UpdateUserRequest = Partial<CreateUserRequest>;
export type UpdateRadarConfigRequest = Partial<z.infer<typeof insertRadarConfigSchema>>;

export interface GeneratedSignal {
  entry: string;
  targetColor: string;
  confidence: number;
  protection: string;
  countdown: number;
  timestamp: string;
}

export interface HealthResponse {
  status: string;
  system: string;
  version: string;
  radarActive: boolean;
  timestamp: string;
}

export interface MetricsResponse {
  signalsToday: number;
  winRate: number;
  currentStreak: number;
  lastSignalResult: string;
  totalGreens: number;
  totalReds: number;
  lastNumber: number;
}
