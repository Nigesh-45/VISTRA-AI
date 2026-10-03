document.addEventListener('DOMContentLoaded', () => {
    fetchStats();
    fetchVisitors();

    // Auto refresh every 5 seconds
    setInterval(() => {
        fetchStats();
        fetchVisitors();
    }, 5000);

    // Search filter listener
    const searchInput = document.getElementById('visitor-search');
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            filterVisitors(e.target.value.toLowerCase());
        });
    }
});

let allVisitors = [];

async function fetchStats() {
    try {
        const res = await fetch('/api/stats');
        if (!res.ok) return;
        const data = await res.json();
        if (data.status === 'success' && data.summary) {
            const s = data.summary;
            document.getElementById('val-unique').textContent = s.total_unique_visitors;
            document.getElementById('val-inside').textContent = s.currently_inside;
            document.getElementById('val-entries').textContent = s.total_entries;
            document.getElementById('val-exits').textContent = s.total_exits;
        }
    } catch (err) {
        console.error('Error fetching stats:', err);
    }
}

async function fetchVisitors() {
    try {
        const res = await fetch('/api/visitors');
        if (!res.ok) return;
        const data = await res.json();
        if (data.status === 'success' && Array.isArray(data.visitors)) {
            allVisitors = data.visitors;
            renderVisitors(allVisitors);
        }
    } catch (err) {
        console.error('Error fetching visitors:', err);
    }
}

function renderVisitors(visitors) {
    const tbody = document.getElementById('visitor-table-body');
    if (!tbody) return;

    if (visitors.length === 0) {
        tbody.innerHTML = `<tr><td colspan="8" class="text-center">No matching visitors found.</td></tr>`;
        return;
    }

    tbody.innerHTML = visitors.map(v => `
        <tr>
            <td><img src="${v.avatar}" alt="${v.visitor_id}" class="avatar-img"></td>
            <td><strong>${v.visitor_id}</strong></td>
            <td>${v.first_seen}</td>
            <td>${v.last_seen}</td>
            <td>
                <span class="status-pill ${v.status === 'INSIDE' ? 'inside' : 'exited'}">
                    ${v.status}
                </span>
            </td>
            <td>${v.entries}</td>
            <td>${v.exits}</td>
            <td>${(v.confidence * 100).toFixed(1)}%</td>
        </tr>
    `).join('');
}

function filterVisitors(query) {
    if (!query) {
        renderVisitors(allVisitors);
        return;
    }
    const filtered = allVisitors.filter(v => 
        v.visitor_id.toLowerCase().includes(query) ||
        v.status.toLowerCase().includes(query)
    );
    renderVisitors(filtered);
}
