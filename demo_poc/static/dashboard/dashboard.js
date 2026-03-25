/* global mqtt, Chart */
(function () {
  const $ = (id) => document.getElementById(id);

  const palette = ['#2ef2ff', '#ff2ecb', '#7cff7c', '#ffd000', '#b388ff', '#ff9f43'];
  const topicToDatasetIndex = {};
  let chart;
  let client;
  let idb;
  let persistTimer;
  const seriesMap = {};

  function log(line) {
    const box = $('logBox');
    const t = new Date().toISOString().slice(11, 23);
    box.textContent = `[${t}] ${line}\n` + box.textContent.slice(0, 8000);
  }

  function openIdb() {
    return new Promise((resolve, reject) => {
      const req = indexedDB.open('opc_mqtt_demo', 1);
      req.onupgradeneeded = (e) => {
        const db = e.target.result;
        if (!db.objectStoreNames.contains('series')) {
          db.createObjectStore('series', { keyPath: 'topic' });
        }
      };
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error);
    });
  }

  function idbPut(topic, points) {
    if (!idb) return;
    const tx = idb.transaction('series', 'readwrite');
    tx.objectStore('series').put({ topic, points });
  }

  function schedulePersist() {
    clearTimeout(persistTimer);
    persistTimer = setTimeout(() => {
      Object.keys(seriesMap).forEach((topic) => {
        idbPut(topic, seriesMap[topic].points);
      });
    }, 800);
  }

  function getMaxPoints() {
    const n = parseInt($('maxPoints').value, 10);
    return Number.isFinite(n) ? Math.min(50000, Math.max(50, n)) : 2000;
  }

  function ensureDataset(topic) {
    if (topicToDatasetIndex[topic] !== undefined) return topicToDatasetIndex[topic];
    const idx = chart.data.datasets.length;
    const color = palette[idx % palette.length];
    chart.data.datasets.push({
      label: topic,
      borderColor: color,
      backgroundColor: color + '33',
      data: [],
      parsing: false,
      pointRadius: 0,
      borderWidth: 2,
      tension: 0.15,
    });
    topicToDatasetIndex[topic] = idx;
    seriesMap[topic] = { points: [], color };
    return idx;
  }

  function trimDataset(ds) {
    const max = getMaxPoints();
    while (ds.data.length > max) ds.data.shift();
  }

  function onPayload(topic, payloadStr) {
    let payload;
    try {
      payload = JSON.parse(payloadStr);
    } catch {
      log(`non-JSON on ${topic}`);
      return;
    }
    const ts = typeof payload.ts === 'number' ? payload.ts : Date.now();
    const val = payload.value;
    const y = typeof val === 'number' ? val : parseFloat(val);
    if (!Number.isFinite(y)) return;

    const dsIdx = ensureDataset(topic);
    const ds = chart.data.datasets[dsIdx];
    ds.data.push({ x: ts, y });
    trimDataset(ds);

    const arr = seriesMap[topic].points;
    arr.push({ t: ts, y });
    while (arr.length > getMaxPoints()) arr.shift();

    chart.update('none');
    schedulePersist();

    const grid = $('valueGrid');
    let card = [...grid.querySelectorAll('.value-card')].find((el) => el.dataset.topicFull === topic);
    if (!card) {
      card = document.createElement('div');
      card.className = 'value-card';
      card.dataset.topicFull = topic;
      card.innerHTML = '<div class="t"></div><div class="v"></div>';
      grid.appendChild(card);
    }
    card.querySelector('.t').textContent = topic;
    card.querySelector('.v').textContent = String(y);
  }

  function initChart() {
    const ctx = $('liveChart').getContext('2d');
    chart = new Chart(ctx, {
      type: 'line',
      data: { datasets: [] },
      options: {
        animation: false,
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: 'nearest', intersect: false },
        scales: {
          x: {
            type: 'linear',
            title: { display: true, text: 'Time (ms since epoch)' },
            grid: { color: 'rgba(120,200,255,0.08)' },
            ticks: { color: '#8aa' },
          },
          y: {
            title: { display: true, text: 'Value' },
            grid: { color: 'rgba(120,200,255,0.08)' },
            ticks: { color: '#8aa' },
          },
        },
        plugins: {
          legend: {
            labels: { color: '#cfe6ff' },
          },
        },
      },
    });
  }

  function setConnected(ok) {
    const pill = $('connPill');
    pill.textContent = ok ? 'Connected' : 'Disconnected';
    pill.classList.toggle('ok', ok);
  }

  async function connect() {
    const url = $('wsUrl').value.trim();
    const pat = $('topicPat').value.trim() || 'opc/#';
    if (client) {
      try {
        client.end(true);
      } catch (_) {}
      client = null;
    }
    log(`Connecting ${url} …`);
    client = mqtt.connect(url, {
      protocolVersion: 4,
      clientId: 'web_' + Math.random().toString(16).slice(2),
      reconnectPeriod: 3000,
    });
    client.on('connect', () => {
      setConnected(true);
      log(`Subscribed ${pat}`);
      client.subscribe(pat, (err) => {
        if (err) log('Subscribe error: ' + err);
      });
    });
    client.on('message', (topic, buf) => {
      onPayload(topic, buf.toString());
    });
    client.on('error', (e) => {
      log('MQTT error: ' + (e && e.message ? e.message : e));
    });
    client.on('close', () => setConnected(false));
    client.on('offline', () => setConnected(false));
  }

  function disconnect() {
    if (client) {
      try {
        client.end(true);
      } catch (_) {}
      client = null;
    }
    setConnected(false);
    log('Disconnected');
  }

  function exportCsv() {
    const rows = [['topic', 't_ms', 'y']];
    Object.keys(seriesMap).forEach((topic) => {
      seriesMap[topic].points.forEach((p) => rows.push([topic, p.t, p.y]));
    });
    const csv = rows.map((r) => r.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(',')).join('\n');
    downloadBlob('opc_export.csv', csv, 'text/csv');
  }

  function exportJson() {
    const obj = {};
    Object.keys(seriesMap).forEach((topic) => {
      obj[topic] = seriesMap[topic].points;
    });
    downloadBlob('opc_export.json', JSON.stringify(obj, null, 2), 'application/json');
  }

  function downloadBlob(name, text, mime) {
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([text], { type: mime }));
    a.download = name;
    a.click();
    URL.revokeObjectURL(a.href);
  }

  function clearChart() {
    chart.data.datasets = [];
    Object.keys(topicToDatasetIndex).forEach((k) => delete topicToDatasetIndex[k]);
    Object.keys(seriesMap).forEach((k) => delete seriesMap[k]);
    chart.update();
    $('valueGrid').innerHTML = '';
    if (idb) {
      const tx = idb.transaction('series', 'readwrite');
      tx.objectStore('series').clear();
    }
  }

  async function restoreFromIdb() {
    if (!idb) return;
    await new Promise((resolve) => {
      const tx = idb.transaction('series', 'readonly');
      const req = tx.objectStore('series').getAll();
      req.onsuccess = () => {
        const rows = req.result || [];
        rows.forEach((row) => {
          const { topic, points } = row;
          if (!topic || !points || !points.length) return;
          ensureDataset(topic);
          const dsIdx = topicToDatasetIndex[topic];
          const ds = chart.data.datasets[dsIdx];
          points.forEach((p) => {
            ds.data.push({ x: p.t, y: p.y });
          });
          trimDataset(ds);
          seriesMap[topic].points = points.slice(-getMaxPoints());
        });
        chart.update('none');
        resolve();
      };
      req.onerror = () => resolve();
    });
  }

  async function boot() {
    initChart();
    try {
      idb = await openIdb();
      await restoreFromIdb();
    } catch (e) {
      log('IndexedDB unavailable: ' + e);
    }

    $('btnConnect').onclick = () => connect();
    $('btnDisconnect').onclick = () => disconnect();
    $('btnClearChart').onclick = () => clearChart();
    $('btnExportCsv').onclick = () => exportCsv();
    $('btnExportJson').onclick = () => exportJson();
  }

  boot();
})();
