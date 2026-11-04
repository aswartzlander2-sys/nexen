/* Display this installation's local identifier without embedding it in the source. */
fetch('/__nexen/meta', {cache:'no-store'})
  .then(r => { if (!r.ok) throw new Error('metadata unavailable'); return r.json(); })
  .then(meta => {
    if (typeof meta.version === 'string') document.querySelectorAll('[data-nexen-version]').forEach(el => { el.textContent = meta.version; });
    if (!/^\d{6}$/.test(meta.id)) return;
    document.querySelectorAll('[data-nexen-id]').forEach(el => { el.textContent = ' • ' + meta.id; });
  }).catch(() => {});
