RESUME_PROFILE_PROMPT = """
You are extracting structured information from a candidate resume.

Extract only information explicitly present in the resume.

Do not invent:
- skills
- education
- experience
- projects
- achievements

If information is not present, return an empty value.

Return valid JSON with exactly these fields:
summary
skills
education
experience
projects

Resume:
{resume_text}
"""


JOB_BLUEPRINT_PROMPT = """
You are extracting a structured job blueprint from an employer's job description.

Extract only requirements explicitly stated by the employer.

Return:
- role
- mandatory_criteria
- optional_criteria
- skills
- experience_requirements
- education_requirements

Do not invent requirements.

Job description:
{job_description}
"""


SYLLABUS_PROMPT = """
Create a structured interview syllabus from the job information below.

The syllabus must cover the important competencies and topics required
for this job.

Use only information supported by the job description and job blueprint.
Do not invent unrelated requirements.

For each syllabus item return:
- competency
- topic
- weight

Job title:
{title}

Job description:
{description}

Job blueprint:
{blueprint}
"""


JD_GENERATION_PROMPT = """
Create a final job description using ONLY the employer-confirmed
job blueprint and the generated interview syllabus.

Do not invent requirements.

Return:
- summary
- responsibilities
- must_have_criteria
- good_to_have_criteria
- experience
- hiring_process

The final job description must remain consistent with the
confirmed blueprint and syllabus.

Job title:
{title}

Confirmed Job Blueprint:
{blueprint}

Syllabus:
{syllabus}
"""


QUESTION_BANK_PROMPT = """
Create a structured interview question bank from the job syllabus.

Questions must test the competencies and topics in the syllabus.

Rules:
- Do not create questions unrelated to the job.
- Cover the syllabus competencies.
- Each question must have a competency.
- Set difficulty to easy, medium, or hard.
- Questions should be suitable for a structured technical/professional interview.

Job title:
{title}

Job description:
{description}

Syllabus:
{syllabus}
"""