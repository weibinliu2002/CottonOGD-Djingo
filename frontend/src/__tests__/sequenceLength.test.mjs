import test from 'node:test'
import assert from 'node:assert/strict'

import { DEFAULT_SEQUENCE_LENGTH, resolveSequenceLengths } from '../utils/sequenceLength.js'

test('resolveSequenceLengths keeps provided upstream and downstream values', () => {
  assert.deepEqual(resolveSequenceLengths({ upstreamLength: 500, downstreamLength: 2000 }), {
    upstreamLength: 500,
    downstreamLength: 2000
  })
})

test('resolveSequenceLengths falls back to aliases and existing values', () => {
  assert.deepEqual(resolveSequenceLengths({ upstream: 1500 }, 300, 900), {
    upstreamLength: 1500,
    downstreamLength: 900
  })
})

test('resolveSequenceLengths uses a scalar value for both lengths', () => {
  assert.deepEqual(resolveSequenceLengths(750), {
    upstreamLength: 750,
    downstreamLength: 750
  })
})

test('resolveSequenceLengths uses defaults when no value is provided', () => {
  assert.deepEqual(resolveSequenceLengths(undefined), {
    upstreamLength: DEFAULT_SEQUENCE_LENGTH,
    downstreamLength: DEFAULT_SEQUENCE_LENGTH
  })
})
