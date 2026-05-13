def load_report_module(testcase):
    try:
        from scripts import report
    except ImportError as exc:
        testcase.fail(f"scripts.report should exist: {exc}")
    return report


def sample_messages():
    return [
        {
            "id": 1,
            "channel": "React Job",
            "date": "2026-05-06T08:00:00+00:00",
            "text": "Senior React Developer at ООО Исходный код remote hr@codesrc.ru",
        },
        {
            "id": 2,
            "channel": "JavaScript Job",
            "date": "2026-05-06T08:05:00+00:00",
            "text": "Senior React Developer - Source Code LLC remote hr@codesrc.ru",
        },
        {
            "id": 3,
            "channel": "TypeScript Job Offers",
            "date": "2026-05-06T08:10:00+00:00",
            "text": "Positive Technologies frontend TypeScript React",
        },
        {
            "id": 4,
            "channel": "IT Jobs",
            "date": "2026-05-06T08:15:00+00:00",
            "text": "Sber frontend Moscow hybrid",
        },
        {
            "id": 5,
            "channel": "Backend Jobs",
            "date": "2026-05-06T08:20:00+00:00",
            "text": "Python backend role",
        },
    ]


def sample_extracted_jobs():
    return [
        {
            "source_message_ids": [1],
            "company": "ООО Исходный код",
            "role": "Senior React Developer",
            "location": "Remote",
            "salary": "Not specified",
            "contact": "hr@codesrc.ru",
            "source": "React Job",
            "rating": "high",
            "why": "React, Redux, TypeScript and Next.js match the profile.",
            "stack": ["React", "Redux", "TypeScript", "Next.js"],
            "concerns": ["Docker experience should be addressed"],
            "action": "Apply",
        },
        {
            "source_message_ids": [2],
            "company": "ООО Исходный код",
            "role": "Senior React Developer",
            "location": "Remote",
            "salary": "Not specified",
            "contact": "hr@codesrc.ru",
            "source": "JavaScript Job",
            "rating": "high",
            "why": "Duplicate posting of the same role.",
            "stack": ["React", "TypeScript"],
            "concerns": [],
            "action": "Apply",
        },
        {
            "source_message_ids": [3],
            "company": "Positive Technologies",
            "role": "Frontend Developer (TypeScript/React)",
            "location": "Unknown",
            "salary": "Not specified",
            "contact": "",
            "source": "TypeScript Job Offers",
            "rating": "medium",
            "why": "Title matches but details are missing.",
            "stack": ["TypeScript", "React"],
            "concerns": ["Search full JD before applying"],
            "action": "Inspect",
        },
        {
            "source_message_ids": [4],
            "company": "Сбер",
            "role": "Frontend Developer",
            "location": "Moscow hybrid",
            "salary": "Not specified",
            "contact": "https://rabota.sber.ru/search/frontend-developer-4524726/",
            "source": "IT Jobs",
            "rating": "low",
            "why": "Frontend match, but location is not remote-first.",
            "stack": ["Frontend"],
            "concerns": ["Russia office/hybrid conflicts with profile"],
            "action": "Skip unless location criteria change",
        },
    ]
