/***********************************************************************
 * OrdersAPI_v1.gs — RootN JP 모델포트 모바일 주문 모듈  v1.0 (2026-08-04)
 *
 * 목적
 *   폰에서 (a) 텔레그램 챗 직접, (b) 클로드 세션(웹앱 API) 두 경로로
 *   거래를 생성하고, 텔레그램 토큰 회신으로 2차 검증 후 거래입력에 기록.
 *
 * 설치 (기존 Code.gs는 건드리지 않음 — 별도 파일)
 *   1) Apps Script 편집기 > 파일 추가 > 이 내용 붙여넣기 (파일명 OrdersAPI_v1)
 *   2) 기존 프로젝트에 doPost가 이미 있으면 아래 doPost를 doPost_ord로 개명 후
 *      기존 doPost에서 위임 호출 추가 (없으면 그대로)
 *   3) 배포 > 배포 관리 > 웹앱 액세스: "모든 사용자(익명 포함)" 로 재배포
 *      (보안: SECRET + 텔레그램 토큰 2FA로 보호 — 아래 보안 노트)
 *   4) 편집기에서 ord_setup() 1회 실행 → 권한 승인
 *      → 1분 폴링 트리거 설치 + SECRET 생성 + Drive에 접속정보 파일 자동 생성
 *   5) (권장) ord_setConfirmFn('함수명') — Code.gs의 [★거래 확정] 메뉴 함수명 지정.
 *      onOpen()의 addItem('★거래 확정', '여기함수명') 에서 확인.
 *      지정 시 주문 확정 직후 기존 확정 파이프라인(로그·알림·TWAP대기)까지 자동.
 *      미지정/실패 시: 행은 "확정 대기"로 남고 텔레로 수동확정 필요 안내(fail-safe).
 *
 * 보안 노트
 *   - SECRET이 유출돼도 거래 실행 불가: 실행은 오직 등록된 TG_CHAT_ID 사용자가
 *     텔레그램에서 "확인 <토큰>" 을 회신해야 함 (봇 자신의 메시지는 getUpdates에
 *     잡히지 않으므로 봇/외부가 확인을 위조할 수 없음).
 *   - doPost는 주문 준비(prepare)·조회(status)만 가능, 확정 엔드포인트 없음.
 *
 * 텔레그램 명령 (사용자가 봇 챗에 직접 입력)
 *   주문 6981 +0.5            비중 +0.5%p 매수 (음수면 매도)
 *   주문 6981 +0.5, 7532 +0.5  여러 건 쉼표/줄바꿈 구분
 *   주문 6981 +0.5 고정가 6900  고정가 체결(TWAP 보정 제외)
 *   청산 7532                 전량매도 (현재비중을 음수로 자동 계산)
 *   신규 9983 +1.0            유니버스 밖 신규 편입 (Watchlist 자동 추가)
 *   확인 123456               토큰 회신 → 실제 거래 기록
 *   취소 / 상태 / 도움말
 ***********************************************************************/

var ORD = {
  SHEET_TRADE: '거래입력',
  SHEET_PORT1: '모델포트1',
  SHEET_TARGET: '타깃',
  SHEET_WATCH: 'Watchlist',
  PORT1_DATA_START: 9,      // 홀딩스 9행~
  COL: { DATE:1, TICKER:2, NAME:3, PRICE:4, DELTA:5, MODE:13, CONFIRM:14, INTIME:15, MEMO:16 },
  PORT1_COL: { TICKER:1, PRICE:6, WEIGHT:8 },  // F 현재가, H 현재비중
  MAX_DELTA_DEFAULT: 3.0,   // |Δ%p| 상한 (Script Property ORD_MAX_DELTA로 변경)
  TOKEN_TTL_MIN: 10,
  DRIVE_CRED_FILE: 'rootn_jp_port_orders_api.txt',
  VERSION: 'v1.0'
};

/* ---------------- 설치 ---------------- */

