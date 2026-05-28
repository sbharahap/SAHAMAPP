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

// Trigger background jobs manual
async function triggerJob(jobName, btnElement) {
    const originalText = btnElement.innerHTML;
    btnElement.disabled = true;
    btnElement.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Memproses...';

    try {
        const response = await fetch(`/api/jobs/trigger?job_name=${jobName}`, {
            method: 'POST'
        });
        const data = await response.json();

        if (response.ok) {
            // Beri notifikasi sukses sederhana
            btnElement.innerHTML = '<i class="fa-solid fa-circle-check"></i> Sukses!';
            btnElement.style.backgroundColor = 'var(--color-buy)';
            btnElement.style.color = 'white';

            setTimeout(() => {
                btnElement.disabled = false;
                btnElement.innerHTML = originalText;
                btnElement.style.backgroundColor = '';
                btnElement.style.color = '';
                // Reload status data setelah job dipicu
                fetchStats();
            }, 3000);
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
            btnElement.innerHTML = originalText;
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
// 5. Inisialisasi Aplikasi Saat Load
// ============================================================
document.addEventListener('DOMContentLoaded', () => {
    initNavigation();
    initChatbot();
    initAddSahamForm();
    startAdminPolling();

    // Jalankan load rekomendasi secara default saat pertama kali dimuat
    loadRecommendations();

    // Event listener refresh button rekomendasi
    document.getElementById('btn-refresh-rec').addEventListener('click', loadRecommendations);
});
