// Automatically detect the correct API backend URL:
// 1. If running on local Live Server or local file system, point to local FastAPI on port 8000.
// 2. Otherwise, use relative paths (if frontend and backend are hosted together on Render).
const getBackendUrl = () => {
    const origin = window.location.origin;
    if (origin.includes("127.0.0.1:5") || origin.includes("localhost:5") || window.location.protocol === "file:") {
        return "http://127.0.0.1:8000";
    }
    if (origin.includes("netlify.app")) {
        return "https://smart-employee-onboarder.onrender.com";
    }
    return ""; // Relative path
};

const BACKEND_URL = getBackendUrl();
const API = `${BACKEND_URL}/employees`;


const formFields = {
    name: document.getElementById("name"),
    email: document.getElementById("email"),
    qualification: document.getElementById("qualification"),
    dob: document.getElementById("date_of_birth"),
    location: document.getElementById("location")
};

const table = document.querySelector("#table tbody");
const btnSave = document.getElementById("btnSave");
const employeeModal = new bootstrap.Modal(document.getElementById('employeeModal'));

const aiModal = new bootstrap.Modal(document.getElementById('aiModal'));
const btnSendToAi = document.getElementById("btnSendToAi");
const aiEmailInput = document.getElementById("aiEmailInput");
const aiChatHistory = document.getElementById("aiChatHistory");

const btnSendInitiatorEmail = document.getElementById("btnSendInitiatorEmail");
const candidateEmailInput = document.getElementById("candidateEmailInput");
const emailInitiatorModal = new bootstrap.Modal(document.getElementById('emailInitiatorModal'));

let currentEditId = null;
let aiThreadId = null; // Tracks the current conversation context
let allEmployees = [];
let currentPage = 1;
const pageSize = 10;


// ---------------- ERROR HANDLING ----------------
function handleError(error, status) {
    if (error && (error.message === "Failed to fetch" || error.message.includes("NetworkError"))) {
        return "Server is unreachable. Please ensure the backend server is running.";
    }

    if (status === 404) return "Employee not found (404)";
    if (status === 422) return "Validation error (422)";
    if (status === 500) return "Server error (500)";
    if (status === 400) return "Bad Request (400)";

    if (error && error.message) return error.message;
    if (!status) return "An unexpected error occurred.";
    return `Unexpected error (${status})`;
}


// ---------------- TOAST ----------------
function showToast(message, type = "danger", delay = 5000) {
    const toastEl = document.getElementById("liveToast");
    const toastBody = document.getElementById("toastBody");

    // Replace \n with <br> for multi-line display
    const formattedMessage = message.replace(/\n/g, '<br>');
    toastBody.innerHTML = formattedMessage;
    toastEl.className = `toast align-items-center text-bg-${type} border-0`;

    const toast = new bootstrap.Toast(toastEl, { delay: delay });
    toast.show();
}


// ---------------- MODAL ----------------
function openModal() {
    currentEditId = null;
    clearForm();
    document.getElementById("employee-form").classList.remove('was-validated');
    document.getElementById("employeeModalLabel").textContent = "Add New Employee";
    btnSave.textContent = "Save Employee";
    employeeModal.show();
}

function closeModal() {
    employeeModal.hide();
}


// ---------------- FORM HELPERS ----------------
function getFormData() {
    return {
        name: formFields.name.value.trim(),
        email: formFields.email.value.trim(),
        qualification: formFields.qualification.value.trim(),
        date_of_birth: formFields.dob.value.trim(),
        location: formFields.location.value.trim()
    };
}

function setFormData(data) {
    if (data.name !== undefined) formFields.name.value = data.name;
    if (data.email !== undefined) formFields.email.value = data.email;
    if (data.qualification !== undefined) formFields.qualification.value = data.qualification;
    if (data.date_of_birth !== undefined) formFields.dob.value = data.date_of_birth;
    if (data.location !== undefined) formFields.location.value = data.location;
}

function clearForm() {
    Object.values(formFields).forEach(f => f.value = "");
}

