function toggleTheme() {
    const html = document.documentElement;
    const current = html.getAttribute('data-theme');
    const next = current === 'dark' ? 'light' : 'dark';
    html.setAttribute('data-theme', next);
    localStorage.setItem('theme', next);
    document.querySelector('.theme-icon').textContent = next === 'dark' ? '\u2600\uFE0F' : '\uD83C\uDF19';
}

(function() {
    const saved = localStorage.getItem('theme');
    if (saved) {
        document.documentElement.setAttribute('data-theme', saved);
        const icon = document.querySelector('.theme-icon');
        if (icon) icon.textContent = saved === 'dark' ? '\u2600\uFE0F' : '\uD83C\uDF19';
    }
})();

function toggleSidebar() {
    document.getElementById('sidebar').classList.toggle('collapsed');
}

function togglePhase(el) {
    const phaseDiv = el.closest('.nav-phase');
    phaseDiv.classList.toggle('expanded');
    const toggle = el.querySelector('.phase-toggle');
    if (toggle) {
        toggle.textContent = phaseDiv.classList.contains('expanded') ? '\u25BC' : '\u25B6';
    }
}

let currentSelectionPayload = null;

function appFlash(message, isError = false) {
    const flash = document.createElement('div');
    flash.className = 'flash-msg';
    if (isError) {
        flash.classList.add('flash-error');
    }
    flash.textContent = message;
    document.body.appendChild(flash);
    setTimeout(() => flash.remove(), 2200);
}

function closeModal(id) {
    const modal = document.getElementById(id);
    if (modal) {
        modal.classList.add('hidden');
    }
}

function openAiAnswerModal(answer) {
    const modal = document.getElementById('ai-answer-modal');
    const content = document.getElementById('ai-answer-content');
    if (!modal || !content) return;
    content.textContent = answer;
    modal.classList.remove('hidden');
}

function positionSelectionPopover(x, y) {
    const popover = document.getElementById('selection-popover');
    if (!popover) return;
    popover.style.left = x + 'px';
    popover.style.top = y + 'px';
    popover.classList.remove('hidden');
}

function hideSelectionPopover() {
    const popover = document.getElementById('selection-popover');
    if (popover) popover.classList.add('hidden');
}

function setupSelectionCommenting() {
    document.addEventListener('mouseup', (event) => {
        const selection = window.getSelection();
        const text = selection ? selection.toString().trim() : '';
        if (!text || text.length < 2) {
            hideSelectionPopover();
            return;
        }

        let target = event.target;
        const annotatable = target.closest('.annotatable');
        if (!annotatable) {
            hideSelectionPopover();
            return;
        }

        const range = selection.getRangeAt(0);
        const rect = range.getBoundingClientRect();
        currentSelectionPayload = {
            selected_text: text,
            chapter_id: annotatable.dataset.chapterId,
            section_id: annotatable.dataset.sectionId,
        };
        positionSelectionPopover(window.scrollX + rect.left, window.scrollY + rect.top - 42);
    });

    document.addEventListener('mousedown', (event) => {
        if (!event.target.closest('#selection-popover')) {
            hideSelectionPopover();
        }
    });

    const selectionBtn = document.getElementById('selection-comment-btn');
    if (selectionBtn) {
        selectionBtn.addEventListener('click', () => {
            if (!currentSelectionPayload) return;
            document.getElementById('annotation-selected-text').textContent = currentSelectionPayload.selected_text;
            document.getElementById('annotation-comment-input').value = '';
            document.getElementById('annotation-modal').classList.remove('hidden');
            hideSelectionPopover();
        });
    }

    const saveBtn = document.getElementById('annotation-save-btn');
    if (saveBtn) {
        saveBtn.addEventListener('click', async () => {
            if (!currentSelectionPayload) return;
            const comment = document.getElementById('annotation-comment-input').value.trim();
            const resp = await fetch('/api/annotations', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({...currentSelectionPayload, comment})
            });
            if (resp.ok) {
                appFlash('评论已保存');
                closeModal('annotation-modal');
            } else {
                appFlash('保存失败', true);
            }
        });
    }

    const askBtn = document.getElementById('annotation-ask-btn');
    if (askBtn) {
        askBtn.addEventListener('click', async () => {
            if (!currentSelectionPayload) return;
            const comment = document.getElementById('annotation-comment-input').value.trim() || '请解释这段内容';

            const saveResp = await fetch('/api/annotations', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({...currentSelectionPayload, comment})
            });
            if (!saveResp.ok) {
                appFlash('评论保存失败', true);
                return;
            }

            const aiResp = await fetch('/api/ai/ask', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    selected_text: currentSelectionPayload.selected_text,
                    question: comment
                })
            });
            const data = await aiResp.json();
            if (data.error) {
                appFlash(data.error, true);
                return;
            }
            closeModal('annotation-modal');
            openAiAnswerModal(data.answer);
        });
    }
}

function setupCodeCopyButtons() {
    document.querySelectorAll('.markdown-body pre').forEach((pre) => {
        if (pre.parentElement.classList.contains('code-copy-wrap')) return;
        const wrap = document.createElement('div');
        wrap.className = 'code-copy-wrap';
        pre.parentNode.insertBefore(wrap, pre);
        wrap.appendChild(pre);

        const btn = document.createElement('button');
        btn.className = 'copy-code-btn';
        btn.type = 'button';
        btn.textContent = '复制';
        btn.addEventListener('click', async () => {
            const code = pre.innerText;
            try {
                await navigator.clipboard.writeText(code);
                btn.textContent = '已复制';
                setTimeout(() => {
                    btn.textContent = '复制';
                }, 1200);
            } catch {
                appFlash('复制失败', true);
            }
        });
        wrap.appendChild(btn);
    });
}

function setupTocHighlight() {
    const links = document.querySelectorAll('[data-section-link]');
    if (!links.length) return;
    const sections = [...document.querySelectorAll('[id^="section-"]')];
    const observer = new IntersectionObserver((entries) => {
        entries.forEach((entry) => {
            const id = entry.target.id;
            const link = document.querySelector(`[data-section-link="${id}"]`);
            if (!link) return;
            if (entry.isIntersecting) {
                document.querySelectorAll('[data-section-link]').forEach((x) => x.classList.remove('active'));
                link.classList.add('active');
            }
        });
    }, {rootMargin: '-20% 0px -60% 0px', threshold: 0.1});
    sections.forEach((section) => observer.observe(section));
}

document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.nav-phase').forEach(el => el.classList.add('expanded'));
    const currentPath = window.location.pathname;
    document.querySelectorAll('.nav-chapter').forEach(el => {
        if (currentPath.startsWith('/chapter/')) {
            const phase = el.closest('.nav-phase');
            if (phase && el.classList.contains('active')) {
                phase.classList.add('expanded');
                const toggle = phase.querySelector('.phase-toggle');
                if (toggle) toggle.textContent = '\u25BC';
            }
        }
    });

    setupCodeCopyButtons();
    setupSelectionCommenting();
    setupTocHighlight();

    document.querySelectorAll('[data-close-modal]').forEach((btn) => {
        btn.addEventListener('click', () => closeModal(btn.dataset.closeModal));
    });
});

window.appFlash = appFlash;
window.openAiAnswerModal = openAiAnswerModal;
