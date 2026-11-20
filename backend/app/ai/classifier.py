"""
Scikit-learn based Ticket Classifier for QueueMind AI.

Classifies inbound IT helpdesk tickets into standard institutional categories:
- Technical issues
- Examination issues
- Admission issues
- Fee and payment issues
- Network issues
- Hardware issues
- Software issues
- Account and access issues
- Other organisational issues

Maps predictions to departments and support teams.
"""

from typing import Dict, List, Optional, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline


# ── Training Dataset for Educational & Institutional Helpdesk ─────────────────

TRAINING_DATA: List[Tuple[str, str, str, str, str]] = [
    # (Text, Category, Subcategory, Recommended Dept, Recommended Team)
    # ── Fee and payment issues ──
    ("Fee receipt not generated after online payment via netbanking transaction failed", "Fee and payment issues", "Online Transaction", "Accounts Department", "Fee Support"),
    ("College tuition fee payment deducted twice from bank account need refund", "Fee and payment issues", "Refund Request", "Accounts Department", "Fee Support"),
    ("Semester exam fee challan verification pending in accounts office", "Fee and payment issues", "Fee Challan", "Accounts Department", "Fee Support"),
    ("Hostel mess fee installment payment gateway error debit card rejected", "Fee and payment issues", "Hostel Fee", "Accounts Department", "Fee Support"),
    ("Scholarship concession fee adjustment not reflected in fee portal ledger", "Fee and payment issues", "Scholarship Adjustment", "Accounts Department", "Fee Support"),
    ("Late fee penalty imposed wrongly despite paying before due date", "Fee and payment issues", "Late Fee Dispute", "Accounts Department", "Fee Support"),
    ("Payment status showing pending but amount debited from student account", "Fee and payment issues", "Payment Reconciliation", "Accounts Department", "Fee Support"),

    # ── Examination issues ──
    ("Admit card hall ticket download link not working for semester examination", "Examination issues", "Admit Card", "Examination Department", "Examination Support"),
    ("Exam portal server crashed during mid-term online test submission timed out", "Examination issues", "Exam Portal", "Examination Department", "Examination Support"),
    ("Marks card grade sheet showing withheld in university results portal", "Examination issues", "Result Discrepancy", "Examination Department", "Examination Support"),
    ("Examination registration form course code mismatch in elective subjects", "Examination issues", "Exam Registration", "Examination Department", "Examination Support"),
    ("Revaluation application fee paid but rechecking request not accepted", "Examination issues", "Revaluation", "Examination Department", "Examination Support"),
    ("Timetable clash between supplementary exam and regular backlog subject", "Examination issues", "Exam Schedule", "Examination Department", "Examination Support"),
    ("Hall ticket photograph and signature missing on printed admit card", "Examination issues", "Admit Card Error", "Examination Department", "Examination Support"),

    # ── Network issues ──
    ("Campus Wi-Fi connectivity dropping constantly in Block B and library", "Network issues", "Campus WiFi", "IT Department", "Network Support"),
    ("Hostel LAN port not providing internet ethernet cable plugged in no IP", "Network issues", "Hostel LAN", "IT Department", "Network Support"),
    ("Captive portal login page not loading on Android and iOS devices", "Network issues", "Captive Portal", "IT Department", "Network Support"),
    ("Complete network outage across campus router offline DNS resolution failed", "Network issues", "Outage", "IT Department", "Network Support"),
    ("Firewall blocking academic repository and research lab GitHub access", "Network issues", "Firewall Policy", "IT Department", "Network Support"),
    ("Campus VPN disconnecting every five minutes during remote library research", "Network issues", "VPN", "IT Department", "Network Support"),
    ("Slow internet bandwidth and high latency in computer science department lab", "Network issues", "Bandwidth", "IT Department", "Network Support"),

    # ── Hardware issues ──
    ("Lab computer monitor displaying black screen desktop PC not turning on", "Hardware issues", "Lab PC", "IT Department", "Hardware Support"),
    ("Overhead projector in seminar hall 3 flickering and bulb light red", "Hardware issues", "Projector", "IT Department", "Hardware Support"),
    ("Network printer in accounts department paper jammed and toner empty", "Hardware issues", "Printer", "IT Department", "Hardware Support"),
    ("Interactive smart board touch screen sensor not responding in classroom", "Hardware issues", "Smart Board", "IT Department", "Hardware Support"),
    ("Computer keyboard keys stuck and optical mouse not tracking in lab 4", "Hardware issues", "Peripherals", "IT Department", "Hardware Support"),
    ("Server rack UPS beeping battery backup warning in central server room", "Hardware issues", "UPS / Power", "IT Department", "Hardware Support"),

    # ── Software issues ──
    ("Matlab academic network license expired cannot launch simulation tool", "Software issues", "Academic License", "IT Department", "Software Support"),
    ("Visual Studio C++ compiler error missing build tools on lab workstations", "Software issues", "IDE / Compilers", "IT Department", "Software Support"),
    ("Office 365 student subscription showing unlicensed product error", "Software issues", "Office 365", "IT Department", "Software Support"),
    ("Antivirus false positive deleting student python project executables", "Software issues", "Antivirus", "IT Department", "Software Support"),
    ("SPSS statistical package installation failing on Windows 11 lab laptops", "Software issues", "Software Install", "IT Department", "Software Support"),
    ("CAD modeling software crashing on render graphics driver incompatible", "Software issues", "Design Software", "IT Department", "Software Support"),

    # ── Account and access issues ──
    ("Forgot student ERP portal password reset email not received", "Account and access issues", "Password Reset", "IT Department", "Network Support"),
    ("Student institutional Google email account locked after multiple attempts", "Account and access issues", "Account Locked", "IT Department", "Network Support"),
    ("Smart RFID campus identity card not unlocking library turnstile", "Account and access issues", "RFID / Smart Card", "IT Department", "Network Support"),
    ("Learning management system LMS Moodle login credentials invalid", "Account and access issues", "LMS Access", "IT Department", "Network Support"),
    ("Two factor authentication 2FA mobile number changed cannot verify login", "Account and access issues", "2FA MFA Reset", "IT Department", "Network Support"),

    # ── Admission issues ──
    ("Counseling seat allotment letter document verification appointment inquiry", "Admission issues", "Counseling", "Admission Department", "Admission Support"),
    ("Application status showing document pending after uploading 12th marksheet", "Admission issues", "Document Verification", "Admission Department", "Admission Support"),
    ("Branch change request eligibility criteria and vacancy seat availability", "Admission issues", "Branch Transfer", "Admission Department", "Admission Support"),
    ("Provisional admission letter not received after counseling round 2", "Admission issues", "Admission Status", "Admission Department", "Admission Support"),

    # ── Technical issues ──
    ("General technical issue with college website portal error 500 server", "Technical issues", "General Technical", "IT Department", "Network Support"),
    ("Audio system and microphone screeching in main auditorium", "Technical issues", "AV Systems", "IT Department", "Hardware Support"),
    ("Biometric attendance machine fingerprint scanner not recording morning shift", "Technical issues", "Biometric Terminal", "IT Department", "Hardware Support"),

    # ── Other organisational issues ──
    ("Classroom ceiling air conditioner remote missing and temperature high", "Other organisational issues", "Facilities", "Facilities Department", "Maintenance Support"),
    ("Lost student bus pass identity card replacement application procedure", "Other organisational issues", "Transport", "Facilities Department", "Transport Support"),
]


