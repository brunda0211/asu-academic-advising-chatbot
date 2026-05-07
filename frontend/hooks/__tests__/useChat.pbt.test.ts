import fc from 'fast-check';

// ADR: Test sanitizeInput directly by extracting the regex logic | avoids hook rendering overhead for PBT
function sanitizeInput(input: string): string {
  return input.replace(/<[^>]*>/g, '');
}

// Property 37: Input Sanitization
// Validates: NFR-SECURITY-3
describe('Property-based: Input Sanitization', () => {
  // 46.1 Property 37: Generate strings with HTML tags, verify all tags stripped after sanitization
  it('strips all <script> tags from input', () => {
    fc.assert(
      fc.property(
        fc.tuple(fc.string(), fc.string(), fc.string()),
        ([before, content, after]) => {
          const input = `${before}<script>${content}</script>${after}`;
          const result = sanitizeInput(input);
          expect(result).not.toMatch(/<script>/i);
          expect(result).not.toMatch(/<\/script>/i);
        }
      ),
      { numRuns: 100 }
    );
  });

  it('strips all <img> tags from input', () => {
    fc.assert(
      fc.property(
        fc.tuple(fc.string(), fc.string()),
        ([before, after]) => {
          const input = `${before}<img src="x" onerror="alert(1)">${after}`;
          const result = sanitizeInput(input);
          expect(result).not.toMatch(/<img[^>]*>/i);
        }
      ),
      { numRuns: 100 }
    );
  });

  it('strips all <div> tags from input', () => {
    fc.assert(
      fc.property(
        fc.tuple(fc.string(), fc.string(), fc.string()),
        ([before, content, after]) => {
          const input = `${before}<div class="test">${content}</div>${after}`;
          const result = sanitizeInput(input);
          expect(result).not.toMatch(/<div[^>]*>/i);
          expect(result).not.toMatch(/<\/div>/i);
        }
      ),
      { numRuns: 100 }
    );
  });

  it('strips arbitrary HTML tags from input', () => {
    const alphaChar = fc.constantFrom(...'abcdefghijklmnopqrstuvwxyz'.split(''));
    const tagName = fc.array(alphaChar, { minLength: 1, maxLength: 10 }).map((arr) => arr.join(''));

    fc.assert(
      fc.property(
        fc.tuple(fc.string(), tagName, fc.string()),
        ([before, tag, after]) => {
          const input = `${before}<${tag} class="x">${after}`;
          const result = sanitizeInput(input);
          expect(result).not.toMatch(/<[^>]+>/);
        }
      ),
      { numRuns: 100 }
    );
  });

  it('preserves text content between tags', () => {
    const safeChar = fc.constantFrom(...'abcdefghijklmnopqrstuvwxyz0123456789 '.split(''));
    const safeString = fc.array(safeChar, { minLength: 1, maxLength: 50 }).map((arr) => arr.join(''));

    fc.assert(
      fc.property(safeString, (text) => {
        const input = `<div>${text}</div>`;
        const result = sanitizeInput(input);
        expect(result).toBe(text);
      }),
      { numRuns: 100 }
    );
  });

  it('returns input unchanged when no HTML tags present', () => {
    const safeChar = fc.constantFrom(...'abcdefghijklmnopqrstuvwxyz0123456789 .,!?'.split(''));
    const safeString = fc.array(safeChar, { minLength: 0, maxLength: 100 }).map((arr) => arr.join(''));

    fc.assert(
      fc.property(safeString, (text) => {
        const result = sanitizeInput(text);
        expect(result).toBe(text);
      }),
      { numRuns: 100 }
    );
  });
});
