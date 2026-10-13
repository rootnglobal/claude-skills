/**
 * BbgUniverseSync_v1.gs — jp_model_portfolio 시트 바운드 모듈 (v261013, 별도 파일로 추가 · Code.gs 무수정)
 *
 * 역할 (Layer 0 — BBG PC 덤프 유니버스·감시):
 *   bbgSyncUniverse()      매일 06시: 타깃 ∪ Watchlist → Drive '내 컴퓨터/Bloomberg_Inbox/watchlist.csv' 갱신
 *                          (변경 시에만 덮어씀, Drive 리비전으로 이력 보존) → Drive for desktop이 BBG PC로 내려받음
 *                          → bbg_dump.py 주간 배치(월 07:50)가 읽음. PC 측 Google 자격증명 불필요.
 *   bbgQueuePostEarnings() 매일 07시: 실적일정 탭에서 발표 후 D+2~D+5 종목을 requests/*.req로 1회 투입
 *                          → BBG PC bbg_request_watcher.py(1분 폴링)가 단건 덤프.
 *   bbgHealthCheck()       매일 12시: PC가 쓰는 _bbg_status.json을 읽어 배치 실패·지연·watchlist 미반영을 텔레 알림.
 *                          새 배치 완료 시 1회 요약. 같은 경보는 1회만.
 *   bbgSetupTriggers()     위 3개 트리거 설치(기존 동일 핸들러 제거 후). 설치 후 1회 수동 실행.
 *
 * 텔레그램: OrdersAPI_v1.gs의 ord_tg()가 있으면 그것을 사용, 없으면 Script Property TG_TOKEN/TG_CHAT_ID(또는 CONFIG).
 * 시간대: 프로젝트 시간대 Asia/Seoul 또는 Asia/Tokyo 전제(동일 UTC+9).
 */

const BBG = {
  INBOX_FOLDER_ID: '1S_6f3qBxEoMz2hBRl-U62ljf50fgXbKf',   // 내 컴퓨터 (1)/Bloomberg_Inbox
  REQ_FOLDER_ID:   '1Mx4b4ezeVv6Bvg3Y2VBbBQFhGt_tnIRs',   // Bloomberg_Inbox/requests
  WL_NAME: 'watchlist.csv',
  STATUS_NAME: '_bbg_status.json',
  TABS: ['타깃', 'Watchlist'],                           // 순서 = 덤프 순서
  EARN_TAB: '실적일정',
  MIN_TICKERS: 15,                                       // 이보다 적게 읽히면 파싱 이상으로 보고 미변경
  TICKER_RE: /^\d{3}[0-9A-Z]$/,
  EXCLUDE: [],                                           // 덤프 제외 티커(예: ['1306','1321','2644'])
  DEFAULT_PACK: 'jp_review',
  POST_EARN_MIN: 2, POST_EARN_MAX: 5,                    // 실적 후 D+2~D+5 사이 1회
  STALE_DAYS: 9,                                         // 마지막 성공 배치가 이보다 오래되면 경보
};

/* ---------------- 1) 유니버스 동기화 ---------------- */

function bbgSyncUniverse() {
  const ss = SpreadsheetApp.getActive();
  const seen = new Set(), rows = [];
  BBG.TABS.forEach(tab => {
    const sh = ss.getSheetByName(tab);
    if (!sh) throw new Error('탭 없음: ' + tab);
    const n = sh.getLastRow();
    if (n < 1) return;
    sh.getRange(1, 1, n, 2).getDisplayValues().forEach(r => {
      const t = String(r[0]).trim(), nm = String(r[1]).trim();
      if (!BBG.TICKER_RE.test(t) || seen.has(t) || BBG.EXCLUDE.indexOf(t) >= 0) return;
      seen.add(t); rows.push([t, nm]);
    });
  });
  if (rows.length < BBG.MIN_TICKERS) {
    bbgNotify_('⚠️ BBG 유니버스: 종목 ' + rows.length + '개만 읽힘 — 탭 구조 확인 필요, watchlist.csv 미변경');
    return;
  }
  const file = bbgFindOne_(BBG.WL_NAME);
  if (file === 'DUP') { bbgNotify_('⚠️ BBG 유니버스: ' + BBG.WL_NAME + ' 중복 — 수동 정리 필요, 미변경'); return; }
  const cur = file ? file.getBlob().getDataAsString('UTF-8').replace(/^\uFEFF/, '') : '';

  const prev = {};                                        // code -> {name, pack} (기존 이름·섹터팩 보존)
  cur.split(/\r?\n/).slice(1).forEach(line => {
    if (!line.trim()) return;
    const c = bbgCsvSplit_(line), code = (c[0] || '').split(' ')[0];
    if (code) prev[code] = { name: c[1] || '', pack: c[2] || '' };
  });

  const out = ['ticker,name,sector_pack'], added = [], review = [];
  rows.forEach(([t, nm]) => {
    const p = prev[t];
    const pack = (p && p.pack) || BBG.DEFAULT_PACK;
    const name = (p && p.name) || nm;
    if (!p) added.push(t + ' ' + name);
    if (pack === BBG.DEFAULT_PACK) review.push(t);
    out.push([t + ' JT Equity', bbgCsvCell_(name), pack].join(','));
  });
  const removed = Object.keys(prev).filter(c => !seen.has(c)).map(c => c + ' ' + prev[c].name);
  const body = out.join('\n') + '\n';
  if (body === cur) { Logger.log('bbgSyncUniverse: 변경 없음 (' + rows.length + '종목)'); return; }

  if (file) file.setContent(body);
  else DriveApp.getFolderById(BBG.INBOX_FOLDER_ID).createFile(BBG.WL_NAME, body, MimeType.CSV);
  const msg = ['📋 BBG 덤프 유니버스 갱신: ' + rows.length + '종목 (다음 주간 배치부터 반영)'];
  if (added.length)   msg.push('추가: ' + added.join(', '));
  if (removed.length) msg.push('제외: ' + removed.join(', '));
  if (review.length)  msg.push('sector_pack 미지정(jp_review, Macro 시트만 빔): ' + review.join(', '));
  bbgNotify_(msg.join('\n'));
}

