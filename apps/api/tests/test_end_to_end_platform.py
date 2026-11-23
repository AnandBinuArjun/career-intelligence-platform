import io
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import settings
from app.services.ai.evidence import build_candidate_evidence_corpus, validate_recommendation_claim
from app.services.matching.job_parser import parse_job_description
from app.services.matching.scorer import evaluate_compatibility

SAMPLE_CV_TXT = b"""Alex Morgan
Cybersecurity Analyst
alex@example.com | +44 7700 900123

Summary
Security analyst focused on incident response, SIEM monitoring, vulnerability assessment, and Linux hardening.

Skills
Python, SIEM, Incident Response, Linux, Vulnerability Assessment, OWASP, Docker

Experience
Security Analyst | Northstar Defence | 2022 - Present
- Investigated 140+ security alerts per week using Splunk SIEM and reduced false positives by 32%.
- Led vulnerability assessments across 45 Linux servers and coordinated remediation with engineering.
- Automated incident triage playbooks in Python, cutting mean time to respond by 40%.

Education
BSc Computer Science | University of Bristol | 2018 - 2021

Certifications
CompTIA Security+
"""

SAMPLE_JD = """
We are hiring a Cybersecurity Analyst to defend our cloud and enterprise infrastructure.

Responsibilities:
- Monitor and triage security alerts in SIEM platforms
- Conduct regular vulnerability assessments and coordinate remediation
- Automate incident response workflows using Python on Linux systems

Required:
- 2+ years of experience in Cybersecurity or SOC Operations
- Hands-on experience with SIEM, Incident Response, Python, and Linux
- Knowledge of OWASP and Vulnerability Assessment

Preferred:
- Experience with Kubernetes and Terraform
- CompTIA Security+ or CISSP certification
"""


def _register_and_login(client: TestClient, email: str, password: str = "StrongPassword!1234") -> dict[str, str]:
    reg = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Test User"},
    )
    assert reg.status_code == 201, reg.text
    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200, login.text
    data = login.json()
    return {"Authorization": f"Bearer {data['access_token']}"}


def test_health_and_security_headers(client: TestClient):
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"
    assert res.headers["X-Content-Type-Options"] == "nosniff"
    assert res.headers["X-Frame-Options"] == "DENY"
    assert "X-Request-ID" in res.headers

    ready = client.get("/api/v1/health/ready")
    assert ready.status_code == 200
    assert ready.json()["checks"]["database"] == "ok"


def test_auth_lifecycle_and_cookie_csrf(client: TestClient):
    headers = _register_and_login(client, "alice@example.com")
    me = client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["email"] == "alice@example.com"

    # Bad password rejected with generic 401
    bad = client.post("/api/v1/auth/login", json={"email": "alice@example.com", "password": "wrong"})
    assert bad.status_code == 401
    unknown = client.post("/api/v1/auth/login", json={"email": "nobody@example.com", "password": "wrong"})
    assert unknown.status_code == 401
    assert bad.json()["detail"] == unknown.json()["detail"]

    # Cookie-based state-changing request without CSRF header must fail with 403
    login_res = client.post("/api/v1/auth/login", json={"email": "alice@example.com", "password": "StrongPassword!1234"})
    assert login_res.status_code == 200
    csrf_denied = client.post("/api/v1/jobs", json={"job_title": "Test", "description": "A" * 30})
    assert csrf_denied.status_code == 403