function ord_setup() {
  var props = PropertiesService.getScriptProperties();
  if (!props.getProperty('ORD_SECRET')) {
    var bytes = Utilities.getUuid() + Utilities.getUuid();
    props.setProperty('ORD_SECRET', bytes.replace(/-/g, ''));
  }
  // 폴링 트리거 재설치 (중복 제거)
  ScriptApp.getProjectTriggers().forEach(function (t) {
    if (t.getHandlerFunction() === 'ord_poll') ScriptApp.deleteTrigger(t);
  });
  ScriptApp.newTrigger('ord_poll').timeBased().everyMinutes(1).create();

  // Drive 접속정보 파일 생성/갱신 (클로드 세션이 읽는 SSOT)
  var url = '';
  try { url = ScriptApp.getService().getUrl() || ''; } catch (e) {}
  var content = 'JP_PORT_ORDERS_API\nurl=' + url +
    '\nsecret=' + props.getProperty('ORD_SECRET') +
    '\nversion=' + ORD.VERSION + '\nupdated=' + ord_now() +
    '\n(주의: 웹앱 재배포로 URL이 바뀌면 ord_setup 재실행)';
  var it = DriveApp.getFilesByName(ORD.DRIVE_CRED_FILE);
  if (it.hasNext()) { it.next().setContent(content); }
  else { DriveApp.createFile(ORD.DRIVE_CRED_FILE, content, MimeType.PLAIN_TEXT); }

  ord_tg('🔧 OrdersAPI ' + ORD.VERSION + ' 설치 완료.\n웹앱 URL ' +
    (url ? '등록됨' : '미등록(배포 후 ord_setup 재실행)') +
    '\n확정 위임 함수: ' + (props.getProperty('ORD_CONFIRM_FN') || '미지정(수동확정 모드)') +
    '\n"도움말" 입력 시 명령 안내.');
  Logger.log('설치 완료. Drive 파일: ' + ORD.DRIVE_CRED_FILE + ' / URL: ' + (url || '미등록'));
}

function ord_setConfirmFn(name) {
  if (name && typeof this[name] !== 'function')
    throw new Error('함수 "' + name + '" 를 찾을 수 없음. onOpen 메뉴 정의에서 확인.');
  PropertiesService.getScriptProperties().setProperty('ORD_CONFIRM_FN', name || '');
  Logger.log('확정 위임 함수 = ' + (name || '(해제)'));
}

/* ---------------- 텔레그램 폴링 ---------------- */

function ord_poll() {
  var creds = ord_tgCreds(); if (!creds) return;
  var props = PropertiesService.getScriptProperties();
  var offset = Number(props.getProperty('ORD_TG_OFFSET') || 0);
  var resp;
  try {
    resp = UrlFetchApp.fetch('https://api.telegram.org/bot' + creds.token +
      '/getUpdates?timeout=0&offset=' + (offset + 1), { muteHttpExceptions: true });
  } catch (e) { return; }
  var data = JSON.parse(resp.getContentText() || '{}');
  if (!data.ok || !data.result || !data.result.length) return;
  data.result.forEach(function (u) {
    offset = Math.max(offset, u.update_id);
    var m = u.message;
    if (!m || !m.text) return;
    if (String(m.chat.id) !== String(creds.chat)) return;  // 등록된 챗만
    try { ord_handleText(m.text.trim()); }
    catch (e) { ord_tg('⚠ 처리 오류: ' + e.message); }
  });
  props.setProperty('ORD_TG_OFFSET', String(offset));
}

function ord_handleText(text) {
  var head = text.split(/\s/)[0];
  if (/^(확인)$/.test(head)) return ord_confirm(text.replace(/^확인\s*/, '').trim());
  if (/^\d{6}$/.test(text)) return ord_tg('토큰은 "확인 ' + text + '" 형식으로 회신해 주세요(오입력 방지).');
  if (head === '취소') return ord_cancelPending();
  if (head === '상태') return ord_tg(ord_statusText());
  if (head === '도움말') return ord_tg(ord_helpText());
  if (/^(주문|매수|매도|청산|신규)$/.test(head)) {
    var parsed = ord_parseOrders(text);
    if (parsed.errors.length) return ord_tg('⚠ 주문 해석 실패:\n' + parsed.errors.join('\n'));
    return ord_prepare(parsed.orders, 'telegram');
  }
  // 그 외 텍스트는 무시 (브리핑 챗 겸용 대비)
}

