import '@testing-library/jest-dom';
import { afterAll, afterEach, beforeAll, beforeEach, vi } from 'vitest';
import { cleanup } from '@testing-library/react';
import { server } from './mocks/server';

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: vi.fn((key: string) => store[key] ?? null),
    setItem: vi.fn((key: string, value: string) => {
      store[key] = value;
    }),
    removeItem: vi.fn((key: string) => {
      delete store[key];
    }),
    clear: vi.fn(() => {
      store = {};
    }),
    get length() {
      return Object.keys(store).length;
    },
    key: vi.fn((index: number) => Object.keys(store)[index] ?? null)
  };
})();

Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
  writable: true
});

// Mock window.location
const mockLocation = {
  href: 'http://localhost:3000',
  origin: 'http://localhost:3000',
  pathname: '/',
  search: '',
  hash: '',
  host: 'localhost:3000',
  hostname: 'localhost',
  port: '3000',
  protocol: 'http:',
  assign: vi.fn(),
  replace: vi.fn(),
  reload: vi.fn()
};

Object.defineProperty(window, 'location', {
  value: mockLocation,
  writable: true
});

// Establish API mocking before all tests
beforeAll(() => server.listen({ onUnhandledRequest: 'error' }));

// Reset state before each test
beforeEach(() => {
  localStorageMock.clear();
  vi.clearAllMocks();
  mockLocation.href = 'http://localhost:3000';
});

// Reset any request handlers after each test
afterEach(() => {
  cleanup();
  server.resetHandlers();
});

// Clean up after all tests
afterAll(() => server.close());
