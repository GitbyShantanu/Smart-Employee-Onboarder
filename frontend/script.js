const API = "http://127.0.0.1:8000/employees";

const formFields = {
    firstName: document.getElementById("first_name"),
    middleName: document.getElementById("middle_name"),
    lastName: document.getElementById("last_name"),
    gender: document.getElementById("gender"),
    dob: document.getElementById("date_of_birth"),
    mobile: document.getElementById("mobile_number"),
    alternateMobile: document.getElementById("alternate_mobile_number"),
    email: document.getElementById("email"),
    maritalStatus: document.getElementById("marrital_status"),
    bloodGroup: document.getElementById("blood_grp")
};

const table = document.querySelector("#table tbody");
const btnSave = document.getElementById("btnSave");
const employeeModal = new bootstrap.Modal(document.getElementById('employeeModal'));

const aiModal = new bootstrap.Modal(document.getElementById('aiModal'));
const btnSendToAi = document.getElementById("btnSendToAi");
const aiEmailInput = document.getElementById("aiEmailInput");
const aiChatHistory = document.getElementById("aiChatHistory");

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
        first_name: formFields.firstName.value.trim(),
        middle_name: formFields.middleName.value.trim(),
        last_name: formFields.lastName.value.trim(),
        gender: formFields.gender.value,
        date_of_birth: formFields.dob.value,
        mobile_number: parseInt(formFields.mobile.value.trim() || 0),
        alternate_mobile_number: parseInt(formFields.alternateMobile.value.trim() || 0),
        email: formFields.email.value.trim(),
        marrital_status: formFields.maritalStatus.value,
        blood_group: formFields.bloodGroup.value
    };
}

function setFormData(data) {
    if (data.first_name !== undefined) formFields.firstName.value = data.first_name;
    if (data.middle_name !== undefined) formFields.middleName.value = data.middle_name;
    if (data.last_name !== undefined) formFields.lastName.value = data.last_name;
    if (data.gender !== undefined) formFields.gender.value = data.gender;
    if (data.date_of_birth !== undefined) formFields.dob.value = data.date_of_birth;
    if (data.mobile_number !== undefined) formFields.mobile.value = data.mobile_number;
    if (data.alternate_mobile_number !== undefined) formFields.alternateMobile.value = data.alternate_mobile_number;
    if (data.email !== undefined) formFields.email.value = data.email;
    if (data.marrital_status !== undefined) formFields.maritalStatus.value = data.marrital_status;
    if (data.blood_group !== undefined) formFields.bloodGroup.value = data.blood_group;
}

function clearForm() {
    Object.values(formFields).forEach(f => f.value = "");
}


// ---------------- LOAD EMPLOYEES ----------------
async function displayEmployees() {
    table.innerHTML = `
        <tr>
            <td colspan="12" class="text-center py-5 text-muted">
                <div class="spinner-border text-secondary" role="status"></div>
                <div class="mt-2 small fw-medium">Loading employees...</div>
            </td>
        </tr>
    `;

    try {
        const res = await fetch(API);

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
            } catch (e) {}
            throw new Error(errorMessage);
        }

        const data = await res.json();
        allEmployees = data;
        renderTable();
        console.log("Employees loaded:", data);
    } catch (error) {
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
        
        row.innerHTML = `
            <td>${emp.id || ""}</td>
            <td>${emp.first_name || ""}</td>
            <td>${emp.middle_name || ""}</td>
            <td>${emp.last_name || ""}</td>
            <td>${emp.gender || ""}</td>
            <td>${emp.date_of_birth || ""}</td>
            <td>${emp.mobile_number || ""}</td>
            <td>${emp.alternate_mobile_number || ""}</td>
            <td>${emp.email || ""}</td>
            <td>${emp.marrital_status || ""}</td>
            <td><span class="badge bg-danger">${emp.blood_group || ""}</span></td>
            <td class="text-end"></td>
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
    if (!body.first_name || !body.last_name) {
        showToast("Please enter first and last name.", "warning");
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
            } catch (e) {}
            throw new Error(errorMessage);
        }

        const result = await res.json();
        console.log(currentEditId ? "Employee updated:" : "Employee created:", result);
        showToast(currentEditId ? "Employee updated successfully" : "Employee added successfully", "success", 7000);
        
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
            } catch (e) {}
            throw new Error(errorMessage);
        }

        const result = await res.json();
        console.log("Employee deleted:", result);
        showToast("Employee deleted successfully", "success", 7000);
        displayEmployees();
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
        const res = await fetch("http://127.0.0.1:8000/api/ai-onboarding", {
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
    aiThreadId = null; // Reset the conversation state when opening the modal
    aiChatHistory.innerHTML = `<div class="alert alert-info"><strong>Agent:</strong> Hello! Paste the raw new hire email below. I will extract the details, validate our required fields, and let you know if I need anything else.</div>`;
});


window.addEventListener("DOMContentLoaded", () => {
    displayEmployees();
    
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
});

console.log("App started...");
