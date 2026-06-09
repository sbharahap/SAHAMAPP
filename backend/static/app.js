// State Global Frontend
const state = {
    activeTab: 'recommendations',
    chatHistory: [],
    stocks: []
};

// ============================================================
// 1. Navigation & Tab Switcher
// ============================================================
function initNavigation() {
    const navItems = document.querySelectorAll('.nav-item');
    navItems.forEach(item => {
        item.addEventListener('click', () => {
            const targetTab = item.getAttribute('data-tab');
            switchTab(targetTab);
        });
    });

    // Tampilkan tanggal hari ini
    const dateOptions = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
    document.getElementById('current-date').innerText = new Date().toLocaleDateString('id-ID', dateOptions);
}

function switchTab(tabId) {
    state.activeTab = tabId;

    // Update active class on sidebar buttons
    document.querySelectorAll('.nav-item').forEach(btn => {
        if (btn.getAttribute('data-tab') === tabId) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });

    // Update active class on tab content sections
    document.querySelectorAll('.tab-content').forEach(section => {
        if (section.id === `tab-${tabId}`) {
            section.classList.add('active');
        } else {
            section.classList.remove('active');
        }
    });

    // Update header title based on tab
    const title = document.getElementById('page-title');
    const subtitle = document.getElementById('page-subtitle');

    if (tabId === 'recommendations') {
        title.innerText = 'Top 10 Rekomendasi Saham';
        subtitle.innerText = 'Rekomendasi model AI terbaik untuk minggu ini berdasarkan analisis multi-faktor.';
        loadRecommendations();
    } else if (tabId === 'chatbot') {
        title.innerText = 'AI Saham RAG Chatbot';
        subtitle.innerText = 'Tanyakan apa saja tentang emiten IDX didukung Vector Store ChromaDB lokal.';
    } else if (tabId === 'admin') {
        title.innerText = 'Sistem & Control Panel';
        subtitle.innerText = 'Monitor status database, kelola emiten pantauan, dan pemicu pekerjaan manual.';
        loadAdminData();
    }
}

// Helper formatting Rupiah
function formatRupiah(value) {
    if (value === null || value === undefined) return 'N/A';
    return 'Rp ' + parseFloat(value).toLocaleString('id-ID', { maximumFractionDigits: 0 });
}

