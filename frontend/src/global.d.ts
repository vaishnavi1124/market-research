// frontend\src\global.d.ts

// Minimal event interfaces
interface SpeechRecognitionEvent extends Event {
  readonly results: SpeechRecognitionResultList;
}

interface SpeechRecognitionErrorEvent extends Event {
  readonly error: string;
  readonly message: string;
}

// Minimal Web Speech API types for TS
interface SpeechRecognition extends EventTarget {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  start: () => void;
  stop: () => void;
  abort: () => void;

  onresult?: (ev: SpeechRecognitionEvent) => any;
  onerror?: (ev: SpeechRecognitionErrorEvent) => any;
  onstart?: (ev: Event) => any;
  onend?: (ev: Event) => any;
  onaudiostart?: (ev: Event) => any;
  onsoundstart?: (ev: Event) => any;
  onspeechstart?: (ev: Event) => any;
  onspeechend?: (ev: Event) => any;
  onsoundend?: (ev: Event) => any;
  onaudioend?: (ev: Event) => any;
}

interface SpeechRecognitionAlternative {
  transcript: string;
  confidence: number;
}
interface SpeechRecognitionResult {
  readonly isFinal: boolean;
  readonly length: number;
  item(index: number): SpeechRecognitionAlternative;
  [index: number]: SpeechRecognitionAlternative;
}
interface SpeechRecognitionResultList {
  readonly length: number;
  item(index: number): SpeechRecognitionResult;
  [index: number]: SpeechRecognitionResult;
}
interface SpeechRecognitionEvent extends Event {
  readonly results: SpeechRecognitionResultList;
  readonly resultIndex: number;
}
interface SpeechRecognitionErrorEvent extends Event {
  readonly error: string;
  readonly message: string;
}

interface Window {
  webkitSpeechRecognition: new () => SpeechRecognition;
}
