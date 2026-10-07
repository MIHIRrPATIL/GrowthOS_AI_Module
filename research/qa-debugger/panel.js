// GrowthOS DevTools QA Panel Controller

const events = [];
let selectedIndex = -1;

const eventListEl = document.getElementById('eventList');
const eventDetailsEl = document.getElementById('eventDetails');
const searchInput = document.getElementById('searchInput');
const categoryFilter = document.getElementById('categoryFilter');
const clearBtn = document.getElementById('clearBtn');
const exportBtn = document.getElementById('exportBtn');

const metaSession = document.getElementById('metaSession');
const metaAnon = document.getElementById('metaAnon');
const metaCustomer = document.getElementById('metaCustomer');
const metaCount = document.getElementById('metaCount');

// Add Event Function
window.addGrowthOSEvent = function(event) {
  events.unshift(event);
  updateMeta(event);
  renderList();
};

function updateMeta(latest) {
  if (latest.session_id) metaSession.textContent = latest.session_id;
  if (latest.anonymous_id) metaAnon.textContent = latest.anonymous_id;
  if (latest.customer_id) metaCustomer.textContent = latest.customer_id;
  metaCount.textContent = events.length.toString();
}

function getEventCategory(name) {
  if (name.startsWith('page') || name.startsWith('session') || name.startsWith('tab')) return 'page';
  if (name.startsWith('element') || name.startsWith('scroll') || name.startsWith('clipboard')) return 'element';
  if (name.startsWith('form')) return 'form';
  if (name.startsWith('user')) return 'user';
  return 'commerce';
}

function renderList() {
  const query = (searchInput.value || '').toLowerCase();
  const category = categoryFilter.value;

  const filtered = events.filter((e, idx) => {
    const cat = getEventCategory(e.event_name);
    if (category !== 'all' && cat !== category) return false;
    if (query) {
      const str = JSON.stringify(e).toLowerCase();
      return str.includes(query);
    }
    return true;
  });

  if (filtered.length === 0) {
    eventListEl.innerHTML = '<div class="empty-state">No matching events found.</div>';
    return;
  }

  eventListEl.innerHTML = filtered.map((e, idx) => {
    const cat = getEventCategory(e.event_name);
    const time = new Date(e.timestamp).toLocaleTimeString();
    const isActive = idx === selectedIndex ? 'active' : '';
    return `
      <div class="event-item ${isActive}" onclick="selectEvent(${idx})">
        <div>
          <div class="event-name">${escapeHtml(e.event_name)}</div>
          <span class="event-tag tag-${cat}">${cat}</span>
        </div>
        <div class="event-time">${time}</div>
      </div>
    `;
  }).join('');
}

window.selectEvent = function(idx) {
  selectedIndex = idx;
  renderList();
  const e = events[idx];
  if (!e) return;

  eventDetailsEl.innerHTML = `
    <h3 style="margin-bottom: 8px; color: #38bdf8;">${escapeHtml(e.event_name)}</h3>
    <div style="font-size: 12px; color: #94a3b8; margin-bottom: 14px;">
      Event ID: <code>${e.event_id}</code> | Time: ${e.timestamp}
    </div>
    <pre>${escapeHtml(JSON.stringify(e, null, 2))}</pre>
  `;
};

clearBtn.addEventListener('click', () => {
  events.length = 0;
  selectedIndex = -1;
  metaCount.textContent = '0';
  eventListEl.innerHTML = '<div class="empty-state">Events cleared. Waiting for new activity...</div>';
  eventDetailsEl.innerHTML = '<div class="empty-state">Select an event from the left.</div>';
});

exportBtn.addEventListener('click', () => {
  const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(events, null, 2));
  const downloadAnchor = document.createElement('a');
  downloadAnchor.setAttribute('href', dataStr);
  downloadAnchor.setAttribute('download', `growthos_events_${Date.now()}.json`);
  document.body.appendChild(downloadAnchor);
  downloadAnchor.click();
  downloadAnchor.remove();
});

searchInput.addEventListener('input', renderList);
categoryFilter.addEventListener('change', renderList);

function escapeHtml(str) {
  return (str || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
