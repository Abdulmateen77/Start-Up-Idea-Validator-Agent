import { RunView, RunSummary } from "./types";

export const PRESET_SCENARIOS: Record<string, RunView> = {
  "mock-intake-loop": {
    run_id: "mock-intake-loop",
    status: "awaiting_human",
    stage: "intake",
    raw_idea: "AI assistant for boutique law firms doing patent work",
    created_at: new Date(Date.now() - 1000 * 60 * 15).toISOString(),
    updated_at: new Date(Date.now() - 1000 * 60 * 2).toISOString(),
    awaiting: {
      kind: "intake_question",
      question:
        "What specific bottleneck in patent prosecution are you targeting — prior art search, claim drafting, or office action responses?",
      turn_index: 3,
    },
    brief: null,
    intake_turns: [
      {
        role: "human",
        content: "AI assistant for boutique law firms doing patent work",
      },
      {
        role: "agent",
        content:
          "Who is the primary user inside the firm — partner attorneys, patent agents, or paralegals?",
      },
      {
        role: "human",
        content:
          "Patent agents and senior associates who spend 15+ hours a week drafting claim matrices.",
      },
      {
        role: "agent",
        content:
          "What specific bottleneck in patent prosecution are you targeting — prior art search, claim drafting, or office action responses?",
      },
    ],
    lanes: [],
    lane_progress: [],
    recommendation: null,
    human_decision: null,
    error: null,
  },

  "mock-2-lane-active": {
    run_id: "mock-2-lane-active",
    status: "running",
    stage: "research",
    raw_idea: "Open-source developer telemetry proxy for GDPR compliance",
    created_at: new Date(Date.now() - 1000 * 60 * 8).toISOString(),
    updated_at: new Date().toISOString(),
    awaiting: null,
    brief: {
      niche: "GDPR compliance infrastructure for developer tools",
      audience: "EU SaaS engineering leads and privacy engineers",
      core_question:
        "Will EU dev leads self-host an open-source telemetry proxy over configuring commercial vendor proxies?",
    },
    intake_turns: [
      {
        role: "human",
        content: "Open-source developer telemetry proxy for GDPR compliance",
      },
      {
        role: "agent",
        content: "Refined brief established with 2 focused research lanes.",
      },
    ],
    lanes: [
      {
        lane_id: "lane-pain",
        name: "Developer Pain Points & Willingness to Self-Host",
        question:
          "Do engineering teams struggle with telemetry anonymization enough to adopt self-hosted proxies?",
        archetype: "customer_pain",
      },
      {
        lane_id: "lane-comp",
        name: "Existing EU Privacy Gateway Competitors",
        question:
          "What open-source and commercial privacy gateways currently dominate PostHog/Datadog pipelines?",
        archetype: "competitors",
      },
    ],
    lane_progress: [
      {
        lane_id: "lane-pain",
        name: "Developer Pain Points & Willingness to Self-Host",
        archetype: "customer_pain",
        state: "running",
        claim_count: 4,
        no_evidence_found: false,
        had_tool_failure: false,
      },
      {
        lane_id: "lane-comp",
        name: "Existing EU Privacy Gateway Competitors",
        archetype: "competitors",
        state: "done",
        claim_count: 6,
        no_evidence_found: false,
        had_tool_failure: false,
      },
    ],
    recommendation: null,
    human_decision: null,
    error: null,
  },

  "mock-5-lane-rich": {
    run_id: "mock-5-lane-rich",
    status: "running",
    stage: "research",
    raw_idea: "B2B vertical payroll & tax automation for US ocean shipping crews",
    created_at: new Date(Date.now() - 1000 * 60 * 20).toISOString(),
    updated_at: new Date().toISOString(),
    awaiting: null,
    brief: {
      niche: "Maritime payroll & international flag-state tax withholdings",
      audience: "Fleet operations directors managing 10-100 vessel crews",
      core_question:
        "Is maritime multi-jurisdiction payroll painful enough to unseat legacy maritime ERPs?",
    },
    intake_turns: [
      {
        role: "human",
        content: "Vertical payroll for shipping crews",
      },
      {
        role: "agent",
        content: "Refined brief generated across 5 distinct research vectors.",
      },
    ],
    lanes: [
      {
        lane_id: "lane-pain",
        name: "Fleet Ops Crew Pay Pain Points",
        question: "How long does manual flag-state withholding calculation take?",
        archetype: "customer_pain",
      },
      {
        lane_id: "lane-comp",
        name: "Maritime ERP Competitors & Lock-in",
        question: "Which legacy software suites (e.g. ShipNet, BASSnet) dominate?",
        archetype: "competitors",
      },
      {
        lane_id: "lane-dist",
        name: "Maritime Ship Management Broker Distribution",
        question: "Can sales be routed through third-party ship management agencies?",
        archetype: "distribution",
      },
      {
        lane_id: "lane-reg",
        name: "MLC 2006 & International Maritime Tax Law",
        question: "What compliance certifications are legally mandated?",
        archetype: "regulatory",
      },
      {
        lane_id: "lane-econ",
        name: "Per-Vessel ACV & Margins",
        question: "Can ACVs support an inside-sales field motion ($20k+ ACV)?",
        archetype: "unit_economics",
      },
    ],
    lane_progress: [
      {
        lane_id: "lane-pain",
        name: "Fleet Ops Crew Pay Pain Points",
        archetype: "customer_pain",
        state: "done",
        claim_count: 8,
        no_evidence_found: false,
        had_tool_failure: false,
      },
      {
        lane_id: "lane-comp",
        name: "Maritime ERP Competitors & Lock-in",
        archetype: "competitors",
        state: "running",
        claim_count: 5,
        no_evidence_found: false,
        had_tool_failure: false,
      },
      {
        lane_id: "lane-dist",
        name: "Maritime Ship Management Broker Distribution",
        archetype: "distribution",
        state: "running",
        claim_count: 3,
        no_evidence_found: false,
        had_tool_failure: false,
      },
      {
        lane_id: "lane-reg",
        name: "MLC 2006 & International Maritime Tax Law",
        archetype: "regulatory",
        state: "pending",
        claim_count: 0,
        no_evidence_found: false,
        had_tool_failure: false,
      },
      {
        lane_id: "lane-econ",
        name: "Per-Vessel ACV & Margins",
        archetype: "unit_economics",
        state: "pending",
        claim_count: 0,
        no_evidence_found: false,
        had_tool_failure: false,
      },
    ],
    recommendation: null,
    human_decision: null,
    error: null,
  },

  "mock-all-other-archetypes": {
    run_id: "mock-all-other-archetypes",
    status: "running",
    stage: "research",
    raw_idea: "Decentralized micro-hydroelectric grid balancing in alpine valleys",
    created_at: new Date(Date.now() - 1000 * 60 * 12).toISOString(),
    updated_at: new Date().toISOString(),
    awaiting: null,
    brief: {
      niche: "Alpine valley micro-hydro grid load synchronization",
      audience: "Independent municipal utility cooperatives in Austria & Switzerland",
      core_question:
        "Can peer-to-peer load scheduling stabilize alpine micro-turbines during seasonal melt runoff?",
    },
    intake_turns: [
      {
        role: "human",
        content: "Decentralized micro-hydroelectric grid balancing in alpine valleys",
      },
    ],
    lanes: [
      {
        lane_id: "lane-alpine-melt",
        name: "Seasonal Runoff Flow Variability",
        question: "What flow rate swings occur during spring snowmelt?",
        archetype: "other",
      },
      {
        lane_id: "lane-turbine-physics",
        name: "Pelton Turbine Wear Dynamics",
        question: "How does rapid throttled cycling impact turbine bearing lifespan?",
        archetype: "other",
      },
      {
        lane_id: "lane-canton-rights",
        name: "Austrian / Swiss Water Rights Charters",
        question: "Do historical riparian charters allow automated diversion controls?",
        archetype: "other",
      },
    ],
    lane_progress: [
      {
        lane_id: "lane-alpine-melt",
        name: "Seasonal Runoff Flow Variability",
        archetype: "other",
        state: "done",
        claim_count: 5,
        no_evidence_found: false,
        had_tool_failure: false,
      },
      {
        lane_id: "lane-turbine-physics",
        name: "Pelton Turbine Wear Dynamics",
        archetype: "other",
        state: "running",
        claim_count: 3,
        no_evidence_found: false,
        had_tool_failure: false,
      },
      {
        lane_id: "lane-canton-rights",
        name: "Austrian / Swiss Water Rights Charters",
        archetype: "other",
        state: "pending",
        claim_count: 0,
        no_evidence_found: false,
        had_tool_failure: false,
      },
    ],
    recommendation: null,
    human_decision: null,
    error: null,
  },

  "mock-edge-evidence-and-failure": {
    run_id: "mock-edge-evidence-and-failure",
    status: "running",
    stage: "research",
    raw_idea: "Synthetic data generation for rare pediatric cardiology ultrasound",
    created_at: new Date(Date.now() - 1000 * 60 * 30).toISOString(),
    updated_at: new Date().toISOString(),
    awaiting: null,
    brief: {
      niche: "Synthetic echocardiogram training datasets for rare congenital heart defects",
      audience: "Medical imaging AI vendors and pediatric research hospitals",
      core_question:
        "Will pediatric imaging labs license synthetic echo datasets given FDA AI/ML validation guidance?",
    },
    intake_turns: [
      {
        role: "human",
        content: "Synthetic ultrasound for pediatric cardiology",
      },
    ],
    lanes: [
      {
        lane_id: "lane-fda-reg",
        name: "FDA Guidance on Synthetic Training Data for SaMD",
        question: "Does the FDA explicitly permit purely synthetic ultrasound for 510(k) clearances?",
        archetype: "regulatory",
      },
      {
        lane_id: "lane-clinical-demand",
        name: "Clinical Trial Data Acquisition Scarcity",
        question: "How many congenital defect cases are accessible per hospital per year?",
        archetype: "customer_pain",
      },
      {
        lane_id: "lane-scraper-pubmed",
        name: "PubMed Central Ultrasound Corpus Scraping",
        question: "What open access annotated ultrasound archives exist?",
        archetype: "technical_feasibility",
      },
    ],
    lane_progress: [
      {
        lane_id: "lane-fda-reg",
        name: "FDA Guidance on Synthetic Training Data for SaMD",
        archetype: "regulatory",
        state: "done",
        claim_count: 0,
        no_evidence_found: true,
        had_tool_failure: false,
      },
      {
        lane_id: "lane-clinical-demand",
        name: "Clinical Trial Data Acquisition Scarcity",
        archetype: "customer_pain",
        state: "done",
        claim_count: 4,
        no_evidence_found: false,
        had_tool_failure: false,
      },
      {
        lane_id: "lane-scraper-pubmed",
        name: "PubMed Central Ultrasound Corpus Scraping",
        archetype: "technical_feasibility",
        state: "failed",
        claim_count: 0,
        no_evidence_found: false,
        had_tool_failure: true,
      },
    ],
    recommendation: null,
    human_decision: null,
    error: null,
  },

  "mock-gate-decision-ready": {
    run_id: "mock-gate-decision-ready",
    status: "awaiting_human",
    stage: "human_gate",
    raw_idea: "AI agent for automated sales tax exemptions in B2B wholesale lumber",
    created_at: new Date(Date.now() - 1000 * 60 * 45).toISOString(),
    updated_at: new Date(Date.now() - 1000 * 60 * 1).toISOString(),
    awaiting: {
      kind: "gate_decision",
      recommendation: {
        core_question:
          "Should we build an AI certificate verification and exemption management tool specifically for US regional lumber distributors?",
        findings: [
          {
            lane_name: "Distributor Pain & Audit Exposure",
            points: [
              "Regional lumber yards (10-50M annual rev) report losing 4-6% margin on unverified resale exemption certificates caught during state audit lookbacks.",
              "Manual audit reconciliation averages 18 hours per monthly billing cycle, conducted entirely via paper binders and PDF scans (high operator error rate).",
              "Caveat: Tier 1 distributors ($100M+) already utilize Avalara CertCapture; however, sub-$30M yards cite Avalara minimum annual commitments ($15k/yr) as cost-prohibitive.",
            ],
          },
          {
            lane_name: "Competitive Landscape",
            points: [
              "Avalara and Vertex dominate enterprise ERP integrations (SAP, NetSuite) but offer minimal out-of-the-box workflows for legacy lumber point-of-sale systems (BisTrack, Spruce).",
              "No dedicated player currently provides automated optical certificate verification paired with contractor license active-status checks in real-time.",
            ],
          },
          {
            lane_name: "Distribution Channels",
            points: [
              "North American Wholesale Lumber Association (NAWLA) trade events and BisTrack developer marketplace serve as direct low-CAC acquisition channels.",
              "Caveat: BisTrack API access requires vendor certification approval, which has historically taken 3-6 months for early-stage software partners.",
            ],
          },
        ],
        gaps: [
          "State-by-state electronic signature recognition statutes for wholesale agricultural/timber exemptions need legal confirmation in GA, NC, and OR.",
          "Willingness to switch away from manual paper filing among multi-generational yard managers has not been quantitatively benchmarked.",
        ],
        verdict:
          "Proceed with targeted prototype validation: strong niche pain and defensible integration wedge into legacy ERPs, contingent on clearing BisTrack partner integration timeline.",
      },
      next_moves: [
        {
          move_id: "customer_interviews",
          label: "Run 5 Customer Interviews",
          rationale:
            "Interview 5 BisTrack-powered lumber yard controllers to validate certificate audit frequency and budget tolerance.",
        },
        {
          move_id: "bistrack_sandbox",
          label: "Apply for BisTrack API Sandbox",
          rationale:
            "Submit vendor partnership application to Epicor/BisTrack to determine API feasibility and sandbox lead time.",
        },
        {
          move_id: "manual_concierge",
          label: "Run Concierge Audit Test",
          rationale:
            "Manually audit 50 sample certificates for a friendly pilot distributor to establish baseline OCR error rate.",
        },
        {
          move_id: "pass_pivot",
          label: "Pass on Niche / Pivot to Construction Subcontractors",
          rationale:
            "Pivot focus if lumber POS integration friction is deemed too high for an early MVP.",
        },
      ],
    },
    brief: {
      niche: "Wholesale lumber and building materials sales tax certificate compliance",
      audience: "CFOs and controllers of regional lumber distributors using BisTrack/Spruce",
      core_question:
        "Should we build an AI certificate verification and exemption management tool specifically for US regional lumber distributors?",
    },
    intake_turns: [
      {
        role: "human",
        content: "AI agent for automated sales tax exemptions in B2B wholesale lumber",
      },
      {
        role: "agent",
        content:
          "Confirmed target: US regional lumber distributors on legacy POS platforms.",
      },
    ],
    lanes: [
      {
        lane_id: "dist-pain",
        name: "Distributor Pain & Audit Exposure",
        question: "What financial penalties do distributors face from expired resale certificates?",
        archetype: "customer_pain",
      },
      {
        lane_id: "comp-land",
        name: "Competitive Landscape",
        question: "How well do Avalara and Vertex serve BisTrack/Spruce POS systems?",
        archetype: "competitors",
      },
      {
        lane_id: "dist-chan",
        name: "Distribution Channels",
        question: "Can we acquire lumber yard customers via NAWLA and POS integrations?",
        archetype: "distribution",
      },
    ],
    lane_progress: [
      {
        lane_id: "dist-pain",
        name: "Distributor Pain & Audit Exposure",
        archetype: "customer_pain",
        state: "done",
        claim_count: 5,
        no_evidence_found: false,
        had_tool_failure: false,
      },
      {
        lane_id: "comp-land",
        name: "Competitive Landscape",
        archetype: "competitors",
        state: "done",
        claim_count: 4,
        no_evidence_found: false,
        had_tool_failure: false,
      },
      {
        lane_id: "dist-chan",
        name: "Distribution Channels",
        archetype: "distribution",
        state: "done",
        claim_count: 3,
        no_evidence_found: false,
        had_tool_failure: false,
      },
    ],
    recommendation: {
      core_question:
        "Should we build an AI certificate verification and exemption management tool specifically for US regional lumber distributors?",
      findings: [
        {
          lane_name: "Distributor Pain & Audit Exposure",
          points: [
            "Regional lumber yards (10-50M annual rev) report losing 4-6% margin on unverified resale exemption certificates caught during state audit lookbacks.",
            "Manual audit reconciliation averages 18 hours per monthly billing cycle, conducted entirely via paper binders and PDF scans (high operator error rate).",
            "Caveat: Tier 1 distributors ($100M+) already utilize Avalara CertCapture; however, sub-$30M yards cite Avalara minimum annual commitments ($15k/yr) as cost-prohibitive.",
          ],
        },
        {
          lane_name: "Competitive Landscape",
          points: [
            "Avalara and Vertex dominate enterprise ERP integrations (SAP, NetSuite) but offer minimal out-of-the-box workflows for legacy lumber point-of-sale systems (BisTrack, Spruce).",
            "No dedicated player currently provides automated optical certificate verification paired with contractor license active-status checks in real-time.",
          ],
        },
        {
          lane_name: "Distribution Channels",
          points: [
            "North American Wholesale Lumber Association (NAWLA) trade events and BisTrack developer marketplace serve as direct low-CAC acquisition channels.",
            "Caveat: BisTrack API access requires vendor certification approval, which has historically taken 3-6 months for early-stage software partners.",
          ],
        },
      ],
      gaps: [
        "State-by-state electronic signature recognition statutes for wholesale agricultural/timber exemptions need legal confirmation in GA, NC, and OR.",
        "Willingness to switch away from manual paper filing among multi-generational yard managers has not been quantitatively benchmarked.",
      ],
      verdict:
        "Proceed with targeted prototype validation: strong niche pain and defensible integration wedge into legacy ERPs, contingent on clearing BisTrack partner integration timeline.",
    },
    human_decision: null,
    error: null,
  },

  "mock-gate-not-enough-evidence": {
    run_id: "mock-gate-not-enough-evidence",
    status: "awaiting_human",
    stage: "human_gate",
    raw_idea: "Sub-orbital hypersonic cargo delivery dispatch for biological organs",
    created_at: new Date(Date.now() - 1000 * 60 * 60).toISOString(),
    updated_at: new Date(Date.now() - 1000 * 60 * 5).toISOString(),
    awaiting: {
      kind: "gate_decision",
      recommendation: {
        core_question:
          "Is commercial hypersonic flight viable for human organ transplant transport within a 3-year horizon?",
        findings: [
          {
            lane_name: "FAA / UNOS Airspace Regulation",
            points: [
              "Current FAA Part 450 regulations lack streamlined commercial launch/reentry corridors for unmanned cargo over continental populated zones.",
              "Caveat: United Network for Organ Sharing (UNOS) logistics protocol requires guaranteed cold-ischemia tracking that spaceport ground turnaround cannot yet meet.",
            ],
          },
        ],
        gaps: [
          "Zero publicly published flight test telemetry on vibration and g-force impact on perfused cardiac tissue.",
          "Sub-orbital launch provider pricing models remain classified or speculative ($500k+ per flight minimum).",
        ],
        verdict:
          "Not enough evidence yet: regulatory flight corridor frameworks and organ cold-chain telemetry are currently insufficient to justify product buildout.",
      },
      next_moves: [
        {
          move_id: "track_faa_part450",
          label: "Set Up Regulatory Watchdog",
          rationale: "Monitor FAA Commercial Space Transportation rulemaking docket for cargo waivers.",
        },
        {
          move_id: "pivot_evtol",
          label: "Pivot to Regional eVTOL Organ Transport",
          rationale: "Investigate 50-200 mile helicopter replacement routes using certified eVTOL aircraft.",
        },
        {
          move_id: "close_study",
          label: "Shelve Research",
          rationale: "Archive hypothesis until point-to-point sub-orbital cadence reaches commercial maturity.",
        },
      ],
    },
    brief: {
      niche: "Point-to-point sub-orbital organ logistics",
      audience: "Transplant surgical teams and UNOS regional procurement coordinators",
      core_question:
        "Is commercial hypersonic flight viable for human organ transplant transport within a 3-year horizon?",
    },
    intake_turns: [
      {
        role: "human",
        content: "Hypersonic organ delivery",
      },
    ],
    lanes: [
      {
        lane_id: "reg-airspace",
        name: "FAA / UNOS Airspace Regulation",
        question: "Can cargo rockets get point-to-point continental FAA flight clearance?",
        archetype: "regulatory",
      },
    ],
    lane_progress: [
      {
        lane_id: "reg-airspace",
        name: "FAA / UNOS Airspace Regulation",
        archetype: "regulatory",
        state: "done",
        claim_count: 2,
        no_evidence_found: false,
        had_tool_failure: false,
      },
    ],
    recommendation: {
      core_question:
        "Is commercial hypersonic flight viable for human organ transplant transport within a 3-year horizon?",
      findings: [
        {
          lane_name: "FAA / UNOS Airspace Regulation",
          points: [
            "Current FAA Part 450 regulations lack streamlined commercial launch/reentry corridors for unmanned cargo over continental populated zones.",
            "Caveat: United Network for Organ Sharing (UNOS) logistics protocol requires guaranteed cold-ischemia tracking that spaceport ground turnaround cannot yet meet.",
          ],
        },
      ],
      gaps: [
        "Zero publicly published flight test telemetry on vibration and g-force impact on perfused cardiac tissue.",
        "Sub-orbital launch provider pricing models remain classified or speculative ($500k+ per flight minimum).",
      ],
      verdict:
        "Not enough evidence yet: regulatory flight corridor frameworks and organ cold-chain telemetry are currently insufficient to justify product buildout.",
    },
    human_decision: null,
    error: null,
  },

  "mock-run-failed": {
    run_id: "mock-run-failed",
    status: "failed",
    stage: "failed",
    raw_idea: "Automated reverse-engineering of legacy COBOL banking mainframes via AST extraction",
    created_at: new Date(Date.now() - 1000 * 60 * 90).toISOString(),
    updated_at: new Date(Date.now() - 1000 * 60 * 80).toISOString(),
    awaiting: null,
    brief: {
      niche: "COBOL-74 to modern Java microservices AST transpilation",
      audience: "Enterprise modernization directors at regional savings banks",
      core_question:
        "Can automated AST transformation accurately preserve CICS transaction semantics?",
    },
    intake_turns: [
      {
        role: "human",
        content: "COBOL banking mainframes reverse engineering",
      },
    ],
    lanes: [
      {
        lane_id: "lane-cics-parsing",
        name: "CICS Transaction Grammar Coverage",
        question: "Can open-source COBOL parsers handle proprietary IBM EXEC CICS macros?",
        archetype: "technical_feasibility",
      },
    ],
    lane_progress: [
      {
        lane_id: "lane-cics-parsing",
        name: "CICS Transaction Grammar Coverage",
        archetype: "technical_feasibility",
        state: "failed",
        claim_count: 0,
        no_evidence_found: false,
        had_tool_failure: true,
      },
    ],
    recommendation: null,
    human_decision: null,
    error:
      "Firecrawl upstream rate limit exceeded (429 Too Many Requests) and fallback AST scraper failed with segmentation fault on malformed IBM Enterprise COBOL test fixture.",
  },

  "mock-run-completed-decision": {
    run_id: "mock-run-completed-decision",
    status: "done",
    stage: "done",
    raw_idea: "AI-assisted drafting of clinical trial patient recruitment consent forms",
    created_at: new Date(Date.now() - 1000 * 60 * 180).toISOString(),
    updated_at: new Date(Date.now() - 1000 * 60 * 120).toISOString(),
    awaiting: null,
    brief: {
      niche: "Pediatric oncology clinical trial informed consent comprehension",
      audience: "Clinical Research Coordinators (CRCs) and IRB administrators",
      core_question:
        "Do CRCs adopt AI-simplified consent language tools without risking IRB protocol rejections?",
    },
    intake_turns: [
      {
        role: "human",
        content: "AI clinical trial consent form drafting",
      },
      {
        role: "agent",
        content: "Brief validated. Pipeline executed to completion.",
      },
    ],
    lanes: [
      {
        lane_id: "lane-irb",
        name: "IRB Approval Turnaround",
        question: "Do IRBs accept simplified reading level translations?",
        archetype: "regulatory",
      },
      {
        lane_id: "lane-crc-speed",
        name: "CRC Drafting Hours Saved",
        question: "How many hours per protocol amendment are spent rewriting consent text?",
        archetype: "customer_pain",
      },
    ],
    lane_progress: [
      {
        lane_id: "lane-irb",
        name: "IRB Approval Turnaround",
        archetype: "regulatory",
        state: "done",
        claim_count: 6,
        no_evidence_found: false,
        had_tool_failure: false,
      },
      {
        lane_id: "lane-crc-speed",
        name: "CRC Drafting Hours Saved",
        archetype: "customer_pain",
        state: "done",
        claim_count: 5,
        no_evidence_found: false,
        had_tool_failure: false,
      },
    ],
    recommendation: {
      core_question:
        "Do CRCs adopt AI-simplified consent language tools without risking IRB protocol rejections?",
      findings: [
        {
          lane_name: "IRB Approval Turnaround",
          points: [
            "Central IRBs (WCG, Advarra) strongly favor 6th-8th grade reading level simplifications when accompanied by standard risk disclosure fidelity checks.",
            "Protocol revisions due to consent form comprehension issues cause a median delay of 22 calendar days in patient accrual.",
          ],
        },
      ],
      gaps: [
        "Multi-language translation requirements (Spanish, Mandarin) must be certified by human medical translators per FDA guidelines.",
      ],
      verdict:
        "Proceed: high willingness to pay from pharma sponsors seeking accelerated trial recruitment velocity.",
    },
    human_decision: {
      chosen_move_id: "customer_interviews",
      custom_note: "Scheduled interviews with 3 CRCs at Memorial Sloan Kettering",
      rerun_lane_id: null,
    },
    error: null,
  },
};

export function createNewMockRun(raw_idea: string): RunView {
  const id = `run-${Date.now().toString(36)}-${Math.random().toString(36).substring(2, 6)}`;
  return {
    run_id: id,
    status: "awaiting_human",
    stage: "intake",
    raw_idea,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    awaiting: {
      kind: "intake_question",
      question: `Thanks for sharing this idea! To narrow this down into a testable validation plan: Who is the exact initial target audience or customer persona for "${raw_idea.trim()}"?`,
      turn_index: 1,
    },
    brief: null,
    intake_turns: [
      {
        role: "human",
        content: raw_idea,
      },
      {
        role: "agent",
        content: `Thanks for sharing this idea! To narrow this down into a testable validation plan: Who is the exact initial target audience or customer persona for "${raw_idea.trim()}"?`,
      },
    ],
    lanes: [],
    lane_progress: [],
    recommendation: null,
    human_decision: null,
    error: null,
  };
}

export function toRunSummary(run: RunView): RunSummary {
  return {
    run_id: run.run_id,
    status: run.status,
    stage: run.stage,
    raw_idea: run.raw_idea,
    created_at: run.created_at,
    updated_at: run.updated_at,
  };
}
