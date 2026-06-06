// region Variables

const clearSearchInputBtn = document.getElementById('clear_search_btn');
const searchCandidatesTableInput = document.getElementById('search_txt_input');
const candidatesTable = document.getElementById('candidates-table');
const jobDetailsTable = document.getElementById('job_details_table');
const noSearchResultsRow = document.getElementById('no_search_results');
const selectedJobIDHiddenInput = document.getElementById('selected_job_id');
const editJobWindow = document.getElementById('editJob-window');
const addCandidatesBtn = document.getElementById('add-candidates-btn');
const selectAllCandidates = document.getElementById('select-all-candidates');

let selectedJobElement = null;
let matchScoreSortOrder = 'desc';
let experienceSortOrder = 'desc';

// endregion
// region EVENT LISTENERS

document.addEventListener('DOMContentLoaded', () => {
    const lastJobId = sessionStorage.getItem('lastSelectedJobId');
    if (lastJobId) {
        const jobCard = document.querySelector(`.job-card[data-job-id="${lastJobId}"]`);
        if (jobCard) selectJob(jobCard);
    }
    addCandidatesBtn.disabled = selectedJobElement === null;
    attachCheckboxListeners();
    injectScoreModalStyles();
});

selectAllCandidates.addEventListener('change', function () {
    candidatesTable.querySelectorAll('#candidates-table tbody .candidate-checkbox')
        .forEach(cb => { cb.checked = this.checked; });
    updateDeleteButtonState();
});

// endregion

// region Score Modal Styles (injected once)