class TicketClassifier:
    """
    Trainable Scikit-learn classifier pipeline for ticket triage.
    Initializes on first use and provides category prediction + confidence scores.
    """
    def __init__(self) -> None:
        self.pipeline: Optional[Pipeline] = None
        self._meta_map: Dict[str, Tuple[str, str, str]] = {}
        self._train()

    def _train(self) -> None:
        texts: List[str] = []
        labels: List[str] = []

        for text, category, subcat, dept, team in TRAINING_DATA:
            texts.append(text.lower())
            labels.append(category)
            # Map category to default subcat, dept, team
            if category not in self._meta_map:
                self._meta_map[category] = (subcat, dept, team)

        self.pipeline = Pipeline([
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2), max_features=2500, stop_words="english")),
            ("clf", MultinomialNB(alpha=0.1)),
        ])
        self.pipeline.fit(texts, labels)

    def predict(self, subject: str, description: str) -> Dict[str, object]:
        """
        Classifies ticket text into predicted category with probability confidence.
        """
        if self.pipeline is None:
            self._train()

        combined_text = f"{subject} {description}".lower().strip()
        probs = self.pipeline.predict_proba([combined_text])[0]
        classes = self.pipeline.classes_

        best_idx = probs.argmax()
        predicted_category = str(classes[best_idx])
        confidence = float(probs[best_idx])

        # Retrieve default subcategory, recommended department and team
        default_subcat, dept, team = self._meta_map.get(
            predicted_category,
            ("General Support", "IT Department", "Network Support")
        )

        return {
            "predicted_category": predicted_category,
            "confidence": round(confidence, 3),
            "subcategory": default_subcat,
            "recommended_department": dept,
            "recommended_support_team": team,
            "all_scores": {
                str(c): round(float(p), 3)
                for c, p in sorted(zip(classes, probs), key=lambda x: x[1], reverse=True)[:4]
            },
        }


# Global classifier instance
classifier = TicketClassifier()
