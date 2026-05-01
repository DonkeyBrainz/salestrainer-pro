import { describe, it, expect, vi, beforeEach, afterEach, beforeAll, afterAll } from 'vitest';
import { renderHook, act } from '@testing-library/react';

// Mock audio utils
vi.mock('@/services/audioUtils', () => ({
  base64ToBytes: vi.fn(() => new Uint8Array([1, 2, 3, 4])),
  bytesToBase64: vi.fn(() => 'base64-encoded'),
  decodeAudioData: vi.fn(() =>
    Promise.resolve({
      numberOfChannels: 1,
      length: 1024,
      sampleRate: 24000,
      getChannelData: () => new Float32Array(1024),
    })
  ),
}));

// Mock logger
vi.mock('@/services/logger', () => ({
  logger: {
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
  },
}));

// Create mock factory for AudioContext
const createMockAudioContext = () => ({
  sampleRate: 48000,
  destination: {},
  createMediaStreamSource: vi.fn(() => ({
    connect: vi.fn(),
    disconnect: vi.fn(),
  })),
  createAnalyser: vi.fn(() => ({
    fftSize: 0,
    frequencyBinCount: 128,
    connect: vi.fn(),
    disconnect: vi.fn(),
    getByteFrequencyData: vi.fn((arr: Uint8Array) => {
      for (let i = 0; i < arr.length; i++) arr[i] = 50;
    }),
  })),
  createScriptProcessor: vi.fn(() => ({
    onaudioprocess: null,
    connect: vi.fn(),
    disconnect: vi.fn(),
  })),
  createGain: vi.fn(() => ({
    gain: { value: 1 },
    connect: vi.fn(),
    disconnect: vi.fn(),
  })),
  createBufferSource: vi.fn(() => ({
    buffer: null,
    connect: vi.fn(),
    start: vi.fn(),
    onended: null,
  })),
  createBuffer: vi.fn((channels: number, frames: number, rate: number) => ({
    numberOfChannels: channels,
    length: frames,
    sampleRate: rate,
    getChannelData: vi.fn(() => new Float32Array(frames)),
  })),
  close: vi.fn(),
});

// Mock media stream
const mockStopFn = vi.fn();
const mockMediaStream = {
  getTracks: vi.fn(() => [{ stop: mockStopFn }]),
};

// Store reference to AudioContext instances
let audioContextInstances: any[] = [];
const MockAudioContext = vi.fn().mockImplementation(() => {
  const ctx = createMockAudioContext();
  audioContextInstances.push(ctx);
  return ctx;
});

// Set up globals before tests
beforeAll(() => {
  // Mock AudioContext
  (globalThis as any).AudioContext = MockAudioContext;

  // Mock navigator.mediaDevices
  Object.defineProperty(globalThis.navigator, 'mediaDevices', {
    writable: true,
    value: {
      getUserMedia: vi.fn(() => Promise.resolve(mockMediaStream)),
    },
  });

  // Mock requestAnimationFrame
  globalThis.requestAnimationFrame = vi.fn(() => 1);
  globalThis.cancelAnimationFrame = vi.fn();
});

afterAll(() => {
  vi.restoreAllMocks();
});

// Import after mocks are set up
import { useAudio } from './useAudio';

describe('useAudio', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    audioContextInstances = [];
    mockStopFn.mockClear();
    mockMediaStream.getTracks.mockReturnValue([{ stop: mockStopFn }]);
  });

  describe('initial state', () => {
    it('should start with mic inactive', () => {
      const { result } = renderHook(() => useAudio());

      expect(result.current.isMicActive).toBe(false);
      expect(result.current.isMuted).toBe(false);
      expect(result.current.inputLevel).toBe(0);
      expect(result.current.isPlaying).toBe(false);
    });

    it('should have null analysers initially', () => {
      const { result } = renderHook(() => useAudio());

      expect(result.current.inputAnalyser).toBeNull();
      expect(result.current.outputAnalyser).toBeNull();
    });
  });

  describe('microphone control', () => {
    it('should start microphone', async () => {
      const { result } = renderHook(() => useAudio());

      await act(async () => {
        await result.current.startMic();
      });

      expect(result.current.isMicActive).toBe(true);
      expect(navigator.mediaDevices.getUserMedia).toHaveBeenCalledWith({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          sampleRate: 16000,
        },
      });
      expect(MockAudioContext).toHaveBeenCalled();
    });

    it('should stop microphone', async () => {
      const { result } = renderHook(() => useAudio());

      await act(async () => {
        await result.current.startMic();
      });

      expect(result.current.isMicActive).toBe(true);

      act(() => {
        result.current.stopMic();
      });

      expect(result.current.isMicActive).toBe(false);
      expect(result.current.inputLevel).toBe(0);
    });

    it('should warn if mic already active', async () => {
      const { result } = renderHook(() => useAudio());

      await act(async () => {
        await result.current.startMic();
      });

      const callCount = MockAudioContext.mock.calls.length;

      await act(async () => {
        await result.current.startMic();
      });

      // Should not create another AudioContext
      expect(MockAudioContext).toHaveBeenCalledTimes(callCount);
      expect(result.current.isMicActive).toBe(true);
    });

    it('should toggle mute', () => {
      const { result } = renderHook(() => useAudio());

      expect(result.current.isMuted).toBe(false);

      act(() => {
        result.current.toggleMute();
      });

      expect(result.current.isMuted).toBe(true);

      act(() => {
        result.current.toggleMute();
      });

      expect(result.current.isMuted).toBe(false);
    });
  });

  describe('audio data callback', () => {
    it('should set up audio processing callback', async () => {
      const onAudioData = vi.fn();
      const { result } = renderHook(() => useAudio(onAudioData));

      await act(async () => {
        await result.current.startMic();
      });

      expect(MockAudioContext).toHaveBeenCalled();
      expect(result.current.isMicActive).toBe(true);
      // The audio context should have created a script processor
      expect(audioContextInstances[0].createScriptProcessor).toHaveBeenCalled();
    });
  });

  describe('audio playback', () => {
    it('should create output context on first playback', async () => {
      const { result } = renderHook(() => useAudio());

      await act(async () => {
        result.current.playAudio('base64-audio-data');
        await new Promise((resolve) => setTimeout(resolve, 10));
      });

      expect(MockAudioContext).toHaveBeenCalled();
    });

    it('should handle playback requests without error', async () => {
      const { result } = renderHook(() => useAudio());

      await act(async () => {
        result.current.playAudio('base64-audio-data');
        await new Promise((resolve) => setTimeout(resolve, 10));
      });

      // Should not throw
      expect(result.current.isPlaying).toBeDefined();
    });
  });

  describe('cleanup', () => {
    it('should clean up all resources', async () => {
      const { result } = renderHook(() => useAudio());

      await act(async () => {
        await result.current.startMic();
      });

      act(() => {
        result.current.cleanup();
      });

      expect(result.current.isMicActive).toBe(false);
      expect(result.current.isPlaying).toBe(false);
      expect(mockStopFn).toHaveBeenCalled();
    });

    it('should stop media stream tracks on cleanup', async () => {
      const { result } = renderHook(() => useAudio());

      await act(async () => {
        await result.current.startMic();
      });

      act(() => {
        result.current.cleanup();
      });

      expect(mockStopFn).toHaveBeenCalled();
    });
  });
});
