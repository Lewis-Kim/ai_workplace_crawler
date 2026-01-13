console.log('[documents] JS LOADED');

/* =========================================================
 * 상태
 * ========================================================= */
let documents = [];
let selectedIds = new Set();
let pendingDeleteIds = [];

/* =========================================================
 * 초기 진입
 * ========================================================= */
document.addEventListener('DOMContentLoaded', () => {
    console.log('[documents] DOMContentLoaded');
    loadDocuments();
});

/* =========================================================
 * 문서 목록 로드
 * ========================================================= */
async function loadDocuments() {
    const folderFilterEl = document.getElementById('folderFilter');
    const fileTypeFilterEl = document.getElementById('fileTypeFilter');

    const folderFilter = folderFilterEl ? folderFilterEl.value : '';
    const fileTypeFilter = fileTypeFilterEl ? fileTypeFilterEl.value : '';

    let url = '/documents?limit=500';
    if (folderFilter) url += `&folder_name=${encodeURIComponent(folderFilter)}`;
    if (fileTypeFilter) url += `&file_type=${encodeURIComponent(fileTypeFilter)}`;

    try {
        const res = await fetch(url);
        if (!res.ok) {
            throw new Error(`HTTP ${res.status}`);
        }

        documents = await res.json();

        renderTable();
        updateFolderFilter();
        updateSelectedUI();

        const countEl = document.getElementById('docCount');
        if (countEl) {
            countEl.textContent = `총 ${documents.length}개 문서`;
        }
    } catch (e) {
        console.error('[documents] load failed:', e);
        const tbody = document.getElementById('docTableBody');
        if (tbody) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="8" style="text-align:center;padding:40px;color:var(--error);">
                        문서 목록을 불러오는데 실패했습니다.
                    </td>
                </tr>
            `;
        }
    }

    window.dispatchEvent(new Event('resize'));
}

/* =========================================================
 * 테이블 렌더링 (inline 이벤트 ❌)
 * ========================================================= */
function renderTable() {
    const tbody = document.getElementById('docTableBody');
    if (!tbody) return;

    if (documents.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="8" style="text-align:center;padding:40px;color:var(--text-muted);">
                    문서가 없습니다.
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = documents.map(doc => `
        <tr class="${selectedIds.has(doc.seq_id) ? 'selected' : ''}"
            data-id="${doc.seq_id}">

            <td>
                <input type="checkbox"
                       data-action="toggle"
                       data-id="${doc.seq_id}"
                       ${selectedIds.has(doc.seq_id) ? 'checked' : ''}>
            </td>

            <td style="font-family:monospace;color:var(--text-muted);">
                ${doc.seq_id}
            </td>

            <td>
                <div class="file-icon">
                    ${getFileIcon(doc.file_type)}
                    <span style="max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;display:inline-block;">
                        ${doc.title || '(제목 없음)'}
                    </span>
                </div>
            </td>

            <td>
                <span class="badge badge-${doc.file_type}">
                    ${(doc.file_type || 'unknown').toUpperCase()}
                </span>
            </td>

            <td style="color:var(--text-muted);font-size:13px;">
                ${doc.folder_name || '-'}
            </td>

            <td style="text-align:center;">${doc.chunk_count}</td>
            <td style="text-align:center;">${doc.image_count}</td>

            <td>
                <button class="btn btn-danger btn-icon btn-sm"
                        data-action="delete"
                        data-id="${doc.seq_id}">
                    🗑️
                </button>
            </td>
        </tr>
    `).join('');
}

/* =========================================================
 * 이벤트 위임 (모든 클릭/체크 여기서 처리)
 * ========================================================= */
document.addEventListener('click', (e) => {
    const el = e.target.closest('[data-action]');
    if (!el) return;

    const action = el.dataset.action;
    const id = el.dataset.id ? Number(el.dataset.id) : null;

    switch (action) {
        case 'delete':
            deleteSingle(id);
            break;

        case 'delete-selected':
            deleteSelected();
            break;

        case 'confirm':
            confirmDelete();
            break;

        case 'close':
            closeModal();
            break;
    }
});

document.addEventListener('change', (e) => {
    if (e.target.dataset.action === 'toggle') {
        toggleSelect(Number(e.target.dataset.id));
    }

    if (e.target.id === 'selectAll') {
        toggleSelectAll();
    }

    if (e.target.id === 'folderFilter' || e.target.id === 'fileTypeFilter') {
        loadDocuments();
    }
});

/* =========================================================
 * 선택 관련
 * ========================================================= */
function toggleSelect(id) {
    if (selectedIds.has(id)) {
        selectedIds.delete(id);
    } else {
        selectedIds.add(id);
    }
    updateSelectedUI();
    renderTable();
}

function toggleSelectAll() {
    const selectAll = document.getElementById('selectAll');
    if (!selectAll) return;

    if (selectAll.checked) {
        documents.forEach(doc => selectedIds.add(doc.seq_id));
    } else {
        selectedIds.clear();
    }
    updateSelectedUI();
    renderTable();
}

function updateSelectedUI() {
    const count = selectedIds.size;

    const countEl = document.getElementById('selectedCount');
    if (countEl) countEl.textContent = count;

    const btn = document.getElementById('deleteSelectedBtn');
    if (btn) btn.disabled = count === 0;

    const selectAll = document.getElementById('selectAll');
    if (selectAll) {
        selectAll.checked = count === documents.length && count > 0;
    }
}

/* =========================================================
 * 삭제 처리
 * ========================================================= */
function deleteSingle(id) {

    const doc = documents.find(d => d.seq_id === id);
    pendingDeleteIds = [id];

    const msg = document.getElementById('deleteMessage');
    if (msg) {
        msg.innerHTML = `
            <b>"${doc?.title || '문서 ' + id}"</b>을(를) 삭제하시겠습니까?<br>
            <span style="font-size:13px;color:var(--text-muted);">
                청크 ${doc?.chunk_count || 0}개, 이미지 ${doc?.image_count || 0}개
            </span>
        `;
    }
    openModal();
}

function deleteSelected() {
    if (selectedIds.size === 0) return;

    pendingDeleteIds = [...selectedIds];

    const msg = document.getElementById('deleteMessage');
    if (msg) {
        msg.innerHTML = `
            선택한 <b>${pendingDeleteIds.length}개</b> 문서를 삭제하시겠습니까?
        `;
    }

    openModal();
}

function openModal() {
    const modal = document.getElementById('deleteModal');
    if (!modal) {
        alert('deleteModal 요소를 찾을 수 없습니다.');
        return;
    }
    modal.style.display = 'flex';
    modal.style.zIndex = '99999';
}

function closeModal() {
    const modal = document.getElementById('deleteModal');
    if (modal) modal.style.display = 'none';
    //pendingDeleteIds = [];
}

async function confirmDelete() {
    if (pendingDeleteIds.length === 0) return;
    closeModal();
    try {
        
        if (pendingDeleteIds.length === 1) {
            const res = await fetch(`/documents/${pendingDeleteIds[0]}`, { method: 'DELETE' });
            const data = await res.json();
            data.success
                ? showToast(`문서 삭제 완료 (벡터 ${data.deleted_vectors}개 삭제)`)
                : showToast(data.message, 'error');
        } else if (pendingDeleteIds.length > 1) {
            const res = await fetch('/documents/batch-delete', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ doc_ids: pendingDeleteIds })
            });
            const data = await res.json();
            showToast(
                data.success
                    ? `${data.total_deleted}개 문서 삭제 완료`
                    : `${data.total_deleted}개 삭제, ${data.failed.length}개 실패`,
                data.success ? 'success' : 'warning'
            );
        }else{
            showToast('삭제할 문서가 없습니다.', 'warning');
        }

        selectedIds.clear();
        pendingDeleteIds = [];
        updateSelectedUI();
        loadDocuments();

    } catch (e) {
        console.error('[documents] delete failed:', e);
        showToast('삭제 중 오류가 발생했습니다.', 'error');
    }
}

/* =========================================================
 * 폴더 필터 업데이트
 * ========================================================= */
function updateFolderFilter() {
    const select = document.getElementById('folderFilter');
    if (!select) return;

    const currentValue = select.value;

    const folders = [...new Set(
        documents.map(d => d.folder_name).filter(Boolean)
    )];

    const existing = new Set(
        [...select.options].slice(1).map(o => o.value)
    );

    folders.forEach(folder => {
        if (!existing.has(folder)) {
            const option = document.createElement('option');
            option.value = folder;
            option.textContent = folder;
            select.appendChild(option);
        }
    });

    select.value = currentValue;
}

/* =========================================================
 * 유틸
 * ========================================================= */
function getFileIcon(fileType) {
    const icons = {
        pdf: '📕', docx: '📘', doc: '📘',
        txt: '📄', xlsx: '📊', xls: '📊',
        csv: '📊', jpg: '🖼️', jpeg: '🖼️', png: '🖼️'
    };
    return icons[fileType?.toLowerCase()] || '📁';
}

function showToast(message, type = 'success') {
    const toast = document.createElement('div');
    toast.style.cssText = `
        position:fixed;
        bottom:20px;
        right:20px;
        padding:12px 20px;
        background:${type === 'error' ? 'var(--error)' : type === 'warning' ? 'var(--warning)' : 'var(--success)'};
        color:white;
        border-radius:8px;
        font-size:14px;
        z-index:1001;
        animation:slideIn 0.3s ease;
    `;
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}
