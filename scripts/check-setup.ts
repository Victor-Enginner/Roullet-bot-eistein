#!/usr/bin/env node

/**
 * Script de Verificação Final - Radar do Green v2.0
 * Executa verificações para garantir que tudo está funcionando
 */

import { execSync } from 'child_process';
import { readFileSync, existsSync } from 'fs';
import { join } from 'path';

console.log('🔍 VERIFICAÇÃO FINAL - Radar do Green v2.0\n');

const checks = {
  nodeVersion: false,
  typescript: false,
  envFile: false,
  databaseUrl: false,
  sessionSecret: false,
  dependencies: false,
  buildCheck: false,
  lintCheck: false
};

let passed = 0;
let total = Object.keys(checks).length;

// 1. Verificar Node.js versão
try {
  const nodeVersion = execSync('node --version', { encoding: 'utf8' }).trim();
  console.log(`✅ Node.js: ${nodeVersion}`);
  checks.nodeVersion = true;
  passed++;
} catch (error) {
  console.log('❌ Node.js não encontrado');
}

// 2. Verificar TypeScript
try {
  const tsVersion = execSync('npx tsc --version', { encoding: 'utf8' }).trim();
  console.log(`✅ TypeScript: ${tsVersion}`);
  checks.typescript = true;
  passed++;
} catch (error) {
  console.log('❌ TypeScript não configurado');
}

// 3. Verificar arquivo .env
if (existsSync('.env')) {
  console.log('✅ Arquivo .env existe');
  checks.envFile = true;
  passed++;

  // Verificar DATABASE_URL
  const envContent = readFileSync('.env', 'utf8');
  if (envContent.includes('DATABASE_URL=postgresql://')) {
    console.log('✅ DATABASE_URL configurado');
    checks.databaseUrl = true;
    passed++;
  } else {
    console.log('⚠️  DATABASE_URL não configurado corretamente');
  }

  // Verificar SESSION_SECRET
  if (envContent.includes('SESSION_SECRET=') && !envContent.includes('SESSION_SECRET=your_')) {
    console.log('✅ SESSION_SECRET configurado');
    checks.sessionSecret = true;
    passed++;
  } else {
    console.log('⚠️  SESSION_SECRET não configurado');
  }
} else {
  console.log('❌ Arquivo .env não encontrado');
}

// 4. Verificar dependências
try {
  execSync('npm list --depth=0', { stdio: 'pipe' });
  console.log('✅ Dependências instaladas');
  checks.dependencies = true;
  passed++;
} catch (error) {
  console.log('❌ Problemas com dependências');
}

// 5. Verificar build
try {
  execSync('npm run typecheck', { stdio: 'pipe' });
  console.log('✅ TypeScript compila sem erros');
  checks.buildCheck = true;
  passed++;
} catch (error) {
  console.log('⚠️  Erros de TypeScript encontrados');
  console.log('   Execute: npm run typecheck');
}

// 6. Verificar lint (se configurado)
try {
  execSync('npm run lint', { stdio: 'pipe' });
  console.log('✅ ESLint passa sem erros');
  checks.lintCheck = true;
  passed++;
} catch (error) {
  console.log('⚠️  Problemas de linting encontrados');
  console.log('   Execute: npm run lint');
}

// Resultado final
console.log('\n' + '='.repeat(50));
console.log(`📊 RESULTADO: ${passed}/${total} verificações passaram`);

if (passed === total) {
  console.log('🎉 PROJETO PRONTO PARA DESENVOLVIMENTO!');
  console.log('\n🚀 Para iniciar:');
  console.log('   npm run dev');
  console.log('   npm run demo');
} else {
  console.log('⚠️  Algumas verificações falharam.');
  console.log('\n🔧 Para corrigir:');
  console.log('   1. Configure o .env com DATABASE_URL e SESSION_SECRET');
  console.log('   2. Execute: npm install');
  console.log('   3. Execute: npm run db:push');
  console.log('   4. Execute: npm run lint');
}

console.log('\n📝 Comandos úteis:');
console.log('   npm run generate-secrets  # Gerar secrets seguros');
console.log('   npm run db:studio        # Abrir Drizzle Studio');
console.log('   npm run demo            # Executar demo completa');
console.log('   npm run test-reasoning  # Testar reasoning agent');