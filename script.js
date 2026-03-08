// ===== State =====
const responses = {};
let currentStep = 0;
const totalSteps = 12;

// ===== DOM References =====
const chatMessages = document.getElementById("chatMessages");
const optionsContainer = document.getElementById("optionsContainer");
const textInputContainer = document.getElementById("textInputContainer");
const textInput = document.getElementById("textInput");
const sendBtn = document.getElementById("sendBtn");
const progressBar = document.getElementById("progressBar");
const progressText = document.getElementById("progressText");
const reportModal = document.getElementById("reportModal");
const reportContent = document.getElementById("reportContent");
const copyBtn = document.getElementById("copyBtn");
const downloadPdfBtn = document.getElementById("downloadPdfBtn");
const restartBtn = document.getElementById("restartBtn");
const modalClose = document.getElementById("modalClose");

// ===== Chat Flow Definition =====
const steps = [
  // Step 0: Welcome & Symptom Category
  {
    message:
      "Hello! I'm MedBot, your medical intake assistant. I'll help you prepare a clear report for your doctor.\n\nLet's start — what type of symptoms are you experiencing?",
    options: [
      "Pain / Discomfort",
      "Digestive Issues",
      "Respiratory Issues",
    ],
    hasOther: true,
    key: "symptomCategory",
  },
  // Step 1: Narrow down symptoms (dynamic based on step 0)
  {
    message: null, // set dynamically
    options: null, // set dynamically
    hasOther: true,
    key: "specificSymptom",
    dynamic: true,
  },
  // Step 2: Pain level
  {
    message:
      "On a scale, how would you rate your discomfort or pain level?",
    options: [
      "Mild (1-3) — Noticeable but manageable",
      "Moderate (4-6) — Interferes with daily activities",
      "Severe (7-10) — Debilitating, hard to function",
    ],
    key: "painLevel",
  },
  // Step 3: Pain location
  {
    message:
      "Where specifically are you feeling this? Please be as specific as possible (e.g., lower back, right knee, left side of chest, upper abdomen).",
    options: [
      "Head / Neck",
      "Chest / Upper Body",
      "Abdomen / Lower Body",
    ],
    hasOther: true,
    key: "painLocation",
  },
  // Step 4: Current medication
  {
    message:
      "Are you currently taking any medication for this condition? If so, is it effective?",
    options: [
      "Yes, and it's effective",
      "Yes, but it's NOT effective",
      "No medication currently",
    ],
    key: "medicationStatus",
  },
  // Step 5: Allergies
  {
    message:
      "Do you have any known allergies? Select all that apply, or type your specific allergies.",
    options: [
      "Drug / Medication allergies",
      "Food allergies",
      "Environmental allergies (pollen, dust, etc.)",
    ],
    hasOther: true,
    multiSelect: true,
    otherPlaceholder: "Type specific allergies or 'None'...",
    key: "allergies",
  },
  // Step 6: Diagnosed conditions
  {
    message:
      "Have you been previously diagnosed with any conditions? (e.g., diabetes, hypertension, asthma, anxiety)",
    options: [
      "Yes — chronic condition(s)",
      "Yes — past condition (resolved)",
      "No previous diagnoses",
    ],
    hasOther: true,
    otherPlaceholder: "List your diagnosed conditions...",
    key: "conditions",
  },
  // Step 7: Supplements & medication cycle
  {
    message:
      "Are you currently taking any supplements, vitamins, or on a medication cycle?",
    options: [
      "Yes, I take supplements/vitamins",
      "Yes, I'm on a medication cycle",
      "No, none currently",
    ],
    hasOther: true,
    otherPlaceholder: "List your supplements or medications...",
    key: "supplements",
  },
  // Step 8: Home remedies
  {
    message: "Have you tried any home remedies or self-treatment for your symptoms?",
    options: [
      "Yes, and they helped",
      "Yes, but no improvement",
      "No, I haven't tried any",
    ],
    hasOther: true,
    otherPlaceholder: "Describe the remedies you tried...",
    key: "homeRemedies",
  },
  // Step 9: Surgical history
  {
    message: "Do you have any surgical history — previous or upcoming surgeries?",
    options: [
      "Yes, I've had surgery before",
      "No previous surgeries",
      "I have one scheduled",
    ],
    hasOther: true,
    otherPlaceholder: "Describe your surgical history...",
    key: "surgeryHistory",
  },
  // Step 10: Expectations
  {
    message:
      "What are you hoping to get from your upcoming doctor visit? What's your main goal?",
    options: [
      "New supplement or medicine",
      "Personal recovery advice",
      "Considering a surgery",
    ],
    hasOther: true,
    otherPlaceholder: "Describe what you're looking for...",
    key: "expectations",
  },
  // Step 11: Side effects & dislikes
  {
    message:
      "Are there any medications or treatments that have NOT worked for you in the past, or that you'd like to avoid?\n\nRemember: if a treatment is optional, you can always opt out and ask for alternatives.",
    options: [
      "Yes, certain meds didn't work / had side effects",
      "I prefer to avoid specific treatments (if avoidable)",
      "No preferences — open to anything",
    ],
    hasOther: true,
    otherPlaceholder: "List medications to avoid or past side effects...",
    key: "sideEffects",
  },
  // Step 12: Doctor satisfaction
  {
    message:
      "Last question — how satisfied are you with your current healthcare provider?",
    options: [
      "Very satisfied",
      "Somewhat satisfied",
      "Not satisfied",
    ],
    key: "doctorSatisfaction",
    advisory: true,
  },
];

