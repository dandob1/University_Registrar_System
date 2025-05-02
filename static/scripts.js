// Toggle account dropdown
function toggleDropdown() {
    const dropdownContent = document.querySelector('.dropdown-content');
    dropdownContent.classList.toggle('show');
}

// Close dropdown on outside click
window.onclick = function(event) {
    if (!event.target.matches('.dropdown button')) {
        const dropdowns = document.querySelectorAll('.dropdown-content');
        dropdowns.forEach(dropdown => dropdown.classList.remove('show'));
    }
};

// Party mode
let partyModeActive = false;
let partyInterval;

function togglePartyMode() {
    const body = document.body;
    const button = document.getElementById('party-button');

    if (!button) return;

    if (!partyModeActive) {
        partyModeActive = true;
        button.textContent = "🛑 Stop Party";
        partyInterval = setInterval(() => {
            body.style.backgroundColor = getRandomColor();
        }, 500);
    } else {
        partyModeActive = false;
        button.textContent = "🎉 Party Mode";
        clearInterval(partyInterval);
        body.style.backgroundColor = "";
    }
}

function getRandomColor() {
    const letters = '0123456789ABCDEF';
    let color = '#';
    for (let i = 0; i < 6; i++) {
        color += letters[Math.floor(Math.random() * 16)];
    }
    return color;
}

// Modal handling (used by GS for advisor assignment)
function openModal(studentUid) {
    const modal = document.getElementById("advisorModal");
    modal.style.display = "flex";
    document.body.classList.add("modal-open");
    window.currentStudentUid = studentUid;
    fetchAdvisors('');
}

function closeModal() {
    const modal = document.getElementById("advisorModal");
    modal.style.display = "none";
    document.body.classList.remove("modal-open");
    window.currentStudentUid = null;
}

function fetchAdvisors(query) {
    fetch(`/searchAdvisors?query=${encodeURIComponent(query)}`)
        .then(response => response.json())
        .then(data => {
            const advisorList = document.getElementById("advisorList");
            advisorList.innerHTML = `
                <table border="1">
                    ${data.length > 0 ? data.map(advisor => `
                        <tr>
                            <td>${advisor.uid}</td>
                            <td>${advisor.fname} ${advisor.lname}</td>
                            <td><button onclick="assignAdvisor('${window.currentStudentUid}', '${advisor.uid}')">Assign</button></td>
                        </tr>
                    `).join('') : `<tr><td colspan="3">No advisors found.</td></tr>`}
                </table>
            `;
        });
}

function assignAdvisor(studentUid, advisorUid) {
    fetch(`/assignAdvisor`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ studentUid, advisorUid })
    })
    .then(response => {
        if (response.ok) {
            alert('Advisor assigned successfully!');
            closeModal();
            location.reload();
        } else {
            alert('Failed to assign advisor.');
        }
    });
}

