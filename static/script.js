/* ============================================
   🌸 أتمتة العطور — Frontend
   ============================================ */
const API = '';
let autoStatusTimer = null;

const STATUS_LABELS = { pending:'انتظار', in_cart:'سلة', checkout:'دفع', delivered:'وصل', reviewed:'تقييم' };
const STATUS_ICONS = { pending:'⏳', in_cart:'🛒', checkout:'💳', delivered:'✅', reviewed:'⭐' };

// =============================================
// الأتمتة الكاملة
// =============================================
async function startAutomation() {
    const btn = document.getElementById('btn-start-auto');
    const store = document.getElementById('auto-store-select')?.value || 'مهووس';
    showLoading(btn);

    try {
        const resp = await fetch(`${API}/api/automate/start`, {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ store })
        });
        const data = await resp.json();

        if (data.success) {
            showToast('🚀 بدأت الأتمتة — راقب المتصفح!', 'success');

            // عرض الشخصية
            const p = data.persona;
            document.getElementById('persona-result').style.display = 'flex';
            document.getElementById('p-avatar').textContent = p.gender === 'female' ? '👩' : '👨';
            document.getElementById('p-name').textContent = p.name;
            document.getElementById('p-city').textContent = `📍 ${p.city}`;

            // عرض السجل
            document.getElementById('auto-log').style.display = 'block';

            // بدء متابعة الحالة
            startAutoStatusPolling();
        } else {
            showToast(data.error || 'فشل', 'error');
        }
    } catch (e) {
        showToast(`فشل: ${e.message}`, 'error');
    } finally { hideLoading(btn); }
}

function startAutoStatusPolling() {
    stopAutoStatusPolling();
    autoStatusTimer = setInterval(checkAutoStatus, 2000);
}

function stopAutoStatusPolling() {
    if (autoStatusTimer) { clearInterval(autoStatusTimer); autoStatusTimer = null; }
}

async function checkAutoStatus() {
    try {
        const resp = await fetch(`${API}/api/automate/status`);
        const data = await resp.json();
        renderAutoLog(data.steps || []);

        if (data.status === 'done' || data.status === 'error') {
            stopAutoStatusPolling();
            if (data.status === 'done') showToast('✅ انتهت الأتمتة!', 'success');
        }
    } catch (e) { console.error(e); }
}

function renderAutoLog(steps) {
    const container = document.getElementById('log-entries');
    if (!container) return;
    container.innerHTML = steps.map((s, i) => `
        <div class="log-entry fade-in" style="animation-delay:${i*0.03}s">
            <span class="log-time">${esc(s.time || '')}</span>
            <span class="log-step-badge">${esc(s.step || '')}</span>
            <span class="log-msg">${esc(s.message || '')}</span>
        </div>
    `).join('');
    container.scrollTop = container.scrollHeight;
}

// =============================================
// نافذة المتجر المدمجة
// =============================================
async function loadStoreInFrame() {
    const store = document.getElementById('auto-store-select')?.value || 'مهووس';
    const loading = document.getElementById('store-frame-loading');
    const frame = document.getElementById('store-frame');
    loading.style.display = 'flex';
    try {
        const resp = await fetch(`${API}/api/store/url?store=${encodeURIComponent(store)}`);
        const data = await resp.json();
        frame.src = `${API}/proxy?url=${encodeURIComponent(data.url)}`;
        frame.onload = () => { loading.style.display = 'none'; };
        setTimeout(() => { loading.style.display = 'none'; }, 8000);
    } catch (e) { loading.style.display = 'none'; }
}

function loadBoomlify() {
    const frame = document.getElementById('store-frame');
    const loading = document.getElementById('store-frame-loading');
    loading.style.display = 'flex';
    frame.src = 'https://boomlify.com/ar';
    frame.onload = () => { loading.style.display = 'none'; };
    setTimeout(() => { loading.style.display = 'none'; }, 8000);
}

function openStoreExternal() {
    const store = document.getElementById('auto-store-select')?.value || 'مهووس';
    fetch(`${API}/api/store/url?store=${encodeURIComponent(store)}`)
        .then(r => r.json()).then(d => window.open(d.url, '_blank'));
}

// =============================================
// شخصية جديدة (يدوي)
// =============================================
async function generatePersona() {
    try {
        const resp = await fetch(`${API}/api/persona/generate`, {
            method: 'POST', headers: {'Content-Type': 'application/json'}
        });
        const data = await resp.json();
        const p = data.persona || {};
        showToast(`✨ ${p.name} — ${p.city}`, 'success');
        document.getElementById('persona-result').style.display = 'flex';
        document.getElementById('p-avatar').textContent = p.gender === 'female' ? '👩' : '👨';
        document.getElementById('p-name').textContent = p.name;
        document.getElementById('p-city').textContent = `📍 ${p.city}`;
        await loadStats();
    } catch (e) { showToast(`فشل: ${e.message}`, 'error'); }
}

