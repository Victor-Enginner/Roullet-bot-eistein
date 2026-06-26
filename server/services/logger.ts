/**
 * Logger Service - Observabilidade para decisões agentic
 * Registra todas as ações, decisões e resultados dos agentes
 */

interface LogEntry {
  timestamp: string;
  level: 'INFO' | 'WARN' | 'ERROR' | 'DEBUG';
  component: string;
  message: string;
  data?: any;
  signalId?: string;
}

export class LoggerService {
  private logs: LogEntry[] = [];
  private maxLogs = 1000;

  log(level: LogEntry['level'], component: string, message: string, data?: any, signalId?: string): void {
    const entry: LogEntry = {
      timestamp: new Date().toISOString(),
      level,
      component,
      message,
      data,
      signalId
    };

    this.logs.push(entry);

    // Mantém apenas os logs mais recentes
    if (this.logs.length > this.maxLogs) {
      this.logs = this.logs.slice(-this.maxLogs);
    }

    // Output para console (pode ser configurado para arquivo/banco)
    const logMessage = `[${entry.timestamp}] ${level} [${component}] ${message}`;
    console.log(logMessage, data ? JSON.stringify(data, null, 2) : '');
  }

  info(component: string, message: string, data?: any, signalId?: string): void {
    this.log('INFO', component, message, data, signalId);
  }

  warn(component: string, message: string, data?: any, signalId?: string): void {
    this.log('WARN', component, message, data, signalId);
  }

  error(component: string, message: string, data?: any, signalId?: string): void {
    this.log('ERROR', component, message, data, signalId);
  }

  debug(component: string, message: string, data?: any, signalId?: string): void {
    this.log('DEBUG', component, message, data, signalId);
  }

  getLogs(component?: string, signalId?: string, limit = 100): LogEntry[] {
    let filtered = this.logs;

    if (component) {
      filtered = filtered.filter(log => log.component === component);
    }

    if (signalId) {
      filtered = filtered.filter(log => log.signalId === signalId);
    }

    return filtered.slice(-limit);
  }

  getRecentLogs(minutes = 60): LogEntry[] {
    const cutoff = new Date(Date.now() - minutes * 60 * 1000);

    return this.logs.filter(log => new Date(log.timestamp) > cutoff);
  }

  getStats(): any {
    const total = this.logs.length;
    const byLevel = this.logs.reduce((acc, log) => {
      acc[log.level] = (acc[log.level] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);

    const byComponent = this.logs.reduce((acc, log) => {
      acc[log.component] = (acc[log.component] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);

    const errors = this.logs.filter(log => log.level === 'ERROR');

    return {
      total,
      byLevel,
      byComponent,
      recentErrors: errors.slice(-10),
      uptime: this.calculateUptime()
    };
  }

  private calculateUptime(): string {
    if (this.logs.length === 0) return '0s';

    const firstLog = new Date(this.logs[0].timestamp);
    const lastLog = new Date(this.logs[this.logs.length - 1].timestamp);
    const uptimeMs = lastLog.getTime() - firstLog.getTime();

    const hours = Math.floor(uptimeMs / (1000 * 60 * 60));
    const minutes = Math.floor((uptimeMs % (1000 * 60 * 60)) / (1000 * 60));
    const seconds = Math.floor((uptimeMs % (1000 * 60)) / 1000);

    return `${hours}h ${minutes}m ${seconds}s`;
  }

  clear(): void {
    this.logs = [];
  }

  exportLogs(): string {
    return JSON.stringify(this.logs, null, 2);
  }
}