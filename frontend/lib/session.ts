// ADR: sessionStorage for chat session state | cleared on tab close per P26

export interface QuestionnaireData {
  academic_year: 'Freshman' | 'Sophomore' | 'Junior' | 'Senior' | 'Graduate';
  major: string;
  advising_topic:
    | 'Course Planning'
    | 'Degree Requirements'
    | 'Academic Standing'
    | 'General Advising';
}

export interface SessionData {
  session_id: string;
  questionnaire: QuestionnaireData | null;
}

const SESSION_KEY = 'guide_session_id';
const QUESTIONNAIRE_KEY = 'guide_questionnaire_data';

/**
 * Generates a session ID with format `session_{timestamp}_{random}`.
 * Guaranteed to be at least 33 characters (P25).
 */
export function generateSessionId(): string {
  const timestamp = Date.now().toString(36);
  const random1 = Math.random().toString(36).substring(2, 15);
  const random2 = Math.random().toString(36).substring(2, 15);
  let sessionId = `session_${timestamp}_${random1}${random2}`;
  // Ensure minimum 33 characters
  while (sessionId.length < 33) {
    sessionId += Math.random().toString(36).substring(2, 3);
  }
  return sessionId;
}

/**
 * Returns existing session ID from sessionStorage, or generates and stores a new one.
 * Persists across page navigations within the same tab (P26).
 */
export function getOrCreateSessionId(): string {
  let sessionId = sessionStorage.getItem(SESSION_KEY);
  if (!sessionId) {
    sessionId = generateSessionId();
    sessionStorage.setItem(SESSION_KEY, sessionId);
  }
  return sessionId;
}

/**
 * Retrieves questionnaire data from sessionStorage.
 * Returns null if not set or if JSON parsing fails.
 */
export function getQuestionnaireData(): QuestionnaireData | null {
  const raw = sessionStorage.getItem(QUESTIONNAIRE_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as QuestionnaireData;
  } catch {
    return null;
  }
}

/**
 * Saves questionnaire data to sessionStorage as JSON.
 */
export function setQuestionnaireData(data: QuestionnaireData): void {
  sessionStorage.setItem(QUESTIONNAIRE_KEY, JSON.stringify(data));
}

/**
 * Clears all session data from sessionStorage.
 */
export function clearSession(): void {
  sessionStorage.removeItem(SESSION_KEY);
  sessionStorage.removeItem(QUESTIONNAIRE_KEY);
}