// ===== Symptom sub-options =====
const symptomSubOptions = {
  "Pain / Discomfort": {
    message: "Can you narrow down the type of pain or discomfort?",
    options: [
      "Headache / Migraine",
      "Joint or Muscle Pain",
      "Chest Pain or Tightness",
    ],
  },
  "Digestive Issues": {
    message: "What kind of digestive issue are you experiencing?",
    options: [
      "Nausea / Vomiting",
      "Stomach Pain / Cramping",
      "Acid Reflux / Heartburn",
    ],
  },
  "Respiratory Issues": {
    message: "What respiratory symptoms are you dealing with?",
    options: [
      "Shortness of Breath",
      "Persistent Cough",
      "Wheezing / Chest Congestion",
    ],
  },
};

// ===== Helper Functions =====

function addBotMessage(text) {
  const wrapper = document.createElement("div");
  wrapper.className = "message bot";
  wrapper.innerHTML = `
    <div class="bot-avatar">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M22 12h-4l-3 9L9 3l-3 9H2"/>
      </svg>
    </div>
    <div class="bubble">${text.replace(/\n/g, "<br>")}</div>
  `;
  chatMessages.appendChild(wrapper);
  scrollToBottom();
}

function addUserMessage(text) {
  const wrapper = document.createElement("div");
  wrapper.className = "message user";
  wrapper.innerHTML = `<div class="bubble">${text}</div>`;
  chatMessages.appendChild(wrapper);
  scrollToBottom();
}

function addTypingIndicator() {
  const wrapper = document.createElement("div");
  wrapper.className = "message bot";
  wrapper.id = "typingIndicator";
  wrapper.innerHTML = `
    <div class="bot-avatar">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M22 12h-4l-3 9L9 3l-3 9H2"/>
      </svg>
    </div>
    <div class="bubble typing-indicator">
      <span></span><span></span><span></span>
    </div>
  `;
  chatMessages.appendChild(wrapper);
  scrollToBottom();
}

function removeTypingIndicator() {
  const el = document.getElementById("typingIndicator");
  if (el) el.remove();
}

function scrollToBottom() {
  setTimeout(() => {
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }, 50);
}

function updateProgress(step) {
  const pct = Math.round(((step + 1) / totalSteps) * 100);
  progressBar.style.width = pct + "%";
  progressText.textContent = `Step ${step + 1} of ${totalSteps}`;
}

