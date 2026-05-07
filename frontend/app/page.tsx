'use client';

import { useState, type FormEvent } from 'react';
import { useRouter } from 'next/navigation';
import { useChatContext } from '@/contexts/ChatContext';
import type { QuestionnaireData } from '@/lib/session';

const ACADEMIC_YEARS: QuestionnaireData['academic_year'][] = [
  'Freshman',
  'Sophomore',
  'Junior',
  'Senior',
  'Graduate',
];

const ADVISING_TOPICS: QuestionnaireData['advising_topic'][] = [
  'Course Planning',
  'Degree Requirements',
  'Academic Standing',
  'General Advising',
];

interface FormErrors {
  academic_year?: string;
  major?: string;
  advising_topic?: string;
}

export default function QuestionnairePage() {
  const router = useRouter();
  const { setQuestionnaireData } = useChatContext();

  const [academicYear, setAcademicYear] = useState<string>('');
  const [major, setMajor] = useState<string>('');
  const [advisingTopic, setAdvisingTopic] = useState<string>('');
  const [errors, setErrors] = useState<FormErrors>({});
  const [submitted, setSubmitted] = useState(false);

  function validate(): FormErrors {
    const newErrors: FormErrors = {};

    if (!academicYear) {
      newErrors.academic_year = 'Academic year is required.';
    }

    const trimmedMajor = major.trim();
    if (!trimmedMajor) {
      newErrors.major = 'Major is required.';
    } else if (trimmedMajor.length > 200) {
      newErrors.major = 'Major must be 200 characters or fewer.';
    }

    if (!advisingTopic) {
      newErrors.advising_topic = 'Advising topic is required.';
    }

    return newErrors;
  }

  function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setSubmitted(true);

    const validationErrors = validate();
    setErrors(validationErrors);

    if (Object.keys(validationErrors).length > 0) {
      return;
    }

    const data: QuestionnaireData = {
      academic_year: academicYear as QuestionnaireData['academic_year'],
      major: major.trim(),
      advising_topic: advisingTopic as QuestionnaireData['advising_topic'],
    };

    setQuestionnaireData(data);
    router.push('/chat');
  }

  return (
    <main className="min-h-screen flex items-center justify-center bg-gray-50 px-4 py-8">
      <div className="w-full max-w-md bg-white rounded-lg shadow-md p-6 sm:p-8">
        <div className="text-center mb-6">
          <h1 className="text-2xl font-bold text-[#8C1D40]">
            GUIDE
          </h1>
          <p className="text-sm text-gray-600 mt-1">
            ASU Academic Advising Assistant
          </p>
        </div>

        <form onSubmit={handleSubmit} noValidate>
          {/* Academic Year */}
          <div className="mb-4">
            <label
              htmlFor="academic-year"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Academic Year
            </label>
            <select
              id="academic-year"
              value={academicYear}
              onChange={(e) => setAcademicYear(e.target.value)}
              aria-required="true"
              aria-invalid={submitted && !!errors.academic_year}
              aria-describedby={errors.academic_year ? 'academic-year-error' : undefined}
              className={`w-full rounded-md border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#8C1D40] ${
                submitted && errors.academic_year
                  ? 'border-red-500'
                  : 'border-gray-300'
              }`}
            >
              <option value="">Select academic year</option>
              {ACADEMIC_YEARS.map((year) => (
                <option key={year} value={year}>
                  {year}
                </option>
              ))}
            </select>
            {submitted && errors.academic_year && (
              <p
                id="academic-year-error"
                role="alert"
                className="mt-1 text-xs text-red-600"
              >
                {errors.academic_year}
              </p>
            )}
          </div>

          {/* Major */}
          <div className="mb-4">
            <label
              htmlFor="major"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Major
            </label>
            <input
              id="major"
              type="text"
              value={major}
              onChange={(e) => setMajor(e.target.value)}
              maxLength={200}
              aria-required="true"
              aria-invalid={submitted && !!errors.major}
              aria-describedby={errors.major ? 'major-error' : undefined}
              placeholder="e.g. Computer Science"
              className={`w-full rounded-md border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#8C1D40] ${
                submitted && errors.major
                  ? 'border-red-500'
                  : 'border-gray-300'
              }`}
            />
            {submitted && errors.major && (
              <p
                id="major-error"
                role="alert"
                className="mt-1 text-xs text-red-600"
              >
                {errors.major}
              </p>
            )}
          </div>

          {/* Advising Topic */}
          <div className="mb-6">
            <label
              htmlFor="advising-topic"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Advising Topic
            </label>
            <select
              id="advising-topic"
              value={advisingTopic}
              onChange={(e) => setAdvisingTopic(e.target.value)}
              aria-required="true"
              aria-invalid={submitted && !!errors.advising_topic}
              aria-describedby={errors.advising_topic ? 'advising-topic-error' : undefined}
              className={`w-full rounded-md border px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#8C1D40] ${
                submitted && errors.advising_topic
                  ? 'border-red-500'
                  : 'border-gray-300'
              }`}
            >
              <option value="">Select advising topic</option>
              {ADVISING_TOPICS.map((topic) => (
                <option key={topic} value={topic}>
                  {topic}
                </option>
              ))}
            </select>
            {submitted && errors.advising_topic && (
              <p
                id="advising-topic-error"
                role="alert"
                className="mt-1 text-xs text-red-600"
              >
                {errors.advising_topic}
              </p>
            )}
          </div>

          <button
            type="submit"
            className="w-full rounded-md bg-[#8C1D40] px-4 py-2 text-sm font-medium text-white hover:bg-[#6b1631] focus:outline-none focus:ring-2 focus:ring-[#FFC627] focus:ring-offset-2 transition-colors"
          >
            Start Chat
          </button>
        </form>
      </div>
    </main>
  );
}