// Resilient fetch with automatic retry policy for Render cold starts
async function fetchWithRetry(url, options = {}, maxRetries = 10, delayMs = 5000) {
    const warmUpAlert = document.getElementById("renderWarmUpAlert");
    const isRender = url.includes("onrender.com");

    for (let attempt = 1; attempt <= maxRetries; attempt++) {
        try {
            const res = await fetch(url, options);
            if (res.ok || res.status < 500) {
                if (warmUpAlert) warmUpAlert.classList.add("d-none");
                return res;
            }
            throw new Error(`Server returned status ${res.status}`);
        } catch (error) {
            console.warn(`Connection attempt ${attempt} failed:`, error);
            
            // If it's a local address or we've reached max retries, fail instantly (don't waste time)
            if (!isRender || attempt === maxRetries) {
                if (warmUpAlert) warmUpAlert.classList.add("d-none");
                throw error;
            }

            // Show the warm-up alert card and update status text dynamically
            if (warmUpAlert) {
                warmUpAlert.classList.remove("d-none");
                const alertText = warmUpAlert.querySelector(".text-muted");
                if (alertText) {
                    alertText.innerHTML = `Deployed on Render's Free tier. The server automatically sleeps during inactivity. <br><strong>Initiating server wake-up: Attempt ${attempt}/${maxRetries}</strong>. Retrying connection in ${delayMs/1000} seconds. Please standby...`;
                }
            }

            // Wait for delayMs before retrying
            await new Promise(resolve => setTimeout(resolve, delayMs));
        }
    }
}

// ---------------- LOAD EMPLOYEES ----------------
async function displayEmployees() {
    table.innerHTML = `
        <tr>
            <td colspan="12" class="text-center py-5 text-muted">
                <div class="spinner-border text-secondary mb-3" role="status"></div>
                <div class="mt-2 small fw-semibold text-secondary">Loading Employee Database...</div>
            </td>
        </tr>
    `;

    const warmUpAlert = document.getElementById("renderWarmUpAlert");
    if (warmUpAlert) warmUpAlert.classList.add("d-none");

    try {
        const res = await fetchWithRetry(API, {}, 10, 5000);

        if (warmUpAlert) warmUpAlert.classList.add("d-none");

        if (!res.ok) {
            let errorMessage = handleError(null, res.status);
            try {
                const errData = await res.json();
                if (res.status === 422 && errData.detail) {
                    const errors = errData.detail.map(err => {
                        const field = err.loc[err.loc.length - 1];
                        return `${field}: ${err.msg}`;
                    });
                    errorMessage = `Validation errors:\n${errors.join('\n')}`;
                } else if (errData?.message) {
                    errorMessage = errData.message;
                }
            } catch (e) { }
            throw new Error(errorMessage);
        }

        const data = await res.json();
        allEmployees = data;
        renderTable();
        console.log("Employees loaded:", data);
    } catch (error) {
        if (warmUpAlert) warmUpAlert.classList.add("d-none");

        console.error("Error loading employees:", error);
        showToast("Failed to load employees: " + handleError(error, null), "danger");

        table.innerHTML = `
            <tr>
                <td colspan="12" class="text-center py-4 text-danger">
                    <i class="bi bi-exclamation-triangle fs-4 d-block mb-2"></i>
                    Failed to connect to the server.
                </td>
            </tr>
        `;
    }
}


