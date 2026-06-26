import type { Express } from "express";
import type { Server } from "http";
import { storage } from "./storage.js";
import { api } from "@shared/routes.js";
import { z } from "zod";
import { generateSignal, sendTelegramSignal, calculateWinRate } from "./signal-engine.js";

// In-memory radar state
let radarInterval: NodeJS.Timeout | null = null;

export async function registerRoutes(
  httpServer: Server,
  app: Express
): Promise<Server> {

  // ─── HEALTH CHECK ────────────────────────────────────────────────────
  app.get(api.health.get.path, async (_req, res) => {
    const config = await storage.getRadarConfig();
    res.json({
      status: 'online',
      system: 'RADAR DO GREEN',
      version: '2.0',
      radarActive: config.radarActive,
      timestamp: new Date().toISOString(),
    });
  });

  // Helper: strip password from user object before sending
  function safeUser(user: { id: number; email: string; password: string; name: string }) {
    const { password: _pw, ...safe } = user;
    return safe;
  }

  // ─── AUTH ────────────────────────────────────────────────────────────
  app.post(api.auth.login.path, async (req, res) => {
    try {
      const input = api.auth.login.input.parse(req.body);
      const user = await storage.getUserByEmail(input.email);
      if (!user || user.password !== input.password) {
        return res.status(401).json({ message: "Email ou senha incorretos" });
      }
      if (req.session) (req.session as any).userId = user.id;
      res.json(safeUser(user));
    } catch (err) {
      if (err instanceof z.ZodError)
        return res.status(400).json({ message: err.errors[0].message, field: err.errors[0].path.join('.') });
      throw err;
    }
  });

  app.post(api.auth.register.path, async (req, res) => {
    try {
      const input = api.auth.register.input.parse(req.body);
      const existingUser = await storage.getUserByEmail(input.email);
      if (existingUser)
        return res.status(409).json({ message: "Este email já está cadastrado", field: "email" });
      const user = await storage.createUser(input);
      if (req.session) (req.session as any).userId = user.id;
      res.status(201).json(safeUser(user));
    } catch (err) {
      if (err instanceof z.ZodError)
        return res.status(400).json({ message: err.errors[0].message, field: err.errors[0].path.join('.') });
      throw err;
    }
  });

  app.get(api.auth.me.path, async (req, res) => {
    if (req.session && (req.session as any).userId) {
      const user = await storage.getUser((req.session as any).userId);
      if (user) return res.json(safeUser(user));
    }
    return res.status(401).json({ message: "Não autenticado" });
  });

  app.post(api.auth.logout.path, (req, res) => {
    if (req.session) req.session.destroy(() => {});
    res.json({ success: true });
  });

  // ─── USERS ───────────────────────────────────────────────────────────
  app.put(api.users.update.path, async (req, res) => {
    try {
      if (!req.session || !(req.session as any).userId)
        return res.status(401).json({ message: "Not authenticated" });
      const id = Number(req.params.id);
      if ((req.session as any).userId !== id)
        return res.status(401).json({ message: "Unauthorized" });
      const input = api.users.update.input.parse(req.body);
      const updatedUser = await storage.updateUser(id, input);
      res.json(updatedUser);
    } catch (err) {
      if (err instanceof z.ZodError)
        return res.status(400).json({ message: err.errors[0].message, field: err.errors[0].path.join('.') });
      throw err;
    }
  });

  // ─── SIGNALS ─────────────────────────────────────────────────────────
  app.get(api.signals.list.path, async (_req, res) => {
    const sigs = await storage.getSignals();
    res.json(sigs);
  });

  app.post(api.signals.generate.path, async (_req, res) => {
    const sigs = await storage.getSignals();
    const recentNums = sigs.map(s => s.number);
    const signal = generateSignal(recentNums);
    res.json(signal);
  });

  // ─── ALERTS ──────────────────────────────────────────────────────────
  app.get(api.alerts.list.path, async (_req, res) => {
    const alertList = await storage.getAlerts();
    res.json(alertList);
  });

  // ─── REPORTS ─────────────────────────────────────────────────────────
  app.get(api.reports.get.path, async (_req, res) => {
    const report = await storage.getReport();
    res.json(report);
  });

  // ─── METRICS ─────────────────────────────────────────────────────────
  app.get(api.metrics.get.path, async (_req, res) => {
    const report = await storage.getReport();
    const winRate = calculateWinRate(report.greens, report.reds);
    res.json({
      signalsToday: report.signalsToday,
      winRate,
      currentStreak: report.currentStreak,
      lastSignalResult: report.lastSignalResult,
      totalGreens: report.greens,
      totalReds: report.reds,
      lastNumber: report.lastNumber,
    });
  });

  // ─── RADAR CONFIG ─────────────────────────────────────────────────────
  app.get(api.radar.getConfig.path, async (_req, res) => {
    const config = await storage.getRadarConfig();
    res.json(config);
  });

  app.put(api.radar.updateConfig.path, async (req, res) => {
    try {
      const input = api.radar.updateConfig.input.parse(req.body);
      const updated = await storage.updateRadarConfig(input);
      res.json(updated);
    } catch (err) {
      if (err instanceof z.ZodError)
        return res.status(400).json({ message: err.errors[0].message });
      throw err;
    }
  });

  // ─── RADAR START / STOP ────────────────────────────────────────────
  app.post(api.radar.start.path, async (_req, res) => {
    await storage.updateRadarConfig({ radarActive: true });

    // Auto-generate signals every 60s while radar is active
    if (radarInterval) clearInterval(radarInterval);
    radarInterval = setInterval(async () => {
      const cfg = await storage.getRadarConfig();
      if (!cfg.radarActive) {
        clearInterval(radarInterval!);
        radarInterval = null;
        return;
      }
      const sigs = await storage.getSignals();
      const recentNums = sigs.map(s => s.number);
      const generated = generateSignal(recentNums);

      if (generated.confidence >= cfg.confidenceThreshold) {
        const randomNum = Math.floor(Math.random() * 37);
        const randomStatus = Math.random() > 0.35 ? 'green' : 'red';
        await storage.createSignal({
          number: randomNum,
          status: randomStatus,
          confidence: generated.confidence,
          entry: generated.entry,
        });

        // Update report
        const report = await storage.getReport();
        const isWin = randomStatus === 'green';
        await storage.updateReport({
          totalSpins: report.totalSpins + 1,
          greens: isWin ? report.greens + 1 : report.greens,
          reds: isWin ? report.reds : report.reds + 1,
          lastNumber: randomNum,
          signalsToday: report.signalsToday + 1,
          currentStreak: isWin ? report.currentStreak + 1 : 0,
          lastSignalResult: isWin ? 'win' : 'loss',
        });

        // Send Telegram if configured
        if (cfg.telegramToken && cfg.chatId) {
          await sendTelegramSignal(cfg.telegramToken, cfg.chatId, generated).catch(console.error);
        }
      }
    }, 60000);

    res.json({ success: true, message: 'RADAR DO GREEN ativado com sucesso!' });
  });

  app.post(api.radar.stop.path, async (_req, res) => {
    await storage.updateRadarConfig({ radarActive: false });
    if (radarInterval) {
      clearInterval(radarInterval);
      radarInterval = null;
    }
    res.json({ success: true, message: 'Radar desativado.' });
  });

  // ─── TELEGRAM TEST ────────────────────────────────────────────────────
  app.post(api.radar.testTelegram.path, async (req, res) => {
    const { token, chatId } = req.body as { token?: string; chatId?: string };
    const cfg = await storage.getRadarConfig();
    const useToken = token || cfg.telegramToken;
    const useChatId = chatId || cfg.chatId;

    const signal = generateSignal();
    const result = await sendTelegramSignal(useToken, useChatId, signal);
    res.json(result);
  });

  // Seed initial data
  seedDatabase().catch(console.error);

  return httpServer;
}

