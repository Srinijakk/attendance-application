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
    tableBody.innerHTML = '<tr><td colspan="8" style="text-align: center;">Loading data...</td></tr>';
    try {
        const branchVal = document.getElementById('branchFilter') ? document.getElementById('branchFilter').value : '';
        const res = await fetch(`/api/attendance?date=${datePicker.value}&branch=${encodeURIComponent(branchVal)}`);
        if (!res.ok) {
            if(res.status === 401) window.location.href = '/login';
            return;
        }
        const data = await res.json();
        
        tableBody.innerHTML = '';
        if (data.rows.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="8" style="text-align: center;">No records found.</td></tr>';
            return;
        }
        
        data.rows.forEach(row => {
            const tr = document.createElement('tr');
            
            // 1. Employee Name
            const tdName = document.createElement('td');
            tdName.innerHTML = `<strong>${row.name}</strong><br><small style="color: var(--text-muted)">${row.emp_code}</small>`;
            tr.appendChild(tdName);

            // 2. Branch
            const tdBranch = document.createElement('td');
            if (row.branch) {
                tdBranch.innerHTML = `<span class="branch-tag">🏢 ${row.branch}</span>`;
            } else {
                tdBranch.innerHTML = `<span style="color: var(--text-muted)">—</span>`;
            }
            tr.appendChild(tdBranch);
            
            // 3. Picture
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
            
            // Helper for distance formatting
            const formatDistBadge = (distM, isWithin) => {
                if (distM === null || distM === undefined) return '';
                const distText = distM < 1000 ? `${Math.round(distM)}m` : `${(distM / 1000).toFixed(2)}km`;
                if (isWithin) {
                    return `<div style="margin-top: 0.35rem;"><span class="badge badge-success">✅ ${distText} (Within 100m)</span></div>`;
                } else {
                    return `<div style="margin-top: 0.35rem;"><span class="badge badge-danger">⚠️ ${distText} (Outside)</span></div>`;
                }
            };

            // 4. Location In
            const tdLocIn = document.createElement('td');
            if (row.in_lat && row.in_lon) {
                const mapLink = `<a href="https://maps.google.com/?q=${row.in_lat},${row.in_lon}" target="_blank">View Map 📍</a>`;
                tdLocIn.innerHTML = mapLink + formatDistBadge(row.in_dist_m, row.in_within_range);
            } else {
                tdLocIn.innerText = '—';
            }
            tr.appendChild(tdLocIn);
            
            // 5. Location Out
            const tdLocOut = document.createElement('td');
            if (row.out_lat && row.out_lon) {
                const mapLink = `<a href="https://maps.google.com/?q=${row.out_lat},${row.out_lon}" target="_blank">View Map 📍</a>`;
                tdLocOut.innerHTML = mapLink + formatDistBadge(row.out_dist_m, row.out_within_range);
            } else {
                tdLocOut.innerText = '—';
            }
            tr.appendChild(tdLocOut);
            
            // 6. Check-in (IST)
            const tdIn = document.createElement('td');
            tdIn.innerText = row.check_in ? row.check_in : '—';
            tr.appendChild(tdIn);
            
            // 7. Check-out (IST)
            const tdOut = document.createElement('td');
            tdOut.innerText = row.check_out ? row.check_out : '—';
            tr.appendChild(tdOut);
            
            // 8. Overall Geofence Status
            const tdStatus = document.createElement('td');
            if (!row.check_in) {
                tdStatus.innerHTML = `<span class="badge badge-neutral">— Not Marked</span>`;
            } else if (row.in_within_range === true && (row.out_within_range === true || row.out_within_range === null)) {
                tdStatus.innerHTML = `<span class="badge badge-success">✅ Verified (&lt;100m)</span>`;
            } else if (row.in_within_range === false || row.out_within_range === false) {
                tdStatus.innerHTML = `<span class="badge badge-danger">❌ Outside (&gt;100m)</span>`;
            } else {
                tdStatus.innerHTML = `<span class="badge badge-warning">⚠️ No GPS / Branch</span>`;
            }
            tr.appendChild(tdStatus);

            tableBody.appendChild(tr);
        });
        
    } catch (err) {
        tableBody.innerHTML = '<tr><td colspan="8" style="text-align: center; color: var(--danger);">Failed to load data.</td></tr>';
    }
}

datePicker.addEventListener('change', loadData);
btnRefresh.addEventListener('click', loadData);
const branchFilter = document.getElementById('branchFilter');
if (branchFilter) branchFilter.addEventListener('change', loadData);

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
