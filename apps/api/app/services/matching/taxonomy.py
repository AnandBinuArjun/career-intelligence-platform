from __future__ import annotations

import re

# Controlled canonical skill taxonomy with aliases/synonyms.
# Kept explicit and deterministic so matches are explainable and reproducible.
SKILL_TAXONOMY: dict[str, list[str]] = {
    # Programming Languages
    "Python": ["python", "python3", "py"],
    "TypeScript": ["typescript", "ts"],
    "JavaScript": ["javascript", "js", "ecmascript", "es6"],
    "Java": ["java", "jvm"],
    "C#": ["c#", "csharp", ".net", "dotnet"],
    "C++": ["c++", "cpp"],
    "Go": ["golang", "go lang"],
    "Rust": ["rust", "rustlang"],
    "SQL": ["sql", "t-sql", "pl/sql"],
    "Bash": ["bash", "shell scripting", "sh", "zsh"],
    "PowerShell": ["powershell", "ps1"],
    # Web & API Frameworks
    "React": ["react", "reactjs", "react.js"],
    "Next.js": ["next.js", "nextjs"],
    "Node.js": ["node.js", "nodejs"],
    "FastAPI": ["fastapi"],
    "Django": ["django"],
    "Flask": ["flask"],
    "Spring Boot": ["spring boot", "springboot"],
    "Tailwind CSS": ["tailwind", "tailwind css", "tailwindcss"],
    "GraphQL": ["graphql"],
    "REST API": ["rest api", "restful", "rest apis", "openapi", "swagger"],
    # Data & Databases
    "PostgreSQL": ["postgresql", "postgres", "psql", "pgvector"],
    "MySQL": ["mysql", "mariadb"],
    "Redis": ["redis"],
    "MongoDB": ["mongodb", "mongo"],
    "Elasticsearch": ["elasticsearch", "elastic search", "elk"],
    "Apache Kafka": ["kafka", "apache kafka"],
    "Apache Spark": ["spark", "pyspark", "apache spark"],
    "dbt": ["dbt"],
    "Power BI": ["power bi", "powerbi"],
    "Tableau": ["tableau"],
    # Cloud & DevOps
    "AWS": ["aws", "amazon web services", "ec2", "s3", "lambda"],
    "Azure": ["azure", "microsoft azure"],
    "Google Cloud": ["gcp", "google cloud", "google cloud platform"],
    "Docker": ["docker", "containers", "containerization"],
    "Kubernetes": ["kubernetes", "k8s", "helm"],
    "Terraform": ["terraform", "iac", "infrastructure as code"],
    "CI/CD": ["ci/cd", "github actions", "gitlab ci", "jenkins", "pipelines"],
    "Linux": ["linux", "ubuntu", "debian", "rhel", "linux administration"],
    "Git": ["git", "github", "gitlab"],
    "OpenTelemetry": ["opentelemetry", "otel", "prometheus", "grafana"],
    # Cybersecurity
    "SIEM": ["siem", "splunk", "microsoft sentinel", "qradar", "siem monitoring"],
    "Incident Response": ["incident response", "dfir", "ir", "threat hunting"],
    "Penetration Testing": ["penetration testing", "pentesting", "pen testing", "ethical hacking"],
    "Vulnerability Assessment": ["vulnerability assessment", "vulnerability management", "nessus", "qualys"],
    "SOC Operations": ["soc", "security operations", "security operations center", "triage"],
    "OWASP": ["owasp", "owasp top 10", "appsec", "application security"],
    "IAM": ["iam", "identity and access management", "oauth", "oidc", "sso", "rbac"],
    "ISO 27001": ["iso 27001", "iso27001", "isms"],
    "NIST": ["nist", "nist csf", "nist 800-53"],
    "GDPR": ["gdpr", "uk gdpr", "data protection", "privacy compliance"],
    "Network Security": ["network security", "firewalls", "ids/ips", "wireshark", "tcp/ip"],
    "Cloud Security": ["cloud security", "devsecops", "cspm", "zero trust"],
    # AI & Machine Learning
    "Machine Learning": ["machine learning", "ml", "scikit-learn", "sklearn"],
    "Deep Learning": ["deep learning", "pytorch", "tensorflow"],
    "NLP": ["nlp", "natural language processing", "spacy", "transformers"],
    "LLM Engineering": ["llm", "llms", "rag", "prompt engineering", "ollama", "langchain"],
    "Data Analysis": ["data analysis", "pandas", "numpy", "statistics"],
    # Delivery & Product
    "Agile": ["agile", "scrum", "kanban", "sprint planning"],
    "Product Management": ["product management", "roadmapping", "stakeholder management"],
    "Technical Writing": ["technical writing", "documentation", "rfc", "architecture docs"],
    "Automated Testing": ["pytest", "jest", "playwright", "unit testing", "integration testing", "tdd"],
}

