/*
  PhishGuard Gmail content script (Manifest V3)
  - Detects email cards/rows in Gmail UI
  - Extracts sender/subject/snippet heuristically
  - Calls local backend to classify
  - Renders a red “PHISHING” pill next to suspicious emails
*/

(() => {
  console.debug('[PhishGuard] content script loaded');

  const PHISHING_CLASS = 'phishguard-phishing-pill';
  const DONE_MARK = 'data-phishguard-processed';

  const state = {
    // cache key -> classification result
    cache: new Map(),
    // keep track of active in-flight requests to dedupe
    inflight: new Map(),
  };

  function getText(el) {
    if (!el) return '';
    return (el.textContent || '').trim();
  }

  function normalizeKey(parts) {
    return parts
      .map(p => (p || '').toLowerCase().replace(/\s+/g, ' ').trim())
      .join('|');
  }

  function ensurePill(container, text) {
    // Avoid duplicates
    if (container.querySelector(`.${PHISHING_CLASS}`)) return;

    const pill = document.createElement('div');
    pill.className = PHISHING_CLASS;
    pill.textContent = text;

    const styles = `
      background: #dc3545;
      color: #fff;
      font-weight: 700;
      font-size: 11px;
      padding: 3px 8px;
      border-radius: 999px;
      margin-left: 8px;
      display: inline-flex;
      align-items: center;
      gap: 6px;
      box-shadow: 0 1px 2px rgba(0,0,0,0.15);
      user-select: none;
    `;
    pill.setAttribute('style', styles);

    container.appendChild(pill);
  }

  function findMessageRows() {
    // Gmail DOM changes over time; this is a best-effort set of selectors.
    // Target the clickable row/card elements.
    const candidates = document.querySelectorAll('tr.zA, tr[role="row"], div.UI, div[role="button"], div[role="row"]');
    return Array.from(candidates).filter(el => el && el.offsetParent !== null);
  }

  function extractFromRow(row) {
    // Heuristic extraction:
    // sender: look for something that resembles email and is short
    // subject: typically appears in bold/strong/span
    // snippet: preview text in the row

    const text = (row.innerText || '').replace(/\s+/g, ' ').trim();
    if (!text) return null;

    // crude email pattern
    const emailMatch = text.match(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/i);
    const from = emailMatch ? emailMatch[0] : '';

    // subject often appears before snippet; use first ~120 chars as subject-ish
    const subject = text.slice(0, 120);

    // snippet-ish: last ~140 chars
    const snippet = text.slice(-140);

    return { from, subject, snippet, rawText: text };
  }

  async function classify({ email_text, email_address }) {
    console.debug('[PhishGuard] classify request', { email_address, email_text_len: (email_text || '').length });
    const cacheKey = normalizeKey([email_text, email_address]);
    if (state.cache.has(cacheKey)) return state.cache.get(cacheKey);
    if (state.inflight.has(cacheKey)) return state.inflight.get(cacheKey);

    const p = new Promise((resolve, reject) => {
      chrome.runtime.sendMessage(
        { type: 'CLASSIFY_EMAIL', payload: { email_text, email_address } },
        (response) => {
          if (chrome.runtime.lastError) {
            return reject(new Error(chrome.runtime.lastError.message));
          }
          if (!response) {
            return reject(new Error('No response from background script'));
          }
          if (!response.success) {
            return reject(new Error(response.error || 'Unknown error from background script'));
          }
          const data = response.data;
          const out = {
            classification: data.classification,
            probability: data.probability,
            risk_score: data.risk_score,
            reasoning: data.reasoning
          };
          state.cache.set(cacheKey, out);
          resolve(out);
        }
      );
    });

    state.inflight.set(cacheKey, p);
    try {
      const result = await p;
      return result;
    } finally {
      state.inflight.delete(cacheKey);
    }
  }

  function shouldMarkAsPhishing(result) {
    // Align with backend: classification is exactly 'Phishing' (case-insensitive)
    return (result?.classification || '').toLowerCase() === 'phishing';
  }

  async function processRow(row) {
    if (row.getAttribute(DONE_MARK) === '1') return;

    const extracted = extractFromRow(row);
    if (!extracted) {
      row.setAttribute(DONE_MARK, '1');
      return;
    }

    const email_text = `${extracted.subject} ${extracted.snippet}`.trim();
    const email_address = extracted.from;

    // If no meaningful text, skip
    if (!email_text || email_text.length < 20) {
      row.setAttribute(DONE_MARK, '1');
      return;
    }

    try {
      const result = await classify({ email_text, email_address });
      const clickableHeader = row; // fallback: append pill to row itself

      if (shouldMarkAsPhishing(result)) {
        ensurePill(clickableHeader, `PHISHING (${Math.round((result.probability || 0) * 100)}%)`);
      }

      // Mark processed even if legit to avoid repeated calls
      row.setAttribute(DONE_MARK, '1');
    } catch (e) {
      // Don't permanently mark failed nodes; but avoid rapid loops.
      row.setAttribute(DONE_MARK, '1');
      console.warn('[PhishGuard] classify failed', e);
    }
  }

  function start() {
    const runOnce = () => {
      const rows = findMessageRows();
      console.debug('[PhishGuard] rows found:', rows.length);

      // Only process a limited number per tick to avoid freezing.
      rows.slice(0, 15).forEach(r => processRow(r));
    };

    // Run immediately
    runOnce();

    // Also run every 5 seconds to catch new emails that might not trigger DOM mutations
    setInterval(runOnce, 5000);

    const observer = new MutationObserver(() => {
      // Debounce by scheduling next frame
      if (observer.__scheduled) return;
      observer.__scheduled = true;
      requestAnimationFrame(() => {
        observer.__scheduled = false;
        runOnce();
      });
    });

    observer.observe(document.documentElement, { childList: true, subtree: true });
  }

  start();
})();

