#!/usr/bin/env node

/**
 * Script para gerar secrets seguros para o projeto
 */

import { randomBytes } from 'crypto';

function generateSecret(length = 32) {
  return randomBytes(length).toString('hex');
}

function generateJWT(length = 64) {
  return randomBytes(length).toString('hex');
}

console.log('🔐 GERANDO SECRETS PARA RADAR DO GREEN v2.0\n');

console.log('SESSION_SECRET=' + generateSecret(32));
console.log('JWT_SECRET=' + generateJWT(64));

console.log('\n📋 COPIE E COLE NO SEU ARQUIVO .env');
console.log('⚠️  NUNCA COMPARTILHE ESTES VALORES PUBLICAMENTE!');