// =============================================
// الطلبات
// =============================================
async function loadOrders() {
    try {
        const resp = await fetch(`${API}/api/orders`);
        const data = await resp.json();
        const orders = data.orders || [];
        const tbody = document.getElementById('orders-tbody');
        const empty = document.getElementById('table-empty');
        const table = document.getElementById('orders-table');
        document.getElementById('table-loading').style.display = 'none';
        if (!orders.length) { table.style.display='none'; empty.style.display='flex'; return; }
        empty.style.display = 'none'; table.style.display = 'table';
        tbody.innerHTML = orders.map((o,i) => {
            const id=o.id||i, name=o.persona_name||'—', store=o.store_name||'—',
                  perfume=o.product_name||'—', price=o.price||0, status=o.status||'pending';
            return `<tr class="fade-in"><td>${i+1}</td>
                <td><span class="copy-cell" onclick="copyText('${esc(name)}')">${esc(name)}</span></td>
                <td>🏪 ${esc(store)}</td>
                <td title="${esc(perfume)}">${esc(perfume)}</td>
                <td>${price?`ر.س${parseFloat(price).toFixed(0)}`:'—'}</td>
                <td><select class="status-select status-${status}" onchange="updateStatus('${id}',this.value)">
                    ${Object.entries(STATUS_LABELS).map(([k,v])=>`<option value="${k}" ${k===status?'selected':''}>${STATUS_ICONS[k]} ${v}</option>`).join('')}
                </select></td>
                <td><div class="actions-cell">
                    <button class="btn btn-action-review btn-xs" onclick="generateReview('${id}',false)">📝</button>
                    <button class="btn btn-action-ai btn-xs" onclick="generateReview('${id}',true)">🤖</button>
                </div></td></tr>`;
        }).join('');
    } catch(e) { document.getElementById('table-loading').style.display='none'; }
}

async function updateStatus(id, s) {
    try { await fetch(`${API}/api/order/${id}/status`, {
        method:'PUT', headers:{'Content-Type':'application/json'}, body:JSON.stringify({status:s})
    }); } catch(e) {}
}

async function handleScrapeTrending() {
    showToast('🔍 جاري جلب الترند...', 'info');
    try {
        const store = document.getElementById('auto-store-select')?.value || 'مهووس';
        const resp = await fetch(`${API}/api/scrape/trending`, {
            method:'POST', headers:{'Content-Type':'application/json'},
            body:JSON.stringify({store_name:store})
        });
        const data = await resp.json();
        showToast(`✅ ${data.products?.length||0} منتج`, 'success');
        await loadOrders(); await loadStats();
    } catch(e) { showToast('فشل', 'error'); }
}

async function generateReview(id, ai=false) {
    showToast('⏳ جاري التوليد...', 'info');
    try {
        const resp = await fetch(`${API}/api/review/generate`, {
            method:'POST', headers:{'Content-Type':'application/json'},
            body:JSON.stringify({order_id:id, use_ai:ai})
        });
        const data = await resp.json();
        showReviewModal(data.reviews||[]);
        await loadOrders(); await loadStats();
    } catch(e) { showToast('فشل', 'error'); }
}

function showReviewModal(reviews) {
    document.getElementById('review-modal-body').innerHTML = reviews.map((r,i) => `
        <div class="review-card fade-in" style="animation-delay:${i*0.1}s">
            <div class="review-header">
                <div class="review-stars">${'★'.repeat(r.rating||5)}${'☆'.repeat(5-(r.rating||5))}</div>
                ${r.ai?'<span class="review-ai-badge">🤖 AI</span>':''}
            </div>
            <div class="review-text" id="rev-${i}">${esc(r.text||'')}</div>
            <button class="btn btn-copy btn-xs" onclick="copyText(document.getElementById('rev-${i}').innerText)">📋 نسخ</button>
        </div>`).join('');
    document.getElementById('review-modal').style.display = 'flex';
    document.body.style.overflow = 'hidden';
}

function closeReviewModal() {
    document.getElementById('review-modal').style.display = 'none';
    document.body.style.overflow = '';
}

// =============================================
// Stats + Utilities
// =============================================
async function loadStats() {
    try {
        const resp = await fetch(`${API}/api/stats`);
        const data = await resp.json();
        ['personas','products','orders','reviews'].forEach(k => {
            const el = document.getElementById(`stat-${k}`);
            if(el) { const t=data[k]||0, c=parseInt(el.textContent)||0;
                if(c!==t){ const s=performance.now(),d=t-c;
                    (function step(n){const p=Math.min((n-s)/600,1);el.textContent=Math.round(c+d*(1-Math.pow(1-p,3)));if(p<1)requestAnimationFrame(step);})(performance.now()); }
            }
        });
    } catch(e) {}
}

function copyText(text) {
    navigator.clipboard.writeText(text)
        .then(() => showToast('📋 تم النسخ: ' + text.substring(0,30), 'success'))
        .catch(() => { const t=document.createElement('textarea');t.value=text;t.style.cssText='position:fixed;opacity:0';document.body.appendChild(t);t.select();document.execCommand('copy');document.body.removeChild(t);showToast('📋 تم','success'); });
}

function showToast(msg, type='info') {
    const c = document.getElementById('toast-container'); if(!c) return;
    const t = document.createElement('div'); t.className = `toast toast-${type}`;
    t.innerHTML = `<span class="toast-icon">${{success:'✅',error:'❌',info:'ℹ️'}[type]||'ℹ️'}</span><span class="toast-message">${esc(msg)}</span>`;
    c.appendChild(t); setTimeout(()=>{t.classList.add('toast-exit');setTimeout(()=>t.remove(),300);},4000);
}

function showLoading(el){if(el){el.classList.add('btn-loading');el.disabled=true;}}
function hideLoading(el){if(el){el.classList.remove('btn-loading');el.disabled=false;}}
function esc(t){if(!t)return'';const d=document.createElement('div');d.textContent=String(t);return d.innerHTML;}

document.addEventListener('keydown',e=>{if(e.key==='Escape')closeReviewModal();});
document.addEventListener('DOMContentLoaded',()=>{
    loadOrders(); loadStats(); loadStoreInFrame();
    setInterval(loadStats, 30000);
});
