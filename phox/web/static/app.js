let encMode = 'encode';
let _hashFileData = null;


function esc(s) {
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}

function fmt(n) { return Number(n).toLocaleString(); }


let _toastId = 0;

function showToast(msg, type = 'info') {
  const container = document.getElementById('toasts');
  if (!container) return;
  const colors = { success: '#22c55e', error: '#ef4444', info: '#7c3aed' };
  const icons = { success: '\u2713', error: '\u2717', info: '\u24D2' };
  const el = document.createElement('div');
  el.style.cssText =
    'display:flex;align-items:center;gap:0.5rem;padding:0.75rem 1rem;' +
    'border-radius:8px;background:var(--bg-card,#1e1e2e);color:var(--text,#e0e0e0);' +
    'border-left:4px solid ' + (colors[type] || colors.info) + ';' +
    'box-shadow:0 4px 12px rgba(0,0,0,.4);animation:toastIn .3s ease;' +
    'font-size:0.875rem;margin-bottom:0.5rem;max-width:380px;transition:all .3s ease';
  el.innerHTML = '<span style="color:' + (colors[type] || colors.info) + ';font-size:1.1rem">' +
    (icons[type] || '') + '</span><span>' + esc(msg) + '</span>';
  container.appendChild(el);
  setTimeout(() => {
    el.style.opacity = '0';
    el.style.transform = 'translateX(100%)';
    setTimeout(() => el.remove(), 300);
  }, 4000);
}


function showLoader() {
  const el = document.getElementById('loader');
  if (el) el.style.display = 'flex';
}

function hideLoader() {
  const el = document.getElementById('loader');
  if (el) el.style.display = 'none';
}


function showPage(id) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
  const page = document.getElementById('page-' + id);
  const btn = document.querySelector('[data-page="' + id + '"]');
  if (page) page.classList.add('active');
  if (btn) btn.classList.add('active');
  try { localStorage.setItem('phox-last-page', id); } catch (_) {}
  if (id === 'settings') loadSettings();
  if (id === 'colors') renderColorPalette();
  const sidebar = document.getElementById('sidebar');
  if (sidebar) sidebar.classList.remove('open');
  const content = document.getElementById('content');
  if (content) content.scrollTop = 0;
}

function toggleSidebar() {
  const sidebar = document.getElementById('sidebar');
  if (sidebar) sidebar.classList.toggle('open');
}

(function restorePage() {
  const last = localStorage.getItem('phox-last-page');
  if (last && document.getElementById('page-' + last)) {
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
    document.getElementById('page-' + last).classList.add('active');
    const btn = document.querySelector('[data-page="' + last + '"]');
    if (btn) btn.classList.add('active');
  }
})();


