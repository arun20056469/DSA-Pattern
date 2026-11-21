(function () {
    "use strict";

    async function updateProgress(problemId, payload) {
        const res = await fetch(`/api/problems/${problemId}/progress`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });
        if (!res.ok) {
            const detail = await res.text();
            throw new Error(detail || `Request failed with ${res.status}`);
        }
        return res.json();
    }

    function marginCell(problemId) {
        return document.querySelector(`.margin-cells .cell[data-problem-id="${problemId}"]`);
    }

    function updateCellLabel(cell, status, due) {
        const row = document.querySelector(`.problem-row[data-problem-id="${cell.dataset.problemId}"]`);
        if (!row) return;
        const nameEl = row.querySelector(".problem-name");
        const difficultyEl = row.querySelector(".difficulty");
        const name = nameEl ? nameEl.textContent.trim() : "Problem";
        const difficulty = difficultyEl ? difficultyEl.textContent.trim() : "";
        const statusLabel = status.replace("_", " ");
        const label = `${name}, ${difficulty}, ${statusLabel}${due ? ", due for review" : ""}`;
        cell.title = label;
        cell.setAttribute("aria-label", label);
    }

    function paintCell(cell, status, due) {
        if (!cell) return;
        cell.classList.toggle("is-solved", status === "solved");
        cell.classList.toggle("is-attempted", status === "attempted");
        cell.classList.toggle("is-due", Boolean(due));
        updateCellLabel(cell, status, due);
    }

    function refreshMarginCounts() {
        const cells = Array.from(document.querySelectorAll(".margin-cells .cell"));
        if (!cells.length) return;
        const counts = { solved: 0, attempted: 0, not_started: 0 };
        cells.forEach((cell) => {
            if (cell.classList.contains("is-solved")) counts.solved += 1;
            else if (cell.classList.contains("is-attempted")) counts.attempted += 1;
            else counts.not_started += 1;
        });
        Object.keys(counts).forEach((key) => {
            document.querySelectorAll(`[data-count="${key}"]`).forEach((target) => {
                target.textContent = String(counts[key]);
            });
        });
    }

    function setStatus(row, status, due) {
        row.dataset.status = status;
        row.querySelectorAll(".status-control button").forEach((button) => {
            button.setAttribute("aria-pressed", String(button.dataset.status === status));
        });
        paintCell(marginCell(row.dataset.problemId), status, due);
        refreshMarginCounts();
    }

    function showRowError(row, message) {
        const error = row.querySelector(".row-error");
        if (!error) return;
        error.textContent = message;
        error.hidden = false;
    }

    function clearRowError(row) {
        const error = row.querySelector(".row-error");
        if (!error) return;
        error.textContent = "";
        error.hidden = true;
    }

    document.addEventListener("click", async (event) => {
        const statusButton = event.target.closest(".status-control button");
        if (statusButton) {
            const row = statusButton.closest(".problem-row");
            if (!row) return;
            const nextStatus = statusButton.dataset.status;
            const previousStatus = row.dataset.status;
            if (!nextStatus || nextStatus === previousStatus) return;

            const buttons = Array.from(row.querySelectorAll(".status-control button"));
            const cell = marginCell(row.dataset.problemId);
            const wasDue = cell ? cell.classList.contains("is-due") : false;
            clearRowError(row);
            setStatus(row, nextStatus, false);
            buttons.forEach((button) => { button.disabled = true; });

            try {
                await updateProgress(row.dataset.problemId, { status: nextStatus });
            } catch (error) {
                setStatus(row, previousStatus, wasDue);
                showRowError(row, "Couldn't save the status. Check the server and try again.");
            } finally {
                buttons.forEach((button) => { button.disabled = false; });
            }
            return;
        }

        const notesToggle = event.target.closest(".notes-toggle");
        if (notesToggle) {
            const id = notesToggle.dataset.problemId;
            const notesRow = document.querySelector(`.notes-row[data-notes-for="${id}"]`);
            if (!notesRow) return;
            const willOpen = notesRow.hidden;
            notesRow.hidden = !willOpen;
            notesToggle.setAttribute("aria-expanded", String(willOpen));
            if (willOpen) {
                const textarea = notesRow.querySelector(".notes-textarea");
                if (textarea) textarea.focus();
            }
            return;
        }

        const saveButton = event.target.closest(".notes-save");
        if (saveButton) {
            const panel = saveButton.closest(".notes-panel");
            if (!panel) return;
            const textarea = panel.querySelector(".notes-textarea");
            const status = panel.querySelector(".notes-status");
            if (!textarea) return;

            saveButton.disabled = true;
            if (status) {
                status.dataset.state = "";
                status.textContent = "Saving...";
            }

            try {
                await updateProgress(panel.dataset.problemId, { notes: textarea.value });
                if (status) {
                    status.dataset.state = "saved";
                    status.textContent = "Saved";
                }
            } catch (error) {
                if (status) {
                    status.dataset.state = "error";
                    status.textContent = "Couldn't save. Check the server and try again.";
                }
            } finally {
                saveButton.disabled = false;
            }
        }
    });

    document.querySelectorAll(".filters select").forEach((select) => {
        select.addEventListener("change", () => {
            if (select.form) select.form.requestSubmit();
        });
    });

    function toast(message) {
        const stack = document.getElementById("toast-stack");
        if (!stack) return;
        const node = document.createElement("div");
        node.className = "toast";
        node.textContent = message;
        stack.appendChild(node);
        setTimeout(() => node.remove(), 2600);
    }

    function initTheme() {
        const root = document.documentElement;
        const button = document.querySelector(".theme-toggle");
        const saved = localStorage.getItem("dsa-theme");
        if (saved === "dark" || saved === "light") root.dataset.theme = saved;
        if (!button) return;
        button.addEventListener("click", () => {
            const next = root.dataset.theme === "dark" ? "light" : "dark";
            root.dataset.theme = next;
            localStorage.setItem("dsa-theme", next);
        });
    }

    function initMobileNav() {
        const button = document.querySelector(".mobile-nav-toggle");
        const sidebar = document.querySelector(".sidebar");
        if (!button || !sidebar) return;
        button.addEventListener("click", () => {
            const open = sidebar.classList.toggle("is-open");
            button.setAttribute("aria-expanded", String(open));
        });
    }

    function initGlobalSearch() {
        const input = document.getElementById("global-search");
        if (!input) return;
        document.addEventListener("keydown", (event) => {
            const tag = document.activeElement ? document.activeElement.tagName : "";
            const typing = tag === "INPUT" || tag === "TEXTAREA" || document.activeElement?.isContentEditable;
            if (event.key === "/" && !typing) {
                event.preventDefault();
                input.focus();
            }
        });
    }

    function initCopyButtons() {
        document.querySelectorAll(".copy-button").forEach((button) => {
            button.addEventListener("click", async () => {
                const target = button.dataset.copy ? document.querySelector(button.dataset.copy) : null;
                if (!target) return;
                try {
                    await navigator.clipboard.writeText(target.textContent.trim());
                    toast("Template copied");
                } catch (error) {
                    toast("Copy failed — select the code manually");
                }
            });
        });
    }

    function initReviewButtons() {
        document.querySelectorAll(".review-done").forEach((button) => {
            button.addEventListener("click", async () => {
                const item = button.closest(".review-item");
                if (!item) return;
                button.disabled = true;
                try {
                    const res = await fetch(`/api/problems/${button.dataset.problemId}/review`, {
                        method: "POST",
                    });
                    if (!res.ok) throw new Error(`Request failed with ${res.status}`);
                    item.classList.add("is-complete");
                    toast("Review logged — next date scheduled");
                    setTimeout(() => item.remove(), 700);
                } catch (error) {
                    button.disabled = false;
                    toast("Couldn't log review. Try again.");
                }
            });
        });
    }

    initTheme();
    initMobileNav();
    initGlobalSearch();
    initCopyButtons();
    initReviewButtons();
})();