/* ---------------- 2) 실적 후 단건 덤프 요청 ---------------- */

/** 실적일정 탭: A티커, C차기실적일(발표 후엔 발표일), E D-day, J상태('발표됨…') */
function bbgQueuePostEarnings() {
  const sh = SpreadsheetApp.getActive().getSheetByName(BBG.EARN_TAB);
  if (!sh || sh.getLastRow() < 2) return;
  const props = PropertiesService.getScriptProperties();
  const done = JSON.parse(props.getProperty('BBG_EARN_QUEUED') || '{}');   // {ticker: 발표일}
  const reqFolder = DriveApp.getFolderById(BBG.REQ_FOLDER_ID);
  const queued = [];
  sh.getRange(2, 1, sh.getLastRow() - 1, 10).getDisplayValues().forEach(r => {
    const t = String(r[0]).trim(), annDt = String(r[2]).trim(), dday = Number(r[4]), st = String(r[9]);
    if (!BBG.TICKER_RE.test(t) || st.indexOf('발표됨') !== 0 || isNaN(dday)) return;
    const after = -dday;
    if (after < BBG.POST_EARN_MIN || after > BBG.POST_EARN_MAX || done[t] === annDt) return;
    const name = t + '_JT_Equity.req';
    if (!reqFolder.getFilesByName(name).hasNext()) reqFolder.createFile(name, t + ' JT Equity\n', MimeType.PLAIN_TEXT);
    done[t] = annDt; queued.push(t);
  });
  if (queued.length) {
    props.setProperty('BBG_EARN_QUEUED', JSON.stringify(done));
    bbgNotify_('📥 실적 후 BBG 단건 덤프 요청: ' + queued.join(', '));
  }
}

/* ---------------- 3) 헬스체크 ---------------- */

