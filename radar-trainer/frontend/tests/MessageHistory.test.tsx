import { render, screen } from '@testing-library/react';
import { expect, it } from 'vitest';
import MessageHistory from '../src/components/MessageHistory';
import type { SimHub } from '../src/useSim';

it('shows corrective trainer feedback without presenting it as a pilot readback or accepted command', () => {
  const message = 'The transcript says descend, but 8,000 feet is above the current 5,000 feet. If that target was intended, use climb.';
  const exchange = {
    transcript: 'AFR123 descend to eight thousand feet', orders: [], trafscript: [], readback: '',
    rejected: [message], feedback: [{code: 'vertical_direction_conflict', category: 'instruction' as const,
      blocking: true, message, evidence: {current_altitude_ft: 5000, target_altitude_ft: 8000}}],
  };
  const hub = { log: [{id: 1, t: '12:00', kind: 'tx', callsigns: ['AFR123'], exchange}], lastExchange: exchange } as unknown as SimHub;
  render(<MessageHistory hub={hub} selected="AFR123" />);
  expect(screen.getByRole('heading', {name: 'Trainer feedback'})).toBeTruthy();
  expect(screen.getAllByText(message)).toHaveLength(1);
  expect(screen.queryByRole('heading', {name: 'Pilot readback'})).toBeNull();
  expect(screen.queryByRole('heading', {name: 'Command accepted'})).toBeNull();
});