// ---------------- RENDER TABLE ----------------
function renderTable() {
    table.innerHTML = "";

    if (allEmployees.length === 0) {
        table.innerHTML = `
            <tr>
                <td colspan="12" class="text-center py-4 text-muted">
                    <i class="bi bi-inbox fs-4 d-block mb-2"></i>
                    No employees found
                </td>
            </tr>
        `;
        document.getElementById("pageInfo").textContent = "Showing 0 entries";
        document.getElementById("btnPrevPage").classList.add("disabled");
        document.getElementById("btnNextPage").classList.add("disabled");
        return;
    }

    const totalPages = Math.ceil(allEmployees.length / pageSize);
    if (currentPage > totalPages) currentPage = totalPages;

    const start = (currentPage - 1) * pageSize;
    const end = start + pageSize;
    const paginatedData = allEmployees.slice(start, end);

    paginatedData.forEach(emp => {
        const row = document.createElement("tr");

        // const date = new Date(emp.date_of_birth); // Your date source

        // const editedFormatDate = new Intl.DateTimeFormat('en-US', {
        //     month: '2-digit',
        //     day: '2-digit',
        //     year: '2-digit'
        // }).format(date);


        row.innerHTML = `
            <td>${emp.id || ""}</td>
            <td>${emp.name || ""}</td>
            <td>${emp.qualification || ""}</td>
            <td>${emp.email || ""}</td>
            <td>${emp.date_of_birth || ""}</td>
            <td>${emp.location || ""}</td>
            <td></td>
        `;

        const actionCell = row.querySelector("td:last-child");

        const editBtn = document.createElement("button");
        editBtn.className = "btn btn-sm btn-outline-primary me-2";
        editBtn.innerHTML = "<i class='bi bi-pencil-square'></i>";
        editBtn.addEventListener("click", () => {
            currentEditId = emp.id;
            setFormData(emp);
            document.getElementById("employee-form").classList.remove('was-validated');
            document.getElementById("employeeModalLabel").textContent = "Edit Employee";
            btnSave.textContent = "Update Employee";
            employeeModal.show();
        });

        const deleteBtn = document.createElement("button");
        deleteBtn.className = "btn btn-sm btn-outline-danger me-2";
        deleteBtn.innerHTML = "<i class='bi bi-trash3'></i>";
        deleteBtn.addEventListener("click", () => deleteEmployee(emp.id, deleteBtn));

        actionCell.appendChild(editBtn);
        actionCell.appendChild(deleteBtn);
        table.appendChild(row);
    });

    // Update pagination UI
    document.getElementById("pageInfo").textContent = `Showing ${start + 1} to ${Math.min(end, allEmployees.length)} of ${allEmployees.length} entries`;
    document.getElementById("btnPrevPage").classList.toggle("disabled", currentPage === 1);
    document.getElementById("btnNextPage").classList.toggle("disabled", currentPage === totalPages);
}


// ---------------- CREATE & UPDATE EMPLOYEE ----------------
document.getElementById("employee-form").addEventListener("submit", async (e) => {
    e.preventDefault();

    const form = document.getElementById("employee-form");
    if (!form.checkValidity()) {
        e.stopPropagation();
        form.classList.add('was-validated');
        return;
    }

    const body = getFormData();

    // Frontend Validation
    if (!body.name) {
        showToast("Please enter a name.", "warning");
        return;
    }
    if (!body.email) {
        showToast("Please enter an email.", "warning");
        return;
    }

    // Disable submit button and show loading state
    const originalText = btnSave.innerHTML;
    btnSave.disabled = true;
    btnSave.innerHTML = '<span class="spinner-border spinner-border-sm" aria-hidden="true"></span> Saving...';

    try {
        const method = currentEditId ? "PUT" : "POST";
        const url = currentEditId ? `${API}/${currentEditId}` : API;

        const res = await fetch(url, {
            method: method,
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body)
        });

        if (!res.ok) {
            if (res.status === 401) {
                localStorage.removeItem("token");
                localStorage.removeItem("role");
                window.location.href = "login.html?expired=true";
                return;
            }
            let errorMessage = handleError(null, res.status);
            try {
                const errData = await res.json();
                if (res.status === 422 && errData.detail) {
                    const errors = errData.detail.map(err => {
                        const field = err.loc[err.loc.length - 1];
                        return `${field}: ${err.msg}`;
                    });
                    errorMessage = `Validation errors:\n${errors.join('\n')}`;
                } else if (errData?.message) {
                    errorMessage = errData.message;
                }
            } catch (e) { }
            throw new Error(errorMessage);
        }

        const result = await res.json();
        console.log(currentEditId ? "Employee updated:" : "Employee created:", result);

        const empName = body.name;
        showToast(currentEditId ? `Employee ${empName} updated successfully` : `Employee ${empName} created successfully`, "success", 7000);

        closeModal();
        displayEmployees();
    } catch (error) {
        console.error("Error saving employee:", error);
        showToast("Failed to save employee: " + handleError(error, null), "danger");
    } finally {
        btnSave.disabled = false;
        btnSave.innerHTML = originalText;
    }
});