/* ---------------- 주문 파싱·검증 ---------------- */

function ord_parseOrders(text) {
  var orders = [], errors = [];
  // 명령 키워드 단위로 분해, 각 명령 내 쉼표/줄바꿈으로 복수 종목
  var segs = text.split(/[,\n;]+/).map(function (s) { return s.trim(); }).filter(String);
  var curCmd = null;
  segs.forEach(function (seg) {
    var m = seg.match(/^(주문|매수|매도|청산|신규)?\s*([0-9A-Za-z]{4,5})(?:\s+([+\-]?\d+(?:\.\d+)?))?(?:\s+고정가\s*(\d+(?:\.\d+)?))?$/);
    if (!m) { errors.push('해석 불가: "' + seg + '"'); return; }
    curCmd = m[1] || curCmd;
    if (!curCmd) { errors.push('명령 키워드 없음: "' + seg + '"'); return; }
    var o = { cmd: curCmd, ticker: m[2].toUpperCase(), delta: m[3] !== undefined ? Number(m[3]) : null, fixPrice: m[4] ? Number(m[4]) : null };
    if (o.cmd === '매수' || o.cmd === '매도') o.cmd = '주문';
    if (o.cmd !== '청산' && o.delta === null) { errors.push(o.ticker + ': Δ%p 누락'); return; }
    orders.push(o);
  });
  if (!orders.length && !errors.length) errors.push('주문 내용 없음');
  return { orders: orders, errors: errors };
}

function ord_validate(orders) {
  var maxD = Number(PropertiesService.getScriptProperties().getProperty('ORD_MAX_DELTA') || ORD.MAX_DELTA_DEFAULT);
  var hold = ord_holdings();          // {ticker: {price, weight}}
  var universe = ord_targetTickers(); // Set-like {}
  var out = [], errors = [];
  orders.forEach(function (o) {
    var held = hold[o.ticker];
    if (o.cmd === '청산') {
      if (!held || !held.weight) { errors.push(o.ticker + ': 미보유 — 청산 불가'); return; }
      o.delta = -Math.round(held.weight * 10000) / 100; // 현재비중 %p 음수
    }
    if (o.cmd === '신규') {
      if (held || universe[o.ticker]) o.cmd = '주문'; // 이미 있으면 일반 주문으로
    } else if (o.cmd === '주문') {
      if (!held && !universe[o.ticker]) { errors.push(o.ticker + ': 타깃/보유에 없음 — "신규 ' + o.ticker + ' Δ%" 로 입력'); return; }
    }
    if (Math.abs(o.delta) > maxD && o.cmd !== '청산') {
      errors.push(o.ticker + ': |Δ|=' + o.delta + '%p > 상한 ' + maxD + '%p (ORD_MAX_DELTA 속성으로 조정)'); return;
    }
    if (o.delta < 0 && held && (-o.delta) > held.weight * 100 + 0.01) {
      errors.push(o.ticker + ': 매도 ' + (-o.delta) + '%p > 보유 ' + (held.weight * 100).toFixed(2) + '%p (롱온리)'); return;
    }
    if (o.delta === 0) { errors.push(o.ticker + ': Δ=0'); return; }
    // 체결가(잠정)
    o.price = o.fixPrice || (held ? held.price : ord_yahooPrice(o.ticker));
    if (!o.price) { errors.push(o.ticker + ': 가격 조회 실패 — "고정가 NNNN" 붙여 재시도'); return; }
    o.name = held ? held.name : '';
    o.isNew = (o.cmd === '신규');
    out.push(o);
  });
  return { orders: out, errors: errors };
}