function injectScoreModalStyles() {
    const style = document.createElement('style');
    style.textContent = `
        /* ── Score badge in table cell ── */
        .match-score-cell { white-space: nowrap; }

        .score-badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            font-weight: 700;
            font-size: 15px;
            padding: 5px 13px;
            border-radius: 999px;
            background: rgba(0,0,0,0.07);
            cursor: pointer;
            transition: background .18s, transform .12s;
            user-select: none;
        }
        .score-badge:hover {
            background: rgba(0,0,0,0.14);
            transform: translateY(-1px);
        }
        .score-badge:active { transform: translateY(0); }
        .score-info-icon { font-size: 12px; opacity: .45; }

        /* ── Overlay dims the page behind the panel ── */
        #score-panel-overlay {
            display: none;
            position: fixed;
            inset: 0;
            z-index: 9998;
            background: rgba(0,0,0,.25);
            backdrop-filter: blur(2px);
            animation: overlayFadeIn .18s ease;
        }
        #score-panel-overlay.open { display: block; }
        @keyframes overlayFadeIn { from { opacity:0; } to { opacity:1; } }

        /* ── Main panel ── */
        #score-panel {
            position: fixed;
            z-index: 9999;
            width: 480px;
            max-width: calc(100vw - 32px);
            max-height: 82vh;
            overflow-y: auto;
            background: #1e1e2e;
            color: #cdd6f4;
            border-radius: 18px;
            padding: 0;
            box-shadow: 0 24px 64px rgba(0,0,0,.6), 0 0 0 1px rgba(255,255,255,.06);
            font-size: 14px;
            line-height: 1.65;
            animation: panelSlideIn .2s cubic-bezier(.34,1.56,.64,1);
        }
        @keyframes panelSlideIn {
            from { opacity:0; transform: translateY(10px) scale(.97); }
            to   { opacity:1; transform: translateY(0)   scale(1);    }
        }
        #score-panel::-webkit-scrollbar { width: 5px; }
        #score-panel::-webkit-scrollbar-track { background: transparent; }
        #score-panel::-webkit-scrollbar-thumb { background: rgba(255,255,255,.12); border-radius: 99px; }

        /* Panel header */
        .panel-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 20px 24px 16px;
            border-bottom: 1px solid rgba(255,255,255,.07);
            position: sticky;
            top: 0;
            background: #1e1e2e;
            border-radius: 18px 18px 0 0;
            z-index: 1;
        }
        .panel-header h4 {
            margin: 0;
            font-size: 14px;
            font-weight: 700;
            color: #cba6f7;
            letter-spacing: .6px;
            text-transform: uppercase;
        }
        .panel-close {
            font-size: 18px;
            cursor: pointer;
            color: #6c7086;
            line-height: 1;
            padding: 4px 8px;
            border-radius: 8px;
            transition: background .15s, color .15s;
            border: none;
            background: none;
        }
        .panel-close:hover { background: rgba(255,255,255,.1); color: #cdd6f4; }

        /* Panel body */
        .panel-body { padding: 20px 24px 24px; }

        /* Section blocks */
        .score-section {
            margin-bottom: 18px;
        }
        .score-section-title {
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: .7px;
            color: #89b4fa;
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .score-section-title .section-weight {
            font-size: 10px;
            font-weight: 500;
            color: #585b70;
            letter-spacing: 0;
            text-transform: none;
        }

        /* Skill pills */
        .skill-tag {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 999px;
            font-size: 12px;
            font-weight: 600;
            margin: 3px 4px 3px 0;
            letter-spacing: .2px;
        }
        .skill-matched {
            background: rgba(166,227,161,.15);
            color: #a6e3a1;
            border: 1px solid rgba(166,227,161,.3);
        }
        .skill-missing {
            background: rgba(243,139,168,.15);
            color: #f38ba8;
            border: 1px solid rgba(243,139,168,.3);
        }

        /* Missing detail box */
        .missing-list {
            margin-top: 10px;
            padding: 10px 14px;
            background: rgba(243,139,168,.06);
            border-radius: 10px;
            border-left: 3px solid rgba(243,139,168,.5);
            font-size: 12px;
            color: #f38ba8;
            line-height: 2;
        }

        /* Zero score banner */
        .zero-score-msg {
            display: flex;
            align-items: center;
            gap: 8px;
            color: #f38ba8;
            font-weight: 600;
            font-size: 13px;
            margin-bottom: 16px;
            padding: 10px 14px;
            background: rgba(243,139,168,.08);
            border-radius: 10px;
            border: 1px solid rgba(243,139,168,.2);
        }

        /* Divider */
        .score-divider {
            border: none;
            border-top: 1px solid rgba(255,255,255,.07);
            margin: 16px 0;
        }

        /* Exp / Edu breakdown row */
        .breakdown-row {
            display: flex;
            gap: 24px;
            margin-top: 8px;
        }
        .breakdown-item {
            display: flex;
            flex-direction: column;
            gap: 3px;
        }
        .breakdown-label {
            font-size: 10px;
            text-transform: uppercase;
            letter-spacing: .5px;
            color: #585b70;
        }
        .breakdown-value {
            font-size: 15px;
            font-weight: 700;
            color: #cdd6f4;
        }

        /* Total score footer */
        .score-total-line {
            font-size: 13px;
            color: #a6adc8;
            padding: 14px 24px;
            border-top: 1px solid rgba(255,255,255,.07);
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        .score-total-line strong { font-size: 22px; font-weight: 800; }
    `;
    document.head.appendChild(style);

    // Create the persistent panel + overlay (hidden by default)
    const overlay = document.createElement('div');
    overlay.id = 'score-panel-overlay';
    overlay.addEventListener('click', closeScorePanel);
    document.body.appendChild(overlay);

    const panel = document.createElement('div');
    panel.id = 'score-panel';
    panel.innerHTML = '<h4>ATS Score <span class="panel-close" onclick="closeScorePanel()">✕</span></h4>';
    panel.addEventListener('click', e => e.stopPropagation());
    document.body.appendChild(panel);
}

function closeScorePanel() {
    document.getElementById('score-panel-overlay').classList.remove('open');
    document.getElementById('score-panel').style.display = 'none';
}

function openScorePanel(badgeEl, html) {
    const panel   = document.getElementById('score-panel');
    const overlay = document.getElementById('score-panel-overlay');
    panel.innerHTML = html;
    panel.style.display = 'block';
    overlay.classList.add('open');

    // Centre the panel in the viewport
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    const pw = Math.min(480, vw - 32);
    panel.style.width    = pw + 'px';
    panel.style.maxWidth = pw + 'px';
    panel.style.left     = Math.round((vw - pw) / 2) + 'px';

    // Vertically: slight upper-centre (40% from top)
    const estimatedH = Math.min(panel.scrollHeight || 460, vh * 0.82);
    panel.style.top  = Math.max(16, Math.round(vh * 0.5 - estimatedH * 0.5)) + 'px';
}

