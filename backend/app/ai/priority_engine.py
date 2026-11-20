"""
Intelligent Multi-Signal Priority Engine for QueueMind AI — Phase 6.

ROOT-CAUSE FIX:
  Previously, category weight (Examination=100, Network=70) contributed 40 pts to
  the composite score, causing Network tickets to frequently score equal to or above
  Examination tickets. Category is now used ONLY as a tie-breaker in queue ordering,
  not in the priority score. Priority is determined purely by severity signals:
    1. Service availability / outage scale
    2. Number of distinct users affected
    3. Academic / business deadline proximity
    4. Incident recurrence / cluster size
    5. Waiting time aging

Priority Levels:
  CRITICAL ≥ 80 pts  — Campus-wide outage, ongoing exam disruption, mass blockage
  HIGH     60–79 pts — Multi-user blocked, deadline approaching, recurring incident
  MEDIUM   35–59 pts — Single-user, workaround available, no critical deadline
  LOW      < 35 pts  — Minor inconvenience, cosmetic, routine info request

Transparent Signals stored in `applied_rules` and `evidence` for Help Desk.
"""

from datetime import datetime, timezone
import re
from typing import Dict, List, Optional
from app.models.ticket import TicketPriority


# ── Keyword Patterns ──────────────────────────────────────────────────────────
PATTERNS = {
    # Scale-of-impact signals
    "CAMPUS_WIDE": re.compile(
        r"\b("
        r"campus[- ]wide|entire (college|institution|campus|university|organization)|"
        r"all students|all employees|whole campus|all hostels|all labs|all departments|"
        r"every student|everyone affected|complete outage|entire network|"
        r"across (campus|all|multiple departments)|"
        r"org[- ]wide|institution[- ]wide|system[- ]wide|hundreds of (students|users)|"
        r"most students|most users"
        r")\b",
        re.IGNORECASE,
    ),
    "MULTIPLE_USERS": re.compile(
        r"\b("
        r"entire lab|whole class|all of us|multiple (students|users|employees)|"
        r"(entire|all|whole) lab \d+|block [a-z] (outage|down|all)|several (students|users|employees|members)|"
        r"our batch|departmental|many (students|users|employees)|"
        r"batch|group of (students|users)|a number of (students|users)|"
        r"across (the )?department|floor[- ]wide|building[- ]wide|wing[- ]wide"
        r")\b",
        re.IGNORECASE,
    ),
    "CRITICAL_SERVICE_DOWN": re.compile(
        r"\b("
        r"complete(ly)? (down|unavailable|offline)|total outage|blackout|"
        r"network down|wi-?fi.*down|ethernet down|campus outage|network outage|outage|"
        r"lost internet|router offline|no internet connection|"
        r"server (crash(ed)?|down|offline)|database (down|crashed)|"
        r"portal (down|unavailable|failing|crashed|not (working|accessible))|"
        r"payment gateway (down|failed|unavailable|throwing \d+|failing|error)|"
        r"gateway (throwing \d+|failing|down|error)|"
        r"exam(ination)? (portal|system) (down|unavailable|crashed|stopped working|not working)|"
        r"no internet at all|service unavailable|system failure|service (down|offline)|"
        r"completely (broken|failed|inaccessible)|down for everyone|not accessible to anyone"
        r")\b",
        re.IGNORECASE,
    ),
    # Deadline / time-critical signals
    "EXAM_IN_PROGRESS_OR_IMMINENT": re.compile(
        r"\b("
        r"exam(ination)?s? (in progress|is running|are running|currently running|ongoing|happening now|started|are in progress)|"
        r"examinations? (are|is) (in progress|ongoing|running|happening)|"
        r"while examinations? (are|is) in progress|"
        r"(during|in|for) (the |an )?(active |ongoing |live |mid-term |final |semester |online )?exam(ination)?s?|"
        r"(active|ongoing|live) exam(ination)?s?|"
        r"(online |mid-term |final )?test (running|in progress|ongoing|submission)|"
        r"exam(ination)?s? starts? in|test (starts?|begins?) in|"
        r"exam(ination)?s? (is |are )?(today|now|live)|"
        r"examination (is )?scheduled (for )?today|test in [1-9]\d* (hour|min)|"
        r"exam(ination)?s? (begins?|starts?) (soon|shortly|in [1-9])|"
        r"blocked (from|during|before) exam(ination)?"
        r")\b",
        re.IGNORECASE,
    ),
    "EXAM_APPROACHING": re.compile(
        r"\b("
        r"exam(ination)? (registration blocked|deadline|cutoff|approaching)|"
        r"admit card|hall ticket|"
        r"exam registration|blocked before exam(ination)?|"
        r"exam(ination)? (in [1-9]\d* (day|week)|next week|this week)|"
        r"result (not showing|withheld|blocked)|revaluation|grade (issue|withheld)"
        r")\b",
        re.IGNORECASE,
    ),
    "FEE_DEADLINE": re.compile(
        r"\b("
        r"deadline (today|tonight|is today|is tomorrow|approaching)|last day to pay|"
        r"fine (tomorrow|today|if not paid)|payment deadline|cutoff (date|today|tomorrow)|"
        r"due (tonight|today|tomorrow)|registration (closing|deadline)|"
        r"late fee (penalty|will be imposed)|admissions deadline|"
        r"before (the )?payment deadline|fee (cutoff|last date)|"
        r"admission deadline|fee deadline|payment due"
        r")\b",
        re.IGNORECASE,
    ),
    "FEE_ADMISSION_DEADLINE_APPROACHING": re.compile(
        r"\b("
        r"admission confirmation is blocked|admission.*deadline.*approaching|"
        r"deadline.*approaching|deadline is approaching|"
        r"payment.*blocked.*deadline|blocked.*deadline|"
        r"admission.*blocked|payment status (not updating|not updated|showing pending)"
        r")\b",
        re.IGNORECASE,
    ),
    "ESSENTIAL_SERVICE_BLOCKED": re.compile(
        r"\b("
        r"cannot (submit|access|login|pay|register|download|upload|complete|confirm)|"
        r"unable to (submit|access|login|pay|register|download|upload|complete|confirm)|"
        r"blocked (from|completely)|"
        r"not (working|accessible|available) (and|for|during|to)|"
        r"preventing (access|submission|completion|payment)|"
        r"admission (blocked|not confirming|confirmation is blocked)|"
        r"payment (failed|failing|blocked|error|not processing|stuck)|"
        r"payment.*failed|payment.*not.*updating|status.*not.*updated|not updating.*status|"
        r"cannot (complete|finish) (the )?(payment|admission|registration|exam)"
        r")\b",
        re.IGNORECASE,
    ),
    # Low-severity signals
    "MINOR_ISSUE": re.compile(
        r"\b("
        r"how to|query|inquiry|general information|procedure for|guidelines|"
        r"curious|question regarding|clarification|minor issue|minor inconvenience|"
        r"one person|one student|cosmetic|just me|only me|my own|"
        r"occasionally|sometimes|intermittent(ly)?|reconnect(ing)? fixes|"
        r"workaround|works after restart|no other users? affected|"
        r"not affecting others|not affecting anyone else|"
        r"sticking slightly|sticking|mouse.*wheel|single pc|pc \d+"
        r")\b",
        re.IGNORECASE,
    ),
    "URGENT_KEYWORD": re.compile(
        r"\b("
        r"immediately|urgent|emergency|asap|within \d+ hours?|"
        r"blocked completely|time[- ]sensitive|time[- ]critical"
        r")\b",
        re.IGNORECASE,
    ),
    # Recurrence signals
    "RECURRING": re.compile(
        r"\b("
        r"again|recurring|repeat(ed)?|happening again|same issue|"
        r"keeps? (happening|occurring|failing|disconnecting)|third time|"
        r"every (day|week|time)|persistent(ly)?|still not (resolved|fixed|working)"
        r")\b",
        re.IGNORECASE,
    ),
}

