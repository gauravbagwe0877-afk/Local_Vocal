/**
 * Hotel Sawant Palace PMS — Frontend Interactions
 * Handles modals, real-time form validation, table sorting, filter chips, loading spinners
 */

document.addEventListener('DOMContentLoaded', () => {
    // ── 1. MODAL CONTROLS ────────────────────────────────────────────────────────
    window.openModal = function(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.add('active');
            document.body.style.overflow = 'hidden';
            // focus first input if available
            const input = modal.querySelector('input:not([type="hidden"]), select, textarea');
            if (input) setTimeout(() => input.focus(), 100);
        }
    };

    window.closeModal = function(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.remove('active');
            document.body.style.overflow = '';
        }
    };

    // Close on overlay backdrop click
    document.querySelectorAll('.pms-modal-overlay').forEach(overlay => {
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) {
                overlay.classList.remove('active');
                document.body.style.overflow = '';
            }
        });
    });

    // Close on Esc key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            document.querySelectorAll('.pms-modal-overlay.active').forEach(modal => {
                modal.classList.remove('active');
            });
            document.body.style.overflow = '';
        }
    });

    // ── 2. TYPE-TO-CONFIRM DELETION MODALS ───────────────────────────────────────
    window.openConfirmDeleteModal = function(formAction, itemName, confirmWord = 'DELETE') {
        let modal = document.getElementById('confirmDeleteModal');
        if (!modal) {
            modal = document.createElement('div');
            modal.id = 'confirmDeleteModal';
            modal.className = 'pms-modal-overlay';
            modal.innerHTML = `
                <div class="pms-modal-container" style="max-width: 480px;">
                    <div class="pms-modal-header">
                        <h3 style="color: var(--color-danger);">⚠️ Permanent Deletion</h3>
                        <button class="pms-modal-close" onclick="closeModal('confirmDeleteModal')">&times;</button>
                    </div>
                    <form id="confirmDeleteForm" method="POST">
                        <p style="font-size: 0.95rem; line-height: 1.5;">
                            Are you absolutely sure you want to delete <strong id="deleteItemName" style="color:var(--color-danger);"></strong>?
                            This action cannot be undone.
                        </p>
                        <p style="font-size: 0.85rem; color: var(--color-muted); margin-bottom: 12px;">
                            To confirm, please type <code id="deleteConfirmWord" style="font-family:var(--font-mono); font-weight:700; color:var(--color-danger);">${confirmWord}</code> below:
                        </p>
                        <div class="pms-floating-label">
                            <input type="text" id="confirmDeleteInput" placeholder=" " required autocomplete="off">
                            <label>Confirmation phrase</label>
                        </div>
                        <div class="pms-form-actions">
                            <button type="button" class="btn-pms btn-pms-outline" onclick="closeModal('confirmDeleteModal')">Cancel</button>
                            <button type="submit" id="confirmDeleteSubmitBtn" class="btn-pms btn-pms-primary" style="background-color:var(--color-danger);" disabled>
                                Delete Permanently
                            </button>
                        </div>
                    </form>
                </div>
            `;
            document.body.appendChild(modal);
        }

        const form = document.getElementById('confirmDeleteForm');
        form.action = formAction;
        document.getElementById('deleteItemName').textContent = itemName;
        document.getElementById('deleteConfirmWord').textContent = confirmWord;

        const input = document.getElementById('confirmDeleteInput');
        const submitBtn = document.getElementById('confirmDeleteSubmitBtn');
        input.value = '';
        submitBtn.disabled = true;

        input.oninput = () => {
            submitBtn.disabled = (input.value.trim() !== confirmWord);
        };

        openModal('confirmDeleteModal');
    };

    // ── 3. FORM VALIDATION & SUBMIT SPINNERS ─────────────────────────────────────
    document.querySelectorAll('form').forEach(form => {
        form.addEventListener('submit', function(e) {
            if (!this.checkValidity()) {
                e.preventDefault();
                this.reportValidity();
                return;
            }

            // Disable submit button and show loading spinner
            const submitBtn = this.querySelector('button[type="submit"]:not([disabled])');
            if (submitBtn && !this.dataset.noSpinner) {
                const originalHtml = submitBtn.innerHTML;
                submitBtn.disabled = true;
                submitBtn.innerHTML = `
                    <svg style="animation: spin 0.8s linear infinite; width:16px; height:16px; vertical-align:middle; display:inline-block;" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <circle cx="12" cy="12" r="10" stroke-opacity="0.25"></circle>
                        <path d="M12 2a10 10 0 0 1 10 10" stroke-linecap="round"></path>
                    </svg>
                    <span>Processing...</span>
                `;

                // Add keyframes if not present
                if (!document.getElementById('pms-spinner-style')) {
                    const style = document.createElement('style');
                    style.id = 'pms-spinner-style';
                    style.textContent = '@keyframes spin { 100% { transform: rotate(360deg); } }';
                    document.head.appendChild(style);
                }

                // If submission doesn't redirect immediately (e.g., error), allow reset after timeout
                setTimeout(() => {
                    if (submitBtn.disabled) {
                        submitBtn.disabled = false;
                        submitBtn.innerHTML = originalHtml;
                    }
                }, 8000);
            }
        });
    });

    // ── 4. TABLE SORTING ────────────────────────────────────────────────────────
    document.querySelectorAll('.pms-table thead th.sortable').forEach((header, index) => {
        header.addEventListener('click', () => {
            const table = header.closest('table');
            const tbody = table.querySelector('tbody');
            const rows = Array.from(tbody.querySelectorAll('tr'));
            const isAsc = header.dataset.sortOrder !== 'asc';

            rows.sort((rowA, rowB) => {
                const cellA = rowA.children[index]?.innerText.trim() || '';
                const cellB = rowB.children[index]?.innerText.trim() || '';

                const numA = parseFloat(cellA.replace(/[^0-9.-]+/g, ''));
                const numB = parseFloat(cellB.replace(/[^0-9.-]+/g, ''));

                if (!isNaN(numA) && !isNaN(numB)) {
                    return isAsc ? numA - numB : numB - numA;
                }
                return isAsc ? cellA.localeCompare(cellB) : cellB.localeCompare(cellA);
            });

            header.dataset.sortOrder = isAsc ? 'asc' : 'desc';
            tbody.innerHTML = '';
            rows.forEach(r => tbody.appendChild(r));
        });
    });

    // ── 5. LIVE SEARCH ON DATA TABLES ───────────────────────────────────────────
    document.querySelectorAll('.pms-search-input input').forEach(searchInput => {
        const targetTableSelector = searchInput.dataset.targetTable || '.pms-table tbody';
        const tbody = document.querySelector(targetTableSelector);
        if (!tbody) return;

        searchInput.addEventListener('input', (e) => {
            const query = e.target.value.toLowerCase().trim();
            const rows = tbody.querySelectorAll('tr');

            rows.forEach(row => {
                const text = row.innerText.toLowerCase();
                row.style.display = text.includes(query) ? '' : 'none';
            });
        });
    });
});