function showOptions(options, hasOther, otherPlaceholder, multiSelect) {
  optionsContainer.innerHTML = "";
  textInputContainer.style.display = "none";
  optionsContainer.style.display = "flex";

  if (multiSelect) {
    const selected = new Set();

    options.forEach((opt) => {
      const btn = document.createElement("button");
      btn.className = "option-btn";
      btn.innerHTML = `<span class="option-checkbox"></span>${opt}`;
      btn.addEventListener("click", () => {
        if (selected.has(opt)) {
          selected.delete(opt);
          btn.classList.remove("selected");
        } else {
          selected.add(opt);
          btn.classList.add("selected");
        }
        // Update done button state
        const doneBtn = document.getElementById("multiSelectDone");
        if (doneBtn) {
          doneBtn.disabled = selected.size === 0;
        }
      });
      optionsContainer.appendChild(btn);
    });

    if (hasOther) {
      const otherBtn = document.createElement("button");
      otherBtn.className = "option-btn";
      otherBtn.innerHTML = `<span class="option-checkbox"></span>Other (type your own)`;
      otherBtn.addEventListener("click", () => {
        optionsContainer.style.display = "none";
        textInputContainer.style.display = "flex";
        textInput.placeholder = otherPlaceholder || "Type your answer...";
        textInput.value = "";
        textInput.focus();
      });
      optionsContainer.appendChild(otherBtn);
    }

    // "None" option
    const noneBtn = document.createElement("button");
    noneBtn.className = "option-btn";
    noneBtn.innerHTML = `<span class="option-dot"></span>None`;
    noneBtn.addEventListener("click", () => handleOptionClick("None"));
    optionsContainer.appendChild(noneBtn);

    // Done button
    const doneBtn = document.createElement("button");
    doneBtn.className = "option-btn done-btn";
    doneBtn.id = "multiSelectDone";
    doneBtn.disabled = true;
    doneBtn.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16"><polyline points="20 6 9 17 4 12"/></svg> Done`;
    doneBtn.addEventListener("click", () => {
      if (selected.size > 0) {
        handleOptionClick([...selected].join(", "));
      }
    });
    optionsContainer.appendChild(doneBtn);
  } else {
    options.forEach((opt) => {
      const btn = document.createElement("button");
      btn.className = "option-btn";
      btn.innerHTML = `<span class="option-dot"></span>${opt}`;
      btn.addEventListener("click", () => handleOptionClick(opt));
      optionsContainer.appendChild(btn);
    });

    if (hasOther) {
      const otherBtn = document.createElement("button");
      otherBtn.className = "option-btn";
      otherBtn.innerHTML = `<span class="option-dot"></span>Other (type your own)`;
      otherBtn.addEventListener("click", () => {
        optionsContainer.style.display = "none";
        textInputContainer.style.display = "flex";
        textInput.placeholder = otherPlaceholder || "Type your answer...";
        textInput.value = "";
        textInput.focus();
      });
      optionsContainer.appendChild(otherBtn);
    }
  }
}

function hideAllInputs() {
  optionsContainer.style.display = "none";
  textInputContainer.style.display = "none";
}

function showToast(message) {
  let toast = document.querySelector(".toast");
  if (!toast) {
    toast = document.createElement("div");
    toast.className = "toast";
    document.body.appendChild(toast);
  }
  toast.textContent = message;
  toast.classList.add("show");
  setTimeout(() => toast.classList.remove("show"), 2500);
}

// ===== Core Logic =====

function handleOptionClick(value) {
  const step = steps[currentStep];
  responses[step.key] = value;
  addUserMessage(value);
  hideAllInputs();
  advanceStep();
}

function handleTextSubmit() {
  const value = textInput.value.trim();
  if (!value) return;

  const step = steps[currentStep];
  responses[step.key] = value;
  addUserMessage(value);
  hideAllInputs();
  textInput.value = "";
  advanceStep();
}

function advanceStep() {
  currentStep++;

  if (currentStep >= steps.length) {
    // All steps done — show report
    updateProgress(currentStep - 1);
    setTimeout(() => {
      addBotMessage(
        "Thank you for completing the intake! I've prepared your medical report. You can copy it or download it as a PDF to bring to your appointment."
      );
      setTimeout(() => showReport(), 600);
    }, 800);
    return;
  }

  updateProgress(currentStep);

  // Show typing then the next question
  addTypingIndicator();
  setTimeout(() => {
    removeTypingIndicator();
    presentStep(currentStep);
  }, 700 + Math.random() * 500);
}

function presentStep(stepIndex) {
  const step = steps[stepIndex];

  // Handle dynamic step (narrowing symptoms)
  if (step.dynamic) {
    const category = responses.symptomCategory || "";
    const sub = symptomSubOptions[category] || {
      message: "Can you describe your symptoms more specifically?",
      options: [
        "Getting worse over time",
        "Comes and goes intermittently",
        "Constant / always present",
      ],
    };
    step.message = sub.message;
    step.options = sub.options;
  }

  addBotMessage(step.message);

  // Show advisory if doctor satisfaction is "Not satisfied"
  if (step.advisory) {
    // We'll handle advisory after answer, not before
  }

  setTimeout(() => {
    showOptions(
      step.options,
      step.hasOther,
      step.otherPlaceholder,
      step.multiSelect
    );
  }, 300);
}

// After doctor satisfaction answer, show advisory if needed
const originalAdvance = advanceStep;
advanceStep = function () {
  // Check if we just answered the doctor satisfaction question
  if (
    currentStep === steps.length - 1 &&
    responses.doctorSatisfaction === "Not satisfied"
  ) {
    setTimeout(() => {
      addBotMessage(
        `<div class="advisory-message"><strong>A friendly reminder:</strong> Your health is your priority. If you feel your current provider isn't meeting your needs, don't hesitate to seek a second opinion or switch to a new doctor. You deserve care that listens to you and addresses your concerns. A fresh perspective can make a real difference.</div>`
      );
    }, 400);
    setTimeout(() => originalAdvance.call(this), 1400);
  } else {
    originalAdvance.call(this);
  }
};

// ===== Report Generation =====