// Dynamic search – Faculty Advisor page
document.addEventListener('DOMContentLoaded', () => {
    const studentSearch = document.getElementById('studentSearch');
    const studentList = document.getElementById('studentList');

    if (studentSearch && studentList && document.body.classList.contains('faculty-advisor-page')) {
        studentSearch.addEventListener('input', (event) => {
            const query = event.target.value.trim();
            fetch(`/searchMyStudents?query=${encodeURIComponent(query)}`)
                .then(res => res.json())
                .then(data => {
                    studentList.innerHTML = data.length > 0
                        ? data.map(s => `
                            <tr>
                                <td>${s.uid}</td>
                                <td>${s.fname} ${s.lname}</td>
                                <td>${s.program}</td>
                                <td>
                                    ${s.form_submitted === 0 ? 'Form Incomplete' :
                                        s.form_approved === 0 ? 'Pending Approval' : 'Approved'}
                                </td>
                                <td>
                                    ${s.program === "PhD" 
                                        ? (s.thesis_submitted === 0 
                                            ? 'Not Submitted' 
                                            : s.thesis_approved === 0 
                                                ? 'Pending Approval' 
                                                : 'Approved') 
                                        : 'N/A'}
                                </td>
                                <td>
                                    ${s.form_submitted === 1 && s.form_approved === 0
                                        ? `<button onclick="location.href='/viewForm/${s.uid}'">Approve Form</button>`
                                        : s.form_submitted === 1
                                            ? `<button onclick="location.href='/viewForm/${s.uid}'">View Form</button>`
                                            : ''}
                                    <button onclick="location.href='/transcript/${s.uid}'">View Transcript</button>
                                    ${s.program === "PhD" && s.thesis_submitted === 1
                                        ? `<button onclick="location.href='/viewThesis/${s.uid}'">View Thesis</button>`
                                        : ''}
                                </td>
                            </tr>
                        `).join('')
                        : `<tr><td colspan="6">No students found.</td></tr>`;
                })
                .catch(err => {
                    console.error('Search error:', err);
                    studentList.innerHTML = `<tr><td colspan="6">Failed to load students.</td></tr>`;
                });
        });
    }

    // Dynamic search – Grad Secretary page
    if (studentSearch && studentList && document.body.classList.contains('grad-secretary-page')) {
        studentSearch.addEventListener('input', (event) => {
            const query = event.target.value.trim();
            fetch(`/search?query=${encodeURIComponent(query)}`)
                .then(res => res.json())
                .then(data => {
                    studentList.innerHTML = data.length > 0
                        ? data.map(student => `
                            <tr>
                                <td>${student.uid}</td>
                                <td>${student.fname} ${student.lname}</td>
                                <td>${student.program}</td>
                                <td>${student.gpa}</td>
                                <td>${student.advisor_uid ? student.advisorName : 'Not Assigned'}</td>
                                <td>
                                    <button onclick="openModal('${student.uid}')">Assign/Change Advisor</button>
                                    ${student.grad_requested
                                        ? `<form action="/processGraduation/${student.uid}" method="post" style="display:inline">
                                             <button type="submit">Process Graduation</button>
                                           </form>`
                                        : ``
                                      }
                                    <a href="/transcript/${student.uid}">
                                        <button type="button">View Transcript</button>
                                    </a>
                                </td>
                            </tr>
                        `).join('')
                        : `<tr><td colspan="6">No students found.</td></tr>`;
                })
                .catch(err => {
                    console.error('Search error:', err);
                    studentList.innerHTML = `<tr><td colspan="6">Failed to load students.</td></tr>`;
                });
        });
    }

    // Dynamic search – System Admin page
    const userSearchInput = document.getElementById('userSearch');
    const userList = document.getElementById('userList');

    if (userSearchInput && userList && document.body.classList.contains('systems-admin-page')) {
        userSearchInput.addEventListener('input', (event) => {
            const query = event.target.value.trim();
            fetch(`/searchUsers?query=${encodeURIComponent(query)}`)
                .then(res => res.json())
                .then(data => {
                    userList.innerHTML = data.length > 0
                        ? data.map(user => `
                            <tr>
                                <td>${user.uid}</td>
                                <td>${user.fname} ${user.lname}</td>
                                <td>${user.user_type}</td>
                                <td>${user.email}</td>
                                <td>${user.address}</td>
                                <td>
                                    <button onclick="location.href='/editUser/${user.uid}'">Edit</button>
                                    <form action="/deleteUser/${user.uid}" method="post" style="display:inline;">
                                        <button type="submit" onclick="return confirm('Are you sure you want to delete this user?');">Delete</button>
                                    </form>
                                </td>
                            </tr>
                        `).join('')
                        : `<tr><td colspan="6">No users found.</td></tr>`;
                })
                .catch(err => {
                    console.error('User search error:', err);
                    userList.innerHTML = `<tr><td colspan="6">Failed to load users.</td></tr>`;
                });
        });
    }
});

document.getElementById("userType").addEventListener("change", function() {
    var userType = this.value;
    document.getElementById("gradStudentFields").style.display = (userType === "grad_student") ? "block" : "none";
    document.getElementById("facultyAdvisorFields").style.display = (userType === "faculty_advisor") ? "block" : "none";
    document.getElementById("alumniFields").style.display = (userType === "alumni") ? "block" : "none";
  });
  document.getElementById("userType").dispatchEvent(new Event("change"));

  // Scroll to Bottom Function
  function scrollToBottom() {
      const createUserSection = document.getElementById("createUserSection");
      createUserSection.scrollIntoView({ behavior: "smooth" });
  }