/* ---------------- 준비(토큰 발송) → 확인 → 실행 ---------------- */

function ord_prepare(rawOrders, source) {
  var v = ord_validate(rawOrders);
  if (v.errors.length) {
    var msg = '⚠ 주문 거절:\n' + v.errors.join('\n');
    ord_tg(msg); return { ok: false, errors: v.errors };
  }
  var token = String(Math.floor(100000 + Math.random() * 900000));
  var pending = { token: token, ts: Date.now(), source: source || 'api', orders: v.orders };
  PropertiesService.getScriptProperties().setProperty('ORD_PENDING', JSON.stringify(pending));
  var lines = v.orders.map(function (o) {
    return '· ' + o.ticker + (o.name ? ' ' + o.name : '') + '  Δ ' + (o.delta > 0 ? '+' : '') + o.delta +
      '%p  @' + o.price + (o.fixPrice ? '(고정가)' : '(잠정→TWAP)') + (o.isNew ? '  [신규편입]' : '') +
      (o.cmd === '청산' ? '  [전량매도]' : '');
  });
  ord_tg('📋 주문 확인 요청 (' + pending.source + ')\n' + lines.join('\n') +
    '\n\n실행하려면 ' + ORD.TOKEN_TTL_MIN + '분 내 회신:\n확인 ' + token);
  return { ok: true, preview: lines, note: '토큰을 텔레그램으로 발송함. "확인 <토큰>" 회신 시 실행.' };
}

function ord_confirm(token) {
  var props = PropertiesService.getScriptProperties();
  var raw = props.getProperty('ORD_PENDING');
  if (!raw) return ord_tg('대기 중인 주문이 없습니다.');
  var p = JSON.parse(raw);
  if (Date.now() - p.ts > ORD.TOKEN_TTL_MIN * 60 * 1000) {
    props.deleteProperty('ORD_PENDING');
    return ord_tg('⏱ 토큰 만료(' + ORD.TOKEN_TTL_MIN + '분). 주문을 다시 입력해 주세요.');
  }
  if (String(token) !== String(p.token)) return ord_tg('❌ 토큰 불일치. 다시 확인해 주세요.');
  props.deleteProperty('ORD_PENDING');
  ord_execute(p.orders);
}

function ord_cancelPending() {
  PropertiesService.getScriptProperties().deleteProperty('ORD_PENDING');
  ord_tg('대기 주문 취소됨.');
}

function ord_execute(orders) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sh = ss.getSheetByName(ORD.SHEET_TRADE);
  var lastRow = ord_lastDataRow(sh, ORD.COL.DATE);
  var today = new Date(); today.setHours(0, 0, 0, 0);
  var nowStamp = new Date();
  var written = [];
  orders.forEach(function (o, i) {
    var r = lastRow + 1 + i;
    sh.getRange(r, ORD.COL.DATE).setValue(today);
    sh.getRange(r, ORD.COL.TICKER).setNumberFormat('@').setValue(String(o.ticker));
    sh.getRange(r, ORD.COL.PRICE).setValue(o.price);
    sh.getRange(r, ORD.COL.DELTA).setNumberFormat('0.00%').setValue(o.delta / 100);
    if (o.fixPrice) sh.getRange(r, ORD.COL.MODE).setValue('고정가');
    sh.getRange(r, ORD.COL.INTIME).setNumberFormat('yyyy-mm-dd hh:mm:ss').setValue(nowStamp);
    sh.getRange(r, ORD.COL.MEMO).setValue('TG주문 ✓토큰검증' + (o.isNew ? ' 신규편입' : '') + (o.cmd === '청산' ? ' 전량매도' : ''));
    if (o.isNew) ord_addWatchlist(o.ticker);
    written.push(o.ticker + ' Δ' + (o.delta > 0 ? '+' : '') + o.delta + '%p @' + o.price + ' (행 ' + r + ')');
  });
  SpreadsheetApp.flush();

  // 기존 [★거래 확정] 파이프라인 위임 (로그·알림·TWAP대기)
  var fn = PropertiesService.getScriptProperties().getProperty('ORD_CONFIRM_FN');
  var confirmed = false, note = '';
  if (fn && typeof this[fn] === 'function') {
    try { this[fn](); confirmed = true; }
    catch (e) { note = '확정 위임 실패(' + e.message + ')'; }
  } else note = '확정 함수 미지정';
  ord_tg('✅ 거래입력 기록 완료\n' + written.join('\n') +
    (confirmed ? '\n★거래 확정까지 자동 완료(로그·TWAP대기 포함).'
               : '\n⚠ ' + note + ' — 행은 "확정 대기" 상태. 데스크톱 [모델포트]>★거래 확정 필요. (입력시각 기준 TWAP은 유지됨)'));
}

