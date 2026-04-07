/* Software Tracker — dashboard app */

const BASE = 'data/';

// ── DOM helpers ──────────────────────────────────────────────────────────────

/** Create an element with optional class and text content. */
function el(tag, { cls, text, href, target, rel, hidden } = {}) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text !== undefined) e.textContent = text;
  if (href) e.href = href;
  if (target) e.target = target;
  if (rel) e.rel = rel;
  if (hidden) e.hidden = true;
  return e;
}

function append(parent, ...children) {
  children.forEach(c => c && parent.appendChild(c));
  return parent;
}

function clearEl(e) { while (e.firstChild) e.removeChild(e.firstChild); }

// ── Theme ────────────────────────────────────────────────────────────────────

function initTheme() {
  const stored = localStorage.getItem('theme');
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  const theme = stored || (prefersDark ? 'dark' : 'light');
  document.documentElement.setAttribute('data-theme', theme);
  updateToggleLabel(theme);
}

function toggleTheme() {
  const current = document.documentElement.getAttribute('data-theme');
  const next = current === 'dark' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', next);
  localStorage.setItem('theme', next);
  updateToggleLabel(next);
}

function updateToggleLabel(theme) {
  const btn = document.getElementById('theme-toggle');
  if (btn) btn.textContent = theme === 'dark' ? '☀ Light' : '☾ Dark';
}

// ── Router ───────────────────────────────────────────────────────────────────

function getProjectSlug() {
  return new URLSearchParams(window.location.search).get('project') || null;
}

async function route() {
  const slug = getProjectSlug();
  if (slug) {
    await renderDetail(slug);
  } else {
    await renderIndex();
  }
}

// ── Index view ───────────────────────────────────────────────────────────────

