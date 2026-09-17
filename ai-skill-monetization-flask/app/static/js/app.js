(function () {
  let entries = []; // {name, proficiency}

  const entryList = document.getElementById('entryList');
  const emptyNote = document.getElementById('emptyNote');
  const runBtn = document.getElementById('runBtn');
  const hiddenInputs = document.getElementById('hiddenInputs');
  const skillInput = document.getElementById('skillInput');
  const addBtn = document.getElementById('addSkillBtn');
  const form = document.getElementById('ledgerForm');

  function addSkill(name) {
    name = (name || '').trim();
    if (!name) return;
    if (entries.some(e => e.name.toLowerCase() === name.toLowerCase())) return;
    entries.push({ name, proficiency: 3 });
    render();
  }

  function render() {
    emptyNote.classList.toggle('hidden', entries.length > 0);
    runBtn.disabled = entries.length === 0;

    entryList.innerHTML = entries.map((e, i) => {
      const dots = [1, 2, 3, 4, 5].map(n =>
        `<button type="button" class="dot ${n <= e.proficiency ? 'filled' : ''}" data-i="${i}" data-n="${n}" title="${n}/5"></button>`
      ).join('');
      return `<div class="entry">
        <div class="entry-name">${escapeHtml(e.name)}</div>
        <div class="dots">${dots}</div>
        <button type="button" class="entry-remove" data-remove="${i}" title="Remove">×</button>
      </div>`;
    }).join('');

    entryList.querySelectorAll('.dot').forEach(dot => {
      dot.addEventListener('click', () => {
        const i = parseInt(dot.dataset.i, 10), n = parseInt(dot.dataset.n, 10);
        entries[i].proficiency = n;
        render();
      });
    });
    entryList.querySelectorAll('[data-remove]').forEach(btn => {
      btn.addEventListener('click', () => {
        entries.splice(parseInt(btn.dataset.remove, 10), 1);
        render();
      });
    });
  }

  function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  function syncHiddenInputs() {
    hiddenInputs.innerHTML = entries.map(e =>
      `<input type="hidden" name="skill_name[]" value="${escapeHtml(e.name)}">` +
      `<input type="hidden" name="skill_proficiency[]" value="${e.proficiency}">`
    ).join('');
  }

  addBtn.addEventListener('click', () => {
    addSkill(skillInput.value);
    skillInput.value = '';
    skillInput.focus();
  });

  skillInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      addSkill(skillInput.value);
      skillInput.value = '';
    }
  });

  form.addEventListener('submit', (e) => {
    if (entries.length === 0) {
      e.preventDefault();
      return;
    }
    syncHiddenInputs();
  });

  render();
})();
