import fc from 'fast-check';
import { generateSessionId } from '../session';

// Property 25: Session ID Generation
// Validates: FR-SESSION-1
describe('Property-based: Session ID Generation', () => {
  // 45.1 Property 25: Generate random timestamps, verify ID format (≥ 33 chars, starts with session_)
  it('always produces IDs ≥ 33 characters starting with session_', () => {
    fc.assert(
      fc.property(fc.integer({ min: 0, max: 1000 }), (_seed) => {
        const id = generateSessionId();
        expect(id.length).toBeGreaterThanOrEqual(33);
        expect(id.startsWith('session_')).toBe(true);
      }),
      { numRuns: 100 }
    );
  });

  it('always produces IDs containing only valid characters', () => {
    fc.assert(
      fc.property(fc.integer({ min: 0, max: 1000 }), (_seed) => {
        const id = generateSessionId();
        // Should only contain alphanumeric, underscores
        expect(id).toMatch(/^[a-z0-9_]+$/);
      }),
      { numRuns: 100 }
    );
  });

  it('always produces unique IDs', () => {
    fc.assert(
      fc.property(fc.integer({ min: 1, max: 50 }), (count) => {
        const ids = new Set<string>();
        for (let i = 0; i < count; i++) {
          ids.add(generateSessionId());
        }
        expect(ids.size).toBe(count);
      }),
      { numRuns: 100 }
    );
  });
});