// ============================================================
// 2. Recommendations (Tab 1)
// ============================================================
async function loadRecommendations() {
    const loading = document.getElementById('rec-loading');
    const empty = document.getElementById('rec-empty');
    const grid = document.getElementById('rec-grid');
    const dateDisplay = document.getElementById('scoring-date-display');

    loading.classList.remove('hidden');
    empty.classList.add('hidden');
    grid.classList.add('hidden');

    try {
        const response = await fetch('/api/rekomendasi/mingguan');
        if (!response.ok) throw new Error('Gagal mengambil data rekomendasi');
        
        const data = await response.json();

        if (!data.tanggal || data.rekomendasi.length === 0) {
            loading.classList.add('hidden');
            empty.classList.remove('hidden');
            return;
        }

        // Set tanggal
        const dateObj = new Date(data.tanggal);
        const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
        dateDisplay.innerText = dateObj.toLocaleDateString('id-ID', options);

        // Render Cards
        grid.innerHTML = '';
        data.rekomendasi.forEach(stock => {
            const card = document.createElement('div');
            card.className = 'stock-card glass';

            const buyHoldSellClass = stock.rekomendasi.toLowerCase();
            const confidencePercentage = Math.round(stock.confidence * 100);

            card.innerHTML = `
                <div class="card-top">
                    <div class="stock-main-info">
                        <div class="rank-badge">#${stock.rank}</div>
                        <div class="stock-name-block">
                            <span class="stock-code">${stock.kode_saham}</span>
                            <span class="stock-company">${stock.nama_perusahaan}</span>
                            <span class="stock-sector">${stock.sektor}</span>
                        </div>
                    </div>

                    <div class="stock-metrics-total">
                        <div class="score-main-display">
                            <span class="score-num">${stock.skor_total.toFixed(1)}<span>/100</span></span>
                            <span class="score-lbl">Skor AI</span>
                        </div>
                        <div class="recommendation-badge ${buyHoldSellClass}">
                            ${stock.rekomendasi}
                        </div>
                    </div>
                </div>

                <div class="card-body">
                    <div class="radar-scores-container">
                        <div class="component-bar-row">
                            <span class="comp-lbl">Fundamental (30%)</span>
                            <div class="comp-bar-wrapper">
                                <div class="comp-bar-fill fund" style="width: ${stock.skor_fundamental}%"></div>
                            </div>
                            <span class="comp-val">${stock.skor_fundamental.toFixed(0)}</span>
                        </div>
                        <div class="component-bar-row">
                            <span class="comp-lbl">Sentimen (25%)</span>
                            <div class="comp-bar-wrapper">
                                <div class="comp-bar-fill sent" style="width: ${stock.skor_sentimen}%"></div>
                            </div>
                            <span class="comp-val">${stock.skor_sentimen.toFixed(0)}</span>
                        </div>
                        <div class="component-bar-row">
                            <span class="comp-lbl">Sektor (20%)</span>
                            <div class="comp-bar-wrapper">
                                <div class="comp-bar-fill sekt" style="width: ${stock.skor_sektor}%"></div>
                            </div>
                            <span class="comp-val">${stock.skor_sektor.toFixed(0)}</span>
                        </div>
                        <div class="component-bar-row">
                            <span class="comp-lbl">Makro (15%)</span>
                            <div class="comp-bar-wrapper">
                                <div class="comp-bar-fill makr" style="width: ${stock.skor_makro}%"></div>
                            </div>
                            <span class="comp-val">${stock.skor_makro.toFixed(0)}</span>
                        </div>
                        <div class="component-bar-row">
                            <span class="comp-lbl">Risiko (10%)</span>
                            <div class="comp-bar-wrapper">
                                <div class="comp-bar-fill risk" style="width: ${stock.skor_risiko}%"></div>
                            </div>
                            <span class="comp-val">${stock.skor_risiko.toFixed(0)}</span>
                        </div>
                    </div>

                    <div class="ai-analysis-block">
                        <div class="ai-header">
                            <i class="fa-solid fa-brain"></i> Analisis AI (Qwen3)
                        </div>
                        <p class="ai-text">${stock.alasan || 'Tidak ada analisis tertulis.'}</p>
                    </div>

                    <div class="card-footer">
                        <div class="confidence-indicator">
                            Tingkat Keyakinan Model: <span>${confidencePercentage}%</span>
                        </div>
                        <button class="btn btn-secondary btn-mini" onclick="askAiAbout('${stock.kode_saham}')">
                            <i class="fa-solid fa-comment-dots"></i> Tanya Asisten
                        </button>
                    </div>
                </div>
            `;

            grid.appendChild(card);
        });

        loading.classList.add('hidden');
        grid.classList.remove('hidden');

    } catch (error) {
        console.error(error);
        loading.classList.add('hidden');
        empty.classList.remove('hidden');
        document.getElementById('rec-empty').innerHTML = `
            <i class="fa-solid fa-triangle-exclamation" style="color: var(--color-sell)"></i>
            <h3>Gagal Memuat Data</h3>
            <p>Terjadi kesalahan saat menghubungi API server lokal. Pastikan server FastAPI berjalan di backend.</p>
        `;
    }
}

function askAiAbout(stockCode) {
    switchTab('chatbot');
    const input = document.getElementById('chat-input');
    input.value = `Bagaimana analisis fundamental dan sentimen saham ${stockCode} menurut data terbaru?`;
    // Trigger submit form
    document.getElementById('chat-form').dispatchEvent(new Event('submit'));
}