// endregion

// region setMatchScoreColors

function setMatchScoreColors() {
    document.querySelectorAll('.match-score-value').forEach((el) => {
        const score = parseFloat(el.textContent);
        if (!isNaN(score)) {
            const ratio = Math.min(100, Math.max(0, score)) / 100;
            const red = Math.floor(255 * clamp(1 - ratio, 0, 0.45) * 2);
            const green = Math.floor(255 * clamp(ratio, 0, 0.45) * 2);
            el.style.color = `rgb(${red}, ${green}, 0)`;
        }
    });
}

// endregion
// region searchTable

function searchTable() {
    const searchTerm = searchCandidatesTableInput.value.toLowerCase().trim();
    const tbody = candidatesTable.querySelector('tbody');
    const rows = tbody.querySelectorAll('tr');
    let hasMatches = false;

    rows.forEach((row) => {
        if (row.id === 'noResultsRow') return;
        const cells = row.querySelectorAll('td:not(.checkbox-col)');
        let rowText = '';
        cells.forEach((cell) => { rowText += cell.textContent.toLowerCase() + ' '; });
        if (searchTerm === '' || rowText.includes(searchTerm)) {
            row.style.display = '';
            hasMatches = true;
        } else {
            row.style.display = 'none';
        }
    });

    if (clearSearchInputBtn) clearSearchInputBtn.disabled = searchTerm === '';
    if (noSearchResultsRow) noSearchResultsRow.style.display = !hasMatches ? 'block' : 'none';
}

// endregion
// region selectJob

function selectJob(newElement) {
    if (selectedJobElement === newElement) return;
    selectedJobElement = newElement;
    selectedJobIDHiddenInput.value = selectedJobElement.dataset.jobId;

    document.querySelectorAll('.job-card').forEach(card => card.classList.remove('active'));
    selectedJobElement.classList.add('active');

    const jobData = {
        id: selectedJobElement.dataset.jobId,
        job_title: selectedJobElement.dataset.jobTitle,
        min_years_exp: selectedJobElement.dataset.minYearsExp,
        min_edu: selectedJobElement.dataset.minEdu,
        min_edu_weight: selectedJobElement.dataset.minEduWeight,
        min_exp_weight: selectedJobElement.dataset.minExpWeight,
        skill_name_weight: JSON.parse(selectedJobElement.dataset.skills),
    };

    updateJobDetailsTable(jobData);
    updateCandidatesTable();
    addCandidatesBtn.disabled = false;
    sessionStorage.setItem('lastSelectedJobId', selectedJobIDHiddenInput.value);
}

// endregion
// region CANDIDATES TABLE

/**
 * Build the ATS score cell. Click the badge to open a full breakdown panel.
 * Shows matched skills (green) and missing skills (red) with explicit messages.
 * Score 0 when no required skills found.
 *
 * Skill matching uses the same core-token logic as the Python backend:
 * 1. Exact substring of full skill phrase
 * 2. Exact substring of core tokens (noise words stripped)
 * 3. Each core token individually present in CV text
 * This ensures the display agrees with the backend score.
 */

// Mirrors Python's SKILL_QUALIFIER_NOISE and _core_skill_tokens()
const SKILL_NOISE = new Set([
    'good','great','excellent','strong','solid','proven','advanced','basic',
    'intermediate','proficient','expert','experienced','familiarity','ability',
    'skill','knowledge','understanding','working','player','practitioner',
    'enthusiast','lover','fan','using','preferred','required','hands-on',
]);

const STOPWORDS_JS = new Set([
    'a','an','the','and','or','in','on','at','for','to','of','with','is','are',
    'be','have','has','been','we','our','you','i','my','it','its','this','that',
    'as','by','from','was','were','will','can','should','must','may','not','but',
    'if','so','do','did','who','what','how','when','where','also','than','more',
    'some','any','all','into','over','after','about','no','just',
]);