function bbgHealthCheck() {
  const f = bbgFindOne_(BBG.STATUS_NAME);
  if (!f || f === 'DUP') {
    bbgAlertOnce_('nostatus', '⚠️ BBG: ' + BBG.STATUS_NAME + ' 없음 — BBG PC에 새 bbg_dump.py가 아직 반영/실행되지 않음' +
      ' (Drive→PC 동기화 또는 PC 꺼짐 확인)');
    return;
  }
  let st;
  try { st = JSON.parse(f.getBlob().getDataAsString('UTF-8')); }
  catch (e) { bbgAlertOnce_('badjson', '⚠️ BBG: 상태파일 파싱 실패 — ' + e); return; }

  const now = new Date();
  const days = iso => iso ? Math.floor((now - new Date(iso)) / 86400000) : 999;
  if ((st.result === 'terminal_down' || st.result === 'aborted') && days(st.last_attempt) <= 2) {
    bbgAlertOnce_('fail:' + st.last_attempt, '⚠️ BBG 주간 배치 ' + (st.result === 'terminal_down' ? '실패(터미널 미접속 3시간)' : '중단(도중 끊김)') +
      ' — ' + st.last_attempt + '. 다음 평일 07:50 자동 재시도. 성공 ' + (st.ok || 0) + '종목');
  }
  if (days(st.last_full_batch) > BBG.STALE_DAYS) {
    bbgAlertOnce_('stale:' + st.last_full_batch, '⚠️ BBG 주간 배치 ' + BBG.STALE_DAYS + '일+ 미실행 (마지막 ' +
      (st.last_full_batch || '없음') + ') — BBG PC·터미널·작업 스케줄러 확인');
  }
  const wl = bbgFindOne_(BBG.WL_NAME);
  if (wl && wl !== 'DUP' && st.last_attempt) {
    const n = wl.getBlob().getDataAsString('UTF-8').split(/\r?\n/).filter(l => l.trim()).length - 1;
    if (n !== st.watchlist_n && new Date(st.last_attempt) - wl.getLastUpdated() > 3600000) {
      bbgAlertOnce_('wl:' + st.last_attempt, '⚠️ BBG: PC가 읽은 watchlist ' + st.watchlist_n + '종목 ≠ Drive ' + n +
        '종목 — Drive→PC 동기화 미반영. BBG PC의 C:\\Bloomberg_Inbox\\watchlist.csv를 Drive 파일로 수동 교체');
    }
  }
  if (st.result === 'ok' && st.last_full_batch && days(st.last_full_batch) <= 1) {
    const extra = (st.empty || []).length ? '\n무데이터: ' + st.empty.join(', ') : '';
    bbgAlertOnce_('ok:' + st.last_full_batch, '✅ BBG 주간 덤프 완료 ' + st.last_full_batch + ': ' + st.ok + '/' +
      st.watchlist_n + '종목' + extra);
  }
}

function bbgSetupTriggers() {
  const handlers = ['bbgSyncUniverse', 'bbgQueuePostEarnings', 'bbgHealthCheck'];
  ScriptApp.getProjectTriggers()
    .filter(tr => handlers.indexOf(tr.getHandlerFunction()) >= 0)
    .forEach(tr => ScriptApp.deleteTrigger(tr));
  ScriptApp.newTrigger('bbgSyncUniverse').timeBased().everyDays(1).atHour(6).create();      // 월 07:50 배치 전
  ScriptApp.newTrigger('bbgQueuePostEarnings').timeBased().everyDays(1).atHour(7).create();
  ScriptApp.newTrigger('bbgHealthCheck').timeBased().everyDays(1).atHour(12).create();      // probe 재시도 3시간 이후
  bbgNotify_('🔧 BBG 트리거 설치: 유니버스 06시 · 실적후 큐 07시 · 헬스체크 12시 (매일)');
}

/* ---------------- 유틸 ---------------- */

function bbgFindOne_(name) {
  const it = DriveApp.getFolderById(BBG.INBOX_FOLDER_ID).getFilesByName(name), fs = [];
  while (it.hasNext()) fs.push(it.next());
  return fs.length > 1 ? 'DUP' : (fs[0] || null);
}

function bbgAlertOnce_(key, msg) {
  const p = PropertiesService.getScriptProperties();
  const sent = JSON.parse(p.getProperty('BBG_HEALTH_SENT') || '[]');
  if (sent.indexOf(key) >= 0) return;
  bbgNotify_(msg);
  sent.push(key);
  p.setProperty('BBG_HEALTH_SENT', JSON.stringify(sent.slice(-30)));
}

function bbgNotify_(msg) {
  Logger.log(msg);
  if (typeof ord_tg === 'function') { ord_tg(msg); return; }      // OrdersAPI_v1.gs 헬퍼 재사용
  const p = PropertiesService.getScriptProperties();
  let tok = p.getProperty('TG_TOKEN'), chat = p.getProperty('TG_CHAT_ID');
  if ((!tok || !chat) && typeof CONFIG !== 'undefined') { tok = tok || CONFIG.TG_TOKEN; chat = chat || CONFIG.TG_CHAT_ID; }
  if (!tok || !chat) return;
  try {
    UrlFetchApp.fetch('https://api.telegram.org/bot' + tok + '/sendMessage', {
      method: 'post', muteHttpExceptions: true, payload: { chat_id: chat, text: msg },
    });
  } catch (e) { Logger.log('텔레 실패: ' + e); }
}

function bbgCsvSplit_(line) {
  const out = []; let cur = '', q = false;
  for (let i = 0; i < line.length; i++) {
    const ch = line[i];
    if (q) { if (ch === '"' && line[i + 1] === '"') { cur += '"'; i++; } else if (ch === '"') q = false; else cur += ch; }
    else if (ch === '"') q = true; else if (ch === ',') { out.push(cur); cur = ''; } else cur += ch;
  }
  out.push(cur); return out;
}

function bbgCsvCell_(s) { return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s; }