// ============================================================
// 3. RAG Chatbot (Tab 2)
// ============================================================
function initChatbot() {
    const form = document.getElementById('chat-form');
    const input = document.getElementById('chat-input');
    const messagesContainer = document.getElementById('chat-messages-container');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const text = input.value.trim();
        if (!text) return;

        // 1. Tampilkan pesan user
        appendMessage('user', text);
        input.value = '';

        // 2. Tampilkan typing indicator
        const typingIndicator = document.getElementById('typing-indicator');
        typingIndicator.classList.remove('hidden');
        messagesContainer.scrollTop = messagesContainer.scrollHeight;

        try {
            // 3. Kirim POST ke endpoint streaming RAG chatbot yang baru
            const response = await fetch('/api/chatbot/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    pertanyaan: text,
                    riwayat: state.chatHistory
                })
            });

            if (!response.ok) throw new Error('Koneksi chatbot ke server terputus');

            // Sembunyikan typing indicator
            typingIndicator.classList.add('hidden');

            // Tambahkan bubble kosong asisten untuk menampung stream
            const aiMsgDiv = appendMessage('assistant', '');
            const textDiv = aiMsgDiv.querySelector('.message-text');

            // 4. Baca stream data secara real-time chunk-by-chunk
            const reader = response.body.getReader();
            const decoder = new TextDecoder("utf-8");
            let jawaban_lengkap = "";

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value, { stream: true });
                jawaban_lengkap += chunk;

                // Format markdown sederhana secara dinamis
                let formattedText = jawaban_lengkap
                    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                    .replace(/\*(.*?)\*/g, '<em>$1</em>')
                    .replace(/`(.*?)`/g, '<code>$1</code>')
                    .replace(/\n/g, '<br>');

                textDiv.innerHTML = formattedText;
                messagesContainer.scrollTop = messagesContainer.scrollHeight;
            }

            // 5. Tampilkan citation block referensi setelah stream teks selesai
            const citationWrapper = aiMsgDiv.querySelector('.meta-citation-wrapper');
            citationWrapper.innerHTML = `
                <div class="citation-block">
                    <div class="citation-header"><i class="fa-solid fa-quote-left"></i> Referensi Dokumen RAG (Lokal)</div>
                    <div class="citation-chips">
                        <span class="citation-chip">ChromaDB Vector Store</span>
                        <span class="citation-chip">PostgreSQL Finance DB</span>
                    </div>
                </div>
            `;
            citationWrapper.classList.remove('hidden');
            messagesContainer.scrollTop = messagesContainer.scrollHeight;

            // 6. Simpan ke riwayat chat
            state.chatHistory.push({ role: 'user', content: text });
            state.chatHistory.push({ role: 'assistant', content: jawaban_lengkap });
            if (state.chatHistory.length > 10) {
                state.chatHistory.shift();
                state.chatHistory.shift();
            }

        } catch (error) {
            typingIndicator.classList.add('hidden');
            appendMessage('assistant', `⚠️ Maaf, saya sedang mengalami gangguan koneksi ke server lokal: ${error.message}`);
        }
    });

    // Suggestion chips click handler
    document.querySelectorAll('.suggest-chip').forEach(chip => {
        chip.addEventListener('click', () => {
            input.value = chip.getAttribute('data-query');
            form.dispatchEvent(new Event('submit'));
        });
    });
}

