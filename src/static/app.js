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
const aiProviderSelect = document.getElementById("ai-provider");

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
let availableProviders = [];

// Initialize Dashboard
document.addEventListener("DOMContentLoaded", () => {
    initApp();
});

async function initApp() {
    setupTabNavigation();
    setupEventListeners();
    await loadProviders();
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

function refreshScrapeButtonState() {
    const hasConfiguredProvider = availableProviders.some(provider => provider.configured);
    btnTriggerScrape.disabled = !(userProfile && hasConfiguredProvider);
}

async function loadProviders() {
    try {
        const response = await fetch(`${API_BASE}/providers`);
        const data = await response.json();
        availableProviders = data.providers || [];

        aiProviderSelect.innerHTML = "";

        if (availableProviders.length === 0) {
            aiProviderSelect.innerHTML = '<option value="gemini">No providers found</option>';
            aiProviderSelect.disabled = true;
            refreshScrapeButtonState();
            return;
        }

        availableProviders.forEach(provider => {
            const option = document.createElement("option");
            option.value = provider.id;
            option.textContent = `${provider.label}${provider.configured ? "" : " (API key missing)"}`;
            option.disabled = !provider.configured;
            aiProviderSelect.appendChild(option);
        });

        const firstReadyProvider = availableProviders.find(provider => provider.configured);
        aiProviderSelect.value = firstReadyProvider ? firstReadyProvider.id : availableProviders[0].id;
        aiProviderSelect.disabled = !firstReadyProvider;
        refreshScrapeButtonState();
    } catch (err) {
        console.error("Error loading providers:", err);
        aiProviderSelect.innerHTML = '<option value="gemini">Gemini</option><option value="groq">Groq</option>';
        aiProviderSelect.disabled = false;
        refreshScrapeButtonState();
    }
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
            profileStatus.className = "sidebar-status border-l border-[#2a2a2a] pl-4";
            profileStatus.innerHTML = `
                <span class="status-dot status-dot-success"></span>
                <span class="font-mono text-[10px] text-[#e8e8e8]">DB_CONNECTED: OK</span>
            `;
            
            // Enable Scraping when a provider is available
            refreshScrapeButtonState();
        } else {
            refreshScrapeButtonState();
        }
    } catch (err) {
        console.error("Error loading profile:", err);
        showToast("Failed to connect with database backend.", "error");
        refreshScrapeButtonState();
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
            profileStatus.className = "sidebar-status border-l border-[#2a2a2a] pl-4";
            profileStatus.innerHTML = `
                <span class="status-dot status-dot-success"></span>
                <span class="font-mono text-[10px] text-[#e8e8e8]">DB_CONNECTED: OK</span>
            `;
            
            // Enable scrape button when a provider is available
            refreshScrapeButtonState();
            
            // Load dashboard data
            await loadDashboardData();
        } else {
            showToast("Failed to save profile: " + data.message, "error");
        }
    } catch (err) {
        console.error("Error saving profile:", err);
        showToast("Backend connection error.", "error");
    } finally {
        refreshScrapeButtonState();
        btnSaveProfile.disabled = false;
    }
}