SOFT_SKILLS: list[str] = [
    "Communication",
    "Leadership",
    "Collaboration",
    "Problem Solving",
    "Stakeholder Management",
    "Mentoring",
    "Analytical Thinking",
    "Time Management",
    "Cross-functional Collaboration",
]

CERTIFICATION_PATTERNS: dict[str, str] = {
    "CISSP": r"\bcissp\b",
    "CISM": r"\bcism\b",
    "Security+": r"\b(?:comptia\s+)?security\+\b",
    "CEH": r"\bceh\b",
    "OSCP": r"\boscp\b",
    "AWS Solutions Architect": r"\baws\s+(?:certified\s+)?solutions?\s+architect\b",
    "Azure Administrator": r"\baz-104\b|\bazure\s+administrator\b",
    "CKA": r"\bcka\b|\bcertified kubernetes administrator\b",
    "PMP": r"\bpmp\b",
    "PRINCE2": r"\bprince2\b",
    "ISO 27001 Lead Auditor": r"\biso\s*27001\s+lead\s+auditor\b",
}

# Build reverse lookup index: alias -> canonical name
_ALIAS_TO_CANONICAL: dict[str, str] = {}
for _canonical, _aliases in SKILL_TAXONOMY.items():
    _ALIAS_TO_CANONICAL[_canonical.lower()] = _canonical
    for _alias in _aliases:
        _ALIAS_TO_CANONICAL[_alias.lower()] = _canonical


def normalize_skill(raw: str) -> str:
    cleaned = raw.strip()
    if not cleaned:
        return ""
    return _ALIAS_TO_CANONICAL.get(cleaned.lower(), cleaned)


def _build_boundary_regex(term: str) -> re.Pattern[str]:
    escaped = re.escape(term)
    prefix = r"(?<![A-Za-z0-9])" if term[0].isalnum() else r"(?<!\w)"
    suffix = r"(?![A-Za-z0-9])" if term[-1].isalnum() else r"(?!\w)"
    return re.compile(f"{prefix}{escaped}{suffix}", re.IGNORECASE)


_COMPILED_SKILL_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (canonical, _build_boundary_regex(alias))
    for canonical, aliases in SKILL_TAXONOMY.items()
    for alias in aliases
]


def extract_skills_from_text(text: str) -> list[str]:
    """Deterministically extract normalized canonical skills from arbitrary text."""
    found: list[str] = []
    seen: set[str] = set()
    for canonical, pattern in _COMPILED_SKILL_PATTERNS:
        if canonical in seen:
            continue
        if pattern.search(text):
            seen.add(canonical)
            found.append(canonical)
    return found


def extract_soft_skills(text: str) -> list[str]:
    lowered = text.lower()
    return [skill for skill in SOFT_SKILLS if skill.lower() in lowered]


def extract_certifications(text: str) -> list[str]:
    return [
        name
        for name, pattern in CERTIFICATION_PATTERNS.items()
        if re.search(pattern, text, re.IGNORECASE)
    ]