async function api(route, data) {
  showLoader();
  try {
    const resp = await fetch(route, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    const json = await resp.json();
    if (!resp.ok && !json.error) json.error = 'HTTP ' + resp.status;
    return json;
  } catch (e) {
    return { error: e.message || 'Network error' };
  } finally {
    hideLoader();
  }
}


function showResult(id, html) {
  const el = document.getElementById(id);
  if (!el) return;
  el.innerHTML = html;
  el.style.display = 'block';
  let parent = el.parentElement;
  while (parent) {
    if (parent.style && parent.style.display === 'none') parent.style.display = 'block';
    parent = parent.parentElement;
  }
}

function showError(id, msg) {
  showResult(id, '<div class="msg msg-error">' + esc(msg) + '</div>');
}

function copyResult(id) {
  const el = document.getElementById(id);
  if (!el) return;
  const text = (el.innerText || el.textContent || '').trim();
  navigator.clipboard.writeText(text).then(() => {
    showToast('Copied to clipboard', 'success');
    const btn = el.parentElement && el.parentElement.querySelector('.btn-copy');
    if (btn) { const old = btn.innerHTML; btn.innerHTML = '&#10003; Copied!'; setTimeout(() => btn.innerHTML = old, 1500); }
  }).catch(() => {
    const ta = document.createElement('textarea');
    ta.value = text; ta.style.cssText = 'position:fixed;opacity:0';
    document.body.appendChild(ta); ta.select();
    try { document.execCommand('copy'); showToast('Copied to clipboard', 'success'); }
    catch (_) { showToast('Failed to copy', 'error'); }
    document.body.removeChild(ta);
  });
}

function copyTextArea(id) {
  const el = document.getElementById(id);
  if (!el) return;
  navigator.clipboard.writeText(el.value).then(
    () => showToast('Copied to clipboard', 'success'),
    () => showToast('Failed to copy', 'error')
  );
}

function switchEncTab(mode) {
  encMode = mode;
  document.querySelectorAll('#page-encode .tab').forEach(t => t.classList.remove('active'));
  if (typeof event !== 'undefined' && event.target) event.target.classList.add('active');
}

async function runEncodeDecode() {
  const text = document.getElementById('enc-text').value;
  const format = document.getElementById('enc-format').value;
  const route = encMode === 'encode' ? '/api/encode' : '/api/decode';
  if (!text.trim()) { showError('enc-result', 'Please enter text to encode/decode'); return; }
  const data = await api(route, { text, format });
  if (data.error) { showError('enc-result', data.error); showToast(data.error, 'error'); }
  else { showResult('enc-result', '<div class="result-box mono">' + esc(data.result) + '</div>'); showToast('Text ' + encMode + 'd successfully', 'success'); }
}

async function runHash() {
  const text = document.getElementById('hash-text').value;
  const algo = document.getElementById('hash-algo').value;
  if (!text.trim()) { showError('hash-result', 'Please enter text to hash'); return; }
  const data = await api('/api/hash', { text, algo });
  if (data.error) { showError('hash-result', data.error); showToast(data.error, 'error'); return; }
  if (algo === 'all' && data.results) {
    let html = '<div class="result-box mono">';
    for (const [a, h] of Object.entries(data.results)) html += '<strong>' + esc(a.toUpperCase()) + '</strong>: ' + esc(h) + '\n';
    showResult('hash-result', html + '</div>');
    showToast('All hash algorithms computed', 'success');
  } else {
    showResult('hash-result', '<div class="result-box mono"><strong>' + esc((data.algo || algo).toUpperCase()) + '</strong>: ' + esc(data.result) + '</div>');
    showToast((data.algo || algo).toUpperCase() + ' hash computed', 'success');
  }
}

async function runQR() {
  const text = document.getElementById('qr-text').value;
  const format = document.getElementById('qr-format').value;
  const size = parseInt(document.getElementById('qr-size').value) || 200;
  if (!text.trim()) { showToast('Please enter text for QR code', 'error'); return; }
  const data = await api('/api/qr', { text, format, size });
  const el = document.getElementById('qr-output');
  if (!el) return;
  if (data.error) { el.innerHTML = '<div class="msg msg-error">' + esc(data.error) + '</div>'; showToast(data.error, 'error'); }
  else if (format === 'svg') { el.innerHTML = data.result; showToast('QR code generated (SVG)', 'success'); }
  else { el.innerHTML = '<pre class="qr-text">' + esc(data.result) + '</pre>'; showToast('QR code generated', 'success'); }
}

async function runPassword() {
  const length = parseInt(document.getElementById('pw-length').value) || 16;
  const count = parseInt(document.getElementById('pw-count').value) || 5;
  const special = document.getElementById('pw-special').checked;
  const digits = document.getElementById('pw-digits').checked;
  const upper = document.getElementById('pw-upper').checked;
  const data = await api('/api/password', { length, count, special, digits, upper });
  if (data.error) { showError('pw-result', data.error); showToast(data.error, 'error'); }
  else { showResult('pw-result', '<div class="result-box mono">' + data.passwords.map(p => esc(p)).join('\n') + '</div>'); showToast(data.passwords.length + ' passwords generated', 'success'); }
}

async function runIPLookup() {
  const ip = document.getElementById('ip-address').value;
  const data = await api('/api/ip-lookup', { ip });
  if (data.error) { showError('ip-result', data.error); showToast(data.error, 'error'); return; }
  const r = data.result;
  const sections = [
    { title: '', fields: [['IP Address','ip'],['Type','type'],['Flag','flag_emoji']] },
    { title: 'Location', fields: [
      ['Continent','continent'],['Country','country'],['Country Code','country_code'],['EU Member','is_eu'],
      ['Region','region'],['Region Code','region_code'],['City','city'],['Zip / Postal','zip'],
      ['Capital','capital'],['Latitude','latitude'],['Longitude','longitude'],['Borders','borders']
    ]},
    { title: 'Timezone', fields: [
      ['Timezone','timezone_id'],['Abbreviation','timezone_abbr'],['UTC Offset','timezone_utc'],
      ['Offset (sec)','timezone_offset'],['DST Active','timezone_is_dst']
    ]},
    { title: 'Network', fields: [
      ['ISP','isp'],['Organization','org'],['ASN','asn'],['Domain','domain'],
      ['Calling Code','calling_code'],['Reverse DNS','reverse']
    ]}
  ];
  let html = '<table>';
  for (const sec of sections) {
    if (sec.title) html += '<tr><td colspan="2" class="section-header">' + esc(sec.title) + '</td></tr>';
    for (const [label, key] of sec.fields) {
      let val = r[key];
      if (val === true) val = '<span class="flag flag-ok">Yes</span>';
      else if (val === false) val = '<span class="flag flag-error">No</span>';
      else if (val !== null && val !== undefined && val !== 'N/A' && val !== '') val = esc(String(val));
      else continue;
      html += '<tr><td>' + esc(label) + '</td><td>' + val + '</td></tr>';
    }
  }
  const flags = [];
  if (r.proxy) flags.push('<span class="flag flag-warn">PROXY</span>');
  if (r.vpn) flags.push('<span class="flag flag-warn">VPN</span>');
  if (r.tor) flags.push('<span class="flag flag-error">TOR</span>');
  if (r.relay) flags.push('<span class="flag flag-warn">RELAY</span>');
  if (r.cloud) flags.push('<span class="flag flag-info">CLOUD</span>');
  if (r.mobile) flags.push('<span class="flag flag-info">MOBILE</span>');
  html += '<tr><td colspan="2" class="section-header">Security</td></tr>';
  html += '<tr><td>Flags</td><td class="flags-cell">' +
    (flags.length ? flags.join(' ') : '<span class="flag flag-ok">None detected</span>') + '</td></tr></table>';
  if (r.latitude && r.longitude && r.latitude !== 'N/A')
    html += '<div style="margin-top:8px"><a href="https://www.google.com/maps?q=' + r.latitude + ',' + r.longitude + '" target="_blank" style="color:var(--accent)">View on Google Maps</a></div>';
  const el = document.getElementById('ip-result');
  el.innerHTML = html; el.style.display = 'block';
  const saveGroup = document.getElementById('ip-save-group');
  if (saveGroup) saveGroup.style.display = 'block';
  window._lastIPResult = data;
  showToast('IP lookup complete', 'success');
}

async function saveIPLookup() {
  const data = window._lastIPResult;
  if (!data || !data.result) { showToast('No IP data to save', 'error'); return; }
  const resp = await api('/api/save-ip', data);
  if (resp.error) { showToast(resp.error, 'error'); }
  else {
    showToast('IP data saved', 'success');
    const btn = document.querySelector('#ip-save-group .btn-save');
    if (btn) { const old = btn.innerHTML; btn.innerHTML = '&#10003; Saved!'; setTimeout(() => btn.innerHTML = old, 1500); }
  }
}

async function runDNS() {
  const domain = document.getElementById('dns-domain').value;
  const type = document.getElementById('dns-type').value;
  if (!domain.trim()) { showToast('Please enter a domain', 'error'); return; }
  const data = await api('/api/dns', { domain, type });
  if (data.error) { showError('dns-result', data.error); showToast(data.error, 'error'); return; }
  if (data.results && data.results.length > 0) {
    let html = '<table><tr><th>Record</th></tr>';
    for (const r of data.results) html += '<tr><td class="mono">' + esc(r) + '</td></tr>';
    showResult('dns-result', html + '</table>');
    showToast(data.results.length + ' record(s) found', 'success');
  } else {
    showResult('dns-result', '<div class="msg msg-error">No records found</div>');
    showToast('No DNS records found', 'info');
  }
}

async function runWhois() {
  const domain = document.getElementById('whois-domain').value;
  if (!domain.trim()) { showToast('Please enter a domain', 'error'); return; }
  const data = await api('/api/whois', { domain });
  if (data.error) { showError('whois-result', data.error); showToast(data.error, 'error'); return; }
  const r = data.result;
  let html = '<table>';
  if (r.ldhName) html += '<tr><td>Domain</td><td>' + esc(r.ldhName) + '</td></tr>';
  if (r.status) html += '<tr><td>Status</td><td>' + esc(r.status.join(', ')) + '</td></tr>';
  for (const ev of (r.events || []))
    if (ev.eventAction && ev.eventDate) html += '<tr><td>' + esc(ev.eventAction) + '</td><td>' + esc(ev.eventDate) + '</td></tr>';
  for (const ns of (r.nameservers || []))
    if (ns.ldhName) html += '<tr><td>Nameserver</td><td>' + esc(ns.ldhName) + '</td></tr>';
  for (const ent of (r.entities || [])) {
    const roles = (ent.roles || []).join(', ');
    if (roles) html += '<tr><td>' + esc(roles) + '</td><td>' + esc(ent.handle || '') + '</td></tr>';
  }
  const el = document.getElementById('whois-result');
  el.innerHTML = html + '</table>'; el.style.display = 'block';
  showToast('WHOIS lookup complete', 'success');
}

async function runUsername() {
  const name = document.getElementById('username-name').value;
  if (!name.trim()) { showToast('Please enter a username', 'error'); return; }
  const el = document.getElementById('username-results');
  el.innerHTML = '<div class="msg msg-info">Checking across platforms...</div>';
  const data = await api('/api/username', { name });
  if (data.error) { el.innerHTML = '<div class="msg msg-error">' + esc(data.error) + '</div>'; showToast(data.error, 'error'); return; }
  const icons = {
    github:'\u{1F419}',twitter:'\u{1F426}',instagram:'\u{1F4F7}',reddit:'\u{1F916}',
    tiktok:'\u{1F3B5}',youtube:'\u{1F4FA}',twitch:'\u{1F3AE}',pinterest:'\u{1F4CC}',
    linkedin:'\u{1F4BC}',medium:'\u{1F4DD}',snapchat:'\u{1F4F9}',facebook:'\u{1F310}',
    threads:'\u{1F517}',bluesky:'\u{1F426}',gitlab:'\u{1F4BB}',bitbucket:'\u{1F4E6}',
    deviantart:'\u{1F3A8}',npm:'\u{1F4E6}',pypi:'\u{1F40D}',codepen:'\u270F',
    replit:'\u{1F525}',keybase:'\u{1F511}',steam:'\u{1F3AE}',spotify:'\u{1F3B5}',
    soundcloud:'\u{1F3B5}',vimeo:'\u{1F3AC}',flickr:'\u{1F4F7}',telegram:'\u{1F4E9}',
    pastebin:'\u{1F4CB}',hackerone:'\u{1F41B}',gravatar:'\u{1F464}',roblox:'\u{1F3AE}',
    epicgames:'\u{1F3AE}',behance:'\u{1F4A8}',mastodon:'\u{1F434}'
  };
  let html = '', taken = 0, available = 0;
  for (const r of data.results) {
    const icon = icons[r.platform] || '';
    let cls, txt;
    if (r.available === null) { cls = 'error'; txt = 'ERROR'; }
    else if (r.available) { cls = 'available'; txt = 'AVAILABLE'; available++; }
    else { cls = 'taken'; txt = 'TAKEN'; taken++; }
    html += '<div class="user-item"><span class="user-platform">' + icon + ' ' + esc(r.platform) + '</span>' +
      '<span class="user-url">' + esc(r.url) + '</span><span class="user-status ' + cls + '">' + txt + '</span></div>';
  }
  el.innerHTML = '<div class="port-summary"><strong>' + taken + '</strong> taken, <strong>' + available +
    '</strong> available out of <strong>' + data.results.length + '</strong></div>' + html;
  const saveGroup = document.getElementById('username-save-group');
  if (saveGroup) saveGroup.style.display = 'block';
  window._lastUsernameResult = { username: name, results: data.results };
  showToast('Username check complete', 'success');
}

async function saveUsername() {
  const data = window._lastUsernameResult;
  if (!data || !data.results) { showToast('No username data to save', 'error'); return; }
  const resp = await api('/api/save-username', data);
  if (resp.error) { showToast(resp.error, 'error'); }
  else {
    showToast('Username data saved', 'success');
    const btn = document.querySelector('#username-save-group .btn-save');
    if (btn) { const old = btn.innerHTML; btn.innerHTML = '&#10003; Saved!'; setTimeout(() => btn.innerHTML = old, 1500); }
  }
}

async function runSubdomain() {
  const domain = document.getElementById('subdomain-domain').value;
  const large = document.getElementById('subdomain-large').checked;
  const brute = document.getElementById('subdomain-brute').checked;
  const maxlen = parseInt(document.getElementById('subdomain-maxlen').value) || 3;
  if (!domain.trim()) { showToast('Please enter a domain', 'error'); return; }
  if (brute) showToast('Brute-force mode: generating combinations...', 'info');
  else if (large) showToast('Downloading large wordlist...', 'info');
  const data = await api('/api/subdomain', { domain, large_wordlist: large, brute: brute, max_length: maxlen });
  if (data.error) { showError('subdomain-result', data.error); showToast(data.error, 'error'); return; }
  if (!data.subdomains || data.subdomains.length === 0) {
    showResult('subdomain-result', '<div class="msg msg-error">No subdomains found</div>');
    showToast('No subdomains found', 'info');
  } else {
    const srcInfo = data.wordlist_source ? ' (source: ' + esc(data.wordlist_source) + ', ' + fmt(data.wordlist_size) + ' words)' : '';
    showResult('subdomain-result', '<div class="result-box mono">' +
      data.subdomains.map(s => esc(s)).join('\n') + '</div>' +
      '<div class="port-summary">Found <strong>' + fmt(data.total) + '</strong> subdomains for ' + esc(data.domain) + srcInfo + '</div>');
    showToast(data.total + ' subdomains found', 'success');
  }
}


const PORT_SERVICES = {
  21:'FTP',22:'SSH',23:'Telnet',25:'SMTP',53:'DNS',80:'HTTP',110:'POP3',
  111:'RPC',135:'MSRPC',139:'NetBIOS',143:'IMAP',443:'HTTPS',445:'SMB',
  993:'IMAPS',995:'POP3S',1433:'MSSQL',1521:'Oracle',2049:'NFS',
  3306:'MySQL',3389:'RDP',5432:'PostgreSQL',5900:'VNC',6379:'Redis',
  8080:'HTTP-Alt',8443:'HTTPS-Alt',8888:'HTTP-Alt2',9090:'Web-UI',27017:'MongoDB'
};

async function runPortscan() {
  const host = document.getElementById('portscan-host').value;
  const ports = document.getElementById('portscan-ports').value;
  const timeout = parseFloat(document.getElementById('portscan-timeout').value) || 1;
  if (!host.trim()) { showToast('Please enter a host or IP', 'error'); return; }
  const data = await api('/api/portscan', { host, ports, timeout });
  if (data.error) { showError('portscan-result', data.error); showToast(data.error, 'error'); return; }
  const el = document.getElementById('portscan-result');
  let html = '';
  if (!data.open || data.open.length === 0) {
    html = '<div class="msg msg-error">No open ports found</div>';
  } else {
    html = '<div class="port-grid">';
    for (const port of data.open) {
      const svc = PORT_SERVICES[port] || 'unknown';
      html += '<div class="port-chip"><span class="port-dot"></span>' + port + ' <span class="port-svc">' + esc(svc) + '</span></div>';
    }
    html += '</div>';
  }
  html += '<div class="port-summary">Scanned <strong>' + fmt(data.scanned) + '</strong> ports on ' +
    esc(data.host) + ' (' + esc(data.ip) + ') &mdash; <strong>' + data.open.length + '</strong> open</div>';
  el.innerHTML = html; el.style.display = 'block';
  const group = document.getElementById('portscan-result-group');
  if (group) group.style.display = 'block';
  showToast('Scan complete: ' + data.open.length + ' open ports', data.open.length > 0 ? 'success' : 'info');
}

async function runSearch() {
  const query = document.getElementById('search-query').value;
  const max = parseInt(document.getElementById('search-max').value) || 10;
  if (!query.trim()) { showToast('Please enter a search query', 'error'); return; }
  const data = await api('/api/search', { query, max });
  const el = document.getElementById('search-results');
  if (data.error) { el.innerHTML = '<div class="msg msg-error">' + esc(data.error) + '</div>'; showToast(data.error, 'error'); }
  else if (!data.results || data.results.length === 0) { el.innerHTML = '<div class="msg msg-error">No results found</div>'; showToast('No results found', 'info'); }
  else {
    el.innerHTML = data.results.map(r => '<div class="search-item"><a href="' + esc(r.url) + '" target="_blank">' +
      esc(r.title || 'Untitled') + '</a><div class="url">' + esc(r.url) + '</div>' +
      (r.snippet ? '<div class="snippet">' + esc(r.snippet) + '</div>' : '') + '</div>').join('');
    showToast(data.results.length + ' results found', 'success');
  }
}

async function runApiRequest() {
  const url = document.getElementById('api-url').value;
  const method = document.getElementById('api-method').value;
  const headersStr = document.getElementById('api-headers').value;
  const bodyStr = document.getElementById('api-body').value;
  if (!url.trim()) { showToast('Please enter a URL', 'error'); return; }
  let headers = {};
  try { headers = JSON.parse(headersStr || '{}'); } catch (e) { showToast('Invalid headers JSON, ignoring', 'error'); }
  let body = null;
  if (bodyStr.trim()) { try { body = JSON.parse(bodyStr); } catch (e) { body = bodyStr; } }
  const data = await api('/api/api-request', { url, method, headers, body });
  if (data.error) { showError('api-result', data.error); showToast(data.error, 'error'); }
  else {
    const r = data.result;
    let html = '<div class="result-box mono"><strong>Status:</strong> ' + r.status + ' ' + esc(r.reason || '') +
      '\n<strong>Size:</strong> ' + fmt(r.size) + ' bytes\n<strong>Content-Type:</strong> ' +
      esc((r.headers && r.headers['content-type']) || 'N/A') + '\n\n';
    html += typeof r.body === 'object' ? esc(JSON.stringify(r.body, null, 2)) : esc(String(r.body || ''));
    showResult('api-result', html + '</div>');
    showToast('Response: ' + r.status, 'success');
  }
}

async function runWebhook() {
  const url = document.getElementById('webhook-url').value;
  const method = document.getElementById('webhook-method').value;
  const name = document.getElementById('webhook-name').value;
  const payload = document.getElementById('webhook-payload').value;
  if (!url.trim()) { showToast('Please enter a webhook URL', 'error'); return; }
  const data = { url, method, name };
  const title = document.getElementById('webhook-title').value;
  const color = document.getElementById('webhook-color').value;
  const message = document.getElementById('webhook-message').value;
  const image = document.getElementById('webhook-image').value;
  if (title || message || image) {
    const embed = {};
    if (title) embed.title = title;
    if (message) embed.description = message;
    if (color) embed.color = parseInt(color.replace('#', ''), 16) || 0;
    if (image) embed.image = { url: image };
    const discordPayload = {};
    try { if (payload) Object.assign(discordPayload, JSON.parse(payload)); } catch (_) {}
    discordPayload.embeds = [embed];
    data.data = JSON.stringify(discordPayload);
  } else {
    data.data = payload;
  }
  const resp = await api('/api/webhook-send', data);
  if (resp.error) { showError('webhook-result', resp.error); showToast(resp.error, 'error'); }
  else {
    showResult('webhook-result', '<div class="result-box mono"><strong>Status:</strong> ' + resp.status + '\n\n' + esc(resp.body || '(empty)') + '</div>');
    showToast('Webhook sent', 'success');
  }
}

async function doDiscord() { await runWebhook(); }


async function runCloner() {
  const url = document.getElementById('cloner-url').value;
  const depth = parseInt(document.getElementById('cloner-depth').value) || 2;
  const concurrency = parseInt(document.getElementById('cloner-concurrency').value) || 5;
  if (!url.trim()) { showToast('Please enter a URL to clone', 'error'); return; }
  const data = await api('/api/cloner-start', { url, depth, concurrency });
  if (data.error) { showError('cloner-result', data.error); showToast(data.error, 'error'); }
  else {
    let html = '<strong>Domain:</strong> ' + esc(data.domain) + '\n<strong>Files cloned:</strong> ' + fmt(data.total) +
      '\n<strong>Save directory:</strong> ' + esc(data.save_dir) + '\n\n';
    for (const f of (data.files || [])) html += '  ' + esc(f.url) + '\n    -> ' + esc(f.file) + ' (' + fmt(f.size) + ' bytes)\n';
    showResult('cloner-result', '<div class="result-box mono">' + html + '</div>');
    showToast(data.total + ' files cloned', 'success');
  }
}

async function runObfuscate() {
  const code = document.getElementById('obfuscate-code').value;
  const layers = parseInt(document.getElementById('obfuscate-layers').value) || 1;
  if (!code.trim()) { showToast('Please paste Python code to obfuscate', 'error'); return; }
  const data = await api('/api/obfuscate', { code, layers });
  if (data.error) { showError('obfuscate-result', data.error); showToast(data.error, 'error'); }
  else { showResult('obfuscate-result', esc(data.result)); showToast('Obfuscated with ' + layers + ' layer(s)', 'success'); }
}

function hashFileSelected() {
  const input = document.getElementById('hashfile-input');
  if (!input || !input.files[0]) return;
  const file = input.files[0];
  const label = document.getElementById('hashfile-label');
  if (label) label.textContent = file.name + ' (' + (file.size / 1024).toFixed(1) + ' KB)';
  const reader = new FileReader();
  reader.onload = function () {
    const base64 = btoa(String.fromCharCode(...new Uint8Array(reader.result)));
    _hashFileData = { content: base64, filename: file.name, size: file.size };
    showResult('hashfile-result', '<div class="msg msg-success">Loaded: ' + esc(file.name) + ' (' + fmt(file.size) + ' bytes)</div>');
    showToast('File loaded: ' + file.name, 'success');
  };
  reader.onerror = () => showToast('Failed to read file', 'error');
  reader.readAsArrayBuffer(file);
}

async function runHashFile() {
  if (!_hashFileData) { showToast('Please select a file first', 'error'); return; }
  const algo = document.getElementById('hashfile-algo').value;
  const data = await api('/api/hash-file', { ..._hashFileData, algo });
  if (data.error) { showError('hashfile-result', data.error); showToast(data.error, 'error'); return; }
  if (algo === 'all' && data.results) {
    let html = '<div class="result-box mono">';
    for (const [a, h] of Object.entries(data.results)) html += '<strong>' + esc(a.toUpperCase()) + '</strong>: ' + esc(h) + '\n';
    html += '</div><div class="port-summary">' + esc(data.filename) + ' (' + fmt(data.size) + ' bytes)</div>';
    showResult('hashfile-result', html);
    showToast('All hashes computed', 'success');
  } else {
    showResult('hashfile-result', '<div class="result-box mono"><strong>' + esc((data.algo || algo).toUpperCase()) + '</strong>: ' +
      esc(data.result) + '\n\n' + esc(data.filename) + ' (' + fmt(data.size) + ' bytes)</div>');
    showToast((data.algo || algo).toUpperCase() + ' hash computed', 'success');
  }
}

function updateRandOptions() {
  const type = document.getElementById('rand-type').value;
  const lengthGroup = document.getElementById('rand-length-group');
  const diceRow = document.getElementById('rand-dice-row');
  if (lengthGroup) lengthGroup.style.display = (type === 'string' || type === 'hex' || type === 'password') ? 'flex' : 'none';
  if (diceRow) diceRow.style.display = (type === 'dice') ? 'flex' : 'none';
}

async function runRandom() {
  const type = document.getElementById('rand-type').value;
  const count = parseInt(document.getElementById('rand-count').value) || 5;
  const length = parseInt(document.getElementById('rand-length').value) || 16;
  const sides = parseInt(document.getElementById('rand-sides').value) || 6;
  const dice = parseInt(document.getElementById('rand-dice').value) || 2;
  const data = await api('/api/random', { type, count, length, sides, dice });
  if (data.error) { showError('rand-result', data.error); showToast(data.error, 'error'); }
  else {
    showResult('rand-result', '<div class="result-box mono">' + data.results.map(r => esc(r)).join('\n') + '</div>');
    showToast(data.results.length + ' values generated', 'success');
  }
}

function renderColorPalette() {
  const el = document.getElementById('colors-display');
  if (!el) return;
  const basic = [
    [0,0,0],[205,0,0],[0,205,0],[205,205,0],[0,0,238],[205,0,205],[0,205,205],[229,229,229],
    [127,127,127],[255,0,0],[0,255,0],[255,255,0],[92,92,255],[255,0,255],[0,255,255],[255,255,255]
  ];
  let html = '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(60px,1fr));gap:4px">';
  const names = ['Black','Red','Green','Yellow','Blue','Magenta','Cyan','White',
    'Bright Black','Bright Red','Bright Green','Bright Yellow','Bright Blue','Bright Magenta','Bright Cyan','Bright White'];
  for (let i = 0; i < 16; i++) {
    const [r, g, b] = basic[i];
    const fg = i < 8 ? '#fff' : '#000';
    html += '<div style="background:rgb(' + r + ',' + g + ',' + b + ');color:' + fg + ';padding:6px 4px;text-align:center;border-radius:4px;font-size:0.7rem;cursor:pointer" title="' + names[i] + '" onclick="document.getElementById(\'color-preview-code\').value=' + i + ';previewColor()">\\e[' + (i < 8 ? '3' : '9') + (i % 8) + 'm</div>';
  }
  html += '</div><div style="margin-top:12px"><strong class="text-sm muted">216-Color Cube (16-231)</strong></div>';
  html += '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(28px,1fr));gap:2px;margin-top:4px">';
  for (let i = 16; i < 232; i++) {
    const idx = i - 16;
    const r = Math.floor(idx / 36) === 0 ? 0 : 55 + Math.floor(idx / 36) * 40;
    const g = Math.floor((idx % 36) / 6) === 0 ? 0 : 55 + Math.floor((idx % 36) / 6) * 40;
    const b = (idx % 6) === 0 ? 0 : 55 + (idx % 6) * 40;
    html += '<div style="background:rgb(' + r + ',' + g + ',' + b + ');width:100%;aspect-ratio:1;border-radius:2px;cursor:pointer" title="' + i + '" onclick="document.getElementById(\'color-preview-code\').value=' + i + ';previewColor()"></div>';
  }
  html += '</div><div style="margin-top:12px"><strong class="text-sm muted">Grayscale (232-255)</strong></div>';
  html += '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(28px,1fr));gap:2px;margin-top:4px">';
  for (let i = 232; i < 256; i++) {
    const v = 8 + (i - 232) * 10;
    html += '<div style="background:rgb(' + v + ',' + v + ',' + v + ');width:100%;aspect-ratio:1;border-radius:2px;cursor:pointer" title="' + i + '" onclick="document.getElementById(\'color-preview-code\').value=' + i + ';previewColor()"></div>';
  }
  el.innerHTML = html + '</div>';
}

function previewColor() {
  const code = parseInt(document.getElementById('color-preview-code').value);
  if (isNaN(code) || code < 0 || code > 255) { showToast('Enter a value between 0 and 255', 'error'); return; }
  let r, g, b;
  const basic = [[0,0,0],[205,0,0],[0,205,0],[205,205,0],[0,0,238],[205,0,205],[0,205,205],[229,229,229],
    [127,127,127],[255,0,0],[0,255,0],[255,255,0],[92,92,255],[255,0,255],[0,255,255],[255,255,255]];
  if (code < 16) { [r, g, b] = basic[code]; }
  else if (code < 232) {
    const idx = code - 16;
    r = Math.floor(idx / 36) === 0 ? 0 : 55 + Math.floor(idx / 36) * 40;
    g = Math.floor((idx % 36) / 6) === 0 ? 0 : 55 + Math.floor((idx % 36) / 6) * 40;
    b = (idx % 6) === 0 ? 0 : 55 + (idx % 6) * 40;
  } else { r = g = b = 8 + (code - 232) * 10; }
  const hex = '#' + [r, g, b].map(c => c.toString(16).padStart(2, '0')).join('');
  const el = document.getElementById('color-preview-result');
  el.style.display = 'block';
  el.innerHTML = '<div style="display:flex;align-items:center;gap:1rem">' +
    '<div style="width:80px;height:80px;border-radius:8px;background:rgb(' + r + ',' + g + ',' + b + ');border:2px solid var(--border)"></div>' +
    '<div><div><strong>Code:</strong> ' + code + '</div><div><strong>RGB:</strong> rgb(' + r + ', ' + g + ', ' + b + ')</div>' +
    '<div><strong>Hex:</strong> ' + hex + '</div><div><strong>Escape:</strong> \\e[38;5;' + code + 'm</div></div></div>';
}

async function loadSettings() {
  const data = await api('/api/config-get', {});
  const el = document.getElementById('settings-list');
  if (data.error) { if (el) el.innerHTML = '<div class="msg msg-error">' + esc(data.error) + '</div>'; showToast('Failed to load settings', 'error'); return; }
  const config = data.config, meta = data.meta;
  let html = '<table>';
  for (const [key, info] of Object.entries(meta)) {
    const parts = key.split('.');
    let val = config;
    for (const p of parts) val = (val || {})[p];
    if (val === undefined) val = '';
    html += '<tr><td>' + esc(info.label || key) + '</td><td>';
    if (info.type === 'bool') {
      html += '<label class="toggle"><input type="checkbox" ' + (val ? 'checked' : '') + ' onchange="saveSetting(\'' + key + '\', this.checked)"><span class="toggle-slider"></span></label>';
    } else if (info.type === 'int') {
      html += '<input type="number" value="' + val + '" min="' + (info.min || 0) + '" max="' + (info.max || 99999) + '" onchange="saveSetting(\'' + key + '\', this.value)" style="background:var(--bg-input);color:var(--text);border:1px solid var(--border);padding:4px 8px;border-radius:4px;width:100px">';
    } else if (info.options) {
      html += '<select onchange="saveSetting(\'' + key + '\', this.value)" style="background:var(--bg-input);color:var(--text);border:1px solid var(--border);padding:4px 8px;border-radius:4px">';
      for (const opt of info.options) html += '<option value="' + opt + '" ' + (val === opt ? 'selected' : '') + '>' + opt + '</option>';
      html += '</select>';
    } else {
      html += '<input type="text" value="' + esc(String(val)) + '" onchange="saveSetting(\'' + key + '\', this.value)" style="background:var(--bg-input);color:var(--text);border:1px solid var(--border);padding:4px 8px;border-radius:4px;width:200px">';
    }
    html += '</td></tr>';
  }
  if (el) el.innerHTML = html + '</table>';
  showToast('Settings loaded', 'success');
}

async function saveSetting(key, value) {
  const resp = await api('/api/config-set', { key, value });
  if (resp.error) showToast(resp.error, 'error');
  else showToast('Setting saved', 'success');
}

async function saveSettings() {
  const el = document.getElementById('settings-list');
  if (!el) return;
  const inputs = el.querySelectorAll('input[type="number"], input[type="text"], select');
  let count = 0;
  for (const inp of inputs) {
    const key = inp.getAttribute('onchange');
    if (!key) continue;
    const match = key.match(/saveSetting\('([^']+)',/);
    if (!match) continue;
    const k = match[1];
    let v = inp.value;
    if (inp.type === 'checkbox') v = inp.checked;
    if (inp.tagName === 'SELECT' && v === 'true') v = true;
    else if (inp.tagName === 'SELECT' && v === 'false') v = false;
    await api('/api/config-set', { key: k, value: v });
    count++;
  }
  showToast(count + ' settings saved', 'success');
}

document.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && e.target.tagName !== 'TEXTAREA') {
    const page = document.querySelector('.page.active');
    if (!page) return;
    const btn = page.querySelector('.btn-primary');
    if (btn) btn.click();
  }
});

