/// <reference types="vite/client" />

interface ImportMetaEnv {
  [key: string]: any;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

declare module 'react' {
  export = React;
  export as namespace React;
  namespace React {
    type ReactNode = any;
    type FC<P = {}> = (props: P) => any;
    type FormEvent<T = any> = any;
    type ChangeEvent<T = any> = any;
    function useState<T>(init: T | (() => T)): [T, (val: T | ((prev: T) => T)) => void];
    function useEffect(effect: () => any, deps?: any[]): void;
    function useRef<T>(val?: T): { current: T };
    function createContext<T>(val?: T): any;
    function useContext<T>(ctx: any): T;
    const StrictMode: any;
  }
}

declare module 'react-dom/client' {
  export function createRoot(container: any): {
    render(children: any): void;
  };
}

declare module 'lucide-react' {
  export const Activity: any;
  export const AlertCircle: any;
  export const AlertTriangle: any;
  export const ArrowRight: any;
  export const CheckCircle2: any;
  export const Clock: any;
  export const Headphones: any;
  export const Info: any;
  export const Lock: any;
  export const Mic: any;
  export const MicOff: any;
  export const Phone: any;
  export const PhoneCall: any;
  export const PhoneOff: any;
  export const Radio: any;
  export const Shield: any;
  export const Sparkles: any;
  export const User: any;
  export const Volume2: any;
  export const X: any;
  export const [key: string]: any;
}

declare module 'livekit-client' {
  export class Room {
    constructor(options?: any);
    connect(url: string, token: string): Promise<void>;
    disconnect(): Promise<void>;
    localParticipant: any;
    on(event: any, handler: (...args: any[]) => void): void;
  }
  export enum RoomEvent {
    TrackSubscribed = 'trackSubscribed',
    TrackUnsubscribed = 'trackUnsubscribed',
    ActiveSpeakersChanged = 'activeSpeakersChanged',
    ParticipantConnected = 'participantConnected',
    ParticipantDisconnected = 'participantDisconnected',
    ConnectionStateChanged = 'connectionStateChanged',
    Disconnected = 'disconnected',
  }
  export class Track {
    kind: any;
    sid: string;
    attach(el?: any): HTMLAudioElement;
    detach(el?: any): void;
    static Kind: { Audio: string; Video: string };
  }
  export type RemoteParticipant = any;
  export type RemoteTrackPublication = any;
  export type ConnectionState = any;
}

declare namespace JSX {
  interface IntrinsicElements {
    [elemName: string]: any;
  }
}