function appendMessage(role, text, metaData = null) {
    const container = document.getElementById('chat-messages-container');
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${role === 'user' ? 'user-msg' : 'system-msg'}`;

    let avatarHtml = '';
    if (role === 'user') {
        avatarHtml = '<div class="msg-avatar"><i class="fa-solid fa-user"></i></div>';
    } else {
        avatarHtml = '<div class="msg-avatar"><i class="fa-solid fa-robot"></i></div>';
    }

    // Format markdown dasar (*bold* atau `code` atau newline)
    let formattedText = "";
    if (text) {
        formattedText = text
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/`(.*?)`/g, '<code>$1</code>')
            .replace(/\n/g, '<br>');
    }

    let citationHtml = '';
    // Jika ada info RAG, tampilkan sumber di bawah bubble
    if (metaData && metaData.sumber_data > 0) {
        citationHtml = `
            <div class="citation-block">
                <div class="citation-header"><i class="fa-solid fa-quote-left"></i> Referensi Dokumen RAG (${metaData.sumber_data})</div>
                <div class="citation-chips">
                    <span class="citation-chip">ChromaDB Vector Store</span>
                    <span class="citation-chip">PostgreSQL Finance DB</span>
                    <span class="citation-chip">LLM Confidence: ${Math.round(metaData.confidence * 100)}%</span>
                </div>
            </div>
        `;
    }

    let disclaimerHtml = '';
    if (role === 'assistant') {
        disclaimerHtml = '<span class="bubble-disclaimer">Informasi di atas merupakan hasil analisis data sistem AI Saham, bukan keputusan saran jual/beli mutlak.</span>';
    }

    msgDiv.innerHTML = `
        ${avatarHtml}
        <div class="msg-bubble">
            <div class="message-text">${formattedText || '...'}</div>
            <div class="meta-citation-wrapper ${citationHtml ? '' : 'hidden'}">${citationHtml}</div>
            ${disclaimerHtml}
        </div>
    `;

    container.appendChild(msgDiv);
    container.scrollTop = container.scrollHeight;
    return msgDiv;
}


// ============================================================
// 4. Admin & Control Panel (Tab 3)
// ============================================================
async function loadAdminData() {
    await fetchStats();
    await fetchStocksList();
    await fetchAlertsHistory();
}

async function fetchStats() {
    try {
        const response = await fetch('/api/status');
        if (!response.ok) throw new Error();
        const data = await response.json();

        // Update top status metrics
        document.getElementById('stat-saham').innerText = data.database.saham_total;
        document.getElementById('stat-fundamental').innerText = data.database.fundamental_total;
        document.getElementById('stat-makro').innerText = data.database.makro_total;
        document.getElementById('stat-berita').innerText = data.database.berita_total;
        document.getElementById('stat-total-scoring').innerText = data.database.scoring_total;

        document.getElementById('stat-scheduler-status').innerText = data.scheduler.running ? 'Aktif (Mendengarkan)' : 'Mati';
        document.getElementById('stat-scheduler-status').style.color = data.scheduler.running ? 'var(--color-buy)' : 'var(--color-sell)';

        if (data.database.tanggal_scoring_terakhir) {
            const dateObj = new Date(data.database.tanggal_scoring_terakhir);
            document.getElementById('stat-last-scoring').innerText = dateObj.toLocaleDateString('id-ID', { year: 'numeric', month: 'short', day: 'numeric' });
        } else {
            document.getElementById('stat-last-scoring').innerText = 'Belum pernah';
        }

        // Render Scheduled Jobs List
        const jobsList = document.getElementById('scheduler-jobs-list');
        jobsList.innerHTML = '';
        
        data.scheduler.jobs.forEach(job => {
            const li = document.createElement('li');
            const nextRun = job.next_run_time ? new Date(job.next_run_time).toLocaleString('id-ID') : 'Mati';
            li.innerHTML = `
                <strong>${job.name}</strong><br>
                <span style="color: var(--text-secondary); font-size: 0.7rem;">ID: ${job.id} | Run Berikutnya: ${nextRun}</span>
            `;
            jobsList.appendChild(li);
        });

    } catch (e) {
        console.error('Gagal fetch status API admin');
    }
}

async function fetchStocksList() {
    const tbody = document.getElementById('saham-table-body');
    tbody.innerHTML = '<tr><td colspan="3" class="text-center">Mengambil data emiten...</td></tr>';

    try {
        const response = await fetch('/api/data/saham/list');
        if (!response.ok) throw new Error();
        state.stocks = await response.json();

        tbody.innerHTML = '';
        if (state.stocks.length === 0) {
            tbody.innerHTML = '<tr><td colspan="3" class="text-center">Belum ada emiten terdaftar.</td></tr>';
            return;
        }

        state.stocks.forEach(stock => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><strong>${stock.kode}</strong></td>
                <td>${stock.nama_perusahaan}</td>
                <td>${stock.sektor}</td>
            `;
            tbody.appendChild(tr);
        });

    } catch (e) {
        tbody.innerHTML = '<tr><td colspan="3" class="text-center" style="color: var(--color-sell)">Gagal mengambil data emiten.</td></tr>';
    }
}

async function fetchAlertsHistory() {
    const tbody = document.getElementById('alert-table-body');
    tbody.innerHTML = '<tr><td colspan="4" class="text-center">Mengambil data alert...</td></tr>';

    try {
        const response = await fetch('/api/alerts');
        if (!response.ok) throw new Error();
        const alerts = await response.json();

        tbody.innerHTML = '';
        if (alerts.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" class="text-center">Belum ada alert yang dipicu.</td></tr>';
            return;
        }

        alerts.forEach(alert => {
            const tr = document.createElement('tr');
            const dateObj = new Date(alert.tanggal);
            const formattedTime = dateObj.toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' }) + ' ' + dateObj.toLocaleDateString('id-ID', { day: '2-digit', month: '2-digit' });
            
            const deltaVal = alert.delta;
            const deltaColor = deltaVal > 0 ? 'var(--color-buy)' : 'var(--color-sell)';
            const deltaText = deltaVal > 0 ? `+${deltaVal.toFixed(1)}` : `${deltaVal.toFixed(1)}`;

            tr.innerHTML = `
                <td><strong>${alert.kode_saham}</strong></td>
                <td style="white-space: nowrap; color: var(--text-muted);">${formattedTime}</td>
                <td style="color: ${deltaColor}; font-weight: bold;">${deltaText}</td>
                <td style="color: var(--text-secondary); max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${alert.pesan}">${alert.pesan}</td>
            `;
            tbody.appendChild(tr);
        });

    } catch (e) {
        tbody.innerHTML = '<tr><td colspan="4" class="text-center" style="color: var(--color-sell)">Gagal mengambil data alert.</td></tr>';
    }
}