function coreTokens(skill) {
    const tokens = skill.toLowerCase()
        .replace(/[^a-z0-9\s]/g, ' ')
        .split(/\s+/)
        .filter(t => t.length >= 3 && !STOPWORDS_JS.has(t));
    const core = tokens.filter(t => !SKILL_NOISE.has(t));
    return core.length > 0 ? core : tokens;
}

function simpleStem(w) {
    w = w.toLowerCase().replace(/s$/, '');
    if (w.endsWith('ie')) w = w.slice(0, -2) + 'y';
    return w;
}

function wbMatch(term, text) {
    // Word-boundary match — prevents "java" matching inside "javascript"
    try {
        const escaped = term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        return new RegExp('\\b' + escaped + '\\b').test(text);
    } catch(e) {
        return text.includes(term);
    }
}

// Common aliases — mirrors Python _SKILL_ALIASES
const SKILL_ALIASES = {
    'javascript': ['js', 'ecmascript', 'es6'],
    'typescript': ['ts'],
    'python': ['py'],
    'kubernetes': ['k8s'],
    'postgresql': ['postgres', 'psql'],
    'mongodb': ['mongo'],
    'machine learning': ['ml'],
    'continuous integration': ['ci', 'cicd', 'ci/cd'],
    'continuous delivery': ['cd', 'cicd', 'ci/cd'],
};
const ALIAS_REVERSE = {};
Object.entries(SKILL_ALIASES).forEach(([canon, aliases]) => {
    aliases.forEach(a => { ALIAS_REVERSE[a] = canon; });
});

function skillFoundInCV(skill, cvTextLower, cvStemsSet) {
    const sl = skill.toLowerCase();

    // 1. Full phrase word-boundary match
    if (wbMatch(sl, cvTextLower)) return true;

    // 2. Core tokens — word-boundary match for each core token
    const core = coreTokens(skill);
    for (const ct of core) {
        if (wbMatch(ct, cvTextLower)) return true;
        // Stem match (only for stems >= 4 chars to avoid false positives)
        const st = simpleStem(ct);
        if (st.length >= 4 && cvStemsSet.has(st)) return true;
    }

    // 3. Alias lookup
    const aliases = SKILL_ALIASES[sl] || [];
    for (const alias of aliases) {
        if (wbMatch(alias, cvTextLower)) return true;
    }

    // 4. Reverse alias
    const canonical = ALIAS_REVERSE[sl];
    if (canonical && wbMatch(canonical, cvTextLower)) return true;

    return false;
}

// Education level map (mirrors Python EDUCATION_LEVELS)
const EDU_LEVELS = {
    'phd': 4, 'doctorate': 4,
    'master': 3, 'masters': 3, 'msc': 3, 'mba': 3,
    'bachelor': 2, 'bachelors': 2, 'bsc': 2,
    'diploma': 1, 'highschool': 1,
    'none': 0
};
function parseEduLevel(raw) {
    const s = (raw || '').toLowerCase();
    for (const [k, v] of Object.entries(EDU_LEVELS)) {
        if (s.includes(k)) return { label: k.charAt(0).toUpperCase() + k.slice(1), level: v };
    }
    return { label: raw && raw !== 'none' ? raw : 'Not specified', level: 0 };
}

