import { z } from 'zod';
import { insertUserSchema, users, signals, alerts, reports, radarConfig, insertRadarConfigSchema } from './schema.js';

export const errorSchemas = {
  validation: z.object({
    message: z.string(),
    field: z.string().optional(),
  }),
  notFound: z.object({
    message: z.string(),
  }),
  internal: z.object({
    message: z.string(),
  }),
  unauthorized: z.object({
    message: z.string(),
  })
};

export const api = {
  health: {
    get: {
      method: 'GET' as const,
      path: '/api/health' as const,
      responses: {
        200: z.object({
          status: z.string(),
          system: z.string(),
          version: z.string(),
          radarActive: z.boolean(),
          timestamp: z.string(),
        }),
      },
    }
  },
  auth: {
    login: {
      method: 'POST' as const,
      path: '/api/auth/login' as const,
      input: z.object({
        email: z.string().email(),
        password: z.string(),
      }),
      responses: {
        200: z.custom<typeof users.$inferSelect>(),
        401: errorSchemas.unauthorized,
      },
    },
    register: {
      method: 'POST' as const,
      path: '/api/auth/register' as const,
      input: z.object({
        email: z.string().email(),
        password: z.string(),
        name: z.string(),
      }),
      responses: {
        201: z.custom<typeof users.$inferSelect>(),
        400: errorSchemas.validation,
      },
    },
    me: {
      method: 'GET' as const,
      path: '/api/auth/me' as const,
      responses: {
        200: z.custom<typeof users.$inferSelect>(),
        401: errorSchemas.unauthorized,
      },
    },
    logout: {
      method: 'POST' as const,
      path: '/api/auth/logout' as const,
      responses: {
        200: z.object({ success: z.boolean() }),
      }
    }
  },
  users: {
    update: {
      method: 'PUT' as const,
      path: '/api/users/:id' as const,
      input: insertUserSchema.partial(),
      responses: {
        200: z.custom<typeof users.$inferSelect>(),
        400: errorSchemas.validation,
        404: errorSchemas.notFound,
      },
    }
  },
  signals: {
    list: {
      method: 'GET' as const,
      path: '/api/sinais' as const,
      responses: {
        200: z.array(z.custom<typeof signals.$inferSelect>()),
      },
    },
    generate: {
      method: 'POST' as const,
      path: '/api/sinais/generate' as const,
      responses: {
        200: z.object({
          entry: z.string(),
          targetColor: z.string(),
          confidence: z.number(),
          protection: z.string(),
          countdown: z.number(),
          timestamp: z.string(),
        }),
      },
    }
  },
  alerts: {
    list: {
      method: 'GET' as const,
      path: '/api/alertas' as const,
      responses: {
        200: z.array(z.custom<typeof alerts.$inferSelect>()),
      },
    }
  },
  reports: {
    get: {
      method: 'GET' as const,
      path: '/api/relatorio' as const,
      responses: {
        200: z.custom<typeof reports.$inferSelect>(),
        404: errorSchemas.notFound,
      },
    }
  },
  radar: {
    getConfig: {
      method: 'GET' as const,
      path: '/api/radar/config' as const,
      responses: {
        200: z.custom<typeof radarConfig.$inferSelect>(),
      },
    },
    updateConfig: {
      method: 'PUT' as const,
      path: '/api/radar/config' as const,
      input: insertRadarConfigSchema.partial(),
      responses: {
        200: z.custom<typeof radarConfig.$inferSelect>(),
      },
    },
    start: {
      method: 'POST' as const,
      path: '/api/radar/start' as const,
      responses: {
        200: z.object({ success: z.boolean(), message: z.string() }),
      },
    },
    stop: {
      method: 'POST' as const,
      path: '/api/radar/stop' as const,
      responses: {
        200: z.object({ success: z.boolean(), message: z.string() }),
      },
    },
    testTelegram: {
      method: 'POST' as const,
      path: '/api/radar/telegram/test' as const,
      responses: {
        200: z.object({ success: z.boolean(), message: z.string() }),
      },
    }
  },
  metrics: {
    get: {
      method: 'GET' as const,
      path: '/api/metrics' as const,
      responses: {
        200: z.object({
          signalsToday: z.number(),
          winRate: z.number(),
          currentStreak: z.number(),
          lastSignalResult: z.string(),
          totalGreens: z.number(),
          totalReds: z.number(),
          lastNumber: z.number(),
        }),
      },
    }
  }
};

export function buildUrl(path: string, params?: Record<string, string | number>): string {
  let url = path;
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (url.includes(`:${key}`)) {
        url = url.replace(`:${key}`, String(value));
      }
    });
  }
  return url;
}