// Job Labels & Original InnerHTML mapping for dynamic state restoration
const jobButtonLabels = {
    "scrape_news": { active: "Scraping Berita...", original: '<i class="fa-solid fa-play"></i> Jalankan' },
    "scrape_fundamental": { active: "Scraping Fundamental...", original: '<i class="fa-solid fa-play"></i> Jalankan' },
    "scrape_makro": { active: "Scraping Makro...", original: '<i class="fa-solid fa-play"></i> Jalankan' },
    "run_alerts": { active: "Memantau Sentimen...", original: '<i class="fa-solid fa-play"></i> Jalankan' },
    "run_scoring": { active: "Menghitung Skor...", original: '<i class="fa-solid fa-bolt"></i> Jalankan Scoring' }
};

// Polling status progress
let progressInterval = null;

async function pollJobsProgress() {
    try {
        const response = await fetch('/api/jobs/progress');
        if (!response.ok) return;
        const data = await response.json();
        
        let shouldReloadStats = false;
        
        for (const [jobName, info] of Object.entries(data)) {
            const container = document.getElementById(`progress-${jobName}`);
            if (!container) continue;
            
            const fill = container.querySelector('.job-progress-fill');
            const percentText = container.querySelector('.progress-percent');
            const msgText = container.querySelector('.progress-msg');
            const btn = document.querySelector(`button[onclick*="'${jobName}'"]`);
            
            if (info.status === 'running') {
                container.classList.remove('hidden');
                fill.style.width = `${info.percent}%`;
                fill.style.background = 'linear-gradient(90deg, var(--color-primary), var(--color-accent))';
                percentText.innerText = `${info.percent}%`;
                percentText.style.color = 'var(--color-primary)';
                msgText.innerText = info.message || 'Memproses...';
                
                if (btn) {
                    btn.disabled = true;
                    const activeLabel = jobButtonLabels[jobName]?.active || 'Memproses...';
                    btn.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i> ${activeLabel}`;
                    btn.style.backgroundColor = '';
                    btn.style.color = '';
                }
            } else if (info.status === 'failed') {
                container.classList.remove('hidden');
                fill.style.width = `${info.percent || 100}%`;
                fill.style.background = 'var(--color-sell)';
                percentText.innerText = 'Gagal';
                percentText.style.color = 'var(--color-sell)';
                msgText.innerText = info.message || 'Gagal menjalankan';
                
                if (btn) {
                    btn.disabled = false;
                    btn.innerHTML = `<i class="fa-solid fa-triangle-exclamation"></i> Coba Lagi`;
                    btn.style.backgroundColor = 'var(--color-sell)';
                    btn.style.color = 'white';
                }
            } else {
                // idle
                const isAlreadyHidden = container.classList.contains('hidden');
                if (!isAlreadyHidden) {
                    fill.style.width = '100%';
                    percentText.innerText = '100%';
                    percentText.style.color = 'var(--color-buy)';
                    msgText.innerText = info.message || 'Selesai';
                    
                    if (btn) {
                        btn.disabled = true; // Tetap nonaktifkan selama transisi sukses 5 detik
                        btn.innerHTML = '<i class="fa-solid fa-circle-check"></i> Selesai!';
                        btn.style.backgroundColor = 'var(--color-buy)';
                        btn.style.color = 'white';
                    }
                    
                    // Selesai -> reload stats sekali
                    shouldReloadStats = true;
                    
                    // Sembunyikan setelah 5 detik dan kembalikan style asli tombol
                    (function(targetJobName, targetBtn) {
                        setTimeout(() => {
                            fetch('/api/jobs/progress')
                                .then(res => res.json())
                                .then(latestData => {
                                    if (latestData[targetJobName] && latestData[targetJobName].status === 'idle') {
                                        const c = document.getElementById(`progress-${targetJobName}`);
                                        if (c) c.classList.add('hidden');
                                        if (targetBtn) {
                                            targetBtn.disabled = false;
                                            targetBtn.innerHTML = jobButtonLabels[targetJobName]?.original || 'Jalankan';
                                            targetBtn.style.backgroundColor = '';
                                            targetBtn.style.color = '';
                                        }
                                    }
                                });
                        }, 5000);
                    })(jobName, btn);
                } else {
                    if (btn && btn.disabled && btn.innerHTML.includes('fa-circle-notch')) {
                        btn.disabled = false;
                        btn.innerHTML = jobButtonLabels[jobName]?.original || 'Jalankan';
                        btn.style.backgroundColor = '';
                        btn.style.color = '';
                    }
                }
            }
        }
        
        if (shouldReloadStats) {
            fetchStats();
        }
    } catch (e) {
        console.error('Error polling jobs progress:', e);
    }
}

function startProgressPolling() {
    if (progressInterval) clearInterval(progressInterval);
    pollJobsProgress();
    progressInterval = setInterval(pollJobsProgress, 1500);
}

// Trigger background jobs manual
async function triggerJob(jobName, btnElement) {
    btnElement.disabled = true;
    btnElement.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Memicu...';

    try {
        const response = await fetch(`/api/jobs/trigger?job_name=${jobName}`, {
            method: 'POST'
        });
        const data = await response.json();

        if (response.ok) {
            // Segera update progress agar UI responsif
            setTimeout(pollJobsProgress, 100);
        } else {
            throw new Error(data.detail || 'Gagal memicu pekerjaan.');
        }
    } catch (e) {
        btnElement.innerHTML = '<i class="fa-solid fa-triangle-exclamation"></i> Gagal';
        btnElement.style.backgroundColor = 'var(--color-sell)';
        btnElement.style.color = 'white';
        alert(`Gagal menjalankan job: ${e.message}`);
        
        setTimeout(() => {
            btnElement.disabled = false;
            btnElement.innerHTML = jobButtonLabels[jobName]?.original || 'Jalankan';
            btnElement.style.backgroundColor = '';
            btnElement.style.color = '';
        }, 3000);
    }
}


// Inisialisasi formulir tambah saham
function initAddSahamForm() {
    const form = document.getElementById('add-saham-form');
    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const kode = document.getElementById('new-kode').value.trim().toUpperCase();
        const nama = document.getElementById('new-nama').value.trim();
        const sektor = document.getElementById('new-sektor').value.trim();

        try {
            const response = await fetch('/api/saham', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    kode: kode,
                    nama_perusahaan: nama,
                    sektor: sektor
                })
            });

            const data = await response.json();
            if (!response.ok) throw new Error(data.detail || 'Gagal menambah emiten.');

            alert(`Saham ${kode} berhasil ditambahkan!`);
            form.reset();
            fetchStocksList();
            fetchStats(); // Update metrics counter

        } catch (e) {
            alert(`Error: ${e.message}`);
        }
    });
}

// Polling status admin setiap 10 detik sekali
let adminInterval = null;
function startAdminPolling() {
    if (adminInterval) clearInterval(adminInterval);
    adminInterval = setInterval(() => {
        if (state.activeTab === 'admin') {
            fetchStats();
            fetchAlertsHistory();
        }
    }, 10000);
}


// ============================================================
// 5. System Log & SSE Real-Time Notifier
// ============================================================

let _sseErrorCount = 0;

function initSSENotifier() {
    const sseDot = document.getElementById('sse-dot');
    const sseText = document.getElementById('sse-status-text');
    const badge = document.getElementById('admin-error-badge');

    const es = new EventSource('/api/admin/events');

    es.onopen = () => {
        sseDot.style.background = 'var(--color-buy)';
        sseDot.style.boxShadow = '0 0 6px var(--color-buy)';
        sseText.style.color = 'var(--color-buy)';
        sseText.innerText = 'SSE Terhubung — Menerima notifikasi real-time';
    };

    es.onerror = () => {
        sseDot.style.background = 'var(--color-sell)';
        sseDot.style.boxShadow = 'none';
        sseText.style.color = 'var(--color-sell)';
        sseText.innerText = 'SSE Terputus — Mencoba sambung ulang...';
    };

    es.onmessage = (event) => {
        try {
            const msg = JSON.parse(event.data);

            // Heartbeat — tidak perlu tampilkan apa pun
            if (msg.type === 'heartbeat') return;

            const entry = msg.data;
            if (!entry) return;

            // Render ke System Log table
            appendSystemLogEntry(entry);

            // Jika ERROR atau CRITICAL: tampilkan banner + badge
            if (entry.level === 'ERROR' || entry.level === 'CRITICAL') {
                _sseErrorCount++;

                // Update badge di sidebar
                badge.innerText = _sseErrorCount;
                badge.classList.remove('hidden');

                // Tampilkan banner di atas halaman
                const banner = document.getElementById('critical-error-banner');
                const bannerTitle = document.getElementById('critical-banner-title');
                const bannerMsg = document.getElementById('critical-banner-msg');

                if (entry.level === 'CRITICAL') {
                    bannerTitle.innerText = '🚨 Error Kritis Sistem — Proses Dihentikan';
                } else {
                    bannerTitle.innerText = '⚠️ Error Sistem';
                }
                bannerMsg.innerText = `[${entry.source}] ${entry.message}`;
                banner.classList.remove('hidden');

                // Auto-scroll ke panel system log jika admin tab aktif
                if (state.activeTab === 'admin') {
                    document.getElementById('system-log-panel')?.scrollIntoView({ behavior: 'smooth' });
                }
            }
        } catch (e) {
            console.warn('SSE parse error:', e);
        }
    };
}

function appendSystemLogEntry(entry) {
    const tbody = document.getElementById('system-log-body');

    // Hapus placeholder jika ada
    const placeholder = tbody.querySelector('tr td[colspan]');
    if (placeholder) placeholder.closest('tr').remove();

    const levelConfig = {
        'CRITICAL': { color: 'var(--color-sell)', bg: 'rgba(239,68,68,0.10)', icon: '🚨', label: 'CRITICAL' },
        'ERROR':    { color: '#f97316',            bg: 'rgba(249,115,22,0.10)', icon: '❌', label: 'ERROR' },
        'INFO':     { color: 'var(--color-buy)',   bg: 'rgba(16,185,129,0.08)', icon: '✅', label: 'INFO' },
    };
    const cfg = levelConfig[entry.level] || levelConfig['INFO'];

    const tr = document.createElement('tr');
    tr.style.borderLeft = `3px solid ${cfg.color}`;
    tr.innerHTML = `
        <td>
            <span style="
                background: ${cfg.bg};
                color: ${cfg.color};
                padding: 2px 8px;
                border-radius: 4px;
                font-size: 0.7rem;
                font-weight: 700;
                font-family: var(--font-heading);
                white-space: nowrap;
            ">${cfg.icon} ${cfg.label}</span>
        </td>
        <td style="color: var(--text-muted); font-size: 0.75rem; white-space: nowrap;">${entry.source || '-'}</td>
        <td style="color: var(--text-secondary); font-size: 0.8rem; line-height: 1.4;">${entry.message || '-'}</td>
        <td style="color: var(--text-muted); font-size: 0.7rem; white-space: nowrap;">${entry.timestamp || ''}</td>
    `;

    // Masukkan di paling atas (terbaru di atas)
    tbody.insertBefore(tr, tbody.firstChild);

    // Batasi 50 baris
    while (tbody.rows.length > 50) {
        tbody.removeChild(tbody.lastChild);
    }
}

function clearSystemLog() {
    const tbody = document.getElementById('system-log-body');
    tbody.innerHTML = '<tr><td colspan="4" class="text-center" style="color:var(--text-muted); padding:24px;">Log dibersihkan.</td></tr>';
    _sseErrorCount = 0;
    document.getElementById('admin-error-badge').classList.add('hidden');
    document.getElementById('critical-error-banner').classList.add('hidden');
}


// ============================================================
// 6. Inisialisasi Aplikasi Saat Load
// ============================================================
document.addEventListener('DOMContentLoaded', () => {
    initNavigation();
    initChatbot();
    initAddSahamForm();
    startAdminPolling();
    startProgressPolling(); // <-- Poll background job progress periodically
    initSSENotifier(); // <-- Subscribe ke SSE notifikasi real-time

    // Jalankan load rekomendasi secara default saat pertama kali dimuat
    loadRecommendations();

    // Event listener refresh button rekomendasi
    document.getElementById('btn-refresh-rec').addEventListener('click', loadRecommendations);
});
