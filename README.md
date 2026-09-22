# AI Recruitment Platform

## Overview

AI Recruitment Platform is a web application that helps employers and candidates through different stages of the recruitment process.

The project uses FastAPI, PostgreSQL, SQLAlchemy, JWT authentication, and Gemini AI.

## Main Features

### 1. Authentication
- Candidate and employer registration
- Login and logout
- JWT-based authentication
- Role-based access

### 2. Candidate Onboarding
- Candidate can upload a resume
- Supports PDF and DOCX files
- Resume information is extracted using AI
- Candidate can review and confirm the extracted profile

### 3. Job Intelligence
- Employer can create a job
- AI generates a job blueprint
- Employer can review the job requirements
- Interview syllabus and questions are generated using AI
- Employer can publish the job

### 4. Candidate Matching
- Candidates can apply for published jobs
- Candidate profile is checked against job requirements
- Mandatory criteria are evaluated
- Only matched candidates can continue to the interview

### 5. Structured AI Interview
- Candidates receive interview questions
- Answers are evaluated using AI
- Evaluation includes demonstrated concepts, missing concepts, evidence, rubric level, and feedback
- A final interview report is generated

## Technologies Used

- Python
- FastAPI
- PostgreSQL
- SQLAlchemy
- Alembic
- Pydantic
- JWT Authentication
- Argon2 Password Hashing
- Google Gemini AI
- PyMuPDF
- python-docx

## Project Structure

```text
app/
├── core/
├── db/
├── ai/
├── modules/
│   ├── auth/
│   ├── onboarding/
│   ├── jobs/
│   ├── matching/
│   └── interviews/
└── services/

tests/
uploads/

Project Flow


User Registration
       ↓
Candidate / Employer Onboarding
       ↓
Employer Creates Job
       ↓
AI Job Blueprint
       ↓
Job Syllabus & Questions
       ↓
Job Published
       ↓
Candidate Applies
       ↓
Matching
       ↓
MATCHED
       ↓
Structured AI Interview
       ↓
Interview Evaluation
       ↓
Final Interview Report