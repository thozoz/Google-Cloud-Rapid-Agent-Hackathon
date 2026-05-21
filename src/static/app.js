// Frontend JavaScript - Hackathon Discovery & Tracking Agent Dashboard

const API_BASE = "/api";

// DOM Elements
const profileForm = document.getElementById("profile-form");
const techStackInput = document.getElementById("tech-stack");
const interestsInput = document.getElementById("interests");
const experienceSelect = document.getElementById("experience-level");
const availabilitySelect = document.getElementById("weekly-availability");
const profileStatus = document.getElementById("profile-status");
const btnSaveProfile = document.getElementById("btn-save-profile");

const btnTriggerScrape = document.getElementById("btn-trigger-scrape");
const scrapeLoader = document.getElementById("scrape-loader");
const scrapeIcon = document.getElementById("scrape-icon");
const btnTriggerReminders = document.getElementById("btn-trigger-reminders");

const statScrapedCount = document.getElementById("stat-scraped-count");
const statMatchedCount = document.getElementById("stat-matched-count");
const statTrackedCount = document.getElementById("stat-tracked-count");

const tabButtons = document.querySelectorAll(".tab-btn");
const tabContents = document.querySelectorAll(".tab-content");

const recommendationsGrid = document.getElementById("recommendations-grid");
const trackedGrid = document.getElementById("tracked-grid");

// App State
let userProfile = null;
let hackathonsList = [];
let trackedList = [];

// Initialize Dashboard
document.addEventListener("DOMContentLoaded", () => {
    initApp();
});

async function initApp() {
    setupTabNavigation();
    setupEventListeners();
    await loadProfile();
    if (userProfile) {
        await loadDashboardData();
    }
}

// Tab Switching Control
function setupTabNavigation() {
    tabButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            const tabId = btn.getAttribute("data-tab");
            
            // Toggle buttons active class
            tabButtons.forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
            
            // Toggle content visibility
            tabContents.forEach(content => {
                content.classList.remove("active");
                if (content.id === tabId) {
                    content.classList.add("active");
                }
            });
        });
    });
}

// Global Event Listeners
function setupEventListeners() {
    // Form submission
    profileForm.addEventListener("submit", handleProfileSubmit);
    
    // Manual scrape trigger
    btnTriggerScrape.addEventListener("click", triggerScrapeAndMatch);
    
    // Manual deadline check trigger
    btnTriggerReminders.addEventListener("click", triggerDeadlineCheck);
}