function buildScoreCell(candidate, jobSkills) {
    const score = parseFloat(candidate.match_score) || 0;
    const cell  = document.createElement('td');
    cell.className = 'match-score-cell';

    // ── Score color ──
    const ratio = Math.min(100, Math.max(0, score)) / 100;
    const red   = Math.floor(255 * clamp(1 - ratio, 0, 0.45) * 2);
    const green = Math.floor(255 * clamp(ratio, 0, 0.45) * 2);
    const scoreColor = `rgb(${red}, ${green}, 0)`;

    // ── Job requirements from active job card ──
    const jobCard   = document.querySelector('.job-card.active');
    const reqExpYrs = jobCard ? (parseInt(jobCard.dataset.minYearsExp) || 0) : 0;
    const reqEduRaw = jobCard ? (jobCard.dataset.minEdu || 'none') : 'none';
    const expWeight = jobCard ? (parseInt(jobCard.dataset.minExpWeight) || 0) : 0;
    const eduWeight = jobCard ? (parseInt(jobCard.dataset.minEduWeight) || 0) : 0;

    // ── Candidate values ──
    const cvExpYrs = parseInt(candidate.experience) || 0;
    const cvEduRaw = candidate.education || 'none';
    const reqEdu   = parseEduLevel(reqEduRaw);
    const cvEdu    = parseEduLevel(cvEduRaw);
    const expMet   = reqExpYrs === 0 || cvExpYrs >= reqExpYrs;
    const eduMet   = reqEdu.level === 0 || cvEdu.level >= reqEdu.level;

    // ── Skill matching ──
    const allSkills     = Object.keys(jobSkills || {});
    const matchedSkills = [];
    const missingSkills = [];

    if (allSkills.length > 0) {
        const rawCV = [
            candidate.file_text || '',
            candidate.cv_text   || '',
            candidate.skills    || '',
            candidate.education || '',
        ].join(' ').toLowerCase().replace(/[^a-z0-9\s]/g, ' ');

        const cvStemsSet = new Set(
            rawCV.split(/\s+/)
                .filter(t => t.length >= 2 && !STOPWORDS_JS.has(t))
                .map(simpleStem)
        );

        allSkills.forEach(skill =>
            (skillFoundInCV(skill, rawCV, cvStemsSet) ? matchedSkills : missingSkills).push(skill)
        );
    }

    // ── Panel HTML ──────────────────────────────────────────────────────────
    let p = `
        <div class="panel-header">
            <h4>📊 ATS Score Breakdown</h4>
            <button class="panel-close" onclick="closeScorePanel()">✕</button>
        </div>
        <div class="panel-body">
    `;

    // Zero-score banner
    if (score === 0 && allSkills.length > 0) {
        p += `<div class="zero-score-msg">⚠️ None of the required skills were found in this CV — score is 0%.</div>`;
    }

    // ── SKILLS ──
    if (allSkills.length > 0) {
        if (matchedSkills.length > 0) {
            p += `<div class="score-section">
                <div class="score-section-title">✅ Skills found in CV (${matchedSkills.length})</div>
                ${matchedSkills.map(s => `<span class="skill-tag skill-matched">${s}</span>`).join('')}
            </div>`;
        }
        if (missingSkills.length > 0) {
            p += `<div class="score-section">
                <div class="score-section-title">❌ Skills not in CV (${missingSkills.length})</div>
                ${missingSkills.map(s => `<span class="skill-tag skill-missing">${s}</span>`).join('')}
                <div class="missing-list">
                    ${missingSkills.map(s => `• <strong>"${s}"</strong> does not exist in this CV`).join('<br>')}
                </div>
            </div>`;
        }
    } else {
        p += `<div class="score-section" style="color:#a6adc8;font-size:12px;">No specific skills required for this job.</div>`;
    }

    p += `<hr class="score-divider">`;

    // ── EXPERIENCE ──
    if (expWeight > 0 && reqExpYrs > 0) {
        const icon  = expMet ? '✅' : '❌';
        const color = expMet ? '#a6e3a1' : '#f38ba8';
        const cvExpLabel = cvExpYrs > 0 ? `${cvExpYrs} year${cvExpYrs !== 1 ? 's' : ''}` : 'Not specified';
        p += `<div class="score-section">
            <div class="score-section-title">${icon} Experience <span class="section-weight">${expWeight}% of score</span></div>
            <div class="breakdown-row">
                <div class="breakdown-item">
                    <span class="breakdown-label">Required</span>
                    <span class="breakdown-value">${reqExpYrs}+ years</span>
                </div>
                <div class="breakdown-item">
                    <span class="breakdown-label">CV has</span>
                    <span class="breakdown-value" style="color:${color}">${cvExpLabel}</span>
                </div>
            </div>
            ${!expMet ? `<div class="missing-list">• CV has ${cvExpLabel} — job requires ${reqExpYrs}+ years</div>` : ''}
        </div>`;
        p += `<hr class="score-divider">`;
    } else if (expWeight > 0) {
        p += `<div class="score-section">
            <div class="score-section-title" style="opacity:.5;">Experience — not required for this job</div>
        </div><hr class="score-divider">`;
    }

    // ── EDUCATION ──
    if (eduWeight > 0 && reqEdu.level > 0) {
        const icon  = eduMet ? '✅' : '❌';
        const color = eduMet ? '#a6e3a1' : '#f38ba8';
        p += `<div class="score-section">
            <div class="score-section-title">${icon} Education <span class="section-weight">${eduWeight}% of score</span></div>
            <div class="breakdown-row">
                <div class="breakdown-item">
                    <span class="breakdown-label">Required</span>
                    <span class="breakdown-value">${reqEdu.label} or higher</span>
                </div>
                <div class="breakdown-item">
                    <span class="breakdown-label">CV has</span>
                    <span class="breakdown-value" style="color:${color}">${cvEdu.label}</span>
                </div>
            </div>
            ${!eduMet ? `<div class="missing-list">• CV has "${cvEdu.label}" — job requires "${reqEdu.label}" or higher</div>` : ''}
        </div>`;
        p += `<hr class="score-divider">`;
    } else if (eduWeight > 0) {
        p += `<div class="score-section">
            <div class="score-section-title" style="opacity:.5;">Education — not required for this job</div>
        </div><hr class="score-divider">`;
    }

    // ── TOTAL ──
    p += `</div>
    <div class="score-total-line">
        <span>Overall ATS Match</span>
        <strong style="color:${scoreColor}">${score}%</strong>
    </div>`;

    // ── Badge ──
    const badge = document.createElement('div');
    badge.className = 'score-badge';
    badge.innerHTML = `<span class="match-score-value" style="color:${scoreColor}">${score}</span><span class="score-info-icon">ℹ</span>`;
    badge.addEventListener('click', e => { e.stopPropagation(); openScorePanel(badge, p); });

    cell.appendChild(badge);
    return cell;
}