def test_full_platform_workflow_and_cross_user_isolation(client: TestClient):
    headers_a = _register_and_login(client, "user_a@example.com")
    headers_b = _register_and_login(client, "user_b@example.com")

    # 1. Verified Candidate Profile CRUD
    prof_up = client.put(
        "/api/v1/profile",
        headers=headers_a,
        json={
            "full_name": "Alex Morgan",
            "professional_title": "Cybersecurity Analyst",
            "summary": "Defensive security engineer.",
            "location": "London, UK",
            "target_roles": ["Cybersecurity Analyst", "SOC Engineer"],
            "years_experience": 3.5,
        },
    )
    assert prof_up.status_code == 200
    assert prof_up.json()["full_name"] == "Alex Morgan"

    skill_res = client.post("/api/v1/profile/skills", headers=headers_a, json={"name": "SIEM", "proficiency": "Advanced"})
    assert skill_res.status_code == 201
    exp_res = client.post(
        "/api/v1/profile/experiences",
        headers=headers_a,
        json={"job_title": "Security Analyst", "employer": "Northstar Defence"},
    )
    assert exp_res.status_code == 201

    # 2. Resume Upload, Parsing, Versioning, Restore & Clean Exports (PDF + DOCX)
    upload = client.post(
        "/api/v1/resumes/upload",
        headers=headers_a,
        data={"title": "Alex Cyber CV", "auto_parse": "true"},
        files={"file": ("alex_cv.txt", SAMPLE_CV_TXT, "text/plain")},
    )
    assert upload.status_code == 201, upload.text
    resume_data = upload.json()
    resume_id = resume_data["id"]
    version_id = resume_data["latest_version_id"]
    assert resume_data["parse_status"] == "completed"
    assert "SIEM" in resume_data["parsed_content"]["skills"]

    # Reject spoofed extension/content
    bad_upload = client.post(
        "/api/v1/resumes/upload",
        headers=headers_a,
        data={"title": "Malicious"},
        files={"file": ("fake.pdf", b"not-a-pdf", "application/pdf")},
    )
    assert bad_upload.status_code == 415

    # Export PDF and DOCX without errors and with valid magic bytes
    pdf_exp = client.get(f"/api/v1/resumes/{resume_id}/export?format=pdf&template=modern", headers=headers_a)
    assert pdf_exp.status_code == 200
    assert pdf_exp.content.startswith(b"%PDF-")

    docx_exp = client.get(f"/api/v1/resumes/{resume_id}/export?format=docx", headers=headers_a)
    assert docx_exp.status_code == 200
    with zipfile.ZipFile(io.BytesIO(docx_exp.content)) as zf:
        assert "word/document.xml" in zf.namelist()

    # 3. Job Intelligence Extraction + Editable Requirements
    job_res = client.post(
        "/api/v1/jobs",
        headers=headers_a,
        json={"company_name": "Acme Sec", "job_title": "Cybersecurity Analyst", "description": SAMPLE_JD},
    )
    assert job_res.status_code == 201
    job = job_res.json()
    job_id = job["id"]
    assert "SIEM" in job["extracted_requirements"]["required_skills"]
    assert "Kubernetes" in job["extracted_requirements"]["preferred_skills"]

    # 4. Deterministic ATS Compatibility Analysis & Reproducibility
    an1 = client.post(
        "/api/v1/analyses",
        headers=headers_a,
        json={"resume_version_id": version_id, "job_description_id": job_id},
    )
    assert an1.status_code == 201, an1.text
    analysis = an1.json()
    assert analysis["overall_score"] >= 70
    assert "not a proprietary ATS vendor score" in analysis["methodology_note"]
    assert len(analysis["scoring_data"]["dimensions"]) >= 8

    # Identical inputs -> exact same deterministic score
    an2 = client.post(
        "/api/v1/analyses",
        headers=headers_a,
        json={"resume_version_id": version_id, "job_description_id": job_id},
    )
    assert an2.status_code == 201
    assert an2.json()["overall_score"] == analysis["overall_score"]

    # Accept a recommendation
    if analysis["recommendations"]:
        rec_id = analysis["recommendations"][0]["id"]
        patch_rec = client.patch(
            f"/api/v1/analyses/{analysis['id']}/recommendations/{rec_id}",
            headers=headers_a,
            json={"status": "accepted"},
        )
        assert patch_rec.status_code == 200
        assert patch_rec.json()["status"] == "accepted"

    # External AI must be blocked when disabled/without consent
    ext_blocked = client.post(
        "/api/v1/analyses",
        headers=headers_a,
        json={
            "resume_version_id": version_id,
            "job_description_id": job_id,
            "external_ai_consent_id": "00000000-0000-0000-0000-000000000001",
        },
    )
    assert ext_blocked.status_code == 403

    # 5. Cover Letter Studio (Generate, Edit, Export)
    cl_res = client.post(
        "/api/v1/cover-letters/generate",
        headers=headers_a,
        json={
            "job_description_id": job_id,
            "resume_version_id": version_id,
            "tone": "professional",
            "length": "medium",
        },
    )
    assert cl_res.status_code == 201
    letter = cl_res.json()
    assert "Acme Sec" in letter["content"]
    assert len(letter["evidence_references"]) >= 1

    cl_pdf = client.get(f"/api/v1/cover-letters/{letter['id']}/export?format=pdf", headers=headers_a)
    assert cl_pdf.status_code == 200
    assert cl_pdf.content.startswith(b"%PDF-")

    # 6. Career Development
    career = client.get("/api/v1/career/overview", headers=headers_a)
    assert career.status_code == 200
    assert career.json()["analyzed_jobs_count"] >= 2
    assert len(career.json()["interview_questions"]) >= 1

    # 7. Application Tracker + Interviews
    app_res = client.post(
        "/api/v1/applications",
        headers=headers_a,
        json={
            "company_name": "Acme Sec",
            "position": "Cybersecurity Analyst",
            "job_description_id": job_id,
            "resume_version_id": version_id,
            "status": "applied",
        },
    )
    assert app_res.status_code == 201
    app_id = app_res.json()["id"]
    iv_res = client.post(
        f"/api/v1/applications/{app_id}/interviews",
        headers=headers_a,
        json={"interview_type": "Technical Screen", "notes": "SIEM scenarios"},
    )
    assert iv_res.status_code == 201

    # 8. Cross-User Authorization Boundary (BOLA) — User B MUST NOT access any of User A's records
    assert client.get(f"/api/v1/resumes/{resume_id}", headers=headers_b).status_code == 404
    assert client.delete(f"/api/v1/resumes/{resume_id}", headers=headers_b).status_code == 404
    assert client.get(f"/api/v1/jobs/{job_id}", headers=headers_b).status_code == 404
    assert client.get(f"/api/v1/analyses/{analysis['id']}", headers=headers_b).status_code == 404
    assert client.get(f"/api/v1/cover-letters/{letter['id']}", headers=headers_b).status_code == 404
    assert client.get(f"/api/v1/applications/{app_id}", headers=headers_b).status_code == 404

    # 9. Dashboard Summary + Privacy Consent + GDPR Export + Verified Account/File Deletion
    dash = client.get("/api/v1/dashboard/summary", headers=headers_a)
    assert dash.status_code == 200
    assert dash.json()["resumes_count"] == 1
    assert dash.json()["active_applications_count"] == 1

    consent = client.post(
        "/api/v1/privacy/consents",
        headers=headers_a,
        json={"purpose": "external_ai_processing", "provider": "none", "granted": False},
    )
    assert consent.status_code == 201

    exported = client.get("/api/v1/account/export", headers=headers_a)
    assert exported.status_code == 200
    assert exported.json()["account"]["email"] == "user_a@example.com"
    assert len(exported.json()["resumes"]) == 1

    # Confirm private storage file exists before account deletion, and is removed after deletion.
    stored_files_before = list(Path(settings.local_storage_dir).rglob("*"))
    assert any(p.is_file() for p in stored_files_before)

    del_acc = client.delete("/api/v1/account", headers=headers_a)
    assert del_acc.status_code == 204
    assert client.get("/api/v1/auth/me", headers=headers_a).status_code == 401
    stored_files_after = [p for p in Path(settings.local_storage_dir).rglob("*") if p.is_file()]
    assert len(stored_files_after) == 0


