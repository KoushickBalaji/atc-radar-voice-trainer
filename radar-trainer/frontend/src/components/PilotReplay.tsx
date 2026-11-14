import { useEffect, useRef, useState } from 'react';
import { playB64Wav } from '../audio';
import { queueRadio } from '../radioChannel';

export default function PilotReplay({ audio, radioNoise }: { audio: string; radioNoise: boolean }) {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState('');
  const mounted = useRef(true);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  const replay = async () => {
    setPending(true); setError('');
    try { await queueRadio(() => playB64Wav(audio, undefined, radioNoise), () => mounted.current); }
    catch { if (mounted.current) setError('Replay failed. Please try again.'); }
    finally { if (mounted.current) setPending(false); }
  };
  return <div>
    <button type="button" disabled={pending} onClick={() => void replay()} aria-label="Replay pilot readback"
      className="text-xs underline disabled:opacity-50">{pending ? 'Replay queued / playing…' : 'Replay pilot readback'}</button>
    {error && <p role="alert">{error}</p>}
  </div>;
}