# Priority score thresholds
THRESHOLD_CRITICAL = 80.0
THRESHOLD_HIGH = 60.0
THRESHOLD_MEDIUM = 30.0


class PriorityEngine:
    """
    Computes ticket priority from pure severity signals.
    Category is NOT part of the score — it is a queue tie-breaker only.
    """

    @classmethod
    def evaluate(
        cls,
        subject: str,
        description: str,
        predicted_category: str = "",
        organization_id: Optional[int] = None,
        created_at: Optional[datetime] = None,
        incident_cluster_size: int = 0,
        distinct_affected_users: int = 0,
    ) -> Dict[str, object]:
        text = f"{subject} {description}".lower()
        applied_rules: List[str] = []
        evidence_found: List[str] = []

        # ── 1. Scale of Impact ────────────────────────────────────────────────
        is_campus_wide = bool(PATTERNS["CAMPUS_WIDE"].search(text))
        is_svc_down = bool(PATTERNS["CRITICAL_SERVICE_DOWN"].search(text))
        is_multi_user = bool(PATTERNS["MULTIPLE_USERS"].search(text))
        is_minor = bool(PATTERNS["MINOR_ISSUE"].search(text))

        # Cluster boost: distinct_users is the authoritative count for escalation
        # cluster_size (total reports) only matters for text signals when no distinct_users
        if distinct_affected_users >= 10:
            is_campus_wide = True
        elif distinct_affected_users >= 3:
            is_multi_user = True

        if is_campus_wide:
            impact = "CRITICAL"
            impact_points = 45.0
            affected_users_est = "Campus/org-wide (100+ users / essential service unavailable)"
            applied_rules.append(
                "RULE-IMP-01: Campus/org-wide scope → impact CRITICAL (+45 pts)"
            )
            evidence_found.append("Campus-wide / organisation-wide scope confirmed")
        elif is_svc_down and is_multi_user:
            impact = "CRITICAL"
            impact_points = 40.0
            affected_users_est = "Multiple users + critical service down"
            applied_rules.append(
                "RULE-IMP-02: Critical service down + multiple users → impact CRITICAL (+40 pts)"
            )
            evidence_found.append("Critical service unavailable, multiple users affected")
        elif is_svc_down and not is_minor:
            impact = "HIGH"
            impact_points = 28.0
            affected_users_est = "Service unavailable — scope under investigation"
            applied_rules.append(
                "RULE-IMP-03: Critical service unavailable → impact HIGH (+28 pts)"
            )
            evidence_found.append("Essential service reported unavailable")
        elif is_multi_user:
            impact = "HIGH"
            impact_points = 25.0
            affected_users_est = "Multiple users / departmental scope (5–50 users)"
            applied_rules.append(
                "RULE-IMP-04: Multiple users affected → impact HIGH (+25 pts)"
            )
            evidence_found.append("Multiple users affected")
        elif is_minor:
            impact = "LOW"
            impact_points = 5.0
            affected_users_est = "Individual — routine / cosmetic / workaround available"
            applied_rules.append(
                "RULE-IMP-05: Routine individual issue / workaround available → impact LOW (+5 pts)"
            )
        else:
            impact = "MEDIUM"
            impact_points = 25.0
            affected_users_est = "Individual user — no workaround evident"
            applied_rules.append(
                "RULE-IMP-06: Standard individual issue → impact MEDIUM (+25 pts)"
            )

        # ── 2. Urgency / Deadline Assessment ─────────────────────────────────
        is_exam_live = bool(PATTERNS["EXAM_IN_PROGRESS_OR_IMMINENT"].search(text))
        is_exam_near = bool(PATTERNS["EXAM_APPROACHING"].search(text))
        is_fee_deadline = bool(PATTERNS["FEE_DEADLINE"].search(text))
        is_fee_admission_near = bool(PATTERNS["FEE_ADMISSION_DEADLINE_APPROACHING"].search(text))
        is_essential_blocked = bool(PATTERNS["ESSENTIAL_SERVICE_BLOCKED"].search(text))
        is_urgent_kw = bool(PATTERNS["URGENT_KEYWORD"].search(text))
        is_recurring = bool(PATTERNS["RECURRING"].search(text))

        # Combine fee deadline signals
        is_fee_deadline = is_fee_deadline or is_fee_admission_near

        if is_exam_live:
            urgency = "CRITICAL"
            urgency_points = 38.0
            applied_rules.append(
                "RULE-URG-01: Exam in progress or starting imminently → urgency CRITICAL (+38 pts)"
            )
            evidence_found.append("Examination in progress or starting within hours")
        elif is_fee_deadline and is_essential_blocked:
            urgency = "CRITICAL"
            urgency_points = 35.0
            applied_rules.append(
                "RULE-URG-02: Fee/admission deadline + service blocked → urgency CRITICAL (+35 pts)"
            )
            evidence_found.append("Fee/admission deadline and payment/process blocked")
        elif is_exam_near and is_essential_blocked:
            urgency = "HIGH"
            urgency_points = 28.0
            applied_rules.append(
                "RULE-URG-03: Upcoming exam + essential service blocked → urgency HIGH (+28 pts)"
            )
            evidence_found.append("Exam approaching and required service inaccessible")
        elif is_fee_deadline:
            urgency = "HIGH"
            urgency_points = 25.0
            applied_rules.append(
                "RULE-URG-04: Fee/admission deadline approaching → urgency HIGH (+25 pts)"
            )
            evidence_found.append("Fee or admission deadline approaching")
        elif is_exam_near:
            urgency = "MEDIUM"
            urgency_points = 15.0
            applied_rules.append(
                "RULE-URG-05: Exam-related issue (not imminent) → urgency MEDIUM (+15 pts)"
            )
            evidence_found.append("Examination-related issue")
        elif is_essential_blocked and not is_minor:
            urgency = "HIGH"
            urgency_points = 20.0
            applied_rules.append(
                "RULE-URG-06: Essential process blocked (payment/submission/registration) → urgency HIGH (+20 pts)"
            )
            evidence_found.append("Essential business/academic process blocked")
        elif is_recurring:
            urgency = "MEDIUM"
            urgency_points = 12.0
            applied_rules.append(
                "RULE-URG-07: Recurring / persistent issue → urgency MEDIUM (+12 pts)"
            )
            evidence_found.append("Recurring or persistent problem")
        elif is_urgent_kw and not is_minor:
            # Urgency keyword alone does NOT guarantee HIGH
            urgency = "MEDIUM"
            urgency_points = 8.0
            applied_rules.append(
                "RULE-URG-08: Urgency keyword without substantive evidence → urgency MEDIUM (+8 pts)"
            )
        elif is_minor:
            urgency = "LOW"
            urgency_points = 0.0
            applied_rules.append(
                "RULE-URG-09: Routine / minor inquiry → urgency LOW (0 pts)"
            )
        else:
            urgency = "MEDIUM"
            urgency_points = 5.0
            applied_rules.append(
                "RULE-URG-10: Standard operational issue → urgency MEDIUM (+5 pts)"
            )

        # ── 3. Cluster / Distinct-User Boost ─────────────────────────────────
        # IMPORTANT: use distinct_affected_users, NOT cluster_size (total reports).
        # One user submitting 5 tickets still = 1 distinct user = 0 cluster boost.
        cluster_points = 0.0
        if distinct_affected_users >= 10:
            cluster_points = 15.0
            applied_rules.append(
                f"RULE-CLU-01: {distinct_affected_users} distinct affected users → cluster boost +15 pts"
            )
        elif distinct_affected_users >= 5:
            cluster_points = 10.0
            applied_rules.append(
                f"RULE-CLU-02: {distinct_affected_users} distinct affected users → cluster boost +10 pts"
            )
        elif distinct_affected_users >= 2:
            cluster_points = 5.0
            applied_rules.append(
                f"RULE-CLU-03: {distinct_affected_users} distinct affected users → cluster boost +5 pts"
            )
        # cluster_size (total_reports) alone with distinct_users=1 gives NO boost

        # ── 4. Waiting Time Aging ─────────────────────────────────────────────
        aging_points = 0.0
        if created_at:
            now_utc = datetime.now(timezone.utc)
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            hours_waiting = max(0.0, (now_utc - created_at).total_seconds() / 3600.0)
            aging_points = round(min(12.0, hours_waiting * 0.5), 2)
            if aging_points > 0:
                applied_rules.append(
                    f"RULE-AGE-01: Waiting time aging boost +{aging_points} pts ({hours_waiting:.1f} hrs)"
                )

        # ── 5. Composite Score ────────────────────────────────────────────────
        # NOTE: category weight is NOT included — it is a queue tie-breaker only.
        total_score = round(impact_points + urgency_points + cluster_points + aging_points, 2)
        total_score = max(5.0, min(100.0, total_score))

        # ── 6. Priority Classification ────────────────────────────────────────
        if total_score >= THRESHOLD_CRITICAL:
            calculated_priority = TicketPriority.CRITICAL
            sla_summary = "SLA-P1: Response < 15 min — Critical operational / ongoing disruption"
        elif total_score >= THRESHOLD_HIGH:
            calculated_priority = TicketPriority.HIGH
            sla_summary = "SLA-P2: Response < 2 hrs — Substantial disruption / deadline impact"
        elif total_score >= THRESHOLD_MEDIUM:
            calculated_priority = TicketPriority.MEDIUM
            sla_summary = "SLA-P3: Response < 4 hrs — Standard individual operational issue"
        else:
            calculated_priority = TicketPriority.LOW
            sla_summary = "SLA-P4: Response < 24 hrs — Routine / minor / no deadline"

        # ── 7. Hard Overrides ────────────────────────────────────────────────
        # Campus-wide outage with critical service down → CRITICAL unconditionally
        if is_campus_wide and is_svc_down:
            calculated_priority = TicketPriority.CRITICAL
            total_score = max(total_score, 90.0)
            applied_rules.append(
                "RULE-OVERRIDE-01: Campus-wide + critical service down → CRITICAL override"
            )

        # Exam in progress (live) → at least HIGH, or CRITICAL if service down / multi-user
        if is_exam_live:
            if is_svc_down or is_campus_wide or is_multi_user:
                calculated_priority = TicketPriority.CRITICAL
                total_score = max(total_score, 85.0)
                applied_rules.append(
                    "RULE-OVERRIDE-02: Live exam + service outage/multi-user → CRITICAL override"
                )
            else:
                if calculated_priority not in (TicketPriority.CRITICAL,):
                    calculated_priority = TicketPriority.HIGH
                    total_score = max(total_score, 65.0)
                    applied_rules.append(
                        "RULE-OVERRIDE-03: Live exam disruption (single user) → at least HIGH"
                    )

        # Fee/admission deadline + service blocked → at least HIGH
        if (is_fee_deadline or is_fee_admission_near) and is_essential_blocked:
            if calculated_priority == TicketPriority.MEDIUM:
                calculated_priority = TicketPriority.HIGH
                total_score = max(total_score, 62.0)
                applied_rules.append(
                    "RULE-OVERRIDE-04: Fee/admission deadline + service blocked → at least HIGH"
                )

        # High-stakes exam/fee deadline with active disruption/outage elevates to CRITICAL
        if (is_exam_near or is_exam_live or is_fee_deadline or is_fee_admission_near) and (is_svc_down or (is_campus_wide and is_essential_blocked)):
            calculated_priority = TicketPriority.CRITICAL
            total_score = max(total_score, 85.0)
            applied_rules.append(
                "RULE-OVERRIDE-04B: Critical academic/financial deadline with service disruption elevated to CRITICAL"
            )

        # Fee deadline + multiple users → at least HIGH
        if (is_fee_deadline or is_fee_admission_near) and is_multi_user:
            if calculated_priority in (TicketPriority.LOW, TicketPriority.MEDIUM):
                calculated_priority = TicketPriority.HIGH
                total_score = max(total_score, 60.0)
                applied_rules.append(
                    "RULE-OVERRIDE-05: Fee/admission deadline + multiple users → at least HIGH"
                )

        # Multiple users affected (and not minor inquiry) → at least HIGH
        if is_multi_user and not is_minor:
            if calculated_priority in (TicketPriority.LOW, TicketPriority.MEDIUM):
                calculated_priority = TicketPriority.HIGH
                total_score = max(total_score, 62.0)
                applied_rules.append(
                    "RULE-OVERRIDE-05B: Multiple users affected → at least HIGH"
                )

        # Prevent keyword-only escalation to CRITICAL
        if (
            is_urgent_kw
            and not is_exam_live
            and not is_exam_near
            and not is_fee_deadline
            and not is_fee_admission_near
            and not is_svc_down
            and not is_campus_wide
            and not is_multi_user
            and not is_essential_blocked
            and calculated_priority == TicketPriority.HIGH
        ):
            if impact_points <= 12.0 and urgency_points <= 8.0:
                calculated_priority = TicketPriority.MEDIUM
                applied_rules.append(
                    "RULE-OVERRIDE-06: Urgency keyword without structural evidence — capped at MEDIUM"
                )

        # Build human-readable explanation
        explanation_lines = [
            f"Calculated Priority: {calculated_priority.value} (Composite Score: {total_score:.1f}/100)",
            f"Category: {predicted_category} (used as queue tie-breaker only, not in score)",
            f"Assessed Impact: {impact} ({affected_users_est})",
            f"Assessed Urgency: {urgency}",
            f"SLA Policy: {sla_summary}",
        ]
        if cluster_points > 0:
            explanation_lines.append(
                f"Cluster/Incident Boost: +{cluster_points} pts ({distinct_affected_users} distinct affected users)"
            )
        if aging_points > 0:
            explanation_lines.append(f"Waiting Time Boost: +{aging_points} pts")
        explanation_lines.append("Applied Rules: " + "; ".join(applied_rules))
        if evidence_found:
            explanation_lines.append("Key Evidence: " + ", ".join(evidence_found))

        full_explanation = "\n".join(explanation_lines)

        return {
            "calculated_priority": calculated_priority,
            "priority": calculated_priority,
            "priority_score": total_score,
            "score": total_score,
            "impact": impact,
            "urgency": urgency,
            "explanation": full_explanation,
            "sla_rule": sla_summary,
            "applied_rules": applied_rules,
            "evidence": evidence_found,
            "signals": {
                "is_campus_wide": is_campus_wide,
                "is_svc_down": is_svc_down,
                "is_multi_user": is_multi_user,
                "is_exam_live": is_exam_live,
                "is_exam_near": is_exam_near,
                "is_fee_deadline": is_fee_deadline,
                "is_essential_blocked": is_essential_blocked,
                "is_recurring": is_recurring,
                "effective_cluster_size": distinct_affected_users,
                "impact_points": impact_points,
                "urgency_points": urgency_points,
                "cluster_points": cluster_points,
                "aging_points": aging_points,
                "total_score": total_score,
            },
        }


priority_engine = PriorityEngine()