async function renderIndex() {
  document.getElementById('detail-view').hidden = true;
  const indexView = document.getElementById('index-view');
  indexView.hidden = false;

  const filterBar = document.getElementById('filter-bar');
  const grid = document.getElementById('project-grid');
  clearEl(filterBar);
  clearEl(grid);

  let index;
  try {
    const res = await fetch(`${BASE}index.json`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    index = await res.json();
  } catch {
    append(grid, el('p', { cls: 'empty-state', text: 'Could not load project index. Run the pipeline first.' }));
    return;
  }

  if (!Array.isArray(index) || index.length === 0) {
    append(grid, el('p', { cls: 'empty-state', text: 'No projects tracked yet. Add a folder under projects/.' }));
    return;
  }

  const projects = await Promise.all(index.map(async ({ slug, name }) => {
    try {
      const res = await fetch(`${BASE}${slug}.json`);
      if (!res.ok) return { slug, name, missing: true };
      return { slug, ...(await res.json()) };
    } catch {
      return { slug, name, missing: true };
    }
  }));

  // Category filter chips
  const allCategories = [...new Set(
    projects.flatMap(p => Array.isArray(p.categories) ? p.categories : [])
  )].sort();

  let activeFilters = new Set();

  if (allCategories.length > 0) {
    append(filterBar, el('span', { cls: 'filter-label', text: 'Filter:' }));
    allCategories.forEach(cat => {
      const chip = el('button', { cls: 'chip', text: cat });
      chip.setAttribute('aria-pressed', 'false');
      chip.addEventListener('click', () => {
        if (activeFilters.has(cat)) {
          activeFilters.delete(cat);
          chip.classList.remove('active');
          chip.setAttribute('aria-pressed', 'false');
        } else {
          activeFilters.add(cat);
          chip.classList.add('active');
          chip.setAttribute('aria-pressed', 'true');
        }
        applyFilter();
      });
      filterBar.appendChild(chip);
    });
  }

  // Project cards
  projects.forEach(p => grid.appendChild(buildCard(p)));

  function applyFilter() {
    Array.from(grid.children).forEach((card, i) => {
      const cats = Array.isArray(projects[i].categories) ? projects[i].categories : [];
      card.hidden = activeFilters.size > 0 && !cats.some(c => activeFilters.has(c));
    });
  }
}

function buildCard(p) {
  const a = el('a', { cls: 'project-card', href: `?project=${encodeURIComponent(p.slug)}` });

  // Header row: title + optional breaking badge
  const header = el('div', { cls: 'card-header' });
  append(header, el('span', { cls: 'card-title', text: p.name || p.slug }));
  if (p.breaking_changes) append(header, el('span', { cls: 'badge-breaking', text: '⚠ Breaking' }));
  a.appendChild(header);

  // Description
  if (p.description) {
    a.appendChild(el('p', { cls: 'card-description', text: p.description }));
  } else if (p.missing) {
    a.appendChild(el('p', { cls: 'card-description', text: 'Not yet tracked — run the pipeline to populate data.' }));
  }

  // Category tags
  const cats = Array.isArray(p.categories) ? p.categories : [];
  if (cats.length > 0) {
    const tagList = el('div', { cls: 'tag-list' });
    cats.forEach(c => tagList.appendChild(el('span', { cls: 'tag', text: c })));
    a.appendChild(tagList);
  }

  // Last updated
  if (p.run_at) a.appendChild(el('p', { cls: 'card-meta', text: `Updated ${formatDate(p.run_at)}` }));

  return a;
}

// ── Detail view ──────────────────────────────────────────────────────────────

async function renderDetail(slug) {
  document.getElementById('index-view').hidden = true;
  const detailView = document.getElementById('detail-view');
  detailView.hidden = false;
  clearEl(detailView);
  detailView.appendChild(el('p', { cls: 'loading', text: 'Loading…' }));

  let p;
  try {
    const res = await fetch(`${BASE}${slug}.json`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    p = await res.json();
  } catch {
    clearEl(detailView);
    const crumb = el('div', { cls: 'breadcrumb' });
    const back = el('a', { href: '?', text: '← All projects' });
    crumb.appendChild(back);
    detailView.appendChild(crumb);
    detailView.appendChild(el('p', { cls: 'empty-state', text: 'Project data not found. Run the pipeline for this project.' }));
    return;
  }

  clearEl(detailView);
  const wrapper = el('div', { cls: 'detail-view' });

  // Breadcrumb
  const crumb = el('div', { cls: 'breadcrumb' });
  crumb.appendChild(el('a', { href: '?', text: '← All projects' }));
  wrapper.appendChild(crumb);

  // Header
  const header = el('div', { cls: 'detail-header' });
  header.appendChild(el('h2', { cls: 'detail-title', text: p.name || slug }));
  if (p.description) header.appendChild(el('p', { cls: 'detail-description', text: p.description }));

  // Links
  const linkItems = [];
  if (p.homepage)       linkItems.push({ href: p.homepage,       label: 'Homepage ↗' });
  if (p.repo)           linkItems.push({ href: p.repo,           label: 'Repository ↗' });
  if (p.changelog_url)  linkItems.push({ href: p.changelog_url,  label: 'Changelog ↗' });
  if (Array.isArray(p.links)) p.links.forEach(l => linkItems.push({ href: l.url, label: `${l.label} ↗` }));
  if (linkItems.length > 0) {
    const linksDiv = el('div', { cls: 'detail-links' });
    linkItems.forEach(({ href, label }) => {
      linksDiv.appendChild(el('a', { href, text: label, target: '_blank', rel: 'noopener noreferrer' }));
    });
    header.appendChild(linksDiv);
  }

  // Category tags
  const cats = Array.isArray(p.categories) ? p.categories : [];
  if (cats.length > 0) {
    const tagList = el('div', { cls: 'tag-list' });
    tagList.style.marginTop = '.75rem';
    cats.forEach(c => tagList.appendChild(el('span', { cls: 'tag', text: c })));
    header.appendChild(tagList);
  }

  if (p.run_at) {
    const meta = el('p', { cls: 'card-meta', text: `Last updated: ${formatDate(p.run_at)}` });
    meta.style.marginTop = '.6rem';
    header.appendChild(meta);
  }
  wrapper.appendChild(header);

  // Summary
  if (p.summary) {
    const sec = section('Summary');
    sec.appendChild(el('p', { cls: 'summary-text', text: p.summary }));
    wrapper.appendChild(sec);
  }

  // Breaking change banner
  if (p.breaking_changes) {
    const banner = el('div', { cls: 'breaking-banner' });
    banner.appendChild(el('strong', { text: '⚠ Breaking changes detected' }));
    const excerpts = Array.isArray(p.breaking_excerpts) ? p.breaking_excerpts : [];
    if (excerpts.length > 0) {
      const ul = el('ul');
      excerpts.forEach(x => ul.appendChild(el('li', { text: x })));
      banner.appendChild(ul);
    }
    wrapper.appendChild(banner);
  }

  // Q&A answers
  const answers = p.answers && typeof p.answers === 'object' ? Object.entries(p.answers) : [];
  if (answers.length > 0) {
    const sec = section('Tracked Questions');
    const table = el('table', { cls: 'qa-table' });
    const thead = el('thead');
    const hrow = el('tr');
    hrow.appendChild(el('th', { text: 'Question' }));
    hrow.appendChild(el('th', { text: 'Answer' }));
    thead.appendChild(hrow);
    table.appendChild(thead);
    const tbody = el('tbody');
    answers.forEach(([q, a]) => {
      const row = el('tr');
      row.appendChild(el('td', { text: q }));
      row.appendChild(el('td', { text: String(a) }));
      tbody.appendChild(row);
    });
    table.appendChild(tbody);
    sec.appendChild(table);
    wrapper.appendChild(sec);
  }

  // Alternatives
  const alts = Array.isArray(p.alternatives) ? p.alternatives : [];
  if (alts.length > 0) {
    const sec = section('Alternatives');

    // Collect all feature keys across all alternatives
    const featureKeys = [...new Set(
      alts.flatMap(a => (a.features && typeof a.features === 'object') ? Object.keys(a.features) : [])
    )];

    if (featureKeys.length > 0) {
      // Comparison table
      const table = el('table', { cls: 'alt-table' });
      const thead = el('thead');
      const hrow = el('tr');
      hrow.appendChild(el('th', { text: 'Alternative' }));
      featureKeys.forEach(f => hrow.appendChild(el('th', { text: f })));
      hrow.appendChild(el('th', { text: 'Notes' }));
      thead.appendChild(hrow);
      table.appendChild(thead);

      const tbody = el('tbody');
      alts.forEach(alt => {
        const row = el('tr');
        // Name cell
        const nameCell = el('td');
        if (alt.url) {
          nameCell.appendChild(el('a', { href: alt.url, text: alt.name, target: '_blank', rel: 'noopener noreferrer' }));
        } else {
          nameCell.textContent = alt.name;
        }
        if (alt.source) nameCell.appendChild(el('span', { cls: 'badge-source', text: alt.source }));
        row.appendChild(nameCell);
        // Feature cells
        featureKeys.forEach(f => {
          const val = alt.features ? alt.features[f] : undefined;
          const cell = el('td', { cls: 'alt-feature-cell' });
          cell.textContent = val === true ? '✅' : val === false ? '❌' : '—';
          row.appendChild(cell);
        });
        // Review/notes cell
        row.appendChild(el('td', { cls: 'alt-review', text: alt.review || '' }));
        tbody.appendChild(row);
      });
      table.appendChild(tbody);
      sec.appendChild(table);
    } else {
      // Fallback: plain list when no features data
      const ul = el('ul', { cls: 'alt-list' });
      alts.forEach(alt => {
        const li = el('li', { cls: 'alt-item' });
        const info = el('div', { cls: 'alt-info' });
        const nameEl = el('div', { cls: 'alt-name' });
        if (alt.url) {
          nameEl.appendChild(el('a', { href: alt.url, text: `${alt.name} ↗`, target: '_blank', rel: 'noopener noreferrer' }));
        } else {
          nameEl.textContent = alt.name;
        }
        info.appendChild(nameEl);
        if (alt.review) info.appendChild(el('div', { cls: 'alt-review', text: alt.review }));
        li.appendChild(info);
        if (alt.source) li.appendChild(el('span', { cls: 'badge-source', text: alt.source }));
        ul.appendChild(li);
      });
      sec.appendChild(ul);
    }

    wrapper.appendChild(sec);
  }

  detailView.appendChild(wrapper);
}

function section(title) {
  const div = el('div', { cls: 'section' });
  div.appendChild(el('div', { cls: 'section-title', text: title }));
  return div;
}

// ── Utilities ────────────────────────────────────────────────────────────────

function formatDate(iso) {
  try {
    return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(new Date(iso));
  } catch {
    return iso;
  }
}

// ── Boot ─────────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  document.getElementById('theme-toggle')?.addEventListener('click', toggleTheme);
  route();
  window.addEventListener('popstate', route);
});