function updateCandidatesTable(sortBy = 'match_score') {
    const candidates = JSON.parse(selectedJobElement.dataset.candidates);
    const jobSkills = JSON.parse(selectedJobElement.dataset.skills || '{}');

    candidates.sort((a, b) => {
        if (sortBy === 'experience') {
            const expA = parseFloat(a.experience) || 0;
            const expB = parseFloat(b.experience) || 0;
            return experienceSortOrder === 'asc' ? expA - expB : expB - expA;
        }
        const scoreA = parseFloat(a.match_score) || 0;
        const scoreB = parseFloat(b.match_score) || 0;
        return matchScoreSortOrder === 'asc' ? scoreA - scoreB : scoreB - scoreA;
    });

    const tbody = candidatesTable.querySelector('tbody');
    tbody.innerHTML = '';

    if (!candidates || candidates.length === 0) {
        const row = tbody.insertRow();
        row.id = 'noResultsRow';
        const cell = row.insertCell(0);
        cell.colSpan = 999;
        cell.textContent = candidates ? 'No candidates found for this job.' : 'Error loading candidates.';
        cell.style.textAlign = 'center';
        return;
    }

    candidates.forEach(candidate => {
        const row = tbody.insertRow();

        // Checkbox
        row.insertCell(0).innerHTML =
            `<input type="checkbox" class="candidate-checkbox" data-candidate-id="${candidate.id}">`;

        row.insertCell(1).textContent = candidate.name || 'N/A';
        row.insertCell(2).textContent = candidate.email || 'N/A';
        row.insertCell(3).textContent = candidate.phone || 'N/A';

        // View Resume
        const resumeCell = row.insertCell(4);
        if (candidate.id) {
            const link = document.createElement('a');
            link.href = `/parse_resumes/view_resume/${candidate.id}`;
            link.textContent = 'View';
            link.className = 'view-btn';
            link.target = '_blank';
            link.style.fontWeight = 'bold';
            resumeCell.appendChild(link);
        } else {
            resumeCell.textContent = 'N/A';
        }

        row.insertCell(5).textContent = candidate.education || 'N/A';
        row.insertCell(6).textContent = candidate.experience ? `${candidate.experience} years` : 'N/A';
        row.insertCell(7).textContent = candidate.skills || 'N/A';

        // ATS Score — organized breakdown cell
        row.appendChild(buildScoreCell(candidate, jobSkills));
    });

    attachCheckboxListeners();
}

