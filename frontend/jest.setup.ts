import '@testing-library/jest-dom';
import { TextEncoder, TextDecoder } from 'util';

// Polyfill TextEncoder/TextDecoder for jsdom
Object.assign(global, { TextEncoder, TextDecoder });

// Mock scrollIntoView (not available in jsdom)
Element.prototype.scrollIntoView = jest.fn();