(function initDropZone() {
  const dropZone = document.getElementById('hashfile-input');
  if (!dropZone) return;
  const container = dropZone.closest('.form-input') || dropZone.parentElement;
  if (!container) return;
  ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(evt =>
    container.addEventListener(evt, e => { e.preventDefault(); e.stopPropagation(); })
  );
  ['dragenter', 'dragover'].forEach(evt =>
    container.addEventListener(evt, () => {
      container.style.borderColor = 'var(--accent, #7c3aed)';
      container.style.background = 'rgba(124,58,237,0.1)';
    })
  );
  ['dragleave', 'drop'].forEach(evt =>
    container.addEventListener(evt, () => { container.style.borderColor = ''; container.style.background = ''; })
  );
  container.addEventListener('drop', (e) => {
    if (e.dataTransfer.files.length > 0) {
      dropZone.files = e.dataTransfer.files;
      hashFileSelected();
    }
  });
})();

(function checkConnection() {
  const dot = document.getElementById('status-dot');
  const text = document.getElementById('status-text');
  async function ping() {
    try {
      const resp = await fetch('/api/config-get', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' });
      if (resp.ok) { if (dot) dot.style.background = '#22c55e'; if (text) text.textContent = 'Connected'; }
      else { if (dot) dot.style.background = '#ef4444'; if (text) text.textContent = 'Error'; }
    } catch (_) { if (dot) dot.style.background = '#ef4444'; if (text) text.textContent = 'Offline'; }
  }
  ping();
  setInterval(ping, 30000);
})();

const doQR = runQR;
const doPassword = runPassword;
const doIPLookup = runIPLookup;
const doDNS = runDNS;
const doWhois = runWhois;
const doUsername = runUsername;
const doPortscan = runPortscan;
const doSubdomain = runSubdomain;
const doSearch = runSearch;
const doAPI = runApiRequest;
const doWebhook = runWebhook;
const doClone = runCloner;
const doObfuscate = runObfuscate;
const doHashFile = runHashFile;
const doRand = runRandom;

async function runUUID() {
  const version = document.getElementById('uuid-version').value;
  const count = parseInt(document.getElementById('uuid-count').value) || 5;
  const data = await api('/api/uuid', { version, count });
  if (data.error) { showError('uuid-result', data.error); showToast(data.error, 'error'); }
  else { showResult('uuid-result', '<div class="result-box mono">' + data.results.map(r => esc(r)).join('\n') + '</div>'); showToast(data.results.length + ' UUIDs generated', 'success'); }
}

async function runTimestampNow() {
  const data = await api('/api/timestamp', { action: 'now' });
  if (data.error) { showError('ts-result', data.error); return; }
  let html = '<table>';
  html += '<tr><td>Unix</td><td class="mono">' + data.unix + '</td></tr>';
  html += '<tr><td>ISO 8601</td><td class="mono">' + esc(data.iso) + '</td></tr>';
  html += '<tr><td>UTC</td><td class="mono">' + esc(data.utc) + '</td></tr>';
  html += '<tr><td>Local</td><td class="mono">' + esc(data.local) + '</td></tr>';
  showResult('ts-result', html + '</table>'); showToast('Current time fetched', 'success');
}

async function runTimestampConvert() {
  const value = document.getElementById('ts-value').value.trim();
  if (!value) { showToast('Enter a Unix timestamp', 'error'); return; }
  const data = await api('/api/timestamp', { action: 'convert', value });
  if (data.error) { showError('ts-result', data.error); showToast(data.error, 'error'); return; }
  let html = '<table>';
  html += '<tr><td>Unix</td><td class="mono">' + data.unix + '</td></tr>';
  html += '<tr><td>ISO 8601</td><td class="mono">' + esc(data.iso) + '</td></tr>';
  html += '<tr><td>UTC</td><td class="mono">' + esc(data.utc) + '</td></tr>';
  html += '<tr><td>Local</td><td class="mono">' + esc(data.local) + '</td></tr>';
  showResult('ts-result', html + '</table>'); showToast('Timestamp converted', 'success');
}

async function runTimestampParse() {
  const value = document.getElementById('ts-value').value.trim();
  if (!value) { showToast('Enter a date string', 'error'); return; }
  const data = await api('/api/timestamp', { action: 'parse', value });
  if (data.error) { showError('ts-result', data.error); showToast(data.error, 'error'); return; }
  let html = '<table>';
  html += '<tr><td>Unix</td><td class="mono">' + data.unix + '</td></tr>';
  html += '<tr><td>ISO 8601</td><td class="mono">' + esc(data.iso) + '</td></tr>';
  html += '<tr><td>UTC</td><td class="mono">' + esc(data.utc) + '</td></tr>';
  showResult('ts-result', html + '</table>'); showToast('Date parsed', 'success');
}

async function runBinary(mode) {
  const text = document.getElementById('binary-text').value;
  if (!text.trim()) { showToast('Enter text or binary', 'error'); return; }
  const data = await api('/api/binary', { text, mode });
  if (data.error) { showError('binary-result', data.error); showToast(data.error, 'error'); }
  else { showResult('binary-result', '<div class="result-box mono">' + esc(data.result) + '</div>'); showToast('Converted', 'success'); }
}

async function runMorse(mode) {
  const text = document.getElementById('morse-text').value;
  if (!text.trim()) { showToast('Enter text or Morse code', 'error'); return; }
  const data = await api('/api/morse', { text, mode });
  if (data.error) { showError('morse-result', data.error); showToast(data.error, 'error'); }
  else { showResult('morse-result', '<div class="result-box mono">' + esc(data.result) + '</div>'); showToast('Morse ' + mode + 'd', 'success'); }
}

async function runColorConvert() {
  const value = document.getElementById('colorconv-value').value.trim();
  const format = document.getElementById('colorconv-format').value;
  if (!value) { showToast('Enter a color value', 'error'); return; }
  const data = await api('/api/color-convert', { value, format });
  if (data.error) { showError('colorconv-result', data.error); showToast(data.error, 'error'); return; }
  let html = '<div style="display:flex;align-items:center;gap:1rem;margin-bottom:8px">' +
    '<div style="width:80px;height:80px;border-radius:12px;background:' + esc(data.hex) + ';border:2px solid var(--border);flex-shrink:0"></div>' +
    '<div><strong>' + esc(data.hex) + '</strong></div></div>';
  html += '<table>';
  html += '<tr><td>HEX</td><td class="mono">' + esc(data.hex) + '</td></tr>';
  html += '<tr><td>RGB</td><td class="mono">' + esc(data.rgb) + '</td></tr>';
  html += '<tr><td>Decimal</td><td class="mono">' + data.decimal + '</td></tr>';
  html += '<tr><td>CSS</td><td class="mono">' + esc(data.css) + '</td></tr>';
  html += '</table>';
  showResult('colorconv-result', html); showToast('Color converted', 'success');
}

async function runLorem() {
  const count = parseInt(document.getElementById('lorem-count').value) || 3;
  const data = await api('/api/lorem', { paragraphs: count });
  if (data.error) { showError('lorem-result', data.error); return; }
  showResult('lorem-result', '<div style="white-space:pre-wrap;line-height:1.8">' + esc(data.text) + '</div>');
  showToast(data.paragraphs + ' paragraphs generated', 'success');
}

async function runDiff() {
  const text1 = document.getElementById('diff-text1').value;
  const text2 = document.getElementById('diff-text2').value;
  if (!text1 && !text2) { showToast('Enter two texts to compare', 'error'); return; }
  const data = await api('/api/diff', { text1, text2 });
  if (data.error) { showError('diff-result', data.error); showToast(data.error, 'error'); return; }
  let html = '<div class="port-summary"><strong>' + data.added + '</strong> added, <strong>' + data.removed + '</strong> removed</div>';
  if (data.diff) {
    const lines = data.diff.split('\n');
    html += '<div class="result-box mono" style="font-size:0.8rem">';
    for (const line of lines) {
      if (line.startsWith('+') && !line.startsWith('+++')) html += '<div style="color:#22c55e;background:rgba(34,197,94,0.1)">' + esc(line) + '</div>';
      else if (line.startsWith('-') && !line.startsWith('---')) html += '<div style="color:#ef4444;background:rgba(239,68,68,0.1)">' + esc(line) + '</div>';
      else if (line.startsWith('@@')) html += '<div style="color:#7c3aed">' + esc(line) + '</div>';
      else html += '<div>' + esc(line) + '</div>';
    }
    html += '</div>';
  } else {
    html += '<div class="msg msg-info">No differences found</div>';
  }
  showResult('diff-result', html); showToast('Diff complete', 'success');
}

async function runHashLookup() {
  const hash = document.getElementById('hashlookup-hash').value.trim();
  const algo = document.getElementById('hashlookup-algo').value;
  if (!hash) { showToast('Enter a hash to look up', 'error'); return; }
  const data = await api('/api/hash-lookup', { hash, algo });
  if (data.error) { showError('hashlookup-result', data.error); showToast(data.error, 'error'); return; }
  let html = '<table>';
  html += '<tr><td>Hash</td><td class="mono">' + esc(data.hash) + '</td></tr>';
  html += '<tr><td>Algorithm</td><td>' + esc(data.algo) + '</td></tr>';
  html += '<tr><td>Length</td><td>' + data.length + ' chars</td></tr>';
  if (data.cracked) {
    html += '<tr><td colspan="2" style="color:var(--green);font-weight:bold">FOUND - ' + data.found.length + ' match(es)</td></tr>';
    for (const f of data.found) html += '<tr><td>Plaintext</td><td class="mono" style="color:var(--green);font-weight:bold">' + esc(f.word) + '</td></tr>';
  } else {
    html += '<tr><td colspan="2" style="color:var(--red)">Not found in common database (' + data.found.length + ' checked)</td></tr>';
  }
  html += '</table>';
  showResult('hashlookup-result', html);
  showToast(data.cracked ? 'Hash cracked!' : 'Not found in database', data.cracked ? 'success' : 'info');
}

const ALL_MODULES = [
  { id: 'home', label: 'Dashboard', icon: '\u{1F3E0}', cat: 'HOME' },
  { id: 'encode', label: 'Encoder/Decoder', icon: '\u{1F510}', cat: 'ENCODING' },
  { id: 'hash', label: 'Hash', icon: '#', cat: 'ENCODING' },
  { id: 'qr', label: 'QR Code', icon: '\u{1F4F1}', cat: 'ENCODING' },
  { id: 'password', label: 'Password Gen', icon: '\u{1F511}', cat: 'ENCODING' },
  { id: 'ip', label: 'IP Lookup', icon: '\u{1F310}', cat: 'RECON' },
  { id: 'dns', label: 'DNS Lookup', icon: '\u{1F4E1}', cat: 'RECON' },
  { id: 'whois', label: 'WHOIS', icon: '\u2261', cat: 'RECON' },
  { id: 'username', label: 'Username Check', icon: '\u{1F464}', cat: 'RECON' },
  { id: 'portscan', label: 'Port Scan', icon: '\u{1F50D}', cat: 'RECON' },
  { id: 'subdomain', label: 'Subdomain Enum', icon: '\u{1F4C2}', cat: 'RECON' },
  { id: 'search', label: 'Web Search', icon: '\u{1F50E}', cat: 'WEB' },
  { id: 'api', label: 'API Request', icon: '\u{1F4E1}', cat: 'WEB' },
  { id: 'webhook', label: 'Webhook', icon: '\u{1F4E4}', cat: 'WEB' },
  { id: 'cloner', label: 'Website Cloner', icon: '\u{1F578}', cat: 'WEB' },
  { id: 'obfuscate', label: 'Obfuscator', icon: '\u{1F6E1}', cat: 'SECURITY' },
  { id: 'hashfile', label: 'Hash File', icon: '\u{1F4C4}', cat: 'SECURITY' },
  { id: 'rand', label: 'Random Gen', icon: '\u{1F3B2}', cat: 'TOOLS' },
  { id: 'colors', label: 'Colors', icon: '\u{1F3A8}', cat: 'TOOLS' },
  { id: 'uuid', label: 'UUID Gen', icon: '\u{1F195}', cat: 'CONVERTERS' },
  { id: 'timestamp', label: 'Timestamp', icon: '\u23F0', cat: 'CONVERTERS' },
  { id: 'binary', label: 'Binary', icon: '\u{1F0CF}', cat: 'CONVERTERS' },
  { id: 'morse', label: 'Morse Code', icon: '\u{1F4E1}', cat: 'CONVERTERS' },
  { id: 'colorconv', label: 'Color Conv', icon: '\u{1F3A8}', cat: 'CONVERTERS' },
  { id: 'lorem', label: 'Lorem Ipsum', icon: '\u{1F4DD}', cat: 'TEXT' },
  { id: 'diff', label: 'Text Diff', icon: '\u2194', cat: 'TEXT' },
  { id: 'hashlookup', label: 'Hash Lookup', icon: '\u{1F510}', cat: 'TEXT' },
  { id: 'settings', label: 'Config', icon: '\u2699', cat: 'TOOLS' },
];

let _moduleConfig = {};

async function loadModuleConfig() {
  const data = await api('/api/module-config', { action: 'get' });
  if (!data.error) _moduleConfig = data.modules || {};
  applyModuleVisibility();
}

function applyModuleVisibility() {
  for (const mod of ALL_MODULES) {
    const btn = document.querySelector('.nav-btn[data-page="' + mod.id + '"]');
    if (btn) btn.style.display = (_moduleConfig[mod.id] === false) ? 'none' : '';
    document.querySelectorAll('.tool-card[onclick*="showPage(\'' + mod.id + '\')"]').forEach(card => {
      card.style.display = (_moduleConfig[mod.id] === false) ? 'none' : '';
    });
    if (btn) {
      const section = btn.closest('.nav-section');
      if (section) {
        const visibleBtns = section.querySelectorAll('.nav-btn');
        let anyVisible = false;
        visibleBtns.forEach(b => { if (b.style.display !== 'none') anyVisible = true; });
        section.style.display = anyVisible ? '' : 'none';
      }
    }
  }
}

function renderModuleToggles() {
  const el = document.getElementById('module-toggles');
  if (!el) return;
  let html = '';
  let currentCat = '';
  for (const mod of ALL_MODULES) {
    if (mod.id === 'home') continue;
    if (mod.cat !== currentCat) {
      if (currentCat) html += '</div>';
      html += '<div style="margin-top:10px;font-size:0.7rem;color:var(--text-dim);text-transform:uppercase;letter-spacing:1px">' + esc(mod.cat) + '</div>';
      html += '<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:6px">';
      currentCat = mod.cat;
    }
    const checked = _moduleConfig[mod.id] !== false ? 'checked' : '';
    html += '<label style="display:flex;align-items:center;gap:6px;padding:6px 8px;border-radius:6px;background:var(--bg-input);border:1px solid var(--border);cursor:pointer;font-size:0.82rem">';
    html += '<input type="checkbox" ' + checked + ' onchange="toggleModule(\'' + mod.id + '\', this.checked)" style="accent-color:var(--accent)">';
    html += '<span>' + mod.icon + '</span><span>' + esc(mod.label) + '</span></label>';
  }
  html += '</div>';
  el.innerHTML = html;
}

function toggleModule(id, visible) {
  _moduleConfig[id] = visible;
}

async function saveModuleConfig() {
  const data = await api('/api/module-config', { action: 'set', modules: _moduleConfig });
  if (data.error) { showToast(data.error, 'error'); return; }
  applyModuleVisibility();
  showToast('Module visibility saved', 'success');
}

async function resetModuleConfig() {
  const data = await api('/api/module-config', { action: 'reset' });
  if (data.error) { showToast(data.error, 'error'); return; }
  _moduleConfig = {};
  renderModuleToggles();
  applyModuleVisibility();
  showToast('All modules visible', 'success');
}

const _origLoadSettings = typeof loadSettings === 'function' ? loadSettings : null;
loadSettings = async function() {
  if (_origLoadSettings) await _origLoadSettings();
  await loadModuleConfig();
  renderModuleToggles();
};

document.addEventListener('DOMContentLoaded', function() {
  loadModuleConfig();
  const mlInput = document.getElementById('subdomain-maxlen');
  if (mlInput) {
    const highlightRow = () => {
      const val = parseInt(mlInput.value) || 3;
      const rows = mlInput.closest('.form-group').querySelectorAll('tr');
      rows.forEach((row, i) => {
        if (i === 0) return;
        row.style.background = i === val ? 'var(--accent-dim, rgba(0,255,65,0.1))' : '';
        row.style.fontWeight = i === val ? 'bold' : '';
      });
    };
    mlInput.addEventListener('input', highlightRow);
    highlightRow();
  }
});