// Toast Notification Engine
function showToast(message, type = "info") {
    const container = document.getElementById("toast-container");
    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    
    let iconClass = "fa-info-circle";
    if (type === "success") iconClass = "fa-check-circle";
    if (type === "error") iconClass = "fa-exclamation-circle";
    
    toast.innerHTML = `
        <i class="fa-solid ${iconClass}"></i>
        <span>${message}</span>
    `;
    
    container.appendChild(toast);
    
    // Auto-remove toast
    setTimeout(() => {
        toast.style.opacity = "0";
        toast.style.transform = "translateY(20px)";
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// Load profile from Atlas
async function loadProfile() {
    try {
        const response = await fetch(`${API_BASE}/profile`);
        const data = await response.json();
        
        if (data.status === "success" && data.profile) {
            userProfile = data.profile;
            
            // Fill inputs
            techStackInput.value = userProfile.tech_stack.join(", ");
            interestsInput.value = userProfile.interests.join(", ");
            experienceSelect.value = userProfile.experience_level;
            availabilitySelect.value = userProfile.weekly_availability;
            
            // Update sidebar status
            profileStatus.className = "sidebar-status glass-panel-inner status-configured";
            profileStatus.innerHTML = `
                <span class="status-dot status-dot-success"></span>
                <span>Profile connected to MongoDB Atlas.</span>
            `;
            
            // Enable Scraping
            btnTriggerScrape.disabled = false;
        } else {
            btnTriggerScrape.disabled = true;
        }
    } catch (err) {
        console.error("Error loading profile:", err);
        showToast("Failed to connect with database backend.", "error");
    }
}

// Save profile (Step 1)
async function handleProfileSubmit(e) {
    e.preventDefault();
    btnSaveProfile.disabled = true;
    
    // Parse stacks & interests
    const techStack = techStackInput.value.split(",").map(s => s.trim()).filter(s => s.length > 0);
    const interests = interestsInput.value.split(",").map(i => i.trim()).filter(i => i.length > 0);
    
    const profilePayload = {
        tech_stack: techStack,
        interests: interests,
        experience_level: experienceSelect.value,
        weekly_availability: availabilitySelect.value
    };
    
    try {
        const response = await fetch(`${API_BASE}/profile`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(profilePayload)
        });
        
        const data = await response.json();
        if (data.status === "success") {
            showToast("Profile saved to MongoDB Atlas!", "success");
            userProfile = data.profile;
            
            // Update sidebar status
            profileStatus.className = "sidebar-status glass-panel-inner status-configured";
            profileStatus.innerHTML = `
                <span class="status-dot status-dot-success"></span>
                <span>Profile connected to MongoDB Atlas.</span>
            `;
            
            // Enable scrape button
            btnTriggerScrape.disabled = false;
            
            // Load dashboard data
            await loadDashboardData();
        } else {
            showToast("Failed to save profile: " + data.message, "error");
        }
    } catch (err) {
        console.error("Error saving profile:", err);
        showToast("Backend connection error.", "error");
    } finally {
        btnSaveProfile.disabled = false;
    }
}

// Trigger Manual Scraper and Gemini Matching (Steps 2 & 3)
async function triggerScrapeAndMatch() {
    btnTriggerScrape.disabled = true;
    scrapeLoader.style.display = "inline-block";
    scrapeIcon.style.display = "none";
    
    showToast("Launching Devpost Scraper & Gemini 2.0 Flash Matcher in background...", "info");
    
    try {
        const response = await fetch(`${API_BASE}/scrape`, { method: "POST" });
        const data = await response.json();
        
        if (data.status === "success") {
            showToast(data.message, "success");
            if (data.gemini_evaluated) {
                showToast("Gemini 2.0 Flash completed scoring matches!", "success");
            }
            await loadDashboardData();
        } else {
            showToast("Scraper error: " + data.detail, "error");
        }
    } catch (err) {
        console.error("Scraper failed:", err);
        showToast("Backend connection error during scraping.", "error");
    } finally {
        btnTriggerScrape.disabled = false;
        scrapeLoader.style.display = "none";
        scrapeIcon.style.display = "inline-block";
    }
}

// Trigger Manual Reminder (Step 5)
async function triggerDeadlineCheck() {
    btnTriggerReminders.disabled = true;
    showToast("Scanning tracked deadlines...", "info");
    
    try {
        const response = await fetch(`${API_BASE}/remind`, { method: "POST" });
        const data = await response.json();
        
        if (data.status === "success") {
            showToast(data.message, "success");
            if (data.reminded && data.reminded.length > 0) {
                showToast(`Sent ${data.reminded.length} urgent deadline reminders!`, "success");
            } else {
                showToast("No deadlines within 3 days. All quiet!", "info");
            }
        } else {
            showToast("Reminder check failed: " + data.message, "error");
        }
    } catch (err) {
        console.error("Reminder check failed:", err);
        showToast("Backend connection error.", "error");
    } finally {
        btnTriggerReminders.disabled = false;
    }
}

// Load data & refresh dashboard (Step 4 UI)
async function loadDashboardData() {
    try {
        // Fetch recommendations & tracked hackathons in parallel
        const [hResponse, tResponse] = await Promise.all([
            fetch(`${API_BASE}/hackathons`),
            fetch(`${API_BASE}/tracked`)
        ]);
        
        const hData = await hResponse.json();
        const tData = await tResponse.json();
        
        if (hData.status === "success") {
            hackathonsList = hData.hackathons || [];
            statScrapedCount.textContent = hackathonsList.length;
            
            // Calculate strong matches (score >= 7)
            const strongMatches = hackathonsList.filter(h => h.match_score >= 7);
            statMatchedCount.textContent = strongMatches.length;
        }
        
        if (tData.status === "success") {
            trackedList = tData.tracked || [];
            statTrackedCount.textContent = trackedList.length;
        }
        
        renderRecommendations();
        renderTracked();
        
    } catch (err) {
        console.error("Error loading dashboard data:", err);
        showToast("Failed to refresh dashboard stats.", "error");
    }
}

// Render Scored Recommendations (Step 4 UI)
function renderRecommendations() {
    recommendationsGrid.innerHTML = "";
    
    if (hackathonsList.length === 0) {
        recommendationsGrid.innerHTML = `
            <div class="empty-state">
                <i class="fa-solid fa-cloud-arrow-down"></i>
                <h4>No hackathons found in database</h4>
                <p>Click the "Scrape & Match" button in the top right to crawl Devpost and match them using Gemini 2.0 Flash.</p>
            </div>
        `;
        return;
    }
    
    hackathonsList.forEach(h => {
        const isTracked = trackedList.some(t => t.url === h.url);
        const score = h.match_score !== undefined ? h.match_score : "N/A";
        
        // Define score badge type & card styling class
        let badgeClass = "score-badge-low";
        let cardClass = "";
        if (typeof score === "number") {
            if (score >= 7) {
                badgeClass = "score-badge-high";
                cardClass = "match-high";
            } else if (score >= 4) {
                badgeClass = "score-badge-medium";
                cardClass = "match-medium";
            }
        }
        
        // Calculate dynamic deadline text & styles
        let deadlineLabel = h.deadline_raw;
        let isDeadlineUrgent = false;
        
        if (h.deadline) {
            const daysLeft = Math.ceil((new Date(h.deadline) - new Date()) / (1000 * 60 * 60 * 24));
            if (daysLeft >= 0) {
                deadlineLabel = `${daysLeft} days left (${h.deadline_raw})`;
                if (daysLeft <= 3) isDeadlineUrgent = true;
            } else {
                deadlineLabel = `Ended (${h.deadline_raw})`;
            }
        }
        
        const card = document.createElement("div");
        card.className = `hackathon-card glass-panel ${cardClass}`;
        
        card.innerHTML = `
            <div class="card-top">
                <div class="card-title-area">
                    <span class="card-org">${escapeHTML(h.organization)}</span>
                    <h4>${escapeHTML(h.title)}</h4>
                </div>
                <div class="score-badge ${badgeClass}">
                    <span>${score}</span>
                    <span class="score-badge-label">Fit</span>
                </div>
            </div>
            
            <div class="tags-list">
                ${(h.tags || []).slice(0, 4).map(tag => `<span class="tag-chip">${escapeHTML(tag)}</span>`).join("")}
            </div>
            
            <div class="card-details">
                <div class="detail-item">
                    <span class="detail-label">🏆 Prize Pool</span>
                    <span class="detail-val prize-highlight">${escapeHTML(h.prize_pool)}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">👥 Eligibility</span>
                    <span class="detail-val">${escapeHTML(h.eligibility)}</span>
                </div>
                <div class="detail-item" style="grid-column: span 2;">
                    <span class="detail-label">📅 Deadline</span>
                    <span class="detail-val ${isDeadlineUrgent ? 'urgent-highlight' : ''}">
                        <i class="fa-regular fa-clock"></i> ${escapeHTML(deadlineLabel)}
                    </span>
                </div>
            </div>
            
            ${h.match_reason ? `
            <div class="ai-reason-bubble">
                <i class="fa-solid fa-robot"></i>
                <p>${escapeHTML(h.match_reason)}</p>
            </div>
            ` : ""}
            
            <div class="card-footer">
                <a href="${h.url}" target="_blank" class="card-link">
                    View on Devpost <i class="fa-solid fa-external-link"></i>
                </a>
                <button class="btn-track ${isTracked ? 'active' : ''}" data-url="${h.url}">
                    <i class="fa-solid ${isTracked ? 'fa-bookmark' : 'fa-plus'}"></i> ${isTracked ? 'Tracked' : 'Track'}
                </button>
            </div>
        `;
        
        // Add event listener to Track button
        const btnTrack = card.querySelector(".btn-track");
        btnTrack.addEventListener("click", () => handleTrackToggle(h.url, !isTracked));
        
        recommendationsGrid.appendChild(card);
    });
}

// Render Tracked Dashboard (Step 4 UI)
function renderTracked() {
    trackedGrid.innerHTML = "";
    
    if (trackedList.length === 0) {
        trackedGrid.innerHTML = `
            <div class="empty-state">
                <i class="fa-solid fa-calendar-day"></i>
                <h4>No tracked hackathons yet</h4>
                <p>Browse the "Smart Recommendations" tab and click "Track" on hackathons you want to join.</p>
            </div>
        `;
        return;
    }
    
    trackedList.forEach(h => {
        const score = h.match_score !== undefined ? h.match_score : "N/A";
        let badgeClass = "score-badge-low";
        if (typeof score === "number" && score >= 7) badgeClass = "score-badge-high";
        else if (typeof score === "number" && score >= 4) badgeClass = "score-badge-medium";
        
        let deadlineLabel = h.deadline_raw;
        let isDeadlineUrgent = false;
        
        if (h.deadline) {
            const daysLeft = Math.ceil((new Date(h.deadline) - new Date()) / (1000 * 60 * 60 * 24));
            if (daysLeft >= 0) {
                deadlineLabel = `${daysLeft} days left (${h.deadline_raw})`;
                if (daysLeft <= 3) isDeadlineUrgent = true;
            } else {
                deadlineLabel = `Ended (${h.deadline_raw})`;
            }
        }
        
        const card = document.createElement("div");
        card.className = "hackathon-card glass-panel";
        
        card.innerHTML = `
            <div class="card-top">
                <div class="card-title-area">
                    <span class="card-org">${escapeHTML(h.organization)}</span>
                    <h4>${escapeHTML(h.title)}</h4>
                </div>
                <div class="score-badge ${badgeClass}">
                    <span>${score}</span>
                    <span class="score-badge-label">Fit</span>
                </div>
            </div>
            
            <div class="card-details">
                <div class="detail-item">
                    <span class="detail-label">🏆 Prize Pool</span>
                    <span class="detail-val prize-highlight">${escapeHTML(h.prize_pool)}</span>
                </div>
                <div class="detail-item" style="grid-column: span 2;">
                    <span class="detail-label">📅 Deadline</span>
                    <span class="detail-val ${isDeadlineUrgent ? 'urgent-highlight' : ''}">
                        <i class="fa-regular fa-clock"></i> ${escapeHTML(deadlineLabel)}
                    </span>
                </div>
            </div>
            
            <div class="card-footer">
                <a href="${h.url}" target="_blank" class="card-link">
                    View Submission Guidelines <i class="fa-solid fa-external-link"></i>
                </a>
                <button class="btn-track active" data-url="${h.url}">
                    <i class="fa-solid fa-bookmark"></i> Untrack
                </button>
            </div>
        `;
        
        const btnTrack = card.querySelector(".btn-track");
        btnTrack.addEventListener("click", () => handleTrackToggle(h.url, false));
        
        trackedGrid.appendChild(card);
    });
}

// Track/Untrack toggle
async function handleTrackToggle(url, trackState) {
    try {
        const response = await fetch(`${API_BASE}/track`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ url: url, track: trackState })
        });
        
        const data = await response.json();
        if (data.status === "success") {
            const hName = hackathonsList.find(h => h.url === url)?.title || "Hackathon";
            if (trackState) {
                showToast(`Tracking '${hName}'! Alerts active.`, "success");
            } else {
                showToast(`Removed '${hName}' from tracked list.`, "info");
            }
            await loadDashboardData();
        } else {
            showToast("Tracking update failed: " + data.message, "error");
        }
    } catch (err) {
        console.error("Track toggle error:", err);
        showToast("Backend connection error.", "error");
    }
}

// Utility to escape HTML and prevent XSS
function escapeHTML(str) {
    if (!str) return "";
    return str.replace(/[&<>'"]/g, 
        tag => ({
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            "'": '&#39;',
            '"': '&quot;'
        }[tag] || tag)
    );
}