// endregion
// region JOB DETAILS TABLE

function updateJobDetailsTable(jobData) {
    const tbody = jobDetailsTable.querySelector('tbody');
    tbody.innerHTML = '';

    const skills = Object.entries(jobData.skill_name_weight || {});

    if (skills.length > 0) {
        const firstSkillRow = tbody.insertRow();
        firstSkillRow.style.backgroundColor = '#f8f9fa';
        const skillCategoryCell = firstSkillRow.insertCell(0);
        skillCategoryCell.rowSpan = skills.length;
        skillCategoryCell.innerHTML = '<strong>Skills</strong>';
        firstSkillRow.insertCell(1).textContent = skills[0][0];
        firstSkillRow.insertCell(2).textContent = `${skills[0][1]}%`;

        for (let i = 1; i < skills.length; i++) {
            const skillRow = tbody.insertRow();
            skillRow.style.backgroundColor = '#f8f9fa';
            skillRow.insertCell(0).textContent = skills[i][0];
            skillRow.insertCell(1).textContent = `${skills[i][1]}%`;
        }
    } else {
        const noSkillsRow = tbody.insertRow();
        noSkillsRow.style.backgroundColor = '#f8f9fa';
        noSkillsRow.insertCell(0).innerHTML = '<strong>Skills</strong>';
        noSkillsRow.insertCell(1).textContent = 'No skills specified';
        noSkillsRow.insertCell(2).textContent = '0%';
    }

    const expRow = tbody.insertRow();
    expRow.style.backgroundColor = 'white';
    expRow.insertCell(0).innerHTML = '<strong>Experience</strong>';
    expRow.insertCell(1).textContent = `${jobData.min_years_exp}+ years`;
    expRow.insertCell(2).textContent = `${jobData.min_exp_weight}%`;

    const eduRow = tbody.insertRow();
    eduRow.style.backgroundColor = '#f8f9fa';
    eduRow.insertCell(0).innerHTML = '<strong>Education</strong>';
    eduRow.insertCell(1).textContent = jobData.min_edu || 'Not specified';
    eduRow.insertCell(2).textContent = `${jobData.min_edu_weight}%`;
}

// endregion
// region getSelectedCandidatesIds

function getSelectedCandidatesIds() {
    const checkboxes = candidatesTable.querySelectorAll('.candidate-checkbox:checked');
    const ids = Array.from(checkboxes).map(cb => cb.dataset.candidateId);
    if (ids.length === 0) return;
    return ids.join(',');
}

// endregion
// region attachCheckboxListeners

function attachCheckboxListeners() {
    candidatesTable.querySelectorAll('.candidate-checkbox').forEach(cb => {
        cb.removeEventListener('change', updateDeleteButtonState);
        cb.addEventListener('change', updateDeleteButtonState);
    });
    updateDeleteButtonState();
}

// endregion
// region updateDeleteButtonState

function updateDeleteButtonState() {
    const deleteButton = document.getElementById('delete-candidate-submit-button');
    const selected = candidatesTable.querySelectorAll('.candidate-checkbox:checked');
    if (deleteButton) deleteButton.disabled = selected.length === 0;
}

function updateEditJobWindow(jobId, jobTitle, jobDescription) {
    editJobWindow.querySelector('#edited_job_title').value = jobTitle;
    editJobWindow.querySelector('#edited_job_description').value = jobDescription;
    editJobWindow.querySelector('#edited_job_id').value = jobId;
}

// endregion
// region TABLE SORTING

function toggleMatchScoreSort() {
    matchScoreSortOrder = matchScoreSortOrder === 'desc' ? 'asc' : 'desc';
    updateCandidatesTable('match_score');
}

function toggleExperienceSort() {
    experienceSortOrder = experienceSortOrder === 'desc' ? 'asc' : 'desc';
    updateCandidatesTable('experience');
}

// endregion
