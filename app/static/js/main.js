document.addEventListener("DOMContentLoaded", () => {
    // 1. Drag & Drop File Upload Handler
    const dropzone = document.getElementById("dropzone");
    const fileInput = document.getElementById("files-input");
    const fileList = document.getElementById("uploaded-file-list");

    if (dropzone && fileInput) {
        // Trigger file input click when clicking dropzone
        dropzone.addEventListener("click", () => fileInput.click());

        // Visual feedback on drag actions
        ["dragenter", "dragover"].forEach(eventName => {
            dropzone.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
                dropzone.classList.add("dragover");
            }, false);
        });

        ["dragleave", "drop"].forEach(eventName => {
            dropzone.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
                dropzone.classList.remove("dragover");
            }, false);
        });

        // Handle dropped files
        dropzone.addEventListener("drop", (e) => {
            const dt = e.dataTransfer;
            const files = dt.files;
            fileInput.files = files;
            updateFileList(files);
        });

        // Handle selected files
        fileInput.addEventListener("change", (e) => {
            updateFileList(e.target.files);
        });
    }

    function updateFileList(files) {
        if (!fileList) return;
        fileList.innerHTML = "";
        
        if (files.length === 0) {
            fileList.innerHTML = '<li class="list-group-item bg-transparent text-muted border-0">No files selected</li>';
            return;
        }

        Array.from(files).forEach((file, index) => {
            const sizeKB = (file.size / 1024).toFixed(1);
            const li = document.createElement("li");
            li.className = "list-group-item bg-transparent text-light border-0 d-flex justify-content-between align-items-center py-2";
            li.innerHTML = `
                <div>
                    <i class="fas fa-file-alt text-cyan me-2"></i>
                    <span>${file.name}</span>
                </div>
                <span class="badge bg-secondary">${sizeKB} KB</span>
            `;
            fileList.appendChild(li);
        });
    }

    // 2. Cryptographic Recalculation Verification Handler
    const verifyBtn = document.getElementById("btn-verify-evidence");
    const verificationResults = document.getElementById("verification-results-container");

    if (verifyBtn) {
        verifyBtn.addEventListener("click", async () => {
            const evidenceId = verifyBtn.dataset.id;
            const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
            
            // Show loading state
            verifyBtn.disabled = true;
            verifyBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i> Recalculating Hashes...';
            
            if (verificationResults) {
                verificationResults.innerHTML = `
                    <div class="text-center py-3">
                        <div class="spinner-border text-cyan mb-2" role="status"></div>
                        <p class="text-muted small">Reading AES-256 encrypted block, executing decrypt pass, and running SHA-256 hashing pass...</p>
                    </div>
                `;
                verificationResults.classList.remove("d-none");
            }

            try {
                const response = await fetch(`/evidence/${evidenceId}/verify`, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': csrfToken,
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                });

                const data = await response.json();
                verifyBtn.disabled = false;
                verifyBtn.innerHTML = '<i class="fas fa-shield-alt me-2"></i> Verify Integrity';

                if (data.status === 'Verified') {
                    // Update Badge and Text
                    const badge = document.getElementById("evidence-status-badge");
                    if (badge) {
                        badge.className = "badge badge-verified";
                        badge.innerText = "Verified";
                    }
                    
                    verificationResults.innerHTML = `
                        <div class="alert alert-success border-success bg-success-transparent mb-0">
                            <h5 class="alert-heading text-success mb-1"><i class="fas fa-check-circle me-2"></i> Integrity Verified!</h5>
                            <p class="small mb-2">Cryptographic match validated. The decrypted binary exact SHA-256 matches the original custody seal.</p>
                            <hr class="my-2 border-success opacity-25">
                            <div class="small">
                                <strong>Original Sealed Hash:</strong> <code class="text-light break-all">${data.original_hash}</code><br>
                                <strong>Computed Vault Hash:</strong> <code class="text-light break-all">${data.recalculated_hash}</code>
                            </div>
                        </div>
                    `;
                } else if (data.status === 'Tampered') {
                    // Update Badge and Text
                    const badge = document.getElementById("evidence-status-badge");
                    if (badge) {
                        badge.className = "badge badge-tampered";
                        badge.innerText = "Tampered";
                    }
                    
                    verificationResults.innerHTML = `
                        <div class="alert alert-danger border-danger bg-danger-transparent mb-0">
                            <h5 class="alert-heading text-danger mb-1"><i class="fas fa-exclamation-triangle me-2"></i> WARNING: Tampering Detected!</h5>
                            <p class="small mb-2">CRITICAL MATCH ERROR. Recalculated file signature does not match the database evidence block.</p>
                            <hr class="my-2 border-danger opacity-25">
                            <div class="small">
                                <strong>Expected (Sealed):</strong> <code class="text-light break-all">${data.original_hash}</code><br>
                                <strong>Found (Tampered):</strong> <code class="text-warning break-all">${data.recalculated_hash}</code>
                            </div>
                        </div>
                    `;
                } else {
                    verificationResults.innerHTML = `
                        <div class="alert alert-warning border-warning bg-warning-transparent mb-0">
                            <h5 class="alert-heading text-warning mb-1"><i class="fas fa-exclamation-circle me-2"></i> Verification Error</h5>
                            <p class="small mb-0">${data.message}</p>
                        </div>
                    `;
                }
            } catch (error) {
                verifyBtn.disabled = false;
                verifyBtn.innerHTML = '<i class="fas fa-shield-alt me-2"></i> Verify Integrity';
                verificationResults.innerHTML = `
                    <div class="alert alert-danger border-danger bg-danger-transparent mb-0">
                        <h5 class="alert-heading text-danger mb-1"><i class="fas fa-times-circle me-2"></i> Connection Failed</h5>
                        <p class="small mb-0">Failed to establish connection with verification node. Details: ${error.message}</p>
                    </div>
                `;
            }
        });
    }

    // 3. Mark Single Notification Read AJAX
    const notifItems = document.querySelectorAll(".notif-mark-read");
    notifItems.forEach(item => {
        item.addEventListener("click", async (e) => {
            e.preventDefault();
            const notifId = item.dataset.id;
            const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
            
            try {
                const response = await fetch(`/notifications/${notifId}/read`, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': csrfToken,
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                });
                
                if (response.ok) {
                    // Remove or grey out notification in lists
                    item.closest(".notification-item-row").classList.add("opacity-50");
                    item.remove();
                    
                    // Decrease count in nav indicators
                    const navCounts = document.querySelectorAll(".nav-notif-count");
                    navCounts.forEach(el => {
                        let c = parseInt(el.innerText);
                        if (c > 0) {
                            el.innerText = c - 1;
                            if (c - 1 === 0) el.remove();
                        }
                    });
                }
            } catch (err) {
                console.error("Failed to read notification:", err);
            }
        });
    });
});
