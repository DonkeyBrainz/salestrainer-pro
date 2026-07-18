import { useState, useRef, useCallback, useEffect } from 'react';
import { base64ToBytes, bytesToBase64, decodeAudioData, floatTo16BitPcm } from '@/services/audioUtils';
import { logger } from '@/services/logger';

const MIC_SAMPLE_RATE = 16000;
const OUTPUT_SAMPLE_RATE = 24000;
const BUFFER_SIZE = 4096;

export interface UseAudioReturn {
  startMic: () => Promise<void>;
  stopMic: () => void;
  isMicActive: boolean;
  isMuted: boolean;
  toggleMute: () => void;
  inputLevel: number;
  inputAnalyser: AnalyserNode | null;
  outputAnalyser: AnalyserNode | null;
  playAudio: (base64Pcm: string) => void;
  stopPlayback: () => void;
  isPlaying: boolean;
  cleanup: () => void;
}

interface AudioState {
  inputContext: AudioContext | null;
  outputContext: AudioContext | null;
  inputAnalyser: AnalyserNode | null;
  outputAnalyser: AnalyserNode | null;
  gainNode: GainNode | null;
  mediaStream: MediaStream | null;
  scriptProcessor: ScriptProcessorNode | null;
}

export function useAudio(
  onAudioData?: (base64Pcm: string) => void
): UseAudioReturn {
  const [isMicActive, setIsMicActive] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [inputLevel, setInputLevel] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);

  // State for analysers to trigger re-renders when created
  const [inputAnalyser, setInputAnalyser] = useState<AnalyserNode | null>(null);
  const [outputAnalyser, setOutputAnalyser] = useState<AnalyserNode | null>(null);

  // Ref for isMuted to avoid stale closure in onaudioprocess
  const isMutedRef = useRef(isMuted);
  useEffect(() => {
    isMutedRef.current = isMuted;
  }, [isMuted]);

  // Ref for onAudioData callback to avoid stale closure
  const onAudioDataRef = useRef(onAudioData);
  useEffect(() => {
    onAudioDataRef.current = onAudioData;
  }, [onAudioData]);

  const audioState = useRef<AudioState>({
    inputContext: null,
    outputContext: null,
    inputAnalyser: null,
    outputAnalyser: null,
    gainNode: null,
    mediaStream: null,
    scriptProcessor: null,
  });

  // Playback queue for sequential audio chunks
  const playbackQueue = useRef<AudioBuffer[]>([]);
  const isProcessingQueue = useRef(false);
  // Track when the next scheduled buffer should start (for gapless playback)
  const nextScheduledTime = useRef<number>(0);
  // Live scheduled sources, kept so barge-in can stop them mid-flight
  const scheduledSources = useRef<Set<AudioBufferSourceNode>>(new Set());
  // Queue for incoming base64 data to ensure order is preserved during async decoding
  const incomingAudioQueue = useRef<string[]>([]);
  const isDecodingAudio = useRef(false);
  // Bumped on flush so in-flight decodes drop buffers from the interrupted turn
  const playbackGeneration = useRef(0);

  // Animation frame for input level
  const levelAnimationFrame = useRef<number | null>(null);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      cleanup();
    };
  }, []);

  const updateInputLevel = useCallback(() => {
    const analyser = audioState.current.inputAnalyser;
    if (!analyser) {
      setInputLevel(0);
      return;
    }

    const dataArray = new Uint8Array(analyser.frequencyBinCount);
    analyser.getByteFrequencyData(dataArray);

    let sum = 0;
    for (let i = 0; i < dataArray.length; i++) {
      sum += dataArray[i];
    }
    const average = sum / dataArray.length;
    const level = Math.min(average / 128, 1);
    setInputLevel(level);

    if (isMicActive) {
      levelAnimationFrame.current = requestAnimationFrame(updateInputLevel);
    }
  }, [isMicActive]);

  const resample = useCallback((
    inputBuffer: Float32Array,
    inputSampleRate: number,
    outputSampleRate: number
  ): Float32Array => {
    if (inputSampleRate === outputSampleRate) {
      return inputBuffer;
    }

    const ratio = inputSampleRate / outputSampleRate;
    const outputLength = Math.round(inputBuffer.length / ratio);
    const output = new Float32Array(outputLength);

    for (let i = 0; i < outputLength; i++) {
      const srcIndex = i * ratio;
      const srcIndexFloor = Math.floor(srcIndex);
      const srcIndexCeil = Math.min(srcIndexFloor + 1, inputBuffer.length - 1);
      const t = srcIndex - srcIndexFloor;

      // Linear interpolation
      output[i] = inputBuffer[srcIndexFloor] * (1 - t) + inputBuffer[srcIndexCeil] * t;
    }

    return output;
  }, []);

  const startMic = useCallback(async () => {
    if (isMicActive) {
      logger.warn('Audio', 'Microphone already active');
      return;
    }

    try {
      // Request microphone access
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          sampleRate: MIC_SAMPLE_RATE,
        },
      });

      // Create audio context
      const inputContext = new AudioContext({ sampleRate: MIC_SAMPLE_RATE });

      // Resume context if suspended (required by browsers after user gesture)
      if (inputContext.state === 'suspended') {
        await inputContext.resume();
      }

      const source = inputContext.createMediaStreamSource(stream);

      // Create analyser for visualization
      const analyser = inputContext.createAnalyser();
      analyser.fftSize = 256;

      // Create script processor for capturing audio data
      // Note: ScriptProcessorNode is deprecated but more widely supported than AudioWorklet
      const scriptProcessor = inputContext.createScriptProcessor(BUFFER_SIZE, 1, 1);

      scriptProcessor.onaudioprocess = (event) => {
        // Use ref to get current muted state (avoids stale closure)
        if (isMutedRef.current) return;

        const inputData = event.inputBuffer.getChannelData(0);

        // Resample if needed (AudioContext may not honor our sample rate request)
        const resampledData = resample(inputData, inputContext.sampleRate, MIC_SAMPLE_RATE);

        // Convert to 16-bit PCM
        const pcmData = floatTo16BitPcm(resampledData);

        // Encode as base64 and send via ref (avoids stale closure)
        const base64 = bytesToBase64(pcmData);
        onAudioDataRef.current?.(base64);
      };

      // Connect nodes: source -> analyser -> scriptProcessor -> destination (muted)
      source.connect(analyser);
      analyser.connect(scriptProcessor);
      scriptProcessor.connect(inputContext.destination);

      // Store references
      audioState.current.inputContext = inputContext;
      audioState.current.mediaStream = stream;
      audioState.current.inputAnalyser = analyser;
      audioState.current.scriptProcessor = scriptProcessor;

      // Update state for re-render
      setInputAnalyser(analyser);
      setIsMicActive(true);
      logger.info('Audio', 'Microphone started', { sampleRate: inputContext.sampleRate });

      // Start level monitoring
      levelAnimationFrame.current = requestAnimationFrame(updateInputLevel);
    } catch (err) {
      logger.error('Audio', 'Failed to start microphone', { error: err });
      throw err;
    }
  }, [isMicActive, resample, updateInputLevel]);

  const stopMic = useCallback(() => {
    if (levelAnimationFrame.current) {
      cancelAnimationFrame(levelAnimationFrame.current);
      levelAnimationFrame.current = null;
    }

    if (audioState.current.scriptProcessor) {
      audioState.current.scriptProcessor.disconnect();
      audioState.current.scriptProcessor = null;
    }

    if (audioState.current.inputAnalyser) {
      audioState.current.inputAnalyser.disconnect();
    }

    if (audioState.current.mediaStream) {
      audioState.current.mediaStream.getTracks().forEach((track) => track.stop());
      audioState.current.mediaStream = null;
    }

    if (audioState.current.inputContext) {
      audioState.current.inputContext.close();
      audioState.current.inputContext = null;
      audioState.current.inputAnalyser = null;
    }

    setInputAnalyser(null);
    setIsMicActive(false);
    setInputLevel(0);
    logger.info('Audio', 'Microphone stopped');
  }, []);

  const toggleMute = useCallback(() => {
    setIsMuted((prev) => !prev);
    logger.info('Audio', `Microphone ${isMuted ? 'unmuted' : 'muted'}`);
  }, [isMuted]);

  const initOutputContext = useCallback(async () => {
    if (audioState.current.outputContext) {
      // Resume if suspended
      if (audioState.current.outputContext.state === 'suspended') {
        await audioState.current.outputContext.resume();
      }
      return audioState.current.outputContext;
    }

    const ctx = new AudioContext({ sampleRate: OUTPUT_SAMPLE_RATE });

    // Resume context if suspended (required by browsers after user gesture)
    if (ctx.state === 'suspended') {
      await ctx.resume();
    }

    // Create output analyser for visualization
    const analyser = ctx.createAnalyser();
    analyser.fftSize = 256;
    analyser.connect(ctx.destination);

    // Create gain node for volume control
    const gainNode = ctx.createGain();
    gainNode.connect(analyser);

    audioState.current.outputContext = ctx;
    audioState.current.outputAnalyser = analyser;
    audioState.current.gainNode = gainNode;

    // Update state for re-render
    setOutputAnalyser(analyser);

    return ctx;
  }, []);

  const processPlaybackQueue = useCallback(() => {
    if (playbackQueue.current.length === 0) {
      return;
    }

    const ctx = audioState.current.outputContext;
    const gainNode = audioState.current.gainNode;
    if (!ctx || !gainNode) return;

    // Set isPlaying if not already
    if (!isProcessingQueue.current) {
      isProcessingQueue.current = true;
      setIsPlaying(true);
    }

    // Initialize or update scheduled time
    // If we're behind the current time, reset to now (avoids playing catch-up)
    const now = ctx.currentTime;
    if (nextScheduledTime.current < now) {
      nextScheduledTime.current = now;
    }

    // Schedule all queued buffers for gapless playback
    while (playbackQueue.current.length > 0) {
      const buffer = playbackQueue.current.shift();
      if (!buffer) continue;

      const source = ctx.createBufferSource();
      source.buffer = buffer;
      source.connect(gainNode);

      // Schedule this buffer to start exactly when the previous one ends
      source.start(nextScheduledTime.current);
      nextScheduledTime.current += buffer.duration;

      // Track active sources so barge-in can stop them and so we know
      // when all playback is done
      scheduledSources.current.add(source);

      source.onended = () => {
        scheduledSources.current.delete(source);

        // When all scheduled sources have finished, reset state
        if (scheduledSources.current.size === 0 && playbackQueue.current.length === 0) {
          isProcessingQueue.current = false;
          setIsPlaying(false);
        }
      };
    }
  }, []);

  // Process incoming audio queue sequentially to preserve order
  const processIncomingAudio = useCallback(async () => {
    if (isDecodingAudio.current || incomingAudioQueue.current.length === 0) {
      return;
    }

    isDecodingAudio.current = true;

    try {
      const ctx = await initOutputContext();

      while (incomingAudioQueue.current.length > 0) {
        const base64Pcm = incomingAudioQueue.current.shift();
        if (!base64Pcm) continue;

        const generation = playbackGeneration.current;
        try {
          // Decode base64 to bytes
          const pcmBytes = base64ToBytes(base64Pcm);

          // Decode PCM to AudioBuffer
          const audioBuffer = await decodeAudioData(pcmBytes, ctx, OUTPUT_SAMPLE_RATE);

          // A flush happened while decoding — this chunk belongs to the
          // interrupted turn, drop it
          if (generation !== playbackGeneration.current) continue;

          // Add to playback queue
          playbackQueue.current.push(audioBuffer);

          // Process playback queue
          processPlaybackQueue();
        } catch (err) {
          logger.error('Audio', 'Failed to decode audio chunk', { error: err });
        }
      }
    } finally {
      isDecodingAudio.current = false;
    }
  }, [initOutputContext, processPlaybackQueue]);

  const playAudio = useCallback((base64Pcm: string) => {
    // Queue incoming audio data to preserve order
    incomingAudioQueue.current.push(base64Pcm);
    // Process queue (will be a no-op if already processing)
    processIncomingAudio();
  }, [processIncomingAudio]);

  // Flush all playback immediately (barge-in): stop already-scheduled sources
  // and drop anything queued or still decoding
  const stopPlayback = useCallback(() => {
    playbackGeneration.current += 1;
    incomingAudioQueue.current = [];
    playbackQueue.current = [];

    for (const source of scheduledSources.current) {
      source.onended = null;
      try {
        source.stop();
      } catch {
        // stop() throws if the source already ended — safe to ignore
      }
    }
    scheduledSources.current.clear();

    nextScheduledTime.current = 0;
    isProcessingQueue.current = false;
    setIsPlaying(false);
    logger.info('Audio', 'Playback flushed');
  }, []);

  const cleanup = useCallback(() => {
    stopMic();
    stopPlayback();
    isDecodingAudio.current = false;

    if (audioState.current.outputContext) {
      audioState.current.outputContext.close();
      audioState.current.outputContext = null;
      audioState.current.outputAnalyser = null;
      audioState.current.gainNode = null;
    }

    setOutputAnalyser(null);
    setIsPlaying(false);
    logger.info('Audio', 'Audio cleanup complete');
  }, [stopMic, stopPlayback]);

  return {
    startMic,
    stopMic,
    isMicActive,
    isMuted,
    toggleMute,
    inputLevel,
    inputAnalyser,
    outputAnalyser,
    playAudio,
    stopPlayback,
    isPlaying,
    cleanup,
  };
}
