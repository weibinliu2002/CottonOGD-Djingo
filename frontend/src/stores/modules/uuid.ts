import { defineStore } from 'pinia';
import { ref, onMounted } from 'vue';
import { v4 as uuidv4 } from 'uuid';

export const useUUIDStore = defineStore('uuid', () => {
  const uuid = ref('');

  const generateUUID = () => {
    uuid.value = uuidv4();
  };

  onMounted(() => {
    if (!uuid.value) {
      generateUUID();
    }
  });

  return { uuid, generateUUID };
});
