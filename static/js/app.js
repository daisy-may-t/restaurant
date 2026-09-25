document.addEventListener("DOMContentLoaded", () => {
  const notes = document.getElementById("order-notes");
  if (!notes) return;

  const notesForm = document.getElementById("notes-form");
  const warning = document.getElementById("notes-warning");
  const savedNotes = notes.value;
  let allowUnload = false;
  const hasUnsavedNotes = () => notes.value !== savedNotes;

  notes.addEventListener("input", () => {
    warning.hidden = true;
  });

  document.addEventListener("submit", (event) => {
    if (event.target === notesForm) {
      allowUnload = true;
    } else if (hasUnsavedNotes()) {
      event.preventDefault();
      warning.hidden = false;
      notes.focus();
    }
  });

  document.addEventListener("click", (event) => {
    const link = event.target.closest("a[href]");
    if (link && hasUnsavedNotes()) {
      allowUnload = window.confirm("You have unsaved notes. Leave this page?");
      if (!allowUnload) event.preventDefault();
    }
  });

  window.addEventListener("beforeunload", (event) => {
    if (hasUnsavedNotes() && !allowUnload) {
      event.preventDefault();
      event.returnValue = "";
    }
  });
});