function buildReportText() {
  const date = new Date().toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });

  return `MEDICAL INTAKE REPORT
Generated: ${date}
${"─".repeat(40)}

1. Primary Symptoms: ${responses.symptomCategory || "N/A"}

2. Specific Symptoms: ${responses.specificSymptom || "N/A"}

3. Pain Level: ${responses.painLevel || "N/A"}

4. Pain Location: ${responses.painLocation || "N/A"}

5. Current Medication Status: ${responses.medicationStatus || "N/A"}

6. Allergies: ${responses.allergies || "N/A"}

7. Diagnosed Conditions: ${responses.conditions || "N/A"}

8. Supplements / Medications: ${responses.supplements || "N/A"}

9. Home Remedies Tried: ${responses.homeRemedies || "N/A"}

10. Surgical History: ${responses.surgeryHistory || "N/A"}

11. Visit Expectations: ${responses.expectations || "N/A"}

12. Medications to Avoid / Side Effects: ${responses.sideEffects || "N/A"}

13. Provider Satisfaction: ${responses.doctorSatisfaction || "N/A"}

${"─".repeat(40)}
This report is for informational purposes to assist your
healthcare provider. It is not a medical diagnosis.
Please share it with your doctor during your appointment
to help make the visit more efficient, as appointments
are professional and typically limited in time.`;
}

function showReport() {
  const date = new Date().toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });

  const fields = [
    ["Primary Symptoms", responses.symptomCategory],
    ["Specific Symptoms", responses.specificSymptom],
    ["Pain Level", responses.painLevel],
    ["Pain Location", responses.painLocation],
    ["Current Medication Status", responses.medicationStatus],
    ["Allergies", responses.allergies],
    ["Diagnosed Conditions", responses.conditions],
    ["Supplements / Medications", responses.supplements],
    ["Home Remedies Tried", responses.homeRemedies],
    ["Surgical History", responses.surgeryHistory],
    ["Visit Expectations", responses.expectations],
    ["Medications to Avoid / Side Effects", responses.sideEffects],
    ["Provider Satisfaction", responses.doctorSatisfaction],
  ];

  let html = `
    <div class="report-title">Medical Intake Report</div>
    <div class="report-date">${date}</div>
    <div class="report-divider"></div>
  `;

  fields.forEach(([label, value]) => {
    html += `
      <div class="report-section">
        <div class="report-label">${label}</div>
        <div class="report-value">${value || "N/A"}</div>
      </div>
    `;
  });

  html += `
    <div class="report-disclaimer">
      This report is for informational purposes to assist your healthcare provider.<br>
      It is not a medical diagnosis. Please share it with your doctor during your appointment<br>
      to help make the visit more efficient, as appointments are professional and typically limited in time.
    </div>
  `;

  reportContent.innerHTML = html;
  reportModal.style.display = "flex";
}

// ===== Event Listeners =====

sendBtn.addEventListener("click", handleTextSubmit);
textInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") handleTextSubmit();
});

copyBtn.addEventListener("click", () => {
  navigator.clipboard.writeText(buildReportText()).then(() => {
    showToast("Report copied to clipboard!");
  });
});

downloadPdfBtn.addEventListener("click", () => {
  downloadPdfBtn.disabled = true;
  downloadPdfBtn.textContent = "Generating...";

  fetch("/generate-pdf", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(responses),
  })
    .then((res) => {
      if (!res.ok) throw new Error("PDF generation failed");
      return res.blob();
    })
    .then((blob) => {
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `medical_intake_${new Date().toISOString().slice(0, 10)}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
      showToast("PDF downloaded!");
    })
    .catch((err) => {
      console.error(err);
      showToast("Failed to generate PDF. Please try again.");
    })
    .finally(() => {
      downloadPdfBtn.disabled = false;
      downloadPdfBtn.innerHTML = `
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
          <polyline points="7 10 12 15 17 10"/>
          <line x1="12" y1="15" x2="12" y2="3"/>
        </svg>
        Download PDF
      `;
    });
});

modalClose.addEventListener("click", () => {
  reportModal.style.display = "none";
});

restartBtn.addEventListener("click", () => {
  // Reset state
  Object.keys(responses).forEach((k) => delete responses[k]);
  currentStep = 0;
  chatMessages.innerHTML = "";
  reportModal.style.display = "none";
  updateProgress(0);
  startChat();
});

// Close modal on overlay click
reportModal.addEventListener("click", (e) => {
  if (e.target === reportModal) {
    reportModal.style.display = "none";
  }
});

// ===== Start =====

function startChat() {
  addTypingIndicator();
  setTimeout(() => {
    removeTypingIndicator();
    presentStep(0);
  }, 1000);
}

startChat();
