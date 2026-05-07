import {
  generateSessionId,
  getOrCreateSessionId,
  setQuestionnaireData,
  getQuestionnaireData,
  type QuestionnaireData,
} from '../session';

// Mock sessionStorage
const mockStorage: Record<string, string> = {};
const mockSessionStorage = {
  getItem: jest.fn((key: string) => mockStorage[key] ?? null),
  setItem: jest.fn((key: string, value: string) => {
    mockStorage[key] = value;
  }),
  removeItem: jest.fn((key: string) => {
    delete mockStorage[key];
  }),
  clear: jest.fn(() => {
    Object.keys(mockStorage).forEach((key) => delete mockStorage[key]);
  }),
  length: 0,
  key: jest.fn(),
};

Object.defineProperty(global, 'sessionStorage', {
  value: mockSessionStorage,
  writable: true,
});

describe('Session Management', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    Object.keys(mockStorage).forEach((key) => delete mockStorage[key]);
  });

  // 39.1 Test generateSessionId() produces IDs ≥ 33 characters starting with session_
  describe('generateSessionId()', () => {
    it('produces IDs at least 33 characters long', () => {
      const id = generateSessionId();
      expect(id.length).toBeGreaterThanOrEqual(33);
    });

    it('produces IDs starting with "session_"', () => {
      const id = generateSessionId();
      expect(id).toMatch(/^session_/);
    });

    it('produces unique IDs on successive calls', () => {
      const id1 = generateSessionId();
      const id2 = generateSessionId();
      expect(id1).not.toBe(id2);
    });
  });

  // 39.2 Test getOrCreateSessionId() returns existing ID from sessionStorage
  describe('getOrCreateSessionId()', () => {
    it('returns existing ID from sessionStorage', () => {
      const existingId = 'session_existing_id_1234567890abcdef';
      mockStorage['guide_session_id'] = existingId;

      const result = getOrCreateSessionId();
      expect(result).toBe(existingId);
      expect(mockSessionStorage.getItem).toHaveBeenCalledWith('guide_session_id');
    });

    // 39.3 Test getOrCreateSessionId() creates new ID when sessionStorage is empty
    it('creates new ID when sessionStorage is empty', () => {
      const result = getOrCreateSessionId();
      expect(result).toMatch(/^session_/);
      expect(result.length).toBeGreaterThanOrEqual(33);
      expect(mockSessionStorage.setItem).toHaveBeenCalledWith(
        'guide_session_id',
        result
      );
    });
  });

  // 39.4 Test setQuestionnaireData() and getQuestionnaireData() round-trip
  describe('Questionnaire data round-trip', () => {
    it('stores and retrieves questionnaire data correctly', () => {
      const data: QuestionnaireData = {
        academic_year: 'Junior',
        major: 'Computer Science',
        advising_topic: 'Course Planning',
      };

      setQuestionnaireData(data);
      expect(mockSessionStorage.setItem).toHaveBeenCalledWith(
        'guide_questionnaire_data',
        JSON.stringify(data)
      );

      const retrieved = getQuestionnaireData();
      expect(retrieved).toEqual(data);
    });

    it('returns null when no questionnaire data is stored', () => {
      const result = getQuestionnaireData();
      expect(result).toBeNull();
    });

    it('returns null when stored data is invalid JSON', () => {
      mockStorage['guide_questionnaire_data'] = 'not-valid-json{';
      const result = getQuestionnaireData();
      expect(result).toBeNull();
    });
  });
});
