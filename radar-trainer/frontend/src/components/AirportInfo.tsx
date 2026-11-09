import { useEffect, useRef } from 'react';
import type { ReactNode } from 'react';
import { X } from 'lucide-react';

export default function AirportInfo({ open, onClose, title, children }: {
  open: boolean; onClose: () => void; title: string; children: ReactNode;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const content = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const element = dialog.current;
    if (open && !element?.open) {
      element?.showModal();
      if (content.current) content.current.scrollTop = 0;
    }
    if (!open && element?.open) element.close();
  }, [open]);
  return <dialog ref={dialog} className="airport-info-modal" aria-labelledby="airport-info-title"
    onCancel={onClose} onClose={onClose} onClick={e => { if (e.target === e.currentTarget) onClose(); }}>
    <div className="airport-info-shell">
      <header><h2 id="airport-info-title">{title}</h2><button type="button" autoFocus aria-label="Close airport information" onClick={onClose}><X size={18} aria-hidden="true" /></button></header>
      <div ref={content} className="airport-info-content">{children}</div>
    </div>
  </dialog>;
}
