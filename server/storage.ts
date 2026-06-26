import { db, withRetry } from "./db.js";
import {
  users, signals, alerts, reports, radarConfig,
  type User, type CreateUserRequest, type UpdateUserRequest,
  type Signal, type Alert, type Report, type RadarConfig, type UpdateRadarConfigRequest
} from "@shared/schema.js";
import { eq, desc } from "drizzle-orm";

export interface IStorage {
  getUser(id: number): Promise<User | undefined>;
  getUserByEmail(email: string): Promise<User | undefined>;
  createUser(user: CreateUserRequest): Promise<User>;
  updateUser(id: number, updates: UpdateUserRequest): Promise<User>;

  getSignals(): Promise<Signal[]>;
  createSignal(signal: Omit<Signal, "id" | "timestamp">): Promise<Signal>;

  getAlerts(): Promise<Alert[]>;
  createAlert(alert: Omit<Alert, "id" | "timestamp">): Promise<Alert>;

  getReport(): Promise<Report>;
  updateReport(updates: Partial<Report>): Promise<Report>;

  getRadarConfig(): Promise<RadarConfig>;
  updateRadarConfig(updates: UpdateRadarConfigRequest): Promise<RadarConfig>;
}

export class DatabaseStorage implements IStorage {
  async getUser(id: number): Promise<User | undefined> {
    return withRetry(async () => {
      const [user] = await db.select().from(users).where(eq(users.id, id));
      return user;
    });
  }

  async getUserByEmail(email: string): Promise<User | undefined> {
    return withRetry(async () => {
      const [user] = await db.select().from(users).where(eq(users.email, email));
      return user;
    });
  }

  async createUser(insertUser: CreateUserRequest): Promise<User> {
    return withRetry(async () => {
      const [user] = await db.insert(users).values(insertUser).returning();
      return user;
    });
  }

  async updateUser(id: number, updates: UpdateUserRequest): Promise<User> {
    return withRetry(async () => {
      const [updated] = await db.update(users).set(updates).where(eq(users.id, id)).returning();
      return updated;
    });
  }

  async getSignals(): Promise<Signal[]> {
    return withRetry(async () => {
      return db.select().from(signals).orderBy(desc(signals.timestamp)).limit(20);
    });
  }

  async createSignal(signal: Omit<Signal, "id" | "timestamp">): Promise<Signal> {
    return withRetry(async () => {
      const [created] = await db.insert(signals).values(signal).returning();
      return created;
    });
  }

  async getAlerts(): Promise<Alert[]> {
    return withRetry(async () => {
      return db.select().from(alerts).orderBy(desc(alerts.timestamp));
    });
  }

  async createAlert(alert: Omit<Alert, "id" | "timestamp">): Promise<Alert> {
    return withRetry(async () => {
      const [created] = await db.insert(alerts).values(alert).returning();
      return created;
    });
  }

  async getReport(): Promise<Report> {
    return withRetry(async () => {
      const [report] = await db.select().from(reports).limit(1);
      if (!report) {
        const [newReport] = await db.insert(reports).values({
          totalSpins: 0,
          greens: 0,
          reds: 0,
          lastNumber: 0,
          signalsToday: 0,
          currentStreak: 0,
          lastSignalResult: 'none',
        }).returning();
        return newReport;
      }
      return report;
    });
  }

  async updateReport(updates: Partial<Report>): Promise<Report> {
    const report = await this.getReport();
    return withRetry(async () => {
      const [updated] = await db.update(reports)
        .set({ ...updates, updatedAt: new Date() })
        .where(eq(reports.id, report.id))
        .returning();
      return updated;
    });
  }

  async getRadarConfig(): Promise<RadarConfig> {
    return withRetry(async () => {
      const [config] = await db.select().from(radarConfig).limit(1);
      if (!config) {
        const [newConfig] = await db.insert(radarConfig).values({
          telegramToken: '',
          chatId: '',
          signalMode: 'auto',
          confidenceThreshold: 70,
          voiceAlerts: true,
          radarActive: false,
        }).returning();
        return newConfig;
      }
      return config;
    });
  }

  async updateRadarConfig(updates: UpdateRadarConfigRequest): Promise<RadarConfig> {
    const config = await this.getRadarConfig();
    return withRetry(async () => {
      const [updated] = await db.update(radarConfig)
        .set({ ...updates, updatedAt: new Date() })
        .where(eq(radarConfig.id, config.id))
        .returning();
      return updated;
    });
  }
}

export const storage = new DatabaseStorage();
