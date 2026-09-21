async function updateProgress(problemId, payload) {
    const res = await fetch(`/api/problems/${problemId}/progress`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });
    if (!res.ok) {
        console.error("Failed to update progress", await res.text());
        alert("Could not save changes. Please try again.");
        return null;
    }
    return res.json();
}

document.addEventListener("change", (e) => {
    if (e.target.matches(".status-select")) {
        const problemId = e.target.dataset.problemId;
        updateProgress(problemId, { status: e.target.value });
    }
});

document.addEventListener("click", (e) => {
    if (e.target.matches(".notes-toggle")) {
        const problemId = e.target.dataset.problemId;
        const panel = document.querySelector(`.notes-panel[data-problem-id="${problemId}"]`);
        if (panel) panel.hidden = !panel.hidden;
    }

    if (e.target.matches(".notes-save")) {
        const problemId = e.target.dataset.problemId;
        const textarea = document.querySelector(`.notes-textarea[data-problem-id="${problemId}"]`);
        if (!textarea) return;
        const original = e.target.textContent;
        e.target.textContent = "Saving...";
        updateProgress(problemId, { notes: textarea.value }).then(() => {
            e.target.textContent = "Saved";
            setTimeout(() => { e.target.textContent = original; }, 1200);
        });
    }
});