def test_evidence_validator_catches_hallucinated_claims():
    resume_content = {
        "summary": "Python backend developer using PostgreSQL and Docker.",
        "skills": ["Python", "PostgreSQL", "Docker"],
        "experiences": [{"job_title": "Engineer", "bullets": ["Built REST APIs with FastAPI."]}],
    }
    corpus, evidenced_skills, _ = build_candidate_evidence_corpus(resume_content)

    # Supported claim passes without confirmation flag
    req_confirm_ok, unverified_ok = validate_recommendation_claim(
        "Highlight your Python and PostgreSQL API work.", corpus, evidenced_skills
    )
    assert not req_confirm_ok
    assert unverified_ok == []

    # Fabricated skill (Kubernetes) and fabricated metric (95%) must be flagged
    req_confirm_bad, unverified_bad = validate_recommendation_claim(
        "Led Kubernetes clusters and reduced downtime by 95%.", corpus, evidenced_skills
    )
    assert req_confirm_bad is True
    assert "skill:Kubernetes" in unverified_bad
    assert "metric:95%" in unverified_bad


def test_mandatory_requirement_cap_prevents_keyword_stuffing():
    jd = parse_job_description(
        "Kubernetes Security Engineer",
        "Required: Kubernetes, Terraform, AWS, SIEM, Incident Response, Go",
    )
    thin_resume = {
        "summary": "Motivated team player looking for opportunities.",
        "skills": ["Python"],
        "experiences": [{"job_title": "Intern", "bullets": ["Assisted team with documentation."]}],
        "education": [{"institution": "State University", "qualification": "BSc"}],
    }
    result = evaluate_compatibility(thin_resume, jd, "Kubernetes Terraform AWS SIEM Incident Response Go")
    assert result["overall_score"] <= 62.0
