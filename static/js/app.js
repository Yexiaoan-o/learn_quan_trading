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
});