/* ---------------- 웹앱 (클로드 세션용) ---------------- */
/* 기존 프로젝트에 doPost가 이미 있으면 이 함수를 doPost_ord로 개명하고
   기존 doPost 안에서 위임하도록 한 줄 추가할 것. */
function doPost(e) {
  var out = ContentService.createTextOutput().setMimeType(ContentService.MimeType.JSON);
  var body;
  try { body = JSON.parse(e.postData.contents); }
  catch (err) { return out.setContent(JSON.stringify({ ok: false, error: 'bad json' })); }
  var secret = PropertiesService.getScriptProperties().getProperty('ORD_SECRET');
  if (!secret || body.secret !== secret) return out.setContent(JSON.stringify({ ok: false, error: 'auth' }));

  var res;
  try {
    switch (body.action) {
      case 'ping': res = { ok: true, version: ORD.VERSION }; break;
      case 'status': res = { ok: true, status: ord_statusText() }; break;
      case 'prepare':
        // orders: [{cmd:'주문'|'청산'|'신규', ticker:'6981', delta:+0.5, fixPrice:6900(optional)}]
        var parsed = (body.orders || []).map(function (o) {
          return { cmd: o.cmd || '주문', ticker: String(o.ticker).toUpperCase(), delta: o.delta != null ? Number(o.delta) : null, fixPrice: o.fixPrice ? Number(o.fixPrice) : null };
        });
        res = ord_prepare(parsed, 'claude-api');
        break;
      default: res = { ok: false, error: 'unknown action' };
    }
  } catch (err) { res = { ok: false, error: err.message }; }
  return out.setContent(JSON.stringify(res));
}

/* ---------------- 시트 조회 헬퍼 ---------------- */

function ord_holdings() {
  var sh = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(ORD.SHEET_PORT1);
  var last = sh.getLastRow();
  var map = {};
  if (last < ORD.PORT1_DATA_START) return map;
  var vals = sh.getRange(ORD.PORT1_DATA_START, 1, last - ORD.PORT1_DATA_START + 1, 8).getValues();
  vals.forEach(function (row) {
    var t = String(row[ORD.PORT1_COL.TICKER - 1]).trim().toUpperCase();
    if (!t || t === '현금' || t === 'CASH') return;
    var w = Number(row[ORD.PORT1_COL.WEIGHT - 1]) || 0;
    if (!/^[0-9A-Z]{4,5}$/.test(t)) return;
    map[t] = { price: Number(row[ORD.PORT1_COL.PRICE - 1]) || 0, weight: w, name: String(row[1] || '') };
  });
  return map;
}

function ord_targetTickers() {
  var sh = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(ORD.SHEET_TARGET);
  var vals = sh.getRange(1, 1, sh.getLastRow(), 1).getValues();
  var set = {};
  vals.forEach(function (r) {
    var t = String(r[0]).trim().toUpperCase();
    if (/^[0-9A-Z]{4,5}$/.test(t) && t !== '티커') set[t] = true;
  });
  return set;
}