// Trigger Manual Scraper and Gemini Matching (Steps 2 & 3)
async function triggerScrapeAndMatch() {
    btnTriggerScrape.disabled = true;
    scrapeLoader.style.display = "inline-block";
    scrapeIcon.style.display = "none";
    const provider = aiProviderSelect.value || "gemini";
    
    const providerLabel = availableProviders.find(item => item.id === provider)?.label || provider;
    showToast(`Launching Devpost Scraper & ${providerLabel} Matcher in background...`, "info");
    
    try {
        const response = await fetch(`${API_BASE}/scrape?provider=${encodeURIComponent(provider)}`, { method: "POST" });
        const data = await response.json();
        
        if (data.status === "success") {
            showToast(data.message, "success");
            if (data.ai_evaluated) {
                showToast(`${providerLabel} completed scoring matches!`, "success");
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
            <div class="col-span-full py-12 flex flex-col items-start font-mono text-[#e8e8e8]">
                <p class="text-xs opacity-60">→ No hackathons found in database.</p>
                <p class="text-xs opacity-40 mt-1">SCRAPE_REQUIRED: TRUE</p>
            </div>
        `;
        return;
    }
    
    hackathonsList.forEach(h => {
        const isTracked = trackedList.some(t => t.url === h.url);
        const score = h.match_score !== undefined ? h.match_score : "N/A";
        
        // Define score badge type & card styling class
        let badgeClass = "text-[#666]";
        if (typeof score === "number") {
            if (score >= 7) {
                badgeClass = "text-[#00ff87]";
            } else if (score >= 4) {
                badgeClass = "text-[#fbbf24]";
            }
        }
        
        // Calculate dynamic deadline text & styles
        let deadlineLabel = h.deadline_raw;
        let isDeadlineUrgent = false;
        let isDeadlineImminent = false;
        let _daysLeft = null;

        if (h.deadline) {
            _daysLeft = Math.ceil((new Date(h.deadline) - new Date()) / (1000 * 60 * 60 * 24));
            if (_daysLeft >= 0) {
                deadlineLabel = `${_daysLeft}d [${h.deadline_raw}]`;
                if (_daysLeft <= 7) isDeadlineUrgent = true; // yellow for 3-7d
                if (_daysLeft <= 3) isDeadlineImminent = true; // red for <=3d
            } else {
                deadlineLabel = `EXPIRED [${h.deadline_raw}]`;
            }
        }
        
        const card = document.createElement("div");
        card.className = "flex flex-col gap-4 p-5 bg-[#1c1b1b] border border-[#1f1f1f] rounded-sm hover:border-[#333] transition-colors group";
        
        card.innerHTML = `
            <div class="flex justify-between items-start">
                <div class="flex flex-col gap-1">
                    <span class="font-mono text-[10px] uppercase tracking-wider text-[#666]">${escapeHTML(h.organization)}</span>
                    <h4 class="font-bold text-[#e8e8e8] text-sm leading-tight">${escapeHTML(h.title)}</h4>
                </div>
                <div class="flex flex-col items-end font-mono">
                    <span class="text-lg font-bold ${badgeClass}">${score}</span>
                    <span class="text-[8px] text-[#666] uppercase tracking-tighter mt-[-4px]">MATCH_SCORE</span>
                </div>
            </div>
            
            <div class="flex flex-wrap gap-2">
                ${(h.tags || []).slice(0, 3).map(tag => `<span class="px-2 py-0.5 font-mono text-[10px] bg-[#111] border border-[#222] text-[#888] rounded-sm">${escapeHTML(tag)}</span>`).join("")}
            </div>
            
            <div class="grid grid-cols-2 gap-4 pt-2 font-mono text-[10px]">
                <div class="flex flex-col gap-1">
                    <span class="text-[#666] uppercase tracking-tighter">PRIZE_POOL</span>
                    <span class="text-[#00ff87]">${escapeHTML(h.prize_pool)}</span>
                </div>
                <div class="flex flex-col gap-1">
                    <span class="text-[#666] uppercase tracking-tighter">DEADLINE</span>
                    <span class="${isDeadlineImminent ? 'text-[#ff4757]' : (isDeadlineUrgent ? 'text-[#fbbf24]' : 'text-[#e8e8e8]')}">${escapeHTML(deadlineLabel)}</span>
                </div>
            </div>
            
            ${h.match_reason ? `
            <div class="mt-2 p-3 bg-[#111] border-l border-[#222] font-mono text-[11px] text-[#888] leading-relaxed italic">
                <span class="text-[#444] mr-1">ANALYSIS:</span> ${escapeHTML(h.match_reason)}
            </div>
            ` : ""}
            
            <div class="flex items-center justify-between mt-auto pt-4 border-t border-[#1f1f1f]">
                <a href="${h.url}" target="_blank" class="font-mono text-[11px] text-[#666] hover:text-[#e8e8e8] flex items-center gap-2 transition-colors">
                    LINK <i class="fa-solid fa-arrow-right text-[8px]"></i>
                </a>
                <button class="btn-track font-mono text-[10px] px-3 py-1 border transition-all ${isTracked ? 'bg-[#ff4757] border-[#ff4757] text-white' : 'bg-transparent border-[#2a2a2a] text-[#666] hover:border-[#e8e8e8] hover:text-[#e8e8e8]'}" data-url="${h.url}">
                    ${isTracked ? 'UNTRACK' : 'TRACK_PROJECT'}
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
            <div class="col-span-full py-12 flex flex-col items-start font-mono text-[#e8e8e8]">
                <p class="text-xs opacity-60">→ No tracked projects found.</p>
                <p class="text-xs opacity-40 mt-1">TRACK_LIST: EMPTY</p>
            </div>
        `;
        return;
    }
    
    trackedList.forEach(h => {
        const score = h.match_score !== undefined ? h.match_score : "N/A";
        let badgeClass = "text-[#666]";
        if (typeof score === "number" && score >= 7) badgeClass = "text-[#00ff87]";
        else if (typeof score === "number" && score >= 4) badgeClass = "text-[#fbbf24]";
        
        let deadlineLabel = h.deadline_raw;
        let isDeadlineUrgent = false;
        let isDeadlineImminent = false;
        
        if (h.deadline) {
            const daysLeft = Math.ceil((new Date(h.deadline) - new Date()) / (1000 * 60 * 60 * 24));
            if (daysLeft >= 0) {
                deadlineLabel = `${daysLeft}d [${h.deadline_raw}]`;
                if (daysLeft <= 3) isDeadlineUrgent = true;
            } else {
                deadlineLabel = `EXPIRED [${h.deadline_raw}]`;
            }
        }
        
        const card = document.createElement("div");
        card.className = "flex flex-col gap-4 p-5 bg-[#1c1b1b] border border-[#1f1f1f] rounded-sm hover:border-[#333] transition-colors group";
        
        card.innerHTML = `
            <div class="flex justify-between items-start">
                <div class="flex flex-col gap-1">
                    <span class="font-mono text-[10px] uppercase tracking-wider text-[#666]">${escapeHTML(h.organization)}</span>
                    <h4 class="font-bold text-[#e8e8e8] text-sm leading-tight">${escapeHTML(h.title)}</h4>
                </div>
                <div class="font-mono text-lg font-bold ${badgeClass}">${score}</div>
            </div>
            
            <div class="grid grid-cols-2 gap-4 pt-2 font-mono text-[10px]">
                <div class="flex flex-col gap-1">
                    <span class="text-[#666] uppercase tracking-tighter">PRIZE_POOL</span>
                    <span class="text-[#00ff87]">${escapeHTML(h.prize_pool)}</span>
                </div>
                <div class="flex flex-col gap-1">
                    <span class="text-[#666] uppercase tracking-tighter">DEADLINE</span>
                    <span class="${isDeadlineImminent ? 'text-[#ff4757]' : (isDeadlineUrgent ? 'text-[#fbbf24]' : 'text-[#e8e8e8]')}">${escapeHTML(deadlineLabel)}</span>
                </div>
            </div>
            
            <div class="flex items-center justify-between mt-auto pt-4 border-t border-[#1f1f1f]">
                <a href="${h.url}" target="_blank" class="font-mono text-[11px] text-[#666] hover:text-[#e8e8e8] flex items-center gap-2 transition-colors">
                    GUIDELINES <i class="fa-solid fa-arrow-right text-[8px]"></i>
                </a>
                <button class="btn-track font-mono text-[10px] px-3 py-1 border bg-[#ff4757] border-[#ff4757] text-white rounded-sm hover:opacity-80 transition-opacity" data-url="${h.url}">
                    UNTRACK
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