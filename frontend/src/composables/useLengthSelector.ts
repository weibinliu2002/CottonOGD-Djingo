import { ref, type Ref } from 'vue'

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
    let newUpstreamLength, newDownstreamLength
    if (typeof lengths === 'object' && lengths !== null) {
      newUpstreamLength = lengths.upstreamLength ?? lengths.upstream ?? upstreamLength.value
      newDownstreamLength = lengths.downstreamLength ?? lengths.downstream ?? downstreamLength.value
    } else {
      newUpstreamLength = lengths ?? upstreamLength.value
      newDownstreamLength = lengths ?? downstreamLength.value
    }

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
