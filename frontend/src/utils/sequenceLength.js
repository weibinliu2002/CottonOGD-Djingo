export const DEFAULT_SEQUENCE_LENGTH = 10000

export function resolveSequenceLengths(lengths, fallbackUpstream = DEFAULT_SEQUENCE_LENGTH, fallbackDownstream = DEFAULT_SEQUENCE_LENGTH) {
  if (typeof lengths === 'object' && lengths !== null) {
    return {
      upstreamLength: lengths.upstreamLength ?? lengths.upstream ?? fallbackUpstream,
      downstreamLength: lengths.downstreamLength ?? lengths.downstream ?? fallbackDownstream
    }
  }

  return {
    upstreamLength: lengths ?? fallbackUpstream,
    downstreamLength: lengths ?? fallbackDownstream
  }
}