async function seedDatabase() {
  const existingSignals = await storage.getSignals();
  if (existingSignals.length === 0) {
    await storage.createSignal({ number: 12, status: 'green', confidence: 88, entry: 'Vermelho + Zero' });
    await storage.createSignal({ number: 3,  status: 'red',   confidence: 72, entry: 'Preto + Zero' });
    await storage.createSignal({ number: 26, status: 'green', confidence: 91, entry: 'Preto + Zero' });
    await storage.createSignal({ number: 0,  status: 'green', confidence: 85, entry: 'Vermelho + Zero' });
    await storage.createSignal({ number: 32, status: 'red',   confidence: 67, entry: 'Preto + Zero' });
    await storage.createSignal({ number: 17, status: 'green', confidence: 79, entry: 'Vermelho + Zero' });
    await storage.createSignal({ number: 5,  status: 'green', confidence: 93, entry: 'Vermelho + Zero' });
  }

  const existingAlerts = await storage.getAlerts();
  if (existingAlerts.length === 0) {
    await storage.createAlert({ message: 'Sequencia de 4x pretos detectada', type: 'sequencia' });
    await storage.createAlert({ message: 'MANIPULACAO DETECTADA — 6x vermelhos seguidos', type: 'manipulacao' });
  }

  const report = await storage.getReport();
  if (report.totalSpins === 0) {
    await storage.updateReport({
      totalSpins: 247,
      greens: 163,
      reds: 84,
      lastNumber: 12,
      signalsToday: 18,
      currentStreak: 5,
      lastSignalResult: 'win',
    });
  }
}