// ---------------- DELETE EMPLOYEE ----------------
async function deleteEmployee(id, btn) {
    if (!confirm("Are you sure you want to delete this employee?")) return;

    const originalText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm" aria-hidden="true"></span>';

    try {
        const res = await fetch(`${API}/${id}`, {
            method: "DELETE"
        });

        if (!res.ok) {
            let errorMessage = handleError(null, res.status);
            try {
                const errData = await res.json();
                if (res.status === 422 && errData.detail) {
                    const errors = errData.detail.map(err => {
                        const field = err.loc[err.loc.length - 1];
                        return `${field}: ${err.msg}`;
                    });
                    errorMessage = `Validation errors:\n${errors.join('\n')}`;
                } else if (errData?.message) {
                    errorMessage = errData.message;
                }
            } catch (e) { }
            throw new Error(errorMessage);
        }

        const result = await res.json();
        console.log("Employee deleted:", result);

        // Find the employee name before we delete it from the array for the toast
        const emp = allEmployees.find(e => e.id === id);
        const empName = emp ? emp.name : "Employee";

        showToast(`${empName} deleted successfully`, "success", 7000);

        // Instantly remove from UI without showing the loading spinner
        allEmployees = allEmployees.filter(emp => emp.id !== id);
        renderTable();
    } catch (error) {
        console.error("Error deleting employee:", error);
        showToast("Failed to delete employee: " + handleError(error, null), "danger");
        btn.disabled = false;
        btn.innerHTML = originalText;
    }
}


// ---------------- AI AGENT INTEGRATION ----------------
btnSendToAi.addEventListener("click", async () => {
    const text = aiEmailInput.value.trim();
    if (!text) return;

    // Append user's text to the chat
    aiChatHistory.innerHTML += `<div class="alert alert-secondary text-end"><strong>You:</strong> ${text}</div>`;
    aiEmailInput.value = "";

    // Scroll to bottom
    aiChatHistory.scrollTop = aiChatHistory.scrollHeight;

    // Show loading state
    const originalBtnText = btnSendToAi.innerHTML;
    btnSendToAi.disabled = true;
    btnSendToAi.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Processing...';

    try {
        const res = await fetch(`${BACKEND_URL}/api/ai-onboarding`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text: text, thread_id: aiThreadId })
        });

        const data = await res.json();

        if (!res.ok) throw new Error(data.detail || "Agent encountered an error.");

        // Save thread ID if the backend provides it so the AI remembers context
        if (data.thread_id) {
            aiThreadId = data.thread_id;
        }

        if (data.status === "success") {
            // Agent successfully added the employee
            aiChatHistory.innerHTML += `<div class="alert alert-success"><strong>Agent:</strong> ${data.message}</div>`;
            showToast("Employee onboarded successfully via AI!", "success");
            displayEmployees(); // Refresh table
        } else if (data.status === "missing_info") {
            // Agent is missing fields and asking for them
            aiChatHistory.innerHTML += `<div class="alert alert-warning"><strong>Agent:</strong> ${data.message}</div>`;
        }
    } catch (error) {
        aiChatHistory.innerHTML += `<div class="alert alert-danger"><strong>Error:</strong> ${error.message}</div>`;
    } finally {
        btnSendToAi.disabled = false;
        btnSendToAi.innerHTML = originalBtnText;
        aiChatHistory.scrollTop = aiChatHistory.scrollHeight;
    }
});

document.getElementById('aiModal').addEventListener('show.bs.modal', () => {
    aiEmailInput.value = '';
    aiThreadId = null;
    aiChatHistory.innerHTML = `<div class="alert alert-info"><strong>System:</strong> Paste the raw text or WhatsApp message from the candidate below. The system will parse and extract the required fields.</div>`;
});