function ord_addWatchlist(ticker) {
  try {
    var sh = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(ORD.SHEET_WATCH);
    if (!sh) return;
    var vals = sh.getRange(1, 1, sh.getLastRow() || 1, 1).getValues().map(function (r) { return String(r[0]).trim().toUpperCase(); });
    if (vals.indexOf(ticker) >= 0) return;
    sh.getRange(ord_lastDataRow(sh, 1) + 1, 1).setNumberFormat('@').setValue(ticker);
  } catch (e) {}
}

function ord_lastDataRow(sh, col) {
  var vals = sh.getRange(1, col, sh.getMaxRows(), 1).getValues();
  for (var i = vals.length - 1; i >= 0; i--) if (String(vals[i][0]).trim() !== '') return i + 1;
  return 1;
}

function ord_statusText() {
  var props = PropertiesService.getScriptProperties();
  var raw = props.getProperty('ORD_PENDING');
  var s = '📊 주문 상태 (' + ord_now() + ')\n';
  s += raw ? '대기 중 주문 있음 (토큰 미확인, ' + JSON.parse(raw).orders.length + '건)\n' : '대기 주문 없음\n';
  var sh = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(ORD.SHEET_TRADE);
  var last = ord_lastDataRow(sh, ORD.COL.DATE);
  var today = Utilities.formatDate(new Date(), Session.getScriptTimeZone(), 'yyyy-MM-dd');
  var lines = [];
  for (var r = Math.max(2, last - 14); r <= last; r++) {
    var v = sh.getRange(r, 1, 1, 16).getValues()[0];
    if (!v[0]) continue;
    var d = (v[0] instanceof Date) ? Utilities.formatDate(v[0], Session.getScriptTimeZone(), 'yyyy-MM-dd') : String(v[0]);
    if (d !== today) continue;
    lines.push('· ' + v[1] + ' Δ' + (Math.round(Number(v[4]) * 10000) / 100) + '%p @' + v[3] + (v[13] ? ' [확정]' : ' [확정대기]'));
  }
  s += lines.length ? '오늘 거래:\n' + lines.join('\n') : '오늘 거래 없음';
  return s;
}

function ord_helpText() {
  return '📱 모바일 주문 명령\n' +
    '주문 6981 +0.5  (여러 건: 쉼표 구분)\n청산 7532\n신규 9983 +1.0\n' +
    '주문 6981 +0.5 고정가 6900\n확인 <토큰> / 취소 / 상태\n' +
    'Δ는 NAV 대비 %p, 매도는 음수. 상한 ±' +
    (PropertiesService.getScriptProperties().getProperty('ORD_MAX_DELTA') || ORD.MAX_DELTA_DEFAULT) + '%p.';
}

/* ---------------- 유틸 ---------------- */

function ord_tgCreds() {
  var props = PropertiesService.getScriptProperties();
  var token = props.getProperty('TG_TOKEN'), chat = props.getProperty('TG_CHAT_ID');
  if ((!token || !chat) && typeof CONFIG !== 'undefined') {
    token = token || CONFIG.TG_TOKEN; chat = chat || CONFIG.TG_CHAT_ID;
  }
  return (token && chat) ? { token: token, chat: chat } : null;
}

function ord_tg(text) {
  var c = ord_tgCreds(); if (!c) return;
  try {
    UrlFetchApp.fetch('https://api.telegram.org/bot' + c.token + '/sendMessage', {
      method: 'post', payload: { chat_id: c.chat, text: text }, muteHttpExceptions: true
    });
  } catch (e) {}
}

function ord_yahooPrice(ticker) {
  try {
    var url = 'https://query1.finance.yahoo.com/v8/finance/chart/' + encodeURIComponent(ticker) + '.T?range=1d&interval=5m';
    var resp = UrlFetchApp.fetch(url, { muteHttpExceptions: true, headers: { 'User-Agent': 'Mozilla/5.0' } });
    var j = JSON.parse(resp.getContentText());
    return Number(j.chart.result[0].meta.regularMarketPrice) || 0;
  } catch (e) { return 0; }
}

function ord_now() {
  return Utilities.formatDate(new Date(), Session.getScriptTimeZone(), 'yyyy-MM-dd HH:mm');
}
