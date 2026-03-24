import { ref, type Ref } from 'vue'
import { resolveSequenceLengths } from '@/utils/sequenceLength'

interface UseLengthSelectorReturn {
  upstreamLength: Ref<number>
  downstreamLength: Ref<number>
  setLengths: (upstream: number, downstream: number) => void
  handleLengthChange: (lengths: any) => boolean
}

export function useLengthSelector(initialUpstream: number = 10000, initialDownstream: number = 10000): UseLengthSelectorReturn {
  const upstreamLength = ref(initialUpstream)
  const downstreamLength = ref(initialDownstream)

  const setLengths = (upstream: number, downstream: number) => {
    upstreamLength.value = upstream
    downstreamLength.value = downstream
  }

  const handleLengthChange = (lengths: any): boolean => {
    const { upstreamLength: newUpstreamLength, downstreamLength: newDownstreamLength } = resolveSequenceLengths(
      lengths,
      upstreamLength.value,
      downstreamLength.value
    )

    const changed = newUpstreamLength !== upstreamLength.value || newDownstreamLength !== downstreamLength.value

    upstreamLength.value = newUpstreamLength
    downstreamLength.value = newDownstreamLength

    return changed
  }

  return {
    upstreamLength,
    downstreamLength,
    setLengths,
    handleLengthChange
  }
}