// ---------------- SEND INITIATOR EMAIL ----------------
btnSendInitiatorEmail.addEventListener("click", async () => {
    const emailInputRaw = candidateEmailInput.value.trim();
    if (!emailInputRaw) {
        showToast("Please enter at least one valid email address.", "warning");
        return;
    }

    // Split by comma and filter out empty strings
    const emailArray = emailInputRaw.split(",").map(e => e.trim()).filter(e => e !== "");

    if (emailArray.length === 0) {
        showToast("Please enter valid email addresses.", "warning");
        return;
    }

    const originalBtnText = btnSendInitiatorEmail.innerHTML;
    btnSendInitiatorEmail.disabled = true;
    btnSendInitiatorEmail.innerHTML = '<span class="spinner-border spinner-border-sm"></span> Sending...';

    try {
        const res = await fetch(`${BACKEND_URL}/api/initiate`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ emails: emailArray })
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Failed to send email.");

        const successMsg = data.message;
        candidateEmailInput.value = "";

        // Wait for modal to be FULLY hidden (backdrop removed), then show toast
        const modalEl = document.getElementById('emailInitiatorModal');
        modalEl.addEventListener('hidden.bs.modal', function onHidden() {
            modalEl.removeEventListener('hidden.bs.modal', onHidden);
            showToast(successMsg, "success", 7000);
        });
        emailInitiatorModal.hide();
    } catch (error) {
        showToast(error.message, "danger");
    } finally {
        btnSendInitiatorEmail.disabled = false;
        btnSendInitiatorEmail.innerHTML = originalBtnText;
    }
});


window.addEventListener("DOMContentLoaded", () => {
    displayEmployees();

    // Set max date for Date of Birth input to today
    const today = new Date().toISOString().split("T")[0];
    formFields.dob.setAttribute("max", today);

    document.getElementById("btnAddNew").addEventListener("click", openModal);

    document.getElementById("btnPrevPage").addEventListener("click", (e) => {
        e.preventDefault();
        if (currentPage > 1) {
            currentPage--;
            renderTable();
        }
    });

    document.getElementById("btnNextPage").addEventListener("click", (e) => {
        e.preventDefault();
        const totalPages = Math.ceil(allEmployees.length / pageSize);
        if (currentPage < totalPages) {
            currentPage++;
            renderTable();
        }
    });

    document.getElementById("brandHome").addEventListener("click", () => {
        if (currentPage !== 1) {
            currentPage = 1;
            renderTable();
            showToast("Navigated to page 1", "info");
        } else {
            displayEmployees();
            showToast("Database refreshed", "success");
        }
    });

    // ---- Email Listener Status (read-only, auto-starts with server) ----
    const listenerBadge = document.getElementById("listenerBadge");
    const listenerStatusWrapper = document.getElementById("listenerStatusWrapper");

    async function pollListenerStatus() {
        if (!listenerBadge || !listenerStatusWrapper) return;
        try {
            const res = await fetch(`${BACKEND_URL}/api/listener/status`);
            if (res.ok) {
                const data = await res.json();
                if (data.is_running) {
                    listenerBadge.textContent = "Agent: Online";
                    listenerStatusWrapper.className = "d-flex align-items-center gap-2 status-online";
                } else {
                    listenerBadge.textContent = "Agent: Connecting";
                    listenerStatusWrapper.className = "d-flex align-items-center gap-2 status-connecting";
                }
            } else {
                listenerBadge.textContent = "Agent: Offline";
                listenerStatusWrapper.className = "d-flex align-items-center gap-2 status-offline";
            }
        } catch (e) {
            listenerBadge.textContent = "Agent: Offline";
            listenerStatusWrapper.className = "d-flex align-items-center gap-2 status-offline";
        }
    }

    // Poll immediately, then every 15 seconds (reduced request rate to optimize resources)
    pollListenerStatus();
    setInterval(pollListenerStatus, 15000);
});

console.log("App started...");
