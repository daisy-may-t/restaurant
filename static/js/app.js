document.addEventListener("DOMContentLoaded", () => {
  if (!document.querySelector(".order-page")) return;

  let savedNotes = document.getElementById("order-notes").value;
  let allowUnload = false;
  let updateInProgress = false;
  const notesField = () => document.getElementById("order-notes");
  const hasUnsavedNotes = () => notesField().value !== savedNotes;

  document.addEventListener("input", (event) => {
    if (event.target === notesField()) {
      document.getElementById("notes-warning").hidden = true;
    }
  });

  document.addEventListener("submit", async (event) => {
    const form = event.target;
    if (!form.closest(".order-page") || event.defaultPrevented) return;

    if (form.id !== "notes-form" && hasUnsavedNotes()) {
      event.preventDefault();
      document.getElementById("notes-warning").hidden = false;
      notesField().focus();
      return;
    }

    if (updateInProgress) {
      event.preventDefault();
      return;
    }

    if (!event.submitter) {
      if (form.id === "notes-form") allowUnload = true;
      return;
    }
    event.preventDefault();
    updateInProgress = true;

    const submitter = event.submitter;
    const data = new FormData(form);
    if (submitter.name) data.append(submitter.name, submitter.value);
    const scrollY = window.scrollY;
    submitter.disabled = true;

    try {
      const response = await fetch(form.action, {
        method: "POST",
        body: data,
        credentials: "same-origin",
      });
      const page = new DOMParser().parseFromString(await response.text(), "text/html");
      const nextMain = page.querySelector("main.container");
      if (!response.ok || !nextMain || !nextMain.querySelector(".order-page")) {
        const message = page.querySelector("main p, body p")?.textContent
          || `Could not update the order (${response.status}).`;
        showOrderError(message);
        return;
      }

      document.querySelector("main.container").replaceWith(nextMain);
      document.title = page.title;
      history.replaceState(history.state, "", response.url);
      savedNotes = notesField().value;
      requestAnimationFrame(() => window.scrollTo(0, scrollY));

      const matchingButton = [...document.querySelectorAll(".order-page form button")]
        .find((button) => button.form.action === form.action
          && button.name === submitter.name && button.value === submitter.value);
      if (matchingButton && !matchingButton.disabled) {
        matchingButton.focus({ preventScroll: true });
      }
      const action = submitter.getAttribute("aria-label") || submitter.textContent.trim();
      document.getElementById("order-update-status").textContent = `${action}. Order updated.`;
    } catch {
      showOrderError("Connection lost. Refresh the page to check whether the order changed.");
    } finally {
      submitter.disabled = false;
      updateInProgress = false;
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

function showOrderError(message) {
  let error = document.getElementById("order-action-error");
  if (!error) {
    error = document.createElement("p");
    error.id = "order-action-error";
    error.className = "error-message";
    error.setAttribute("role", "alert");
    document.querySelector(".order-page-heading").after(error);
  }
  error.textContent = message;
}
