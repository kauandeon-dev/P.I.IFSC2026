/* Sentinela — painel web (JavaScript puro, sem build). */
(function () {
  'use strict';

  // ------------------------------------------------------------------ ícones
  const I = {
    shield: (s = 19, w = 2.2) => `<svg width="${s}" height="${s}" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="${w}" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3l7 3v5c0 4.4-3 8-7 10-4-2-7-5.6-7-10V6z"/><path d="M9 12l2 2 4-4"/></svg>`,
    check: (c = '#6fa8ff', s = 14) => `<svg width="${s}" height="${s}" viewBox="0 0 24 24" fill="none" stroke="${c}" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12l5 5 9-11"/></svg>`,
    grid: '<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9"><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/></svg>',
    cal: '<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"><rect x="3" y="4" width="18" height="17" rx="2"/><line x1="3" y1="9" x2="21" y2="9"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="16" y1="2" x2="16" y2="6"/></svg>',
    clock: '<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"><circle cx="12" cy="12" r="9"/><line x1="12" y1="7" x2="12" y2="12"/><line x1="12" y1="12" x2="16" y2="14"/></svg>',
    doc: '<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"><rect x="4" y="3" width="16" height="18" rx="2"/><line x1="8" y1="8" x2="16" y2="8"/><line x1="8" y1="12" x2="16" y2="12"/><line x1="8" y1="16" x2="13" y2="16"/></svg>',
    db: '<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"><ellipse cx="12" cy="6" rx="8" ry="3"/><path d="M4 6v12c0 1.66 3.58 3 8 3s8-1.34 8-3V6"/><path d="M4 12c0 1.66 3.58 3 8 3s8-1.34 8-3"/></svg>',
    logout: '<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M15 4h3a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2h-3"/><path d="M10 17l-5-5 5-5"/><line x1="5" y1="12" x2="16" y2="12"/></svg>',
    refresh: (c = '#fff') => `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="${c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12a9 9 0 1 1-3-6.7"/><path d="M21 4v4h-4"/></svg>`,
    restore: '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12a9 9 0 1 0 3-6.7"/><path d="M3 4v4h4"/></svg>',
    download: '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3v13"/><path d="M7 12l5 5 5-5"/><line x1="5" y1="21" x2="19" y2="21"/></svg>',
    trash: '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 7h16"/><path d="M9 7V4h6v3"/><path d="M6 7l1 13h10l1-13"/></svg>',
    verify: '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3l7 3v5c0 4.4-3 8-7 10-4-2-7-5.6-7-10V6z"/><path d="M9 12l2 2 4-4"/></svg>',
    warn: (c = '#b7791f', s = 18) => `<svg width="${s}" height="${s}" viewBox="0 0 24 24" fill="none" stroke="${c}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3l10 17H2z"/><line x1="12" y1="10" x2="12" y2="14"/><line x1="12" y1="17" x2="12" y2="17"/></svg>`,
    back: '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 6l-6 6 6 6"/></svg>',
    spinner: (s = 15) => `<svg class="spin" width="${s}" height="${s}" viewBox="0 0 24 24" fill="none" stroke="#1e6ae1" stroke-width="2.4" stroke-linecap="round"><path d="M12 3a9 9 0 1 0 9 9"/></svg>`,
    x: '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#d64545" stroke-width="2.6" stroke-linecap="round"><path d="M6 6l12 12M18 6L6 18"/></svg>',
  };

  // --------------------------------------------------------------- utilidades
  const esc = (v) => String(v ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const MESES = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez'];
  const parse = (s) => (s ? new Date(s.replace(' ', 'T')) : null);
  const pad = (n) => String(n).padStart(2, '0');
  const num = (v, d = 1) => v.toFixed(d).replace('.', ',');

  function fmtWhen(s) {
    const d = parse(s); if (!d) return '—';
    return `${pad(d.getDate())} ${MESES[d.getMonth()]} ${d.getFullYear()} · ${pad(d.getHours())}:${pad(d.getMinutes())}`;
  }
  function fmtDay(s) {
    const d = parse(s); if (!d) return '—';
    return `${pad(d.getDate())} ${MESES[d.getMonth()]} ${d.getFullYear()}`;
  }
  function fmtSize(n) {
    if (n == null) return '—';
    const u = ['B', 'KB', 'MB', 'GB', 'TB']; let i = 0; n = +n;
    while (n >= 1024 && i < u.length - 1) { n /= 1024; i++; }
    return i === 0 ? `${n} B` : `${num(n)} ${u[i]}`;
  }
  function fmtDur(s) {
    if (s == null) return '—';
    if (s < 60) return s < 0.5 ? `${num(s)}s` : `${Math.round(s)}s`;
    const m = Math.floor(s / 60); return `${m}min ${pad(Math.round(s % 60))}s`;
  }
  function relPast(s) {
    const d = parse(s); if (!d) return '';
    const m = Math.round((Date.now() - d) / 60000);
    if (m < 1) return 'agora mesmo';
    if (m < 60) return `há ${m} min`;
    const h = Math.round(m / 60);
    if (h < 48) return `há ${h}h`;
    return `há ${Math.round(h / 24)} dias`;
  }
  function relFuture(s) {
    const d = parse(s); if (!d) return '';
    const m = Math.round((d - Date.now()) / 60000);
    if (m <= 0) return 'em instantes';
    if (m < 60) return `em ~${m} min`;
    const h = Math.round(m / 60);
    if (h < 48) return `em ~${h} ${h === 1 ? 'hora' : 'horas'}`;
    return `em ~${Math.round(h / 24)} dias`;
  }
  function dayLabel(s) {
    const d = parse(s); if (!d) return '—';
    const today = new Date(); today.setHours(0, 0, 0, 0);
    const that = new Date(d); that.setHours(0, 0, 0, 0);
    const diff = Math.round((that - today) / 86400000);
    const hm = `${pad(d.getHours())}:${pad(d.getMinutes())}`;
    if (diff === 0) return `Hoje, ${hm}`;
    if (diff === 1) return `Amanhã, ${hm}`;
    return `${pad(d.getDate())} ${MESES[d.getMonth()]}, ${hm}`;
  }
  const TYPE = { auto: 'Automático', manual: 'Manual', 'pre-restore': 'Pré-restauração' };
  const KIND = { backup: 'Backup', restore: 'Restauração', verify: 'Verificação' };
  const PILL = { success: 'Concluído', error: 'Falhou', running: 'Em execução' };
  const pill = (st) => `<span class="pill ${esc(st)}"><i></i>${PILL[st] || esc(st)}</span>`;
  const time = (s) => (s || '').slice(11, 19);

  // ---------------------------------------------------------------------- API
  async function api(method, url, data) {
    const opt = { method, headers: {}, credentials: 'same-origin' };
    if (data !== undefined) { opt.headers['Content-Type'] = 'application/json'; opt.body = JSON.stringify(data); }
    const r = await fetch(url, opt);
    let body = {};
    try { body = await r.json(); } catch (e) { /* sem corpo */ }
    if (r.status === 401 && url !== '/api/login') { S.user = null; go('login'); throw new Error(body.error || 'Sessão expirada'); }
    if (!r.ok) throw new Error(body.error || `Erro ${r.status}`);
    return body;
  }

  // -------------------------------------------------------------------- estado
  const S = {
    user: null, route: 'login', param: null, data: null,
    backups: null, filter: 'all', detail: null, logs: null,
    policyDraft: null, connDraft: null, test: { status: 'idle' },
    busy: {}, loginErr: '',
  };
  const app = document.getElementById('app');
  const modalRoot = document.getElementById('modal-root');
  const toastRoot = document.getElementById('toast-root');
  let toastTimer = null, pollTimer = null;

  function toast(msg, err) {
    toastRoot.innerHTML = `<div class="toast${err ? ' err' : ''}">${err ? I.warn('#ffb4b4', 16) : I.check('#5cd08a', 16)}<span>${esc(msg)}</span></div>`;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { toastRoot.innerHTML = ''; }, err ? 5000 : 2600);
  }

  // ------------------------------------------------------------------ roteador
  const ROUTES = { painel: 'dashboard', politica: 'policy', historico: 'history', backup: 'detail', logs: 'logs', conexao: 'conn', login: 'login' };
  const PATH = { dashboard: 'painel', policy: 'politica', history: 'historico', detail: 'backup', logs: 'logs', conn: 'conexao', login: 'login' };

  function go(route, param) {
    const h = '#/' + PATH[route] + (param ? '/' + encodeURIComponent(param) : '');
    if (location.hash !== h) location.hash = h; else onRoute();
  }

  async function onRoute() {
    const parts = location.hash.replace(/^#\/?/, '').split('/');
    let route = ROUTES[parts[0]] || 'dashboard';
    const param = parts[1] ? decodeURIComponent(parts[1]) : null;
    if (!S.user && route !== 'login') route = 'login';
    if (S.user && route === 'login') route = 'dashboard';
    S.route = route; S.param = param;
    if (route === 'policy') S.policyDraft = null;
    if (route === 'conn') { S.connDraft = null; S.test = { status: 'idle' }; }
    render();
    await load();
    render();
    schedulePoll();
  }

  async function load() {
    if (S.route === 'login') return;
    try {
      const tasks = [api('GET', '/api/state').then((d) => { S.data = d; })];
      if (S.route === 'history') tasks.push(api('GET', '/api/backups?filter=' + S.filter).then((d) => { S.backups = d.backups; }));
      if (S.route === 'detail') tasks.push(api('GET', '/api/backups/' + encodeURIComponent(S.param)).then((d) => { S.detail = d; }).catch((e) => { S.detail = { error: e.message }; }));
      if (S.route === 'logs') tasks.push(api('GET', '/api/logs?limit=30').then((d) => { S.logs = d.executions; }));
      await Promise.all(tasks);
      if (S.route === 'policy' && !S.policyDraft) S.policyDraft = Object.assign({}, S.data.policy);
      if (S.route === 'conn' && !S.connDraft) S.connDraft = newConnDraft(S.data.connection, S.data.policy.directory);
    } catch (e) {
      if (S.user) toast(e.message, true);
    }
  }

  // Atualiza periodicamente as telas de leitura (mais rápido se algo estiver rodando).
  function schedulePoll() {
    clearTimeout(pollTimer);
    if (!S.user || ['policy', 'conn', 'login'].includes(S.route)) return;
    const running = S.data && S.data.running;
    pollTimer = setTimeout(async () => {
      if (modalRoot.innerHTML) { schedulePoll(); return; }
      const wasRunning = running;
      await load();
      render();
      if (wasRunning && S.data && !S.data.running) notifyFinished();
      schedulePoll();
    }, running ? 2000 : 15000);
  }

  function notifyFinished() {
    const last = S.data.recent && S.data.recent[0];
    if (!last) return;
    if (last.status === 'success') toast('Backup concluído · ' + fmtSize(last.size));
    else if (last.status === 'error') toast('Backup falhou — veja os logs', true);
  }

  // -------------------------------------------------------------------- render
  function render() {
    if (S.route === 'login') { app.innerHTML = viewLogin(); bindLogin(); return; }
    const body = !S.data ? `<div class="loading">${I.spinner(18)} Carregando…</div>` : ({
      dashboard: viewDashboard, policy: viewPolicy, history: viewHistory,
      detail: viewDetail, logs: viewLogs, conn: viewConn,
    }[S.route])();
    const main = document.querySelector('.main');
    const scroll = main ? main.scrollTop : 0;
    app.innerHTML = viewShell(body);
    const m2 = document.querySelector('.main'); if (m2) m2.scrollTop = scroll;
    document.querySelectorAll('[data-w]').forEach((el) => { el.style.width = el.dataset.w + '%'; });
  }

  // ---------------------------------------------------------------- login
  function viewLogin() {
    const feat = (t) => `<div class="feat"><span>${I.check()}</span>${t}</div>`;
    return `<div class="login">
      <div class="login-side">
        <div class="brand"><span class="brand-logo">${I.shield(24)}</span>
          <div><div class="brand-name">Sentinela</div><div class="brand-sub">backup · segurança · rastreabilidade</div></div></div>
        <div class="login-pitch">
          <h2>Proteção automatizada de bancos de dados para pequenas empresas.</h2>
          ${feat('Agendamento automático diário ou por intervalo')}
          ${feat('Criptografia AES-256 e compressão gzip')}
          ${feat('Armazenamento isolado seguindo a regra 3-2-1')}
        </div>
        <div class="login-foot">Projeto Integrador · IFSC São Lourenço do Oeste · Open source</div>
      </div>
      <div class="login-main">
        <form class="login-form" id="login-form" autocomplete="on">
          <h1>Entrar</h1>
          <p>Acesse o painel de backup do servidor.</p>
          ${S.loginErr ? `<div class="login-err">${esc(S.loginErr)}</div>` : ''}
          <label class="lbl" for="lu">Usuário</label>
          <input class="input mb18" id="lu" name="username" autocomplete="username" required autofocus>
          <label class="lbl" for="lp">Senha</label>
          <input class="input mb24" id="lp" name="password" type="password" autocomplete="current-password" required>
          <button class="btn btn-primary btn-block" type="submit" ${S.busy.login ? 'disabled' : ''}>${S.busy.login ? 'Entrando…' : 'Entrar no painel'}</button>
        </form>
      </div>
    </div>`;
  }

  function bindLogin() {
    const f = document.getElementById('login-form');
    f.addEventListener('submit', async (ev) => {
      ev.preventDefault();
      const username = f.username.value, password = f.password.value;
      S.busy.login = true; S.loginErr = ''; render();
      try {
        const r = await api('POST', '/api/login', { username, password });
        S.user = r.user; S.busy.login = false; S.data = null;
        go('dashboard');
      } catch (e) {
        S.busy.login = false; S.loginErr = e.message; render();
        const u = document.getElementById('lu'); u.value = username;
        document.getElementById('lp').focus();
      }
    });
  }

  // ---------------------------------------------------------------- shell
  function viewShell(body) {
    const nav = (r, icon, label) => {
      const active = S.route === r || (r === 'history' && S.route === 'detail');
      return `<a href="#/${PATH[r]}" class="${active ? 'active' : ''}">${icon}${label}</a>`;
    };
    const d = S.data;
    let dbState = '<span class="dot y"></span>Não configurado';
    if (d) {
      const cs = d.conn_status, label = d.connection.sgbd_label.replace(' (MySQL)', '');
      if (d.running) dbState = `<span class="dot b"></span>${esc(label)} · em execução`;
      else if (!d.active) dbState = '<span class="dot y"></span>Conexão pendente';
      else if (cs && cs.ok) dbState = `<span class="dot g"></span>${esc(label)} · conectado`;
      else if (cs && !cs.ok) dbState = `<span class="dot r"></span>${esc(label)} · falha`;
      else dbState = `<span class="dot y"></span>${esc(label)} · não testado`;
    }
    const u = S.user || '';
    return `<div class="shell">
      <aside class="sidebar">
        <div class="side-brand"><span class="logo">${I.shield()}</span>
          <div><div class="name">Sentinela</div><div class="ver">v${esc(d ? d.version : '')} · beta</div></div></div>
        <div class="side-sec">PRINCIPAL</div>
        <nav class="nav">
          ${nav('dashboard', I.grid, 'Painel')}
          ${nav('policy', I.cal, 'Política de backup')}
          ${nav('history', I.clock, 'Histórico')}
          ${nav('logs', I.doc, 'Logs')}
          ${nav('conn', I.db, 'Conexão')}
        </nav>
        <div class="side-bottom">
          <div class="dbbox"><div class="t">BANCO DE DADOS</div><div class="v">${dbState}</div></div>
          <div class="me"><span class="avatar">${esc(u.slice(0, 1))}</span>
            <div style="flex:1;min-width:0"><div class="n">${esc(u)}</div><div class="r">administrador</div></div>
            <button class="iconbtn" data-action="logout" title="Sair">${I.logout}</button></div>
        </div>
      </aside>
      <main class="main"><div class="content">${body}</div></main>
    </div>`;
  }

  const runBtn = () => `<button class="btn btn-primary" data-action="run" ${S.busy.run || (S.data && S.data.running) ? 'disabled' : ''}>${S.data && S.data.running ? I.spinner() + 'Em execução…' : I.refresh() + 'Fazer backup agora'}</button>`;

  // -------------------------------------------------------------- dashboard
  function viewDashboard() {
    const d = S.data, p = d.policy;
    const last = d.last_backup;
    const st = d.storage;
    const pct = Math.min(100, Math.round((st.copies / st.expected) * 100));
    const sched = p.schedule_mode === 'daily' ? 'Diário · 00:00' : `A cada ${p.interval_days} dias`;
    const copies = `${st.copies} de ${st.expected} ${st.expected === 1 ? 'cópia' : 'cópias'}`;

    let alert = '';
    if (!d.active) {
      alert = `<div class="alert info">${I.db.replace('currentColor', '#1e6ae1')}<span>Configure a conexão com o banco de dados para ativar os backups automáticos.</span><a href="#/conexao">Configurar →</a></div>`;
    } else if (d.failures.count) {
      const f = d.failures.last;
      alert = `<div class="alert">${I.warn()}<span>${d.failures.count} ${d.failures.count === 1 ? 'backup falhou' : 'backups falharam'} — o mais recente em <strong>${fmtDay(f.created_at)}</strong>: ${esc(shortErr(f.error))}</span><a href="#/backup/${esc(f.id)}">Ver logs →</a></div>`;
    }

    const rows = d.recent.length ? d.recent.map((b) => `
      <div class="row" data-open="${esc(b.id)}">
        <span class="r-date">${fmtWhen(b.created_at)}</span>
        <span class="r-type">${TYPE[b.trigger] || esc(b.trigger)}</span>
        <span class="r-size">${fmtSize(b.size)}</span>
        ${pill(b.status)}
      </div>`).join('') : '<div class="empty">Nenhum backup realizado ainda.</div>';

    const disk = st.disk ? ` · ${fmtSize(st.disk.free)} livres` : '';
    return `
      <div class="page-head"><div><h1>Painel</h1><p>Visão geral do sistema de backup.</p></div>${runBtn()}</div>
      <div class="stats">
        <div class="card pad stat"><div class="k">Status</div>
          <div class="v"><span class="dot ${d.running ? 'b' : d.active ? 'g' : 'y'}"></span>${d.running ? 'Executando' : d.active ? 'Ativo' : 'Inativo'}</div>
          <div class="s">${d.active ? 'Agendamento habilitado' : 'Aguardando configuração'}</div></div>
        <div class="card pad stat"><div class="k">Próximo backup</div>
          <div class="v">${d.active && d.next_run_at ? dayLabel(d.next_run_at) : '—'}</div>
          <div class="s">${d.active && d.next_run_at ? relFuture(d.next_run_at) : 'sem agendamento ativo'}</div></div>
        <div class="card pad stat"><div class="k">Último backup</div>
          <div class="v">${last ? (last.status === 'success' ? 'Concluído' : 'Falhou') : '—'}</div>
          <div class="s">${last ? relPast(last.created_at) + (last.status === 'success' ? ' · ' + fmtSize(last.size) : '') : 'nenhuma execução'}</div></div>
        <div class="card pad stat"><div class="k">Retenção</div>
          <div class="v">${p.retention_days} ${p.retention_days === 1 ? 'dia' : 'dias'}</div>
          <div class="s">${copies}</div></div>
      </div>
      ${alert}
      <div class="grid-dash">
        <div class="card">
          <div class="card-head"><span class="card-title">Backups recentes</span><a href="#/historico" style="font-size:12.5px;font-weight:600">Ver tudo →</a></div>
          ${rows}
        </div>
        <div class="col">
          <div class="card pad">
            <div class="card-title" style="margin-bottom:14px">Armazenamento</div>
            <div class="bar"><div data-w="${pct}"></div></div>
            <div class="kv" style="margin-top:10px"><span>${copies}</span><span class="mono">${fmtSize(st.bytes)}</span></div>
            <div class="hint mono" style="word-break:break-all">${esc(st.directory)}${esc(disk)}</div>
          </div>
          <div class="card pad">
            <div class="card-title" style="margin-bottom:14px">Configuração atual</div>
            <div class="col" style="gap:11px">
              <div class="kv"><span>SGBD</span><span>${esc(d.connection.sgbd_label)}</span></div>
              <div class="kv"><span>Banco</span><span class="mono">${esc(d.connection.dbname || '—')}</span></div>
              <div class="kv"><span>Acesso</span><span>${d.connection.ssh && d.connection.ssh.enabled ? 'Túnel SSH · ' + esc(d.connection.ssh.host) : 'Direto'}</span></div>
              <div class="kv"><span>Agendamento</span><span>${sched}</span></div>
              <div class="kv"><span>Criptografia</span><span>${p.encryption ? 'AES-256 · ativa' : 'Desativada'}</span></div>
              <div class="kv"><span>Compressão</span><span>${p.compression ? 'gzip · ativa' : 'Desativada'}</span></div>
            </div>
          </div>
        </div>
      </div>`;
  }

  function shortErr(e) {
    e = (e || 'erro desconhecido').replace(/^Falha na conexão com o banco: /, 'conexão recusada — ');
    return e.length > 110 ? e.slice(0, 110) + '…' : e;
  }

  // ------------------------------------------------------------------ política
  function viewPolicy() {
    const p = S.policyDraft || S.data.policy;
    const L = S.data.limits;
    const seg = (on, act, label) => `<div class="${on ? 'on' : ''}" data-action="${act}">${label}</div>`;
    return `<div class="narrow">
      <div class="page-head"><div><h1>Política de backup</h1><p>Defina como, quando e por quanto tempo as cópias são feitas.</p></div></div>

      <div class="card pad-lg mb16">
        <div class="card-title">Banco de dados</div>
        <div class="card-sub">SGBD em uso: <strong>${esc(S.data.connection.sgbd_label)}</strong>${S.data.connection.dbname ? ` · banco <span class="mono">${esc(S.data.connection.dbname)}</span>` : ''}. Altere na tela <a href="#/conexao">Conexão</a>.</div>
      </div>

      <div class="card pad-lg mb16">
        <div class="card-title">Agendamento</div>
        <div class="card-sub">Automação elimina a dependência de intervenção manual.</div>
        <div class="seg">${seg(p.schedule_mode === 'daily', 'pol-daily', 'Diário à meia-noite')}${seg(p.schedule_mode === 'custom', 'pol-custom', 'Intervalo personalizado')}</div>
        ${p.schedule_mode === 'custom' ? `<div class="inline">Executar a cada <input class="num" type="number" id="pol-interval" min="${L.interval[0]}" max="${L.interval[1]}" value="${esc(p.interval_days)}"> dias, à meia-noite</div>` : ''}
      </div>

      <div class="card pad-lg mb16">
        <div class="card-title">Retenção</div>
        <div class="card-sub" style="margin-bottom:18px">Por quantos dias cada cópia é mantida antes de ser excluída automaticamente.</div>
        <div class="range-row">
          <input type="range" id="pol-retention" min="${L.retention[0]}" max="${L.retention[1]}" value="${esc(p.retention_days)}">
          <div class="range-val"><b id="ret-val">${esc(p.retention_days)}</b><span>dias</span></div>
        </div>
        <div class="hint">Mínimo: ${L.retention[0]} dia · máximo: ${L.retention[1]} dias. A cópia válida mais recente nunca é excluída.</div>
      </div>

      <div class="card pad-lg mb16">
        <div class="card-title">Diretório de armazenamento</div>
        <div class="card-sub">Pasta isolada da aplicação. Aponte para um volume externo ou remoto para atender à regra 3-2-1.</div>
        <input class="input mono" id="pol-dir" value="${esc(p.directory)}" spellcheck="false">
      </div>

      <div class="card pad-lg mb22">
        <div class="card-title" style="margin-bottom:16px">Segurança das cópias</div>
        <div class="toggle-row"><div><div class="t">Criptografia (AES-256)</div><div class="d">Protege o conteúdo mesmo se a cópia for interceptada.</div></div>
          <button class="toggle ${p.encryption ? 'on' : ''}" data-action="pol-enc" aria-label="Criptografia"><span></span></button></div>
        <div class="toggle-row"><div><div class="t">Compressão (gzip)</div><div class="d">Reduz o espaço ocupado em disco pelas cópias diárias.</div></div>
          <button class="toggle ${p.compression ? 'on' : ''}" data-action="pol-comp" aria-label="Compressão"><span></span></button></div>
        ${p.encryption ? `<div class="warn-note">A chave de criptografia fica em <code>${esc(S.data.key_path)}</code>. Guarde uma cópia dela fora do servidor: sem a chave, as cópias não podem ser recuperadas.</div>` : ''}
      </div>

      <div class="actions">
        <button class="btn btn-primary btn-lg" data-action="pol-save" ${S.busy.pol ? 'disabled' : ''}>${S.busy.pol ? 'Salvando…' : 'Salvar política'}</button>
        <a class="btn btn-ghost btn-lg" href="#/painel">Cancelar</a>
      </div>
    </div>`;
  }

  // -------------------------------------------------------------- histórico
  function viewHistory() {
    const list = S.backups;
    const tab = (f, label) => `<div class="${S.filter === f ? 'on' : ''}" data-filter="${f}">${label}</div>`;
    const rows = !list ? `<div class="empty">${I.spinner()} </div>` : list.length ? list.map((b) => `
      <div class="row" data-open="${esc(b.id)}">
        <span class="c-date">${fmtWhen(b.created_at)}</span>
        <span class="c-type">${TYPE[b.trigger] || esc(b.trigger)}</span>
        <span class="c-db">${esc(b.dbname)} <small>· ${esc(b.sgbd_label.replace(' (MySQL)', ''))}</small></span>
        <span class="c-size">${fmtSize(b.size)}</span>
        <span class="c-dur">${fmtDur(b.duration)}</span>
        <span class="c-st">${pill(b.status)}</span>
      </div>`).join('') : '<div class="empty">Nenhuma cópia neste filtro.</div>';
    return `
      <div class="page-head"><div><h1>Histórico de backups</h1><p>${list ? list.length : '…'} ${list && list.length === 1 ? 'cópia listada' : 'cópias listadas'} · cópias expiradas são removidas pela retenção.</p></div>${runBtn()}</div>
      <div class="tabs">${tab('all', 'Todos')}${tab('auto', 'Automáticos')}${tab('manual', 'Manuais')}${tab('error', 'Falhas')}</div>
      <div class="card table" style="overflow:hidden">
        <div class="thead"><span class="c-date">Data</span><span class="c-type">Tipo</span><span class="c-db">Banco · SGBD</span><span class="c-size">Tamanho</span><span class="c-dur">Duração</span><span class="c-st">Status</span></div>
        ${rows}
      </div>`;
  }

  // ---------------------------------------------------------------- detalhe
  function logLines(lines) {
    if (!lines || !lines.length) return '<div class="ln"><span class="m">Sem registros.</span></div>';
    return lines.map((l) => `<div class="ln"><span class="t">${esc(time(l.ts))}</span><span class="l ${esc(l.level)}">${esc(l.level)}</span><span class="m">${esc(l.message)}</span></div>`).join('');
  }

  function viewDetail() {
    const D = S.detail;
    const backLink = `<a class="back" href="#/historico">${I.back}Histórico</a>`;
    if (!D) return backLink + `<div class="loading">${I.spinner(18)} Carregando…</div>`;
    if (D.error) return backLink + `<div class="card pad empty">${esc(D.error)}</div>`;
    const b = D.backup;
    const ok = b.status === 'success';
    const prot = [b.encrypted ? 'AES-256-GCM' : null, b.compressed ? 'gzip' : null].filter(Boolean).join(' · ') || 'Nenhuma';
    let integ = 'Não verificada';
    if (b.verify_ok === true) integ = `Íntegra · ${fmtWhen(b.verified_at)}`;
    if (b.verify_ok === false) integ = `Corrompida · ${fmtWhen(b.verified_at)}`;
    const running = S.data.running;
    const extra = (D.executions || []).length ? `<div class="grp">━━ outras execuções desta cópia: ${D.executions.map((e) => `${KIND[e.kind]} ${fmtWhen(e.started_at)} (${PILL[e.status]})`).map(esc).join(' · ')} — veja em <a href="#/logs">Logs</a></div>` : '';
    return `${backLink}
      <div class="detail-head"><div><h1>${esc(b.id)}</h1><p>${fmtWhen(b.created_at)}</p></div>${pill(b.status)}</div>
      <div class="grid-detail">
        <div class="card pad-lg">
          <div class="card-title" style="margin-bottom:16px">Metadados</div>
          <div class="meta">
            <div><div class="k">TIPO</div><div class="v">${TYPE[b.trigger] || esc(b.trigger)}</div></div>
            <div><div class="k">SGBD</div><div class="v">${esc(b.sgbd_label)}</div></div>
            <div><div class="k">BANCO DE DADOS</div><div class="v mono">${esc(b.dbname)}</div></div>
            <div><div class="k">TAMANHO</div><div class="v">${fmtSize(b.size)}${b.raw_size ? ` <span style="color:var(--muted-3)">(dump ${fmtSize(b.raw_size)})</span>` : ''}</div></div>
            <div><div class="k">DURAÇÃO</div><div class="v">${fmtDur(b.duration)}</div></div>
            <div><div class="k">PROTEÇÃO</div><div class="v">${prot}</div></div>
            <div><div class="k">INTEGRIDADE</div><div class="v">${integ}</div></div>
            <div><div class="k">SHA-256</div><div class="v mono" style="font-size:11.5px;word-break:break-all">${esc(b.sha256 || '—')}</div></div>
          </div>
          ${ok ? `<div class="path"><div class="k">LOCAL DE ARMAZENAMENTO</div><div class="v">${esc(b.path)}</div></div>` : ''}
          ${b.error ? `<div class="err-box">${esc(b.error)}</div>` : ''}
        </div>
        <div class="card pad-lg act">
          <div class="card-title" style="margin-bottom:6px">Ações</div>
          <button class="btn btn-primary" data-action="restore" ${!ok || running ? 'disabled' : ''}>${I.restore}Restaurar este backup</button>
          <button class="btn btn-ghost" data-action="verify" ${!ok || running || S.busy.verify ? 'disabled' : ''}>${S.busy.verify ? I.spinner() + 'Verificando…' : I.verify + 'Verificar integridade'}</button>
          <a class="btn btn-ghost ${ok ? '' : 'disabled'}" ${ok ? `href="/api/backups/${encodeURIComponent(b.id)}/download"` : ''}>${I.download}Baixar cópia</a>
          <button class="btn btn-danger-ghost" data-action="delete" ${b.status === 'running' ? 'disabled' : ''}>${I.trash}Excluir cópia</button>
        </div>
      </div>
      <div class="term">
        <div class="term-head"><span class="dot ${b.status === 'error' ? 'r' : b.status === 'running' ? 'b' : 'g'}"></span><span>log desta execução</span></div>
        <div class="term-body">${logLines(D.logs)}${extra}</div>
      </div>`;
  }

  // -------------------------------------------------------------------- logs
  function viewLogs() {
    const ex = S.logs;
    const body = !ex ? `${I.spinner()}` : ex.length ? ex.map((e) => {
      const ref = e.backup_id ? ` · <a href="#/backup/${esc(e.backup_id)}">${esc(e.backup_id)}</a>` : '';
      const trig = e.kind === 'backup' ? ' · ' + (TYPE[e.trigger] || e.trigger) : '';
      return `<div class="grp">━━ ${fmtWhen(e.started_at)} · ${KIND[e.kind] || esc(e.kind)}${esc(trig)}${ref} · ${PILL[e.status] || esc(e.status)}</div>${logLines(e.lines)}`;
    }).join('') : '<div class="ln"><span class="m">Nenhuma execução registrada ainda.</span></div>';
    return `
      <div class="page-head"><div><h1>Logs de execução</h1><p>Registro detalhado de cada etapa, com horário exato.</p></div>
        <a class="btn btn-ghost" href="/api/logs/download">${I.download}Baixar logs</a></div>
      <div class="term">
        <div class="term-head"><span class="dot ${S.data.running ? 'b' : 'g'}"></span><span>sentinela.log — últimas execuções</span></div>
        <div class="term-body tall">${body}</div>
      </div>`;
  }

  // ---------------------------------------------------------------- conexão
  function viewConn() {
    const c = S.connDraft || S.data.connection;
    const sh = c.ssh || {};
    const seg = (on, act, label) => `<div class="${on ? 'on' : ''}" data-action="${act}">${label}</div>`;
    const t = S.test;
    let testMsg = '';
    if (t.status === 'testing') testMsg = `<span class="test-run">${I.spinner()}Testando…</span>`;
    if (t.status === 'ok') testMsg = `<span class="test-ok">${I.check('#22a565', 15)}Conexão bem-sucedida · ${esc(t.version)}${sh.enabled ? ' · via SSH' : ''}</span>`;
    if (t.status === 'error') testMsg = `<span class="test-err">${I.x}${esc(t.error)}</span>`;
    const f = (id, label, val, type = 'text', ph = '') => `<div><label class="lbl" for="${id}">${label}</label><input class="input sm mono" id="${id}" type="${type}" value="${esc(val)}" placeholder="${esc(ph)}" spellcheck="false" autocomplete="off"></div>`;
    return `<div class="narrow-sm">
      <div class="page-head"><div><h1>Conexão com o banco</h1><p>Configure o acesso ao banco de dados que será copiado.</p></div></div>
      <div class="card pad-lg mb16">
        <div class="lbl" style="margin-bottom:10px">Gerenciador (SGBD)</div>
        <div class="seg full mb20">${seg(c.sgbd === 'postgres', 'sgbd-postgres', 'PostgreSQL')}${seg(c.sgbd === 'mariadb', 'sgbd-mariadb', 'MariaDB (MySQL)')}</div>
        <div class="lbl" style="margin-bottom:10px">Forma de acesso</div>
        <div class="seg full">${seg(!sh.enabled, 'ssh-off', 'Conexão direta')}${seg(sh.enabled, 'ssh-on', 'Túnel SSH')}</div>
        ${sh.enabled ? viewSsh(sh, f, seg) : '<div class="hint">O Sentinela conecta direto na porta do banco. Use o túnel SSH quando o banco estiver em outro servidor e a porta dele não estiver exposta.</div>'}
      </div>
      <div class="card pad-lg mb16">
        <div class="card-title">Banco de dados</div>
        <div class="card-sub">${sh.enabled ? 'Host e porta do banco <strong>vistos a partir do servidor SSH</strong> — normalmente <span class="mono">localhost</span>.' : 'Endereço do servidor de banco de dados.'}</div>
        <div class="g21 mb16">${f('c-host', 'Host', c.host)}${f('c-port', 'Porta', c.port)}</div>
        <div class="mb16">${f('c-dbname', 'Nome do banco', c.dbname, 'text', 'ex.: loja_producao')}</div>
        <div class="g2 mb20">${f('c-user', 'Usuário', c.user)}${f('c-password', 'Senha', c.password || '', 'password', S.data.connection.has_password ? '•••••••• (mantida)' : '')}</div>
        <div class="actions" style="align-items:center;gap:14px">
          <button class="btn btn-soft" data-action="conn-test" ${t.status === 'testing' ? 'disabled' : ''}>Testar conexão</button>
          ${testMsg}
        </div>
      </div>
      <div class="card pad-lg mb22">
        <div class="card-title">Diretório de backup</div>
        <div class="card-sub">Pasta isolada, idealmente em disco externo ou remoto (regra 3-2-1).</div>
        <input class="input mono" id="c-directory" value="${esc(c.directory)}" spellcheck="false">
      </div>
      <button class="btn btn-primary btn-lg" data-action="conn-save" ${S.busy.conn ? 'disabled' : ''}>${S.busy.conn ? 'Salvando…' : 'Salvar configurações'}</button>
    </div>`;
  }

  function viewSsh(sh, f, seg) {
    const saved = S.data.connection.ssh || {};
    const keep = (has) => (has ? '•••••••• (mantida)' : '');
    const hostKey = sh.host_key
      ? `<div class="hint">Chave do servidor registrada: <span class="mono">${esc(sh.host_key)}</span> · <a data-action="ssh-reset">redefinir</a></div>`
      : '<div class="hint">A impressão digital do servidor SSH será registrada na primeira conexão; se ela mudar depois, a conexão é bloqueada.</div>';
    const auth = sh.auth === 'key'
      ? `<div class="mb16"><label class="lbl" for="s-private_key">Chave privada</label>
           <textarea class="input mono" id="s-private_key" rows="5" spellcheck="false" placeholder="${saved.has_private_key ? 'Chave mantida — cole outra para substituir' : '-----BEGIN OPENSSH PRIVATE KEY-----'}">${esc(sh.private_key || '')}</textarea></div>
         ${f('s-key_passphrase', 'Senha da chave (se houver)', sh.key_passphrase || '', 'password', keep(saved.has_passphrase))}`
      : f('s-password', 'Senha SSH', sh.password || '', 'password', keep(saved.has_password));
    return `<div style="margin-top:20px;padding-top:20px;border-top:1px solid var(--line-2)">
        <div class="g21 mb16">${f('s-host', 'Servidor SSH', sh.host, 'text', 'ex.: 200.100.50.10')}${f('s-port', 'Porta SSH', sh.port || '22')}</div>
        <div class="mb16">${f('s-user', 'Usuário SSH', sh.user, 'text', 'ex.: backup')}</div>
        <div class="lbl" style="margin-bottom:10px">Autenticação</div>
        <div class="seg mb16">${seg(sh.auth !== 'key', 'ssh-auth-password', 'Senha')}${seg(sh.auth === 'key', 'ssh-auth-key', 'Chave privada')}</div>
        ${auth}
        ${hostKey}
      </div>`;
  }

  // Lê os campos da tela de conexão para o rascunho (sem re-renderizar).
  function readConn() {
    const d = S.connDraft; if (!d) return;
    ['host', 'port', 'dbname', 'user', 'password', 'directory'].forEach((k) => {
      const el = document.getElementById('c-' + k); if (el) d[k] = el.value;
    });
    ['host', 'port', 'user', 'password', 'private_key', 'key_passphrase'].forEach((k) => {
      const el = document.getElementById('s-' + k); if (el) d.ssh[k] = el.value;
    });
  }
  function readPolicy() {
    const d = S.policyDraft; if (!d) return;
    const iv = document.getElementById('pol-interval'); if (iv) d.interval_days = +iv.value || 1;
    const r = document.getElementById('pol-retention'); if (r) d.retention_days = +r.value;
    const dir = document.getElementById('pol-dir'); if (dir) d.directory = dir.value;
  }

  // ---------------------------------------------------------------- modal
  function confirmModal({ title, html, okLabel, onOk }) {
    modalRoot.innerHTML = `<div class="overlay" data-close="1"><div class="modal" role="dialog" aria-modal="true">
      <div class="ic">${I.warn('#d97706', 24)}</div>
      <h3>${title}</h3><p>${html}</p>
      <div class="foot"><button class="btn btn-ghost" data-close="1">Cancelar</button><button class="btn btn-danger" id="modal-ok">${okLabel}</button></div>
    </div></div>`;
    document.getElementById('modal-ok').addEventListener('click', async () => { modalRoot.innerHTML = ''; await onOk(); });
  }
  modalRoot.addEventListener('click', (e) => {
    if (e.target.dataset.close) modalRoot.innerHTML = '';
  });
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') modalRoot.innerHTML = ''; });

  // --------------------------------------------------------------- ações
  const actions = {
    async logout() {
      try { await api('POST', '/api/logout'); } catch (e) { /* ignora */ }
      S.user = null; S.data = null; go('login');
    },
    async run() {
      S.busy.run = true; render();
      try {
        const r = await api('POST', '/api/backups');
        toast('Backup manual iniciado…');
        S.busy.run = false;
        await load(); render(); schedulePoll();
        return r;
      } catch (e) { S.busy.run = false; render(); toast(e.message, true); }
    },
    'pol-daily'() { readPolicy(); S.policyDraft.schedule_mode = 'daily'; render(); },
    'pol-custom'() { readPolicy(); S.policyDraft.schedule_mode = 'custom'; render(); },
    'pol-enc'() { readPolicy(); S.policyDraft.encryption = !S.policyDraft.encryption; render(); },
    'pol-comp'() { readPolicy(); S.policyDraft.compression = !S.policyDraft.compression; render(); },
    async 'pol-save'() {
      readPolicy(); S.busy.pol = true; render();
      try {
        const r = await api('PUT', '/api/policy', S.policyDraft);
        S.policyDraft = Object.assign({}, r.policy); S.data.policy = r.policy;
        toast('Política de backup salva');
      } catch (e) { toast(e.message, true); }
      S.busy.pol = false; render();
    },
    'sgbd-postgres'() { setSgbd('postgres'); },
    'sgbd-mariadb'() { setSgbd('mariadb'); },
    'ssh-on'() { readConn(); S.connDraft.ssh.enabled = true; S.test = { status: 'idle' }; render(); },
    'ssh-off'() { readConn(); S.connDraft.ssh.enabled = false; S.test = { status: 'idle' }; render(); },
    'ssh-auth-password'() { readConn(); S.connDraft.ssh.auth = 'password'; render(); },
    'ssh-auth-key'() { readConn(); S.connDraft.ssh.auth = 'key'; render(); },
    'ssh-reset'() {
      readConn(); S.connDraft.ssh.reset_host_key = true; S.connDraft.ssh.host_key = null; render();
      toast('A chave do servidor será registrada de novo na próxima conexão');
    },
    async 'conn-test'() {
      readConn(); S.test = { status: 'testing' }; render();
      try {
        const r = await api('POST', '/api/connection/test', S.connDraft);
        S.test = r.ok ? { status: 'ok', version: r.version } : { status: 'error', error: r.error };
        if (r.ok && r.ssh_host_key) S.connDraft.ssh.host_key = r.ssh_host_key;
      } catch (e) { S.test = { status: 'error', error: e.message }; }
      render();
    },
    async 'conn-save'() {
      readConn(); S.busy.conn = true; render();
      try {
        const r = await api('PUT', '/api/connection', S.connDraft);
        S.data.connection = r.connection;
        S.connDraft = newConnDraft(r.connection, S.connDraft.directory);
        toast('Configurações de conexão salvas');
        await load();
      } catch (e) { toast(e.message, true); }
      S.busy.conn = false; render();
    },
    restore() {
      const b = S.detail.backup;
      confirmModal({
        title: 'Restaurar backup?',
        html: `Isto substituirá os dados atuais do banco <strong class="mono">${esc(S.data.connection.dbname)}</strong> pela cópia de <strong>${fmtWhen(b.created_at)}</strong>. Antes, o Sentinela gera automaticamente uma cópia do estado atual.`,
        okLabel: 'Restaurar agora',
        async onOk() {
          try {
            await api('POST', `/api/backups/${encodeURIComponent(b.id)}/restore`);
            toast('Restauração iniciada…');
            go('logs');
          } catch (e) { toast(e.message, true); }
        },
      });
    },
    async verify() {
      const b = S.detail.backup;
      S.busy.verify = true; render();
      try {
        const r = await api('POST', `/api/backups/${encodeURIComponent(b.id)}/verify`);
        if (r.ok) toast('Cópia íntegra: hash, criptografia e dump conferem');
        else toast('Cópia inválida: ' + r.error, true);
      } catch (e) { toast(e.message, true); }
      S.busy.verify = false; await load(); render();
    },
    delete() {
      const b = S.detail.backup;
      confirmModal({
        title: 'Excluir cópia?',
        html: `O arquivo da cópia <strong class="mono">${esc(b.id)}</strong> será apagado do diretório de backup. Esta ação não pode ser desfeita.`,
        okLabel: 'Excluir',
        async onOk() {
          try {
            await api('DELETE', `/api/backups/${encodeURIComponent(b.id)}`);
            toast('Cópia excluída'); go('history');
          } catch (e) { toast(e.message, true); }
        },
      });
    },
  };

  function newConnDraft(conn, directory) {
    const ssh = Object.assign({ password: '', private_key: '', key_passphrase: '' }, conn.ssh || {});
    return Object.assign({}, conn, { password: '', directory, ssh });
  }

  function setSgbd(s) {
    readConn();
    const d = S.connDraft;
    const defaults = { postgres: '5432', mariadb: '3306' };
    if (!d.port || d.port === defaults[d.sgbd]) d.port = defaults[s];
    d.sgbd = s; S.test = { status: 'idle' }; render();
  }

  // ------------------------------------------------------------- eventos
  app.addEventListener('click', (e) => {
    const a = e.target.closest('[data-action]');
    if (a && !a.disabled) { e.preventDefault(); actions[a.dataset.action](); return; }
    const o = e.target.closest('[data-open]');
    if (o) { if (e.target.closest('a')) return; S.detail = null; go('detail', o.dataset.open); return; }
    const f = e.target.closest('[data-filter]');
    if (f) { S.filter = f.dataset.filter; S.backups = null; render(); load().then(render); }
  });
  app.addEventListener('input', (e) => {
    if (e.target.id === 'pol-retention') {
      document.getElementById('ret-val').textContent = e.target.value;
    }
  });
  window.addEventListener('hashchange', onRoute);

  // ------------------------------------------------------------- início
  (async function boot() {
    try { const r = await api('GET', '/api/me'); S.user = r.user; } catch (e) { S.user = null; }
    onRoute();
  })();
})();
