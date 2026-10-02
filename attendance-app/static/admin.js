const datePicker = document.getElementById('datePicker');
const tableBody = document.getElementById('tableBody');
const btnRefresh = document.getElementById('btnRefresh');
const addEmployeeForm = document.getElementById('addEmployeeForm');
const addEmployeeMsg = document.getElementById('addEmployeeMsg');

// Set today's date in IST
function getISTDateString() {
    const d = new Date();
    // Offset for IST is +5:30
    d.setMinutes(d.getMinutes() + 330 + d.getTimezoneOffset());
    return d.toISOString().split('T')[0];
}

datePicker.value = getISTDateString();

async function loadData() {
    tableBody.innerHTML = '<tr><td colspan="6" style="text-align: center;">Loading data...</td></tr>';
    try {
        const res = await fetch(`/api/attendance?date=${datePicker.value}`);
        if (!res.ok) {
            if(res.status === 401) window.location.href = '/login';
            return;
        }
        const data = await res.json();
        
        tableBody.innerHTML = '';
        if (data.rows.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="6" style="text-align: center;">No records found.</td></tr>';
            return;
        }
        
        data.rows.forEach(row => {
            const tr = document.createElement('tr');
            
            // Name
            const tdName = document.createElement('td');
            tdName.innerHTML = `<strong>${row.name}</strong><br><small style="color: var(--text-muted)">${row.emp_code}</small>`;
            tr.appendChild(tdName);
            
            // Picture
            const tdPic = document.createElement('td');
            if (row.in_selfie) {
                tdPic.innerHTML += `<img src="/selfie/${row.in_selfie}" class="selfie-thumb" title="Check-in Photo" onclick="window.open(this.src)"/> `;
            }
            if (row.out_selfie) {
                tdPic.innerHTML += `<img src="/selfie/${row.out_selfie}" class="selfie-thumb" title="Check-out Photo" onclick="window.open(this.src)"/>`;
            }
            if (!row.in_selfie && !row.out_selfie) {
                tdPic.innerText = '—';
            }
            tr.appendChild(tdPic);
            
            // Location In
            const tdLocIn = document.createElement('td');
            if (row.in_lat && row.in_lon) {
                tdLocIn.innerHTML = `<a href="https://maps.google.com/?q=${row.in_lat},${row.in_lon}" target="_blank">View Map 📍</a>`;
            } else {
                tdLocIn.innerText = '—';
            }
            tr.appendChild(tdLocIn);
            
            // Location Out
            const tdLocOut = document.createElement('td');
            if (row.out_lat && row.out_lon) {
                tdLocOut.innerHTML = `<a href="https://maps.google.com/?q=${row.out_lat},${row.out_lon}" target="_blank">View Map 📍</a>`;
            } else {
                tdLocOut.innerText = '—';
            }
            tr.appendChild(tdLocOut);
            
            // Times
            const tdIn = document.createElement('td');
            tdIn.innerText = row.check_in ? row.check_in : '—';
            tr.appendChild(tdIn);
            
            const tdOut = document.createElement('td');
            tdOut.innerText = row.check_out ? row.check_out : '—';
            tr.appendChild(tdOut);
            
            tableBody.appendChild(tr);
        });
        
    } catch (err) {
        tableBody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: var(--danger);">Failed to load data.</td></tr>';
    }
}

datePicker.addEventListener('change', loadData);
btnRefresh.addEventListener('click', loadData);

loadData();
// Auto refresh every 30 seconds
setInterval(loadData, 30000);

if (addEmployeeForm) {
    addEmployeeForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        addEmployeeMsg.style.color = 'var(--text-muted)';
        addEmployeeMsg.innerText = 'Adding employee...';
        
        const fd = new FormData(addEmployeeForm);
        try {
            const res = await fetch('/api/add-user', {
                method: 'POST',
                body: fd
            });
            const data = await res.json();
            if (res.ok) {
                addEmployeeMsg.style.color = '#4ade80';
                addEmployeeMsg.innerText = data.message || 'Added successfully';
                addEmployeeForm.reset();
                loadData(); // refresh the table if needed
            } else {
                addEmployeeMsg.style.color = 'var(--danger)';
                addEmployeeMsg.innerText = data.detail || 'Error adding employee';
            }
        } catch (err) {
            addEmployeeMsg.style.color = 'var(--danger)';
            addEmployeeMsg.innerText = 'Failed to connect to server';
        }
    });
}
