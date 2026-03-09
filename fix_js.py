import sys

filepath = r"c:\Users\prave\Downloads\ANTIGRAVITY\QLM 3\frontend\js\views\DataView.js"

with open(filepath, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Keep everything up to line 298 (0-indexed 297, which is '            windowBody.querySelectorAll('.btn-save-row').forEach(btn => {')
good_lines = lines[:298]

new_code = """            windowBody.querySelectorAll('.btn-save-row').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const tr = e.currentTarget.closest('tr');
                    this.saveRowEdit(datasetId, tr);
                });
            });

            windowBody.querySelectorAll('.btn-delete-row').forEach(btn => {
                btn.addEventListener('click', async (e) => {
                    if (!confirm("Delete this row entirely from the Parquet dataset?")) return;
                    const index = parseInt(e.currentTarget.closest('tr').dataset.rowIndex);
                    try {
                        await dataService.deleteRow(datasetId, index);
                        if (window.Toast) window.Toast.success("Row deleted permanently.");
                        this.openDiscrepancyModal(datasetId); // Refresh
                    } catch (err) {
                        if (window.Toast) window.Toast.error("Delete failed: " + err.message);
                    }
                });
            });

            windowBody.querySelectorAll('.btn-interp-row').forEach(btn => {
                btn.addEventListener('click', async (e) => {
                    if (!confirm("Auto-interpolate missing bars into this gap? This will modify the sequence bounds.")) return;
                    const index = parseInt(e.currentTarget.closest('tr').dataset.rowIndex);
                    try {
                        const r = await dataService.interpolateGap(datasetId, index);
                        if (window.Toast) window.Toast.success(r.message || "Gap filled.");
                        this.openDiscrepancyModal(datasetId); // Refresh
                    } catch (err) {
                        if (window.Toast) window.Toast.error("Interp failed: " + err.message);
                    }
                });
            });

            windowBody.querySelectorAll('.btn-autofix-row').forEach(btn => {
                btn.addEventListener('click', async (e) => {
                    const index = parseInt(e.currentTarget.closest('tr').dataset.rowIndex);
                    try {
                        await dataService.autofixRow(datasetId, index);
                        if (window.Toast) window.Toast.success("Logic inverted automatically.");
                        this.openDiscrepancyModal(datasetId); // Refresh
                    } catch (err) {
                        if (window.Toast) window.Toast.error("Autofix failed: " + err.message);
                    }
                });
            });

            if (window.Toast && discrepancyType) {
                 window.Toast.info(`Inspecting ${discrepancyType} at row ${index}`);
            }

        } catch (e) {
            if (window.Toast) window.Toast.error("Failed to load context: " + e.message);
            detailView.classList.add('hidden');
        } finally {
            windowLoading.classList.add('hidden');
        }
    }

    async saveRowEdit(datasetId, tr) {
        const index = parseInt(tr.dataset.rowIndex);
        const btn = tr.querySelector('.btn-save-row');

        const updates = {
            open: parseFloat(tr.querySelector('[data-field="open"]').value),
            high: parseFloat(tr.querySelector('[data-field="high"]').value),
            low: parseFloat(tr.querySelector('[data-field="low"]').value),
            close: parseFloat(tr.querySelector('[data-field="close"]').value),
            volume: parseFloat(tr.querySelector('[data-field="volume"]').value)
        };

        const originalText = btn.innerHTML;
        btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i>`;
        btn.disabled = true;

        try {
            await dataService.updateRow(datasetId, index, updates);
            if (window.Toast) window.Toast.success(`Row ${index} successfully updated in Parquet file`);
            this.openDiscrepancyModal(datasetId);
        } catch (e) {
            if (window.Toast) window.Toast.error("Failed to update row: " + e.message);
        } finally {
            btn.innerHTML = originalText;
            btn.disabled = false;
        }
    }

    async inspectCustomRow(datasetId, query) {
        const inputField = document.getElementById('inspect-row-input');
        const btnInspect = document.getElementById('btn-inspect-row');
        
        if (btnInspect) {
            btnInspect.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i>`;
            btnInspect.disabled = true;
        }

        try {
            const res = await dataService.inspectRow(datasetId, query);
            if (res.target_index !== undefined) {
                if (window.Toast) window.Toast.success(`Found Dataset Match at Row ${res.target_index}`);
                await this.openContextWindow(datasetId, res.target_index, "CUSTOM_INSPECT");
            }
        } catch (e) {
            if (window.Toast) window.Toast.error("Could not find row: " + (e.response?.data?.detail || e.message));
        } finally {
            if (btnInspect) {
                btnInspect.innerHTML = `Inspect`;
                btnInspect.disabled = false;
            }
            if (inputField) inputField.value = '';
        }
    }
}
"""

with open(filepath, "w", encoding="utf-8") as f:
    f.writelines(good_lines)
    f.write(new_code)
